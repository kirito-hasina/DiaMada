from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.reservations.models import Reservation, Embarquement
from rest_framework.permissions import IsAuthenticated
from apps.api.serializers import (
    ReservationReadSerializer, ReservationWriteSerializer,
    ReservationSerializer, EmbarquementSerializer,
)


class ReservationViewSet(viewsets.ModelViewSet):
    """
    GET  /reservations/           → mes réservations (passager) ou toutes (admin)
    POST /reservations/           → créer une réservation
    GET  /reservations/{id}/      → détail
    PATCH /reservations/{id}/     → modifier (limité)
    POST /reservations/{id}/annuler/ → annuler une réservation
    """
    queryset = Reservation.objects.all()
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        write_serializer = ReservationWriteSerializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        self.perform_create(write_serializer)
        
        # Retourner la réponse avec le ReadSerializer
        read_serializer = ReservationReadSerializer(
            write_serializer.instance,
            context={'request': request}
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Reservation.objects.none()

        qs = Reservation.objects.select_related(
            'passager__user', 'trajet__gare_depart',
            'trajet__gare_arrivee', 'agent__user'
        )

        if user.role == 'admin':
            return qs.all().order_by('-date_reservation')

        if user.role == 'passager':
            # Un passager voit uniquement ses propres réservations
            return qs.filter(
                passager__user=user
            ).order_by('-date_reservation')

        if user.role == 'agent':
            # Un agent voit les réservations de son trajet du jour
            return qs.filter(
                trajet__statut='planifie'
            ).order_by('-date_reservation')

        return Reservation.objects.none()

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return ReservationReadSerializer
        return ReservationWriteSerializer

    def perform_create(self, serializer):
        user = self.request.user
        # Lier automatiquement le passager connecté
        try:
            passager = user.passager
        except AttributeError:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                "Seul un passager peut créer une réservation."
            )
        serializer.save(passager=passager)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        # Empêcher la modification si déjà embarquée ou annulée
        if instance.statut in ('embarquee', 'annulee'):
            return Response(
                {'error': f"Impossible de modifier une réservation '{instance.statut}'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='annuler')
    def annuler(self, request, pk=None):
        """POST /reservations/{id}/annuler/"""
        reservation = self.get_object()

        if reservation.statut in ('annulee', 'embarquee'):
            return Response(
                {'error': f"Impossible d'annuler une réservation '{reservation.statut}'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Restituer les places au trajet
        trajet = reservation.trajet
        trajet.places_disponibles = min(
            trajet.places_disponibles + reservation.nb_places,
            trajet.places_totales
        )
        trajet.save()

        reservation.statut = 'annulee'
        reservation.save()

        return Response(
            {'message': 'Réservation annulée. Les places ont été restituées.'},
            status=status.HTTP_200_OK
        )


class EmbarquementViewSet(viewsets.ModelViewSet):
    """
    GET  /embarquement/      → liste des embarquements (agent/admin)
    POST /embarquement/      → enregistrer un embarquement
    """
    serializer_class = EmbarquementSerializer
    queryset = Embarquement.objects.all()

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Embarquement.objects.none()

        qs = Embarquement.objects.select_related(
            'reservation__passager__user',
            'reservation__trajet__gare_depart',
            'reservation__trajet__gare_arrivee',
            'agent__user',
        )

        if user.role == 'admin':
            return qs.all().order_by('-heure_scan')

        if user.role == 'agent':
            # L'agent voit les embarquements qu'il a validés
            return qs.filter(agent__user=user).order_by('-heure_scan')

        return Embarquement.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        try:
            agent = user.agent
        except AttributeError:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Seul un agent peut valider un embarquement.")
        serializer.save(agent=agent)