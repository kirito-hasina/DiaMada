from rest_framework import serializers
from apps.users.models import User, Passager, Chauffeur, Agent, AdminProfil


# ═══════════════════════════════════════════════
# USER
# ═══════════════════════════════════════════════
class UserSerializer(serializers.ModelSerializer):
    # write_only → jamais retourné dans les réponses GET
    password = serializers.CharField(
        write_only=True,
        min_length=6,
        error_messages={'min_length': 'Le mot de passe doit contenir au moins 6 caractères.'}
    )

    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'nom', 'prenom', 'telephone', 'role', 'password']
        extra_kwargs = {'role': {'read_only': True}}

    def validate_username(self, value):
        qs = User.objects.filter(username=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ce nom d'utilisateur existe déjà.")
        return value

    def validate_email(self, value):
        qs = User.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Cet email est déjà utilisé.")
        return value

    def validate_telephone(self, value):
        if value and not value.replace('+', '').isdigit():
            raise serializers.ValidationError(
                "Le téléphone doit contenir uniquement des chiffres."
            )
        if value and len(value.replace('+', '')) < 9:
            raise serializers.ValidationError("Numéro de téléphone invalide.")
        return value


# ═══════════════════════════════════════════════
# PASSAGER
# ═══════════════════════════════════════════════
class PassagerSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model  = Passager
        fields = '__all__'

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        password  = user_data.pop('password')
        user = User.objects.create_user(role='passager', password=password, **user_data)
        return Passager.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        password  = user_data.pop('password', None)
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        if password:
            instance.user.set_password(password)
        instance.user.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# ═══════════════════════════════════════════════
# CHAUFFEUR
# ═══════════════════════════════════════════════
class ChauffeurSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model  = Chauffeur
        fields = '__all__'

    def validate_num_permis(self, value):
        qs = Chauffeur.objects.filter(num_permis=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ce numéro de permis existe déjà.")
        return value

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        password  = user_data.pop('password')
        user = User.objects.create_user(role='chauffeur', password=password, **user_data)
        return Chauffeur.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        password  = user_data.pop('password', None)
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        if password:
            instance.user.set_password(password)
        instance.user.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# ═══════════════════════════════════════════════
# AGENT
# ═══════════════════════════════════════════════
class AgentSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model  = Agent
        fields = '__all__'

    def validate_matricule(self, value):
        qs = Agent.objects.filter(matricule=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ce matricule existe déjà.")
        return value

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        password  = user_data.pop('password')
        user = User.objects.create_user(role='agent', password=password, **user_data)
        return Agent.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        password  = user_data.pop('password', None)
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        if password:
            instance.user.set_password(password)
        instance.user.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# ═══════════════════════════════════════════════
# ADMIN
# ═══════════════════════════════════════════════
class AdminSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model  = AdminProfil
        fields = '__all__'

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        password  = user_data.pop('password')
        user = User.objects.create_user(
            role='admin', password=password, is_staff=True, **user_data
        )
        return AdminProfil.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        password  = user_data.pop('password', None)
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        if password:
            instance.user.set_password(password)
        instance.user.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance