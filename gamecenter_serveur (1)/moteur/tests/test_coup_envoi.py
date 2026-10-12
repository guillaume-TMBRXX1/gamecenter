"""Tests du coup d'envoi avec retour (moteur/coup_envoi.py).

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import random
import statistics
import unittest

from moteur import coup_envoi as ce


def serie(n=40000, graine=7, **kw):
    r = random.Random(graine)
    return [ce.coup_envoi(r, **kw) for _ in range(n)]


class TestRepartition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.R = serie()

    def test_touchbacks(self):
        tb = sum(x["touchback"] for x in self.R) / len(self.R)
        self.assertTrue(0.35 <= tb <= 0.48, tb)
        self.assertTrue(all(x["depart"] == ce.TOUCHBACK and x["retour"] == 0 for x in self.R if x["touchback"]))

    def test_retours(self):
        ret = [x for x in self.R if not x["touchback"]]
        self.assertTrue(21 <= statistics.mean(x["retour"] for x in ret) <= 29)
        grands = sum(x["retour"] >= 40 for x in ret) / len(self.R)
        self.assertTrue(0.01 <= grands <= 0.05, grands)
        td = sum(x["td"] for x in self.R) / len(self.R)
        self.assertTrue(0.001 <= td <= 0.008, td)

    def test_depart_moyen_comme_avant(self):
        d = statistics.mean(x["depart"] for x in self.R if not x["td"])
        self.assertTrue(24 <= d <= 28, d)

    def test_coherence(self):
        for x in self.R:
            self.assertEqual(x["chute"], ce.LIGNE_TIR + x["longueur"])
            self.assertEqual(x["reception"], 100 - x["chute"])
            self.assertTrue(ce.LONGUEUR_BORNES[0] <= x["longueur"] <= ce.LONGUEUR_BORNES[1])
            if x["td"]:
                self.assertEqual(x["depart"], 100)
            else:
                self.assertTrue(ce.DEPART_MIN <= x["depart"] <= 99)
            if not x["touchback"]:
                self.assertEqual(x["depart"], x["reception"] + x["retour"])
            if x["chute"] - 100 > ce.FOND_EN_BUT:
                self.assertTrue(x["touchback"])


class TestNotes(unittest.TestCase):
    def test_kicker_puissant_plus_de_touchbacks(self):
        f = lambda R: sum(x["touchback"] for x in R) / len(R)
        self.assertGreater(f(serie(puissance_kicker=95)), f(serie(puissance_kicker=70)) + 0.1)

    def test_receveur_rapide_plus_loin(self):
        m = lambda R: statistics.mean(x["depart"] for x in R if not x["touchback"] and not x["td"])
        self.assertGreater(m(serie(receveur=90)), m(serie(receveur=60)) + 3)
        self.assertGreater(m(serie(couverture=60)), m(serie(couverture=90)) + 3)

    def test_pas_de_td_hors_drive(self):
        R = serie(td_possible=False)
        self.assertFalse(any(x["td"] for x in R))
        self.assertTrue(max(x["depart"] for x in R) <= 99)


class TestDeterminisme(unittest.TestCase):
    def test_flux_dedie(self):
        self.assertEqual(ce.tirer(42, 17), ce.tirer(42, 17))
        etat = random.getstate()
        ce.tirer(42, 18, receveur=80)
        self.assertEqual(random.getstate(), etat, "le hasard global ne doit pas être consommé")

    def test_note_receveur(self):
        self.assertEqual(ce.note_receveur(90, 80), 85.0)


if __name__ == "__main__":
    unittest.main()
