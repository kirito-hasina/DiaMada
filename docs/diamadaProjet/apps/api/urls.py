from rest_framework.routers import DefaultRouter
from apps.api.views.user_views import *
from apps.api.views.trajet_views import *
from apps.api.views.reservation_views import *
from apps.api.views.notification_views import *

router = DefaultRouter()

# Users
router.register(r'users', UserViewSet)
router.register(r'passagers', PassagerViewSet)
router.register(r'chauffeurs', ChauffeurViewSet)
router.register(r'agents', AgentViewSet)

# Trajets
router.register(r'trajets', TrajetViewSet)
router.register(r'gares', GareViewSet)
router.register(r'vehicules', VehiculeViewSet)

# Reservations
router.register(r'reservations', ReservationViewSet)
router.register(r'embarquement', EmbarquementViewSet)

# Notifications
router.register(r'notifications', NotificationViewSet)

urlpatterns = router.urls