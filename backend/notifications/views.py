from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notifications.models import Notification
from notifications.serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de notificaciones del usuario autenticado.

    Endpoints:
      - GET  /api/notifications/            → lista del usuario
                                              (filter opcional ?status=unread|read|saved)
      - POST /api/notifications/{id}/mark-read/     → marca como leída
      - POST /api/notifications/{id}/toggle-save/   → toggle guardada
      - POST /api/notifications/mark-all-read/      → marca todas como leídas

    SEGURIDAD: el queryset siempre se filtra por `request.user` — un
    usuario NUNCA puede leer o mutar notificaciones de otro, ni siquiera
    con el id correcto (404 antes que 403 para no leak).
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    # El drawer del frontend pide la lista completa de cada tab y filtra
    # client-side. Pagination default de DRF aplica solo si crece mucho.
    pagination_class = None

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        tab = self.request.query_params.get("status")
        if tab == "unread":
            qs = qs.filter(is_read=False)
        elif tab == "read":
            qs = qs.filter(is_read=True)
        elif tab == "saved":
            qs = qs.filter(is_saved=True)
        return qs

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)

    @action(detail=True, methods=["post"], url_path="toggle-save")
    def toggle_save(self, request, pk=None):
        notification = self.get_object()
        notification.is_saved = not notification.is_saved
        notification.save(update_fields=["is_saved"])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        updated = Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True
        )
        return Response({"updated": updated}, status=status.HTTP_200_OK)
