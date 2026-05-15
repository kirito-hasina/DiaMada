"""
apps/api/views/dashboard_views.py
Stats globales pour l'administrateur.
"""
from datetime import date, timedelta
from django.db.models import Sum, Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime

from apps.api.permissions import IsAdmin
from apps.trajets.models import Trajet
from apps.reservations.models import Reservation
from apps.users.models import User
from apps.core.algorithms import statistiques_remplissage


# ═══════════════════════════════════════════════════════════
# 1. STATISTIQUES GLOBALES
# GET /api/v1/dashboard/statistiques/
# ═══════════════════════════════════════════════════════════
class StatistiquesGlobalesView(APIView):
    """
    Vue d'ensemble complète du système.
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        aujourd_hui = date.today()
        debut_mois  = aujourd_hui.replace(day=1)
        debut_semaine = aujourd_hui - timedelta(days=aujourd_hui.weekday())

        # ── Utilisateurs ──────────────────────────────────
        users = User.objects.aggregate(
            total        = Count('id'),
            passagers    = Count('id', filter=Q(role='passager')),
            chauffeurs   = Count('id', filter=Q(role='chauffeur')),
            agents       = Count('id', filter=Q(role='agent')),
            admins       = Count('id', filter=Q(role='admin')),
            actifs       = Count('id', filter=Q(is_active=True)),
        )

        # ── Trajets ───────────────────────────────────────
        trajets = Trajet.objects.aggregate(
            total      = Count('id'),
            planifies  = Count('id', filter=Q(statut='planifie')),
            en_cours   = Count('id', filter=Q(statut='en_cours')),
            termines   = Count('id', filter=Q(statut='termine')),
            annules    = Count('id', filter=Q(statut='annule')),
            aujourd_hui= Count('id', filter=Q(date_depart=aujourd_hui)),
        )

        # ── Réservations ──────────────────────────────────
        reservations = Reservation.objects.aggregate(
            total      = Count('id'),
            confirmees = Count('id', filter=Q(statut='confirmee')),
            embarquees = Count('id', filter=Q(statut='embarquee')),
            annulees   = Count('id', filter=Q(statut='annulee')),
            ce_mois    = Count('id', filter=Q(date_reservation__gte=debut_mois)),
            cette_semaine = Count('id', filter=Q(date_reservation__gte=debut_semaine)),
            aujourd_hui= Count('id', filter=Q(date_reservation__date=aujourd_hui)),
        )

        # ── Revenus ───────────────────────────────────────
        revenus = Reservation.objects.filter(
            statut__in=['confirmee', 'embarquee']
        ).aggregate(
            total       = Sum('prix_total'),
            ce_mois     = Sum('prix_total', filter=Q(date_reservation__gte=debut_mois)),
            cette_semaine = Sum('prix_total', filter=Q(date_reservation__gte=debut_semaine)),
            aujourd_hui = Sum('prix_total', filter=Q(date_reservation__date=aujourd_hui)),
        )

        # ── Remplissage ───────────────────────────────────
        trajets_qs   = Trajet.objects.filter(statut__in=['planifie', 'en_cours', 'termine'])
        stats_rempl  = statistiques_remplissage(list(trajets_qs))

        return Response({
            'utilisateurs'  : users,
            'trajets'       : trajets,
            'reservations'  : reservations,
            'revenus'       : {
                'total'         : float(revenus['total'] or 0),
                'ce_mois'       : float(revenus['ce_mois'] or 0),
                'cette_semaine' : float(revenus['cette_semaine'] or 0),
                'aujourd_hui'   : float(revenus['aujourd_hui'] or 0),
            },
            'remplissage'   : stats_rempl,
        }, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════
# 2. TRAJETS LES PLUS POPULAIRES
# GET /api/v1/dashboard/trajets-populaires/
# ═══════════════════════════════════════════════════════════
class TrajetsPopulairesView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        try:
            limite = max(1, min(int(request.query_params.get('limite', 5)), 50))
        except ValueError:
            limite = 5

        trajets = Trajet.objects.annotate(
            nb_reservations = Count('reservation',
                filter=Q(reservation__statut__in=['confirmee', 'embarquee']))
        ).order_by('-nb_reservations').select_related(
            'gare_depart', 'gare_arrivee'
        )[:limite]

        data = []
        for t in trajets:
            data.append({
                'trajet_id'      : t.id,
                'itineraire'     : f"{t.gare_depart.ville} → {t.gare_arrivee.ville}",
                'date'           : t.date_depart,
                'nb_reservations': t.nb_reservations,
                'taux_remplissage': round(
                    (t.places_totales - t.places_disponibles)
                    / t.places_totales * 100, 1
                ) if t.places_totales > 0 else 0,
                'statut'         : t.statut,
            })

        return Response({
            'trajets_populaires': data
        }, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════
# 3. REVENUS PAR PÉRIODE
# GET /api/v1/dashboard/revenus/?periode=mois
# ═══════════════════════════════════════════════════════════
class RevenusView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        periode     = request.query_params.get('periode', 'mois')
        aujourd_hui = date.today()

        if periode == 'semaine':
            debut = aujourd_hui - timedelta(days=7)
            label = "7 derniers jours"
        elif periode == 'mois':
            debut = aujourd_hui - timedelta(days=30)
            label = "30 derniers jours"
        elif periode == 'trimestre':
            debut = aujourd_hui - timedelta(days=90)
            label = "90 derniers jours"
        else:
            debut = aujourd_hui - timedelta(days=30)
            label = "30 derniers jours"

        reservations = Reservation.objects.filter(
            statut__in=['confirmee', 'embarquee'],
            date_reservation__date__gte=debut,
        )

        # Revenus par jour
        from django.db.models.functions import TruncDate
        revenus_par_jour = reservations.annotate(
            jour=TruncDate('date_reservation')
        ).values('jour').annotate(
            revenu    = Sum('prix_total'),
            nb_resa   = Count('id'),
        ).order_by('jour')

        return Response({
            'periode'         : label,
            'total_revenus'   : float(reservations.aggregate(t=Sum('prix_total'))['t'] or 0),
            'total_reservations': reservations.count(),
            'revenus_par_jour': list(revenus_par_jour),
        }, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════
# 4. TAUX DE REMPLISSAGE
# GET /api/v1/dashboard/remplissage/
# ═══════════════════════════════════════════════════════════
class RemplissageView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        trajets = Trajet.objects.select_related(
            'gare_depart', 'gare_arrivee'
        ).filter(statut__in=['planifie', 'en_cours', 'termine'])

        # Filtre optionnel par date
        date_str = request.query_params.get('date')

        if date_str:
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                trajets = trajets.filter(date_depart=parsed_date)
            except ValueError:
                return Response(
                    {'erreur': "Format date invalide. Utiliser YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        stats = statistiques_remplissage(list(trajets))

        detail = []
        for t in trajets:
            places_prises = t.places_totales - t.places_disponibles
            taux = round(places_prises / t.places_totales * 100, 1) if t.places_totales > 0 else 0
            detail.append({
                'trajet_id'     : t.id,
                'itineraire'    : f"{t.gare_depart.ville} → {t.gare_arrivee.ville}",
                'date'          : t.date_depart,
                'places_totales': t.places_totales,
                'places_prises' : places_prises,
                'places_dispo'  : t.places_disponibles,
                'taux'          : taux,
                'statut'        : t.statut,
            })

        # Trier du plus rempli au moins rempli
        detail.sort(key=lambda x: x['taux'], reverse=True)

        return Response({
            'statistiques_globales': stats,
            'detail_trajets'       : detail,
        }, status=status.HTTP_200_OK)