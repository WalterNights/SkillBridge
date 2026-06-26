from rest_framework import serializers

from users.models import (
    CompanyInterest,
    CompanyProfile,
    PasswordResetToken,
    User,
    UserProfile,
    strip_image_metadata,
)


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    # SEGURIDAD: `rol`, `is_staff`, `is_superuser` y `account_type` son
    # read-only para prevenir mass-assignment desde el endpoint público
    # de register. Sin esto, cualquiera podía POSTear con `{"is_staff":
    # true}` y crearse cuenta privilegiada. El toggle de roles vive en
    # su propio endpoint admin-gated (PATCH /dashboard/users/{id}/role/).
    # `account_type` se setea en el endpoint de registro correspondiente
    # (UserRegisterView → professional, CompanyRegisterView → company).
    rol = serializers.CharField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
    account_type = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "rol",
            "is_staff",
            "is_superuser",
            "account_type",
        ]

    def create(self, validate_data):
        password = validate_data.pop("password")
        user = User(**validate_data)
        user.set_password(password)
        user.save()
        UserProfile.objects.create(user=user)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    phone_code = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(write_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "user",
            "first_name",
            "last_name",
            "number_id",
            "phone_code",
            "phone_number",
            "phone",
            "city",
            "professional_title",
            "summary",
            "education",
            "skills",
            "experience",
            "resume",
            "photo",
            "banner",
            "linkedin_url",
            "portfolio_url",
            "soft_skills",
            "languages",
            "email_alerts_enabled",
            "visible_to_companies",
        ]
        # `last_alert_sent_at` no se expone — es contador interno de la
        # tarea de alertas, no debería editarse desde el cliente.
        read_only_fields = ["phone"]

    def validate_photo(self, value):
        """SEGURIDAD: stripa EXIF/XMP. Las fotos de cámara mobile traen
        GPS y modelo de dispositivo, leak pasivo cuando se sirven public."""
        if not value:
            return value
        return strip_image_metadata(value)

    def validate_banner(self, value):
        """Mismo motivo que `validate_photo` — algunos banners vienen
        de cámaras y arrastran metadata sensible."""
        if not value:
            return value
        return strip_image_metadata(value)

    def validate_linkedin_url(self, value):
        """Normaliza el URL de LinkedIn sin romper los que ya vienen bien.

        Casos:
          - `https://linkedin.com/in/x`   → se respeta (ya tiene scheme)
          - `https://www.linkedin.com/.`  → se respeta
          - `www.linkedin.com/in/x`       → `https://www.linkedin.com/...`
          - `linkedin.com/in/x`           → `https://www.linkedin.com/...`
          - vacío                         → vacío

        La regla anterior (`if not value.startswith("https://www")`)
        prependía `https://www.` a cualquier cosa que no fuese ya
        canonical, lo cual le pegaba el prefijo DOS VECES a URLs ya
        válidas tipo `https://linkedin.com/in/x` y las dejaba como
        `https://www.https://linkedin.com/in/x`.
        """
        if not value:
            return value
        value = value.strip()
        if value.startswith(("http://", "https://")):
            return value
        if value.startswith("www."):
            return f"https://{value}"
        return f"https://www.{value}"

    def create(self, validate_data):
        phone_code = validate_data.pop("phone_code")
        phone_number = validate_data.pop("phone_number")
        validate_data["phone"] = f"{phone_code} {phone_number}"
        return super().create(validate_data)

    def update(self, instance, validate_data):
        phone_code = validate_data.pop("phone_code", None)
        phone_number = validate_data.pop("phone_number", None)
        if phone_code and phone_number:
            validate_data["phone"] = f"{phone_code} {phone_number}"
        return super().update(instance, validate_data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.phone:
            parts = instance.phone.strip().split()
            if len(parts) >= 2:
                rep["phone_code"] = parts[0]
                rep["phone_number"] = " ".join(parts[1:])
        return rep


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer para solicitar restablecimiento de contraseña.

    SEGURIDAD: NO validamos acá si el email existe. Devolver "no existe
    usuario" sería un vector de user enumeration — un atacante podría
    recorrer una lista de emails (de breaches públicas) y filtrar cuáles
    tienen cuenta acá para targeted phishing. La view decide si mandar
    o no el email basado en si el user existe, pero siempre responde
    200 con mensaje genérico.
    """

    email = serializers.EmailField()


class PasswordResetVerifySerializer(serializers.Serializer):
    """Serializer para verificar código y establecer nueva contraseña"""

    email = serializers.EmailField()
    # Aceptamos tanto los códigos viejos de 6 dígitos (compat) como los
    # nuevos de 8 hasta que vencen los emitidos antes del bump de entropía.
    code = serializers.CharField(max_length=8, min_length=6)
    new_password = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )

    def validate(self, data):
        """Valida que el usuario y el código sean correctos.

        SEGURIDAD: si el email no existe O el código no matchea, devolvemos
        el MISMO error genérico. Diferenciar "usuario no encontrado" vs
        "código inválido" sería user enumeration via password reset.
        """
        generic_error = "Código inválido o expirado."
        try:
            user = User.objects.get(email=data["email"])
        except User.DoesNotExist as exc:
            raise serializers.ValidationError(generic_error) from exc

        # Buscar el token más reciente no usado
        token = (
            PasswordResetToken.objects.filter(user=user, code=data["code"], is_used=False)
            .order_by("-created_at")
            .first()
        )

        if not token or not token.is_valid():
            raise serializers.ValidationError(generic_error)

        data["user"] = user
        data["token"] = token
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Cambio de contraseña desde la sesión activa del user.

    Pide la pass actual + la nueva (con confirmación) — la view valida
    `current_password` contra el hash en DB. Si el user perdió la pass
    debe usar el flow de password-reset (con email), no este.
    """

    current_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )
    confirm_password = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Las contraseñas no coinciden."}
            )
        if data["new_password"] == data["current_password"]:
            raise serializers.ValidationError(
                {"new_password": "La nueva contraseña debe ser distinta a la actual."}
            )
        return data


# =============================================================================
# CompanyProfile — lado empresa del marketplace
# =============================================================================


class CompanyProfileSerializer(serializers.ModelSerializer):
    """Vista completa del perfil de empresa — usada para GET /companies/me/
    y para el PATCH de edición."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = CompanyProfile
        fields = [
            "id",
            "user",
            "legal_name",
            "country",
            "city",
            "industry",
            "website",
            "size",
            "short_description",
            "logo",
            "responsible_name",
            "responsible_role",
            "responsible_email",
            "create_at",
            "update_at",
        ]
        read_only_fields = ["create_at", "update_at"]


class CompanyRegisterSerializer(serializers.Serializer):
    """Input del POST /api/companies/register/.

    Crea User + CompanyProfile en una sola transacción. El username del
    User se deriva del email (parte antes del @) — la empresa nunca lo
    ve, pero Django lo necesita unique.

    SEGURIDAD:
      - account_type se fuerza a `company` en el view, NO se acepta del
        cliente (defensa contra mass-assignment).
      - `is_staff`, `is_superuser`, `rol` jamás aparecen acá — no son
        seteables desde signup.
    """

    # ─── User auth ──────────────────────────────────────────────────
    email = serializers.EmailField()
    password = serializers.CharField(
        min_length=8, write_only=True, style={"input_type": "password"}
    )

    # ─── Company data ────────────────────────────────────────────────
    legal_name = serializers.CharField(max_length=120, trim_whitespace=True)
    country = serializers.CharField(
        max_length=60, required=False, allow_blank=True, default=""
    )
    city = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default=""
    )
    industry = serializers.CharField(
        max_length=80, required=False, allow_blank=True, default=""
    )
    website = serializers.URLField(required=False, allow_blank=True, default="")
    size = serializers.ChoiceField(
        choices=[c[0] for c in CompanyProfile.COMPANY_SIZE_CHOICES],
        required=False,
        allow_blank=True,
        default="",
    )
    short_description = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default=""
    )

    # ─── Responsable ─────────────────────────────────────────────────
    responsible_name = serializers.CharField(max_length=100, trim_whitespace=True)
    responsible_role = serializers.CharField(max_length=80, trim_whitespace=True)
    responsible_email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "Ya existe una cuenta con este correo electrónico."
            )
        return value.lower()


class ProfileDetailForCompanySerializer(serializers.ModelSerializer):
    """Vista detallada del perfil para el lado empresa.

    SEGURIDAD: jamás expone email, phone, ni number_id. El contacto va
    por flujo de "marcar interés" — el profesional decide si revelar
    email cuando responde desde su inbox.

    Es READ-ONLY: la empresa no puede modificar nada del profesional.
    """

    has_resume = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "first_name",
            "last_name",
            "professional_title",
            "city",
            "photo",
            "banner",
            "summary",
            "skills",
            "experience",
            "education",
            "soft_skills",
            "languages",
            "linkedin_url",
            "portfolio_url",
            "has_resume",
        ]
        read_only_fields = fields

    def get_has_resume(self, obj: UserProfile) -> bool:
        return bool(obj.resume)


class CompanyInterestSerializer(serializers.ModelSerializer):
    """Vista de un CompanyInterest, perspectiva empresa.
    Se usa en el response del POST de "marcar interés" para que el
    frontend sepa si era nuevo (created) o un update."""

    class Meta:
        model = CompanyInterest
        fields = ["id", "status", "message", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class InterestForProfessionalSerializer(serializers.ModelSerializer):
    """Vista de un CompanyInterest desde el lado del PROFESIONAL
    (inbox "empresas interesadas en mí").

    Privacy del email del responsable:
      - status=pending  → email NO se devuelve. El profesional ve el
        nombre de la empresa y un preview del mensaje, decide si
        aceptar antes de revelar contacto.
      - status=accepted → email visible. El profesional aceptó el
        interés y necesita el contacto para responder por fuera.
      - status=dismissed → email NO se devuelve. El profesional
        decidió no continuar; no tiene sentido revelar.
    """

    company_legal_name = serializers.CharField(source="company.legal_name", read_only=True)
    company_industry = serializers.CharField(source="company.industry", read_only=True)
    company_city = serializers.CharField(source="company.city", read_only=True)
    company_country = serializers.CharField(source="company.country", read_only=True)
    company_website = serializers.CharField(source="company.website", read_only=True)
    company_short_description = serializers.CharField(
        source="company.short_description", read_only=True
    )
    company_logo = serializers.SerializerMethodField()
    responsible_name = serializers.CharField(source="company.responsible_name", read_only=True)
    responsible_role = serializers.CharField(source="company.responsible_role", read_only=True)
    # Email gated por status (solo accepted).
    responsible_email = serializers.SerializerMethodField()

    class Meta:
        model = CompanyInterest
        fields = [
            "id",
            "status",
            "message",
            "created_at",
            "updated_at",
            "company_legal_name",
            "company_industry",
            "company_city",
            "company_country",
            "company_website",
            "company_short_description",
            "company_logo",
            "responsible_name",
            "responsible_role",
            "responsible_email",
        ]
        read_only_fields = fields

    def get_company_logo(self, obj: CompanyInterest) -> str:
        request = self.context.get("request")
        if obj.company.logo and request is not None:
            return request.build_absolute_uri(obj.company.logo.url)
        return ""

    def get_responsible_email(self, obj: CompanyInterest) -> str:
        # Solo revelamos el email cuando el profesional aceptó el
        # interés. En pending/dismissed devolvemos string vacío.
        if obj.status == CompanyInterest.STATUS_ACCEPTED:
            return obj.company.responsible_email
        return ""
