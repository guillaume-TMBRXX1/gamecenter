"""Tests de la valeur des décisions (moteur/valeur.py) : points attendus, probabilité de victoire, 4e essai.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import unittest

from moteur import valeur as vl
from moteur.valeur import quatrieme_essai as q4


class TestTables(unittest.TestCase):
    def test_points_attendus(self):
        # plus on est près de l'en-but, plus un 1er essai vaut de points ; bornes
        eps = [vl.points_attendus(x) for x in range(1, 100)]
        self.assertTrue(all(a >= b for a, b in zip(eps, eps[1:])))
        self.assertGreater(vl.points_attendus(5), 6)
        self.assertLess(vl.points_attendus(95), 0.5)

    def test_conversion(self):
        ps = [vl.conversion(d) for d in range(1, 16)]
        self.assertTrue(all(a >= b for a, b in zip(ps, ps[1:])))
        self.assertGreater(vl.conversion(1, ecart_unites=10), vl.conversion(1))
        self.assertLess(vl.conversion(1, ecart_unites=-10), vl.conversion(1))

    def test_punt(self):
        # punt depuis ses 20 : l'adversaire part loin ; depuis le milieu : près de son en-but
        self.assertLess(vl.depart_apres_punt(80), 70)
        self.assertGreater(vl.depart_apres_punt(50), 80)


class TestProbabiliteVictoire(unittest.TestCase):
    def test_bornes_et_sens(self):
        p = vl.probabilite_victoire
        self.assertAlmostEqual(p(0, 1.0), 0.5, places=6)
        self.assertGreater(p(7, 0.5), p(3, 0.5))
        self.assertGreater(p(3, 0.1), p(3, 0.9))                     # même avance, moins de temps : plus sûr
        self.assertGreater(p(0, 0.5, en_but=20), p(0, 0.5, en_but=80))  # le ballon près de l'en-but vaut des points
        self.assertGreater(p(0, 1.0, avantage=7), 0.6)
        self.assertGreater(p(21, 0.05), 0.999)

    def test_ecart_type_mesure(self):
        # 13,2 points sur un match, ≈ 10 à mi-match, ≈ 5,5 au dernier dixième (mesures du moteur)
        sd = lambda part: vl._loi(0, part, 0, 0)[1]
        self.assertAlmostEqual(sd(1.0), 13.2, places=1)
        self.assertTrue(9.5 < sd(0.5) < 10.6)
        self.assertTrue(5.0 < sd(0.1) < 6.0)


class TestQuatriemeEssai(unittest.TestCase):
    def test_deterministe_et_complet(self):
        d = q4(55, 2, 0, 2, 500, quart_secondes=900)
        self.assertEqual(d, q4(55, 2, 0, 2, 500, quart_secondes=900))
        self.assertIn(d["choix"], ("JOUER", "FG", "PUNT"))
        self.assertEqual(set(d["wp"]), {"JOUER", "PUNT"})            # FG de 72 yards : hors de portée
        self.assertTrue(d["raison"])

    def test_identite(self):
        # 4e et 1 au milieu du terrain : le prudent punte, l'agressif joue
        self.assertEqual(q4(50, 1, 0, 1, 600, quart_secondes=900, agressivite=0.0)["choix"], "PUNT")
        self.assertEqual(q4(50, 1, 0, 1, 600, quart_secondes=900, agressivite=1.0)["choix"], "JOUER")
        # 4e et 8 aux 30 adverses : field goal sauf pour le plus agressif
        self.assertEqual(q4(30, 8, 0, 1, 700, quart_secondes=900, agressivite=0.5)["choix"], "FG")

    def test_bon_sens(self):
        # 4e et 15 dans son camp, 0-0 : punt pour tout le monde
        for a in (0.0, 0.5, 1.0):
            self.assertEqual(q4(75, 15, 0, 1, 700, quart_secondes=900, agressivite=a)["choix"], "PUNT")
        # 4e et 2 aux 25 adverses : jamais de punt
        for a in (0.0, 0.5, 1.0):
            self.assertNotEqual(q4(25, 2, 0, 2, 400, quart_secondes=900, agressivite=a)["choix"], "PUNT")
        # mené de 4 à 2:00, 4e et 6 aux 20 : le field goal ne sert à rien
        self.assertEqual(q4(20, 6, -4, 4, 120, quart_secondes=900, agressivite=0.0)["choix"], "JOUER")
        # mène de 6 à 1:00, 4e et 7 dans son camp : punt, même pour l'agressif
        self.assertEqual(q4(65, 7, 6, 4, 60, quart_secondes=900, agressivite=1.0)["choix"], "PUNT")
        # mené de 3 dans les dernières secondes, 4e et 10 aux 15 : field goal
        self.assertEqual(q4(15, 10, -3, 4, 8, quart_secondes=900, agressivite=0.5)["choix"], "FG")

    def test_portee_du_coordinateur(self):
        d = q4(36, 9, 0, 1, 600, quart_secondes=900, fg_max=50)    # 53 yards, portée de 50
        self.assertNotIn("FG", d["wp"])

    def test_match_plie(self):
        self.assertIsNone(q4(80, 2, 24, 4, 400, quart_secondes=900))
        self.assertIsNone(q4(80, 2, -28, 4, 200, quart_secondes=900))

    def test_echelle_du_quart(self):
        # même situation (même part du match) avec des quarts-temps de 3 et de 15 minutes : même décision
        for args in ((50, 1, 0, 1), (30, 8, 0, 2), (65, 4, -3, 3)):
            a = q4(*args, 600, quart_secondes=900)
            b = q4(*args, 120, quart_secondes=180, duree_action=6 * 180 / 900)
            self.assertEqual(a["choix"], b["choix"], args)


if __name__ == "__main__":
    unittest.main()
