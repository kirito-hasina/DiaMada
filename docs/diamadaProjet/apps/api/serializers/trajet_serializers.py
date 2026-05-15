from rest_framework import serializers
from apps.trajets.models import Trajet, GareRoutiere, Vehicule


# ═══════════════════════════════════════════════
# GARE
# ═══════════════════════════════════════════════
class GareSerializer(serializers.ModelSerializer):
    class Meta:
        model  = GareRoutiere
        fields = '__all__'

    def validate_nom(self, value):
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Le nom de la gare doit contenir au moins 3 caractères.")
        return value.strip()

    def validate_ville(self, value):
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Le nom de la ville est invalide.")
        return value.strip()


# ═══════════════════════════════════════════════
# VEHICULE
# ═══════════════════════════════════════════════
class VehiculeSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Vehicule
        fields = '__all__'

    def validate_capacite(self, value):
        if value <= 0:
            raise serializers.ValidationError("La capacité doit être supérieure à 0.")
        if value > 20:
            raise serializers.ValidationError("Capacité maximale dépassée (20 places).")
        return value

    def validate_immatriculation(self, value):
        qs = Vehicule.objects.filter(immatriculation=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ce numéro d'immatriculation existe déjà.")
        return value.strip().upper()


# ═══════════════════════════════════════════════
# TRAJET — serializer lecture (nested, pour les GET)
# ═══════════════════════════════════════════════
class TrajetReadSerializer(serializers.ModelSerializer):
    """Retourné dans les GET — données lisibles avec noms des gares, véhicule, etc."""
    gare_depart  = GareSerializer(read_only=True)
    gare_arrivee = GareSerializer(read_only=True)
    vehicule     = VehiculeSerializer(read_only=True)
    taux_remplissage = serializers.SerializerMethodField()

    class Meta:
        model  = Trajet
        fields = [
            'id', 'gare_depart', 'gare_arrivee', 'vehicule', 'chauffeur',
            'date_depart', 'heure_depart', 'heure_arrivee_est',
            'prix', 'places_totales', 'places_disponibles',
            'taux_remplissage', 'statut', 'created_at', 'updated_at',
        ]

    def get_taux_remplissage(self, obj):
        if obj.places_totales == 0:
            return 0
        places_prises = obj.places_totales - obj.places_disponibles
        return round((places_prises / obj.places_totales) * 100, 1)


# ═══════════════════════════════════════════════
# TRAJET — serializer écriture (pour les POST/PATCH)
# ═══════════════════════════════════════════════
class TrajetWriteSerializer(serializers.ModelSerializer):
    """Utilisé pour créer/modifier — reçoit des IDs."""

    class Meta:
        model  = Trajet
        fields = [
            'id', 'gare_depart', 'gare_arrivee', 'vehicule', 'chauffeur',
            'date_depart', 'heure_depart', 'heure_arrivee_est',
            'prix', 'places_totales', 'places_disponibles', 'statut',
        ]

    def validate(self, data):
        # Gare départ ≠ gare arrivée
        gare_depart = data.get(
            'gare_depart',
            self.instance.gare_depart if self.instance else None
        )

        gare_arrivee = data.get(
            'gare_arrivee',
            self.instance.gare_arrivee if self.instance else None
        )

        if gare_depart == gare_arrivee:
            raise serializers.ValidationError({
                'gare_arrivee':
                "La gare d'arrivée doit être différente de la gare de départ."
            })

        # Heure arrivée > heure départ
        heure_depart  = data.get('heure_depart')
        heure_arrivee = data.get('heure_arrivee_est')
        if heure_depart and heure_arrivee and heure_arrivee <= heure_depart:
            raise serializers.ValidationError({
                'heure_arrivee_est': "L'heure d'arrivée doit être après l'heure de départ."
            })

        # Places disponibles ≤ places totales
        places_totales     = data.get('places_totales')
        places_disponibles = data.get('places_disponibles')
        if places_totales is not None and places_disponibles is not None:
            if places_disponibles > places_totales:
                raise serializers.ValidationError({
                    'places_disponibles': "Les places disponibles ne peuvent pas dépasser les places totales."
                })
            if places_totales <= 0:
                raise serializers.ValidationError({
                    'places_totales': "Le nombre de places doit être supérieur à 0."
                })

        # Prix > 0
        prix = data.get('prix')
        if prix is not None and prix <= 0:
            raise serializers.ValidationError({
                'prix': "Le prix doit être supérieur à 0."
            })

        # Empêcher modification si trajet en cours ou terminé
        if self.instance and self.instance.statut in ('en_cours', 'termine'):
            raise serializers.ValidationError(
                "Impossible de modifier un trajet en cours ou terminé."
            )

        return data

    def validate_gare_depart(self, value):
        if value is None:
            raise serializers.ValidationError("La gare de départ est obligatoire.")
        return value

    def validate_gare_arrivee(self, value):
        if value is None:
            raise serializers.ValidationError("La gare d'arrivée est obligatoire.")
        return value

    def validate_vehicule(self, value):
        if value is None:
            raise serializers.ValidationError("Le véhicule est obligatoire.")
        if value.statut != 'actif':
            raise serializers.ValidationError("Ce véhicule n'est pas disponible (statut : " + value.statut + ").")
        return value

    # chauffeur est nullable → pas de validate_chauffeur obligatoire


# Alias simple pour les imports existants
TrajetSerializer = TrajetWriteSerializer