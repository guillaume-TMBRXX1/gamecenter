"""Tests de l'appel de jeu qui apprend (moteur/scouting.py) : situations, carnet et oubli, tendance nette, engagement de
la défense, attaque qui se sait lue et casse sa tendance, anticipation, profils ; idée 6 : le film d'une semaine à
l'autre (oubli hebdomadaire, plafonds, a priori < film < match, film vide = idée 5, réputation, stabilité). Aucun test
ne dépend de l'heure.

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


# ---------- idée 6 : la mémoire d'une semaine à l'autre ----------
def match_film(film, off, de, jeux, formation="I_FORM", down=1, distance=10, lectures=None):
    obs = [sc.observation(down, distance, 35, formation, "21", cote, "INSIDE_RUN" if cote == "RUN" else "QUICK_SLANT",
                          "inside") for cote in jeux]
    return sc.film_match(film, off, de, obs, lectures)


def semaine(n_matchs=3, jeux=("RUN",) * 20 + ("PASS",) * 5, de="ONX", lectures=None):
    f = sc.film_vide()
    for k in range(n_matchs):
        match_film(f, "MNL", de if k == 0 else f"D{k}", list(jeux), lectures=lectures)
    return f


CLES = sc.situations(1, 10, 35, "I_FORM", "21")


class Film(unittest.TestCase):
    def test_film_vide_ne_change_rien(self):
        """Sans film, le carnet, la tendance et le texte sont exactement ceux de l'idée 5."""
        a, b = carnet(["RUN"] * 6), carnet(["RUN"] * 6)
        b.amorcer({}, sc.FILM_DEMI_VIE, {"games": 3, "own": 0})
        ta, tb = sc.tendance(a, CLES, PD, sc.A_PRIORI["1"]), sc.tendance(b, CLES, PD, sc.A_PRIORI["1"])
        self.assertEqual(ta, tb)
        self.assertNotIn("film", tb)
        self.assertEqual(a.lire(CLES, 0.58, 2.0), b.lire(CLES, 0.58, 2.0))
        self.assertEqual(sc.film_pour(None, "ONX", "MNL"), ({}, None))
        self.assertEqual(sc.film_pour(sc.film_vide(), "ONX", "MNL"), ({}, None))

    def test_tendance_des_le_premier_snap(self):
        film, info = sc.film_pour(sc.film_suivant(None, semaine()), "ONX", "MNL", 1.0)
        c = sc.Carnet()
        c.amorcer(film, sc.FILM_DEMI_VIE, info)
        t = sc.tendance(c, CLES, PD, sc.A_PRIORI["1"])
        self.assertEqual(t["cote"], "RUN")
        self.assertGreaterEqual(t["film"]["part"], 0.99)
        self.assertEqual((t["film"]["games"], t["film"]["own"]), (3, 1))
        self.assertEqual((t["vu"], t["sur"]), (60, 75))
        self.assertTrue(sc.raison(t, "on 1st down").startswith("film: 60 of 75 runs on 1st down, 3 games"))

    def test_plafonds_proportions_pas_masse(self):
        """1 000 snaps de film ne valent pas 1 000 snaps vus : FILM_MAX × poids, proportions gardées."""
        gros = sc.film_suivant(None, semaine(n_matchs=40))
        film, _ = sc.film_pour(gros, "D1", "MNL", 1.0)
        e = film[("ddf", "1|I_FORM")]
        self.assertAlmostEqual(e["pas"] + e["run"], sc.FILM_MAX["ddf"], places=6)
        self.assertAlmostEqual(e["run"] / (e["pas"] + e["run"]), 0.8, places=6)
        film2, _ = sc.film_pour(gros, "D1", "MNL", 0.6)
        self.assertAlmostEqual(sum(film2[("ddf", "1|I_FORM")][k] for k in ("pas", "run")), 0.6 * sc.FILM_MAX["ddf"],
                               places=6)
        self.assertNotIn(("zone", "mid"), film)                    # situations générales : celles du match
        soi, _ = sc.film_pour(gros, None, "MNL", 1.0)              # l'attaque sait ce qu'elle montre par down
        self.assertAlmostEqual(sum(soi[("dd", "1")][k] for k in ("pas", "run")), sc.FILM_MAX_SOI["dd"], places=6)
        self.assertEqual(sc.poids_film("SPK", 8), 0.6)
        self.assertEqual(sc.poids_film("CTX", 8), 1.0)
        self.assertLessEqual(max(sc.poids_film(a, f) for a in sc.SCOUT for f in (6, 8, 10, 12)), 1.4)

    def test_ses_matchs_pesent_plus(self):
        f = sc.film_vide()
        match_film(f, "MNL", "ONX", ["RUN"] * 10)                 # contre ONX : il court
        for k in range(3):
            match_film(f, "MNL", f"D{k}", ["PASS"] * 10)           # contre les autres : il passe
        f = sc.film_suivant(None, f)
        onx, _ = sc.film_pour(f, "ONX", "MNL", 1.0)
        autre, _ = sc.film_pour(f, "D0", "MNL", 1.0)
        part = lambda e: e["run"] / (e["run"] + e["pas"])
        self.assertAlmostEqual(part(onx[("form", "I_FORM")]), 15 / 45, places=6)       # 10 × 1,5 sur 45
        self.assertAlmostEqual(part(autre[("form", "I_FORM")]), 10 / 45, places=6)     # ses passes contre D0 × 1,5

    def test_a_priori_film_match(self):
        """Le film s'efface pendant le match : ce que l'attaque fait AUJOURD'HUI finit par l'emporter."""
        film, info = sc.film_pour(sc.film_suivant(None, semaine()), "ONX", "MNL", 1.0)
        c = sc.Carnet(16.0)
        c.amorcer(film, sc.FILM_DEMI_VIE, info)
        for _ in range(12):
            c.observer(CLES, "PASS", "quick")
        t = sc.tendance(c, CLES, PD, sc.A_PRIORI["1"])
        self.assertEqual(t["cote"], "PASS")
        self.assertLess(t["film"]["part"], 0.5)
        self.assertEqual((t["vu"], t["sur"]), (12, 12))          # le texte raconte le match
        self.assertLess(c._k_film(), 0.8)

    def test_confiance_du_film_plafonnee(self):
        t_film = {"conf": 0.97, "film": {"part": 0.9}}
        t_match = {"conf": 0.97}
        self.assertLess(sc._confiance(t_film), sc._confiance(t_match))
        self.assertAlmostEqual(sc._confiance(t_film), sc._confiance({"conf": sc.FILM_CONF_MAX}))

    def test_doute_efface_aussi_le_film(self):
        film, info = sc.film_pour(sc.film_suivant(None, semaine()), "ONX", "MNL", 1.0)
        c = sc.Carnet()
        c.amorcer(film, sc.FILM_DEMI_VIE, info)
        avant = c.lire(CLES, 0.58, 2.0)["n"]
        c.douter(CLES)
        self.assertAlmostEqual(c.lire(CLES, 0.58, 2.0)["n"], avant / 2, places=6)

    def test_self_scout_match_ou_film(self):
        """L'attaque se sait prévisible si le match OU son film le montre : le film ne noie jamais le match."""
        film, info = sc.film_pour(sc.film_suivant(None, semaine(jeux=("PASS",) * 13 + ("RUN",) * 12)), None, "MNL")
        nu, ou = carnet(["RUN"] * 6), carnet(["RUN"] * 6)
        ou.amorcer(film, sc.FILM_DEMI_VIE, info, ou=True)
        self.assertEqual(sc.tendance(nu, CLES, PO, sc.A_PRIORI["1"]), sc.tendance(ou, CLES, PO, sc.A_PRIORI["1"]))
        seul = sc.Carnet()
        seul.amorcer(sc.film_pour(sc.film_suivant(None, semaine()), None, "MNL")[0], sc.FILM_DEMI_VIE,
                     {"games": 3, "own": 0}, ou=True)
        t = sc.tendance(seul, sc.situations(1, 10, 35), PO, sc.A_PRIORI["1"])     # avant la formation
        self.assertEqual(t["cote"], "RUN")
        self.assertGreaterEqual(t["film"]["part"], 0.99)


class Semaines(unittest.TestCase):
    def test_oubli_hebdomadaire_et_stabilite(self):
        """Anti-inflation : avec la même semaine rejouée 20 fois, le film plafonne à 1 / (1 − oubli) semaines."""
        s = semaine()
        f = None
        for _ in range(20):
            f = sc.film_suivant(f, s)
        un = sc.film_suivant(None, s)
        borne = 1.0 / (1.0 - sc.OUBLI_SEMAINE)
        self.assertLessEqual(f["attaques"]["MNL"]["matchs"], borne * un["attaques"]["MNL"]["matchs"] + 0.05)
        e, e1 = f["attaques"]["MNL"]["cles"]["dd|1"], un["attaques"]["MNL"]["cles"]["dd|1"]
        self.assertLessEqual(e[1], borne * e1[1] + 0.05)
        self.assertEqual(f["semaines"], 20)
        self.assertFalse(sc.controler_film(f, ["MNL", "ONX", "D1", "D2"]))

    def test_arrondis_dans_les_bornes(self):
        """Comptes et familles arrondis au dixième : le contrôle de l'audit les tolère (semaine du 26/10)."""
        f = None
        for k in range(5):
            s = sc.film_vide()
            obs = [sc.observation(1, 10, 35, "I_FORM", "21", c, con, cl) for c, con, cl in
                   (("RUN", "INSIDE_RUN", "inside"), ("RUN", "JET_SWEEP", "perimeter"), ("RUN", "DRAW", "inside"),
                    ("PASS", "STICK", None), ("PASS", "PA_SLIDE", None), ("PASS", "FOUR_VERTS", None),
                    ("PASS", "Y_CROSS", None))[:3 + k]]
            sc.film_match(s, "MNL", "ONX", obs * 3)
            f = sc.film_suivant(f, s)
        self.assertFalse(sc.controler_film(f, ["MNL", "ONX"]))

    def test_vieux_film_oublie(self):
        f = sc.film_suivant(None, semaine())
        for _ in range(12):
            f = sc.film_suivant(f, sc.film_vide())
        self.assertNotIn("MNL", f["attaques"])                     # comptes < FILM_MIN : oubliés

    def test_film_deterministe_et_cle(self):
        a, b = sc.film_suivant(None, semaine()), sc.film_suivant(None, semaine())
        self.assertEqual(a, b)
        self.assertEqual(sc.film_cle(a), sc.film_cle(b))
        self.assertNotEqual(sc.film_cle(a), sc.film_cle(sc.film_suivant(a, semaine())))
        self.assertIsNone(sc.film_cle(None))

    def test_reputation(self):
        def defense(lectures, n=4):
            f = sc.film_vide()
            for k in range(n):
                match_film(f, f"A{k}", "ONX", ["RUN"] * 5, lectures=lectures)
            return sc.film_suivant(None, f)
        self.assertTrue(sc.reputation(defense((5, 4)), "ONX"))
        self.assertFalse(sc.reputation(defense((5, 4), n=2), "ONX"))   # deux matchs : trop peu
        self.assertFalse(sc.reputation(defense((5, 2)), "ONX"))        # elle lit, mais se trompe
        self.assertFalse(sc.reputation(defense((2, 2)), "ONX"))        # elle lit peu
        self.assertFalse(sc.reputation(defense((5, 4)), "A1"))
        self.assertTrue(sc.se_sait_lue({"reputation": True}))

    def test_controle_et_rapport(self):
        f = sc.film_suivant(None, semaine())
        self.assertTrue(sc.controler_film(f, ["ONX"]))             # équipes inconnues
        self.assertEqual(sc.controler_film({"version": "?"}), ["film : version inconnue"])
        film, info = sc.film_pour(f, "ONX", "MNL", 1.0)
        c = sc.Carnet()
        c.amorcer(film, sc.FILM_DEMI_VIE, info)
        top = sc.film_tendances(c, PD)
        self.assertEqual(top[0]["dd"], "1")
        self.assertEqual(top[0]["cote"], "RUN")

    def test_observations_feed(self):
        feed = {"game": {"home": {"abbr": "MNL"}, "away": {"abbr": "ONX"}},
                "plays": [{"offense": "home", "los_x": 45, "down": 1, "to_go": 10,
                           "call": {"type": "run", "concept": "INSIDE_RUN", "formation": "I_FORM", "personnel": "21",
                                    "play_id": "I_FORM_INSIDE_RUN"}},
                          {"offense": "away", "los_x": 45, "down": 3, "to_go": 2,
                           "call": {"type": "pass", "concept": "STICK", "formation": "SHOTGUN", "personnel": "11",
                                    "play_id": "X"}, "scout": {"def": {"team": "home", "right": True}}},
                          {"offense": "home", "los_x": 45, "down": 1, "to_go": 10,
                           "call": {"type": "run", "play_id": "KNEEL"}},
                          {"offense": "home", "los_x": 45, "down": None, "to_go": None, "call": {"type": "punt"}}]}
        o = sc.observations_feed(feed, {"INSIDE_RUN": "inside"})
        self.assertEqual(len(o), 2)
        self.assertEqual(o[0][:2], ("MNL", "ONX"))
        self.assertIn(("zone", "mid"), o[0][2])                     # home : ligne des 35 de l'attaque
        self.assertIn(("zone", "terr"), o[1][2])                    # away : 110 − 45 = 65
        self.assertEqual(o[1][3:], ("PASS", "quick"))
        self.assertEqual(sc.lectures_feed(feed), {"MNL": [1, 1]})


if __name__ == "__main__":
    unittest.main()
