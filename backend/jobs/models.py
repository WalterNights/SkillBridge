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
