from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.notifications.models import Notification
from apps.api.serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    """
    GET   /notifications/              → mes notifications
    PATCH /notifications/{id}/         → marquer comme lue
    POST  /notifications/tout-lire/    → tout marquer comme lu
    DELETE /notifications/{id}/        → supprimer
    """
    serializer_class = NotificationSerializer
    queryset = Notification.objects.all()
    # Pas de create() public — les notifications sont créées automatiquement
    # par les signals Django (prochaine étape)
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Notification.objects.none()

        qs = Notification.objects.filter(
            utilisateur=user
        ).order_by('-created_at')

        # Filtre optionnel : /notifications/?non_lues=1
        non_lues = self.request.query_params.get('non_lues')
        if non_lues == '1':
            qs = qs.filter(lu=False)

        return qs

    def partial_update(self, request, *args, **kwargs):
        """PATCH /notifications/{id}/ — marquer comme lue."""
        instance = self.get_object()
        if not instance.lu:
            instance.lu = True
            instance.save(update_fields=['lu'])
        return Response(
            {'message': 'Notification marquée comme lue.'},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['patch'], url_path='tout-lire')
    def tout_lire(self, request):
        """PATCH /notifications/tout-lire/ — tout marquer comme lu."""
        count = self.get_queryset().filter(lu=False).update(lu=True)
        return Response(
            {'message': f'{count} notification(s) marquées comme lues.'},
            status=status.HTTP_200_OK
        )