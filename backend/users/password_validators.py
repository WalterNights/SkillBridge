"""Validadores de contraseña propios.

La traducción al español de Django no cubre el mensaje de largo mínimo
(sale "This password is too short…" aunque se active "es"), y ese es el
error más común. Este validador lo reemplaza con el mismo comportamiento.
"""

from django.contrib.auth.password_validation import MinimumLengthValidator
from django.core.exceptions import ValidationError


class SpanishMinimumLengthValidator(MinimumLengthValidator):
    """`MinimumLengthValidator` con mensajes en español."""

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                f"La contraseña es muy corta: debe tener al menos {self.min_length} caracteres.",
                code="password_too_short",
                params={"min_length": self.min_length},
            )

    def get_help_text(self):
        return f"Tu contraseña debe tener al menos {self.min_length} caracteres."
