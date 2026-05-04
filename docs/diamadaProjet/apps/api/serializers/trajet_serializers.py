from rest_framework import serializers
from apps.trajets.models import Trajet, GareRoutiere, Vehicule


class GareSerializer(serializers.ModelSerializer):
    class Meta:
        model = GareRoutiere
        fields = '__all__'


class VehiculeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicule
        fields = '__all__'


class TrajetSerializer(serializers.ModelSerializer):
    gare_depart = GareSerializer(read_only=True)
    gare_arrivee = GareSerializer(read_only=True)
    vehicule = VehiculeSerializer(read_only=True)

    class Meta:
        model = Trajet
        fields = '__all__'