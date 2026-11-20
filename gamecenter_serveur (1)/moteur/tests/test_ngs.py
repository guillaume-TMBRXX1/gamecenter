"""Statistiques de suivi (moteur/ngs.py, programme/Next_Gen_Stats_plan.md, NGS-1 et NGS-2).

  Comptage     un petit GameFeed fabriqué, chaque compte vérifié à la main (passeur, receveurs, poche, course,
               plaquages, blocs, équipes) ; pénalités, genou et spike exclus ; rôle -> joueur avec les remplacements
  Modèles      apprentissage, lissage vers la case parente, ligue recentrée (CPOE et RYOE de la ligue = 0)
  Tableaux     seuils par match de l'équipe, postes, tri, statistique du jour
  Données      un vrai match de la semaine la plus récente (si présent) ; une semaine sans geo ne plante pas
  Serveur      /api/tracking : matchs terminés seulement, rien de Pro hors liste (la stat du jour pour tous),
               interrupteur GC_TRACKING (et GC_INSIGHTS), temps de calcul de la semaine entière

    python -m unittest moteur.tests.test_ngs        (depuis « gamecenter_serveur (1) »)
"""
import glob
import json
import os
import time
import unittest
from unittest import mock

from moteur import ngs as N
from moteur.tests import test_serveur as ts


def _ngs_du_jour():
    return N.DU_JOUR

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(os.path.dirname(ICI))


def _roster(eq):
    pos = [("QB1", "QB"), ("RB1", "RB"), ("WR1", "WR"), ("WR2", "WR"), ("WR3", "WR"), ("TE1", "TE"), ("LT1", "LT"),
           ("RT1", "RT"), ("EDGE1", "EDGE"), ("CB1", "CB"), ("LB1", "LB"), ("S1", "S")]
    return [{"id": f"{eq}_{k}", "name": f"{eq} {k}", "pos": p} for k, p in pos]


def _passe(seq, res, gain, tt=2.0, cible="WR1", st="L", sep=4.0, prof=10, pression=False, read=1, action="LANCER",
           duels=None, subs=None, blitz=False, rc="open", qb="AAA_QB1", tid=None, cov="BBB_CB1"):
    return {"seq": seq, "offense": "home", "down": 1, "to_go": 10, "result": res, "gain": gain,
            "call": {"type": "pass", "route": {"depth": prof}}, "players": {}, "subs": subs or [],
            "decision": {"action": action, "throw_time": tt, "pressure": pression, "time_to_pressure": 1.5 if pression else 4.0,
                         "read": read, "misread": False, "blitz": blitz, "reception": rc,
                         "qb": {"id": qb, "name": "AAA QB1"},
                         "target": {"role": cible, "id": tid or f"AAA_{N._ROLE_DEFAUT.get(cible, cible)}"},
                         "coverer": {"id": cov, "name": "BBB CB1", "pos": "CB"}},
            "geo": {"k": "pass", "tt": tt, "tgt": cible,
                    "rec": [[cible, sep, st, cov, False], ["TE", 1.0, "C", "BBB_LB1", False]]},
            "pocket": {"duels": duels or []}}


def _course(seq, gain, box=7, contact=2.0, ev=None, duels=None, car="AAA_RB1", res="run"):
    return {"seq": seq, "offense": "home", "down": 1, "to_go": 10, "result": res, "gain": gain,
            "call": {"type": "run"}, "players": {"carrier": {"id": car, "name": car}}, "run": {"box": box},
            "geo": {"k": "run", "cls": "inside", "duels": duels or [],
                    "sim": {"c": [[contact, 20.0], [contact + 1, 20.0]], "ev": ev or []}}}


def _feed(plays):
    return {"game": {"home": {"abbr": "AAA", "roster": _roster("AAA")}, "away": {"abbr": "BBB", "roster": _roster("BBB")}},
            "plays": plays}


DUEL_GAGNE = {"rusher": {"id": "BBB_EDGE1", "pos": "EDGE"}, "blocker": {"id": "AAA_LT1", "pos": "LT"}, "t": 1.2}
DUEL_PERDU = {"rusher": {"id": "BBB_EDGE1", "pos": "EDGE"}, "blocker": {"id": "AAA_LT1", "pos": "LT"}, "t": 4.0}


class Comptage(unittest.TestCase):
    def setUp(self):
        self.F = _feed([
            _passe(1, "complete", 14, tt=2.0, prof=10, duels=[DUEL_PERDU]),               # YAC 4
            _passe(2, "incomplete", 0, tt=3.0, st="C", sep=1.0, prof=20, pression=True, read=2,
                   duels=[DUEL_GAGNE], rc="contested"),
            _passe(3, "sack", -7, tt=2.5, action="SACK", duels=[DUEL_GAGNE]),
            _passe(4, "penalty", 0),                                                        # exclue
            _passe(5, "complete", 6, cible="WR2", prof=5, blitz=True,
                   subs=[{"in": "AAA_WR3", "out": "AAA_WR2", "pos": "WR2", "side": "off"}], tid="AAA_WR3"),
            _course(6, 5, box=8, contact=2.0, ev=[[0.2, "BBB_LB1", 0], [0.6, "BBB_S1", 1]],
                    duels=[["AAA_LT1", "BBB_EDGE1", 2.0], ["AAA_RT1", "BBB_LB1", -1.0]]),
            _course(7, -1, box=6, contact=-1.0, ev=[[0.1, "BBB_LB1", 1]]),
            {"seq": 8, "offense": "home", "result": "run", "gain": -1, "call": {"type": "kneel"}, "players": {}},
        ])
        self.C = N.compter(self.F)

    def test_passeur(self):
        q = self.C["players"]["AAA_QB1"]
        self.assertEqual(q["db"], 4)                      # 1, 2, 3, 5 (la pénalité ne compte pas)
        self.assertEqual(q["att"], 3)                     # le sack n'est pas une tentative
        self.assertEqual(q["cmp"], 2)
        self.assertEqual(q["pyds"], 20)
        self.assertAlmostEqual(q["tt_s"] / q["tt_n"], 7 / 3, places=3)
        self.assertAlmostEqual(q["ay_s"] / q["ay_n"], 35 / 3, places=3)
        self.assertEqual(q["tw"], 1)                      # cible couverte
        self.assertEqual((q["rd_1"], q["rd_n"]), (2, 3))
        self.assertEqual((q["prs_db"], q["prs_att"], q.get("prs_cmp", 0)), (1, 1, 0))
        self.assertEqual(q["sk"], 1)
        self.assertEqual(q["db_y"], 13)

    def test_receveurs_et_remplacements(self):
        r = self.C["players"]["AAA_WR1"]
        self.assertEqual((r["tgt"], r["rec"], r["ryds"]), (2, 1, 14))       # passes 1, 2 (le sack : pas une cible)
        self.assertEqual((r["yac_n"], r["yac_s"]), (1, 4))
        self.assertEqual((r["ct_t"], r.get("ct_c", 0)), (1, 0))
        self.assertNotIn("AAA_WR2", self.C["players"])                   # remplacé par AAA_WR3 au rôle WR2
        w3 = self.C["players"]["AAA_WR3"]
        self.assertEqual((w3["tgt"], w3["rec"], w3["rt"], w3["rt_open"]), (1, 1, 1, 1))
        te = self.C["players"]["AAA_TE1"]                                # TE -> AAA_TE1, route non ciblée
        self.assertEqual((te["rt"], te.get("rt_open", 0)), (4, 0))
        self.assertNotIn("tgt", te)

    def test_couverture_et_poche(self):
        c = self.C["players"]["BBB_CB1"]
        self.assertEqual((c["cv_t"], c["cv_c"], c["cv_y"]), (3, 2, 20))
        e = self.C["players"]["BBB_EDGE1"]
        self.assertEqual((e["pr_d"], e["pr_w"], e["prs"]), (3, 2, 1))    # pression créditée sur la passe 2
        lt = self.C["players"]["AAA_LT1"]
        self.assertEqual((lt["pb_d"], lt["pb_w"]), (3, 1))
        self.assertEqual((lt["rb_d"], lt["rb_w"]), (1, 1))
        self.assertEqual((self.C["players"]["AAA_RT1"]["rb_d"], self.C["players"]["AAA_RT1"].get("rb_w", 0)), (1, 0))

    def test_course_et_plaquages(self):
        b = self.C["players"]["AAA_RB1"]
        self.assertEqual((b["car"], b["ruyds"], b["stuff"], b["box8"]), (2, 4, 1, 1))
        self.assertEqual((b["ybc_s"], b["yaco_s"], b["mtf"]), (1.0, 3.0, 1))
        lb = self.C["players"]["BBB_LB1"]
        self.assertEqual((lb["tk_a"], lb["tk_m"]), (2, 1))

    def test_equipes(self):
        o, d = self.C["teams"]["AAA"], self.C["teams"]["BBB"]
        self.assertEqual((o["o_db"], o["o_att"], o["o_cmp"], o["o_prs"]), (4, 3, 2, 1))
        self.assertEqual((d["d_db"], d["d_blitz"], d["d_blz_db"], d["d_blz_y"]), (4, 1, 1, 6))
        self.assertEqual((o["o_car"], o["o_ryds"]), (2, 4))
        self.assertEqual(self.C["gp"], ["AAA", "BBB"])

    def test_noms_et_postes(self):
        self.assertEqual(self.C["names"]["AAA_WR3"], ["AAA WR3", "WR", "AAA"])
        self.assertEqual(self.C["names"]["BBB_EDGE1"][1:], ["EDGE", "BBB"])


class Modeles(unittest.TestCase):
    def test_apprentissage_et_lissage(self):
        F = _feed([_passe(i, "complete" if i % 4 else "incomplete", 12) for i in range(1, 41)] +
                  [_course(100 + i, 4 + (i % 3)) for i in range(30)])
        M = N.entrainer([F], ["essai"])
        self.assertEqual(M["comp"][""][0], 40)
        self.assertAlmostEqual(N.x_comp(N._table_modele(M), "L", 10, False, 2.0), 0.75, places=2)
        # une case jamais vue prend la valeur de la plus proche parente
        self.assertAlmostEqual(N.x_comp(N._table_modele(M), "D", 30, True, 4.0), 0.75, places=2)
        self.assertAlmostEqual(N.x_rush(N._table_modele(M), 7, "inside", 1, 10), 5.0, places=1)

    def test_ligue_recentree(self):
        F = _feed([_passe(i, "complete" if i % 3 else "incomplete", 10, qb="AAA_QB1") for i in range(1, 61)])
        M = N.entrainer([_feed([_passe(i, "complete", 10) for i in range(1, 30)])])      # modèle trop optimiste
        T = N.tableaux(N.agreger([N.compter(F, M)]), M)
        qb = next(g for g in T["groups"] if g["key"] == "passing")["rows"][0]
        self.assertAlmostEqual(qb["v"]["cpoe"], 0.0, places=1)           # un seul QB : il est la ligue


class Tableaux(unittest.TestCase):
    def test_seuil_par_match_de_l_equipe(self):
        F = _feed([_passe(i, "complete", 8) for i in range(1, 14)])          # 13 tentatives : sous 14 par match
        T = N.tableaux(N.agreger([N.compter(F)]))
        self.assertEqual(next(g for g in T["groups"] if g["key"] == "passing")["rows"], [])
        F = _feed([_passe(i, "complete", 8) for i in range(1, 16)])
        T = N.tableaux(N.agreger([N.compter(F)]))
        g = next(g for g in T["groups"] if g["key"] == "passing")
        self.assertEqual([r["id"] for r in g["rows"]], ["AAA_QB1"])
        self.assertEqual(g["rows"][0]["v"]["cmp"], 1.0)
        self.assertEqual({c["k"] for c in g["cols"]} >= {"tt", "adot", "cpoe", "agg"}, True)

    def test_postes_et_stat_du_jour(self):
        F = _feed([_passe(i, "complete", 8, tt=1.0 + i / 100) for i in range(1, 30)])
        T = N.tableaux(N.agreger([N.compter(F)]))
        rec = next(g for g in T["groups"] if g["key"] == "receiving")
        self.assertTrue(all(r["pos"] in ("WR", "TE", "RB") for r in rec["rows"]))
        s = N.stat_du_jour(T, 0)
        self.assertEqual((s["title"], s["id"]), ("Fastest release", "AAA_QB1"))
        self.assertIsNone(N.stat_du_jour(None, 0))
        self.assertIsNotNone(N.stat_du_jour(T, 5))                    # un groupe vide : on passe au suivant


class Fiches(unittest.TestCase):
    """NGS-5 : la fiche d'un joueur (phare + rangs), le profil d'une équipe, le suivi d'un match."""
    def setUp(self):
        self.F = _feed([_passe(i, "complete" if i % 3 else "incomplete", 9, tt=1.5 + i / 50, prof=8,
                               duels=[DUEL_GAGNE if i % 4 == 0 else DUEL_PERDU]) for i in range(1, 31)] +
                       [_course(100 + i, 3 + i % 4) for i in range(12)])
        self.C = N.compter(self.F)
        self.A = N.agreger([self.C])
        self.T = N.tableaux(self.A)

    def test_joueur(self):
        q = N.joueur(self.A, self.T, "AAA_QB1")
        self.assertEqual((q["name"], q["pos"], q["team"]), ("AAA QB1", "QB", "AAA"))
        h = q["headline"]
        self.assertEqual((h["k"], h["group"], h["qualified"], h["rank"], h["of"]), ("tt", "Passing", True, 1, 1))  # sans modèles
        M = N.entrainer([self.F])
        T = N.tableaux(N.agreger([N.compter(self.F, M)]), M)
        self.assertEqual(N.joueur(N.agreger([N.compter(self.F, M)]), T, "AAA_QB1")["headline"]["k"], "cpoe")
        self.assertEqual([g["key"] for g in q["groups"]], ["passing"])
        self.assertTrue(all(x["rank"] == 1 for x in q["groups"][0]["stats"] if x["v"] is not None))
        e = N.joueur(self.A, self.T, "BBB_EDGE1")
        self.assertEqual(e["headline"]["k"], "prwr")
        self.assertAlmostEqual(e["headline"]["v"], round(7 / 30, 3), places=3)    # gagné sur i = 4, 8, … 28 (7 fois)
        self.assertEqual(N.joueur(self.A, self.T, "ZZZ_QB1")["headline"], None)    # inconnu : rien, sans erreur

    def test_pas_encore_qualifie(self):
        F = _feed([_passe(i, "complete", 9) for i in range(1, 6)])
        A = N.agreger([N.compter(F)]); T = N.tableaux(A)
        h = N.joueur(A, T, "AAA_QB1")["headline"]
        self.assertFalse(h["qualified"]); self.assertIsNone(h["rank"])
        self.assertEqual((h["n"], h["min"]), (5, ["att", 14]))

    def test_rang_dans_le_bon_sens(self):
        rows = [{"v": {"x": v}} for v in (0.1, 0.3, 0.2)]
        self.assertEqual(N._rang(rows, "x", 1, 0.3), 1)
        self.assertEqual(N._rang(rows, "x", -1, 0.3), 3)
        self.assertEqual(N._rang(rows, "x", 0, 0.1), 3)

    def test_equipe_et_match(self):
        e = N.equipe(self.T, "AAA")
        self.assertEqual((e["team"], e["games"], e["of"]), ("AAA", 1, 2))
        self.assertEqual(len(e["stats"]), len(N.EQUIPES["cols"]))
        self.assertIsNone(N.equipe(self.T, "ZZZ"))
        m = N.match(self.C, None, self.T["_ligue"])
        aaa = next(x for x in m["teams"] if x["team"] == "AAA")
        self.assertEqual([p["role"] for p in aaa["players"]], ["QB", "Target", "Carrier"])
        self.assertEqual(aaa["players"][1]["v"]["share"], 1.0)                 # la part des cibles : celles du match
        bbb = next(x for x in m["teams"] if x["team"] == "BBB")
        self.assertEqual([p["role"] for p in bbb["players"]], ["Rusher"])
        peu = N.compter(_feed([_passe(1, "complete", 9), _course(2, 4)]))         # un match : pas de seuil
        aaa = next(x for x in N.match(peu, None, self.T["_ligue"])["teams"] if x["team"] == "AAA")
        self.assertEqual([p["role"] for p in aaa["players"]], ["QB", "Target", "Carrier"])


class Ngs6(unittest.TestCase):
    """NGS-6 : zones des passes, couloirs des courses, cartes, récompenses, historique, formatage."""
    def test_zones_et_couloirs(self):
        geo = {"cov": {"r": [["WR1", 0, 0, "X", [[0, 200], [120, 100]], []]]}}
        self.assertEqual(N.zone_passe(geo, "WR1", 24.0), ("L", "i"))             # 14 yd à gauche, 12 yd de profondeur
        self.assertEqual(N.zone_passe(geo, "WR1", 14.0, prof=25), ("M", "d"))    # profondeur de la route, au milieu
        self.assertEqual(N.zone_passe(geo, "WR1", 2.0, prof=-2), ("R", "b"))
        self.assertIsNone(N.zone_passe(geo, "TE", 24.0))
        self.assertIsNone(N.zone_passe({}, "WR1", 24.0))
        self.assertEqual(N.couloir_course({"side": "L", "cls": "outside"}), "LO")
        self.assertEqual(N.couloir_course({"side": "R", "cls": "gap"}), "RI")
        self.assertIsNone(N.couloir_course({"cls": "inside"}))

    def test_cartes(self):
        def passe(i, res, y_fin, prof):
            P = _passe(i, res, 12 if res == "complete" else 0, prof=prof)
            P["ball_y"] = 25.0
            P["geo"]["cov"] = {"r": [["WR1", 0, 0, "X", [[0, 250], [prof * 10, y_fin * 10]], []]]}
            return P
        F = _feed([passe(1, "complete", 10, 5), passe(2, "incomplete", 10, 5), passe(3, "complete", 40, 25),
                   _course(10, 6), _course(11, -1)])
        for P in F["plays"][3:]:
            P["geo"]["side"] = "R"
        c = N.compter(F)["players"]
        ch = N.cartes(c["AAA_QB1"])
        self.assertEqual(sorted(ch["pass"]), [["L", "s", 2, 1, 12, 0, 0], ["R", "d", 1, 1, 12, 0, 0]])
        self.assertEqual(N.cartes(c["AAA_WR1"])["pass"], ch["pass"])           # le receveur ciblé : la même carte
        self.assertEqual(N.cartes(c["AAA_RB1"])["run"], [["RI", 2, 5, 0]])
        A = N.agreger([N.compter(F)])
        self.assertEqual(N.joueur(A, N.tableaux(A), "AAA_QB1")["charts"], ch)
        self.assertEqual(N.ligue_cartes(A)["pass"], sorted(ch["pass"], key=lambda x: ("LMR".index(x[0]), "bsid".index(x[1]))))

    def test_recompenses_et_historique(self):
        F = _feed([_passe(i, "complete", 9, tt=1.5 + i / 100) for i in range(1, 30)])
        A = N.agreger([N.compter(F)]); T = N.tableaux(A)
        aw = N.recompenses(T)
        self.assertIn("Fastest release", [a["title"] for a in aw])
        self.assertEqual(next(a for a in aw if a["col"] == "tt")["id"], "AAA_QB1")
        self.assertEqual(N.recompenses(None), [])
        H = N.historique([(7, A, T), (8, A, T)], "AAA_QB1", "AAA QB1")
        self.assertEqual([h["week"] for h in H], [7, 8])
        self.assertEqual(N.historique([(7, A, T)], "AAA_QB1", "Un autre"), [])     # un autre joueur au même poste
        self.assertEqual(N.historique([(7, A, T)], "AAA_QB1", "AAA QB1", ("passing", "adot"))[0]["k"], "adot")

    def test_formater(self):
        self.assertEqual([N.formater(1.844, "s"), N.formater(0.1432, "pct"), N.formater(3.94, "pp"),
                          N.formater(-2.5, "sy"), N.formater(273.6, "sn"), N.formater(None, "s"), N.formater(1234, "n")],
                         ["1.84 s", "14.3%", "+3.9 pts", "−2.50 yd", "+274 yd", "—", "1,234"])


class Donnees(unittest.TestCase):
    def test_vrai_match_et_semaine_sans_geo(self):
        semaines = sorted(glob.glob(os.path.join(RACINE, "data", "weeks", "week_*")))
        if not semaines:
            self.skipTest("pas de semaine")
        with open(os.path.join(RACINE, "moteur", "ngs_modeles.json"), encoding="utf-8") as fh:
            M = json.load(fh)
        for w in (semaines[-1], semaines[0]):
            fs = sorted(glob.glob(os.path.join(w, "games", "*.json")))
            if not fs:
                continue
            with open(fs[0], encoding="utf-8") as fh:
                F = json.load(fh)
            C = N.compter(F, M)
            T = N.tableaux(N.agreger([C]), M)
            self.assertEqual(len(T["groups"]), len(N.GROUPES) + 1)
            json.dumps(T)                                              # sérialisable tel quel


class Serveur(ts.Base):
    def setUp(self):
        ts.serveur._TRK_CACHE.clear()

    def _get(self, token=""):
        return json.loads(ts.serveur.api_tracking(token).body)

    def _compte(self, pseudo):
        p = ts.serveur.player_by_login(pseudo)
        if p:
            return p["token"]
        return ts.appel(ts.serveur.api_register, {"pseudo": pseudo, "password": "motdepasse1"})["token"]

    def test_seulement_les_matchs_finis(self):
        tok = self._compte("Trk Pro")
        with mock.patch.dict(os.environ, {"GC_INSIGHTS_USERS": "Trk Pro"}):
            ts.a_l_heure(self.reg[0]["ko"] - 60_000)                    # avant le 1er coup d'envoi : rien
            d = self._get(tok)
            self.assertEqual((d["final"], d["today"]), (0, None))
            self.assertNotIn("groups", d)
            for k in (3, 40):
                t = self.reg[k]["ko"] + 60_000
                ts.a_l_heure(t)
                finis = [g for g in self.w.sched if self.w.status(g, t) == "final" and g.get("result")]
                d = self._get(tok)
                self.assertEqual(d["final"], len(finis))
                eq = next(g for g in d["groups"] if g["key"] == "teams")
                self.assertEqual(sum(r["n"] for r in eq["rows"]), 2 * len(finis))   # matchs joués : finis seulement

    def test_acces(self):
        ts.a_l_heure(self.reg[-1]["end"] + 1000)
        jo = self._compte("Trk Jo")
        invite = ts.appel(ts.serveur.api_new_player, {"name": "Invité"})["token"]
        with mock.patch.dict(os.environ, {"GC_INSIGHTS_USERS": "autre, trk JO"}):
            p = self._get(jo)
            self.assertTrue(p["pro"])
            self.assertEqual([g["key"] for g in p["groups"]][-1], "teams")
            self.assertTrue(p["models"])
            for tok in ("", invite, "inconnu"):
                d = self._get(tok)
                self.assertFalse(d["pro"])
                self.assertNotIn("groups", d)
                self.assertTrue(d["today"] and d["today"]["name"])      # la stat du jour : gratuite
                self.assertEqual(d["today"], p["today"])

    def test_interrupteur(self):
        for env in ({"GC_TRACKING": "off"}, {"GC_INSIGHTS": "off"}):
            with mock.patch.dict(os.environ, env):
                with self.assertRaises(ts.HTTPException) as e:
                    ts.serveur.api_tracking("")
                self.assertEqual(e.exception.status_code, 404)
                self.assertNotIn('"tracking":true', ts.serveur.page().body.decode())
        with mock.patch.dict(os.environ, {"GC_TRACKING": "on", "GC_INSIGHTS": "on"}):
            self.assertIn('"tracking":true', ts.serveur.page().body.decode())

    def test_fiches_ngs5(self):
        t = self.reg[40]["ko"] + 60_000
        ts.a_l_heure(t)
        jo = self._compte("Trk Fiche")
        finis = [g for g in self.w.sched if self.w.status(g, t) == "final" and g.get("result")]
        pas_fini = next(g for g in self.w.sched if self.w.status(g, t) != "final")
        qb = finis[0]["home"] + "_QB1"
        with mock.patch.dict(os.environ, {"GC_INSIGHTS_USERS": "Trk Fiche"}):
            libre = json.loads(ts.serveur.api_tracking_player(qb, "").body)
            self.assertEqual(libre["headline"]["k"], "cpoe")                     # la stat phare : gratuite
            self.assertNotIn("groups", libre)
            pro = json.loads(ts.serveur.api_tracking_player(qb, jo).body)
            self.assertTrue(pro["groups"]) ; self.assertEqual(pro["headline"], libre["headline"])
            for bad in ("", "qb1", "<x>", "AAA-QB1"):
                with self.assertRaises(ts.HTTPException) as e:
                    ts.serveur.api_tracking_player(bad, jo)
                self.assertEqual(e.exception.status_code, 400)
            a, b = finis[0]["home"], finis[0]["away"]
            d = json.loads(ts.serveur.api_tracking_team(a, b, jo).body)
            self.assertEqual([x["team"] for x in d["teams"]], [a, b])
            for args in ((a, "", ""), (a, b, "")):                              # sans compte Pro : verrouillé
                with self.assertRaises(ts.HTTPException) as e:
                    ts.serveur.api_tracking_team(*args)
                self.assertEqual(e.exception.status_code, 403)
            with self.assertRaises(ts.HTTPException) as e:
                ts.serveur.api_tracking_team(a, a, jo)
            self.assertEqual(e.exception.status_code, 400)
            m = json.loads(ts.serveur.api_tracking_game(finis[0]["id"], jo).body)
            self.assertEqual({x["team"] for x in m["teams"]}, {a, b})
            with self.assertRaises(ts.HTTPException) as e:                       # un match pas fini : rien
                ts.serveur.api_tracking_game(pas_fini["id"], jo)
            self.assertEqual(e.exception.status_code, 404)
            with self.assertRaises(ts.HTTPException) as e:
                ts.serveur.api_tracking_game(finis[0]["id"], "")
            self.assertEqual(e.exception.status_code, 403)
        with mock.patch.dict(os.environ, {"GC_TRACKING": "off"}):
            for fn, args in ((ts.serveur.api_tracking_player, (qb, "")), (ts.serveur.api_tracking_team, (a, "", jo)),
                             (ts.serveur.api_tracking_game, (finis[0]["id"], jo))):
                with self.assertRaises(ts.HTTPException) as e:
                    fn(*args)
                self.assertEqual(e.exception.status_code, 404)

    def test_ngs6_recompenses_cartes_historique(self):
        jo = self._compte("Trk Six")
        ts.a_l_heure(self.reg[40]["ko"] + 60_000)                            # semaine en cours : pas de récompenses
        self.assertNotIn("awards", self._get())
        ts.a_l_heure(max(g["end"] for g in self.w.sched) + 60_000)            # semaine finie : les récompenses, pour tous
        ts.serveur._TRK_CACHE.clear()
        d = self._get()
        self.assertEqual(len(d["awards"]), len(_ngs_du_jour()))
        qb = d["awards"][0]["id"]
        with mock.patch.dict(os.environ, {"GC_INSIGHTS_USERS": "Trk Six"}):
            p = json.loads(ts.serveur.api_tracking_player(qb, jo).body)
            self.assertTrue(p["charts"].get("pass")) ; self.assertTrue(p["league_charts"].get("pass"))
            self.assertEqual(p["history"][-1]["week"], self.w.doc["week"]["index"])
            libre = json.loads(ts.serveur.api_tracking_player(qb, "").body)
            for k in ("charts", "league_charts", "history"):
                self.assertNotIn(k, libre)

    def test_temps_semaine_entiere(self):
        ts.a_l_heure(self.reg[-1]["end"] + 1000)
        ts.serveur._TRK_MATCH.clear()
        t0 = time.time(); self._get(); t1 = time.time()
        ts.serveur._TRK_CACHE.clear()
        self._get(); t2 = time.time()
        self.assertLess(t1 - t0, 30)                 # ≈ 5 s pour 279 matchs, une fois par semaine et par démarrage
        self.assertLess(t2 - t1, 2)                  # ensuite : les comptes d'un match sont gardés


if __name__ == "__main__":
    unittest.main()
