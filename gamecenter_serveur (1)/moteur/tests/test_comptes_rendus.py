"""Comptes rendus des matchs (comptes_rendus.py, routes /games, /games/<id> et /weeks/<n> de serveur.py) : points
retrouvés dans le résumé, texte propre sur tous les matchs d'une semaine, rien d'un match pas encore terminé, plan du
site, liens depuis les pages des franchises.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import glob
import json
import os
import re
import sys
import tempfile
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
sys.path.insert(0, RACINE)
import comptes_rendus as cr
from moteur import histoire

SEMAINES = sorted(glob.glob(os.path.join(RACINE, "data", "weeks", "week_*")))

try:                                    # le serveur (fastapi) n'est pas installé partout : tests sautés
    os.environ.setdefault("GC_DATA", tempfile.mkdtemp(prefix="gc-cr-"))
    os.environ.setdefault("GC_PUSH_LOOP", "0")
    import serveur
    from fastapi import HTTPException
except Exception:                       # pragma: no cover
    serveur = None


def texte(s):
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))


class Req:
    base_url = "http://localhost:8000/"


def charger(dossier):
    with open(os.path.join(dossier, "week.json"), encoding="utf-8") as fh:
        doc = json.load(fh)
    return doc


@unittest.skipIf(not SEMAINES, "aucune semaine dans data/weeks")
class TestComptesRendus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dossier = SEMAINES[-2] if len(SEMAINES) > 1 else SEMAINES[-1]
        cls.doc = charger(cls.dossier)

    def feed(self, g):
        with open(os.path.join(self.dossier, g["feed"]), encoding="utf-8") as fh:
            return json.load(fh)

    def page(self, g):
        f = self.feed(g)
        ctx = {"semaine": self.doc["week"]["index"], "date": "Monday 1 January 2026", "conference": "Nexus",
               "bilans": {"home": (1, 0, 0), "away": (0, 1, 0)}}
        return f, cr.page_match(g, f, histoire.feuille_de_match(f), self.doc["teams"], ctx, "https://snapline.live")

    def test_tous_les_matchs(self):
        """Chaque match de la semaine : le résumé des points refait le score final, le texte est propre."""
        for g in self.doc["schedule"]:
            f, s = self.page(g)
            A = cr.analyser(g, f, histoire.feuille_de_match(f))
            tot = {"home": 0, "away": 0}
            for m in A["marques"]:
                tot[m["side"]] += m["pts"]
            self.assertEqual((tot["home"], tot["away"]), (A["sh"], A["sa"]), g["id"])
            self.assertEqual((A["sh"], A["sa"]), (g["result"]["home"], g["result"]["away"]), g["id"])
            t = texte(s)
            self.assertGreater(len(t.split()), 450, g["id"])
            for faux in ("None", "{", "}", "…", "  "):
                self.assertNotIn(faux, t, (g["id"], faux))
            self.assertIsNone(re.search(r"(?<![\d-])1 (catches|carries)\b|(?<!\d)-?1 yards", t), g["id"])
            self.assertIn(f'<link rel="canonical" href="https://snapline.live/games/{g["id"]}">', s)

    def test_finale(self):
        g = next(g for g in self.doc["schedule"] if g["phase"] == "ai_bowl")
        _, s = self.page(g)
        champion = self.doc["teams"][self.doc["champion"]]["name"]
        self.assertIn(f"The {champion} are the champions of Week {self.doc['week']['index']}.", texte(s))

    def test_tournures_fixes(self):
        """La même page à chaque visite (tournures choisies par l'identifiant du match)."""
        g = self.doc["schedule"][0]
        self.assertEqual(self.page(g)[1], self.page(g)[1])

    def test_action(self):
        p = {"result": "touchdown", "call": {"type": "pass"}, "text": "X TD catch, 8 yds", "gain": 8,
             "players": {"carrier": {"name": "Ann Lee"}, "passer": {"name": "Bo Ray"}}}
        self.assertEqual(cr._action(p), "an 8-yard touchdown pass from Bo Ray to Ann Lee")
        p = {"result": "field_goal_good", "call": {"type": "field_goal"}, "text": "Field goal good, 11 yds",
             "players": {"carrier": {"name": "<K>"}}}
        self.assertEqual(cr._action(p), "an 11-yard field goal by &lt;K&gt;")


@unittest.skipIf(serveur is None or not SEMAINES, "serveur.py non importable ou aucune semaine")
class TestRoutesComptesRendus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = serveur.Week(SEMAINES[-1])

    def setUp(self):
        self.avant = (serveur.load_weeks, serveur.now_ms, serveur.league_history)
        serveur.load_weeks = lambda: {self.w.start: self.w}
        serveur.league_history = lambda t, fini=False: {"franchises": [], "seasons": []}
        serveur._RECAPS.clear()

    def tearDown(self):
        serveur.load_weeks, serveur.now_ms, serveur.league_history = self.avant
        serveur._RECAPS.clear()

    def a(self, t):
        serveur.now_ms = lambda: t

    def test_rien_avant_la_fin(self):
        g = self.w.sched[0]
        self.a(g["end"] - 1)                         # en cours : pas de compte rendu, pas dans le plan du site
        with self.assertRaises(HTTPException):
            serveur.game_recap(g["id"], Req())
        self.assertNotIn("/games/" + g["id"], serveur._sitemap_recaps())
        self.a(g["end"])
        self.assertIn("Game recap", serveur.game_recap(g["id"], Req()).body.decode())
        self.assertIn("/games/" + g["id"], serveur._sitemap_recaps())
        with self.assertRaises(HTTPException):
            serveur.game_recap(self.w.sched[-1]["id"], Req())

    def test_semaine_et_index(self):
        g = self.w.sched[0]
        self.a(g["end"])
        s = serveur.week_results(self.w.doc["week"]["index"], Req()).body.decode()
        self.assertIn(f'href="/games/{g["id"]}"', s)
        self.assertNotIn(f'href="/games/{self.w.sched[-1]["id"]}"', s)
        self.assertIn(f'href="/weeks/{self.w.doc["week"]["index"]}"', serveur.games_index(Req()).body.decode())
        with self.assertRaises(HTTPException):
            serveur.week_results(999, Req())

    def test_lien_depuis_la_franchise(self):
        g = self.w.sched[0]
        self.a(g["end"])
        self.assertEqual([r["id"] for r in serveur._derniers_matchs(g["home"], g["end"])], [g["id"]])


if __name__ == "__main__":
    unittest.main()
