"""
apps/api/views/chauffeur_views.py

Views spécifiques au Chauffeur :
  - Mon trajet du jour
  - Liste de mes passagers
  - Confirmer le départ
  - Confirmer l'arrivée
"""
from datetime import date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import transaction

from apps.api.permissions import IsChauffeur
from apps.trajets.models import Trajet
from apps.reservations.models import Reservation
from apps.api.serializers import TrajetReadSerializer


# ═══════════════════════════════════════════════════════════
# 1. MON TRAJET DU JOUR
# GET /api/v1/chauffeur/mon-trajet/
# ═══════════════════════════════════════════════════════════
class MonTrajetView(APIView):
    """
    Retourne le trajet assigné au chauffeur connecté pour aujourd'hui.
    Si plusieurs trajets → retourne le prochain à venir.
    """
    permission_classes = [IsChauffeur]

    def get(self, request):
        try:
            chauffeur = request.user.chauffeur
        except AttributeError:
            return Response(
                {'erreur': "Profil chauffeur introuvable."},
                status=status.HTTP_400_BAD_REQUEST
            )

        aujourd_hui = timezone.localdate()

        # Chercher le trajet du jour assigné à ce chauffeur
        trajets = Trajet.objects.select_related(
            'gare_depart', 'gare_arrivee', 'vehicule'
        ).filter(
            chauffeur=chauffeur,
            date_depart=aujourd_hui,
            statut__in=['planifie', 'en_cours'],
        ).order_by('heure_depart')

        if not trajets.exists():
            return Response(
                {'message': "Aucun trajet assigné pour aujourd'hui."},
                status=status.HTTP_200_OK
            )

        # Prendre le prochain trajet (le plus tôt)
        trajet = trajets.first()
        serializer = TrajetReadSerializer(trajet)

        return Response({
            'trajet'             : serializer.data,
            'nb_passagers_total' : trajet.places_totales - trajet.places_disponibles,
            'places_disponibles' : trajet.places_disponibles,
        }, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════
# 2. MES PASSAGERS
# GET /api/v1/chauffeur/mes-passagers/
# ═══════════════════════════════════════════════════════════
class MesPassagersView(APIView):
    """
    Liste tous les passagers embarqués (ou confirmés) pour le trajet
    du chauffeur connecté aujourd'hui.
    """
    permission_classes = [IsChauffeur]

    def get(self, request):
        try:
            chauffeur = request.user.chauffeur
        except AttributeError:
            return Response(
                {'erreur': "Profil chauffeur introuvable."},
                status=status.HTTP_400_BAD_REQUEST
            )

        aujourd_hui = timezone.localdate()

        # Trajet du jour
        trajet = Trajet.objects.filter(
            chauffeur=chauffeur,
            date_depart=aujourd_hui,
            statut__in=['planifie', 'en_cours'],
        ).order_by('heure_depart').first()

        if not trajet:
            return Response(
                {'message': "Aucun trajet assigné pour aujourd'hui."},
                status=status.HTTP_200_OK
            )

        # Récupérer les réservations confirmées et embarquées
        reservations = Reservation.objects.select_related(
            'passager__user'
        ).filter(
            trajet=trajet,
            statut__in=['confirmee', 'embarquee'],
        ).order_by('statut', 'date_reservation')

        # Filtre optionnel : /chauffeur/mes-passagers/?statut=embarquee
        statut_filtre = request.query_params.get('statut')
        if statut_filtre:
            reservations = reservations.filter(statut=statut_filtre)

        passagers = []
        for resa in reservations:
            passagers.append({
                'reservation_id': resa.id,
                'code_billet'   : resa.code_billet,
                'nom'           : resa.passager.user.nom,
                'prenom'        : resa.passager.user.prenom,
                'telephone'     : resa.passager.user.telephone,
                'nb_places'     : resa.nb_places,
                'statut'        : resa.statut,
                'embarque'      : resa.statut == 'embarquee',
            })

        return Response({
            'trajet'    : {
                'id'    : trajet.id,
                'depart': trajet.gare_depart.ville,
                'arrivee': trajet.gare_arrivee.ville,
                'heure' : str(trajet.heure_depart),
                'statut': trajet.statut,
            },
            'total_passagers'   : len(passagers),
            'embarques'         : sum(1 for p in passagers if p['embarque']),
            'en_attente'        : sum(1 for p in passagers if not p['embarque']),
            'passagers'         : passagers,
        }, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════
# 3. CONFIRMER LE DÉPART
# POST /api/v1/chauffeur/confirmer-depart/
# ═══════════════════════════════════════════════════════════
class ConfirmerDepartView(APIView):
    """
    Le chauffeur confirme que le véhicule est parti.
    Passe le trajet en statut 'en_cours'.
    """
    permission_classes = [IsChauffeur]

    def post(self, request):
        try:
            chauffeur = request.user.chauffeur
        except AttributeError:
            return Response(
                {'erreur': "Profil chauffeur introuvable."},
                status=status.HTTP_400_BAD_REQUEST
            )

        aujourd_hui = timezone.localdate()
        with transaction.atomic():
            trajet = Trajet.objects.filter(
                chauffeur=chauffeur,
                date_depart=aujourd_hui,
                statut='planifie',
            ).order_by('heure_depart').first()

            if not trajet:
                return Response(
                    {'erreur': "Aucun trajet planifié trouvé pour aujourd'hui."},
                    status=status.HTTP_404_NOT_FOUND
                )
             # Vérifier qu'au moins 1 passager est embarqué
            nb_embarques = Reservation.objects.filter(
                trajet=trajet,
                statut='embarquee'
            ).count()

            if nb_embarques == 0:
                return Response(
                    {'erreur': "Aucun passager embarqué."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            trajet.statut = 'en_cours'
            trajet.save()

        # Stats au départ
        nb_embarques = Reservation.objects.filter(
            trajet=trajet, statut='embarquee'
        ).count()

        return Response({
            'message'    : "Départ confirmé. Bon voyage !",
            'trajet_id'  : trajet.id,
            'depart'     : trajet.gare_depart.ville,
            'arrivee'    : trajet.gare_arrivee.ville,
            'nb_embarques': nb_embarques,
            'places_totales': trajet.places_totales,
            'statut'     : trajet.statut,
        }, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════
# 4. CONFIRMER L'ARRIVÉE
# POST /api/v1/chauffeur/confirmer-arrivee/
# ═══════════════════════════════════════════════════════════
class ConfirmerArriveeView(APIView):
    """
    Le chauffeur confirme l'arrivée à destination.
    Passe le trajet en statut 'termine'.
    """
    permission_classes = [IsChauffeur]

    def post(self, request):
        try:
            chauffeur = request.user.chauffeur
        except AttributeError:
            return Response(
                {'erreur': "Profil chauffeur introuvable."},
                status=status.HTTP_400_BAD_REQUEST
            )

        aujourd_hui = timezone.localdate()

        with transaction.atomic():
            trajet = Trajet.objects.filter(
                chauffeur=chauffeur,
                date_depart=aujourd_hui,
                statut='en_cours',
            ).order_by('heure_depart').first()

            if not trajet:
                return Response(
                    {'erreur': "Aucun trajet en cours trouvé."},
                    status=status.HTTP_404_NOT_FOUND
                )

            trajet.statut = 'termine'
            trajet.save()

        return Response({
            'message'  : "Arrivée confirmée. Trajet terminé.",
            'trajet_id': trajet.id,
            'depart'   : trajet.gare_depart.ville,
            'arrivee'  : trajet.gare_arrivee.ville,
            'statut'   : trajet.statut,
        }, status=status.HTTP_200_OK)