from django.db import models


class JobOffer(models.Model):
    title = models.CharField(max_length=500)
    company = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    summary = models.TextField()
    # Las URLs de Computrabajo (y otros portales) suelen pasarse de 200.
    url = models.URLField(max_length=500, unique=True)
    keywords = models.TextField(help_text="Palabras clave extraídas de los requisitos")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
