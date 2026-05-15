from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.models import User, Passager, Agent, Chauffeur, AdminProfil


# ═══════════════════════════════════════════════════════════
# REGISTER SERIALIZER
# Gère l'inscription + création automatique du profil
# ═══════════════════════════════════════════════════════════
class RegisterSerializer(serializers.ModelSerializer):
    password         = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)

    # Champs spécifiques selon le rôle (optionnels selon le rôle)
    num_permis    = serializers.CharField(required=False, allow_blank=True)
    matricule     = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model  = User
        fields = [
            'username', 'email', 'nom', 'prenom', 'telephone',
            'role', 'password', 'password_confirm',
            # Champs profil spécifiques
            'num_permis', 'matricule',
        ]

    # ── Validations ──────────────────────────────────────────
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Cet email est déjà utilisé.")
        return value

    def validate_role(self, value):
        roles_valides = ('passager', 'agent', 'chauffeur', 'admin')
        if value not in roles_valides:
            raise serializers.ValidationError(
                f"Rôle invalide. Choisir parmi : {', '.join(roles_valides)}"
            )
        return value

    def validate(self, data):
        # Vérification mots de passe identiques
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': "Les mots de passe ne correspondent pas."
            })

        role = data.get('role', 'passager')

        # Chauffeur → num_permis obligatoire
        if role == 'chauffeur':
            num_permis = data.get('num_permis', '').strip()
            if not num_permis:
                raise serializers.ValidationError({
                    'num_permis': "Le numéro de permis est obligatoire pour un chauffeur."
                })
            if Chauffeur.objects.filter(num_permis=num_permis).exists():
                raise serializers.ValidationError({
                    'num_permis': "Ce numéro de permis existe déjà."
                })

        # Agent → matricule obligatoire
        if role == 'agent':
            matricule = data.get('matricule', '').strip()
            if not matricule:
                raise serializers.ValidationError({
                    'matricule': "Le matricule est obligatoire pour un agent."
                })
            if Agent.objects.filter(matricule=matricule).exists():
                raise serializers.ValidationError({
                    'matricule': "Ce matricule existe déjà."
                })

        return data

    # ── Création User + profil selon le rôle ─────────────────
    def create(self, validated_data):
        # Retirer les champs non-User
        validated_data.pop('password_confirm')
        password   = validated_data.pop('password')
        num_permis = validated_data.pop('num_permis', '').strip()
        matricule  = validated_data.pop('matricule', '').strip()
        role       = validated_data.get('role', 'passager')

        # Créer le User (mot de passe haché)
        user = User.objects.create_user(
            password=password,
            is_staff=(role == 'admin'),
            **validated_data
        )

        # Créer le profil correspondant au rôle
        if role == 'passager':
            Passager.objects.create(user=user)

        elif role == 'chauffeur':
            Chauffeur.objects.create(user=user, num_permis=num_permis)

        elif role == 'agent':
            Agent.objects.create(user=user, matricule=matricule)

        elif role == 'admin':
            AdminProfil.objects.create(user=user)

        return user


# ═══════════════════════════════════════════════════════════
# LOGIN RESPONSE SERIALIZER
# Enrichit la réponse JWT avec les infos du user
# ═══════════════════════════════════════════════════════════
class LoginResponseSerializer(serializers.Serializer):
    """
    Utilisé pour construire la réponse du login.
    Retourne : access, refresh + infos complètes du user.
    """
    access  = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user    = serializers.SerializerMethodField()

    def get_user(self, obj):
        user = obj['user']
        return {
            'id'      : user.id,
            'username': user.username,
            'email'   : user.email,
            'nom'     : user.nom,
            'prenom'  : user.prenom,
            'role'    : user.role,
            'is_active': user.is_active,
        }