"""Serveur de direct (serveur.py) : remplace les tests hors dépôt tserver.py, tavance.py, taccounts.py, tparis2.py,
tsearch.py, tadjust.py, perdus (bloc 1, étape 4, 11/10/2026). La recherche (barre du site) est testée dans le navigateur :
outils/site/test_recherche.js.

Le serveur tourne sur une COPIE des données (dossier temporaire, semaines du dépôt en liens symboliques) ; l'horloge du
serveur est déplacée à des moments choisis de la semaine la plus récente. Les fonctions de l'API sont appelées
directement (requête simulée), sans réseau ni httpx. Il faut fastapi (requirements.txt), sinon les tests sont sautés.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)

  Horloge       GC_DEMO_AT (instant fixé, « auto » = 15 min avant le premier match de la dernière semaine)
  Direct        rien d'avance : actions révélées à l'heure (pauses comprises), aucun score ni action future dans
                /api/delta, /api/feed et la page ; résultat public = score du moteur
  Playoffs      affiches cachées jusqu'au verrou du vendredi, finale jusqu'à la fin des demi-finales, classement et
                champion seulement quand ils sont joués
  Paris         simple, combiné, refus (cote, solde, mise, marché fermé), règlement = score du moteur, cash-out,
                historique, semaine fermée
  Comptes       inscription, connexion (limite d'essais, paris d'invité repris), mot de passe, admin, équipe favorite
  Classement    semaine (soldes) et saison (comptes seulement)
  Ajustement    semaines enchaînées : numéro + 1, staffs de départ = staffs ajustés de la semaine d'avant
  Domaine       GC_DOMAINE : l'ancienne adresse *.up.railway.app redirigée (308, chemin et paramètres gardés) ;
                le domaine lui-même, localhost et un serveur sans GC_DOMAINE servent la page
"""
import asyncio
import glob
import json
import os
import sys
import tempfile
import time
import types
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
SEMAINES = sorted(glob.glob(os.path.join(RACINE, "data", "weeks", "week_*")))

try:                                    # même dossier temporaire que test_pauses.py si celui-ci a importé le serveur
    os.environ.setdefault("GC_DATA", tempfile.mkdtemp(prefix="gc-serveur-"))
    sys.path.insert(0, RACINE)
    import serveur
    from fastapi import HTTPException
except Exception as e:                  # pragma: no cover
    serveur, ERREUR = None, e


def _req(body, ip="10.0.0.1"):
    async def _json():
        return body
    return types.SimpleNamespace(json=_json, client=types.SimpleNamespace(host=ip))


def appel(fn, body, ip="10.0.0.1"):
    return asyncio.run(fn(_req(body, ip)))


def a_l_heure(t):
    """L'horloge du serveur indique t (ms)."""
    serveur._OFFSET_MS = t - int(time.time() * 1000)


@unittest.skipUnless(serveur is not None and SEMAINES, "serveur.py non importable (fastapi absent) ou pas de semaine")
class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.realpath(serveur.DATA) == os.path.realpath(os.path.join(RACINE, "data")):
            raise unittest.SkipTest("GC_DATA pointe sur les données du dépôt : les tests écriraient la base des paris")
        for s in SEMAINES:                       # semaines du dépôt, sans copie (lecture seule)
            dst = os.path.join(serveur.WEEKS_DIR, os.path.basename(s))
            if not os.path.exists(dst):
                os.symlink(s, dst)
        serveur.load_weeks()
        cls.w = max(serveur._WEEKS.values(), key=lambda w: w.monday)
        cls.reg = sorted(cls.w.reg, key=lambda g: (g["ko"], g["id"]))
        cls._offset = serveur._OFFSET_MS

    @classmethod
    def tearDownClass(cls):
        serveur._OFFSET_MS = cls._offset

    def joueur(self, nom="Testeur"):
        return appel(serveur.api_new_player, {"name": nom})

    def pick(self, gid, mk="ml", side="home", stake=10.0, t=None):
        q = self.w.quote(f"{gid}:{mk}:{side}", serveur.now_ms() if t is None else t)
        return {"key": f"{gid}:{mk}:{side}", "price_dec": q["price_dec"], "line": q["line"], "stake": stake, "title": gid}

    def parier(self, tok, picks=(), combos=()):
        return appel(serveur.api_bets, {"token": tok, "picks": list(picks), "combos": list(combos)})

    def refus(self, code, fn, *a, **k):
        with self.assertRaises(HTTPException) as cm:
            fn(*a, **k)
        self.assertEqual(cm.exception.status_code, code)
        return cm.exception


class Horloge(Base):
    def test_demo_at(self):
        old = os.environ.get("GC_DEMO_AT")
        try:
            os.environ["GC_DEMO_AT"] = "2026-10-14T12:59:00+02:00"
            serveur._init_clock()
            self.assertLess(abs(serveur.now_ms() - serveur.iso_ms("2026-10-14T12:59:00+02:00")), 2000)
            os.environ["GC_DEMO_AT"] = "auto"
            serveur._init_clock()
            self.assertLess(abs(serveur.now_ms() - (self.w.sched[0]["ko"] - 15 * 60 * 1000)), 2000)
            self.assertIs(serveur.current_week(), self.w)
        finally:
            if old is None:
                os.environ.pop("GC_DEMO_AT", None)
            else:
                os.environ["GC_DEMO_AT"] = old


class Direct(Base):
    def test_avant_le_premier_match_rien_n_est_connu(self):
        g = self.reg[0]
        a_l_heure(g["ko"] - 60_000)
        self.assertIs(serveur.current_week(), self.w)
        d = serveur.api_delta("")
        self.assertEqual(d["plays"], {})
        self.assertTrue(all(x["status"] == "upcoming" and "result" not in x for x in d["state"]["schedule"]))
        self.assertIsNone(d["state"]["standings"])
        self.assertEqual(d["state"]["standings_by_slot"], [])
        self.refus(404, serveur.api_feed, g["id"])

    def test_actions_revelees_a_l_heure(self):
        g = self.reg[0]
        plays = self.w.feeds[g["id"]]["plays"]
        for k in (0, 1, 10, 60, g["n"] - 1):
            fin = g["ko"] + int(g["ends"][k] * 1000)
            self.assertEqual(self.w.revealed_plays(g, fin - 1), k, f"action {k} révélée trop tôt")
            self.assertEqual(self.w.revealed_plays(g, fin + 1), k + 1, f"action {k} pas révélée à l'heure")
        # pendant une pause, rien de nouveau : l'action suivante attend la fin de la pause
        i = next(i for i, p in enumerate(plays) if serveur.break_kind(p))
        pause = serveur.BREAK_SEC[serveur.break_kind(plays[i])]
        self.assertAlmostEqual(g["ends"][i + 1] - g["ends"][i], serveur.PLAY_SEC + pause)
        # /api/delta pendant le match : exactement les actions révélées, rien au-delà, pas de score final
        t = g["ko"] + int(g["ends"][40] * 1000) + 1500
        a_l_heure(t)
        d = serveur.api_delta("")
        r = self.w.revealed_plays(g, serveur.now_ms())
        self.assertGreaterEqual(r, 41)
        self.assertEqual(d["plays"][g["id"]]["plays"], plays[:r])
        d2 = serveur.api_delta(f"{g['id']}:30")
        self.assertEqual(d2["plays"][g["id"]]["from"], 30)
        self.assertEqual(d2["plays"][g["id"]]["plays"], plays[30:r])
        f = serveur.api_feed(g["id"])
        self.assertNotIn("final_score", f["game"])
        self.assertEqual(len(f["plays"]), r)
        x = next(x for x in d["state"]["schedule"] if x["id"] == g["id"])
        self.assertEqual(x["status"], "live")
        self.assertNotIn("result", x)

    def test_page_sans_rien_d_avance(self):
        g = self.reg[0]
        t = g["ko"] + int(g["ends"][20] * 1000) + 500
        b = serveur._page_bundle(self.w, t)
        for gid, f in b["feeds"].items():
            st = self.w.status(self.w.by[gid], t)
            self.assertNotIn("final_score", f.get("game") or {}, gid)
            self.assertEqual(len(f["plays"]), self.w.revealed_plays(self.w.by[gid], t) if st != "upcoming" else 0, gid)
        a_l_heure(t)
        html = serveur.page().body.decode()
        self.assertNotIn("__WEEK__", html)
        self.assertNotIn("__SERVER__", html)

    def test_resultat_public_egal_au_score_du_moteur(self):
        """Score de la fiche du calendrier = score final du GameFeed = score après la dernière action (tous les matchs)."""
        for g in self.w.sched:
            f = self.w.feeds[g["id"]]
            fin = f["plays"][-1]["after"]["score"]
            self.assertEqual((g["result"]["home"], g["result"]["away"]), (fin["home"], fin["away"]), g["id"])
        g = self.reg[0]
        a_l_heure(g["end"] + 1000)
        x = next(x for x in serveur.api_delta("")["state"]["schedule"] if x["id"] == g["id"])
        self.assertEqual(x["status"], "final")
        self.assertEqual(x["result"]["home"], g["result"]["home"])
        f = serveur.api_feed(g["id"])
        self.assertEqual(len(f["plays"]), g["n"])
        self.assertEqual(f["game"]["final_score"], {"home": g["result"]["home"], "away": g["result"]["away"]})


class Playoffs(Base):
    def test_affiches_et_champion_au_bon_moment(self):
        w = self.w
        sf1, fin = sorted(w.semis, key=lambda g: g["ko"])[0], w.final
        last_reg = max(g["end"] for g in w.reg)

        def etat(t):
            a_l_heure(t)
            st = serveur.api_delta("")["state"]
            return st, {x["id"]: x for x in st["schedule"]}

        st, s = etat(min(last_reg, w.lock) - 60_000)              # saison régulière en cours
        self.assertIsNone(s[sf1["id"]]["home"])
        self.assertIsNone(s[fin["id"]]["home"])
        self.assertIsNone(st["standings"])
        self.assertEqual(w.quote(f"{sf1['id']}:ml:home", serveur.now_ms())["locked"], "seeds")
        self.assertIsNone(serveur.api_delta("")["games"][sf1["id"]]["home"])
        st, s = etat(max(last_reg, w.lock) + 60_000)              # verrou passé : demi-finales connues, finale cachée
        self.assertEqual((s[sf1["id"]]["home"], s[sf1["id"]]["away"]), (sf1["home"], sf1["away"]))
        self.assertIsNone(s[fin["id"]]["home"])
        self.assertEqual(st["standings"], w.doc["standings"])
        self.assertIsNone(st["champion"])
        st, s = etat(max(g["end"] for g in w.semis) + 60_000)     # demi-finales jouées : finale connue
        self.assertEqual((s[fin["id"]]["home"], s[fin["id"]]["away"]), (fin["home"], fin["away"]))
        self.assertIsNone(st["champion"])
        st, s = etat(fin["end"] + 60_000)                         # finale jouée : champion
        self.assertEqual((st["champion"], st["runner_up"]), (w.doc["champion"], w.doc["runner_up"]))


class Paris(Base):
    def test_simple_combine_refus_et_reglement(self):
        g1, g2, g3 = self.reg[0], self.reg[1], self.reg[2]
        a_l_heure(g1["ko"] - 120_000)
        p = self.joueur("Parieur")
        tok = p["token"]
        r = self.parier(tok, [self.pick(g1["id"], stake=100), self.pick(g2["id"], "tot", "over", stake=50)])
        self.assertEqual(len(r["accepted"]), 2, r)
        self.assertAlmostEqual(r["balance"], serveur.BANKROLL - 150)
        mauvais = dict(self.pick(g1["id"], "ml", "away"), price_dec=99.0)
        r = self.parier(tok, [mauvais, dict(self.pick(g1["id"]), stake=0.5), dict(self.pick(g1["id"]), stake=5000)])
        self.assertEqual([x["reason"] for x in r["rejected"]], ["price", "stake", "balance"])
        self.assertEqual(r["accepted"], [])
        combo = {"stake": 20, "legs": [self.pick(g1["id"], "ml", "away"), self.pick(g3["id"], "sp", "home")]}
        meme = {"stake": 20, "legs": [self.pick(g1["id"]), self.pick(g1["id"], "tot", "under")]}
        fut = {"stake": 20, "legs": [self.pick(g1["id"]), {"key": "fut:ai_bowl:CTX", "price_dec": 2.0, "line": None}]}
        seul = {"stake": 20, "legs": [self.pick(g1["id"])]}
        r = self.parier(tok, combos=[combo, meme, fut, seul])
        self.assertEqual(len(r["accepted"]), 1, r)
        self.assertEqual(r["accepted"][0]["key"], "combo")
        self.assertEqual([x["reason"] for x in r["rejected"]], ["same_game", "futures", "legs"])
        # match terminé : marché fermé
        a_l_heure(g1["end"] + 1000)
        q =self.w.quote(f"{g1['id']}:ml:home", serveur.now_ms())
        self.assertEqual(q["locked"], "final")
        r = self.parier(tok, [{"key": f"{g1['id']}:ml:home", "price_dec": 2.0, "line": None, "stake": 10}])
        self.assertEqual(r["rejected"][0]["reason"], "closed")
        # règlement, une fois les trois matchs joués : gagné / perdu selon le score du moteur
        a_l_heure(max(g["end"] for g in (g1, g2, g3)) + 1000)
        me = serveur.api_me(tok)
        res = lambda g: (g["result"]["home"], g["result"]["away"])
        attendu = {}
        h, a = res(g1)
        attendu[f"{g1['id']}:ml:home"] = "push" if h == a else "won" if h > a else "lost"
        b2 = next(b for b in me["bets"] if b["key"] == f"{g2['id']}:tot:over")
        tot = sum(res(g2)) - b2["line"]
        attendu[b2["key"]] = "push" if tot == 0 else "won" if tot > 0 else "lost"
        for b in me["bets"]:
            if b["key"] in attendu:
                self.assertEqual(b["st"], attendu[b["key"]], b["key"])
        cb = next(b for b in me["bets"] if b["key"] == "combo")
        l1 = "push" if h == a else "won" if a > h else "lost"
        h3, a3 = res(g3)
        mg = h3 - a3 + cb["legs"][1]["line"]
        l2 = "won" if mg > 0 else "lost" if mg < 0 else "push"
        st = "lost" if "lost" in (l1, l2) else "push" if l1 == l2 == "push" else "won"
        self.assertEqual(cb["st"], st)
        mises = sum(b["stake"] for b in me["bets"])
        self.assertAlmostEqual(me["balance"], round(serveur.BANKROLL - mises + sum(b["ret"] for b in me["bets"]), 2))

    def test_cash_out(self):
        g = self.reg[3]
        a_l_heure(g["ko"] - 60_000)
        tok = self.joueur("Encaisseur")["token"]
        bid = self.parier(tok, [self.pick(g["id"], stake=100)])["accepted"][0]["id"]
        k = next(i for i in range(5, g["n"]) if (self.w.feeds[g["id"]]["plays"][i].get("odds") or {}).get("ml"))
        a_l_heure(g["ko"] + int(g["ends"][max(k, 30)] * 1000) + 500)
        b = serveur.bet_row(serveur.db().execute("SELECT * FROM bets WHERE id=?", (bid,)).fetchone())
        val, why = self.w.cash_value(b, serveur.now_ms())
        self.assertIsNone(why)
        r = appel(serveur.api_cashout, {"token": tok, "id": bid, "amount": val + 50})
        self.assertEqual((r["ok"], r["reason"]), (False, "value"))
        self.assertAlmostEqual(r["amount"], val)
        r = appel(serveur.api_cashout, {"token": tok, "id": bid, "amount": val})
        self.assertTrue(r["ok"], r)
        self.assertAlmostEqual(r["balance"], round(serveur.BANKROLL - 100 + val, 2))
        b = next(x for x in serveur.api_me(tok)["bets"] if x["id"] == bid)
        self.assertEqual((b["st"], b["ret"]), ("cashed", val))
        r = appel(serveur.api_cashout, {"token": tok, "id": bid, "amount": val})
        self.assertFalse(r["ok"])                                  # déjà encaissé

    def test_historique_et_semaine_fermee(self):
        g = self.reg[0]
        a_l_heure(g["ko"] - 60_000)
        tok = self.joueur("Historien")["token"]
        self.parier(tok, [self.pick(g["id"], stake=10)])
        h = serveur.api_history(tok)
        self.assertEqual([x["week"] for x in h["weeks"]], [self.w.start])
        self.assertEqual(h["weeks"][0]["bets"], 1)
        self.assertEqual(serveur.api_history(tok, self.w.start)["bets"][0]["stake"], 10)
        self.refus(404, serveur.api_history, tok, "1999-01-04")
        self.refus(401, serveur.api_history, "inconnu")
        a_l_heure(self.w.reset + 3600_000)                         # semaine finie, la suivante n'existe pas encore
        e = self.refus(409, appel, serveur.api_bets, {"token": tok, "picks": [self.pick(g["id"])]})
        self.assertIn("fermés", e.detail)


class Comptes(Base):
    def setUp(self):
        a_l_heure(self.reg[0]["ko"] - 60_000)

    def test_inscription_et_connexion(self):
        r = appel(serveur.api_register, {"pseudo": "Alice Test", "password": "motdepasse1"})
        self.assertTrue(r["account"])
        self.refus(409, appel, serveur.api_register, {"pseudo": "alice  test", "password": "autremotdepasse"})
        self.refus(400, appel, serveur.api_register, {"pseudo": "A<b>", "password": "motdepasse1"})
        self.refus(400, appel, serveur.api_register, {"pseudo": "Bob Test", "password": "court"})
        self.refus(401, appel, serveur.api_login, {"pseudo": "Alice Test", "password": "faux"}, "10.1.0.1")
        r2 = appel(serveur.api_login, {"pseudo": "ALICE TEST", "password": "motdepasse1"}, "10.1.0.1")
        self.assertEqual(r2["token"], r["token"])

    def test_paris_d_invite_repris(self):
        g = self.reg[0]
        inv = self.joueur("Invité")["token"]
        self.parier(inv, [self.pick(g["id"], stake=25)])
        r = appel(serveur.api_register, {"pseudo": "Carla Test", "password": "motdepasse1", "token": inv})
        self.assertEqual(r["token"], inv)                         # compte posé sur la clé de l'invité : paris gardés
        self.assertEqual(len(serveur.api_me(inv)["bets"]), 1)
        autre = self.joueur("Invité 2")["token"]                  # un autre appareil : ses paris passent sur le compte
        self.parier(autre, [self.pick(self.reg[1]["id"], stake=5)])
        r = appel(serveur.api_login, {"pseudo": "Carla Test", "password": "motdepasse1", "token": autre}, "10.2.0.1")
        self.assertEqual((r["moved"], r["left_behind"]), (0, 1))  # même semaine déjà jouée par le compte : rien mélangé
        nouveau = appel(serveur.api_register, {"pseudo": "Dora Test", "password": "motdepasse1"})["token"]
        r = appel(serveur.api_login, {"pseudo": "Dora Test", "password": "motdepasse1", "token": autre}, "10.2.0.2")
        self.assertEqual(r["moved"], 1)
        self.assertEqual(len(serveur.api_me(nouveau)["bets"]), 1)

    def test_limite_d_essais(self):
        appel(serveur.api_register, {"pseudo": "Eve Test", "password": "motdepasse1"})
        for i in range(serveur.FAIL_MAX_PSEUDO):
            self.refus(401, appel, serveur.api_login, {"pseudo": "Eve Test", "password": "faux"}, f"10.3.0.{i}")
        self.refus(429, appel, serveur.api_login, {"pseudo": "Eve Test", "password": "motdepasse1"}, "10.3.1.1")

    def test_mot_de_passe_et_admin(self):
        tok = appel(serveur.api_register, {"pseudo": "Fred Test", "password": "motdepasse1"})["token"]
        self.refus(401, appel, serveur.api_password, {"token": tok, "old": "faux", "new": "nouveaumdp1"})
        tok2 = appel(serveur.api_password, {"token": tok, "old": "motdepasse1", "new": "nouveaumdp1"})["token"]
        self.assertNotEqual(tok, tok2)
        self.assertIsNone(serveur.player_by_token(tok))           # les autres appareils sont déconnectés
        old = os.environ.get("GC_ADMIN_KEY")
        try:
            os.environ.pop("GC_ADMIN_KEY", None)
            self.refus(403, appel, serveur.api_admin_password, {"key": "", "pseudo": "Fred Test", "password": "x" * 9})
            self.refus(403, serveur.api_backup, "")
            os.environ["GC_ADMIN_KEY"] = "cle-admin-de-test-0123456789"
            self.refus(403, appel, serveur.api_admin_password, {"key": "mauvaise", "pseudo": "Fred Test", "password": "x" * 9})
            self.refus(403, serveur.api_backup, "mauvaise")
            r = appel(serveur.api_admin_password, {"key": "cle-admin-de-test-0123456789", "pseudo": "fred test",
                                                   "password": "reinitialise1"})
            self.assertTrue(r["ok"])
            self.assertIsNone(serveur.player_by_token(tok2))
            appel(serveur.api_login, {"pseudo": "Fred Test", "password": "reinitialise1"}, "10.4.0.1")
        finally:
            if old is None:
                os.environ.pop("GC_ADMIN_KEY", None)
            else:
                os.environ["GC_ADMIN_KEY"] = old

    def test_equipe_favorite(self):
        inv = self.joueur("Invité 3")["token"]
        self.refus(401, appel, serveur.api_fav_team, {"token": inv, "team": "CTX"})
        tok = appel(serveur.api_register, {"pseudo": "Gina Test", "password": "motdepasse1"})["token"]
        self.assertEqual(appel(serveur.api_fav_team, {"token": tok, "team": "ctx"})["fav_team"], "CTX")
        self.refus(400, appel, serveur.api_fav_team, {"token": tok, "team": "ZZZ"})
        self.assertEqual(serveur.api_me(tok)["fav_team"], "CTX")


class Classement(Base):
    def test_semaine_et_saison(self):
        g = self.reg[5]
        a_l_heure(g["ko"] - 60_000)
        prudent = self.joueur("Prudent")["token"]
        joueur = appel(serveur.api_register, {"pseudo": "Hugo Test", "password": "motdepasse1"})["token"]
        self.parier(prudent, [self.pick(g["id"], stake=1)])
        self.parier(joueur, [self.pick(g["id"], "ml", "home", stake=200), self.pick(g["id"], "ml", "away", stake=200)])
        a_l_heure(g["end"] + 1000)
        lb = serveur.api_leaderboard(prudent)
        rangs = {r["name"]: r for r in lb["top"]}
        self.assertTrue(lb["me"]["me"])
        self.assertEqual([r["rank"] for r in lb["top"]], list(range(1, len(lb["top"]) + 1)))
        self.assertEqual([r["balance"] for r in lb["top"]], sorted((r["balance"] for r in lb["top"]), reverse=True))
        self.assertIn("Hugo Test", rangs)
        s = serveur.api_leaderboard(prudent, "season")
        self.assertNotIn("Prudent", {r["name"] for r in s["top"]})   # invité : pas au classement de la saison
        self.assertIsNone(s["me"]["rank"])
        s = serveur.api_leaderboard(joueur, "season")
        self.assertEqual(s["me"]["name"], "Hugo Test")
        self.assertIsNotNone(s["me"]["rank"])


class Ajustement(Base):
    def test_semaines_enchainees(self):
        ws = sorted(serveur._WEEKS.values(), key=lambda w: w.monday)
        for a, b in zip(ws, ws[1:]):
            self.assertEqual(b.doc["week"]["index"], a.doc["week"]["index"] + 1, b.start)
            nxt, dep = a.doc.get("staffs_next_week") or {}, b.doc.get("staffs_at_start") or {}
            communes = set(nxt) & set(dep)
            self.assertTrue(communes, b.start)
            for team in communes:                                 # staffs de départ = staffs ajustés de la semaine d'avant
                for cote in ("offense", "defense"):
                    for k, v in (nxt[team].get(cote) or {}).items():
                        self.assertEqual(dep[team][cote].get(k), v, f"{b.start} {team} {cote}.{k}")

    def test_historique_des_equipes_sans_spoiler(self):
        a_l_heure(self.w.final["end"] - 60_000)                    # finale pas finie : la semaine n'y est pas
        h = serveur.api_teams_history()
        self.assertNotIn(self.w.start, [x["week"] for x in h["weeks"]])
        a_l_heure(self.w.final["end"] + 60_000)
        h = serveur.api_teams_history()
        x = next(x for x in h["weeks"] if x["week"] == self.w.start)
        self.assertEqual(x["champion"], self.w.doc["champion"])


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(serveur is not None, "serveur.py non importable (fastapi absent)")
class Domaine(unittest.TestCase):
    def passe(self, hote, domaine, chemin="/api/health", query=""):
        req = types.SimpleNamespace(headers={"host": hote}, url=types.SimpleNamespace(path=chemin, query=query))
        async def suite(r):
            return "page"
        avant, serveur.DOMAINE = serveur.DOMAINE, domaine
        try:
            return asyncio.run(serveur._vers_le_domaine(req, suite))
        finally:
            serveur.DOMAINE = avant

    def test_ancienne_adresse_redirigee(self):
        r = self.passe("gridironsim.up.railway.app", "snapline.live", "/api/bets", "token=abc&x=1")
        self.assertEqual(r.status_code, 308)
        self.assertEqual(r.headers["location"], "https://snapline.live/api/bets?token=abc&x=1")
        r = self.passe("GridironSim.up.railway.app:443", "snapline.live", "/")
        self.assertEqual(r.headers["location"], "https://snapline.live/")

    def test_pas_de_redirection(self):
        self.assertEqual(self.passe("snapline.live", "snapline.live"), "page")
        self.assertEqual(self.passe("localhost:8108", "snapline.live"), "page")
        self.assertEqual(self.passe("gridironsim.up.railway.app", ""), "page")
