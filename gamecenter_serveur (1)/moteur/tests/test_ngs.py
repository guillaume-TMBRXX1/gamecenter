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
