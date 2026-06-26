"""Feature flags / settings runtime-toggleables por admin.

Pensado para flags binarias chiquitas que el admin necesita prender/apagar
sin tocar código ni deployar (ej. mostrar al usuario un checkbox de debug
en el feed). Si en algún momento necesitamos settings con valores
arbitrarios (string, int, JSON), agregamos columnas extra o un campo
`value` polimórfico — por ahora solo bool.

Los flags vivos los siembra una data migration al crear la tabla — así
el endpoint público nunca devuelve un dict vacío sin que falte agregar
filas en producción a mano.
"""

from __future__ import annotations

from django.db import models


class SystemSetting(models.Model):
    """Flag boolean runtime-toggleable por un admin.

    `key` es el identificador estable que consume el frontend (snake_case,
    inmutable). `description` es para que el admin entienda qué controla
    el flag sin tener que leer código.
    """

    key = models.CharField(
        max_length=64,
        unique=True,
        help_text="Identificador estable consumido por el frontend (snake_case).",
    )
    value_bool = models.BooleanField(default=False)
    description = models.TextField(
        blank=True,
        help_text="Qué hace este flag. Visible para el admin en la UI.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        state = "ON" if self.value_bool else "off"
        return f"{self.key} = {state}"
