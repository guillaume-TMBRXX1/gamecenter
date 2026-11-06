"""Causal léger, bloc 2 : la course après la réception (moteur/course_spatiale.py, apres_reception).

  Réception   au bout de la route, jamais plus loin que les yards déjà tirés
  Notes       un receveur rapide gagne plus ; une défense rapide qui plaque bien en concède moins ; un receveur libre
              gagne plus qu'un receveur couvert de près
  Fins        touche, en-but (touchdown = les yards jusqu'à l'en-but), plaqueur = un des défenseurs
  Hasard      flux dédié : mêmes graine et action -> même réception ; bloc 1 inchangé

    python -m unittest moteur.tests.test_reception_spatiale        (depuis « gamecenter_serveur (1) »)
"""
import statistics
import unittest

from moteur import course_spatiale as CS


def _defense(tackling=78, speed=84):
    out = []
    for k, pos in enumerate(("EDGE", "EDGE", "DT", "DT", "LB", "LB", "LB", "S", "S", "CB", "CB")):
        r = {"tackling": tackling}
        if pos not in ("EDGE", "DT"):
            r["speed"] = speed
        out.append({"id": f"D{k}", "pos": pos, "ratings": r})
    return out


def _receveur(speed=88):
    return {"pos": "WR", "ratings": {"speed": speed, "acceleration": speed, "route_running": 82, "catching": 80}}


def _serie(rec, defense, air=6.5, t_pre=9, sep=2.0, n=500, but=70):
    return [CS.apres_reception(rec, defense, air, t_pre, "WR1", "INSIDE", 3.6, "D9", sep, but, 5, k) for k in range(n)]


class Reception(unittest.TestCase):
    def test_jamais_plus_loin_que_les_yards_tires(self):
        for r in _serie(_receveur(), _defense(), air=11.5, t_pre=4, n=200):
            self.assertLessEqual(r["air"], 4.0)

    def test_au_bout_de_la_route(self):
        court = statistics.mean(r["air"] for r in _serie(_receveur(), _defense(), air=4.0, t_pre=30))
        long_ = statistics.mean(r["air"] for r in _serie(_receveur(), _defense(), air=20.0, t_pre=30))
        self.assertLess(court, long_ - 10)


class Notes(unittest.TestCase):
    def test_receveur_rapide(self):
        vite = statistics.mean(r["yards"] for r in _serie(_receveur(96), _defense()))
        lent = statistics.mean(r["yards"] for r in _serie(_receveur(72), _defense()))
        self.assertGreater(vite, lent)

    def test_defense(self):
        dure = statistics.mean(r["yards"] for r in _serie(_receveur(), _defense(tackling=92, speed=92)))
        tendre = statistics.mean(r["yards"] for r in _serie(_receveur(), _defense(tackling=62, speed=74)))
        self.assertLess(dure, tendre)

    def test_separation(self):
        libre = statistics.mean(r["apres"] for r in _serie(_receveur(), _defense(), sep=6.0))
        serre = statistics.mean(r["apres"] for r in _serie(_receveur(), _defense(), sep=0.6))
        self.assertGreater(libre, serre)


class Fins(unittest.TestCase):
    def test_issues_coherentes(self):
        ids = {d["id"] for d in _defense()}
        R = _serie(_receveur(96), _defense(tackling=60, speed=72), air=6.5, t_pre=9, sep=6.0, but=14)
        for r in R:
            self.assertLessEqual(r["yards"], 14)
            if r["td"]:
                self.assertEqual(r["yards"], 14)
                self.assertIsNone(r["plaqueur"])
            if r["plaqueur"]:
                self.assertIn(r["plaqueur"], ids)
        self.assertTrue(any(r["td"] for r in R))


class Hasard(unittest.TestCase):
    def test_deterministe(self):
        a = CS.apres_reception(_receveur(), _defense(), 6.5, 9, "WR2", "OUTSIDE", 4.8, "D10", 2.2, 60, 11, 42, trace=True)
        b = CS.apres_reception(_receveur(), _defense(), 6.5, 9, "WR2", "OUTSIDE", 4.8, "D10", 2.2, 60, 11, 42, trace=True)
        self.assertEqual(a, b)

    def test_flux_propre(self):
        """Le flux de la réception n'est pas celui de la course : mêmes graine et action, tirages différents."""
        a = [CS.apres_reception(_receveur(), _defense(), 6.5, 9, "WR1", "INSIDE", 3.6, "D9", 2.0, 60, 11, k)["yards"]
             for k in range(40)]
        self.assertGreater(len(set(a)), 3)


if __name__ == "__main__":
    unittest.main()
