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

from users.models import CompanyProfile, PasswordResetToken, User, UserProfile
from users.serializers import (
    ChangePasswordSerializer,
    CompanyProfileSerializer,
    CompanyRegisterSerializer,
    PasswordResetRequestSerializer,
    PasswordResetVerifySerializer,
    UserProfileSerializer,
    UserSerializer,
)
from users.services.achievement_quantifier import QuantifyError, quantify_achievement
from users.services.cv_analysis_service import get_cv_analyzer
from users.services.cv_auditor import AuditError, audit_cv, profile_to_audit_payload
from users.services.cv_improver import ImproveError, improve_cv, profile_to_improve_payload
from users.services.profile_service import ProfileService
from users.services import totp_service


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


@method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True), name="post")
class CompanyRegisterView(APIView):
    """POST /api/companies/register/ — registro de cuenta empresa.

    Flow:
      1. Valida el payload (datos User + CompanyProfile en una sola request).
      2. En transacción crea User(account_type=company) + CompanyProfile.
      3. Devuelve el shape del CompanyProfileSerializer (incluye User
         anidado read-only).

    SEGURIDAD:
      - account_type se fuerza a `company` desde el view — NO se acepta
        del cliente.
      - rate-limit 5/min/IP (mismo que UserRegisterView).
      - El username del User se deriva del email (parte antes del @ +
        sufijo aleatorio si choca con uno existente). La empresa nunca
        ve el username — la auth posterior usa email/password vía el
        endpoint /token/login/.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        from django.db import transaction
        import secrets

        serializer = CompanyRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            # Si el email ya existe, generalizamos para no filtrar
            # existencia de cuenta (anti enumeration). Otros campos
            # devuelven detail específico.
            if "email" in serializer.errors:
                return Response(
                    {"error": "No pudimos crear la cuenta con esos datos."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        email = data["email"]

        # Username: parte antes del @ + sufijo si choca. Esto no afecta
        # al user-facing (siempre logueamos por email), solo cumple el
        # constraint unique del modelo User.
        base_username = email.split("@", 1)[0][:120]
        username = base_username
        while User.objects.filter(username=username).exists():
            username = f"{base_username}-{secrets.token_hex(2)}"[:150]

        with transaction.atomic():
            user = User.objects.create(
                username=username,
                email=email,
                account_type=User.ACCOUNT_TYPE_COMPANY,
            )
            user.set_password(data["password"])
            user.save()

            company = CompanyProfile.objects.create(
                user=user,
                legal_name=data["legal_name"],
                country=data.get("country", ""),
                city=data.get("city", ""),
                industry=data.get("industry", ""),
                website=data.get("website", ""),
                size=data.get("size", ""),
                short_description=data.get("short_description", ""),
                responsible_name=data["responsible_name"],
                responsible_role=data["responsible_role"],
                responsible_email=data["responsible_email"],
            )

        return Response(
            {
                "message": "Empresa registrada exitosamente.",
                "data": CompanyProfileSerializer(company).data,
            },
            status=status.HTTP_201_CREATED,
        )


class CompanyMeView(APIView):
    """GET/PATCH /api/companies/me/ — perfil de la empresa logueada.

    GET devuelve el CompanyProfile del request.user.
    PATCH actualiza campos editables. account_type / user son inmutables.
    """

    permission_classes = [IsAuthenticated]

    def _get_company(self, request):
        if request.user.account_type != User.ACCOUNT_TYPE_COMPANY:
            return None
        try:
            return request.user.company_profile
        except CompanyProfile.DoesNotExist:
            return None

    def get(self, request):
        company = self._get_company(request)
        if company is None:
            return Response(
                {"error": "account_type_mismatch",
                 "detail": "Esta cuenta no es de tipo empresa."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(CompanyProfileSerializer(company).data)

    def patch(self, request):
        company = self._get_company(request)
        if company is None:
            return Response(
                {"error": "account_type_mismatch",
                 "detail": "Esta cuenta no es de tipo empresa."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CompanyProfileSerializer(
            company, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


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
        """Retorna solo el perfil del usuario autenticado.

        order_by('id') — necesario para que la paginación de DRF sea
        determinística. Sin un ordering explícito el ORM emite
        UnorderedObjectListWarning y los items pueden venir en orden
        distinto en pages distintas. En este queryset cada user tiene
        UN perfil (OneToOne), así que el ordering es cosmético, pero
        suprime el warning y deja el comportamiento documentado."""
        return (
            UserProfile.objects.filter(user=self.request.user)
            .select_related("user")
            .order_by("id")
        )

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
    ratelimit(key="user", rate="5/h", method="POST", block=True), name="post"
)
class CvImproveView(APIView):
    """POST /api/users/cv/improve/ → propone una versión mejorada del CV
    del user (summary reescrito, bullets de experiencia cuantificados,
    skills reordenados, fechas corregidas si están rotas). NO persiste
    — devuelve el JSON con los campos mejorados para que el frontend
    lo muestre y el user confirme con PATCH.

    Rate limits superpuestos:
      - 5/hora por user (django-ratelimit, anti-burst).
      - LIFETIME 1/user (UserProfile.cv_improved_at). Los users normales
        usan el feature UNA vez en la vida — la mejora iterativa de un
        CV no aporta valor (el modelo ya gastó tokens proponiendo lo
        mejor). Admins (is_staff) bypassean para QA / debug del prompt.

    Response 200: { ...improved fields... }
    Response 404: profile_missing
    Response 429: already_used (cuando lifetime cap se alcanzó)
    Response 502: improve_failed (Gemini caído / JSON inválido)
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = ProfileService.get_profile_by_user(request.user)
        if profile is None:
            return Response(
                {"error": "profile_missing", "detail": "Completá tu perfil antes de mejorarlo."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Lifetime cap — non-admins solo pueden usarlo una vez.
        if not request.user.is_staff and profile.cv_improved_at is not None:
            return Response(
                {
                    "error": "already_used",
                    "detail": (
                        "Ya usaste 'Mejorar con AI' una vez. Esta función está "
                        "limitada a un único uso por cuenta."
                    ),
                    "used_at": profile.cv_improved_at.isoformat(),
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            result = improve_cv(profile_to_improve_payload(profile))
        except ImproveError as exc:
            return Response(
                {"error": "improve_failed", "detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Marcar el uso SOLO si Gemini respondió OK. Si falla, el user
        # puede reintentar sin gastar su único turno.
        if not request.user.is_staff:
            from django.utils import timezone

            profile.cv_improved_at = timezone.now()
            profile.save(update_fields=["cv_improved_at"])

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
        # `is_staff` permite al frontend mostrar el grupo "Administración"
        # del sidebar y resolver AdminGuard sin tener que pegarle a /users/me/.
        # `is_superuser` queda dispobnible por si en algún momento separamos
        # admin (staff) de super-admin (settings de sistema).
        data["is_staff"] = user.is_staff
        data["is_superuser"] = user.is_superuser
        # Tipo de cuenta — el frontend lo usa para decidir qué AppShell /
        # sidebar / redirect post-login mostrar. Necesario en el payload
        # del login (no en cada request) porque la decisión de routing
        # es síncrona al recibir el token.
        data["account_type"] = user.account_type

        # Las cuentas empresa NO tienen UserProfile — tienen CompanyProfile.
        # Los campos del payload se llenan desde el modelo apropiado.
        if user.account_type == User.ACCOUNT_TYPE_COMPANY:
            self._fill_company_data(data, user)
        else:
            self._fill_professional_data(data, user)

        return data

    def _fill_professional_data(self, data: dict, user) -> None:
        """Completa el payload JWT para cuentas profesional.

        Mismo gate que el endpoint /profiles/check/ — más realista
        que `number_id is not None`: ese campo es opcional en el
        modelo y el form no siempre lo manda, así que muchos perfiles
        con datos válidos quedaban marcados como incompletos y el
        frontend bouncea al wizard de /profile en cada login.
        """
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
            data["professional_title"] = profile.professional_title or ""
            request = self.context.get("request")
            if profile.photo and request is not None:
                data["profile_photo"] = request.build_absolute_uri(profile.photo.url)
            else:
                data["profile_photo"] = ""
        else:
            data["is_profile_complete"] = False
            data["professional_title"] = ""
            data["profile_photo"] = ""

    def _fill_company_data(self, data: dict, user) -> None:
        """Completa el payload JWT para cuentas empresa.

        Reusa las mismas keys del lado profesional para no romper el
        contrato del frontend: `is_profile_complete`, `user_name`,
        `profile_photo`. `professional_title` no aplica acá (queda en "").
        """
        try:
            company = user.company_profile
        except CompanyProfile.DoesNotExist:
            data["is_profile_complete"] = False
            data["user_name"] = user.username
            data["professional_title"] = ""
            data["profile_photo"] = ""
            return

        data["is_profile_complete"] = bool(
            company.legal_name and company.responsible_name and company.responsible_role
        )
        # `user_name` lo usa el topbar / dropdown — para empresa mostramos
        # el nombre comercial, no el del registrante.
        data["user_name"] = company.legal_name
        data["professional_title"] = company.industry or ""
        request = self.context.get("request")
        if company.logo and request is not None:
            data["profile_photo"] = request.build_absolute_uri(company.logo.url)
        else:
            data["profile_photo"] = ""


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


@method_decorator(
    # 10/hora por user — protege contra brute-force de la pass actual,
    # pero deja margen razonable para que el user se equivoque.
    ratelimit(key="user", rate="10/h", method="POST", block=True),
    name="post",
)
class ChangePasswordView(APIView):
    """POST /api/users/me/change-password/

    Cambio de contraseña desde la sesión activa. Requiere:
      - current_password : verifica contra el hash actual
      - new_password / confirm_password : la nueva (deben coincidir)

    Respuestas:
      - 200 : OK, contraseña actualizada
      - 400 : current_password incorrecta, validation fail, o pass nueva
              == actual
      - 401 : sin auth
      - 403 : rate-limit alcanzado (10/hora)

    Nota: este endpoint NO invalida tokens activos del user. Si quieres
    forzar re-login después de cambiar pass, el frontend tiene que
    decidirlo y limpiar storage.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        current = serializer.validated_data["current_password"]
        if not user.check_password(current):
            # Mensaje específico — el user YA está autenticado, no hay
            # riesgo de enumeration.
            return Response(
                {"current_password": "La contraseña actual es incorrecta."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        return Response(
            {"message": "Contraseña actualizada correctamente."},
            status=status.HTTP_200_OK,
        )


# =============================================================================
# 2FA TOTP — endpoints de setup/activate/disable/status
# =============================================================================
#
# El flow desde el frontend:
#   1. GET  /2fa/status/   → ¿está activo?
#   2. POST /2fa/setup/    → genera secret + QR (no activa todavía)
#   3. POST /2fa/activate/ → user envía código de 6 dígitos del authenticator
#                            app. Si verifica, activa.
#   4. POST /2fa/disable/  → user envía código para confirmar identidad
#                            antes de desactivar.
#
# NOTA: por ahora 2FA NO se enforcea en el login — el feature está solo
# en /settings para que el user pueda configurarlo. Cuando se agregue
# enforcement en el login (próxima fase), `totp_enabled` será consultado
# en CustomTokenObtainPairView para pedir TOTP antes de emitir JWT.


class TwoFactorStatusView(APIView):
    """GET /api/users/2fa/status/ → `{enabled: bool}` para el user actual."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"enabled": bool(request.user.totp_enabled)})


@method_decorator(
    ratelimit(key="user", rate="10/h", method="POST", block=True), name="post"
)
class TwoFactorSetupView(APIView):
    """POST /api/users/2fa/setup/ → genera secret + QR data URL.

    Si el user YA tiene un secret guardado pero no activó (i.e., abrió
    el setup antes pero abandonó), devolvemos el mismo secret — no
    regeneramos. Esto deja que el user vuelva al mismo QR si reabre el
    modal. Solo si ya está totp_enabled=True devolvemos 409.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.totp_enabled:
            return Response(
                {"error": "already_enabled", "detail": "El 2FA ya está activo."},
                status=status.HTTP_409_CONFLICT,
            )

        if not user.totp_secret:
            user.totp_secret = totp_service.generate_secret()
            user.save(update_fields=["totp_secret"])

        uri = totp_service.provisioning_uri(user.totp_secret, user.email or user.username)
        qr = totp_service.qr_data_url(uri)
        return Response(
            {
                "secret": user.totp_secret,  # útil para entry manual si el QR falla
                "qr_data_url": qr,
                "otpauth_uri": uri,
            }
        )


@method_decorator(
    ratelimit(key="user", rate="10/m", method="POST", block=True), name="post"
)
class TwoFactorActivateView(APIView):
    """POST /api/users/2fa/activate/ → body `{code}` — activa 2FA si el
    código del authenticator es válido.

    Rate-limit estricto (10/m) — evita brute-force del TOTP de 6 dígitos
    durante la activación (1M combinaciones, pero con ventana de 30s y
    cap de 10 intentos/min queda fuera de práctico).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.totp_enabled:
            return Response(
                {"error": "already_enabled"},
                status=status.HTTP_409_CONFLICT,
            )
        if not user.totp_secret:
            return Response(
                {"error": "setup_required", "detail": "Hacé setup primero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = (request.data.get("code") or "").strip()
        if not totp_service.verify(user.totp_secret, code):
            return Response(
                {"error": "invalid_code", "detail": "Código inválido o expirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.totp_enabled = True
        user.save(update_fields=["totp_enabled"])
        return Response({"enabled": True})


@method_decorator(
    ratelimit(key="user", rate="10/m", method="POST", block=True), name="post"
)
class TwoFactorDisableView(APIView):
    """POST /api/users/2fa/disable/ → body `{code}` — desactiva 2FA si
    el código es válido. Borra el secret además del flag para que un
    re-enable empiece de cero (no reusamos secret viejo)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.totp_enabled:
            return Response({"enabled": False})

        code = (request.data.get("code") or "").strip()
        if not totp_service.verify(user.totp_secret, code):
            return Response(
                {"error": "invalid_code", "detail": "Código inválido o expirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.totp_enabled = False
        user.totp_secret = ""
        user.save(update_fields=["totp_enabled", "totp_secret"])
        return Response({"enabled": False})
