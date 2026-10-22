"""Tests du banc, des packages, de la fatigue et des rotations (moteur/rotations.py, étape 7.3). Aucun test ne dépend de
l'heure.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import unittest
from collections import Counter

from moteur import developpement as dev
from moteur import rotations as ro

GABARIT = {"QB": ["throw_power", "throw_accuracy", "mobility", "decision_making"],
           "RB": ["speed", "acceleration", "elusiveness", "power"],
           "WR": ["speed", "acceleration", "route_running", "catching"],
           "TE": ["speed", "route_running", "catching", "run_block"],
           **{p: ["run_block", "pass_block", "strength"] for p in ("LT", "LG", "C", "RG", "RT")},
           "EDGE": ["strength", "pass_rush", "tackling"], "DT": ["strength", "pass_rush", "tackling"],
           "LB": ["speed", "strength", "coverage", "tackling"], "CB": ["speed", "acceleration", "coverage", "tackling"],
           "S": ["speed", "coverage", "tackling", "run_support"]}
COMPTE = {"QB": 1, "RB": 2, "WR": 3, "TE": 1, "LT": 1, "LG": 1, "C": 1, "RG": 1, "RT": 1, "EDGE": 2, "DT": 2,
          "LB": 3, "CB": 2, "S": 2}
EQUIPES = ("CTX", "VEC", "AEG", "MNL", "AXM", "GLT", "CPH", "NVA", "PLS", "ONX", "FRG", "MRD", "APX", "LTC", "ZPH",
           "BST", "GRZ", "MRG", "GMB", "PRM", "SPK", "CTD", "TDL", "CMT")
PRENOMS = ["Adrien", "Bastien", "Cyrus", "Dorian", "Emeric", "Fabian", "Gideon", "Hector", "Ivo", "Jonas",
           "Kasimir", "Lazlo", "Matteo", "Nils", "Orson", "Pavel", "Quentin", "Roman", "Soren", "Tariq",
           "Ulric", "Valen", "Wendell", "Yannick", "Zane", "Anders", "Bram", "Cassius", "Darius", "Elio"]
FAMILLES = ["Ashford", "Bellamy", "Castellan", "Delacroix", "Eriksen", "Falkner", "Garrow", "Hargrove",
            "Ingram", "Jovanovic", "Kincaid", "Lachance", "Montague", "Norcross", "Oyelaran", "Pellegrini",
            "Quarles", "Radcliffe", "Sandoval", "Thorne", "Underwood", "Varga", "Whitlock", "Yardley",
            "Zamora", "Achebe", "Brennan", "Coventry", "Draven", "Esposito"]


def titulaires(base=80):
    return {p: [{k: base - 3 * i for k in GABARIT[p]} for i in range(n)] for p, n in COMPTE.items()}


class Banc(unittest.TestCase):
    def test_onze_places(self):
        b = ro.construire_banc("CTX", titulaires(), GABARIT)
        self.assertEqual([x["id"] for x in b], ["CTX_QB2", "CTX_RB3", "CTX_WR4", "CTX_TE2", "CTX_RT2", "CTX_LG2",
                                                 "CTX_EDGE3", "CTX_DT3", "CTX_LB4", "CTX_CB3", "CTX_S3"])
        self.assertEqual(ro.controler_banc("CTX", b, titulaires()), [])
        self.assertEqual(b[4]["covers"], ["LT", "RT"])
        self.assertEqual(b[5]["covers"], ["LG", "RG", "C"])
        self.assertTrue(all(x["depth"] == 2 for x in b))

    def test_deterministe(self):
        self.assertEqual(ro.construire_banc("MNL", titulaires(), GABARIT), ro.construire_banc("MNL", titulaires(), GABARIT))

    def test_niveau_sous_le_titulaire(self):
        ecarts = []
        for e in EQUIPES:
            t = titulaires(82)
            for (poste, n, couvre, slot), x in zip(ro.BANC, ro.construire_banc(e, t, GABARIT)):
                d = ro.ecart_ovr(x["ratings"], ro.reference(t, couvre))
                self.assertTrue(-12.75 <= d <= -2.25, (x["id"], d))
                ecarts.append(d)
        m = sum(ecarts) / len(ecarts)
        self.assertTrue(-8.5 <= m <= -6.0, m)                     # ≈ −7 sous le titulaire

    def test_profils(self):
        n = Counter(p for e in EQUIPES for p in ro.profils(e).values())
        self.assertEqual(sum(n.values()), 24 * 11)
        self.assertTrue(all(n[p] >= 60 for p in ro.PROFILS), n)
        self.assertEqual(Counter(ro.profils("SPK").values())[ro.JEUNE], 6)
        self.assertEqual(Counter(ro.profils("CTD").values())[ro.VETERAN], 6)

    def test_specialiste_un_profil_pas_un_niveau(self):
        t = titulaires(80)
        ref = {k: 80.0 for k in GABARIT["CB"]}
        spe, autres = ro.SPECIALITES["CB"][1], [k for k in GABARIT["CB"] if k not in ro.SPECIALITES["CB"][1]]
        r = ro.notes("CTX", "CB", ro.SPECIALISTE, ref)
        self.assertTrue(min(r[k] for k in spe) > max(r[k] for k in autres), r)
        self.assertTrue(-12.75 <= ro.ecart_ovr(r, ref) <= -2.25)
        self.assertIsNotNone(t)

    def test_developpement_par_profil(self):
        v = ro.profil_developpement("CTX", "LB", ro.VETERAN)
        j = ro.profil_developpement("CTX", "LB", ro.JEUNE)
        self.assertTrue(v["age0"] >= 29.5 and v["potentiel"] <= 1.0)
        self.assertTrue(j["age0"] <= 24.0 and j["potentiel"] >= 8.0)
        self.assertTrue(ro.profil_developpement("CTX", "QB", ro.VETERAN)["age0"] >= 31.0)


class Noms(unittest.TestCase):
    def test_jamais_deja_portes_ni_deux_fois(self):
        pris = {f"{PRENOMS[i % 30]} {FAMILLES[(i * 7) % 30]}" for i in range(450)}
        ids = [ro.pid(e, poste, n) for e in EQUIPES for poste, n, _, _ in ro.BANC]
        out = ro.noms(ids, PRENOMS, FAMILLES, pris)
        self.assertEqual(len(out), 264)
        self.assertEqual(len(set(out.values())), 264)
        self.assertFalse(set(out.values()) & pris)
        self.assertEqual(out, ro.noms(ids, PRENOMS, FAMILLES, pris))

    def test_reservoir_epuise(self):
        with self.assertRaises(ValueError):
            ro.noms(["A_QB2", "A_RB3"], ["X"], ["Y"], set())


class BlocE(unittest.TestCase):
    """Le banc dans l'état du bloc E : les titulaires évoluent exactement comme sans banc."""

    def etat(self, banc):
        J = []
        for e in ("CTX", "VEC"):
            t = titulaires(80 if e == "CTX" else 78)
            for p, rs in t.items():
                for i, r in enumerate(rs):
                    J.append({"id": f"{e}_{p}{i + 1}", "name": f"{e} {p}{i + 1}", "pos": p, "team": e, "ratings": r})
            if banc:
                for b in ro.construire_banc(e, t, GABARIT):
                    J.append({"id": b["id"], "name": b["id"], "pos": b["pos"], "team": e, "ratings": b["ratings"],
                              "profil": b["dev"], "banc": b["profile"]})
        return dev.etat_initial(J)

    def test_titulaires_identiques(self):
        a, b = self.etat(False), self.etat(True)
        sj = {"CTX_QB1": {"pass_att": 60, "pass_yds": 420, "pass_td": 3}, "CTX_DT3": {"snaps": 20, "team_snaps": 60}}
        se = {"CTX": {"games": 2, "rush_att": 50, "rush_yds": 220, "pass_att": 70, "sacks_taken": 4},
              "VEC": {"games": 2, "rush_att": 40, "rush_yds": 170, "pass_att": 80, "sacks_taken": 6}}
        for k in range(1, 4):
            a, _ = dev.semaine_suivante(a, sj, se, index=k, bilans={"CTX": 0.6, "VEC": 0.4})
            b, _ = dev.semaine_suivante(b, sj, se, index=k, bilans={"CTX": 0.6, "VEC": 0.4})
        for pid, j in a["joueurs"].items():
            self.assertEqual(j, b["joueurs"][pid], pid)
        self.assertEqual(len(b["joueurs"]) - len(a["joueurs"]), 22)
        self.assertEqual(b["joueurs"]["CTX_DT3"]["banc"], ro.profils("CTX")["DT"])

    def test_profil_du_banc_garde(self):
        e = self.etat(True)
        b = ro.construire_banc("CTX", titulaires(80), GABARIT)[0]
        self.assertEqual(e["joueurs"]["CTX_QB2"]["age0"], b["dev"]["age0"])
        self.assertEqual(e["joueurs"]["CTX_QB2"]["potentiel"], b["dev"]["potentiel"])
        self.assertNotIn("banc", e["joueurs"]["CTX_QB1"])

    def test_participation_aux_snaps(self):
        self.assertEqual(dev.participation_banc({"snaps": 0, "team_snaps": 60}, {}), 0.0)
        self.assertAlmostEqual(dev.participation_banc({"snaps": 20, "team_snaps": 60}, {}), 0.5)
        self.assertEqual(dev.participation_banc({"snaps": 50, "team_snaps": 60}, {}), 1.0)
        self.assertEqual(dev.participation_banc({}, {}), 0.0)

    def test_recrue_du_banc(self):
        e = self.etat(True)
        e["joueurs"]["CTX_S3"]["age0"] = 40.0
        e["joueurs"]["CTX_S1"]["age0"] = 40.0
        n, r = dev.semaine_suivante(e, index=1, recrues=(PRENOMS, FAMILLES), noms_ligue=True)
        self.assertEqual(n["joueurs"]["CTX_S3"]["banc"], dev.RECRUE_BANC)
        self.assertNotIn("banc", n["joueurs"]["CTX_S1"])
        noms = [j["name"] for j in n["joueurs"].values()]
        self.assertEqual(len(noms), len(set(noms)))
        self.assertEqual({m["id"] for m in r["retirements"]}, {"CTX_S1", "CTX_S3"})


def joueurs_match():
    pos = ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "LT", "LG", "C", "RG", "RT", "EDGE", "EDGE", "DT", "DT", "LB", "LB",
           "LB", "CB", "CB", "S", "S", "K", "P"] + [b[0] for b in ro.BANC]
    n, out = Counter(), []
    for p in pos:
        n[p] += 1
        out.append({"id": f"X_{p}{n[p]}", "pos": p})
    return out


class Alignement(unittest.TestCase):
    def test_titulaires_par_defaut(self):
        r = ro.Rotations("CTX", joueurs_match())
        occ, subs = r.alignement("off", personnel="11")
        self.assertEqual(occ, {"LT": "X_LT1", "LG": "X_LG1", "C": "X_C1", "RG": "X_RG1", "RT": "X_RT1", "QB": "X_QB1",
                               "RB": "X_RB1", "TE": "X_TE1", "WR1": "X_WR1", "WR2": "X_WR2", "WR3": "X_WR3"})
        self.assertEqual(subs, [])

    def test_packages_attaque(self):
        r = ro.Rotations("CTX", joueurs_match())
        occ, subs = r.alignement("off", personnel="12")
        self.assertEqual(occ["WR3"], "X_TE2")
        self.assertEqual(subs, [{"in": "X_TE2", "out": "X_WR3", "pos": "WR3", "reason": "package"}])
        occ, subs = r.alignement("off", personnel="11")
        self.assertEqual(subs, [{"in": "X_WR3", "out": "X_TE2", "pos": "WR3", "reason": "package"}])
        self.assertEqual(r.alignement("off", personnel="21")[0]["WR3"], "X_RB2")
        self.assertEqual(r.alignement("off", personnel="10")[0]["TE"], "X_WR4")
        self.assertEqual(r.alignement("off", formation="EMPTY")[0]["RB"], "X_WR4")
        o = r.alignement("off", formation="HEAVY")[0]
        self.assertEqual((o["WR1"], o["WR3"]), ("X_RT2", "X_RB2"))

    def test_packages_defense(self):
        r = ro.Rotations("CTX", joueurs_match())
        self.assertEqual(r.alignement("def", paquet="NICKEL")[0]["LB3"], "X_CB3")
        o = r.alignement("def", paquet="DIME")[0]
        self.assertEqual((o["LB3"], o["LB2"]), ("X_CB3", "X_S3"))
        self.assertEqual(r.alignement("def", paquet="GOAL_LINE")[0]["CB2"], "X_LB4")
        self.assertEqual(r.alignement("def", paquet="4_3")[0]["CB2"], "X_CB2")

    def test_onze_distincts(self):
        r = ro.Rotations("CTX", joueurs_match())
        for per in ("10", "11", "12", "13", "21", "22"):
            o = r.alignement("off", personnel=per)[0]
            self.assertEqual(len(set(o.values())), 11, per)
        for paq in ("4_3", "3_4", "NICKEL", "DIME", "GOAL_LINE"):
            self.assertEqual(len(set(r.alignement("def", paquet=paq)[0].values())), 11, paq)

    def test_garbage_time(self):
        r = ro.Rotations("CTX", joueurs_match())
        occ, subs = r.alignement("off", personnel="11", garbage=True)
        self.assertEqual((occ["QB"], occ["WR1"], occ["TE"], occ["LT"], occ["LG"]), ("X_QB2", "X_WR4", "X_TE2", "X_RT2", "X_LG2"))
        self.assertTrue(all(x["reason"] == "garbage" for x in subs))
        occ = r.alignement("def", paquet="4_3", garbage=True)[0]
        self.assertEqual((occ["CB1"], occ["S1"], occ["LB1"], occ["DT1"], occ["EDGE1"]),
                         ("X_CB3", "X_S3", "X_LB4", "X_DT3", "X_EDGE3"))
        self.assertTrue(ro.garbage_time(0.99, 4, part_du_quart=0.3, ecart=21))
        self.assertFalse(ro.garbage_time(0.99, 4, part_du_quart=0.3, ecart=8))      # une possession : pas plié
        self.assertFalse(ro.garbage_time(0.99, 4, part_du_quart=0.9, ecart=21))     # trop tôt dans le quart
        self.assertFalse(ro.garbage_time(0.99, 3, part_du_quart=0.1, ecart=28))
        self.assertTrue(ro.garbage_time(0.96, 4, deja=True, part_du_quart=0.2, ecart=17))

    def test_parts_de_snaps(self):
        import random
        for eq in ("CTX", "FRG", "GLT"):
            r, rng = ro.Rotations(eq, joueurs_match()), random.Random(5)
            for d in range(24):
                cote = "off" if d % 2 == 0 else "def"
                for _ in range(rng.randint(4, 8)):
                    occ = r.alignement(cote, rng=rng)[0]
                    r.jouer(cote, occ, gain=rng.choice([2, 5, 18]))
                if d == 12:
                    r.mi_temps()
            s = r.resume()
            dt = ro.part_visee(eq, "DT") * 100
            self.assertTrue(abs(s["X_DT1"]["pct"] - dt) <= 7 and abs(s["X_DT2"]["pct"] - dt) <= 7, (eq, s["X_DT1"]))
            self.assertTrue(abs(s["X_EDGE1"]["pct"] - ro.part_visee(eq, "EDGE") * 100) <= 7, (eq, s["X_EDGE1"]))
            self.assertTrue(abs(s["X_RB1"]["pct"] - ro.part_visee(eq, "RB") * 100) <= 8, (eq, s["X_RB1"]))
            self.assertEqual((s["X_QB1"]["pct"], s["X_LT1"]["pct"], s["X_CB1"]["pct"]), (100, 100, 100))
            self.assertTrue(s["X_RB3"]["pct"] <= 8 and s["X_QB2"]["snaps"] == 0)

    def test_energie(self):
        r = ro.Rotations("CTX", joueurs_match())
        occ = r.alignement("def")[0]
        r.jouer("def", occ, gain=3)
        self.assertLess(r.energie["X_DT1"], r.energie["X_LB1"])            # DL plus que LB
        r.jouer("def", occ, gain=25)
        e = r.energie["X_DT1"]
        r.jouer("off", r.alignement("off")[0])
        self.assertAlmostEqual(r.energie["X_DT1"], e + ro.RECUP_SNAP)       # hors du terrain : il récupère
        o = r.alignement("off")[0]
        r.jouer("off", o, gain=3)
        self.assertGreater(r.energie["X_LT1"], r.energie["X_RB1"])          # RB plus que OL
        self.assertGreater(r.energie["X_QB1"], r.energie["X_LT1"])          # OL plus que QB
        r2 = ro.Rotations("CTX", joueurs_match())
        r2.jouer("def", occ, gain=3, hurry=True)
        self.assertLess(r2.energie["X_DT1"], 100 - ro.COUT["DT"] + 1e-9)    # hurry-up : la défense s'use plus

    def test_malus_un_profil(self):
        self.assertEqual(ro.malus(ro.REFERENCE), 0.0)
        self.assertEqual(ro.malus(0), ro.MALUS_MAX)
        self.assertEqual(ro.malus(100), -ro.BONUS_MAX)
        n = {"pass_rush": 80, "strength": 80, "decision_making": 80}
        f = ro.notes_fatiguees(n, 50)
        self.assertEqual((f["pass_rush"], f["decision_making"]), (80 - round(ro.malus(50)), 80))
        self.assertEqual(ro.notes_fatiguees(n, ro.REFERENCE), n)

    def test_deterministe(self):
        import random
        a, b = ro.Rotations("CTX", joueurs_match()), ro.Rotations("CTX", joueurs_match())
        for k in range(60):
            for r in (a, b):
                occ = r.alignement("def", paquet="NICKEL" if k % 3 else "4_3", rng=random.Random(k))[0]
                r.jouer("def", occ, gain=k % 20)
        self.assertEqual(a.resume(), b.resume())


if __name__ == "__main__":
    unittest.main()
