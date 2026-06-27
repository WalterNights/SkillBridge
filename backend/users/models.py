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

    # ─── Tipo de cuenta ────────────────────────────────────────────────
    # Distingue marketplaces: profesional busca ofertas, empresa busca
    # profesionales. Se setea en el signup y no debería cambiar después
    # (los flujos y datos son distintos). Default `professional` para
    # backwards-compat: todos los users existentes son profesionales.
    #
    # Admin staff puede ser de cualquier tipo — `is_staff` es ortogonal.
    ACCOUNT_TYPE_PROFESSIONAL = "professional"
    ACCOUNT_TYPE_COMPANY = "company"
    ACCOUNT_TYPE_CHOICES = [
        (ACCOUNT_TYPE_PROFESSIONAL, "Profesional"),
        (ACCOUNT_TYPE_COMPANY, "Empresa"),
    ]
    account_type = models.CharField(
        max_length=12,
        choices=ACCOUNT_TYPE_CHOICES,
        default=ACCOUNT_TYPE_PROFESSIONAL,
        db_index=True,
    )

    rol = models.CharField(max_length=10, choices=ROL_CHOICES, default="user")
    create_at = models.DateTimeField(auto_now_add=True)

    # OAuth — identificador único de LinkedIn (claim `sub` del OIDC).
    # Permite idempotencia: si un user re-loguea con LinkedIn, lo
    # encontramos por este id en vez de por email (que podría haber
    # cambiado). null para users registrados con password.
    linkedin_user_id = models.CharField(
        max_length=64, unique=True, null=True, blank=True
    )

    # 2FA TOTP — Time-based One-Time Password (RFC 6238).
    #
    # `totp_secret` se guarda al iniciar el setup (POST /2fa/setup/) y
    # queda en DB incluso si el user no termina de activar — eso permite
    # mostrar el mismo QR si vuelve a abrir el modal. Solo se borra en
    # disable().
    #
    # `totp_enabled` queda False hasta que el user verifica con un código
    # del authenticator. Mientras está False, el setup puede regenerar
    # el secret libremente.
    #
    # NOTA: el secret NO está encriptado en reposo — Django no provee
    # encryption at-rest nativo y agregar django-cryptography por una
    # sola columna es overkill ahora. Si la DB se compromete, los
    # secrets se filtran. Para producción crítica, considerar
    # encriptación a nivel de columna o usar un secret manager.
    totp_secret = models.CharField(max_length=64, blank=True, default="")
    totp_enabled = models.BooleanField(default=False)

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
    # Habilidades blandas (liderazgo, comunicación, trabajo en equipo, etc).
    # Texto libre separado por coma, igual contrato que `skills` para que
    # el front pueda hacer split sin lógica especial.
    soft_skills = models.TextField(blank=True, help_text="Habilidades blandas separadas por coma")
    # Idiomas que maneja el user. JSON-as-text: array de
    # `{"language": str, "level": str}`. Igual patrón que experience/education
    # cuando los popula Gemini.
    languages = models.TextField(blank=True, help_text="JSON array de idiomas {language, level}")
    create_at = models.DateTimeField(auto_now_add=True)

    # Preferences ----------------------------------------------------
    # Si el user quiere recibir digest diario de matches >85% por email.
    # Default True — la mayoría de los users esperan esto al registrarse;
    # se puede apagar desde /settings.
    email_alerts_enabled = models.BooleanField(default=True)
    # Visibilidad del perfil para el lado empresa del marketplace.
    # Default True desde 2026-06-27 (era False): el usuario que se
    # registra en una plataforma de empleo claramente QUIERE que las
    # empresas lo encuentren — pedirle que entre a /settings a activarlo
    # generaba una bolsa vacía y feedback de cliente confuso ("¿por qué
    # no me encuentran?"). Si quiere ocultarse, lo apaga manualmente
    # desde Settings → Privacidad.
    visible_to_companies = models.BooleanField(default=True, db_index=True)
    # Anti dedup: cuándo le mandamos el último email de alertas. La tarea
    # diaria solo manda si el último envío fue hace más de 20h (margen
    # contra timing drift entre runs del beat).
    last_alert_sent_at = models.DateTimeField(null=True, blank=True)

    # CV Improve usage ------------------------------------------------
    # Timestamp del primer (y único, para users no-admin) uso del
    # endpoint /cv/improve/. Cada user normal puede regenerar el CV con
    # AI UNA vez en la vida (la operación es cara y la mejora
    # iterativa no aporta valor — el CV original ya lo tiene). Admins
    # bypassean este check para QA / debugging del prompt.
    cv_improved_at = models.DateTimeField(null=True, blank=True)

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


class CompanyProfile(models.Model):
    """Perfil de empresa — análogo a UserProfile pero para cuentas con
    `account_type='company'`.

    Diseño: igual que UserProfile, vivimos en una tabla separada y la
    enlazamos 1:1 con User. Eso evita ensuciar UserProfile con campos
    irrelevantes para profesionales (tax_id, website, etc.) y permite
    queries específicas del lado empresa sin tocar el perfil profesional.

    Privacidad: los campos `responsible_*` son la cara visible que el
    profesional ve cuando una empresa marca interés en él (no exponemos
    el email del User registrante directamente — el `responsible_email`
    puede o no coincidir).
    """

    COMPANY_SIZE_CHOICES = [
        ("1-10", "1-10 empleados"),
        ("11-50", "11-50 empleados"),
        ("51-200", "51-200 empleados"),
        ("201-500", "201-500 empleados"),
        ("501-1000", "501-1000 empleados"),
        ("1000+", "Más de 1000 empleados"),
    ]

    user = models.OneToOneField(
        "users.User",
        on_delete=models.PROTECT,
        related_name="company_profile",
    )

    # ─── Datos comerciales ────────────────────────────────────────────
    legal_name = models.CharField(
        max_length=120,
        help_text="Nombre comercial o razón social.",
    )
    # País + ciudad (separados; queremos filtrar por país en el feed).
    country = models.CharField(max_length=60, blank=True)
    city = models.CharField(max_length=100, blank=True)
    industry = models.CharField(
        max_length=80,
        blank=True,
        help_text="Sector económico (Tech, Salud, Finanzas, etc.).",
    )
    website = models.URLField(blank=True)
    size = models.CharField(
        max_length=10, choices=COMPANY_SIZE_CHOICES, blank=True
    )
    short_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Pitch breve (140-200 chars) que ve el profesional.",
    )
    logo = models.ImageField(
        upload_to="company_logos/",
        null=True,
        blank=True,
        validators=[validate_uploaded_image],
    )

    # ─── Responsable principal ───────────────────────────────────────
    # La persona de contacto dentro de la empresa que firma el registro.
    # Se le muestra al profesional cuando recibe "interés" (próxima fase).
    responsible_name = models.CharField(max_length=100)
    responsible_role = models.CharField(
        max_length=80,
        help_text="Cargo (CEO, HR Lead, CTO, Recruiter, etc.).",
    )
    responsible_email = models.EmailField(
        help_text=(
            "Email del responsable. Puede coincidir con el email del User "
            "registrante o ser distinto (ej. recruiting@empresa.com)."
        )
    )

    create_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            # Filtros del search del lado profesional cuando reciba
            # "empresas interesadas" agrupadas por industria/país.
            models.Index(fields=["country", "industry"]),
        ]

    def __str__(self) -> str:
        return f"Empresa: {self.legal_name}"


class CompanyInterest(models.Model):
    """Una empresa marcó interés en un profesional desde su feed.

    Lo persistimos para:
      - Dedup: una empresa no puede mandar 50 notificaciones al mismo
        profesional spammeando el botón.
      - Vista del profesional (Fase 4 — inbox "empresas interesadas").
      - Métricas downstream — qué empresas marcan a quién.

    Privacidad: NO copiamos email/teléfono del profesional acá. El
    contacto efectivo sigue siendo el inbox: el profesional decide
    si responder (revelando contacto) o ignorar.

    Status:
      - `pending` : la empresa marcó, el profesional aún no decidió.
      - `accepted`: el profesional respondió positivo (Fase 4).
      - `dismissed`: el profesional ignoró (Fase 4).
    """

    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_DISMISSED = "dismissed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pendiente"),
        (STATUS_ACCEPTED, "Aceptado"),
        (STATUS_DISMISSED, "Descartado"),
    ]

    company = models.ForeignKey(
        CompanyProfile,
        on_delete=models.CASCADE,
        related_name="interests",
    )
    professional = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="received_interests",
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    # Mensaje opcional que la empresa puede agregar al marcar interés
    # ("Buscamos alguien con tu perfil para X equipo, te interesaría
    # charlar?"). Recortado por seguridad.
    message = models.CharField(max_length=400, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Una empresa solo puede tener UN interés activo por profesional
        # — re-marcar update el row existente, no crea nuevo.
        constraints = [
            models.UniqueConstraint(
                fields=["company", "professional"],
                name="unique_company_professional_interest",
            ),
        ]
        ordering = ["-created_at"]
        indexes = [
            # Listado "empresas interesadas en mí" del profesional.
            models.Index(fields=["professional", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.company.legal_name} → {self.professional.user.username} ({self.status})"
