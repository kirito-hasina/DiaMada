from django.db import models
from apps.users.models import Chauffeur
# Create your models here.

class GareRoutiere(models.Model):
    nom = models.CharField(max_length=150)
    ville = models.CharField(max_length=100)
    adresse = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "gare_routiere"


class Vehicule(models.Model):
    immatriculation = models.CharField(max_length=20, unique=True)
    capacite = models.IntegerField()
    type_vehicule = models.CharField(max_length=50, default='taxi-brousse')

    chauffeur = models.ForeignKey(Chauffeur, on_delete=models.SET_NULL, null=True)

    STATUT_CHOICES = (
        ('actif', 'Actif'),
        ('en_maintenance', 'Maintenance'),
        ('inactif', 'Inactif'),
    )

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='actif')

    class Meta:
        db_table = "vehicule"

class Trajet(models.Model):
    gare_depart = models.ForeignKey(GareRoutiere, on_delete=models.CASCADE, related_name='depart')
    gare_arrivee = models.ForeignKey(GareRoutiere, on_delete=models.CASCADE, related_name='arrivee')

    vehicule = models.ForeignKey(Vehicule, on_delete=models.CASCADE)
    chauffeur = models.ForeignKey(Chauffeur, on_delete=models.SET_NULL, null=True)

    date_depart = models.DateField()
    heure_depart = models.TimeField()
    heure_arrivee_est = models.TimeField(null=True, blank=True)

    prix = models.DecimalField(max_digits=10, decimal_places=2)

    places_totales = models.IntegerField()
    places_disponibles = models.IntegerField()

    STATUT_CHOICES = (
        ('planifie', 'Planifié'),
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('annule', 'Annulé'),
    )

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='planifie')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "trajet"