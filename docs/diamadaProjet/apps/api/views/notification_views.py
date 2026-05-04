from rest_framework import viewsets
from apps.notifications.models import Notification
from apps.api.serializers import NotificationSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer