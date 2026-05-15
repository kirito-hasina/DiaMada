"""
apps/api/views/agent_views.py

Views spécifiques à l'Agent de gare :
  - Vérifier un billet (code ou QR)
  - Valider l'embarquement
  - Créer une réservation au guichet
  - Liste des réservations du jour
"""
from datetime import date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.api.permissions import IsAgent
from apps.reservations.models import Reservation, Embarquement
from apps.trajets.models import Trajet
from apps.api.serializers import (
    ReservationReadSerializer,
    ReservationWriteSerializer,
    EmbarquementSerializer,
)
from django.db import transaction


# ═══════════════════════════════════════════════════════════
# 1. VÉRIFIER UN BILLET
# POST /api/v1/agent/verifier-billet/
# ═══════════════════════════════════════════════════════════
class VerifierBilletView(APIView):
    """
    L'agent scanne ou saisit le code_billet.
    Retourne les infos du passager et le statut du billet.
    Ne valide pas encore l'embarquement — juste la vérification.
    """
    permission_classes = [IsAgent]

    def post(self, request):
        code = request.data.get('code_billet', '').strip().upper()

        if not code:
            return Response(
                {'valide': False, 'erreur': "Le code billet est requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Chercher la réservation
        try:
            reservation = Reservation.objects.select_related(
                'passager__user',
                'trajet__gare_depart',
                'trajet__gare_arrivee',
            ).get(code_billet=code)
        except Reservation.DoesNotExist:
            return Response(
                {'valide': False, 'erreur': "Billet introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Vérifier le statut
        if reservation.statut == 'embarquee':
            return Response({
                'valide'  : False,
                'erreur'  : "Ce billet a déjà été utilisé.",
                'statut'  : reservation.statut,
                'passager': f"{reservation.passager.user.prenom} {reservation.passager.user.nom}",
            }, status=status.HTTP_200_OK)

        if reservation.statut == 'annulee':
            return Response({
                'valide': False,
                'erreur': "Cette réservation est annulée.",
                'statut': reservation.statut,
            }, status=status.HTTP_200_OK)

        if reservation.statut != 'confirmee':
            return Response({
                'valide': False,
                'erreur': f"Statut invalide : {reservation.statut}.",
                'statut': reservation.statut,
            }, status=status.HTTP_200_OK)

        # Billet valide
        trajet = reservation.trajet
        return Response({
            'valide'      : True,
            'code_billet' : reservation.code_billet,
            'passager'    : {
                'nom'     : reservation.passager.user.nom,
                'prenom'  : reservation.passager.user.prenom,
                'telephone': reservation.passager.user.telephone,
            },
            'trajet'      : {
                'depart'  : trajet.gare_depart.ville,
                'arrivee' : trajet.gare_arrivee.ville,
                'date'    : trajet.date_depart.isoformat(),
                'heure'   : str(trajet.heure_depart),
            },
            'nb_places'   : reservation.nb_places,
            'prix_total'  : reservation.prix_total,
            'statut'      : reservation.statut,
        }, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════
# 2. VALIDER L'EMBARQUEMENT
# POST /api/v1/agent/embarquement/
# ═══════════════════════════════════════════════════════════
class ValiderEmbarquementView(APIView):
    """
    Après vérification, l'agent valide l'embarquement.
    Passe la réservation en statut 'embarquee'.
    Crée un enregistrement Embarquement avec heure et agent.
    """
    permission_classes = [IsAgent]

    def post(self, request):
        code = request.data.get('code_billet', '').strip().upper()

        if not code:
            return Response(
                {'erreur': "Le code billet est requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            agent = request.user.agent
        except AttributeError:
            return Response(
                {'erreur': "Profil agent introuvable."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():

                reservation = Reservation.objects.select_for_update().select_related(
                    'passager__user',
                    'trajet'
                ).get(code_billet=code)

                # Déjà utilisé
                if reservation.statut == 'embarquee':
                    return Response(
                        {'erreur': "Ce passager est déjà embarqué."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Mauvais statut
                if reservation.statut != 'confirmee':
                    return Response(
                        {
                            'erreur': f"Impossible d'embarquer — statut : {reservation.statut}."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Créer embarquement
                embarquement = Embarquement.objects.create(
                    reservation=reservation,
                    agent=agent,
                    statut='valide',
                )

                # Mettre à jour réservation
                reservation.statut = 'embarquee'
                reservation.save()

        except Reservation.DoesNotExist:
            return Response(
                {'erreur': "Billet introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            'message': "Embarquement validé avec succès.",
            'code_billet': reservation.code_billet,
            'passager': (
                f"{reservation.passager.user.prenom} "
                f"{reservation.passager.user.nom}"
            ),
            'heure_scan': embarquement.heure_scan,
            'agent': f"{agent.user.prenom} {agent.user.nom}",
        }, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════
# 3. RÉSERVATION AU GUICHET
# POST /api/v1/agent/reservation-guichet/
# ═══════════════════════════════════════════════════════════
class ReservationGuichetView(APIView):
    """
    L'agent crée une réservation pour un passager physique.
    Le canal est automatiquement 'guichet'.
    L'agent est automatiquement lié à la réservation.
    """
    permission_classes = [IsAgent]

    def post(self, request):
        from apps.users.models import Passager

        # Récupérer agent
        try:
            agent = request.user.agent
        except AttributeError:
            return Response(
                {'erreur': "Profil agent introuvable."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Identifier passager
        passager_id = request.data.get('passager_id')
        passager_email = request.data.get('passager_email')

        if not passager_id and not passager_email:
            return Response(
                {'erreur': "Fournir 'passager_id' ou 'passager_email'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if passager_id:
                passager = Passager.objects.select_related('user').get(
                    user__id=passager_id
                )
            else:
                passager = Passager.objects.select_related('user').get(
                    user__email=passager_email
                )

        except Passager.DoesNotExist:
            return Response(
                {'erreur': "Passager introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Préparer données
        data = request.data.copy()
        data['canal'] = 'guichet'

        serializer = ReservationWriteSerializer(data=data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():

                trajet = Trajet.objects.select_for_update().get(
                    id=serializer.validated_data['trajet'].id
                )

                nb_places = serializer.validated_data['nb_places']

                if trajet.places_disponibles < nb_places:
                    return Response(
                        {'erreur': "Places insuffisantes."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                prix_total = trajet.prix * nb_places

                trajet.places_disponibles -= nb_places
                trajet.save()

                validated = serializer.validated_data.copy()
                validated.pop('statut', None)
                validated.pop('prix_total', None)
                validated.pop('passager', None)
                validated['trajet'] = trajet

                reservation = Reservation.objects.create(
                    passager=passager,
                    agent=agent,
                    prix_total=prix_total,
                    statut='confirmee',
                    **validated
                )

        except Trajet.DoesNotExist:
            return Response(
                {'erreur': "Trajet introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        read_serializer = ReservationReadSerializer(reservation)

        return Response({
            'message': "Réservation guichet créée avec succès.",
            'reservation': read_serializer.data,
        }, status=status.HTTP_201_CREATED)


# ═══════════════════════════════════════════════════════════
# 4. RÉSERVATIONS DU JOUR
# GET /api/v1/agent/reservations-du-jour/
# ═══════════════════════════════════════════════════════════
class ReservationsDuJourView(APIView):
    """
    Liste toutes les réservations confirmées pour aujourd'hui.
    Utile pour l'agent pour voir qui doit embarquer.
    """
    permission_classes = [IsAgent]

    def get(self, request):
        aujourd_hui = date.today()

        reservations = Reservation.objects.select_related(
            'passager__user',
            'trajet__gare_depart',
            'trajet__gare_arrivee',
        ).filter(
            trajet__date_depart=aujourd_hui,
            statut__in=['confirmee', 'embarquee'],
        ).order_by('trajet__heure_depart', 'statut')

        # Filtre optionnel par trajet : /agent/reservations-du-jour/?trajet_id=1
        trajet_id = request.query_params.get('trajet_id')
        if trajet_id:
            reservations = reservations.filter(trajet__id=trajet_id)

        serializer = ReservationReadSerializer(reservations, many=True)
        return Response({
            'date'        : aujourd_hui,
            'total'       : reservations.count(),
            'reservations': serializer.data,
        }, status=status.HTTP_200_OK)