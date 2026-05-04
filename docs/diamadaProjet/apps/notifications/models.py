from django.db import models
from apps.users.models import User
# Create your models here.

class Notification(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE)

    TYPE_CHOICES = (
        ('confirmation', 'Confirmation'),
        ('annulation', 'Annulation'),
        ('rappel', 'Rappel'),
        ('info', 'Info'),
    )

    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    message = models.TextField()

    lu = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notification"