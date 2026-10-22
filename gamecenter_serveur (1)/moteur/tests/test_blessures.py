"""Tests des blessures (moteur/blessures.py et les indisponibles de moteur/rotations.py, étape 7.4). Aucun test ne
dépend de l'heure.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import random
import unittest
from collections import Counter

from moteur import blessures as bl
from moteur import rotations as ro
from moteur.tests.test_rotations import joueurs_match


def sur_le_terrain(r):
    return [(i, r.pos[i], c) for c in ("off", "def") for i in r.alignement(c)[0].values()]


class Tirage(unittest.TestCase):
    def test_gravites(self):
        self.assertAlmostEqual(sum(p for _, _, p in bl.GRAVITE), 1.0)
        rng = random.Random(1)
        n = Counter(bl.blessure(rng)["severity"] for _ in range(20000))
        self.assertTrue(0.33 <= n[bl.LEGERE] / 20000 <= 0.37, n)            # les commotions passent en « match »
        self.assertTrue(0.24 <= n[bl.SEMAINES] / 20000 <= 0.28, n)

    def test_commotion_jamais_legere(self):
        rng = random.Random(2)
        for _ in range(5000):
            b = bl.blessure(rng)
            if b["part"] == "concussion":
                self.assertNotEqual(b["severity"], bl.LEGERE)
            self.assertEqual(b["snaps"] is not None, b["severity"] == bl.LEGERE)
            self.assertEqual(b["weeks"] > 0, b["severity"] == bl.SEMAINES)

    def test_expositions(self):
        sur = [("QB", "QB", "off"), ("RB", "RB", "off"), ("LT", "LT", "off"), ("LB", "LB", "def"), ("CB", "CB", "def")]
        w = bl.expositions({"play_type": "RUN", "outcome": "RUN", "carrier_id": "RB", "tackler_id": "LB",
                            "credited_category": "TACKLE", "yards_gained": 4, "passer_id": "QB"}, sur)
        self.assertGreater(w["RB"], w["LB"])
        self.assertGreater(w["LB"], w["CB"])
        self.assertGreater(w["LT"], w["QB"])                                  # le QB est protégé hors sack
        s = bl.expositions({"play_type": "PASS", "outcome": "SACK", "credited_category": "SACK", "passer_id": "QB",
                            "tackler_id": "LB", "carrier_id": "QB"}, sur)
        self.assertGreater(s["QB"], 10 * w["QB"])                             # le QB sacké
        g = bl.expositions({"play_type": "RUN", "outcome": "RUN", "carrier_id": "RB", "yards_gained": 30}, sur)
        self.assertGreater(g["RB"], w["RB"])                                  # course lancée

    def test_fatigue_et_age(self):
        self.assertEqual(bl.facteur_fatigue(90), 1.0)
        self.assertGreater(bl.facteur_fatigue(30), bl.facteur_fatigue(60))
        self.assertAlmostEqual(bl.facteur_fatigue(0), 1 + bl.FATIGUE_MAX)
        self.assertEqual(bl.facteur_age(25), 1.0)
        self.assertGreater(bl.facteur_age(33), bl.facteur_age(31))

    def test_deterministe_proteges_et_une_par_action(self):
        poids = {f"P{k}": 1.0 for k in range(22)}
        a = [bl.tirer(random.Random(k), poids) for k in range(300)]
        self.assertEqual(a, [bl.tirer(random.Random(k), poids) for k in range(300)])
        old = bl.ECHELLE
        bl.ECHELLE = 0.5                                                       # presque tout le monde est touché
        try:
            for k in range(200):
                t = bl.tirer(random.Random(k), poids, proteges=["P0"])
                self.assertEqual(len(t), 1)                                    # un arrêt de jeu, un blessé
                self.assertNotEqual(t[0][0], "P0")
            self.assertEqual(bl.tirer(random.Random(1), {"P0": 1.0}, proteges=["P0"]), [])
        finally:
            bl.ECHELLE = old

    def test_taux(self):
        """≈ 0,5 sortie par match : ≈ 125 actions de l'attaque, 22 joueurs, un porteur plaqué et un plaqueur."""
        r = ro.Rotations("CTX", joueurs_match())
        sur = sur_le_terrain(r)
        rng, n = random.Random(7), 0
        for k in range(125 * 400):
            act = {"play_type": "RUN", "outcome": "RUN" if k % 3 else "PASS_INCOMPLETE", "carrier_id": "X_RB1",
                   "tackler_id": "X_LB1", "credited_category": "TACKLE" if k % 3 else None, "yards_gained": k % 9}
            n += len(bl.tirer(rng, bl.expositions(act, sur)))
        self.assertTrue(0.3 <= n / 400 <= 0.8, n / 400)


class Indisponibles(unittest.TestCase):
    def test_sans_blesse_identique(self):
        a, b = ro.Rotations("CTX", joueurs_match()), ro.Rotations("CTX", joueurs_match())
        b.blesser("X_WR1", 1)
        for r in (a, b):                                                     # les mêmes snaps ; il est revenu
            r.jouer("off", r.alignement("off")[0])
            r.jouer("off", r.alignement("off")[0])
        self.assertEqual(b.indispo, {})
        self.assertEqual(a.base, b.base)
        self.assertEqual(a.alignement("off", personnel="12")[0], b.alignement("off", personnel="12")[0])

    def test_la_profondeur_monte(self):
        r = ro.Rotations("CTX", joueurs_match())
        r.alignement("off")
        r.blesser("X_WR1")
        occ, subs = r.alignement("off")
        self.assertEqual((occ["WR1"], occ["WR2"], occ["WR3"]), ("X_WR2", "X_WR3", "X_WR4"))
        self.assertTrue(subs and all(x["reason"] == "injury" for x in subs))
        self.assertNotIn("X_WR1", r.alignement("off", personnel="10")[0].values())
        occ, subs = r.alignement("off")
        self.assertEqual(subs, [])                                           # plus de changement ensuite

    def test_tackle_et_glissements(self):
        r = ro.Rotations("CTX", joueurs_match())
        r.blesser("X_LT1")
        self.assertEqual(r.alignement("off")[0]["LT"], "X_RT2")              # le tackle de rechange
        for i in ("X_CB1", "X_CB2", "X_CB3"):
            r.blesser(i)
        occ = r.alignement("def", paquet="NICKEL")[0]
        self.assertEqual(occ["CB1"], "X_S3")                                 # le S3 glisse en CB, un remplaçant d'abord
        self.assertEqual(len(set(occ.values())), 11)
        self.assertFalse({"X_CB1", "X_CB2", "X_CB3"} & set(occ.values()))

    def test_blessure_legere_puis_retour(self):
        r = ro.Rotations("CTX", joueurs_match())
        r.alignement("def")
        r.blesser("X_LB1", 2)
        for _ in range(2):
            occ, _ = r.alignement("def")
            self.assertNotIn("X_LB1", occ.values())
            r.jouer("def", occ)
        occ, subs = r.alignement("def")
        self.assertEqual(occ["LB1"], "X_LB1")
        self.assertTrue(any(x["in"] == "X_LB1" and x["reason"] == "return" for x in subs), subs)

    def test_toujours_onze(self):
        rng = random.Random(3)
        r = ro.Rotations("CTX", joueurs_match())
        ids = [i for i in r.pos if r.pos[i] not in ("QB",)]
        for i in rng.sample(ids, 14):
            r.blesser(i)
            for c, par in (("off", ("10", "11", "12", "21")), ("def", ("4_3", "NICKEL", "DIME", "GOAL_LINE"))):
                for p in par:
                    occ = r.alignement(c, personnel=p if c == "off" else None, paquet=p if c == "def" else None,
                                       rng=rng)[0]
                    v = list(occ.values())
                    self.assertTrue(None not in v and len(set(v)) == 11, (c, p, occ))


if __name__ == "__main__":
    unittest.main()
