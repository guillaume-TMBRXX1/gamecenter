"""Tests des checks avant le snap (moteur/presnap.py) : boîte montrée, lecture, audible, trompé, motion, chrono.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import unittest

from moteur import presnap as ps

QB = {"awareness": 80, "coverage_reading": 80}
SIT = {"down": 1, "distance": 10, "en_but": 60, "mode": None, "secondes": 200}


def checks(attaque="AXM", defense="CTX", intention="RUN", boite=8, n=400, qb=QB, sit=SIT, **kw):
    return [ps.check(attaque, defense, intention, qb, boite, sit, 123, i, **kw) for i in range(n)]


class Boite(unittest.TestCase):
    def test_presentations(self):
        self.assertEqual(ps.boite_montree(8, "COVER_3_SKY", "2-high rotating"), 7)
        self.assertEqual(ps.boite_montree(6, "SIM_PRESSURE", "mug"), 7)
        self.assertEqual(ps.boite_montree(6, "MUG_DROP", "double A-gap mug"), 8)
        self.assertEqual(ps.boite_montree(8, "MUG_BLITZ", "double A-gap mug"), 8)    # vraie pression : pas de mensonge
        self.assertEqual(ps.boite_montree(7, None, None), 7)
        self.assertEqual(ps.boite_montree(9, "MUG_DROP", "double A-gap mug"), 9)     # borné à 9

    def test_coquilles(self):
        self.assertEqual(ps.coquilles("ZONE", "COVER_3_SKY", "2-high rotating"), ("2-high", "1-high"))
        self.assertEqual(ps.coquilles("COVER_4", "MATCH_QUARTERS", "2-high"), ("2-high", "2-high"))
        self.assertEqual(ps.coquilles("BLITZ", "SEVEN_MAN_PRESSURE", "0-high"), ("0-high", "0-high"))

    def test_regard(self):
        self.assertEqual([ps.regard(b) for b in (5, 6, 7, 8, 9)], ["legere", "legere", "neutre", "chargee", "chargee"])


class Audible(unittest.TestCase):
    def test_deterministe(self):
        self.assertEqual(checks(n=50), checks(n=50))

    def test_course_contre_boite_chargee(self):
        r = checks(boite=8)
        a = [x for x in r if x["audible"]]
        self.assertTrue(a and all(x["audible"] == "PASS" for x in a))
        self.assertTrue(0.25 < len(a) / len(r) < 0.75, len(a))                     # AXM : grande liberté

    def test_rien_contre_boite_neutre(self):
        self.assertFalse(any(x["audible"] for x in checks(boite=7)))
        self.assertFalse(any(x["audible"] for x in checks(intention="PASS", boite=7)))

    def test_passe_contre_boite_legere(self):
        sit = dict(SIT, distance=4)
        a = [x for x in checks(intention="PASS", boite=6, sit=sit) if x["audible"]]
        self.assertTrue(a and all(x["audible"] == "RUN" for x in a))
        self.assertFalse(any(x["audible"] for x in checks(intention="PASS", boite=6, sit=dict(SIT, distance=9))))

    def test_profil_de_la_franchise(self):
        """Un profil, pas un niveau : à QB égal, l'identité décide de la fréquence."""
        haute = sum(bool(x["audible"]) for x in checks("PLS"))
        basse = sum(bool(x["audible"]) for x in checks("MNL"))
        self.assertGreater(haute, 3 * basse)

    def test_awareness(self):
        bon = sum(bool(x["audible"]) for x in checks(qb={"awareness": 90, "coverage_reading": 90}))
        moyen = sum(bool(x["audible"]) for x in checks(qb={"awareness": 74, "coverage_reading": 74}))
        self.assertGreater(bon, moyen)

    def test_situations_interdites(self):
        for sit in (dict(SIT, mode="clock"), dict(SIT, secondes=10), dict(SIT, down=3, distance=1),
                    dict(SIT, distance=1, en_but=2)):
            self.assertFalse(any(x["audible"] for x in checks(sit=sit, n=100)), sit)
        self.assertFalse(any(x["audible"] for x in checks(intention="PASS", boite=5,
                                                           sit=dict(SIT, distance=3, mode="hurry"), n=100)))


class Trompe(unittest.TestCase):
    def test_rotation_cachee(self):
        """Course contre une boîte de 8 montrée à 7 (le safety descend au snap) : le QB qui ne voit pas reste en
        course — audible manqué ; celui qui voit au travers peut changer."""
        r = checks(boite=8, paquet="COVER_3_SKY", presente="2-high rotating", famille="zone", deguisement=0.2)
        self.assertTrue(all(x["boite_montree"] == 7 for x in r))
        pas_vu = [x for x in r if x["vu"] is False]
        self.assertTrue(pas_vu and not any(x["audible"] for x in pas_vu))
        self.assertTrue(any(x["trompe"] == "manque" for x in pas_vu))
        self.assertTrue(any(x["audible"] for x in r if x["vu"]))
        self.assertFalse(any(x["trompe"] for x in r if x["vu"]))

    def test_pression_simulee(self):
        """Course contre une boîte de 7 montrée à 9 (mug) : le QB trompé passe en passe — mauvais audible."""
        r = checks(boite=7, paquet="MUG_DROP", presente="double A-gap mug", famille="zone", deguisement=0.35)
        mauvais = [x for x in r if x["trompe"] == "mauvais"]
        self.assertTrue(mauvais and all(x["audible"] == "PASS" and x["boite_lue"] == 9 for x in mauvais))

    def test_awareness_voit_au_travers(self):
        kw = dict(boite=8, paquet="COVER_3_SKY", presente="2-high rotating", famille="zone", deguisement=0.2)
        bon = sum(bool(x["vu"]) for x in checks(qb={"awareness": 92, "coverage_reading": 92}, **kw))
        moyen = sum(bool(x["vu"]) for x in checks(qb={"awareness": 72, "coverage_reading": 72}, **kw))
        self.assertGreater(bon, moyen)


class Motion(unittest.TestCase):
    def test_reponses(self):
        r = checks(boite=7, motion="JET", famille="zone", n=600)
        rep = {x["reponse"] for x in r}
        self.assertEqual(rep, {None, "roll", "bump"})
        self.assertTrue(all(x["boite_reelle"] == 8 for x in r if x["reponse"] == "roll"))
        self.assertTrue(all(x["boite_reelle"] == 7 for x in r if x["reponse"] != "roll"))
        homme = {x["reponse"] for x in checks(boite=7, motion="JET", famille="homme", n=600)}
        self.assertEqual(homme, {None, "roll", "lock"})
        self.assertFalse(any(x["reponse"] for x in checks(boite=7, motion=None, famille="zone")))

    def test_rotation_devoile(self):
        r = checks(boite=8, paquet="COVER_3_SKY", presente="2-high rotating", famille="zone", deguisement=0.3,
                   motion="JET", n=600)
        for x in r:
            if x["reponse"] in ("roll", "lock"):
                self.assertTrue(x["vu"])
                self.assertEqual(x["boite_montree"], x["boite_reelle"])


class Chrono(unittest.TestCase):
    def test_cout(self):
        self.assertEqual(ps.cout(None, None, 3), 0)
        self.assertEqual(ps.cout("PASS", None, 3), 2)
        self.assertEqual(ps.cout("PASS", "roll", 3), 3)
        self.assertEqual(ps.cout("PASS", None, 8), 1)            # il reste toujours 1 s au snap
        self.assertEqual(ps.cout("PASS", None, 9), 0)
        self.assertEqual(ps.cout("RUN", None, 3, mode="clock"), 0)
        self.assertEqual(ps.cout("RUN", "bump", None), 3)          # horloge arrêtée : le coût se voit à l'écran


if __name__ == "__main__":
    unittest.main()
