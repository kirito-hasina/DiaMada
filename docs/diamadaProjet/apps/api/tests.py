"""
apps/api/tests.py

Tests unitaires et d'intégration pour DiaMada.
Couvre : algorithme glouton, permissions, serializers, endpoints API.
"""
import heapq
from datetime import date, timedelta
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import MagicMock, patch

from apps.users.models import User, Passager, Agent, Chauffeur, AdminProfil
from apps.trajets.models import GareRoutiere, Vehicule, Trajet
from apps.reservations.models import Reservation, Embarquement
from apps.core.algorithms import (
    choisir_trajet_optimal,
    calculer_taux_remplissage,
    classer_trajets_par_remplissage,
    statistiques_remplissage,
)
from apps.api.permissions import IsPassager, IsAgent, IsChauffeur, IsAdmin


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════
def creer_user(username, role, password='test1234', **kwargs):
    user = User.objects.create_user(
        username=username, email=f"{username}@test.mg",
        nom='Test', prenom='User', role=role,
        password=password, **kwargs
    )
    return user

def creer_passager(username='passager1'):
    user = creer_user(username, 'passager')
    return Passager.objects.create(user=user)

def creer_agent(username='agent1'):
    user = creer_user(username, 'agent')
    return Agent.objects.create(user=user, matricule=f'AGT-{username}')

def creer_chauffeur(username='chauffeur1'):
    user = creer_user(username, 'chauffeur')
    return Chauffeur.objects.create(user=user, num_permis=f'MDG-{username}')

def creer_admin(username='admin1'):
    user = creer_user(username, 'admin', is_staff=True)
    return AdminProfil.objects.create(user=user)

def creer_gare(nom='Gare Test', ville='Tana'):
    return GareRoutiere.objects.create(nom=nom, ville=ville)

def creer_vehicule(immat='MG-TEST-1', capacite=15):
    return Vehicule.objects.create(immatriculation=immat, capacite=capacite)

def creer_trajet(gare_dep, gare_arr, vehicule, date_dep=None,
                 places_totales=15, places_dispo=15, prix=10000):
    if date_dep is None:
        date_dep = date.today() + timedelta(days=1)
    return Trajet.objects.create(
        gare_depart=gare_dep, gare_arrivee=gare_arr,
        vehicule=vehicule, date_depart=date_dep,
        heure_depart='06:00:00', prix=prix,
        places_totales=places_totales,
        places_disponibles=places_dispo,
        statut='planifie',
    )


# ═══════════════════════════════════════════════════════════
# 1. TESTS ALGORITHME GLOUTON
# ═══════════════════════════════════════════════════════════
class AlgorithmeGloutonTest(TestCase):
    """Tests unitaires de l'algorithme glouton et du Max-Heap."""

    def setUp(self):
        self.gare_dep = creer_gare('Gare Tana', 'Antananarivo')
        self.gare_arr = creer_gare('Gare Toama', 'Toamasina')
        self.vehicule1 = creer_vehicule('MG-001-T', 15)
        self.vehicule2 = creer_vehicule('MG-002-T', 12)
        self.vehicule3 = creer_vehicule('MG-003-T', 10)
        self.demain = date.today() + timedelta(days=1)

    def test_choisit_trajet_plus_rempli(self):
        """Doit choisir le trajet avec le taux de remplissage le plus élevé."""
        # Trajet A : 15 places, 10 prises → 66.7%
        t_a = creer_trajet(self.gare_dep, self.gare_arr, self.vehicule1,
                           self.demain, 15, 5)
        # Trajet B : 12 places, 3 prises → 25%
        t_b = creer_trajet(self.gare_dep, self.gare_arr, self.vehicule2,
                           self.demain, 12, 9)

        resultat = choisir_trajet_optimal(
            self.gare_dep.id, self.gare_arr.id, self.demain, 2
        )
        self.assertIsNotNone(resultat)
        self.assertEqual(resultat.id, t_a.id,
            "Doit choisir Trajet A (66.7%) plutôt que Trajet B (25%)")

    def test_elimine_trajet_places_insuffisantes(self):
        """Trajet avec 1 place dispo ne doit pas être choisi si on en demande 2."""
        t_presque_plein = creer_trajet(self.gare_dep, self.gare_arr,
                                       self.vehicule1, self.demain, 15, 1)
        t_disponible    = creer_trajet(self.gare_dep, self.gare_arr,
                                       self.vehicule2, self.demain, 12, 8)

        resultat = choisir_trajet_optimal(
            self.gare_dep.id, self.gare_arr.id, self.demain, 2
        )
        self.assertIsNotNone(resultat)
        self.assertNotEqual(resultat.id, t_presque_plein.id,
            "Ne doit pas choisir un trajet avec 1 place si on en demande 2")

    def test_retourne_none_si_aucun_trajet(self):
        """Retourne None si aucun trajet disponible."""
        resultat = choisir_trajet_optimal(
            self.gare_dep.id, self.gare_arr.id, self.demain, 5
        )
        self.assertIsNone(resultat)

    def test_retourne_none_si_places_insuffisantes(self):
        """Retourne None si toutes les places sont insuffisantes."""
        creer_trajet(self.gare_dep, self.gare_arr, self.vehicule1,
                     self.demain, 15, 1)  # 1 dispo

        resultat = choisir_trajet_optimal(
            self.gare_dep.id, self.gare_arr.id, self.demain, 5
        )
        self.assertIsNone(resultat)

    def test_ignore_trajets_annules_ou_termines(self):
        """Ne doit pas considérer les trajets non planifiés."""
        t_planifie = creer_trajet(self.gare_dep, self.gare_arr,
                                  self.vehicule1, self.demain, 15, 10)
        t_annule   = creer_trajet(self.gare_dep, self.gare_arr,
                                  self.vehicule2, self.demain, 12, 12)
        t_annule.statut = 'annule'
        t_annule.save()

        resultat = choisir_trajet_optimal(
            self.gare_dep.id, self.gare_arr.id, self.demain, 1
        )
        self.assertEqual(resultat.id, t_planifie.id)


class CalculsTauxRemplissageTest(TestCase):
    """Tests des fonctions de calcul de taux."""

    def setUp(self):
        self.gare1 = creer_gare('G1', 'Ville1')
        self.gare2 = creer_gare('G2', 'Ville2')
        self.veh   = creer_vehicule()

    def test_calculer_taux_remplissage(self):
        t = creer_trajet(self.gare1, self.gare2, self.veh,
                         places_totales=10, places_dispo=5)
        taux = calculer_taux_remplissage(t)
        self.assertEqual(taux, 50.0)

    def test_taux_zero_si_vide(self):
        t = creer_trajet(self.gare1, self.gare2, self.veh,
                         places_totales=10, places_dispo=10)
        self.assertEqual(calculer_taux_remplissage(t), 0.0)

    def test_taux_cent_si_plein(self):
        t = creer_trajet(self.gare1, self.gare2, self.veh,
                         places_totales=10, places_dispo=0)
        self.assertEqual(calculer_taux_remplissage(t), 100.0)

    def test_classer_par_remplissage(self):
        t1 = creer_trajet(self.gare1, self.gare2, creer_vehicule('MG-A'),
                          places_totales=10, places_dispo=8)   # 20%
        t2 = creer_trajet(self.gare1, self.gare2, creer_vehicule('MG-B'),
                          places_totales=10, places_dispo=2)   # 80%
        t3 = creer_trajet(self.gare1, self.gare2, creer_vehicule('MG-C'),
                          places_totales=10, places_dispo=5)   # 50%

        classement = classer_trajets_par_remplissage([t1, t2, t3])
        self.assertEqual(classement[0].id, t2.id)  # 80%
        self.assertEqual(classement[1].id, t3.id)  # 50%
        self.assertEqual(classement[2].id, t1.id)  # 20%

    def test_statistiques_globales(self):
        t1 = creer_trajet(self.gare1, self.gare2, creer_vehicule('MG-X'),
                          places_totales=10, places_dispo=0)   # 100% plein
        t2 = creer_trajet(self.gare1, self.gare2, creer_vehicule('MG-Y'),
                          places_totales=10, places_dispo=10)  # 0% vide

        stats = statistiques_remplissage([t1, t2])
        self.assertEqual(stats['taux_moyen'], 50.0)
        self.assertEqual(stats['taux_max'],   100.0)
        self.assertEqual(stats['taux_min'],   0.0)
        self.assertEqual(stats['trajets_pleins'], 1)
        self.assertEqual(stats['trajets_vides'],  1)
        self.assertEqual(stats['total_places'],   20)
        self.assertEqual(stats['total_reservees'],10)

    def test_statistiques_liste_vide(self):
        stats = statistiques_remplissage([])
        self.assertEqual(stats['taux_moyen'], 0)
        self.assertEqual(stats['total_places'], 0)


# ═══════════════════════════════════════════════════════════
# 2. TESTS PERMISSIONS
# ═══════════════════════════════════════════════════════════
class PermissionsTest(TestCase):
    """Tests des classes de permission."""

    def _make_request(self, role, authenticated=True):
        req = MagicMock()
        req.user = MagicMock()
        req.user.role = role
        req.user.is_authenticated = authenticated
        return req

    def test_is_passager(self):
        perm = IsPassager()
        view = MagicMock()
        self.assertTrue(perm.has_permission(self._make_request('passager'), view))
        self.assertFalse(perm.has_permission(self._make_request('admin'), view))
        self.assertFalse(perm.has_permission(self._make_request('agent'), view))
        self.assertFalse(perm.has_permission(self._make_request('passager', False), view))

    def test_is_agent(self):
        perm = IsAgent()
        view = MagicMock()
        self.assertTrue(perm.has_permission(self._make_request('agent'), view))
        self.assertFalse(perm.has_permission(self._make_request('passager'), view))
        self.assertFalse(perm.has_permission(self._make_request('chauffeur'), view))

    def test_is_chauffeur(self):
        perm = IsChauffeur()
        view = MagicMock()
        self.assertTrue(perm.has_permission(self._make_request('chauffeur'), view))
        self.assertFalse(perm.has_permission(self._make_request('admin'), view))

    def test_is_admin(self):
        perm = IsAdmin()
        view = MagicMock()
        self.assertTrue(perm.has_permission(self._make_request('admin'), view))
        self.assertFalse(perm.has_permission(self._make_request('chauffeur'), view))
        self.assertFalse(perm.has_permission(self._make_request('passager'), view))


# ═══════════════════════════════════════════════════════════
# 3. TESTS AUTH API
# ═══════════════════════════════════════════════════════════
class AuthAPITest(APITestCase):
    """Tests des endpoints d'authentification."""

    def test_register_passager(self):
        url = '/api/v1/auth/register/'
        data = {
            'username': 'jean', 'email': 'jean@test.mg',
            'nom': 'Rakoto', 'prenom': 'Jean',
            'role': 'passager', 'telephone': '+261340000001',
            'password': 'test1234', 'password_confirm': 'test1234',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['role'], 'passager')
        self.assertTrue(Passager.objects.filter(user__username='jean').exists())

    def test_register_chauffeur_sans_permis_echoue(self):
        url = '/api/v1/auth/register/'
        data = {
            'username': 'chauf1', 'email': 'chauf1@test.mg',
            'nom': 'Solo', 'prenom': 'Andry',
            'role': 'chauffeur', 'password': 'test1234',
            'password_confirm': 'test1234',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('num_permis', response.data)

    def test_register_mots_de_passe_differents(self):
        url = '/api/v1/auth/register/'
        data = {
            'username': 'user2', 'email': 'user2@test.mg',
            'nom': 'A', 'prenom': 'B', 'role': 'passager',
            'password': 'test1234', 'password_confirm': 'autrechose',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_retourne_token_et_role(self):
        creer_user('jean2', 'passager', 'test1234')
        url = '/api/v1/auth/login/'
        response = self.client.post(url, {
            'username': 'jean2', 'password': 'test1234'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertEqual(response.data['user']['role'], 'passager')

    def test_login_mauvais_mot_de_passe(self):
        creer_user('jean3', 'passager')
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'jean3', 'password': 'mauvais'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_sans_token(self):
        response = self.client.get('/api/v1/auth/me/')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


    def test_me_avec_token(self):
        passager = creer_passager('jean4')
        self.client.force_authenticate(user=passager.user)
        response = self.client.get('/api/v1/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['role'], 'passager')


# ═══════════════════════════════════════════════════════════
# 4. TESTS TRAJETS API
# ═══════════════════════════════════════════════════════════
class TrajetAPITest(APITestCase):

    def setUp(self):
        self.admin   = creer_admin('admin_t')
        self.passager = creer_passager('pass_t')
        self.gare1   = creer_gare('Gare Tana', 'Antananarivo')
        self.gare2   = creer_gare('Gare Toama', 'Toamasina')
        self.vehicule = creer_vehicule('MG-200-T')

    def test_liste_trajets_publique(self):
        """Sans auth, on peut voir les trajets planifiés."""
        creer_trajet(self.gare1, self.gare2, self.vehicule)
        response = self.client.get('/api/v1/trajets/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_creer_trajet_admin_ok(self):
        self.client.force_authenticate(user=self.admin.user)
        data = {
            'gare_depart': self.gare1.id,
            'gare_arrivee': self.gare2.id,
            'vehicule': self.vehicule.id,
            'date_depart': str(date.today() + timedelta(days=2)),
            'heure_depart': '07:00:00',
            'prix': 15000,
            'places_totales': 15,
            'places_disponibles': 15,
        }
        response = self.client.post('/api/v1/trajets/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_meme_gare_depart_arrivee_rejete(self):
        self.client.force_authenticate(user=self.admin.user)
        data = {
            'gare_depart': self.gare1.id,
            'gare_arrivee': self.gare1.id,  # même gare !
            'vehicule': self.vehicule.id,
            'date_depart': str(date.today() + timedelta(days=2)),
            'heure_depart': '07:00:00',
            'prix': 15000,
            'places_totales': 15,
            'places_disponibles': 15,
        }
        response = self.client.post('/api/v1/trajets/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ═══════════════════════════════════════════════════════════
# 5. TESTS RÉSERVATIONS
# ═══════════════════════════════════════════════════════════
class ReservationAPITest(APITestCase):

    def setUp(self):
        self.passager = creer_passager('pass_r')
        self.gare1    = creer_gare('G-Dep', 'Tana')
        self.gare2    = creer_gare('G-Arr', 'Toama')
        self.vehicule = creer_vehicule('MG-300-T')
        self.trajet   = creer_trajet(
            self.gare1, self.gare2, self.vehicule,
            places_totales=10, places_dispo=10, prix=15000
        )

    def test_reserver_en_ligne(self):
        self.client.force_authenticate(user=self.passager.user)
        response = self.client.post('/api/v1/reservations/', {
            'trajet': self.trajet.id,
            'nb_places': 2,
            'canal': 'web',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('code_billet', response.data)
        self.assertEqual(response.data['statut'], 'confirmee')
        self.assertEqual(float(response.data['prix_total']), 30000.0)

        # Vérifier décrément des places
        self.trajet.refresh_from_db()
        self.assertEqual(self.trajet.places_disponibles, 8)

    def test_reserver_sans_auth_refuse(self):
        response = self.client.post('/api/v1/reservations/', {
            'trajet': self.trajet.id, 'nb_places': 1,
        }, format='json')
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_reserver_plus_que_disponible_refuse(self):
        self.client.force_authenticate(user=self.passager.user)
        response = self.client.post('/api/v1/reservations/', {
            'trajet': self.trajet.id,
            'nb_places': 20,  # > 10 disponibles
            'canal': 'web',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_annuler_reservation(self):
        self.client.force_authenticate(user=self.passager.user)
        # Créer réservation
        resp = self.client.post('/api/v1/reservations/', {
            'trajet': self.trajet.id, 'nb_places': 2, 'canal': 'web',
        }, format='json')
        resa_id = resp.data['id']

        # Annuler
        resp_annul = self.client.post(f'/api/v1/reservations/{resa_id}/annuler/')
        self.assertEqual(resp_annul.status_code, status.HTTP_200_OK)

        # Vérifier restitution des places
        self.trajet.refresh_from_db()
        self.assertEqual(self.trajet.places_disponibles, 10)

    def test_code_billet_unique(self):
        """Deux réservations ne doivent pas avoir le même code_billet."""
        self.client.force_authenticate(user=self.passager.user)
        r1 = self.client.post('/api/v1/reservations/', {
            'trajet': self.trajet.id, 'nb_places': 1, 'canal': 'web',
        }, format='json')
        r2 = self.client.post('/api/v1/reservations/', {
            'trajet': self.trajet.id, 'nb_places': 1, 'canal': 'web',
        }, format='json')
        self.assertNotEqual(
            r1.data['code_billet'], r2.data['code_billet']
        )

    def test_passager_voit_seulement_ses_reservations(self):
        """Un passager ne doit pas voir les réservations des autres."""
        passager2 = creer_passager('pass_r2')
        # Réservation du passager 2
        self.client.force_authenticate(user=passager2.user)
        self.client.post('/api/v1/reservations/', {
            'trajet': self.trajet.id, 'nb_places': 1, 'canal': 'web',
        }, format='json')

        # Passager 1 ne doit pas voir la résa de passager 2
        self.client.force_authenticate(user=self.passager.user)
        response = self.client.get('/api/v1/reservations/')
        self.assertEqual(len(response.data), 0)

    def test_algo_glouton_mode2(self):
        """Mode 2 — gare_depart_id + gare_arrivee_id + date_depart."""
        self.client.force_authenticate(user=self.passager.user)
        response = self.client.post('/api/v1/reservations/', {
            'gare_depart_id' : self.gare1.id,
            'gare_arrivee_id': self.gare2.id,
            'date_depart'    : str(self.trajet.date_depart),
            'nb_places'      : 1,
            'canal'          : 'web',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['trajet_detail']['id'], self.trajet.id)


# ═══════════════════════════════════════════════════════════
# 6. TESTS AGENT
# ═══════════════════════════════════════════════════════════
class AgentAPITest(APITestCase):

    def setUp(self):
        self.agent    = creer_agent('agent_test')
        self.passager = creer_passager('pass_agent')
        self.gare1    = creer_gare('G-A', 'VilleA')
        self.gare2    = creer_gare('G-B', 'VilleB')
        self.vehicule = creer_vehicule('MG-400-T')
        self.trajet   = creer_trajet(
            self.gare1, self.gare2, self.vehicule,
            date_dep=date.today(), places_totales=10, places_dispo=10
        )
        # Créer une réservation confirmée
        self.reservation = Reservation.objects.create(
            passager=self.passager,
            trajet=self.trajet,
            nb_places=1, prix_total=10000,
            canal='web', statut='confirmee',
        )

    def test_verifier_billet_valide(self):
        self.client.force_authenticate(user=self.agent.user)
        response = self.client.post('/api/v1/agent/verifier-billet/', {
            'code_billet': self.reservation.code_billet
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valide'])

    def test_verifier_billet_inexistant(self):
        self.client.force_authenticate(user=self.agent.user)
        response = self.client.post('/api/v1/agent/verifier-billet/', {
            'code_billet': 'DMINEXISTANT'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['valide'])

    def test_valider_embarquement(self):
        self.client.force_authenticate(user=self.agent.user)
        response = self.client.post('/api/v1/agent/embarquement/', {
            'code_billet': self.reservation.code_billet
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Vérifier statut
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.statut, 'embarquee')

    def test_double_embarquement_refuse(self):
        """Impossible d'embarquer deux fois le même billet."""
        self.client.force_authenticate(user=self.agent.user)
        self.client.post('/api/v1/agent/embarquement/', {
            'code_billet': self.reservation.code_billet
        }, format='json')
        response = self.client.post('/api/v1/agent/embarquement/', {
            'code_billet': self.reservation.code_billet
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_passager_ne_peut_pas_verifier_billet(self):
        """Seul un agent peut vérifier un billet."""
        self.client.force_authenticate(user=self.passager.user)
        response = self.client.post('/api/v1/agent/verifier-billet/', {
            'code_billet': self.reservation.code_billet
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)