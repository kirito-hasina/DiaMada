from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.users.models import User, Passager, Chauffeur, Agent
from apps.api.serializers import (
    UserSerializer, PassagerSerializer,
    ChauffeurSerializer, AgentSerializer,
)
from apps.api.permissions import IsAdmin, IsSelfOrAdmin


class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD utilisateurs — Admin uniquement.
    GET    /users/       → liste tous les users
    GET    /users/{id}/  → détail
    PATCH  /users/{id}/  → modifier
    DELETE /users/{id}/  → désactiver (soft delete)
    """
    serializer_class   = UserSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        qs = User.objects.all().order_by('id')
        # Filtre optionnel par rôle : /users/?role=passager
        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        # Filtre actif/inactif : /users/?actif=1
        actif = self.request.query_params.get('actif')
        if actif is not None:
            qs = qs.filter(is_active=actif == '1')
        return qs

    def destroy(self, request, *args, **kwargs):
        """Désactivation douce — ne supprime pas physiquement."""
        instance = self.get_object()
        if instance == request.user:
            return Response(
                {'error': "Vous ne pouvez pas désactiver votre propre compte."},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.is_active = False
        instance.save()
        return Response(
            {'message': f"Compte de '{instance.username}' désactivé."},
            status=status.HTTP_200_OK
        )

    def perform_update(self, serializer):
        """Empêcher de changer le rôle via ce endpoint."""
        serializer.save(
            role=self.get_object().role
        )


class PassagerViewSet(viewsets.ModelViewSet):
    """
    GET    /passagers/       → Admin : tous | Passager : son propre profil
    POST   /passagers/       → Admin uniquement
    PATCH  /passagers/{id}/  → Admin ou passager lui-même
    DELETE /passagers/{id}/  → Admin uniquement
    """
    serializer_class   = PassagerSerializer
    permission_classes = [IsAuthenticated]
    permission_classes = [IsSelfOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Passager.objects.select_related('user').all().order_by('user__id')
        return Passager.objects.select_related('user').filter(user=user)

    def create(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response(
                {'error': "Seul un admin peut créer un profil passager directement."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response(
                {'error': "Accès refusé."},
                status=status.HTTP_403_FORBIDDEN
            )
        instance = self.get_object()
        instance.user.is_active = False
        instance.user.save()
        return Response(
            {'message': 'Compte passager désactivé.'},
            status=status.HTTP_200_OK
        )


class ChauffeurViewSet(viewsets.ModelViewSet):
    """
    GET    /chauffeurs/       → Admin : tous | Chauffeur : son propre profil
    POST   /chauffeurs/       → Admin uniquement
    PATCH  /chauffeurs/{id}/  → Admin ou chauffeur lui-même
    DELETE /chauffeurs/{id}/  → Admin uniquement
    """
    serializer_class   = ChauffeurSerializer
    permission_classes = [IsAuthenticated]
    permission_classes = [IsSelfOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Chauffeur.objects.select_related('user').all().order_by('user__id')
        return Chauffeur.objects.select_related('user').filter(user=user)

    def create(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response(
                {'error': "Seul un admin peut créer un profil chauffeur."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response({'error': "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        instance.user.is_active = False
        instance.user.save()
        return Response({'message': 'Compte chauffeur désactivé.'}, status=status.HTTP_200_OK)


class AgentViewSet(viewsets.ModelViewSet):
    """
    GET    /agents/       → Admin : tous | Agent : son propre profil
    POST   /agents/       → Admin uniquement
    PATCH  /agents/{id}/  → Admin ou agent lui-même
    DELETE /agents/{id}/  → Admin uniquement
    """
    serializer_class   = AgentSerializer
    permission_classes = [IsAuthenticated]
    permission_classes = [IsSelfOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Agent.objects.select_related('user', 'gare').all().order_by('user__id')
        return Agent.objects.select_related('user', 'gare').filter(user=user)

    def create(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response(
                {'error': "Seul un admin peut créer un profil agent."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response({'error': "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        instance.user.is_active = False
        instance.user.save()
        return Response({'message': 'Compte agent désactivé.'}, status=status.HTTP_200_OK)