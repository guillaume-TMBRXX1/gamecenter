"""Tests de l'appel de jeu qui apprend (moteur/scouting.py) : situations, carnet et oubli, tendance nette, engagement de
la défense, attaque qui se sait lue et casse sa tendance, anticipation, profils. Aucun test ne dépend de l'heure.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import unittest

from moteur import scouting as sc

PD = sc.profil_defense("CTX", trigger=1, fenetre=8)        # n_min 3, k0 2
PO = sc.profil_attaque("MRG", learn=0.6, patience=3, fenetre=8)


def carnet(jeux, demi_vie=16.0, formation="I_FORM", down=1, distance=10, yard_line=35):
    c = sc.Carnet(demi_vie)
    for cote in jeux:
        c.observer(sc.situations(down, distance, yard_line, formation, "21"), cote,
                   sc.famille(cote, "INSIDE_RUN" if cote == "RUN" else "QUICK_SLANT"))
    return c


class Situations(unittest.TestCase):
    def test_down_distance(self):
        self.assertEqual([sc.down_distance(d, t) for d, t in ((1, 10), (2, 8), (2, 4), (2, 1), (3, 12), (3, 2), (4, 1))],
                         ["1", "2-long", "2-mid", "2-short", "3-long", "3-short", "4"])

    def test_zone(self):
        self.assertEqual(sc.zone(10, 10), "own")
        self.assertEqual(sc.zone(45, 10), "mid")
        self.assertEqual(sc.zone(70, 10), "terr")
        self.assertEqual(sc.zone(85, 10), "red")
        self.assertEqual(sc.zone(95, 5), "goal")             # goal-to-go

    def test_cles(self):
        cles = sc.situations(2, 3, 40, "SHOTGUN", "11")
        self.assertEqual(cles, [("dd", "2-mid"), ("zone", "mid"), ("form", "SHOTGUN"), ("ddf", "2-mid|SHOTGUN"),
                                ("pers", "11")])
        self.assertEqual(sc.situations(1, 10, 40), [("dd", "1"), ("zone", "mid")])   # avant le choix de la formation

    def test_familles(self):
        self.assertEqual(sc.famille("RUN", "INSIDE_RUN", "inside"), "inside")
        self.assertEqual(sc.famille("RUN", "JET_SWEEP", "perimeter"), "outside")
        self.assertEqual(sc.famille("RUN", "DRAW", "inside"), "screen")
        self.assertEqual(sc.famille("PASS", "PA_SLIDE"), "pa")
        self.assertEqual(sc.famille("PASS", "STICK"), "quick")
        self.assertEqual(sc.famille("PASS", "FOUR_VERTS"), "deep")
        self.assertEqual(sc.famille("PASS", "Y_CROSS"), "medium")
        self.assertEqual(sc.famille("PASS", "WR_TUNNEL_SCREEN"), "screen")


class Tendance(unittest.TestCase):
    def test_nette_apres_assez_d_actions(self):
        cles = sc.situations(1, 10, 35, "I_FORM", "21")
        self.assertIsNone(sc.tendance(carnet(["RUN", "RUN"]), cles, PD, sc.A_PRIORI["1"]))   # trop peu vu
        t = sc.tendance(carnet(["RUN"] * 6), cles, PD, sc.A_PRIORI["1"])
        self.assertEqual(t["cote"], "RUN")
        self.assertGreaterEqual(t["conf"], sc.SEUIL)
        self.assertEqual(t["fam"], "inside")
        self.assertEqual((t["vu"], t["sur"]), (6, 6))

    def test_pas_de_tendance_sans_ecart_a_l_a_priori(self):
        """Passer sur un 3e et long, tout le monde le sait : ce n'est pas une tendance."""
        cles = sc.situations(3, 12, 35, "SHOTGUN", "11")
        c = carnet(["PASS"] * 7 + ["RUN"], formation="SHOTGUN", down=3, distance=12)
        self.assertIsNone(sc.tendance(c, cles, PD, sc.A_PRIORI["3-long"]))

    def test_melange_equilibre(self):
        cles = sc.situations(1, 10, 35, "I_FORM", "21")
        self.assertIsNone(sc.tendance(carnet(["RUN", "PASS"] * 5), cles, PD, sc.A_PRIORI["1"]))

    def test_oubli(self):
        """Les comptes s'effacent : une vieille tendance n'est plus nette après une longue série d'autres situations."""
        c = carnet(["RUN"] * 5, demi_vie=4.0)
        cles = sc.situations(1, 10, 35, "I_FORM", "21")
        self.assertIsNotNone(sc.tendance(c, cles, PD, sc.A_PRIORI["1"]))
        for _ in range(30):
            c.observer(sc.situations(3, 8, 10, "SHOTGUN", "11"), "PASS", "quick")      # autre zone du terrain
        self.assertIsNone(sc.tendance(c, cles, PD, sc.A_PRIORI["1"]))
        self.assertEqual(c.preuve(("ddf", "1|I_FORM")), (0, 5))           # le texte garde les comptes bruts

    def test_doute(self):
        c = carnet(["RUN"] * 4)
        cles = sc.situations(1, 10, 35, "I_FORM", "21")
        avant = c.lire(cles, sc.A_PRIORI["1"], 1.0)["n"]
        c.douter(cles)
        self.assertAlmostEqual(c.lire(cles, sc.A_PRIORI["1"], 1.0)["n"], avant / 2, places=6)


class Engagement(unittest.TestCase):
    def test_deterministe_et_profil(self):
        cles = sc.situations(1, 10, 35, "I_FORM", "21")
        t = sc.tendance(carnet(["RUN"] * 8), cles, PD, sc.A_PRIORI["1"])
        a = [sc.engagement(t, PD, 99, n) for n in range(300)]
        self.assertEqual(a, [sc.engagement(t, PD, 99, n) for n in range(300)])
        joueur = dict(PD, engagement=0.8)
        prudent = dict(PD, engagement=0.3)
        n_j = sum(sc.engagement(t, joueur, 99, n)[0] for n in range(1000))
        n_p = sum(sc.engagement(t, prudent, 99, n)[0] for n in range(1000))
        self.assertGreater(n_j, 2 * n_p)
        self.assertEqual(sc.engagement(None, PD, 99, 1), (False, 0.0))


class Cassure(unittest.TestCase):
    T_RUN = {"cote": "RUN", "conf": 0.85}
    LUE = {"lu_juste": 1, "reponse": False, "stoppees": 0}

    def test_se_sait_lue(self):
        self.assertFalse(sc.se_sait_lue({"lu_juste": 0, "reponse": False, "stoppees": 1}))
        self.assertTrue(sc.se_sait_lue({"lu_juste": 1}))
        self.assertTrue(sc.se_sait_lue({"reponse": True}))
        self.assertTrue(sc.se_sait_lue({"stoppees": 2}))

    def test_jamais_sans_signal_ni_en_hurry_up(self):
        sit = {"down": 1, "dd": "1", "recents": ["RUN"] * 4}
        for n in range(200):
            self.assertEqual(sc.cassure(self.T_RUN, PO, {}, 0, sit, 5, n)[0], None)
            self.assertEqual(sc.cassure(self.T_RUN, PO, self.LUE, 0, dict(sit, mode="hurry"), 5, n)[0], None)
            self.assertEqual(sc.cassure(self.T_RUN, PO, self.LUE, 0, dict(sit, mode="clock"), 5, n)[0], None)
            self.assertEqual(sc.cassure(self.T_RUN, PO, self.LUE, 0, dict(sit, down=4), 5, n)[0], None)
            self.assertEqual(sc.cassure(self.T_RUN, PO, self.LUE, PO["casse_max"], sit, 5, n)[0], None)

    def test_identite(self):
        """« Un profil, pas un niveau » : MRG casse bien plus souvent que MNL, qui joue son jeu."""
        sit = {"down": 2, "dd": "2-mid", "recents": ["PASS", "RUN"]}
        mrg = sc.profil_attaque("MRG", learn=0.6)
        mnl = sc.profil_attaque("MNL", learn=0.3)
        n_mrg = sum(bool(sc.cassure(self.T_RUN, mrg, self.LUE, 0, sit, 7, n)[0]) for n in range(1000))
        n_mnl = sum(bool(sc.cassure(self.T_RUN, mnl, self.LUE, 0, sit, 7, n)[0]) for n in range(1000))
        self.assertGreater(n_mrg, 5 * max(1, n_mnl))
        self.assertLess(mnl["casse_max"], mrg["casse_max"])

    def test_genres(self):
        self.assertEqual(sc.type_cassure({"cote": "RUN"}, ["RUN", "RUN", "PASS", "RUN"], "2-mid"), "pa")
        self.assertEqual(sc.type_cassure({"cote": "RUN"}, ["PASS"], "3-short"), "run_down_pass")
        self.assertEqual(sc.type_cassure({"cote": "RUN"}, ["PASS"], "2-mid"), "same_formation")
        self.assertEqual(sc.type_cassure({"cote": "PASS"}, ["PASS"], "3-long"), "pass_down_run")
        self.assertEqual(sc.type_cassure({"cote": "PASS"}, ["PASS"], "1"), "same_formation")


class Anticipation(unittest.TestCase):
    def test_signes(self):
        juste_course = sc.anticipation("RUN", "inside", "RUN", "inside")
        self.assertGreater(juste_course["boite"], 0)
        self.assertLess(juste_course["yds"], 0)
        fausse_course = sc.anticipation("PASS", "quick", "RUN", "inside")
        self.assertLess(fausse_course["boite"], 0)
        self.assertGreater(fausse_course["yds"], 0)
        juste_passe = sc.anticipation("PASS", "deep", "PASS", "deep")
        self.assertLess(juste_passe["profond"], juste_passe["moyen"])
        self.assertLess(juste_passe["poche"], 0)
        pa = sc.anticipation("RUN", "inside", "PASS", "pa")
        passe = sc.anticipation("RUN", "inside", "PASS", "quick")
        self.assertGreater(pa["profond"], passe["profond"] - 1e-9)
        self.assertGreater(passe["court"], 0)
        self.assertGreater(passe["poche"], 0)

    def test_raison(self):
        t = {"cote": "RUN", "vu": 7, "sur": 8}
        self.assertEqual(sc.raison(t, "on 1st down from I-Form"), "7 of 8 runs on 1st down from I-Form")


class Profils(unittest.TestCase):
    def test_derives_de_12_2_quater_et_bloc_d(self):
        vite = sc.profil_defense("CTX", trigger=1, fenetre=6)
        lent = sc.profil_defense("AEG", trigger=3, fenetre=10)
        self.assertLess(vite["n_min"], lent["n_min"])
        self.assertLess(vite["demi_vie"], lent["demi_vie"])
        self.assertTrue(set(sc.SCOUT) >= {"CTX", "MNL", "MRG", "SPK", "CMT"})
        self.assertEqual(len(sc.SCOUT), 24)


if __name__ == "__main__":
    unittest.main()
