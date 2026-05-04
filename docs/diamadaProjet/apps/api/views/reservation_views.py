from rest_framework import viewsets
from apps.reservations.models import Reservation, Embarquement
from apps.api.serializers import (
    ReservationSerializer, EmbarquementSerializer
)

class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer


class EmbarquementViewSet(viewsets.ModelViewSet):
    queryset = Embarquement.objects.all()
    serializer_class = EmbarquementSerializer