from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.


class User(AbstractUser):
    ROLE_CHOICES = (
        ('passager', 'Passager'),
        ('agent', 'Agent'),
        ('chauffeur', 'Chauffeur'),
        ('admin', 'Admin'),
    )

    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='passager')

    class Meta:
        db_table = "utilisateur"

class Passager(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    nb_reservations_total = models.IntegerField(default=0)

    class Meta:
        db_table = "passager"


class Chauffeur(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    num_permis = models.CharField(max_length=50, unique=True)
    date_embauche = models.DateField(null=True, blank=True)

    STATUT_CHOICES = (
        ('disponible', 'Disponible'),
        ('en_service', 'En service'),
        ('inactif', 'Inactif'),
    )

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='disponible')

    class Meta:
        db_table = "chauffeur"


class Agent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    matricule = models.CharField(max_length=30, unique=True)
    gare = models.ForeignKey('trajets.GareRoutiere', on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = "agent"


class AdminProfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)

    NIVEAU_CHOICES = (
        ('standard', 'Standard'),
        ('super_admin', 'Super Admin'),
    )

    niveau_acces = models.CharField(max_length=20, choices=NIVEAU_CHOICES, default='standard')

    class Meta:
        db_table = "admin_profil"