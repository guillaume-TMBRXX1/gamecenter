"""Mesure de l'audience (promotion, étape 9.1 — serveur.py) : interrupteur GC_MESURE (sans lui : rien de compté, liens
courts et /admin/stats en 404, /legal inchangée), visites de l'accueil par source (Referer réduit au nom du site),
robots et préchargements à part, liens courts /tt /ig /yt /r/<source>, tableau de bord (clé, essais limités, semaines
de Bruxelles, joueurs / comptes / actifs tirés de la base, comptes exclus). Le tableau de bord dans un navigateur est
vérifié par outils/site/test_mesure.js.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import asyncio
import os
import sys
import tempfile
import unittest
import uuid
from datetime import datetime

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))

try:                                    # le serveur (fastapi) n'est pas installé partout : tests sautés
    os.environ.setdefault("GC_DATA", tempfile.mkdtemp(prefix="gc-mesure-"))
    os.environ.setdefault("GC_PUSH_LOOP", "0")
    sys.path.insert(0, RACINE)
    import serveur
    from fastapi import HTTPException
except Exception:                       # pragma: no cover
    serveur = None

NAVIGATEUR = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
CLE = "k" * 20


def ouvrir(req=None):
    """L'accueil (la page elle-même n'est pas dessinée : le dossier de test n'a pas de semaine, 503 après le comptage)."""
    try:
        serveur.page() if req is None else serveur.page(req)
    except HTTPException as e:
        if e.status_code != 503:
            raise


class Req:
    """Requête minimale pour appeler les routes directement."""
    def __init__(self, headers=None, body=None, method="GET", ip="1.2.3.4"):
        self.headers = {"user-agent": NAVIGATEUR, "host": "snapline.live", "x-forwarded-for": ip}
        self.headers.update(headers or {})
        self.method, self.body, self.client = method, body or {}, None

    async def json(self):
        return self.body


def ms(a, m, j, h=12):
    return int(datetime(a, m, j, h, tzinfo=serveur.TZ).timestamp() * 1000)


@unittest.skipIf(serveur is None, "serveur.py non importable")
class TestMesure(unittest.TestCase):
    def setUp(self):
        self.env = {k: os.environ.get(k) for k in ("GC_MESURE", "GC_ADMIN_KEY", "GC_STATS_EXCLURE")}
        serveur.LOGIN_FAILS.clear()
        with serveur.db() as c:
            tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for t in ("stats_day", "players", "bets", "leagues", "league_members", "push_subs", "chat_messages"):
                if t in tables:                  # base partagée avec les autres tests (chat…) : repartir de zéro
                    c.execute("DELETE FROM " + t)

    def tearDown(self):
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def totaux(self):
        with serveur.db() as c:
            return {r["k"]: r["n"] for r in c.execute("SELECT k, SUM(n) n FROM stats_day GROUP BY k")}

    def joueur(self, cree, login=None, compte=None):
        pid = uuid.uuid4().hex
        with serveur.db() as c:
            c.execute("INSERT INTO players(id, token, name, created, login, acct_at) VALUES(?,?,?,?,?,?)",
                      (pid, uuid.uuid4().hex, login or "Guest", cree, serveur.login_key(login) if login else None, compte))
        return pid

    def pari(self, pid, t):
        with serveur.db() as c:
            c.execute("INSERT INTO bets(id, player, week, key, price_dec, stake, pt) VALUES(?,?,?,?,?,?,?)",
                      (uuid.uuid4().hex, pid, "w", "k", 2.0, 10, t))

    def test_interrupteur_coupe(self):
        os.environ.pop("GC_MESURE", None)
        os.environ["GC_ADMIN_KEY"] = CLE
        ouvrir(Req({"referer": "https://www.google.com/"}))
        self.assertEqual(self.totaux(), {})
        for f in (serveur.lien_tt, serveur.lien_ig, serveur.lien_yt):
            with self.assertRaises(HTTPException) as e:
                f(Req())
            self.assertEqual(e.exception.status_code, 404)
        with self.assertRaises(HTTPException):
            serveur.lien_r(Req(), "hn")
        with self.assertRaises(HTTPException) as e:
            serveur.admin_stats_page()
        self.assertEqual(e.exception.status_code, 404)
        with self.assertRaises(HTTPException) as e:
            asyncio.run(serveur.api_admin_stats(Req(body={"key": CLE}, method="POST")))
        self.assertEqual(e.exception.status_code, 404)
        self.assertNotIn("short links", serveur.legal().body.decode())

    def test_sources(self):
        cas = {None: "direct", "": "direct", "https://www.google.be/": "google", "https://www.google.com/search?q=x": "google",
               "https://www.bing.com/": "bing", "https://duckduckgo.com/": "duckduckgo",
               "https://www.tiktok.com/@snapline.live": "tiktok", "android-app://com.zhiliaoapp.musically/": "tiktok",
               "https://l.instagram.com/?u=x": "instagram", "https://lm.facebook.com/": "facebook",
               "https://m.youtube.com/": "youtube", "https://youtu.be/x": "youtube",
               "https://old.reddit.com/r/SideProject/": "reddit", "https://news.ycombinator.com/item?id=1": "hackernews",
               "https://www.producthunt.com/posts/snapline": "producthunt", "https://t.co/abc": "x", "https://x.com/": "x",
               "https://bsky.app/": "bluesky", "https://snapline.live/legal": "site", "https://exemple.org/": "autre",
               "pas une adresse": "direct", "http://[::1": "direct"}
        for ref, src in cas.items():
            self.assertEqual(serveur.source_visite(ref, "snapline.live"), src, ref)
        self.assertEqual(serveur.source_visite("http://localhost:8000/legal", "localhost:8000"), "site")

    def test_visites(self):
        os.environ["GC_MESURE"] = "1"
        ouvrir(Req({"referer": "https://www.google.be/"}))
        ouvrir(Req({"referer": "https://www.google.fr/"}))
        ouvrir(Req())
        ouvrir(Req({"user-agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}))
        ouvrir(Req({"user-agent": "facebookexternalhit/1.1"}))
        ouvrir(Req({"user-agent": ""}))
        ouvrir(Req({"sec-purpose": "prefetch;prerender"}))
        ouvrir(Req(method="HEAD"))
        ouvrir()                                         # appel interne (tests) : rien
        self.assertEqual(self.totaux(), {"visite": 3, "visite:google": 2, "visite:direct": 1, "robot": 3})

    def test_liens_courts(self):
        os.environ["GC_MESURE"] = "1"
        r = serveur.lien_tt(Req())
        self.assertEqual((r.status_code, r.headers["location"]), (302, "/"))
        self.assertEqual(r.headers["x-robots-tag"], "noindex")
        serveur.lien_tt(Req())
        serveur.lien_ig(Req())
        serveur.lien_yt(Req({"user-agent": "TikTokSpider"}))          # aperçu du lien : pas compté, mais redirigé
        serveur.lien_r(Req(), "reddit-sideproject")
        serveur.lien_r(Req(method="HEAD"), "hn")
        for faux in ("", "HN", "a" * 25, "-x", "x/y", "x.y"):
            with self.assertRaises(HTTPException, msg=faux):
                serveur.lien_r(Req(), faux)
        self.assertEqual(self.totaux(), {"lien:tt": 2, "lien:ig": 1, "lien:reddit-sideproject": 1})

    def test_tableau_de_bord_cle(self):
        os.environ["GC_MESURE"] = "1"
        os.environ.pop("GC_ADMIN_KEY", None)
        with self.assertRaises(HTTPException) as e:                   # sans clé posée : fermé
            asyncio.run(serveur.api_admin_stats(Req(body={"key": ""}, method="POST")))
        self.assertEqual(e.exception.status_code, 403)
        os.environ["GC_ADMIN_KEY"] = CLE
        for _ in range(10):
            with self.assertRaises(HTTPException) as e:
                asyncio.run(serveur.api_admin_stats(Req(body={"key": "faux"}, method="POST", ip="9.9.9.9")))
            self.assertEqual(e.exception.status_code, 403)
        with self.assertRaises(HTTPException) as e:                   # trop d'essais : même la bonne clé attend
            asyncio.run(serveur.api_admin_stats(Req(body={"key": CLE}, method="POST", ip="9.9.9.9")))
        self.assertEqual(e.exception.status_code, 429)
        r = asyncio.run(serveur.api_admin_stats(Req(body={"key": CLE, "semaines": "x"}, method="POST")))
        self.assertEqual(r.headers["cache-control"], "no-store")
        page = serveur.admin_stats_page()
        self.assertIn("noindex", page.headers["x-robots-tag"])
        self.assertIn("/api/admin/stats", page.body.decode())

    def test_semaines(self):
        s = serveur._semaines(3, ms(2026, 10, 28))                    # un mercredi
        self.assertEqual([x[0] for x in s], ["2026-10-26", "2026-10-19", "2026-10-12"])
        self.assertEqual(s[0][1], int(datetime(2026, 10, 26, tzinfo=serveur.TZ).timestamp() * 1000))
        self.assertEqual(s[1][2], s[0][1])                            # semaine du changement d'heure (25/10) : bout à bout
        self.assertEqual(s[1][2] - s[1][1], (7 * 24 + 1) * 3600 * 1000)

    def test_tableau_de_bord(self):
        os.environ["GC_STATS_EXCLURE"] = "Guillaume, autre-inconnu"
        moi = self.joueur(ms(2026, 10, 14), "Guillaume", ms(2026, 10, 14))
        a = self.joueur(ms(2026, 10, 20))                              # invité de la semaine du 19/10
        b = self.joueur(ms(2026, 10, 27), "Bob", ms(2026, 10, 27))     # compte de cette semaine
        self.joueur(ms(2026, 10, 25, 23), "Carla", ms(2026, 10, 26, 1))  # invitée le dimanche, compte le lundi
        for p, t in ((moi, ms(2026, 10, 27)), (a, ms(2026, 10, 27)), (a, ms(2026, 10, 28)), (b, ms(2026, 10, 27)),
                     (a, ms(2026, 10, 21))):
            self.pari(p, t)
        with serveur.db() as c:
            c.execute("INSERT INTO leagues(id, name, code, owner, created) VALUES('L1','Amis','ABCDEF',?,?)", (b, ms(2026, 10, 27)))
            c.execute("INSERT INTO league_members(league, player, joined) VALUES('L1',?,?)", (b, ms(2026, 10, 27)))
            c.execute("INSERT INTO league_members(league, player, joined) VALUES('L1',?,?)", (a, ms(2026, 10, 28)))
            c.execute("INSERT INTO push_subs(endpoint, player, created) VALUES('e1',?,?)", (a, ms(2026, 10, 27)))
        serveur.compter("visite", "visite:tiktok", "lien:tt", jour="2026-10-27")
        serveur.compter("visite", "visite:direct", jour="2026-10-26")
        serveur.compter("visite", jour="2026-10-25")                   # dimanche : semaine d'avant
        serveur.compter("robot", jour="2026-11-02")                    # semaine suivante : hors tableau
        j = serveur.stats_admin(3, ms(2026, 10, 28))
        self.assertEqual(j["depuis"], "2026-10-25")
        self.assertEqual(j["exclus"], 1)
        w0, w1, w2 = j["semaines"]
        self.assertEqual((w0["debut"], w0["visites"], w0["robots"]), ("2026-10-26", 2, 0))
        self.assertEqual(w0["sources"], {"tiktok": 1, "direct": 1})
        self.assertEqual(w0["liens"], {"tt": 1})
        self.assertEqual((w0["joueurs"], w0["comptes"], w0["actifs"], w0["paris"]), (1, 2, 2, 3))
        self.assertEqual((w0["ligues"], w0["adhesions"], w0["rappels"], w0["messages"]), (1, 1, 1, 0))
        self.assertEqual((w1["debut"], w1["visites"], w1["joueurs"], w1["comptes"], w1["actifs"]), ("2026-10-19", 1, 2, 0, 1))
        self.assertEqual((w2["joueurs"], w2["comptes"]), (0, 0))       # Guillaume exclu
        self.assertEqual(j["total"], {"joueurs": 3, "comptes": 2, "ligues": 1, "rappels": 1})
        self.assertEqual(len(serveur.stats_admin(99)["semaines"]), 52)

    def test_page_legale(self):
        os.environ["GC_MESURE"] = "1"
        s = serveur.legal().body.decode()
        self.assertIn("short links", s)
        self.assertIn("no IP address or identifier is kept", s)
        self.assertEqual(s.count("snapline.live/tt"), 1)


if __name__ == "__main__":
    unittest.main()
