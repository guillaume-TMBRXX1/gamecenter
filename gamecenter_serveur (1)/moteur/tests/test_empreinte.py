"""Empreinte de jeu (moteur/empreinte.py, /api/fingerprint, README section 89).

  Calcul       8 axes (passes, courses en force, motion, play-action, RPO, 4es tentés, blitz, homme), genou exclu,
               fenêtre des derniers matchs, minimum de matchs, ligue, forme arrondie, changements
  Direct       seuls les matchs terminés comptent (rien d'un match en cours ou à venir)
  Accès        forme pour tous ; chiffres, ligue, changements et deux franchises aux comptes Insights seulement
  Interrupteur GC_EMPREINTE=off : ni API ni drapeau dans la page

    python -m unittest moteur.tests.test_empreinte        (depuis « gamecenter_serveur (1) »)
"""
import collections
import importlib.util
import json
import os
import unittest
from unittest import mock

from moteur import empreinte as E
from moteur.tests import test_serveur as ts

ICI = os.path.dirname(os.path.abspath(__file__))


def _p(off, typ, concept, down=1, motion=None, dcon="COVER_3"):
    return {"offense": off, "down": down, "call": {"type": typ, "concept": concept, "motion": motion,
                                                   "defense": {"concept": dcon}}}


class Calcul(unittest.TestCase):
    def test_comptes_d_un_match(self):
        F = {"plays": [_p("home", "pass", "MESH", motion="ORBIT"), _p("home", "run", "POWER", dcon="BLITZ"),
                       _p("home", "run", "INSIDE_RUN"), _p("home", "pass", "BOOT", dcon="MAN"),
                       _p("home", "run", "RPO_READ"), _p("home", "run", "KNEEL"),            # genou : exclu
                       _p("home", "punt", None, down=4), _p("home", "run", "COUNTER", down=4),
                       _p("away", "pass", "FOUR_VERTS", dcon="BLITZ"), _p("away", "run", "TRAP")]}
        M = E.mesurer_match(F, "AAA", "BBB")
        a, b = M["AAA"], M["BBB"]
        self.assertEqual((a["snaps"], a["pass"], a["runs"], a["power"]), (6, 2, 4, 2))
        self.assertEqual((a["motion"], a["pa"], a["rpo"], a["q4"], a["go4"]), (1, 1, 1, 2, 1))
        self.assertEqual((a["dsnaps"], a["blitz"], a["man"]), (2, 1, 0))            # sa défense contre BBB
        self.assertEqual((b["dsnaps"], b["blitz"], b["man"]), (6, 1, 1))
        v = E.valeurs([a])
        self.assertAlmostEqual(v["pass"], 2 / 6)
        self.assertAlmostEqual(v["power"], 0.5)
        self.assertAlmostEqual(v["go4"], 0.5)

    def test_fenetre_minimum_ligue_forme(self):
        m = lambda p: dict(E._vide(), snaps=10, **{"pass": p, "runs": 10 - p, "dsnaps": 10})
        P = {"AAA": [m(8)] * 25, "BBB": [m(4)] * 7, "CCC": [m(6)] * 3}
        r = E.calculer(P)
        self.assertEqual(r["teams"]["AAA"]["games"], E.FENETRE)
        self.assertIsNone(r["teams"]["CCC"]["values"])                 # moins de MIN_MATCHS : pas d'empreinte
        self.assertEqual((r["league"]["min"]["pass"], r["league"]["max"]["pass"]), (0.4, 0.8))
        self.assertAlmostEqual(r["league"]["avg"]["pass"], 0.6)
        self.assertEqual(E.forme(r["league"], r["teams"]["AAA"]["values"])[0], 1.0)
        self.assertEqual(E.forme(r["league"], r["teams"]["BBB"]["values"])[0], 0.0)
        self.assertIsNone(E.publique(r, "CCC")["shape"])
        self.assertIsNone(E.calculer({"AAA": [m(8)] * 9})["league"])  # une seule franchise : pas de ligue

    def test_forme_publique_arrondie(self):
        L = {"min": {k: 0.0 for k in E.CLES}, "max": {k: 1.0 for k in E.CLES}}
        f = E.forme(L, {k: 0.1234 + 0.1 * i for i, k in enumerate(E.CLES)})
        self.assertEqual(f, [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])
        self.assertTrue(all(abs(x * 10 - round(x * 10)) < 1e-9 for x in f))

    def test_changements(self):
        a = {k: 0.2 for k in E.CLES}
        b = dict(a, blitz=0.27, power=0.12, motion=0.23)
        c = E.changements(a, b)
        self.assertEqual([(x["axis"], x["delta"]) for x in c], [("power", -0.08), ("blitz", 0.07)])
        self.assertEqual(c[0]["label"], "Power runs")
        self.assertEqual(E.changements(None, b), [])

    def test_memes_familles_que_la_mesure_de_l_identite(self):
        spec = importlib.util.spec_from_file_location(
            "identite_playbooks", os.path.join(ICI, "..", "..", "outils", "moteur", "identite_playbooks.py"))
        ip = importlib.util.module_from_spec(spec); spec.loader.exec_module(ip)
        self.assertEqual(E.COURSES, ip.COURSES)
        self.assertEqual(E.PLAY_ACTION, set(ip.FAMILLES["play_action"]))
        self.assertEqual(E.RPO, set(ip.FAMILLES["rpo"]))
        self.assertTrue(E.FORCE <= E.COURSES)


class Serveur(ts.Base):
    def setUp(self):
        ts.serveur._EMP_CACHE.clear()

    def _get(self, **k):
        return json.loads(ts.serveur.api_fingerprint(**k).body)

    def _compte(self, pseudo):
        p = ts.serveur.player_by_login(pseudo)
        if p:
            return p["token"]
        return ts.appel(ts.serveur.api_register, {"pseudo": pseudo, "password": "motdepasse1"})["token"]

    def _semaines(self):
        return [x for x in ts.serveur.load_weeks().values()
                if x.doc["week"]["index"] >= ts.serveur.EMPREINTE_DEPUIS and x.monday <= self.w.monday]

    def test_seulement_les_matchs_finis(self):
        if self.w.doc["week"]["index"] < ts.serveur.EMPREINTE_DEPUIS:
            self.skipTest("semaine d'avant les identités de jeu")
        with mock.patch.dict(os.environ, {"GC_INSIGHTS_USERS": "Emma Test"}):
            tok = self._compte("Emma Test")
            for k in (0, 40, 120):
                t = self.reg[k]["ko"] + 60_000
                ts.a_l_heure(t)
                ts.serveur._EMP_CACHE.clear()
                P = collections.defaultdict(list)
                jeux = sorted(((x, g) for x in self._semaines() for g in x.sched if x.status(g, t) == "final"),
                              key=lambda xg: (xg[1]["end"], xg[1]["id"]), reverse=True)
                for x, g in jeux:
                    m = E.mesurer_match(x.feed(g["id"]), g["home"], g["away"])
                    for s in ("home", "away"):
                        P[g[s]].append(m[g[s]])
                attendu = E.calculer(P)
                d = self._get(team="VEC", token=tok)
                self.assertTrue(d["pro"])
                e = d["teams"][0]
                self.assertEqual(e["games"], min(E.FENETRE, len(P["VEC"])))
                ev = (attendu["teams"].get("VEC") or {}).get("values")
                self.assertEqual(e["values"] is None, ev is None)
                if ev:
                    for kk in E.CLES:
                        self.assertAlmostEqual(e["values"][kk], ev[kk], places=3)
                    self.assertEqual(len(d["league"]["avg_pos"]), 8)

    def test_acces(self):
        ts.a_l_heure(self.reg[-1]["end"] + 1000)
        invite = ts.appel(ts.serveur.api_new_player, {"name": "Invité"})["token"]
        with mock.patch.dict(os.environ, {"GC_INSIGHTS_USERS": "Fanny Test"}):
            tok = self._compte("Fanny Test")
            for t in ("", invite, "inconnu"):
                d = self._get(team="MNL", token=t)
                self.assertFalse(d["pro"])
                self.assertNotIn("league", d)
                e = d["teams"][0]
                self.assertEqual(set(e), {"team", "games", "shape"})         # la forme seulement : aucun chiffre
                if e["shape"]:
                    self.assertTrue(all(abs(x * 10 - round(x * 10)) < 1e-9 for x in e["shape"]))
                self.refus(403, ts.serveur.api_fingerprint, "", "MNL", "VEC", t)
            d = self._get(a="MNL", b="VEC", token=tok)
            self.assertEqual([x["team"] for x in d["teams"]], ["MNL", "VEC"])
            self.assertIn("changes", d["teams"][0])
            for bad in (dict(team="ZZZ"), dict(team="mnl"), dict(a="MNL", b="MNL"), dict(a="MNL"), {}):
                self.refus(400, ts.serveur.api_fingerprint, token=tok, **bad)

    def test_interrupteur(self):
        with mock.patch.dict(os.environ, {"GC_EMPREINTE": "off"}):
            self.refus(404, ts.serveur.api_fingerprint, "VEC")
            self.assertFalse(ts.serveur.empreinte_on())


if __name__ == "__main__":
    unittest.main()
