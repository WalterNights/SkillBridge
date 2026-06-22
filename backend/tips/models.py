from django.db import models


class Tip(models.Model):
    """Tip rotativo del widget "Tip del día" del sidebar.

    Cada tip es una sola frase accionable (~80-160 chars). Los `manual`
    son curados a mano (seed inicial). Los `ai` se generan semanalmente
    via Celery + Gemini para refrescar el pool sin tocar código.
    """

    SOURCE_CHOICES = [
        ("manual", "Manual"),
        ("ai", "AI-generated"),
    ]

    CATEGORY_CHOICES = [
        ("cv", "CV / ATS"),
        ("search", "Búsqueda activa"),
        ("interview", "Entrevistas"),
        ("networking", "Networking / marca personal"),
        ("soft", "Soft skills / negociación"),
        ("tech", "Técnicas industry-specific"),
        ("product", "SkilTak meta-uso"),
        ("wellness", "Diversificación / wellness"),
        ("other", "Otro"),
    ]

    # Profession scope — para filtrar tips por la vertical del usuario.
    # `all` aplica a todos. Las demás son las macro categorías que
    # devuelve `users.services.profession_classifier`.
    PROFESSION_SCOPE_CHOICES = [
        ("all", "Todos"),
        ("tech", "Tech"),
        ("design", "Diseño"),
        ("marketing", "Marketing"),
        ("sales", "Ventas"),
        ("finance", "Finanzas"),
        ("hr", "RRHH"),
        ("operations", "Operaciones"),
        ("health", "Salud"),
        ("education", "Educación"),
        ("legal", "Legal"),
    ]

    text = models.CharField(max_length=300, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")
    profession_scope = models.CharField(
        max_length=20, choices=PROFESSION_SCOPE_CHOICES, default="all", db_index=True
    )
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="manual")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # El endpoint `today/` recorre tips activos — el índice
            # acelera el filtro en una tabla que solo crece (~5/semana).
            models.Index(fields=["is_active", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.category}/{self.source}] {self.text[:60]}…"
