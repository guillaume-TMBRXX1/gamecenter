"""Tests de la transformation après un touchdown (moteur/transformation.py) : point après touchdown ou 2 points.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import random
import unittest

from moteur import transformation as tr


class TestProbabilites(unittest.TestCase):
    def test_pat(self):
        self.assertEqual(tr.probabilite_pat(), tr.P_PAT)
        self.assertGreater(tr.probabilite_pat(95), tr.probabilite_pat(70))
        self.assertLessEqual(tr.probabilite_pat(200), tr.PAT_BORNES[1])
        self.assertGreaterEqual(tr.probabilite_pat(0), tr.PAT_BORNES[0])

    def test_deux_points(self):
        self.assertEqual(tr.probabilite_2pt(), tr.P_2PT)
        self.assertGreater(tr.probabilite_2pt(8), tr.probabilite_2pt(-8))
        self.assertEqual(tr.probabilite_2pt(100), tr.DEUX_BORNES[1])
        self.assertEqual(tr.probabilite_2pt(-100), tr.DEUX_BORNES[0])

    def test_agressivite(self):
        self.assertEqual(tr.agressivite(1, 62), 0.0)
        self.assertEqual(tr.agressivite(5, 30), 1.0)
        self.assertLess(tr.agressivite(2, 45), tr.agressivite(3, 40))


class TestChoix(unittest.TestCase):
    def test_tableau_au_4e_quart(self):
        for ecart in tr.TABLEAU:
            self.assertEqual(tr.decider(ecart, 4, 300)["choix"], "2PT", ecart)
            self.assertEqual(tr.decider(ecart, 5, 300)["choix"], "2PT", ecart)       # prolongation
        for ecart in (-1, 0, 2, 3, 6, 7, -3, -4, -6, -7, -8, 20):
            self.assertEqual(tr.decider(ecart, 4, 300)["choix"], "PAT", ecart)
        self.assertEqual(tr.decider(-2, 4, 300)["raison"], "égaliser")

    def test_premiere_mi_temps_point_apres_touchdown(self):
        for ecart in tr.TABLEAU:
            self.assertEqual(tr.decider(ecart, 1, 100, agressivite_oc=1.0)["choix"], "PAT")
            self.assertEqual(tr.decider(ecart, 2, 100, agressivite_oc=1.0)["choix"], "PAT")

    def test_3e_quart_selon_le_coordinateur(self):
        self.assertEqual(tr.decider(-2, 3, 100, agressivite_oc=0.2)["choix"], "PAT")
        self.assertEqual(tr.decider(-2, 3, 100, agressivite_oc=tr.AGRESSIF_Q3)["choix"], "2PT")

    def test_hors_tableau_agressif(self):
        n = 20000
        for agr in (0.0, 1.0):
            rng = random.Random(5)
            k = sum(tr.decider(0, 1, 100, agr, rng)["choix"] == "2PT" for _ in range(n))
            self.assertAlmostEqual(k / n, tr.BASE_2PT * agr, delta=0.006)

    def test_fin_de_match(self):
        self.assertIsNone(tr.decider(3, 4, 0)["choix"])          # touchdown gagnant sur la dernière action
        self.assertIsNone(tr.decider(1, 5, 0)["choix"])
        self.assertEqual(tr.decider(0, 4, 0)["choix"], "PAT")      # égalité : le point donne la victoire
        self.assertEqual(tr.decider(-2, 4, 0)["choix"], "2PT")     # mené de 2 : égaliser
        self.assertEqual(tr.decider(3, 2, 0)["choix"], "PAT")      # fin de mi-temps : on transforme


class TestResultat(unittest.TestCase):
    def test_taux(self):
        n = 20000
        rng = random.Random(11)
        pat = sum(tr.resoudre("PAT", rng)["reussie"] for _ in range(n)) / n
        deux = [tr.resoudre("2PT", rng) for _ in range(n)]
        self.assertAlmostEqual(pat, tr.P_PAT, delta=0.006)
        self.assertAlmostEqual(sum(r["reussie"] for r in deux) / n, tr.P_2PT, delta=0.012)
        self.assertAlmostEqual(sum(r["jeu"] == "PASS" for r in deux) / n, tr.PART_PASSE, delta=0.012)

    def test_points(self):
        rng = random.Random(1)
        for _ in range(200):
            r = tr.resoudre("PAT", rng)
            self.assertEqual(r["points"], 1 if r["reussie"] else 0)
            self.assertEqual(r["jeu"], "KICK")
            r = tr.resoudre("2PT", rng)
            self.assertEqual(r["points"], 2 if r["reussie"] else 0)
            self.assertIn(r["jeu"], ("RUN", "PASS"))
        with self.assertRaises(ValueError):
            tr.resoudre("FG", rng)

    def test_deterministe_et_flux_dedie(self):
        a = tr.transformation(-2, 4, 120, 77, 130, 0.4, 85, 3)
        self.assertEqual(a, tr.transformation(-2, 4, 120, 77, 130, 0.4, 85, 3))
        self.assertEqual(a["choix"], "2PT")
        self.assertIsNone(tr.transformation(5, 4, 0, 77, 130))
        etat = random.getstate()
        tr.transformation(0, 1, 100, 77, 12)
        self.assertEqual(random.getstate(), etat, "le hasard global ne doit pas être consommé")


if __name__ == "__main__":
    unittest.main()
