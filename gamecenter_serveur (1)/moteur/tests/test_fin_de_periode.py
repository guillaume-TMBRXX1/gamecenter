"""Tests de la décision de fin de période (moteur/fin_de_periode.py) : field goal ou continuer, fin du Q2 et du Q4.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import unittest

from moteur import fin_de_periode as fp
from moteur.fin_de_periode import decider


class TestFenetre(unittest.TestCase):
    def test_hors_fenetre(self):
        self.assertIsNone(decider(1, 5, 1, 10, 20, 0))
        self.assertIsNone(decider(3, 5, 1, 10, 20, 0))
        self.assertIsNone(decider(5, 5, 1, 10, 20, 0))              # prolongation
        self.assertIsNone(decider(2, fp.FENETRE + 1, 1, 10, 20, 0))
        self.assertIsNone(decider(4, 0, 1, 10, 20, 0))

    def test_deterministe(self):
        self.assertEqual(decider(4, 9, 2, 7, 22, -2), decider(4, 9, 2, 7, 22, -2))


class TestChoix(unittest.TestCase):
    def test_dernieres_secondes_q2(self):
        d = decider(2, 3, 1, 10, 20, 0)
        self.assertEqual(d["choix"], "FG")
        self.assertEqual(d["objectif"], "points attendus")

    def test_mene_de_2_ou_3(self):
        for ecart in (-1, -2, -3):
            for essai in (1, 2, 3):
                self.assertEqual(decider(4, 3, essai, 10, 20, ecart)["choix"], "FG", (ecart, essai))
        self.assertIn("égalisent", decider(4, 3, 1, 10, 20, -3)["raison"])

    def test_mene_de_4_ou_plus(self):
        for ecart in (-4, -5, -8):
            d = decider(4, 3, 1, 10, 20, ecart)
            self.assertEqual(d["choix"], "JOUER")
            self.assertIn("touchdown", d["raison"])

    def test_temps_de_s_approcher(self):
        # 40 s à la ligne des 30 : il reste le temps de plusieurs actions — pas de field goal au 1er essai
        self.assertEqual(decider(2, 40, 1, 10, 30, 0)["choix"], "JOUER")
        self.assertEqual(decider(4, 40, 1, 10, 30, -2)["choix"], "JOUER")

    def test_plus_le_temps_presse_plus_le_fg(self):
        """Même situation, horloge qui descend : le field goal finit par l'emporter (et ne repart pas)."""
        choix = [decider(4, s, 1, 10, 25, -2)["choix"] for s in range(45, 0, -1)]
        premier = choix.index("FG")
        self.assertTrue(all(c == "FG" for c in choix[premier:]), choix)
        self.assertGreater(premier, 0)

    def test_hors_de_portee(self):
        d = decider(4, 3, 1, 10, 60, -2)                         # 77 yards
        self.assertEqual(d["choix"], "JOUER")
        self.assertIsNone(d["fg"])

    def test_kicker(self):
        # 62 yards : un bon kicker tente, un kicker faible est hors de portée
        self.assertEqual(decider(4, 3, 2, 10, 45, -1, special_teams_rating=85)["choix"], "FG")
        self.assertIsNone(decider(4, 3, 2, 10, 45, -1, special_teams_rating=50)["fg"])

    def test_quatrieme_essai(self):
        # 4e & 8 à la ligne des 20, 30 s, mené de 2 : les 3 points ; mené de 5 : on joue
        self.assertEqual(decider(4, 30, 4, 8, 20, -2)["choix"], "FG")
        self.assertEqual(decider(4, 30, 4, 8, 20, -5)["choix"], "JOUER")

    def test_valeurs_bornees(self):
        for args in ((2, 30, 1, 10, 5, 0), (4, 30, 2, 5, 15, 3), (4, 10, 1, 10, 35, -7)):
            d = decider(*args)
            hi = 7 if args[0] == 2 else 1
            self.assertLessEqual(d["jouer"], hi + 1e-9)
            self.assertGreaterEqual(d["jouer"], 0)

    def test_attaque_plus_forte_joue_plus(self):
        """Une attaque nettement supérieure à la défense a plus de chances de marquer : elle joue plus longtemps."""
        fort = sum(decider(2, s, 1, 10, 12, 0, ecart_unites=12)["choix"] == "JOUER" for s in range(1, 46))
        faible = sum(decider(2, s, 1, 10, 12, 0, ecart_unites=-12)["choix"] == "JOUER" for s in range(1, 46))
        self.assertGreater(fort, faible)

    def test_probabilite_fg(self):
        self.assertEqual(fp.probabilite_fg(37, 75), 0.92)
        self.assertEqual(fp.probabilite_fg(55, 85), 0.75)


if __name__ == "__main__":
    unittest.main()
