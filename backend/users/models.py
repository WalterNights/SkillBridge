import random
import string
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# SEGURIDAD: extensiones permitidas para imágenes de perfil. SVG queda
# fuera a propósito — puede embed JS y, servido same-origin como `<img>`,
# ejecutar XSS. Si en el futuro se necesita SVG, hay que sanitizarlo y
# servirlo con Content-Disposition: attachment.
_ALLOWED_IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "webp")
_ALLOWED_IMAGE_FORMATS = ("JPEG", "PNG", "WEBP")
_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


def validate_uploaded_image(value):
    """Valida imágenes subidas (photo, banner) contra spoofing y bombs.

    Tres capas:
      1. Extensión en allow-list.
      2. Tamaño máximo 5MB (anti decompression bomb + DoS de disco).
      3. Magic bytes vía Pillow — la extensión sola no garantiza nada
         (un atacante puede renombrar `evil.svg` a `evil.png`).
    """
    from PIL import Image, UnidentifiedImageError

    name = getattr(value, "name", "") or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in _ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f"Formato no permitido. Usá: {', '.join(_ALLOWED_IMAGE_EXTENSIONS)}."
        )

    size = getattr(value, "size", 0)
    if size > _MAX_IMAGE_BYTES:
        raise ValidationError(f"La imagen excede {_MAX_IMAGE_BYTES // (1024 * 1024)} MB.")

    # Pillow lee el header y verifica el formato real (magic bytes).
    try:
        value.seek(0)
        img = Image.open(value)
        img.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError("El archivo no es una imagen válida.") from exc
    finally:
        try:
            value.seek(0)
        except Exception:
            pass

    if img.format not in _ALLOWED_IMAGE_FORMATS:
        raise ValidationError(
            "El contenido del archivo no coincide con un formato de imagen permitido."
        )


def strip_image_metadata(uploaded_file):
    """Devuelve un nuevo InMemoryUploadedFile sin EXIF/metadata.

    Las fotos de teléfono suelen incluir coordenadas GPS y modelo de
    dispositivo en EXIF. Servidos same-origin como avatar, son un leak
    de privacidad pasivo. Re-codificamos via Pillow.save() sin pasarle
    el bloque `exif`, lo que descarta también XMP y comentarios.

    Idempotente sobre archivos ya limpios. Si Pillow no puede abrir el
    archivo devolvemos el original — el validator ya corrió antes y
    debería haber rechazado un archivo inválido.
    """
    import io

    from django.core.files.uploadedfile import InMemoryUploadedFile
    from PIL import Image

    try:
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        # `load()` fuerza el decode completo; sin esto el save() puede
        # arrastrar el header del archivo original con su EXIF intacto.
        img.load()
    except Exception:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass
        return uploaded_file

    fmt = img.format or "JPEG"
    if fmt not in _ALLOWED_IMAGE_FORMATS:
        uploaded_file.seek(0)
        return uploaded_file

    # `getexif()` existe en JPEG/PNG/WEBP modernos pero no en todos
    # los modos. Si el archivo no tiene EXIF (ya limpio), evitamos el
    # re-encode para no perder calidad innecesariamente.
    has_exif = bool(getattr(img, "_getexif", lambda: None)()) or bool(img.info.get("exif"))
    has_xmp = bool(img.info.get("xmp") or img.info.get("XML:com.adobe.xmp"))
    if not has_exif and not has_xmp:
        uploaded_file.seek(0)
        return uploaded_file

    if fmt == "JPEG" and img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    buffer = io.BytesIO()
    save_kwargs = {"format": fmt}
    if fmt == "JPEG":
        save_kwargs["quality"] = 90
        save_kwargs["optimize"] = True
    img.save(buffer, **save_kwargs)
    size = buffer.tell()
    buffer.seek(0)

    content_type_map = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
    return InMemoryUploadedFile(
        file=buffer,
        field_name=getattr(uploaded_file, "field_name", None),
        name=uploaded_file.name,
        content_type=content_type_map.get(fmt, "application/octet-stream"),
        size=size,
        charset=None,
    )


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("rol", "user")

        if not email:
            raise ValueError("El usuario debe tener un correo electrónico")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("rol", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superusuario debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superusuario debe tener is_superuser=True.")

        return self.create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    ROL_CHOICES = [
        ("user", "User"),
        ("admin", "Admin"),
    ]

    rol = models.CharField(max_length=10, choices=ROL_CHOICES, default="user")
    create_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    def __str__(self):
        return f"{self.username}"


class UserProfile(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.PROTECT, related_name="profile")
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    number_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=30)
    city = models.CharField(max_length=100)
    professional_title = models.CharField(max_length=100)
    summary = models.TextField(blank=True)
    education = models.TextField(blank=True)
    skills = models.TextField(help_text="Lista de habilidades separadas por coma")
    experience = models.TextField(help_text="Descripción libre de experiencia")
    resume = models.FileField(upload_to="resumes/", null=True, blank=True)
    photo = models.ImageField(
        upload_to="profile_photos/",
        null=True,
        blank=True,
        validators=[validate_uploaded_image],
    )
    banner = models.ImageField(
        upload_to="profile_banners/",
        null=True,
        blank=True,
        validators=[validate_uploaded_image],
    )
    linkedin_url = models.URLField(null=True, blank=True)
    portfolio_url = models.URLField(null=True, blank=True)
    create_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Perfil de {self.user.username}"


class PasswordResetToken(models.Model):
    """Modelo para almacenar tokens de restablecimiento de contraseña"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reset_tokens")
    code = models.CharField(max_length=6)  # Código de 6 dígitos
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Reset token for {self.user.username} - {self.code}"

    def is_valid(self):
        """Verifica si el token aún es válido (no expirado y no usado)"""
        from django.conf import settings

        expiration_time = self.created_at + timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)
        return not self.is_used and timezone.now() < expiration_time

    @staticmethod
    def generate_code():
        """Genera un código de 8 dígitos usando un CSPRNG.

        SEGURIDAD: 8 dígitos → 100M combos (vs 1M con 6). Con el rate
        limit del endpoint verify (10/h por IP), atacar el código fuerza
        bruta requeriría ~1000 años — efectivamente inviable. `secrets`
        usa el CSPRNG del SO (vs `random` que es Mersenne Twister
        predecible si conoce el seed).
        """
        import secrets

        return "".join(str(secrets.randbelow(10)) for _ in range(8))
