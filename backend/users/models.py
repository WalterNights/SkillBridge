from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from datetime import timedelta
import random
import string


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('rol', 'user')

        if not email:
            raise ValueError('El usuario debe tener un correo electrónico')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('rol', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')

        return self.create_user(username, email, password, **extra_fields)
    

class User(AbstractUser):
    ROL_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
    ]
    
    rol = models.CharField(max_length=10, choices=ROL_CHOICES, default='user')
    create_at = models.DateTimeField(auto_now_add=True)
    
    objects = UserManager()

    def __str__(self):
        return f"{self.username}"
    

class UserProfile(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.PROTECT, related_name="profile")
    first_name  = models.CharField(max_length=50)
    last_name  = models.CharField(max_length=50)
    number_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=30)
    city = models.CharField(max_length=100)
    professional_title = models.CharField(max_length=100)
    summary = models.TextField(blank=True)
    education = models.TextField(blank=True)
    skills = models.TextField(help_text="Lista de habilidades separadas por coma")
    experience = models.TextField(help_text="Descripción libre de experiencia")
    resume = models.FileField(upload_to="resumes/", null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)
    portfolio_url = models.URLField(null=True, blank=True)
    create_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Perfil de {self.user.username}"


class PasswordResetToken(models.Model):
    """Modelo para almacenar tokens de restablecimiento de contraseña"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    code = models.CharField(max_length=6)  # Código de 6 dígitos
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Reset token for {self.user.username} - {self.code}"
    
    def is_valid(self):
        """Verifica si el token aún es válido (no expirado y no usado)"""
        from django.conf import settings
        expiration_time = self.created_at + timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT)
        return not self.is_used and timezone.now() < expiration_time
    
    @staticmethod
    def generate_code():
        """Genera un código aleatorio de 6 dígitos"""
        return ''.join(random.choices(string.digits, k=6))