"""Onglet Insights (README section 78) : moteur/insights.py et /api/insights.

  Calcul      bilans, contre le spread, over / under, chance, force (SRS), indices (seuils), récap du jour
              (remontée, grosses actions sans les retours), duels passe / course / pression, écart à la ligne
  Face-à-face confrontations terminées de toutes les semaines (depuis HIST_DEPUIS), joueurs en forme / en méforme
  Direct      seuls les matchs terminés comptent (aucun résultat, aucune action d'un match en cours ou à venir)
  Accès       récap ouvert à tous ; « This week » et « Head-to-head » aux pseudos de GC_INSIGHTS_USERS seulement
  Interrupteur GC_INSIGHTS=off : ni API ni drapeau dans la page

    python -m unittest moteur.tests.test_insights        (depuis « gamecenter_serveur (1) »)
"""
import json
import os
import unittest
from unittest import mock

from moteur import insights
from moteur.tests import test_serveur as ts


def _match(i, home, away, hs, as_, spread=-3.0, total=45.5, p_home=0.6, ml=(-150, 130), jour="2026-10-26", plays=()):
    g = {"id": f"g{i}", "phase": "regular", "kickoff": f"{jour}T10:{i % 60:02d}:00+01:00", "home": home, "away": away,
         "result": {"home": hs, "away": as_}}
    F = {"game": {"pregame_odds": {"p_home": p_home, "p_tie": 0.0, "ml": {"home": ml[0], "away": ml[1]},
                                   "spread_home": spread, "total": total}}, "plays": list(plays)}
    return g, F


def _passe(seq, off, gain, res="complete", down=1, x=50, qb="AAA_QB1", wr="AAA_WR1"):
    return {"seq": seq, "offense": off, "result": res, "gain": gain, "down": down, "los_x": x, "call": {"type": "pass"},
            "players": {"passer": {"id": qb, "name": "Q " + qb}, "carrier": {"id": wr, "name": "R " + wr}},
            "after": {"offense": off, "down": 1}}


class Calcul(unittest.TestCase):
    def test_bilans_spread_total_chance(self):
        jeux = [_match(1, "AAA", "BBB", 30, 20),            # AAA favori -3 : couvre ; 50 > 45,5 : over
                _match(2, "BBB", "AAA", 24, 21, spread=2.5, ml=(120, -140), p_home=0.4),  # BBB outsider gagne
                _match(3, "AAA", "BBB", 20, 20)]            # nul
        d = insights.calculer(jeux)
        a = next(r for r in d["rows"] if r["team"] == "AAA")
        b = next(r for r in d["rows"] if r["team"] == "BBB")
        self.assertEqual((a["gp"], a["w"], a["l"], a["t"]), (3, 1, 1, 1))
        self.assertEqual((b["w"], b["l"], b["t"]), (1, 1, 1))
        self.assertEqual(a["ats"], [1, 2, 0])               # 30-20 couvre -3 ; perd 21-24 (+2,5 pour AAA) ; nul à -3
        self.assertEqual(b["ats"], [2, 1, 0])
        self.assertEqual(a["ou"], [1, 2])
        self.assertAlmostEqual(a["xw"], 0.6 + 0.6 + 0.6, places=1)
        self.assertAlmostEqual(a["luck"], 1.5 - 1.8, places=1)
        self.assertAlmostEqual(a["rating"] + b["rating"], 0, places=1)
        self.assertEqual(d["league"]["games"], 3)
        self.assertEqual(d["league"]["home_w"], round(2 / 3, 3))   # AAA puis BBB gagnent chez eux
        self.assertEqual(d["recaps"]["2026-10-26"]["n_upsets"], 1)
        self.assertEqual(d["recaps"]["2026-10-26"]["upsets"][0]["winner"], "BBB")

    def test_indices_seuils(self):
        peu = [_match(i, "AAA", "BBB", 30, 10) for i in range(insights.MIN_MATCHS - 1)]
        self.assertEqual(insights.calculer(peu)["hints"], [])          # échantillon trop petit : aucun indice
        assez = [_match(i, "AAA", "BBB", 30, 10) for i in range(insights.MIN_MATCHS)]
        h = insights.calculer(assez)["hints"]
        self.assertTrue(h and len(h) <= insights.MAX_HINTS)
        self.assertTrue(any(x["kind"] == "ats" and x["team"] == "AAA" and "covers" in x["text"] for x in h))
        self.assertTrue(any(x["kind"] == "ats" and x["team"] == "BBB" and "fails" in x["text"] for x in h))
        self.assertLessEqual(max(sum(1 for x in h if x["kind"] == k) for k in ("ats", "ou", "luck")), insights.PAR_GENRE)

    def test_actions_et_recap(self):
        plays = [_passe(1, "home", 25, down=3, x=60), _passe(2, "home", 15, res="touchdown", x=95),
                 {"seq": 3, "offense": "away", "result": "run", "gain": 7, "down": 1, "los_x": 60, "call": {"type": "run"},
                  "players": {"carrier": {"id": "BBB_RB1", "name": "Runner"}}},
                 {"seq": 4, "offense": "away", "result": "interception", "gain": 0, "down": 2, "los_x": 60,
                  "call": {"type": "pass"}, "players": {"passer": {"id": "BBB_QB1", "name": "Q"}}},
                 {"seq": 5, "offense": "home", "result": "punt", "gain": 40, "los_x": 30, "call": {}}]
        d = insights.calculer([_match(1, "AAA", "BBB", 7, 0, plays=plays)])
        a = next(r for r in d["rows"] if r["team"] == "AAA")
        b = next(r for r in d["rows"] if r["team"] == "BBB")
        self.assertEqual(a["ypp"], 20.0)                    # 40 yards en 2 actions (le punt ne compte pas)
        self.assertEqual(a["d3"], 1.0)
        self.assertEqual(a["rz"], 1.0)                      # une entrée dans les 20 yards, un touchdown
        self.assertEqual((a["to"], b["to"]), (1, -1))
        self.assertEqual(a["xpl"], 1.0)
        r = d["recaps"]["2026-10-26"]
        self.assertEqual(r["top"]["pass"][0]["yds"], 40)
        self.assertEqual(r["top"]["pass"][0]["vs"], "BBB")
        self.assertEqual(r["top"]["rush"][0]["name"], "Runner")
        self.assertEqual(r["shootout"]["id"], "g1")

    def test_points_duels_marche(self):
        plays = [_passe(1, "home", 12), _passe(2, "home", -6, res="sack"),
                 {"seq": 3, "offense": "home", "result": "run", "gain": 5, "down": 1, "los_x": 40, "call": {"type": "run"},
                  "players": {"carrier": {"id": "AAA_RB1", "name": "R"}}}]
        jeux = [_match(1, "AAA", "BBB", 27, 13, plays=plays), _match(2, "BBB", "AAA", 17, 10, spread=-1.0)]
        d = insights.calculer(jeux)
        a = next(r for r in d["rows"] if r["team"] == "AAA")
        b = next(r for r in d["rows"] if r["team"] == "BBB")
        self.assertEqual((a["ppg"], a["papg"]), (18.5, 15.0))   # les tentatives de passe ne se mêlent pas aux points
        self.assertEqual((a["pya"], a["ypc"], a["skr_a"]), (3.0, 5.0, 0.5))
        self.assertEqual((b["pya_a"], b["ypc_a"], b["skr"]), (3.0, 5.0, 0.5))
        self.assertEqual(a["atsm"], round((14 - 3 + (-7 + 1)) / 2, 1))   # +11 puis -6 contre la ligne
        self.assertEqual(d["league"]["home_margin"], round((14 + 7) / 2, 1))

    def test_remontee_et_grosses_actions(self):
        wp = lambda v: {"seq": 0, "offense": "away", "result": "incomplete", "gain": 0, "win_prob_home": v}
        td = _passe(5, "home", 34, res="touchdown", x=76)
        ret = {"seq": 6, "offense": "away", "result": "touchdown", "gain": -35, "los_x": 35,
               "text": "Zed Quick 99-yd kickoff return …", "players": {"carrier": {"id": "AAA_WR2", "name": "Zed Quick"}}}
        fg = {"seq": 7, "offense": "home", "result": "field_goal_good", "gain": 0, "text": "Field goal good, 52 yds"}
        it = {"seq": 8, "offense": "away", "result": "interception", "gain": 0, "los_x": 50, "call": {"type": "pass"},
              "players": {"passer": {"id": "BBB_QB1", "name": "Q B"}, "defender": {"name": "Ball Hawk", "credit": "INTERCEPTION"}}}
        jeux = [_match(1, "AAA", "BBB", 24, 21, plays=[wp(0.4), wp(0.07), wp(0.9), td, ret, fg, it]),
                _match(2, "CCC", "DDD", 10, 30, plays=[wp(0.5), wp(0.3)])]
        r = insights.calculer(jeux)["recaps"]["2026-10-26"]
        self.assertEqual(r["comeback"], {"id": "g1", "winner": "AAA", "loser": "BBB", "low": 0.07, "score": "24-21"})
        self.assertEqual([(x["name"], x["yds"], x["kind"]) for x in r["big"]["td"]], [("R AAA_WR1", 34, "pass")])  # pas le retour
        self.assertEqual(r["big"]["fg"], [{"game": "g1", "team": "AAA", "vs": "BBB", "yds": 52}])
        self.assertEqual((r["big"]["n_int"], r["big"]["int"][0]["name"], r["big"]["int"][0]["team"]), (1, "Ball Hawk", "AAA"))

    def test_confrontations_et_joueurs(self):
        g = lambda i, h, a, hs, as_: {"id": f"w{i}", "kickoff": f"2026-10-0{i}T10:00:00+02:00", "phase": "regular", "home": h,
                                      "away": a, "result": {"home": hs, "away": as_}, "odds": {"spread_home": -2.5, "total": 44.5}}
        sem = [(2, [g(1, "AAA", "BBB", 20, 17), g(2, "CCC", "AAA", 9, 3)]), (3, [g(3, "BBB", "AAA", 30, 10)])]
        m = insights.confrontations(sem, "BBB", "AAA")
        self.assertEqual([(x["week"], x["home"], x["hs"], x["as"]) for x in m], [(3, "BBB", 30, 10), (2, "AAA", 20, 17)])
        self.assertEqual(m[1]["spread_home"], -2.5)
        r = lambda i, pos, form, depth=1, status="active": {"id": f"AAA_{i}", "name": f"P{i}", "pos": pos, "depth": depth,
                                                             "status": status, "progression": {"ovr": 80, "form": form}}
        j = insights.joueurs([r(1, "QB", 2.5), r(2, "WR", 1.0), r(3, "LT", 2.0), r(4, "RB", 3.0, depth=2),
                              r(5, "CB", -2.0), r(6, "LG", -2.5), r(7, "S", -1.0), r(8, "WR", 2.9, status="out")])
        self.assertEqual([x["id"] for x in j["hot"]], ["AAA_1", "AAA_3", "AAA_2"])     # titulaires, ≥ +1, les meilleurs d'abord
        self.assertEqual([x["id"] for x in j["cold"]], ["AAA_5", "AAA_7"])             # postes clés seulement (pas un garde)

    def test_vide(self):
        d = insights.calculer([])
        self.assertEqual((d["rows"], d["hints"], d["recaps"]), ([], [], {}))
        self.assertIsNone(d["league"]["ppg"])


class Serveur(ts.Base):
    def setUp(self):
        insights_cache = ts.serveur._INS_CACHE
        insights_cache.clear()

    def _get(self, token=""):
        return json.loads(ts.serveur.api_insights(token).body)

    def test_seulement_les_matchs_finis(self):
        reg = self.reg
        for k in (0, 7, 40):                               # au milieu de la journée : matchs finis, en cours, à venir
            t = reg[k]["ko"] + 60_000
            ts.a_l_heure(t)
            finis = [g for g in self.w.sched if self.w.status(g, t) == "final"]
            d = self._get()
            self.assertEqual(d["final"], len(finis))
            jours = {g["kickoff"][:10] for g in finis}
            self.assertEqual(set(d["recaps"]), jours)
            self.assertEqual(sum(r["games"] for r in d["recaps"].values()), len(finis))
            ids = {g["id"] for g in finis}
            for r in d["recaps"].values():
                for u in r["upsets"]:
                    self.assertIn(u["game"], ids)
                for x in (r["shootout"], r["thriller"]):
                    self.assertIn(x["id"], ids)
            with mock.patch.dict(os.environ, {"GC_INSIGHTS_USERS": "Ines Test"}):
                tok = self._compte("Ines Test")
                p = self._get(tok)
                self.assertTrue(p["pro"])
                self.assertEqual(sum(r["gp"] for r in p["rows"]), 2 * len(finis))
                self.assertEqual(p["league"]["games"], len(finis))

    def _compte(self, pseudo):
        p = ts.serveur.player_by_login(pseudo)
        if p:
            return p["token"]
        return ts.appel(ts.serveur.api_register, {"pseudo": pseudo, "password": "motdepasse1"})["token"]

    def test_acces(self):
        ts.a_l_heure(self.reg[-1]["end"] + 1000)
        jo = self._compte("Jo Test")
        invite = ts.appel(ts.serveur.api_new_player, {"name": "Invité"})["token"]
        with mock.patch.dict(os.environ, {"GC_INSIGHTS_USERS": " autre , JO test "}):
            self.assertTrue(self._get(jo)["pro"])          # pseudo sans tenir compte des majuscules ni des espaces
            for tok in ("", invite, "inconnu"):
                d = self._get(tok)
                self.assertFalse(d["pro"])
                self.assertTrue(d["recaps"])                # le récap du jour reste ouvert à tous
                for k in ("rows", "hints", "league"):
                    self.assertNotIn(k, d)
        with mock.patch.dict(os.environ, {"GC_INSIGHTS_USERS": ""}):
            self.assertFalse(self._get(jo)["pro"])

    def test_face_a_face(self):
        t = self.reg[30]["ko"] + 60_000
        ts.a_l_heure(t)
        g = self.reg[0]
        a, b = g["home"], g["away"]
        with mock.patch.dict(os.environ, {"GC_INSIGHTS_USERS": "Ines Test"}):
            tok = self._compte("Ines Test")
            d = json.loads(ts.serveur.api_insights_h2h(a, b, tok).body)
            for m in d["meetings"]:
                self.assertEqual({m["home"], m["away"]}, {a, b})
                self.assertGreaterEqual(m["week"], ts.serveur.HIST_DEPUIS)
            futurs = {x["id"] for x in self.w.sched if self.w.status(x, t) != "final"}
            self.assertFalse(futurs & {m["id"] for m in d["meetings"]})            # rien d'un match pas terminé
            self.assertEqual(set(d["players"]), {a, b})
            for p in d["players"].values():
                self.assertTrue(all(x["form"] >= insights.FORME for x in p["hot"]))
                self.assertTrue(all(x["form"] <= -insights.FORME for x in p["cold"]))
            for bad in ((a, a), ("zz", b), (a, "XXX")):
                with self.assertRaises(ts.HTTPException) as e:
                    ts.serveur.api_insights_h2h(bad[0], bad[1], tok)
                self.assertEqual(e.exception.status_code, 400)
            with self.assertRaises(ts.HTTPException) as e:                          # hors liste : verrouillé
                ts.serveur.api_insights_h2h(a, b, "")
            self.assertEqual(e.exception.status_code, 403)

    def test_interrupteur(self):
        with mock.patch.dict(os.environ, {"GC_INSIGHTS": "off"}):
            with self.assertRaises(ts.HTTPException) as e:
                ts.serveur.api_insights("")
            self.assertEqual(e.exception.status_code, 404)
            self.assertNotIn('"insights":true', ts.serveur.page().body.decode())
        with mock.patch.dict(os.environ, {"GC_INSIGHTS": "on"}):
            self.assertIn('"insights":true', ts.serveur.page().body.decode())


if __name__ == "__main__":
    unittest.main()
