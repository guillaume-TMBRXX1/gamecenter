"""Causal léger, bloc 4 : la poche (moteur/poche_spatiale.py) et son branchement (moteur.poche, decider_passe).

  Duels       un meilleur rusher arrive plus tôt ; un blitzeur libre arrive vite ; un DT doublé arrive plus tard
  Poche       avec les instants simulés, le premier arrivé est le duel perdu, les autres cèdent à leur instant
  Hasard      flux dédié : mêmes graine et action -> mêmes instants
  Moteur      sans SIMULATION, la poche d'avant (mêmes duels, même temps)

    python -m unittest moteur.tests.test_poche_spatiale        (depuis « gamecenter_serveur (1) »)
"""
import random
import statistics
import unittest

from moteur import poche as PO
from moteur import poche_spatiale as PS


def _j(pos, **r):
    return {"id": pos + str(sorted(r.items())), "pos": pos, "ratings": r}


LIGNE = {k: _j(k, pass_block=78, strength=80) for k in ("LT", "LG", "C", "RG", "RT")}


def _rush(edge=80, dt=78):
    return {"EDGE": [_j("EDGE", pass_rush=edge, strength=80), _j("EDGE", pass_rush=edge, strength=79)],
            "DT": [_j("DT", pass_rush=dt, strength=82), _j("DT", pass_rush=dt, strength=81)],
            "LB": [_j("LB", speed=82), _j("LB", speed=80)], "S": [_j("S", speed=86)], "CB": []}


def _tmin(rush, n=4, k=500):
    D = PO.affecter(LIGNE, rush, n)
    return statistics.mean(min(PS.simuler(D, 1, i, n)[0]) for i in range(k))


class Duels(unittest.TestCase):
    def test_meilleur_rusher(self):
        self.assertLess(_tmin(_rush(edge=95)), _tmin(_rush(edge=68)))

    def test_libre_et_double(self):
        rng = random.Random(1)
        libre = {"rusher": _j("LB", speed=85), "bloqueur": None, "type": "interior", "marge": 15.0, "libre": True}
        engage = {"rusher": _j("DT", pass_rush=78), "bloqueur": _j("RG"), "type": "interior", "marge": 0.0, "libre": False}
        double = dict(engage, marge=-9.0, double=True)
        t = {k: statistics.mean(PS.duel(d, rng) for _ in range(800)) for k, d in (("libre", libre), ("engage", engage),
                                                                                  ("double", double))}
        self.assertLess(t["libre"], t["engage"])
        self.assertLess(t["engage"], t["double"])


class Poche(unittest.TestCase):
    def test_premier_arrive_perd_le_duel(self):
        D = PO.affecter(LIGNE, _rush(), 4)
        P = PO.Poche(D, random.Random(3))
        P.temps_sim = [3.0, 2.1, 4.0, 2.6]
        P.armer(2.8)
        self.assertIs(P.premier, D[1])
        self.assertEqual([d["t"] for d in D], [3.7, 2.8, 4.7, 3.3])


class Hasard(unittest.TestCase):
    def test_deterministe(self):
        D = PO.affecter(LIGNE, _rush(), 5)
        self.assertEqual(PS.simuler(D, 7, 12, 5), PS.simuler(D, 7, 12, 5))


class Moteur(unittest.TestCase):
    def test_sans_simulation(self):
        self.assertIsNone(PO.SIMULATION)


if __name__ == "__main__":
    unittest.main()
