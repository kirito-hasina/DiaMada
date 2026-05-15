from rest_framework import serializers
from django.db import transaction
from apps.reservations.models import Reservation, Embarquement
from apps.core.algorithms import choisir_trajet_optimal
from apps.trajets.models import Trajet


class ReservationReadSerializer(serializers.ModelSerializer):
    passager_nom  = serializers.SerializerMethodField()
    trajet_detail = serializers.SerializerMethodField()

    class Meta:
        model  = Reservation
        fields = [
            'id', 'code_billet', 'passager_nom', 'trajet_detail',
            'nb_places', 'prix_total', 'canal', 'statut', 'date_reservation',
        ]

    def get_passager_nom(self, obj):
        if not obj.passager:
            return None
        u = obj.passager.user
        return f"{u.prenom} {u.nom}".strip()

    def get_trajet_detail(self, obj):
        if not obj.trajet:
            return None

        t = obj.trajet
        return {
            'id': t.id,
            'depart': t.gare_depart.ville,
            'arrivee': t.gare_arrivee.ville,
            'date': t.date_depart,
            'heure': t.heure_depart,
            'prix': t.prix,
        }
    
    def validate_canal(self, value):
        if value not in ['web', 'guichet']:
            raise serializers.ValidationError("Canal invalide.")
        return value


class ReservationWriteSerializer(serializers.ModelSerializer):
    """
    MODE 1 — trajet fourni directement (champ 'trajet')
    MODE 2 — algorithme glouton (gare_depart_id + gare_arrivee_id + date_depart)
    """
    gare_depart_id  = serializers.IntegerField(required=False, write_only=True)
    gare_arrivee_id = serializers.IntegerField(required=False, write_only=True)
    date_depart     = serializers.DateField(required=False, write_only=True)

    class Meta:
        model  = Reservation
        fields = [
            'id', 'trajet', 'nb_places', 'canal', 'agent',
            'gare_depart_id', 'gare_arrivee_id', 'date_depart',
        ]
        read_only_fields = ['id']
        extra_kwargs = {'trajet': {'required': False}}

    def validate_nb_places(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Le nombre de places doit être supérieur à 0."
            )
        if value > 10:
            raise serializers.ValidationError(
                "Impossible de réserver plus de 10 places à la fois."
            )
        return value

    def validate(self, data):
        trajet    = data.get('trajet')
        nb_places = data.get('nb_places', 1)

        # ── MODE 2 : algorithme glouton ──────────────────────────
        if trajet is None:
            gare_depart_id  = data.pop('gare_depart_id', None)
            gare_arrivee_id = data.pop('gare_arrivee_id', None)
            date_dep        = data.pop('date_depart', None)

            if not all([gare_depart_id, gare_arrivee_id, date_dep]):
                raise serializers.ValidationError(
                    "Fournir soit 'trajet', soit "
                    "'gare_depart_id' + 'gare_arrivee_id' + 'date_depart'."
                )

            trajet_optimal = choisir_trajet_optimal(
                gare_depart_id  = gare_depart_id,
                gare_arrivee_id = gare_arrivee_id,
                date_depart     = date_dep,
                nb_places       = nb_places,
            )

            if trajet_optimal is None:
                raise serializers.ValidationError(
                    "Aucun trajet disponible pour cet itinéraire "
                    "avec le nombre de places demandé."
                )

            data['trajet'] = trajet_optimal
            return data

        # ── MODE 1 : trajet choisi explicitement ──────────────────
        data.pop('gare_depart_id', None)
        data.pop('gare_arrivee_id', None)
        data.pop('date_depart', None)

        if trajet.statut != 'planifie':
            raise serializers.ValidationError({
                'trajet': f"Ce trajet n'est plus disponible (statut : {trajet.statut})."
            })

        if trajet.places_disponibles < nb_places:
            raise serializers.ValidationError({
                'nb_places': f"Pas assez de places disponibles "
                             f"(disponibles : {trajet.places_disponibles})."
            })

        return data

    def create(self, validated_data):
        nb_places = validated_data['nb_places']
        trajet_id = validated_data['trajet'].id

        # ── select_for_update → évite la race condition ──────────
        # Deux réservations simultanées ne peuvent plus dépasser
        # la capacité du véhicule
        with transaction.atomic():
            trajet = Trajet.objects.select_for_update().get(id=trajet_id)

            # Re-vérifier les places dans le verrou
            if trajet.places_disponibles < nb_places:
                raise serializers.ValidationError(
                    f"Plus assez de places disponibles "
                    f"(disponibles : {trajet.places_disponibles})."
                )

            prix_total = trajet.prix * nb_places
            trajet.places_disponibles -= nb_places
            trajet.save()

            validated_data['trajet'] = trajet
            return Reservation.objects.create(
                prix_total = prix_total,
                statut     = 'confirmee',
                **validated_data
            )


class EmbarquementSerializer(serializers.ModelSerializer):

    class Meta:
        model  = Embarquement
        fields = '__all__'
        read_only_fields = ['heure_scan', 'statut']

    def validate(self, data):
        reservation = data.get('reservation')

        if reservation is None:
            raise serializers.ValidationError(
                {'reservation': "La réservation est obligatoire."}
            )

        if reservation.statut != 'confirmee':
            raise serializers.ValidationError({
                'reservation': f"Impossible d'embarquer — statut : {reservation.statut}."
            })

        if Embarquement.objects.filter(reservation=reservation).exists():
            raise serializers.ValidationError(
                {'reservation': "Ce passager est déjà embarqué."}
            )

        return data

    def create(self, validated_data):
        with transaction.atomic():
            reservation = Reservation.objects.select_for_update().get(
                id=validated_data['reservation'].id
            )

            if reservation.statut != 'confirmee':
                raise serializers.ValidationError(
                    {'reservation': "Déjà embarqué ou invalide."}
                )

            reservation.statut = 'embarquee'
            reservation.save()

            validated_data['reservation'] = reservation
            return Embarquement.objects.create(**validated_data)


ReservationSerializer = ReservationWriteSerializer