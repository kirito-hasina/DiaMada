from datetime import date
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny, IsAdminUser
from apps.trajets.models import Trajet, GareRoutiere, Vehicule
from apps.api.serializers import (
    TrajetReadSerializer, TrajetWriteSerializer,
    TrajetSerializer, GareSerializer, VehiculeSerializer,
)


class TrajetViewSet(viewsets.ModelViewSet):
    """
    GET  /trajets/          → liste des trajets planifiés à venir (public)
    GET  /trajets/{id}/     → détail d'un trajet (public)
    POST /trajets/          → créer un trajet (admin uniquement — via permissions)
    PATCH/PUT /trajets/{id}/→ modifier (admin)
    DELETE /trajets/{id}/  → annuler logiquement (admin)
    """
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields   = ['gare_depart__ville', 'gare_arrivee__ville']
    ordering_fields = ['date_depart', 'heure_depart', 'prix', 'places_disponibles']
    ordering        = ['date_depart', 'heure_depart']

    def get_permissions(self):
        # Lecture publique, écriture admin seulement
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsAdminUser()]

    def get_queryset(self):
        user = self.request.user

        # Admin : voit tous les trajets
        if user.is_authenticated and user.role == 'admin':
            qs = Trajet.objects.select_related(
                'gare_depart', 'gare_arrivee', 'vehicule', 'chauffeur__user'
            ).all()
        else:
            # Public / passager : uniquement les trajets planifiés à venir
            qs = Trajet.objects.select_related(
                'gare_depart', 'gare_arrivee', 'vehicule', 'chauffeur__user'
            ).filter(
                statut='planifie',
                date_depart__gte=date.today(),
                places_disponibles__gt=0,
            )

        # Filtres optionnels via query params
        # ex: /trajets/?depart=Antananarivo&arrivee=Toamasina&date=2026-05-01
        depart  = self.request.query_params.get('depart')
        arrivee = self.request.query_params.get('arrivee')
        d       = self.request.query_params.get('date')

        if depart:
            qs = qs.filter(gare_depart__ville__icontains=depart)
        if arrivee:
            qs = qs.filter(gare_arrivee__ville__icontains=arrivee)
        if d:
            qs = qs.filter(date_depart=d)

        return qs

    def get_serializer_class(self):
        # Lecture → serializer avec données nested lisibles
        if self.action in ('list', 'retrieve'):
            return TrajetReadSerializer
        # Écriture → serializer avec IDs
        return TrajetWriteSerializer

    def destroy(self, request, *args, **kwargs):
        # Annulation logique au lieu de suppression physique
        from rest_framework.response import Response
        from rest_framework import status
        instance = self.get_object()
        if instance.statut in ('en_cours', 'termine'):
            return Response(
                {'error': "Impossible d'annuler un trajet en cours ou terminé."},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.statut = 'annule'
        instance.save()
        return Response(
            {'message': 'Trajet annulé avec succès.'},
            status=status.HTTP_200_OK
        )


class GareViewSet(viewsets.ModelViewSet):
    """CRUD gares — public en lecture, admin en écriture."""
    serializer_class = GareSerializer
    queryset = GareRoutiere.objects.all().order_by('ville', 'nom')


class VehiculeViewSet(viewsets.ModelViewSet):
    """CRUD véhicules — admin uniquement."""
    serializer_class = VehiculeSerializer

    def get_queryset(self):
        qs = Vehicule.objects.select_related('chauffeur__user').all()
        # Filtre optionnel par statut : /vehicules/?statut=actif
        statut = self.request.query_params.get('statut')
        if statut:
            qs = qs.filter(statut=statut)
        return qs