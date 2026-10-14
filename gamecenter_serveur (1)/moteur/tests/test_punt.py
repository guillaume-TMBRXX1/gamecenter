"""Tests du punt avec retour (moteur/punt.py).

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import collections
import random
import statistics
import unittest

from moteur import punt as pu


def serie(ligne=30, n=40000, graine=7, **kw):
    r = random.Random(graine)
    return [pu.punt(r, ligne, **kw) for _ in range(n)]


def parts(R):
    c = collections.Counter(x["issue"] for x in R)
    return {k: v / len(R) for k, v in c.items()}


class TestRepartition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.R = serie(30)                       # depuis sa ligne des 30 : punt normal

    def test_longueur_et_net(self):
        self.assertTrue(45 <= statistics.mean(x["longueur"] for x in self.R) <= 48)
        net = statistics.mean(70 - x["depart"] for x in self.R if not x["td"])
        self.assertTrue(40 <= net <= 44.5, net)

    def test_issues(self):
        p = parts(self.R)
        self.assertTrue(0.40 <= p["retour"] <= 0.55, p)
        self.assertTrue(0.30 <= p["fair_catch"] <= 0.42, p)
        self.assertTrue(0.05 <= p["sortie"] <= 0.12, p)

    def test_retours(self):
        ret = [x["retour"] for x in self.R if x["issue"] == "retour"]
        self.assertTrue(8 <= statistics.mean(ret) <= 11.5, statistics.mean(ret))
        td = sum(x["td"] for x in self.R) / len(self.R)
        self.assertTrue(0.001 <= td <= 0.007, td)

    def test_coherence(self):
        for x in self.serie_mixte():
            self.assertEqual(x["chute"] - x["longueur"] in (20, 30, 40, 50, 60), True)
            if x["issue"] == "touchback":
                self.assertEqual((x["depart"], x["retour"], x["td"]), (pu.TOUCHBACK, 0, False))
            elif x["td"]:
                self.assertEqual((x["issue"], x["depart"]), ("retour", 100))
                self.assertEqual(x["reception"] + x["retour"], 100)
            else:
                self.assertTrue(1 <= x["depart"] <= 99)
                self.assertEqual(x["depart"], x["reception"] + x["retour"])
                if x["issue"] != "retour":
                    self.assertEqual(x["retour"], 0)
                    self.assertTrue(x["reception"] >= 1)

    def serie_mixte(self):
        return [x for ligne in (20, 30, 40, 50, 60) for x in serie(ligne, n=4000)]


class TestPrecision(unittest.TestCase):
    def test_terrain_adverse(self):
        R = serie(60)                           # depuis la ligne des 40 adverse
        self.assertTrue(all(x["precision"] for x in R))
        self.assertFalse(any(x["precision"] for x in serie(30, n=2000)))
        p = parts(R)
        self.assertLess(p["retour"], 0.25)
        self.assertTrue(0.10 <= p["touchback"] <= 0.25, p)
        dedans = sum(x["issue"] != "touchback" and x["depart"] <= 20 for x in R) / len(R)
        self.assertGreater(dedans, 0.65)        # ballon pris ou arrêté dans les 20
        self.assertLess(statistics.mean(x["longueur"] for x in R), 36)


class TestNotes(unittest.TestCase):
    def test_punter_puissant_plus_loin(self):
        m = lambda R: statistics.mean(x["longueur"] for x in R)
        self.assertGreater(m(serie(puissance_punter=95)), m(serie(puissance_punter=65)) + 5)

    def test_retourneur_rapide_plus_loin(self):
        m = lambda R: statistics.mean(x["retour"] for x in R if x["issue"] == "retour" and not x["td"])
        self.assertGreater(m(serie(retourneur=90)), m(serie(retourneur=60)) + 2.5)
        self.assertGreater(m(serie(couverture=60)), m(serie(couverture=90)) + 2.5)

    def test_pas_de_td_en_prolongation(self):
        R = serie(20, td_possible=False)
        self.assertFalse(any(x["td"] for x in R))
        self.assertTrue(max(x["depart"] for x in R) <= 99)


class TestDeterminisme(unittest.TestCase):
    def test_flux_dedie(self):
        self.assertEqual(pu.tirer(42, 17, 30), pu.tirer(42, 17, 30))
        etat = random.getstate()
        pu.tirer(42, 18, 35, retourneur=80)
        self.assertEqual(random.getstate(), etat, "le hasard global ne doit pas être consommé")

    def test_note_retourneur(self):
        self.assertEqual(pu.note_retourneur(90, 80), 85.0)


if __name__ == "__main__":
    unittest.main()
