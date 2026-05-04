from rest_framework import serializers
from apps.users.models import User, Passager, Chauffeur, Agent, AdminProfil


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'nom', 'prenom', 'telephone', 'role']


class PassagerSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Passager
        fields = '__all__'


class ChauffeurSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Chauffeur
        fields = '__all__'


class AgentSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Agent
        fields = '__all__'


class AdminSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = AdminProfil
        fields = '__all__'