from rest_framework import viewsets
from apps.users.models import User, Passager, Chauffeur, Agent
from apps.api.serializers import (
    UserSerializer, PassagerSerializer,
    ChauffeurSerializer, AgentSerializer
)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class PassagerViewSet(viewsets.ModelViewSet):
    queryset = Passager.objects.all()
    serializer_class = PassagerSerializer


class ChauffeurViewSet(viewsets.ModelViewSet):
    queryset = Chauffeur.objects.all()
    serializer_class = ChauffeurSerializer


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer