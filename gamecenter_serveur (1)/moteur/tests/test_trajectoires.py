"""Trajectoires du moteur, palier 1 : les passes (moteur/trajectoires.py).

  Forme       play.geo compact : chaque receveur (rôle, séparation en yards, statut, défenseur, bust), lancer, couverture
  Fidélité    statut et défenseur = ceux de l'état après le snap ; séparation monotone ; seuils cohérents
  Neutralité  geo_passe ne tire rien : decider_passe donne la même décision avec ou sans lui (même flux)

    python -m unittest moteur.tests.test_trajectoires        (depuis « gamecenter_serveur (1) »)
"""
import unittest

import moteur
from moteur import reaction_defensive as RD
from moteur import trajectoires as T


def _joueur(i, **notes):
    r = {"speed": 82, "route_running": 78, "acceleration": 80, "hands": 76, "coverage": 76, "awareness": 74}
    r.update(notes)
    return {"id": i, "name": i, "ratings": r}


RECEVEURS = {"WR1": _joueur("A_WR1", route_running=88), "WR2": _joueur("A_WR2"), "WR3": _joueur("A_WR3"),
             "TE": _joueur("A_TE1"), "RB": _joueur("A_RB1")}
DEFENSEURS = {"CB1": _joueur("B_CB1"), "CB2": _joueur("B_CB2"), "CB3": _joueur("B_CB3"), "S1": _joueur("B_S1"),
              "S2": _joueur("B_S2"), "LB1": _joueur("B_LB1"), "LB2": _joueur("B_LB2")}


def _passe(n, concept_def="COVER_3"):
    return moteur.decider_passe("STICK", "TRIPS", concept_def, RECEVEURS, DEFENSEURS, _joueur("A_QB1"), 1, 42, n)


class Forme(unittest.TestCase):
    def test_une_passe(self):
        _, etat, d = _passe(7)
        g = T.geo_passe(etat, d)
        self.assertEqual(T.controler(g), [])
        self.assertEqual(g["v"], T.VERSION)
        self.assertEqual({r[0] for r in g["rec"]}, set(etat.receveurs))
        self.assertEqual(g["cov"], etat.couverture)
        self.assertEqual(g["tt"], round(d.temps_lancer, 2))
        self.assertEqual(g["tgt"], d.cible or None)

    def test_ordre_stable(self):
        _, etat, d = _passe(3)
        roles = [r[0] for r in T.geo_passe(etat, d)["rec"]]
        self.assertEqual(roles, [r for r in T.ORDRE if r in roles] + sorted(r for r in roles if r not in T.ORDRE))

    def test_dict_ou_objet(self):
        _, etat, d = _passe(11)
        self.assertEqual(T.geo_passe(etat, d), T.geo_passe(etat.to_dict(), dict(d.__dict__)))


class Fidelite(unittest.TestCase):
    def test_statuts_et_defenseurs_du_moteur(self):
        for n in range(40):
            _, etat, d = _passe(n, "MAN" if n % 2 else "COVER_2")
            for role, sep, st, cov, bust in T.geo_passe(etat, d)["rec"]:
                e = etat.receveurs[role]
                self.assertEqual(st, T.STATUTS[e.statut])
                self.assertEqual(cov, e.couvreur_id or None)
                self.assertEqual(bust, 1 if e.bust else 0)

    def test_seuils_d_affichage(self):
        self.assertGreaterEqual(T.separation_yards(RD.SEUIL_LIBRE, RD.LIBRE), 3.0)
        self.assertLess(T.separation_yards(RD.SEUIL_LIBRE - 0.01, RD.SERRE), 3.0)
        self.assertEqual(T.separation_yards(RD.SEUIL_SERRE, RD.SERRE), 1.6)
        self.assertLess(T.separation_yards(-0.01, RD.COUVERT), 1.6)
        self.assertEqual(T.separation_yards(5, RD.DOUBLE), T.SEP_DOUBLE)
        self.assertEqual(T.separation_yards(-9, RD.COUVERT), T.SEP_MIN)
        self.assertEqual(T.separation_yards(9, RD.LIBRE), T.SEP_MAX)

    def test_monotone(self):
        v = [T.separation_yards(p / 10, RD.SERRE) for p in range(-20, 40)]
        self.assertEqual(v, sorted(v))


class Neutralite(unittest.TestCase):
    def test_aucun_tirage(self):
        a = _passe(5)
        T.geo_passe(a[1], a[2])
        b = _passe(5)
        self.assertEqual(a[2].__dict__, b[2].__dict__)
        self.assertEqual(a[1].to_dict(), b[1].to_dict())

    def test_controle_detecte(self):
        _, etat, d = _passe(2)
        g = T.geo_passe(etat, d)
        g["rec"].append(list(g["rec"][0]))
        self.assertIn("receveur en double", T.controler(g))
        self.assertEqual(T.controler({"v": "x"}), ["version ou type"])


if __name__ == "__main__":
    unittest.main()
