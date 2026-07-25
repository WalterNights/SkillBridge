from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from applications.models import JobApplication
from jobs.models import IgnoredOffer, JobOffer
from users.models import UserProfile
from users.serializers import UserProfileSerializer

User = get_user_model()


class dashboardUserList(ListAPIView):
    """Listado paginado de perfiles para el panel admin.

    SEGURIDAD: `IsAdminUser` (Django `is_staff=True`) — antes era
    `IsAuthenticated` y cualquier user con sesión podía listar TODOS
    los perfiles. PII leak. Ahora solo admins ven la lista.
    """

    permission_classes = [IsAdminUser]
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.select_related("user").order_by("-id")


class dashboardUserData(APIView):
    """Devuelve el perfil del request.user — usado por flows
    autenticados normales (no requiere admin)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserRoleUpdateView(APIView):
    """PATCH /api/dashboard/users/{id}/role/ — promueve o degrada un user.

    Body: {"is_staff": bool, "is_superuser": bool} — ambos opcionales,
    se aplican solo los que vengan en el payload.

    Reglas de seguridad:
      - Solo IsAdminUser puede llamar al endpoint.
      - No puedes degradarte a ti mismo (anti-lockout: si el único
        admin se sacó is_staff por error, nadie puede recuperarlo
        sin SSH al VPS).
      - Solo un superuser puede tocar `is_superuser` (el escalado
        a super requiere ya ser super).
      - 404 si el target user no existe.
    """

    permission_classes = [IsAdminUser]

    def patch(self, request, user_id: int):
        target = get_object_or_404(User, pk=user_id)

        # Anti-self-lockout: el admin no puede sacarse sus propios
        # privilegios. Hay que pedirle a OTRO admin.
        is_self = request.user.id == target.id
        wants_demote_self = is_self and (
            request.data.get("is_staff") is False
            or request.data.get("is_superuser") is False
        )
        if wants_demote_self:
            return Response(
                {
                    "error": "self_demote_forbidden",
                    "detail": (
                        "No puedes degradarte a ti mismo. Pídele a otro admin "
                        "que lo haga."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Solo superusers pueden tocar is_superuser ajeno (defensa
        # contra escalado: un staff común no debería poder hacer
        # super a otro user, ni quitarle super a un super existente).
        if "is_superuser" in request.data and not request.user.is_superuser:
            return Response(
                {
                    "error": "superuser_required",
                    "detail": "Solo un super-admin puede modificar el flag de superuser.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        updates: dict[str, bool] = {}
        if "is_staff" in request.data:
            updates["is_staff"] = bool(request.data["is_staff"])
        if "is_superuser" in request.data:
            updates["is_superuser"] = bool(request.data["is_superuser"])
        if not updates:
            return Response(
                {
                    "error": "no_fields",
                    "detail": "Envía al menos is_staff o is_superuser en el body.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        for field, value in updates.items():
            setattr(target, field, value)
        target.save(update_fields=list(updates.keys()))

        return Response(
            {
                "id": target.id,
                "username": target.username,
                "email": target.email,
                "is_staff": target.is_staff,
                "is_superuser": target.is_superuser,
            }
        )


class AdminUserProfileDetailView(APIView):
    """GET /api/dashboard/users/{user_id}/profile-detail/

    Devuelve el detalle "profesional" de un user para que el admin lo
    inspeccione desde el panel /admin/users sin tener que abrir el
    perfil completo. Foco en lo que el admin necesita para curar /
    dar soporte: skills, idiomas, links — NO experiencia ni educación
    (que son densos en texto y no aportan a la decisión rápida).

    Privacidad: este endpoint es admin-only (IsAdminUser). Incluye
    email del usuario porque el admin lo necesita para contactar /
    revocar acceso; el flow normal de empresa NO recibe email (eso
    está en /api/companies/profiles/{id}/).
    """

    permission_classes = [IsAdminUser]

    def get(self, request, user_id: int):
        user = get_object_or_404(User, pk=user_id)
        profile = UserProfile.objects.filter(user=user).first()

        # Profile inexistente o vacío — devolvemos placeholder para que
        # el frontend no rompa, pero marcamos `has_profile=False`.
        if profile is None:
            return Response(
                {
                    "user_id": user.id,
                    "email": user.email,
                    "has_profile": False,
                    "first_name": "",
                    "last_name": "",
                    "professional_title": "",
                    "city": "",
                    "skills": [],
                    "soft_skills": [],
                    "languages": [],
                    "linkedin_url": None,
                    "portfolio_url": None,
                    "visible_to_companies": False,
                }
            )

        # Skills/soft_skills viven como CSV en TextField. Split + trim.
        skills = [s.strip() for s in (profile.skills or "").split(",") if s.strip()]
        soft_skills = [s.strip() for s in (profile.soft_skills or "").split(",") if s.strip()]

        # Languages es un TextField con JSON adentro (o string libre en
        # perfiles viejos pre-Gemini). Intentamos parsear como JSON; si
        # falla, devolvemos texto crudo para que el frontend lo muestre.
        languages_raw = (profile.languages or "").strip()
        languages: list = []
        if languages_raw:
            import json

            try:
                parsed = json.loads(languages_raw)
                if isinstance(parsed, list):
                    languages = parsed
            except (ValueError, TypeError):
                # Formato legacy — texto libre. Lo devolvemos como single
                # entry para que el frontend muestre algo en vez de [].
                languages = [{"language": languages_raw, "level": ""}]

        return Response(
            {
                "user_id": user.id,
                "email": user.email,
                "has_profile": True,
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "professional_title": profile.professional_title,
                "city": profile.city,
                "skills": skills,
                "soft_skills": soft_skills,
                "languages": languages,
                "linkedin_url": profile.linkedin_url,
                "portfolio_url": profile.portfolio_url,
                "visible_to_companies": profile.visible_to_companies,
            }
        )


class dashboardStats(APIView):
    """Métricas de plataforma para el dashboard admin.

    Todo en queries agregadas — nada de N+1 ni materializar querysets.
    Las métricas se calculan en el momento; sin cache. Si el volumen de
    datos crece (decenas de miles de ofertas) considerar mover a una
    materialized view o cron que escriba un snapshot diario.
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        # Usuarios
        total_users = User.objects.count()
        total_profiles = UserProfile.objects.count()
        # Perfil "completo" = mismo criterio que el JWT login response.
        complete_profiles = UserProfile.objects.exclude(
            first_name=""
        ).exclude(
            last_name=""
        ).exclude(
            city=""
        ).exclude(
            phone=""
        ).exclude(
            professional_title=""
        ).count()

        # Ofertas
        total_offers = JobOffer.objects.count()
        active_offers = JobOffer.objects.filter(is_active=True).count()
        inactive_offers = total_offers - active_offers
        offers_by_portal = list(
            JobOffer.objects.filter(is_active=True)
            .values("portal")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        offers_by_country = list(
            JobOffer.objects.filter(is_active=True)
            .exclude(country="XX")
            .values("country")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # Postulaciones
        total_applications = JobApplication.objects.count()
        applications_by_status = list(
            JobApplication.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        # Tasa de éxito real: applications con outcome positivo
        # (offer recibida) sobre el total de applications confirmadas
        # (cualquier status que no sea pending).
        non_pending = JobApplication.objects.exclude(status="pending").count()
        with_offer = JobApplication.objects.filter(status="offer").count()
        success_rate_pct = (with_offer / non_pending * 100) if non_pending > 0 else 0.0

        # Ignoradas — métrica de cuánto ruido tenemos.
        total_ignored = IgnoredOffer.objects.count()

        return Response(
            {
                "users": {
                    "total": total_users,
                    "with_profile": total_profiles,
                    "complete_profile": complete_profiles,
                },
                "offers": {
                    "total": total_offers,
                    "active": active_offers,
                    "inactive": inactive_offers,
                    "by_portal": offers_by_portal,
                    "by_country": offers_by_country,
                },
                "applications": {
                    "total": total_applications,
                    "by_status": applications_by_status,
                    "success_rate_pct": round(success_rate_pct, 1),
                },
                "ignored": {
                    "total": total_ignored,
                },
            },
            status=status.HTTP_200_OK,
        )


# Ventanas permitidas para el selector 7d/30d/90d del panel /admin/trends.
# Se mantiene consistente con AnalyticsSummary — misma UX de tabs. Cualquier
# valor fuera de este set colapsa al default (30). Blindar contra querys
# arbitrarias evita que un cliente pida "days=99999" y cargue toda la DB.
_TRENDS_ALLOWED_WINDOWS = (7, 30, 90)
_TRENDS_DEFAULT_WINDOW = 30


class dashboardTrends(APIView):
    """Métricas de comportamiento agregadas para /admin/trends.

    Distinto de dashboardStats: acá miramos POR QUE / COMO se comporta el
    user en la plataforma (motivos de ignore, conversión por portal),
    no CUANTO hay (snapshot descriptivo). Alimenta las decisiones de
    matching y prioriza deprecar portales con baja tasa de respuesta.

    Todo con agregaciones ORM sobre la ventana ?days=7|30|90 (clamped).
    Sin cache: si el volumen crece a decenas de miles de eventos por dia
    considerar mover a un snapshot diario en tabla materializada.
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        # Ventana temporal — validada contra el set permitido para no
        # aceptar valores arbitrarios (evita ?days=99999 que cargaria
        # todo el histórico y bloqueria la DB).
        try:
            requested_days = int(request.query_params.get("days", _TRENDS_DEFAULT_WINDOW))
        except (TypeError, ValueError):
            requested_days = _TRENDS_DEFAULT_WINDOW
        window_days = (
            requested_days if requested_days in _TRENDS_ALLOWED_WINDOWS else _TRENDS_DEFAULT_WINDOW
        )
        since = timezone.now() - timedelta(days=window_days)

        # ─────────────────────────────────────────────────────────────
        # 1) Motivos de ignore agregados
        # ─────────────────────────────────────────────────────────────
        ignored_qs = IgnoredOffer.objects.filter(created_at__gte=since)
        total_ignores_window = ignored_qs.count()

        # Distribución global por motivo. Retornamos incluso las que
        # tienen count=0 en el frontend rellenando con el set completo
        # de choices — acá solo emitimos las que aparecieron.
        by_reason = list(
            ignored_qs.values("reason").annotate(count=Count("id")).order_by("-count")
        )

        # Breakdown por vertical + motivo. `offer__category` sigue la FK
        # sin queries extra (Django lo resuelve en una JOIN). Excluimos
        # 'general' para no ensuciar el reporte con ofertas sin vertical
        # detectada — el fix real es en profession_classifier.
        by_category_reason = list(
            ignored_qs.exclude(offer__category="general")
            .values("offer__category", "reason")
            .annotate(count=Count("id"))
            .order_by("offer__category", "-count")
        )

        # ─────────────────────────────────────────────────────────────
        # 2) Funnel de aplicaciones por portal
        # ─────────────────────────────────────────────────────────────
        # Ventana basada en clicked_at (momento del click "Aplicar") —
        # es el evento que "arranca" el funnel. Un user que aplica hoy
        # y consigue entrevista en 45 dias entra en la ventana correcta
        # porque los status posteriores mutan la misma fila (no crean
        # una nueva).
        apps_qs = JobApplication.objects.filter(clicked_at__gte=since)

        portal_status_rows = list(
            apps_qs.values("offer__portal", "status")
            .annotate(count=Count("id"))
            .order_by("offer__portal", "status")
        )

        # Pivotear en Python — evita SQL condicional que difiere entre
        # SQLite (tests) y Postgres (prod). Volumen es chico (portales x
        # status = decenas de filas), no vale la pena optimizar en SQL.
        # Un portal existe en el output solo si tuvo al menos 1 click en
        # la ventana; no forzamos filas vacias.
        portal_map: dict[str, dict] = {}
        for row in portal_status_rows:
            portal = row["offer__portal"] or "unknown"
            bucket = portal_map.setdefault(
                portal,
                {
                    "portal": portal,
                    "clicks": 0,  # total incluye pending
                    "applied": 0,
                    "in_review": 0,
                    "interview": 0,
                    "offer": 0,
                    "rejected": 0,
                    "withdrawn": 0,
                    "conversion_pct": 0.0,
                },
            )
            bucket["clicks"] += row["count"]
            status_key = row["status"]
            if status_key in bucket:
                bucket[status_key] = row["count"]

        # `conversion_pct` = ofertas recibidas / total clicks. Es la
        # metrica que responde "vale la pena este portal?". Redondeamos
        # a 1 decimal para que la UI no tenga que formatear.
        for bucket in portal_map.values():
            clicks = bucket["clicks"] or 1  # evita div/0; muestra 0.0 si no hay
            bucket["conversion_pct"] = round(bucket["offer"] / clicks * 100, 1)

        # Orden por conversion desc — el portal con mejor tasa arriba,
        # que es lo primero que el admin quiere ver. Empates: mas clicks
        # gana (mas señal).
        portal_funnel = sorted(
            portal_map.values(),
            key=lambda b: (b["conversion_pct"], b["clicks"]),
            reverse=True,
        )

        return Response(
            {
                "window_days": window_days,
                "ignore_breakdown": {
                    "total": total_ignores_window,
                    "by_reason": by_reason,
                    "by_category_reason": by_category_reason,
                },
                "portal_funnel": portal_funnel,
            },
            status=status.HTTP_200_OK,
        )
