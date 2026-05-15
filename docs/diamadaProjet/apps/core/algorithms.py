"""
apps/core/algorithms.py

Algorithmes et structures de données utilisés par DiaMada.

Algorithme principal : Algorithme Glouton (Greedy Algorithm)
─────────────────────────────────────────────────────────────
Principe : lors d'une réservation, au lieu de laisser le passager
choisir n'importe quel trajet, le système sélectionne AUTOMATIQUEMENT
le véhicule le plus rempli qui a encore assez de places.

Pourquoi ? → Remplir au maximum un véhicule avant d'en "ouvrir" un autre.
Résultat  → Moins de véhicules qui partent à moitié vides → économie
            de carburant, départs plus fréquents, meilleur service.

Structure de données utilisée : Tas max (Max-Heap)
───────────────────────────────────────────────────
Python n'a que heapq (min-heap), donc on stocke le négatif du taux
de remplissage pour simuler un max-heap.

Complexité :
  - Construction du tas : O(n log n)
  - Extraction du meilleur : O(log n)
  - Recherche linéaire simple : O(n) — utilisée comme alternative claire
"""

import heapq
from datetime import date as date_type
from apps.trajets.models import Trajet


# ═══════════════════════════════════════════════════════════
# FONCTION PRINCIPALE — appelée par la réservation
# ═══════════════════════════════════════════════════════════

def choisir_trajet_optimal(gare_depart_id, gare_arrivee_id, date_depart, nb_places):
    """
    Algorithme glouton avec Max-Heap.

    Paramètres :
        gare_depart_id  (int) : ID de la gare de départ
        gare_arrivee_id (int) : ID de la gare d'arrivée
        date_depart     (date): date du trajet
        nb_places       (int) : nombre de places demandées

    Retourne :
        Trajet (instance) : le trajet optimal sélectionné
        None              : si aucun trajet disponible

    Exemple :
        3 trajets disponibles Tana → Toamasina le 01/06 :
        - Trajet A : 15 places, 10 prises  → taux = 66.7%
        - Trajet B : 12 places,  3 prises  → taux = 25.0%
        - Trajet C : 15 places, 14 prises, mais 0 dispo → éliminé
        → Algorithme choisit Trajet A (le plus rempli avec places dispo)
    """

    # ── Étape 1 : Récupérer les trajets candidats ────────────
    # Filtrage en base → seuls les trajets du bon itinéraire,
    # à la bonne date, planifiés, avec assez de places
    trajets_candidats = Trajet.objects.filter(
        gare_depart_id      = gare_depart_id,
        gare_arrivee_id     = gare_arrivee_id,
        date_depart         = date_depart,
        statut              = 'planifie',
        places_disponibles__gte = nb_places,  # assez de places
    ).select_related('gare_depart', 'gare_arrivee', 'vehicule')

    if not trajets_candidats.exists():
        return None

    # ── Étape 2 : Construire le Max-Heap ─────────────────────
    # On utilise le TAUX DE REMPLISSAGE comme critère glouton
    # Formule : places_prises / places_totales
    # heapq est un min-heap → on stocke le négatif pour simuler max-heap
    heap = []

    for trajet in trajets_candidats:
        if trajet.places_totales == 0:
            continue  # sécurité division par zéro
        places_prises = trajet.places_totales - trajet.places_disponibles
        taux          = places_prises / trajet.places_totales  # entre 0.0 et 1.0
        # (-taux, id) → le plus grand taux sera extrait en premier
        heapq.heappush(heap, (-taux, trajet.id, trajet))

    if not heap:
        return None

    # ── Étape 3 : Extraire le meilleur (glouton) ─────────────
    # heappop retourne l'élément avec la plus petite valeur
    # comme on a stocké -taux, c'est celui avec le PLUS GRAND taux
    _, _, meilleur_trajet = heapq.heappop(heap)

    return meilleur_trajet


# ═══════════════════════════════════════════════════════════
# FONCTION STATS — utilisée par le dashboard admin
# ═══════════════════════════════════════════════════════════

def calculer_taux_remplissage(trajet):
    """
    Calcule le taux de remplissage d'un trajet en %.

    Retourne : float entre 0.0 et 100.0
    """
    if trajet.places_totales == 0:
        return 0.0
    places_prises = trajet.places_totales - trajet.places_disponibles
    return round((places_prises / trajet.places_totales) * 100, 1)


def classer_trajets_par_remplissage(trajets):
    """
    Trie une liste de trajets du plus rempli au moins rempli.
    Utilise un tri par tas (heapsort) — O(n log n).

    Paramètre : QuerySet ou liste de Trajet
    Retourne  : liste triée de Trajet
    """
    heap = []
    for trajet in trajets:
        taux = calculer_taux_remplissage(trajet)
        heapq.heappush(heap, (-taux, trajet.id, trajet))

    resultat = []
    while heap:
        _, _, trajet = heapq.heappop(heap)
        resultat.append(trajet)
    return resultat


def statistiques_remplissage(trajets):
    """
    Calcule les statistiques globales de remplissage.
    Utilisée par le dashboard admin.

    Retourne un dict avec :
        - taux_moyen       : taux moyen de remplissage (%)
        - taux_max         : taux maximum
        - taux_min         : taux minimum
        - total_places     : total places disponibles tous trajets
        - total_reservees  : total places réservées
        - trajets_pleins   : nombre de trajets complets
        - trajets_vides    : nombre de trajets sans réservation
    """
    if not trajets:
        return {
            'taux_moyen'     : 0,
            'taux_max'       : 0,
            'taux_min'       : 0,
            'total_places'   : 0,
            'total_reservees': 0,
            'trajets_pleins' : 0,
            'trajets_vides'  : 0,
        }

    taux_list      = []
    total_places   = 0
    total_reservees = 0
    trajets_pleins = 0
    trajets_vides  = 0

    for trajet in trajets:
        taux = calculer_taux_remplissage(trajet)
        taux_list.append(taux)
        total_places    += trajet.places_totales
        places_prises    = trajet.places_totales - trajet.places_disponibles
        total_reservees += places_prises

        if trajet.places_disponibles == 0:
            trajets_pleins += 1
        if places_prises == 0:
            trajets_vides += 1

    return {
        'taux_moyen'     : round(sum(taux_list) / len(taux_list), 1),
        'taux_max'       : round(max(taux_list), 1),
        'taux_min'       : round(min(taux_list), 1),
        'total_places'   : total_places,
        'total_reservees': total_reservees,
        'trajets_pleins' : trajets_pleins,
        'trajets_vides'  : trajets_vides,
    }