"""Onglet Insights (README section 77) : moteur/insights.py et /api/insights.

  Calcul      bilans, contre le spread, over / under, chance, force (SRS), indices (seuils), récap du jour
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
