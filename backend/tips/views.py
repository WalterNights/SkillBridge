from datetime import date

from django.db.models import Q
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from tips.models import Tip
from tips.serializers import TipSerializer


class TipOfTheDayView(APIView):
    """GET /api/tips/today/[?profession=tech] → devuelve el tip de hoy.

    Filtrado opcional por `profession_scope`: el cliente puede pasar
    `?profession=design` (etc.) para recibir solo tips relevantes a
    esa vertical PLUS los universales (`scope='all'`). Sin el query
    param, devuelve solo los universales — comportamiento seguro
    para usuarios sin perfil completado.

    Determinístico por fecha UTC: `index = days_since_epoch % count`.
    Mismo tip todo el día → fácil de cachear cliente-side. El conteo
    es contra el subconjunto filtrado, así que un user de marketing
    siempre ve tips de marketing+universales, no se cruzan.

    Sin auth (AllowAny) — el contenido no es sensible y queremos que
    el widget funcione aunque la sesión expire. Frontend cae al array
    static si la red falla — defensa en profundidad.
    """

    permission_classes = [AllowAny]

    _VALID_SCOPES = {scope for scope, _ in Tip.PROFESSION_SCOPE_CHOICES}

    _FALLBACK_TEXT = (
        "Personalizá el resumen del CV para cada match. "
        "La IA detecta keywords del job post."
    )

    def get(self, request):
        profession = (request.query_params.get("profession") or "").strip().lower()

        qs = Tip.objects.filter(is_active=True)
        if profession and profession in self._VALID_SCOPES and profession != "all":
            # Vertical-aware: tips de la vertical específica + los universales.
            qs = qs.filter(Q(profession_scope="all") | Q(profession_scope=profession))
        else:
            # Sin profession o profession inválida: solo universales.
            qs = qs.filter(profession_scope="all")

        qs = qs.order_by("id")
        total = qs.count()
        if total == 0:
            return Response(
                {
                    "id": 0,
                    "text": self._FALLBACK_TEXT,
                    "category": "cv",
                    "source": "manual",
                }
            )
        # `toordinal()` da días desde year 1. Mod sobre el subconjunto
        # filtrado: cada vertical tiene su propia rotación independiente.
        index = date.today().toordinal() % total
        tip = qs[index]
        return Response(TipSerializer(tip).data)
