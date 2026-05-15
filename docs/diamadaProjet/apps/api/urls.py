from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

# Auth
from apps.api.views.auth_views import RegisterView, LoginView, LogoutView, MeView

# CRUD ViewSets
from apps.api.views.user_views import (
    UserViewSet, PassagerViewSet, ChauffeurViewSet, AgentViewSet
)
from apps.api.views.trajet_views import TrajetViewSet, GareViewSet, VehiculeViewSet
from apps.api.views.reservation_views import ReservationViewSet, EmbarquementViewSet
from apps.api.views.notification_views import NotificationViewSet

# Views Agent
from apps.api.views.agent_views import (
    VerifierBilletView,
    ValiderEmbarquementView,
    ReservationGuichetView,
    ReservationsDuJourView,
)

# Views Chauffeur
from apps.api.views.chauffeur_views import (
    MonTrajetView,
    MesPassagersView,
    ConfirmerDepartView,
    ConfirmerArriveeView,
)

from apps.api.views.dashboard_views import (
    StatistiquesGlobalesView, TrajetsPopulairesView,
    RevenusView, RemplissageView,
)

# ── Router ───────────────────────────────────────────────────
router = DefaultRouter()

router.register(r'users',         UserViewSet,         basename='users')
router.register(r'passagers',     PassagerViewSet,     basename='passagers')
router.register(r'chauffeurs',    ChauffeurViewSet,    basename='chauffeurs')
router.register(r'agents',        AgentViewSet,        basename='agents')
router.register(r'trajets',       TrajetViewSet,       basename='trajets')
router.register(r'gares',         GareViewSet,         basename='gares')
router.register(r'vehicules',     VehiculeViewSet,     basename='vehicules')
router.register(r'reservations',  ReservationViewSet,  basename='reservations')
router.register(r'embarquements', EmbarquementViewSet, basename='embarquements')
router.register(r'notifications', NotificationViewSet, basename='notifications')

# ── URL patterns ─────────────────────────────────────────────
urlpatterns = [

    # ── Auth ─────────────────────────────────────────────────
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/',    LoginView.as_view(),    name='auth-login'),
    path('auth/logout/',   LogoutView.as_view(),   name='auth-logout'),
    path('auth/refresh/',  TokenRefreshView.as_view(), name='auth-refresh'),
    path('auth/me/',       MeView.as_view(),       name='auth-me'),

    # ── Agent ─────────────────────────────────────────────────
    path('agent/verifier-billet/',      VerifierBilletView.as_view(),      name='agent-verifier-billet'),
    path('agent/embarquement/',         ValiderEmbarquementView.as_view(), name='agent-embarquement'),
    path('agent/reservation-guichet/',  ReservationGuichetView.as_view(),  name='agent-guichet'),
    path('agent/reservations-du-jour/', ReservationsDuJourView.as_view(),  name='agent-reservations-jour'),

    # ── Chauffeur ─────────────────────────────────────────────
    path('chauffeur/mon-trajet/',       MonTrajetView.as_view(),       name='chauffeur-mon-trajet'),
    path('chauffeur/mes-passagers/',    MesPassagersView.as_view(),    name='chauffeur-mes-passagers'),
    path('chauffeur/confirmer-depart/', ConfirmerDepartView.as_view(), name='chauffeur-depart'),
    path('chauffeur/confirmer-arrivee/',ConfirmerArriveeView.as_view(),name='chauffeur-arrivee'),

    path('dashboard/statistiques/',      StatistiquesGlobalesView.as_view(), name='dashboard-stats'),
    path('dashboard/trajets-populaires/',TrajetsPopulairesView.as_view(),     name='dashboard-trajets'),
    path('dashboard/revenus/',           RevenusView.as_view(),              name='dashboard-revenus'),
    path('dashboard/remplissage/',       RemplissageView.as_view(),          name='dashboard-remplissage'),

] + router.urls