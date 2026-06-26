"""Serializers de SystemSetting.

Dos serializers porque hay dos audiencias:
- `PublicFeatureFlagsSerializer`: forma plana {key: bool} para el frontend
  de usuario regular. Se sirve sin auth para que el bootstrap del SPA lo
  pueda leer sin esperar al login.
- `AdminSystemSettingSerializer`: full payload (key, value, description,
  updated_at) para la UI admin que necesita ver/editar.
"""

from __future__ import annotations

from rest_framework import serializers

from system_settings.models import SystemSetting


class AdminSystemSettingSerializer(serializers.ModelSerializer):
    """Serializer admin: expone todo. PATCH permite mover value_bool y
    description. `key` es read-only — los flags son creados via data
    migration, no via API (evita typos que dejen flags inalcanzables)."""

    class Meta:
        model = SystemSetting
        fields = ["id", "key", "value_bool", "description", "updated_at"]
        read_only_fields = ["id", "key", "updated_at"]
