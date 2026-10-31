"""Ligues privées entre amis (bloc 2, étape 7 — serveur.py).

Vérifie : comptes seulement, création (code d'invitation), aperçu et adhésion par code (majuscules ou non, déjà membre),
limites (membres par ligue, ligues par compte), codes faux en série refusés, départ (le créateur passe la main ; ligue
vide supprimée), droits du créateur (renommer, retirer, nouveau code — l'ancien ne marche plus —, supprimer), classement
de la semaine (solde ; qui n'a pas parié vient après, sans rang) et de la saison, réservé aux membres.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import asyncio
import glob
import json
import os
import sys
import tempfile
import time
import unittest
import uuid

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
SEMAINES = sorted(glob.glob(os.path.join(RACINE, "data", "weeks", "week_*")))

try:                                    # le serveur (fastapi) n'est pas installé partout : tests sautés
    os.environ.setdefault("GC_DATA", tempfile.mkdtemp(prefix="gc-ligues-"))
    os.environ.setdefault("GC_PUSH_LOOP", "0")
    sys.path.insert(0, RACINE)
    import serveur
    from fastapi import HTTPException
except Exception:                       # pragma: no cover
    serveur = None


class Req:
    """Requête minimale pour appeler les routes directement (corps JSON, adresse du client)."""
    def __init__(self, body=None, ip="1.2.3.4"):
        self.body, self.headers = body or {}, {"x-forwarded-for": ip}
        self.client = None

    async def json(self):
        return self.body


def run(route, body=None, ip="1.2.3.4"):
    return asyncio.run(route(Req(body, ip)))


@unittest.skipIf(serveur is None or not SEMAINES, "serveur.py non importable ou pas de semaine")
class TestLigues(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nom = os.path.basename(SEMAINES[-1])
        cls.lien = os.path.join(serveur.WEEKS_DIR, cls.nom)
        cls.ajoute = not os.path.exists(cls.lien)
        if cls.ajoute:
            os.symlink(SEMAINES[-1], cls.lien)
        cls.w = serveur.load_weeks()[cls.nom[5:]]

    @classmethod
    def tearDownClass(cls):
        if cls.ajoute:
            os.unlink(cls.lien)
            serveur._WEEKS.pop(cls.nom[5:], None)

    def setUp(self):
        with serveur._db_lock, serveur.db() as c:
            for t in ("leagues", "league_members"):
                c.execute(f"DELETE FROM {t}")
            c.execute("DELETE FROM players WHERE id LIKE 'lg-%'")
            c.execute("DELETE FROM bets WHERE player LIKE 'lg-%'")
        serveur.LOGIN_FAILS.clear()
        self.n = 0

    def joueur(self, compte=True):
        self.n += 1
        pid, tok = f"lg-{self.n}-{uuid.uuid4().hex[:6]}", uuid.uuid4().hex
        with serveur._db_lock, serveur.db() as c:
            c.execute("INSERT INTO players(id, token, name, created, login) VALUES(?,?,?,0,?)",
                      (pid, tok, f"Ami {self.n}", f"ami {self.n} {pid}" if compte else None))
        return {"id": pid, "token": tok}

    def creer(self, p, nom="Les potes"):
        return run(serveur.api_league_create, {"token": p["token"], "name": nom})["league"]

    def erreur(self, route, body, code, ip="1.2.3.4"):
        with self.assertRaises(HTTPException) as e:
            run(route, body, ip)
        self.assertEqual(e.exception.status_code, code, e.exception.detail)
        return e.exception.detail

    def test_comptes_seulement(self):
        invite = self.joueur(compte=False)
        self.assertEqual(self.erreur(serveur.api_league_create, {"token": invite["token"], "name": "X ligue"}, 403), "account_required")
        a = self.joueur()
        L = self.creer(a)
        self.erreur(serveur.api_league_join, {"token": invite["token"], "code": L["code"]}, 403)

    def test_creer_et_rejoindre(self):
        a, b = self.joueur(), self.joueur()
        L = self.creer(a)
        self.assertRegex(L["code"], r"^[A-HJ-NP-Z2-9]{6}$")
        self.assertTrue(L["owner"])
        apercu = serveur.api_league_preview(Req(), code=L["code"].lower(), token=b["token"])
        self.assertEqual((apercu["name"], apercu["members"], apercu["member"]), ("Les potes", 1, False))
        r = run(serveur.api_league_join, {"token": b["token"], "code": L["code"].lower()})
        self.assertEqual((r["league"]["members"], r["league"]["owner"], r["already"]), (2, False, False))
        self.assertTrue(run(serveur.api_league_join, {"token": b["token"], "code": L["code"]})["already"])
        self.assertEqual([x["name"] for x in serveur.api_leagues(b["token"])["leagues"]], ["Les potes"])
        self.erreur(serveur.api_league_create, {"token": a["token"], "name": "<b>"}, 400)
        self.erreur(serveur.api_league_create, {"token": a["token"], "name": "ab"}, 400)

    def test_limites(self):
        a = self.joueur()
        L = self.creer(a)
        old = serveur.LIGUE_MAX_MEMBRES, serveur.LIGUE_MAX_PAR_COMPTE
        try:
            serveur.LIGUE_MAX_MEMBRES = 2
            run(serveur.api_league_join, {"token": self.joueur()["token"], "code": L["code"]})
            self.assertEqual(self.erreur(serveur.api_league_join, {"token": self.joueur()["token"], "code": L["code"]}, 409), "league_full")
            serveur.LIGUE_MAX_PAR_COMPTE = 2
            self.creer(a, "Deuxième")
            self.assertEqual(self.erreur(serveur.api_league_create, {"token": a["token"], "name": "Troisième"}, 409), "too_many_leagues")
        finally:
            serveur.LIGUE_MAX_MEMBRES, serveur.LIGUE_MAX_PAR_COMPTE = old

    def test_codes_faux_en_serie(self):
        a, b = self.joueur(), self.joueur()
        L = self.creer(a)
        for i in range(serveur.JOIN_FAIL_MAX_JOUEUR):
            self.erreur(serveur.api_league_join, {"token": b["token"], "code": "ZZZZZ" + "23456789"[i % 8]}, 404, ip=f"9.9.9.{i}")
        self.assertEqual(self.erreur(serveur.api_league_join, {"token": b["token"], "code": L["code"]}, 429, ip="8.8.8.8"),
                         "too_many_attempts")                    # même le bon code : 15 minutes d'attente

    def test_depart_et_droits_du_createur(self):
        a, b, c = self.joueur(), self.joueur(), self.joueur()
        L = self.creer(a)
        for p in (b, c):
            run(serveur.api_league_join, {"token": p["token"], "code": L["code"]})
        self.erreur(serveur.api_league_rename, {"token": b["token"], "league": L["id"], "name": "Pirates"}, 403)
        self.assertEqual(run(serveur.api_league_rename, {"token": a["token"], "league": L["id"], "name": "Pirates"})["league"]["name"], "Pirates")
        neuf = run(serveur.api_league_code, {"token": a["token"], "league": L["id"]})["league"]["code"]
        self.assertNotEqual(neuf, L["code"])
        self.erreur(serveur.api_league_join, {"token": self.joueur()["token"], "code": L["code"]}, 404)   # ancien lien
        run(serveur.api_league_kick, {"token": a["token"], "league": L["id"], "member": c["id"]})
        self.assertEqual(serveur.api_leagues(c["token"])["leagues"], [])
        run(serveur.api_league_leave, {"token": a["token"], "league": L["id"]})                # le créateur part
        self.assertTrue(serveur.api_leagues(b["token"])["leagues"][0]["owner"])                # b reprend la ligue
        run(serveur.api_league_leave, {"token": b["token"], "league": L["id"]})
        with serveur.db() as cx:
            self.assertIsNone(cx.execute("SELECT 1 FROM leagues WHERE id=?", (L["id"],)).fetchone())   # vide : supprimée
        L2 = self.creer(a, "Autre ligue")
        run(serveur.api_league_join, {"token": b["token"], "code": L2["code"]})
        self.erreur(serveur.api_league_delete, {"token": b["token"], "league": L2["id"]}, 403)
        run(serveur.api_league_delete, {"token": a["token"], "league": L2["id"]})
        self.assertEqual(serveur.api_leagues(b["token"])["leagues"], [])

    def test_classement(self):
        a, b, c = self.joueur(), self.joueur(), self.joueur()
        L = self.creer(a)
        for p in (b, c):
            run(serveur.api_league_join, {"token": p["token"], "code": L["code"]})
        g = next(x for x in self.w.reg if x["result"]["home"] != x["result"]["away"])
        gagnant = "home" if g["result"]["home"] > g["result"]["away"] else "away"
        perdant = "away" if gagnant == "home" else "home"
        with serveur._db_lock, serveur.db() as cx:
            for p, cote in ((a, gagnant), (b, perdant)):
                cx.execute("INSERT INTO bets(id, player, week, key, price_dec, line, stake, pt, title, sub) VALUES(?,?,?,?,?,?,?,?,?,?)",
                           (uuid.uuid4().hex, p["id"], self.w.start, f"{g['id']}:ml:{cote}", 2.0, None, 100.0, g["ko"] - 60000, "t", "s"))
        t = g["end"] + 1000
        old = serveur._OFFSET_MS                       # 31/10 : la semaine en cours est celle de l'horloge du serveur ;
        serveur._OFFSET_MS = t - int(time.time() * 1000)   # avec toutes les semaines chargées (suite complète), elle était
        self.addCleanup(setattr, serveur, "_OFFSET_MS", old)   # celle d'avant tant que la dernière n'a pas commencé
        _, rows = serveur.ligue_classement(L["id"], "week", t)
        self.assertEqual([(r["id"], r["rank"], r["balance"]) for r in rows],
                         [(a["id"], 1, 1100.0), (b["id"], 2, 900.0), (c["id"], None, 1000.0)])
        _, rows = serveur.ligue_classement(L["id"], "season", t)
        self.assertEqual([(r["id"], r["rank"], r["net"]) for r in rows][:2], [(a["id"], 1, 100.0), (b["id"], 2, -100.0)])
        self.assertIsNone(rows[2]["rank"])
        intrus = self.joueur()
        with self.assertRaises(HTTPException) as e:
            serveur.api_league_standings(L["id"], token=intrus["token"])
        self.assertEqual(e.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
