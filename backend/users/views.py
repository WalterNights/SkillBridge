from django.conf import settings
from django.core.mail import send_mail
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from users.models import PasswordResetToken, User, UserProfile
from users.serializers import (
    PasswordResetRequestSerializer,
    PasswordResetVerifySerializer,
    UserProfileSerializer,
    UserSerializer,
)
from users.services.achievement_quantifier import QuantifyError, quantify_achievement
from users.services.cv_analysis_service import get_cv_analyzer
from users.services.cv_auditor import AuditError, audit_cv, profile_to_audit_payload
from users.services.profile_service import ProfileService


@method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True), name="post")
class UserRegisterView(APIView):
    """Vista para registro de nuevos usuarios.

    SEGURIDAD: rate limit 5/min por IP (anti-spam de cuentas).
    Los errores de validación se generalizan para no exponer si un
    username/email ya existe (anti user-enumeration).
    """

    permission_classes = [AllowAny]

    # Campos en `serializer.errors` que disparan el mensaje genérico —
    # cualquiera de estos revela existencia de cuenta en el sistema.
    _ENUM_FIELDS = ("username", "email")

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Usuario creado exitosamente", "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )

        errors = serializer.errors
        if any(field in errors for field in self._ENUM_FIELDS):
            # No diferenciar entre "username taken", "email taken", o
            # "email malformed" — todos son "no pudimos crear la cuenta".
            return Response(
                {"error": "No pudimos crear la cuenta con esos datos."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(
    ratelimit(key="user_or_ip", rate="10/h", method="POST", block=True), name="post"
)
class AnalyzerResumeView(APIView):
    """Vista para analizar CVs y extraer información usando Gemini AI.

    SEGURIDAD: requiere autenticación + rate limit 10/hora por usuario.
    El endpoint despacha el archivo a Gemini AI (costoso por request) —
    sin auth + rate limit, un atacante podía drenar tu cuota de la API
    en minutos. Cuando el front llama a este endpoint, el usuario ya
    pasó por register/login.
    """

    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        file = request.FILES.get("resume")

        if not file:
            return Response(
                {"error": "No se proporcionó ningún archivo"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            analyzer = get_cv_analyzer()

            is_valid, error_message = analyzer.validate(file)
            if not is_valid:
                return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)

            extracted_data = analyzer.analyze(file)

            # Formatear respuesta para mantener compatibilidad con el frontend
            response_data = {
                "first_name": extracted_data.get("first_name", ""),
                "last_name": extracted_data.get("last_name", ""),
                "email": extracted_data.get("email", ""),
                "number_id": "",  # Este campo se llena manualmente
                "phone_code": extracted_data.get("phone_code", ""),
                "phone_number": extracted_data.get("phone_number", ""),
                "country": extracted_data.get("country", ""),
                "city": extracted_data.get("city", ""),
                "professional_title": extracted_data.get("professional_title", ""),
                "summary": extracted_data.get("summary", ""),
                "education": extracted_data.get("education", []),  # Puede ser array o string
                "skills": extracted_data.get("skills", ""),
                "experience": extracted_data.get("experience", []),  # Puede ser array o string
                "linkedin_url": extracted_data.get("linkedin_url", ""),
                "portfolio_url": extracted_data.get("portfolio_url", ""),
                "full_name": extracted_data.get("full_name", ""),
                # Nuevos campos extraídos por el prompt mejorado.
                "soft_skills": extracted_data.get("soft_skills", ""),
                "languages": extracted_data.get("languages", []),
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except ValueError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Log error for debugging but don't expose details to client
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"CV analysis error: {e!s}", exc_info=True)
            return Response(
                {"error": "Error al analizar el archivo"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de perfiles de usuario.

    Endpoints:
    - GET /users/profiles/ - Obtener perfil del usuario autenticado
    - POST /users/profiles/ - Crear o actualizar perfil
    - GET /users/profiles/check/ - Verificar si perfil está completo
    """

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Retorna solo el perfil del usuario autenticado"""
        return UserProfile.objects.filter(user=self.request.user).select_related("user")

    def create(self, request):
        """Crea o actualiza el perfil del usuario.

        Delega en `UserProfileSerializer` (que ya mapea todos los campos
        del modelo + combina phone_code/phone_number en `phone`). El
        path POST/profiles/ funciona como upsert: si el usuario ya
        tiene perfil — siempre tiene uno vacío creado al registro —
        hacemos partial update para que un payload incompleto no
        nullee campos que ya estaban llenos.

        Esto reemplaza el `ProfileService.create_profile/update_profile`
        anterior que silenciosamente descartaba ~10 campos (sólo
        persistía `skills/city/summary`) y mapeaba a una columna
        inexistente `title` en lugar de `professional_title`.
        """
        user = request.user
        existing = ProfileService.get_profile_by_user(user)

        if existing is not None:
            serializer = self.get_serializer(
                existing, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def check(self, request):
        """Verifica si el perfil del usuario está completo"""
        if not ProfileService.profile_exists(request.user):
            return Response(
                {"error": "Profile not found", "profile_complete": False},
                status=status.HTTP_404_NOT_FOUND,
            )

        profile = ProfileService.get_profile_by_user(request.user)
        is_complete = all([profile.first_name, profile.last_name, profile.city, profile.phone])

        return Response({"profile_complete": is_complete}, status=status.HTTP_200_OK)


@method_decorator(
    ratelimit(key="user", rate="10/h", method="POST", block=True), name="post"
)
class CvAuditView(APIView):
    """POST /api/users/cv/audit/ → análisis estructural del CV del user
    autenticado. Sin body — usa request.user.profile.

    Response: {score, overall, categories[], top_recommendations[]}
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = ProfileService.get_profile_by_user(request.user)
        if profile is None:
            return Response(
                {"error": "profile_missing", "detail": "Completá tu perfil antes de auditarlo."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            result = audit_cv(profile_to_audit_payload(profile))
        except AuditError as exc:
            return Response(
                {"error": "audit_failed", "detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(result)


@method_decorator(
    ratelimit(key="user", rate="20/h", method="POST", block=True), name="post"
)
class QuantifyAchievementView(APIView):
    """POST /api/users/cv/quantify/ → devuelve 3 variantes cuantificadas
    de un bullet de experiencia.

    Body: {"text": str, "role_title": str (opcional), "company": str (opcional)}
    Response: {"suggestions": [str, str, str]}

    Rate-limit: 20/hora por user — Gemini cuesta tokens. El user puede
    abrir y regenerar varias veces pero no farmear ilimitado.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = (request.data.get("text") or "").strip()
        role_title = (request.data.get("role_title") or "").strip()
        company = (request.data.get("company") or "").strip()

        if not text:
            return Response(
                {"error": "text is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            suggestions = quantify_achievement(
                original_text=text,
                role_title=role_title,
                company=company,
            )
        except QuantifyError as exc:
            return Response(
                {"error": "quantify_failed", "detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"suggestions": suggestions})


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Serializer personalizado para incluir datos de perfil en token"""

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        data["user_id"] = user.id
        data["username"] = user.username
        data["email"] = user.email
        data["rol"] = user.rol

        # Mismo gate que el endpoint /profiles/check/ — más realista
        # que `number_id is not None`: ese campo es opcional en el
        # modelo y el form no siempre lo manda, así que muchos perfiles
        # con datos válidos quedaban marcados como incompletos y el
        # frontend bouncea al wizard de /profile en cada login.
        profile = ProfileService.get_profile_by_user(user)
        if profile:
            data["is_profile_complete"] = bool(
                profile.first_name
                and profile.last_name
                and profile.city
                and profile.phone
                and profile.professional_title
            )
            data["user_name"] = profile.first_name
            # Sumamos professional_title al payload del login para que el
            # frontend pueda inferir la profesión del usuario sin un
            # roundtrip extra a /profiles/ — usado al menos por el widget
            # de tips del sidebar para pedir tips de su vertical.
            data["professional_title"] = profile.professional_title or ""
            # URL absoluta de la foto para el avatar del topbar. None si
            # el user no subió foto — el frontend cae al initial.
            request = self.context.get("request")
            if profile.photo and request is not None:
                data["profile_photo"] = request.build_absolute_uri(profile.photo.url)
            else:
                data["profile_photo"] = ""
        else:
            data["is_profile_complete"] = False
            data["professional_title"] = ""
            data["profile_photo"] = ""

        return data


@method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True), name="post")
class CustomTokenObtainPairView(TokenObtainPairView):
    """Vista personalizada para obtención de tokens JWT.

    SEGURIDAD: rate limit 5/min por IP en el login — anti credential
    stuffing y brute force. Combinado con el lockout natural de JWT
    (cada intento es un POST sincronico), ataques offline necesitan
    horas para probar ~300 credenciales.
    """

    serializer_class = CustomTokenObtainPairSerializer


@method_decorator(ratelimit(key="ip", rate="3/h", method="POST", block=True), name="post")
class PasswordResetRequestView(APIView):
    """Vista para solicitar restablecimiento de contraseña.

    SEGURIDAD: rate limit 3/hora por IP. Combinado con el mensaje
    genérico (ver `post()`), evita email enumeration scanning.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Solicita un código de password reset.

        SEGURIDAD: Siempre devuelve 200 con el mismo mensaje genérico,
        exista o no el email — evita user enumeration. Si el email no
        está registrado, no se hace nada server-side (no se crea token,
        no se envía email). El response time se mantiene similar a un
        envío real para evitar timing oracles.
        """
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        generic_response = Response(
            {"message": "Si el email existe en nuestro sistema, te enviamos un código."},
            status=status.HTTP_200_OK,
        )

        user = User.objects.filter(email=email).first()
        if user is None:
            return generic_response

        code = PasswordResetToken.generate_code()
        token = PasswordResetToken.objects.create(user=user, code=code)

        subject = "Código de restablecimiento de contraseña - SkilTak"
        message = (
            f"Hola {user.username},\n\n"
            f"Has solicitado restablecer tu contraseña en SkilTak.\n\n"
            f"Tu código de verificación es: {code}\n\n"
            f"Este código expirará en 10 minutos.\n\n"
            f"Si no solicitaste este cambio, ignora este mensaje.\n\n"
            f"Saludos,\nEl equipo de SkilTak"
        )

        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
        except Exception as e:
            # No filtramos el error al cliente — el mensaje genérico es el
            # mismo que cuando el email no existe. Solo logueamos para ops.
            token.delete()
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Email sending error: {type(e).__name__}", exc_info=True)

        return generic_response


@method_decorator(ratelimit(key="ip", rate="10/h", method="POST", block=True), name="post")
class PasswordResetVerifyView(APIView):
    """Vista para verificar código y restablecer contraseña.

    SEGURIDAD: rate limit 10/hora por IP — el código es de 6 dígitos
    (1M combos) pero el rate limit reduce el espacio efectivo a ~240
    intentos antes de que el token expire (10 min) y bloquee la IP
    durante 1h.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Obtener usuario y token validados
        user = serializer.validated_data["user"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        # Cambiar contraseña
        user.set_password(new_password)
        user.save()

        # Marcar token como usado
        token.is_used = True
        token.save()

        return Response(
            {"message": "Contraseña restablecida exitosamente"}, status=status.HTTP_200_OK
        )
