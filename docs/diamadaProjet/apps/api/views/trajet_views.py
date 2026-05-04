from rest_framework import viewsets
from apps.trajets.models import Trajet, GareRoutiere, Vehicule
from apps.api.serializers import (
    TrajetSerializer, GareSerializer, VehiculeSerializer
)

class TrajetViewSet(viewsets.ModelViewSet):
    queryset = Trajet.objects.all()
    serializer_class = TrajetSerializer


class GareViewSet(viewsets.ModelViewSet):
    queryset = GareRoutiere.objects.all()
    serializer_class = GareSerializer


class VehiculeViewSet(viewsets.ModelViewSet):
    queryset = Vehicule.objects.all()
    serializer_class = VehiculeSerializer