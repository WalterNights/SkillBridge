from rest_framework import serializers

from users.models import PasswordResetToken, User, UserProfile, strip_image_metadata


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    # SEGURIDAD: `rol` es read-only para prevenir mass-assignment desde
    # el endpoint público de register. Sin esto, cualquiera podía POSTear
    # con `{"rol": "admin"}` y crearse cuenta privilegiada.
    rol = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "rol"]

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
