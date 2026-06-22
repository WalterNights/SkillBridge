from datetime import date

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from tips.models import Tip
from tips.serializers import TipSerializer


class TipOfTheDayView(APIView):
    """GET /api/tips/today/ → devuelve un tip rotativo, mismo todo el día.

    Determinístico por fecha UTC: `index = days_since_epoch % count`.
    El mismo día, todos los usuarios ven el mismo tip — eso simplifica
    el caching del cliente y elimina la necesidad de auth para esta
    cosita inofensiva.

    Sin auth (AllowAny) porque el contenido no es sensible y queremos
    que el widget renderee aunque la sesión expire. El frontend cae al
    array static si la red falla — defensa en profundidad.

    Si la tabla queda vacía (ej. tests con un schema migrado pero sin
    seed corrido), devuelve un placeholder en vez de 404 — el widget
    nunca debería romper la página.
    """

    permission_classes = [AllowAny]

    _FALLBACK_TEXT = (
        "Personalizá el resumen del CV para cada match. "
        "La IA detecta keywords del job post."
    )

    def get(self, request):
        qs = Tip.objects.filter(is_active=True).order_by("id")
        total = qs.count()
        if total == 0:
            return Response(
                {"id": 0, "text": self._FALLBACK_TEXT, "category": "cv", "source": "manual"}
            )
        # `toordinal()` da el número de días desde el year 1. Mod del
        # total da un índice estable durante el día completo.
        index = date.today().toordinal() % total
        # `[index]` requiere QS ordenado y sin huecos, que ya tenemos via
        # order_by("id"). Hacerlo con `.values_list` evita un .get().
        tip = qs[index]
        return Response(TipSerializer(tip).data)
