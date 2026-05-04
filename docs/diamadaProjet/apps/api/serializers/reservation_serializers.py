from rest_framework import serializers
from apps.reservations.models import Reservation, Embarquement


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = '__all__'


class EmbarquementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Embarquement
        fields = '__all__'