from django.conf import settings
from django.db import models


class JobOffer(models.Model):
    PORTAL_CHOICES = [
        ("computrabajo", "Computrabajo"),
        ("weworkremotely", "We Work Remotely"),
        ("elempleo", "Elempleo"),
        ("infojobs", "InfoJobs"),
        ("magneto", "Magneto"),
        ("bumeran", "Bumeran"),
        ("indeed", "Indeed"),
        ("linkedin", "LinkedIn"),
        ("trabajos_co", "Trabajos Colombia"),
        ("hireline", "Hireline"),
        ("trabajando", "Trabajando.com"),
        ("other", "Otro"),
    ]

    # Modalidad de trabajo — extraída heurísticamente de location + summary
    # al persistir (ver jobs.utils.offer_attributes.extract_modality).
    # 'unknown' default para no esconder ofertas cuando el scraper no
    # logró detectar; los filtros del dashboard la incluyen por opt-in.
    MODALITY_CHOICES = [
        ("remote", "Remoto"),
        ("hybrid", "Híbrido"),
        ("onsite", "Presencial"),
        ("unknown", "Sin especificar"),
    ]

    title = models.CharField(max_length=500)
    company = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    summary = models.TextField()
    # Las URLs de Computrabajo (y otros portales) suelen pasarse de 200.
    url = models.URLField(max_length=500, unique=True)
    keywords = models.TextField(help_text="Palabras clave extraídas de los requisitos")
    portal = models.CharField(
        max_length=32,
        choices=PORTAL_CHOICES,
        default="computrabajo",
        db_index=True,
        help_text="Portal de origen de la oferta",
    )
    # País ISO 3166-1 alpha-2 derivado de `location`. 'XX' = no se pudo
    # detectar. Indexed: el filtro del dashboard hace queries por este
    # campo en cada list de ofertas.
    country = models.CharField(
        max_length=2,
        default="XX",
        db_index=True,
        help_text="Código ISO 3166-1 alpha-2. 'XX' = desconocido",
    )
    modality = models.CharField(
        max_length=10,
        choices=MODALITY_CHOICES,
        default="unknown",
        db_index=True,
        help_text="Modalidad de trabajo detectada heurísticamente",
    )
    # Categoría profesional macro de la oferta, calculada al guardar via
    # `users.services.profession_classifier.infer_profession_category`
    # sobre `title + summary`. CRITICO para evitar mezclar ofertas entre
    # verticales: un abogado nunca debe ver ofertas de diseño web; un
    # zootecnista nunca debe ver Senior React Native Developer. El feed
    # filtra por `category == user_category OR category == 'general'`.
    # 'general' funciona como comodín — ofertas no clasificables las
    # ven todos los users (mejor mostrar que ocultar de más).
    # Indexed porque casi todas las queries del feed filtran por este
    # campo. Valores válidos: los keys de `infer_profession_category`
    # (tech / design / marketing / sales / finance / hr / operations /
    # agro / health / education / legal / admin / trades / general).
    category = models.CharField(
        max_length=20,
        default="general",
        db_index=True,
        help_text="Categoría profesional macro inferida del título+summary",
    )
    # Disponibilidad — false cuando detectamos que la oferta ya no está en
    # el portal de origen (vía sync por sitemap, probe HTTP, etc). El feed
    # filtra is_active=True por default — "cero ruido". Indexed porque
    # casi todas las queries del frontend lo usan como filtro.
    is_active = models.BooleanField(default=True, db_index=True)
    # Cuándo se verificó por última vez la disponibilidad. Sirve para
    # priorizar el probe diario (chequear primero las que llevan más
    # tiempo sin verificar).
    last_checked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class IgnoredOffer(models.Model):
    """Marca per-user de una oferta que el usuario decidió ocultar del feed.

    CASCADE en `offer`: cuando el cron `clean_old_offers` purga ofertas
    >30 días, los registros de ignore mueren con ellas — no hay que
    mantener un cleanup paralelo. Mismo razonamiento para `user`.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ignored_offers",
    )
    offer = models.ForeignKey(
        JobOffer,
        on_delete=models.CASCADE,
        related_name="ignored_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "offer"], name="unique_ignored_offer_per_user"
            )
        ]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"{self.user_id} ignored {self.offer_id}"
