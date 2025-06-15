from django.db import models


class JobOffer(models.Model):
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    summary = models.TextField()
    url = models.URLField(unique=True)
    keywords = models.TextField(help_text="Palabras clave extraídas de los requisitos")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
