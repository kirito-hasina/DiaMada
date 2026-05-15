from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate

from apps.users.models import User
from apps.api.serializers.auth_serializers import RegisterSerializer


# ═══════════════════════════════════════════════════════════
# REGISTER VIEW
# POST /api/v1/auth/register/
# ═══════════════════════════════════════════════════════════
class RegisterView(APIView):
    """
    Inscription d'un nouvel utilisateur.
    Crée le User + le profil selon le rôle automatiquement.
    Retourne directement le JWT pour connecter l'utilisateur.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        user = serializer.save()

        # Générer les tokens JWT directement après inscription
        refresh = RefreshToken.for_user(user)

        return Response({
            'message' : f'Compte créé avec succès. Bienvenue {user.prenom} !',
            'access'  : str(refresh.access_token),
            'refresh' : str(refresh),
            'user'    : {
                'id'      : user.id,
                'username': user.username,
                'email'   : user.email,
                'nom'     : user.nom,
                'prenom'  : user.prenom,
                'role'    : user.role,
            }
        }, status=status.HTTP_201_CREATED)


# ═══════════════════════════════════════════════════════════
# CUSTOM LOGIN VIEW
# POST /api/v1/auth/login/
# ═══════════════════════════════════════════════════════════
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Enrichit le token JWT avec le rôle et les infos du user.
    Ces infos sont encodées DANS le token (payload).
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Données custom ajoutées au payload du JWT
        token['role']   = user.role
        token['nom']    = user.nom
        token['prenom'] = user.prenom
        token['email']  = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Vérifier que le compte est actif
        if not self.user.is_active:
            raise serializers.ValidationError(
                "Ce compte est désactivé. Contactez l'administrateur."
            )

        # Enrichir la réponse avec les infos du user
        data['user'] = {
            'id'      : self.user.id,
            'username': self.user.username,
            'email'   : self.user.email,
            'nom'     : self.user.nom,
            'prenom'  : self.user.prenom,
            'role'    : self.user.role,
            'is_active': self.user.is_active,
        }
        return data


class LoginView(TokenObtainPairView):
    """
    Connexion — retourne access + refresh + infos user.
    Utilise le serializer custom qui enrichit le token.
    """
    permission_classes = [AllowAny]
    serializer_class   = CustomTokenObtainPairSerializer


# ═══════════════════════════════════════════════════════════
# LOGOUT VIEW
# POST /api/v1/auth/logout/
# ═══════════════════════════════════════════════════════════
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(
            {'message': 'Déconnexion réussie.'},
            status=status.HTTP_200_OK
        )


# ═══════════════════════════════════════════════════════════
# ME VIEW
# GET /api/v1/auth/me/
# ═══════════════════════════════════════════════════════════
class MeView(APIView):
    """
    Retourne les infos de l'utilisateur actuellement connecté.
    Utile pour que le frontend récupère le profil après login.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            'id'       : user.id,
            'username' : user.username,
            'email'    : user.email,
            'nom'      : user.nom,
            'prenom'   : user.prenom,
            'telephone': user.telephone,
            'role'     : user.role,
            'is_active': user.is_active,
        }

        # Ajouter les infos du profil selon le rôle
        try:
            if user.role == 'passager':
                profil = user.passager
                data['profil'] = {
                    'nb_reservations_total': profil.nb_reservations_total,
                }
            elif user.role == 'chauffeur':
                profil = user.chauffeur
                data['profil'] = {
                    'num_permis'   : profil.num_permis,
                    'date_embauche': profil.date_embauche,
                    'statut'       : profil.statut,
                }
            elif user.role == 'agent':
                profil = user.agent
                data['profil'] = {
                    'matricule': profil.matricule,
                    'gare'     : profil.gare.nom if profil.gare else None,
                }
            elif user.role == 'admin':
                profil = user.adminprofil
                data['profil'] = {
                    'niveau_acces': profil.niveau_acces,
                }
        except Exception:
            data['profil'] = None

        return Response(data, status=status.HTTP_200_OK)

    def patch(self, request):
        """Modifier son propre profil (nom, prénom, téléphone)."""
        user = request.user
        champs_modifiables = ['nom', 'prenom', 'telephone']

        for champ in champs_modifiables:
            if champ in request.data:
                setattr(user, champ, request.data[champ])

        # Changer le mot de passe si fourni
        nouveau_mdp = request.data.get('password')
        ancien_mdp  = request.data.get('old_password')
        if nouveau_mdp:
            if not ancien_mdp:
                return Response(
                    {'error': "L'ancien mot de passe est requis."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not user.check_password(ancien_mdp):
                return Response(
                    {'error': "Ancien mot de passe incorrect."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if nouveau_mdp and len(nouveau_mdp) < 6:
                return Response(
                    {'error': 'Mot de passe trop court (6 caractères min).'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.set_password(nouveau_mdp)

        user.save()
        return Response(
            {'message': 'Profil mis à jour avec succès.'},
            status=status.HTTP_200_OK
        )