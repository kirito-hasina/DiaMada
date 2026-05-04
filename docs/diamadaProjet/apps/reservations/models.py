from django.db import models
from apps.users.models import Passager, Agent
from apps.trajets.models import Trajet
# Create your models here.

class Reservation(models.Model):
    code_billet = models.CharField(max_length=20, unique=True)

    passager = models.ForeignKey(Passager, on_delete=models.CASCADE)
    trajet = models.ForeignKey(Trajet, on_delete=models.CASCADE)
    agent = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True)

    nb_places = models.IntegerField(default=1)
    prix_total = models.DecimalField(max_digits=10, decimal_places=2)

    CANAL_CHOICES = (
        ('web', 'Web'),
        ('guichet', 'Guichet'),
    )

    canal = models.CharField(max_length=20, choices=CANAL_CHOICES, default='web')

    STATUT_CHOICES = (
        ('en_attente', 'En attente'),
        ('confirmee', 'Confirmée'),
        ('annulee', 'Annulée'),
        ('embarquee', 'Embarquée'),
    )

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')

    date_reservation = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reservation"

class Embarquement(models.Model):
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)

    heure_scan = models.DateTimeField(auto_now_add=True)

    STATUT_CHOICES = (
        ('valide', 'Valide'),
        ('invalide', 'Invalide'),
    )

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='valide')

    class Meta:
        db_table = "embarquement"