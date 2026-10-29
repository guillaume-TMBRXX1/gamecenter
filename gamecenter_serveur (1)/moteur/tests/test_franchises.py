"""Pages des franchises (pages_franchises.py, routes /teams et /teams/<nom> de serveur.py) : un texte pour chaque
franchise, pages lisibles sans JavaScript, noms échappés, histoire des semaines terminées, redirection depuis
l'abréviation, plan du site.

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
import pages_franchises as pf

SEMAINES = sorted(glob.glob(os.path.join(RACINE, "data", "weeks", "week_*", "week.json")))

try:                                    # le serveur (fastapi) n'est pas installé partout : tests sautés
    os.environ.setdefault("GC_DATA", tempfile.mkdtemp(prefix="gc-fr-"))
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


@unittest.skipIf(not SEMAINES, "aucune semaine dans data/weeks")
class TestPagesFranchises(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SEMAINES[-1], encoding="utf-8") as fh:
            cls.doc = json.load(fh)
        cls.teams, cls.league = cls.doc["teams"], cls.doc["week"]["league"]

    def test_un_texte_par_franchise(self):
        for a in self.teams:
            self.assertIn(a, pf.TEXTES, a)
            self.assertIn(a, pf.STYLE_EN, a)
            self.assertIn(a, pf.COULEURS, a)
            mots = sum(len(p.split()) for p in pf.TEXTES[a]["about"])
            self.assertGreaterEqual(mots, 120, a)

    def test_page_index(self):
        s = pf.page_index(self.teams, self.league, "https://snapline.live")
        for t in self.teams.values():
            self.assertIn('href="/teams/' + pf.slug(t["name"]) + '"', s)
        self.assertIn('<link rel="canonical" href="https://snapline.live/teams">', s)

    def test_page_equipe(self):
        histo = {"team": "CTX", "seasons": 3, "w": 40, "l": 25, "t": 4, "pf": 1700, "pa": 1500, "playoffs": 2,
                 "finals": 1, "titles": 1, "title_weeks": [3]}
        saisons = [{"week": 3, "complete": True, "champion": "CTX", "runner_up": "VEC"}]
        s = pf.page_equipe("CTX", self.teams, self.league, histo, saisons, "https://snapline.live")
        t = texte(s)
        self.assertGreater(len(t.split()), 400)          # du texte lisible sans JavaScript
        self.assertIn("Cortex Foxes", t)
        self.assertIn(self.teams["CTX"]["coordinators"]["offense"], t)
        self.assertIn("40-25-4", t)
        self.assertIn("Week 3: won the Grand Final against the Vector Strikers", t)
        self.assertIn('<link rel="canonical" href="https://snapline.live/teams/cortex-foxes">', s)
        self.assertNotIn("<script src", s)

    def test_echappement(self):
        teams = json.loads(json.dumps(self.teams))
        teams["CTX"]["coordinators"]["offense"] = "<script>x</script>"
        s = pf.page_equipe("CTX", teams, self.league, None, [], "https://snapline.live")
        self.assertNotIn("<script>x", s)
        self.assertIn("&lt;script&gt;x", s)


@unittest.skipIf(serveur is None or not SEMAINES, "serveur.py non importable ou aucune semaine")
class TestRoutesFranchises(unittest.TestCase):
    def setUp(self):
        with open(SEMAINES[-1], encoding="utf-8") as fh:
            doc = json.load(fh)
        semaine = type("W", (), {"doc": doc})()
        self.avant = (serveur._need_week, serveur.current_week, serveur.league_history)
        serveur._need_week = lambda: semaine
        serveur.current_week = lambda t=None: semaine
        serveur.league_history = lambda t, fini=False: {"franchises": [], "seasons": []}

    def tearDown(self):
        serveur._need_week, serveur.current_week, serveur.league_history = self.avant

    def test_routes(self):
        self.assertIn("The 24 franchises", serveur.teams_index(Req()).body.decode())
        self.assertIn("Cortex Foxes", serveur.teams_page("cortex-foxes", Req()).body.decode())
        r = serveur.teams_page("ctx", Req())
        self.assertEqual((r.status_code, r.headers["location"]), (301, "/teams/cortex-foxes"))
        with self.assertRaises(HTTPException):
            serveur.teams_page("inconnue", Req())

    def test_plan_du_site(self):
        xml = serveur.sitemap(Req()).body.decode()
        self.assertIn("<loc>http://localhost:8000/teams</loc>", xml)
        self.assertIn("<loc>http://localhost:8000/teams/cortex-foxes</loc>", xml)
        self.assertEqual(xml.count("<loc>http://localhost:8000/teams/"), 24)


if __name__ == "__main__":
    unittest.main()
