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

    def test_prudence(self):
        # 17/10/2026 (35 % des 4es essais joués, trop) : à 0-0, un coordinateur moyen punte le 4e et 1 dans son camp et
        # prend les 3 points au 4e et 2 aux 8 adverses ; seul l'agressif joue
        for args in ((60, 1, 0, 1, 600), (8, 2, 0, 2, 500)):
            self.assertNotEqual(q4(*args, quart_secondes=900, agressivite=0.59)["choix"], "JOUER", args)
            self.assertEqual(q4(*args, quart_secondes=900, agressivite=1.0)["choix"], "JOUER", args)

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
        # gagné : le coordinateur garde sa règle (garbage time) ; perdu : on tente sa chance, même le plus prudent
        self.assertIsNone(q4(80, 2, 24, 4, 400, quart_secondes=900))
        self.assertIsNone(q4(60, 2, 14, 4, 90, quart_secondes=900))
        self.assertEqual(q4(58, 10, -27, 4, 210, quart_secondes=900, agressivite=0.0)["choix"], "JOUER")

    def test_situation(self):
        # menée en fin de match : la prudence d'identité s'efface — même le plus prudent joue
        self.assertEqual(q4(60, 2, -2, 4, 90, quart_secondes=900, agressivite=0.0)["choix"], "JOUER")
        self.assertEqual(q4(60, 6, -14, 4, 180, quart_secondes=900, agressivite=0.0)["choix"], "JOUER")
        # même situation au 1er quart-temps : le prudent punte
        self.assertEqual(q4(60, 2, -2, 1, 600, quart_secondes=900, agressivite=0.0)["choix"], "PUNT")
        # mène de 2 à 1:30, 4e et 6 aux 30 adverses : les 3 points (sauf le plus agressif)
        self.assertEqual(q4(30, 6, 2, 4, 90, quart_secondes=900, agressivite=0.5)["choix"], "FG")
        # fin de Q2 dans ses 4 : punt, jamais un 4e et 9 joué
        for a in (0.0, 1.0):
            self.assertEqual(q4(96, 9, 1, 2, 25, quart_secondes=900, agressivite=a)["choix"], "PUNT")
        # prolongation, menée de 3 (dernière possession) : on joue le 4e et 4 au milieu du terrain
        self.assertEqual(q4(50, 4, -3, 5, 400, quart_secondes=900, agressivite=0.0)["choix"], "JOUER")

    def test_echelle_du_quart(self):
        # même situation (même part du match) avec des quarts-temps de 3 et de 15 minutes : même décision
        for args in ((50, 1, 0, 1), (30, 8, 0, 2), (65, 4, -3, 3)):
            a = q4(*args, 600, quart_secondes=900)
            b = q4(*args, 120, quart_secondes=180, duree_action=6 * 180 / 900)
            self.assertEqual(a["choix"], b["choix"], args)


class TestTexte(unittest.TestCase):
    def test_texte_wp(self):
        self.assertEqual(vl.texte_wp("go", .554, "punt", .4954), "go 55% vs punt 50% win prob.")
        self.assertEqual(vl.texte_wp("go", .926, "punt", .9294), "go 92.6% vs punt 92.9% win prob.")
        self.assertEqual(vl.texte_wp("go", .9256, "punt", .9256), "go ≈ punt 93% win prob.")
        self.assertEqual(vl.texte_wp("go", .0144, "field goal", .0006), "go 1% vs field goal <1% win prob.")


if __name__ == "__main__":
    unittest.main()
