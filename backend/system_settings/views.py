"""Views de feature flags / system settings.

Dos endpoints:
- `GET /api/system/feature-flags/` — público sin auth. Devuelve un dict
  {key: bool} con TODOS los flags conocidos. El SPA lo lee al bootstrap
  para decidir qué UI exponer.
- `GET/PATCH /api/system/admin/feature-flags/` — restringido a is_staff.
  Lista y actualiza los flags. `key` no se puede crear ni renombrar via
  API (eso vive en data migrations) — para evitar typos que dejen flags
  inalcanzables.
"""

from __future__ import annotations

from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from system_settings.models import SystemSetting
from system_settings.serializers import AdminSystemSettingSerializer


class PublicFeatureFlagsView(APIView):
    """Endpoint público — sin auth — que devuelve `{key: bool}` para todos
    los flags. El frontend lo cachea localmente y lo lee al bootstrap del
    SPA. Sin auth porque el shell del SPA carga antes del login (la
    pantalla de login en sí podría usar un flag).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        flags = dict(SystemSetting.objects.values_list("key", "value_bool"))
        return Response(flags)


class AdminSystemSettingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """ViewSet admin (is_staff) para listar y togglear flags. NO permite
    crear ni borrar — los flags se crean en data migrations para que el
    código que los consume siempre sepa que existen."""

    queryset = SystemSetting.objects.all()
    serializer_class = AdminSystemSettingSerializer
    permission_classes = [IsAdminUser]
    lookup_field = "key"
