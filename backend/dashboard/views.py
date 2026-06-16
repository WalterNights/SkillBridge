from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import UserProfile
from users.serializers import UserProfileSerializer


class dashboardUserList(ListAPIView):
    """Listado paginado de perfiles.

    TODO: revisar modelo de acceso — actualmente cualquier usuario autenticado
    ve TODOS los perfiles (potencial leak de PII). Decidir si:
      - Restringir a IsAdminUser
      - Filtrar por owner (cada usuario ve sólo el propio)
      - Filtrar por rol de reclutador (caso de uso de matching inverso)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all().order_by('-id')


class dashboardUserData(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

