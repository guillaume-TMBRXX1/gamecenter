"""Onglet News (actualites.py, routes /api/news et /api/news/vote de serveur.py, README section 115).

Vérifie : quotas par jour ; seulement des matchs terminés (et leurs blessures) ; textes propres ; même édition à chaque
calcul ; au serveur, rien d'un match pas fini à l'heure donnée, réponses aux questions (modifiables, une ligne par
joueur, résultats seulement après sa réponse, limite en série) et interrupteur GC_NEWS=off.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import asyncio
import glob
import json
import os
import re
import sys
import tempfile
import unittest
import uuid
from collections import Counter
from datetime import datetime
from unittest import mock

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
sys.path.insert(0, RACINE)
import actualites as nw
from moteur import histoire, insights, rivalites

SEMAINES = sorted(glob.glob(os.path.join(RACINE, "data", "weeks", "week_*")))

try:                                    # le serveur (fastapi) n'est pas installé partout : tests sautés
    os.environ.setdefault("GC_DATA", tempfile.mkdtemp(prefix="gc-news-"))
    os.environ.setdefault("GC_PUSH_LOOP", "0")
    import serveur
    from fastapi import HTTPException
except Exception:                       # pragma: no cover
    serveur = None

QUOTAS = {"upset": 1, "ref": 1, "rivalry": nw.RIV_JOUR, "injury": nw.INJ_JOUR, "brief": nw.BREVES_JOUR}
SALE = re.compile(r"None|\{|\}|\ba [aeiou]|\s{2}|\.\.(?!\.)|nan\b")


def semaine(dossier, n=None):
    """Les matchs d'une semaine du dépôt (avec ko et end, comme le serveur), les n premiers à finir si n est donné."""
    d = json.load(open(os.path.join(dossier, "week.json"), encoding="utf-8"))
    jeux = []
    for g in d["schedule"]:
        f = json.load(open(os.path.join(dossier, g["feed"]), encoding="utf-8"))
        ko = int(datetime.fromisoformat(g["kickoff"]).timestamp() * 1000)
        jeux.append(dict(g, ko=ko, end=ko + len(f["plays"]) * 6500))
    jeux.sort(key=lambda g: g["end"])
    if n is not None:
        jeux = jeux[:n]

    def lire(gid):
        g = next(x for x in jeux if x["id"] == gid)
        f = json.load(open(os.path.join(dossier, g["feed"]), encoding="utf-8"))
        return f, histoire.feuille_de_match(f)

    def serie(a, b, avant):
        return rivalites.serie(insights.confrontations([(d["week"]["index"], [g for g in jeux if g["ko"] < avant])], a, b), a, b)
    fini = {g["id"] for g in jeux}
    bl = [x for x in (d.get("injuries") or {}).get("in_week") or [] if x.get("game") in fini]
    return d, jeux, lire, serie, bl


@unittest.skipIf(len(SEMAINES) < 2, "moins de deux semaines dans data/weeks")
class TestEdition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d, cls.jeux, lire, serie, bl = semaine(SEMAINES[-2])        # une semaine complète
        cls.arts = nw.edition(cls.jeux, cls.d["teams"], cls.d["week"]["index"], lire, serie, bl)
        cls.args = (lire, serie, bl)

    def test_rubriques_et_quotas(self):
        kinds = Counter(a["kind"] for a in self.arts)
        for k in ("upset", "ref", "playoff", "ats", "hot", "brief"):
            self.assertGreater(kinds[k], 0, k)
        self.assertEqual(kinds["playoff"], 3)                           # deux demi-finales et la Grand Final
        par_jour = Counter((a["day"], a["kind"]) for a in self.arts)
        for (j, k), n in par_jour.items():
            if k in QUOTAS:
                self.assertLessEqual(n, QUOTAS[k], (j, k))
        for k in ("ats", "hot", "cold"):                                # un seul article par tendance et par semaine
            self.assertLessEqual(kinds[k], 1)
        self.assertEqual(len({a["id"] for a in self.arts}), len(self.arts))

    def test_textes_propres(self):
        for a in self.arts:
            for txt in [a["title"], a["dek"], a["kicker"]] + a["body"]:
                self.assertFalse(SALE.search(txt or ""), (a["id"], txt))
            self.assertTrue(a["title"])
            for x in a["teams"]:
                self.assertIn(x, self.d["teams"])

    def test_questions(self):
        refs = [a for a in self.arts if a["kind"] == "ref"]
        for a in refs:
            self.assertEqual([o["id"] for o in a["question"]["options"]], ["yes", "no"])
            self.assertIn("flag", a["visual"])
        self.assertTrue(all(a["question"] is None for a in self.arts if a["kind"] != "ref"))

    def test_meme_edition(self):
        again = nw.edition(self.jeux, self.d["teams"], self.d["week"]["index"], *self.args, memo={})
        self.assertEqual(json.dumps(again, sort_keys=True), json.dumps(self.arts, sort_keys=True))

    def test_seulement_les_matchs_termines(self):
        n = len(self.jeux) // 3
        d, jeux, lire, serie, bl = semaine(SEMAINES[-2], n)
        fini = {g["id"] for g in jeux}
        fin = max(g["end"] for g in jeux)
        arts = nw.edition(jeux, d["teams"], d["week"]["index"], lire, serie, bl)
        self.assertTrue(arts)
        for a in arts:
            if a["game"]:
                self.assertIn(a["game"], fini)
            self.assertLessEqual(a["at"], fin)
        self.assertFalse([a for a in arts if a["kind"] == "playoff"])


class Req:
    def __init__(self, body=None, ip="1.2.3.4"):
        self.body, self.headers, self.client = body or {}, {"x-forwarded-for": ip}, None

    async def json(self):
        return self.body


@unittest.skipIf(serveur is None or len(SEMAINES) < 2, "serveur.py non importable ou moins de deux semaines")
class TestServeurNews(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.liens = []
        for s in SEMAINES[-2:]:
            lien = os.path.join(serveur.WEEKS_DIR, os.path.basename(s))
            if not os.path.exists(lien):
                os.symlink(s, lien)
                cls.liens.append(lien)
        ws = serveur.load_weeks()
        cls.prev, cls.w = ws[os.path.basename(SEMAINES[-2])[5:]], ws[os.path.basename(SEMAINES[-1])[5:]]
        cls.t = cls.w.monday + (2 * 24 + 12) * 3600 * 1000               # mercredi midi : semaine en cours
        with mock.patch.object(serveur, "now_ms", lambda: cls.t):
            serveur._news_semaine(cls.prev, cls.t)                        # la semaine d'avant, sans attendre le calcul à côté

    @classmethod
    def tearDownClass(cls):
        for lien in cls.liens:
            os.unlink(lien)
            serveur._WEEKS.pop(os.path.basename(lien)[5:], None)
        serveur._NEWS_CACHE.clear()
        serveur._NEWS_MEMO.clear()

    def setUp(self):
        with serveur._db_lock, serveur.db() as c:
            c.execute("DELETE FROM news_votes")
        serveur.LOGIN_FAILS.clear()
        p = mock.patch.object(serveur, "now_ms", lambda: self.t)
        p.start()
        self.addCleanup(p.stop)

    def joueur(self):
        pid, tok = f"nw-{uuid.uuid4().hex[:8]}", uuid.uuid4().hex
        with serveur._db_lock, serveur.db() as c:
            c.execute("INSERT INTO players(id, token, name, created) VALUES(?,?,?,0)", (pid, tok, "Reader"))
        return tok

    def lire(self, tok=""):
        return json.loads(serveur.api_news(tok).body)

    def vote(self, tok, art, choix, ip="1.2.3.4"):
        return asyncio.run(serveur.api_news_vote(Req({"token": tok, "article": art, "choice": choix}, ip)))

    def refus(self, f, *a):
        with self.assertRaises(HTTPException) as e:
            f(*a)
        return e.exception.status_code, e.exception.detail

    def test_rien_d_un_match_pas_fini(self):
        r = self.lire()
        arts = r["articles"]
        self.assertTrue(arts)
        self.assertEqual({a["week"] for a in arts}, {self.prev.doc["week"]["index"], self.w.doc["week"]["index"]})
        par_id = {**self.prev.by, **self.w.by}
        for a in arts:
            self.assertNotIn("impact", a)
            self.assertLessEqual(a["at"], self.t)
            if a["game"]:
                g = par_id[a["game"]]
                x = self.w if a["game"] in self.w.by else self.prev
                self.assertEqual(x.status(g, self.t), "final", a["id"])

    def test_vote(self):
        arts = self.lire()["articles"]
        q = next(a for a in arts if a.get("question"))
        tok = self.joueur()
        self.assertEqual(self.refus(self.vote, "inconnu", q["id"], "yes")[0], 401)
        self.assertEqual(self.refus(self.vote, tok, "w0-r00-ref", "yes"), (404, "unknown_article"))
        self.assertEqual(self.refus(self.vote, tok, q["id"], "maybe"), (400, "unknown_choice"))
        r0 = self.lire(tok)
        self.assertEqual(r0["votes"], {})
        self.assertEqual(r0["results"], {})                         # pas de résultats avant sa réponse
        self.assertEqual(self.vote(tok, q["id"], "yes")["results"], {"yes": 1, "total": 1})
        autre = self.joueur()
        self.vote(autre, q["id"], "no")
        r = self.vote(tok, q["id"], "no")                           # réponse modifiable
        self.assertEqual(r["results"], {"no": 2, "total": 2})
        r1 = self.lire(tok)
        self.assertEqual(r1["votes"], {q["id"]: "no"})
        self.assertEqual(r1["results"][q["id"]]["total"], 2)
        with serveur.db() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM news_votes").fetchone()[0], 2)

    def test_limite_de_reponses(self):
        q = next(a for a in self.lire()["articles"] if a.get("question"))
        tok = self.joueur()
        for i in range(serveur.NEWS_VOTE_MAX_JOUEUR):
            self.vote(tok, q["id"], "yes" if i % 2 else "no")
        self.assertEqual(self.refus(self.vote, tok, q["id"], "yes"), (429, "too_many_attempts"))

    def test_interrupteur(self):
        with mock.patch.dict(os.environ, {"GC_NEWS": "off"}):
            self.assertEqual(self.refus(serveur.api_news, "")[0], 404)
            self.assertEqual(self.refus(self.vote, self.joueur(), "x", "yes")[0], 404)


class TestPage(unittest.TestCase):
    def test_onglet_sur_le_site(self):
        html = open(os.path.join(RACINE, "gamecenter_source.html"), encoding="utf-8").read()
        self.assertIn("const NAV_TABS=NEWS_ON?['live','news','schedule','bets']", html)
        self.assertIn("newsInit();\nnavInit();", html)
        self.assertIn("else if(VIEW==='news') renderNews(t,force);", html)
        self.assertIn("'live','news','schedule','standings'", html)


if __name__ == "__main__":
    unittest.main()
