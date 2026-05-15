from rest_framework.permissions import BasePermission


class IsPassager(BasePermission):
    """Autorise uniquement les utilisateurs avec le rôle passager."""
    message = "Accès réservé aux passagers."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'passager'
        )


class IsAgent(BasePermission):
    """Autorise uniquement les utilisateurs avec le rôle agent."""
    message = "Accès réservé aux agents de gare."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'agent'
        )


class IsChauffeur(BasePermission):
    """Autorise uniquement les utilisateurs avec le rôle chauffeur."""
    message = "Accès réservé aux chauffeurs."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'chauffeur'
        )


class IsAdmin(BasePermission):
    """Autorise uniquement les utilisateurs avec le rôle admin."""
    message = "Accès réservé aux administrateurs."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'admin'
        )


class IsPassagerOrAdmin(BasePermission):
    """Passager ou Admin — ex: annuler une réservation."""
    message = "Accès réservé aux passagers ou administrateurs."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ('passager', 'admin')
        )


class IsAgentOrAdmin(BasePermission):
    """Agent ou Admin — ex: vérifier un billet."""
    message = "Accès réservé aux agents ou administrateurs."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ('agent', 'admin')
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Permission au niveau de l'objet.
    Autorise uniquement le propriétaire de l'objet ou un admin.
    À utiliser avec has_object_permission().
    """
    message = "Vous n'avez pas accès à cet objet."

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        # Pour une Reservation : vérifier que c'est le passager propriétaire
        if hasattr(obj, 'passager'):
            return obj.passager.user == request.user
        # Pour un User : vérifier que c'est lui-même
        if hasattr(obj, 'username'):
            return obj == request.user
        return False
class IsSelfOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return (
            request.user.role == 'admin'
            or obj.user == request.user
        )