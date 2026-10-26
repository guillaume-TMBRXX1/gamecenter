"""Chat (bloc 3, étape 1 — serveur.py, section « chat »).

Vérifie : l'interrupteur GC_CHAT (off : routes en 404, /api/delta sans rien de plus ; read : lecture seule ; on),
lecture libre et écriture réservée aux comptes (compte trop récent, pseudo réservé, banni), nettoyage du texte
(caractères invisibles et de direction, une ligne, 280 caractères), filtre de mots (refusé, masqué, aucun faux positif
sur des phrases ordinaires), liens et coordonnées refusés, débit (3 s, 10 par minute, doublons, une même adresse),
signalements (un par compte, masqué au 3e, pas de nouveau masquage après l'avis de l'administrateur), effacement par
l'auteur, administration (clé, masquer avec motif montré à l'auteur, bannir, lever, message de l'équipe), purge
(30 jours, GC_CHAT_DAYS, plafond), salon de match (position bornée au direct, score ou fin de match renvoyés au point le
plus loin connu, lecture d'un replay à sa position avec les messages à venir à part, salon fermé avant l'heure),
équipes citées et messages « spoiler » dans General, tampon et retraits, aucun id interne ni jeton dans les réponses.
Aucun test ne lit l'horloge : les instants viennent du calendrier de la semaine.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import asyncio
import glob
import json
import os
import sys
import tempfile
import unittest
import uuid

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
SEMAINES = sorted(glob.glob(os.path.join(RACINE, "data", "weeks", "week_*")))

try:                                    # le serveur (fastapi) n'est pas installé partout : tests sautés
    os.environ.setdefault("GC_DATA", tempfile.mkdtemp(prefix="gc-chat-"))
    os.environ.setdefault("GC_PUSH_LOOP", "0")
    sys.path.insert(0, RACINE)
    import serveur
    from fastapi import HTTPException
except Exception:                       # pragma: no cover
    serveur = None

CLE = "une-cle-admin-assez-longue-pour-les-tests"
JOUR = 24 * 3600 * 1000


class Req:
    """Requête minimale (corps JSON, adresse du client, type du contenu)."""
    def __init__(self, body=None, ip="1.2.3.4", ct="application/json"):
        self.body, self.headers = body or {}, {"x-forwarded-for": ip, "content-type": ct}
        self.client = None

    async def json(self):
        return self.body


def run(route, body=None, ip="1.2.3.4", ct="application/json"):
    return asyncio.run(route(Req(body, ip, ct)))


@unittest.skipIf(serveur is None or not SEMAINES, "serveur.py non importable ou pas de semaine")
class TestChat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nom = os.path.basename(SEMAINES[-1])
        cls.lien = os.path.join(serveur.WEEKS_DIR, cls.nom)
        cls.ajoute = not os.path.exists(cls.lien)
        if cls.ajoute:
            os.symlink(SEMAINES[-1], cls.lien)
        cls.w = serveur.load_weeks()[cls.nom[5:]]
        cls.g = next(g for g in cls.w.sched if g["phase"] == "regular")
        cls.T = cls.g["ko"] + 40 * 60 * 1000           # 40 min après le premier coup d'envoi : match en direct
        cls.salle = f"m:{cls.w.start}:{cls.g['id']}"
        cls.env = {k: os.environ.get(k) for k in ("GC_CHAT", "GC_CHAT_DAYS", "GC_ADMIN_KEY")}

    @classmethod
    def tearDownClass(cls):
        if cls.ajoute:
            os.unlink(cls.lien)
            serveur._WEEKS.pop(cls.nom[5:], None)
        for k, v in cls.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def setUp(self):
        os.environ["GC_CHAT"] = "on"
        os.environ["GC_ADMIN_KEY"] = CLE
        os.environ.pop("GC_CHAT_DAYS", None)
        serveur._chat_init()
        with serveur._db_lock, serveur.db() as c:
            for t in ("chat_messages", "chat_reports", "chat_bans", "chat_actions"):
                c.execute(f"DELETE FROM {t}")
            c.execute("DELETE FROM players WHERE id LIKE 'ch-%'")
        for k in ("rate", "ip", "dup", "reports"):
            serveur._CHAT[k].clear()
        serveur._CHAT["rooms"].clear()
        serveur._CHAT["purged"] = None
        serveur.LOGIN_FAILS.clear()
        self.n = 0

    # ---- outils ----
    def joueur(self, compte=True, nom=None, acct_at=0, team=None):
        self.n += 1
        pid, tok = f"ch-{self.n}-{uuid.uuid4().hex[:6]}", uuid.uuid4().hex
        nom = nom or f"Fan {self.n}"
        with serveur._db_lock, serveur.db() as c:
            c.execute("INSERT INTO players(id, token, name, created, login, acct_at, fav_team) VALUES(?,?,?,0,?,?,?)",
                      (pid, tok, nom, serveur.login_key(nom) if compte else None, acct_at if compte else None, team))
        return serveur.player_by_token(tok)

    def poste(self, p, texte, t, salle="general", at=None, ip=None):
        return serveur.chat_post(p, salle, texte, at, ip, t)["msg"]

    def refus(self, code, fn, *a, **k):
        with self.assertRaises(HTTPException) as e:
            fn(*a, **k)
        self.assertEqual(e.exception.detail, code)
        return e.exception.status_code

    def lire(self, salle="general", **k):
        return serveur.chat_read(salle, t=k.pop("t", self.T), **k)

    # ---- interrupteur ----
    def test_interrupteur(self):
        os.environ["GC_CHAT"] = "off"
        self.assertNotIn("chat", serveur.api_delta(""))
        with self.assertRaises(HTTPException) as e:
            serveur.api_chat("general")
        self.assertEqual(e.exception.status_code, 404)
        for route in (serveur.api_chat_status, serveur.api_chat_post, serveur.api_chat_report, serveur.api_chat_delete):
            with self.assertRaises(HTTPException) as e:
                run(route, {})
            self.assertEqual(e.exception.status_code, 404)
        self.assertEqual(serveur.chat_mode(), "off")
        os.environ["GC_CHAT"] = "n'importe quoi"
        self.assertEqual(serveur.chat_mode(), "off")
        os.environ["GC_CHAT"] = "read"
        d = serveur.api_delta("")
        self.assertEqual(set(d["chat"]), {"general", "rev"})
        self.assertEqual(serveur.api_chat("general")["msgs"], [])
        self.assertEqual(self.refus("chat_read_only", self.poste, self.joueur(), "hello", self.T), 403)
        os.environ["GC_CHAT"] = "on"
        m = self.poste(self.joueur(), "hello", self.T)
        self.assertEqual(serveur.api_delta("")["chat"]["general"], m["id"])

    def test_page_legale_et_administration(self):
        """Étape 2 : la page reçoit « chat » seulement chat allumé ; page légale et /admin/chat selon l'interrupteur."""
        os.environ["GC_CHAT"] = "off"
        page0 = serveur.page().body.decode()
        legal0 = serveur.legal().body.decode()
        self.assertNotIn('"chat":"', page0)
        self.assertNotIn('id="chat"', legal0)
        self.assertNotIn("__DAYS__", legal0)
        with self.assertRaises(HTTPException) as e:
            serveur.admin_chat_page()
        self.assertEqual(e.exception.status_code, 404)
        for mode in ("read", "on"):
            os.environ["GC_CHAT"] = mode
            self.assertIn('"chat":"%s"' % mode, serveur.page().body.decode())
        os.environ["GC_CHAT_DAYS"] = "14"
        legal = serveur.legal().body.decode()
        self.assertIn('<section id="chat">', legal)
        self.assertLess(legal.index('<section id="chat">'), legal.index('<section id="legal">'))
        self.assertIn("<b>Chat</b> (accounts only", legal)
        self.assertIn("deleted automatically after\n      14 days", legal)
        self.assertIn("except chat messages (14 days)", legal)
        self.assertNotIn("__DAYS__", legal)
        r = serveur.admin_chat_page()
        self.assertEqual(r.headers["x-robots-tag"], "noindex, nofollow")
        self.assertIn("Modération du chat", r.body.decode())

    # ---- qui écrit ----
    def test_lecture_libre_ecriture_comptes(self):
        invite, a = self.joueur(compte=False), self.joueur(team="CTX")
        self.assertEqual(self.refus("account_required", self.poste, invite, "salut", self.T), 403)
        self.assertEqual(self.refus("account_required", self.poste, None, "salut", self.T), 403)
        m = self.poste(a, "  Great   drive\nby the offense  ", self.T)
        self.assertEqual(m["b"], "Great drive by the offense")
        self.assertEqual((m["n"], m["t"], m["ts"]), (a["name"], "CTX", self.T))
        self.assertEqual(m["a"], serveur.chat_author(a["id"]))
        self.assertEqual(len(m["a"]), 10)
        r = self.lire()
        self.assertEqual([x["id"] for x in r["msgs"]], [m["id"]])
        self.assertEqual(r["last"], m["id"])
        st = serveur.chat_status(invite, self.T)
        self.assertEqual((st["can_write"], st["why"]), (False, "account_required"))
        st = serveur.chat_status(a, self.T)
        self.assertEqual((st["can_write"], st["a"], st["max_len"]), (True, m["a"], 280))
        self.assertEqual(serveur.chat_status(None, self.T)["a"], None)
        # rien d'interne : ni id de joueur, ni jeton, ni adresse
        tout = json.dumps([r, st, serveur.chat_read("general", after=0, rev=0, t=self.T)])
        for secret in (a["id"], a["token"], "1.2.3.4"):
            self.assertNotIn(secret, tout)
        self.assertNotIn("player", tout)

    def test_compte_recent_pseudo_reserve(self):
        neuf = self.joueur(acct_at=self.T - 5 * 60 * 1000)
        self.refus("account_too_new", self.poste, neuf, "hello", self.T)
        self.assertEqual(serveur.chat_status(neuf, self.T)["why"], "account_too_new")
        self.poste(neuf, "hello", self.T + 10 * 60 * 1000)
        for nom in ("Admin", "Adm1n_Joe", "SnaplineTeam", "the.snapline", "Moderateur", "Staff", "Official CTX"):
            self.refus("pseudo_reserved", self.poste, self.joueur(nom=nom), "hello", self.T)
        for nom in ("Badminton", "CTXsupporter", "Modou", "Systematic"):
            self.poste(self.joueur(nom=nom), "hello " + nom, self.T)

    # ---- texte ----
    def test_nettoyage_et_longueur(self):
        a = self.joueur()
        t = self.T
        self.refus("empty", self.poste, a, "  \u200b\u202e \n ", t)
        self.refus("too_long", self.poste, a, "x" * 281, t)
        m = self.poste(a, "y" * 280, t)
        self.assertEqual(len(m["b"]), 280)
        m = self.poste(a, "\u202egnp.exe\u200b go\u0007 \u2066team\u2069\r\nline two", t + 4000)
        self.assertEqual(m["b"], "gnp.exe go team line two")
        m = self.poste(a, "<img src=x onerror=alert(1)> & \"quotes\"", t + 8000)
        self.assertEqual(m["b"], "<img src=x onerror=alert(1)> & \"quotes\"")   # du texte : la page l'affiche tel quel
        m = self.poste(a, "Go 🏈🔥 team", t + 12000)
        self.assertEqual(m["b"], "Go 🏈🔥 team")

    def test_filtre_de_mots(self):
        a = self.joueur()
        t = [self.T + i * 7000 for i in range(40)]
        for i, x in enumerate(("he is a n1gg3r", "kill yourself", "just kys", "N I G G E R")):
            self.assertEqual(self.refus("message_blocked", self.poste, a, x, t[i]), 400)
        m = self.poste(a, "What a fuuuck!! play", t[5])
        self.assertEqual(m["b"], "What a ******!! play")
        r = serveur.chat_post(a, "general", "putain de match", None, None, t[6])
        self.assertTrue(r["masked"])
        self.assertEqual(r["msg"]["b"], "****** de match")
        self.assertEqual(self.poste(a, "fuсk", t[7])["b"], "****")               # с cyrillique
        ordinaires = ["as good as it gets", "Pass the class, assist the shooter", "Scunthorpe and Essex",
                      "a niggling injury, he flew from Niger", "Raccoon City", "Mr.Smith ran 3.5 yds, e.g. a draw",
                      "the Comet offense is cooking", "Badminton is not football", "hello world", "pro and con",
                      "Dickens wrote that", "great pedal", "a bass guitar"]
        for i, x in enumerate(ordinaires):
            r = serveur.chat_post(a, "general", x, None, None, t[10 + i])
            self.assertEqual((r["msg"]["b"], r["masked"]), (x, False), x)

    def test_liens_et_coordonnees(self):
        a = self.joueur()
        for i, x in enumerate(("see https://evil.com", "go to www.free-coins.io now", "best odds at bet365.com",
                               "promo.xyz/abc")):
            self.refus("links_not_allowed", self.poste, a, x, self.T + i * 4000)
        for i, x in enumerate(("mail me at joe@example.org", "call 0475 12 34 56", "+32 475 123 456")):
            self.refus("contact_not_allowed", self.poste, a, x, self.T + i * 4000)
        self.poste(a, "rules at snapline.live/legal.", self.T + 20000)
        self.poste(a, "https://snapline.live is the place", self.T + 24000)

    # ---- débit ----
    def test_debit(self):
        a, b = self.joueur(), self.joueur()
        t = self.T
        self.poste(a, "un", t)
        self.assertEqual(self.refus("too_fast", self.poste, a, "deux", t + 2999), 429)
        self.poste(b, "un", t + 1000)                                  # un autre compte n'est pas freiné
        for i in range(1, 10):
            self.poste(a, f"message {i}", t + i * 3000)
        self.refus("too_many", self.poste, a, "onze", t + 30000)       # 10 en moins d'une minute
        self.poste(a, "onze", t + 60001)
        self.refus("duplicate", self.poste, a, "Onze!", t + 64000)     # même message (casse, ponctuation)
        self.poste(a, "Onze!", t + 60001 + 2 * 60 * 1000)
        # une même adresse : 30 par minute, tous comptes
        gens = [self.joueur() for _ in range(31)]
        for i, p in enumerate(gens[:30]):
            self.poste(p, f"hi {i}", t + 500_000 + i, ip="9.9.9.9")
        self.refus("too_many", self.poste, gens[30], "hi", t + 500_100, ip="9.9.9.9")
        self.poste(gens[30], "hi", t + 500_100, ip="8.8.8.8")
        self.poste(gens[30], "hi again", t + 600_000, ip="9.9.9.9")

    # ---- signaler, effacer ----
    def test_signalements(self):
        auteur = self.joueur()
        m = self.poste(auteur, "something rude", self.T)
        rev = self.lire()["rev"]
        self.refus("own_message", serveur.chat_report, auteur, m["id"], "abuse", self.T)
        self.refus("account_required", serveur.chat_report, self.joueur(compte=False), m["id"], "abuse", self.T)
        self.refus("message_not_found", serveur.chat_report, self.joueur(), 999999, "abuse", self.T)
        r1, r2, r3, r4 = (self.joueur() for _ in range(4))
        self.assertFalse(serveur.chat_report(r1, m["id"], "abuse", self.T)["hidden"])
        self.assertFalse(serveur.chat_report(r1, m["id"], "spam", self.T)["hidden"])    # le même compte : une fois
        self.assertFalse(serveur.chat_report(r2, m["id"], "nonsense", self.T)["hidden"])
        self.assertTrue(serveur.chat_report(r3, m["id"], "hate", self.T)["hidden"])
        r = self.lire(after=m["id"] - 1, rev=rev)
        self.assertEqual(r["msgs"], [])
        self.assertEqual(r["gone"], [m["id"]])
        self.assertEqual(self.lire()["msgs"], [])
        n = serveur.chat_status(auteur, self.T)["notices"]
        self.assertEqual([(x["id"], x["reason"]) for x in n], [(m["id"], "Hidden after several reports, pending review")])
        rep = run(serveur.api_admin_chat, {"key": CLE, "action": "reports"})["reports"]
        self.assertEqual(rep[0]["id"], m["id"])
        self.assertEqual(rep[0]["reports"], {"abuse": 1, "other": 1, "hate": 1})
        # l'administrateur le laisse : réaffiché, et de nouveaux signalements ne le masquent plus
        run(serveur.api_admin_chat, {"key": CLE, "action": "unhide", "id": m["id"]})
        self.assertEqual([x["id"] for x in self.lire()["msgs"]], [m["id"]])
        self.assertFalse(serveur.chat_report(r4, m["id"], "abuse", self.T)["hidden"])
        self.assertEqual(run(serveur.api_admin_chat, {"key": CLE, "action": "reports"})["reports"], [])
        # 20 signalements par heure au plus
        cible = self.joueur()
        ms = [self.poste(cible, f"msg {i}", self.T + i * 7000) for i in range(10)]
        ms += [self.poste(self.joueur(), f"other {i}", self.T + i * 7000) for i in range(10)]
        for x in ms[:19]:                                         # 19 + celui d'avant = 20 dans l'heure
            serveur.chat_report(r4, x["id"], "spam", self.T + 1000)
        self.refus("too_many", serveur.chat_report, r4, ms[19]["id"], "spam", self.T + 2000)
        serveur.chat_report(r4, ms[19]["id"], "spam", self.T + 3600 * 1000 + 1001)

    def test_effacer_son_message(self):
        a, b = self.joueur(), self.joueur()
        m = self.poste(a, "oops", self.T)
        rev = self.lire()["rev"]
        self.refus("message_not_found", serveur.chat_delete, b, m["id"])
        self.assertEqual(run(serveur.api_chat_delete, {"token": a["token"], "id": m["id"]}), {"ok": True})
        r = self.lire(after=m["id"] - 1, rev=rev)
        self.assertEqual((r["msgs"], r["gone"]), ([], [m["id"]]))
        self.refus("message_not_found", serveur.chat_delete, a, m["id"])

    # ---- administration ----
    def test_administration(self):
        a, b = self.joueur(), self.joueur()
        for k in ("", "faux", CLE + "x"):
            with self.assertRaises(HTTPException) as e:
                run(serveur.api_admin_chat, {"key": k, "action": "reports"})
            self.assertEqual(e.exception.status_code, 403)
        serveur.LOGIN_FAILS.clear()
        os.environ["GC_ADMIN_KEY"] = "courte"                     # clé trop courte : désactivé
        with self.assertRaises(HTTPException):
            run(serveur.api_admin_chat, {"key": "courte", "action": "reports"})
        os.environ["GC_ADMIN_KEY"] = CLE
        for _ in range(10):                                       # essais en série : pause
            with self.assertRaises(HTTPException):
                run(serveur.api_admin_chat, {"key": "faux"}, ip="5.5.5.5")
        with self.assertRaises(HTTPException) as e:
            run(serveur.api_admin_chat, {"key": CLE, "action": "reports"}, ip="5.5.5.5")
        self.assertEqual(e.exception.status_code, 429)
        adm = lambda **k: run(serveur.api_admin_chat, dict(k, key=CLE))
        with self.assertRaises(HTTPException) as e:
            adm(action="rien")
        self.assertEqual(e.exception.status_code, 400)
        m1 = self.poste(a, "first", self.T)
        m2 = self.poste(a, "second", self.T + 4000)
        mb = self.poste(b, "other", self.T + 5000)
        # masquer avec un motif, montré à l'auteur
        adm(action="hide", id=m1["id"], reason="Personal attack")
        self.assertEqual([x["id"] for x in self.lire()["msgs"]], [m2["id"], mb["id"]])
        self.assertEqual(serveur.chat_status(a, self.T)["notices"][0]["reason"], "Personal attack")
        au = adm(action="author", a=m1["a"])
        self.assertEqual([(x["id"], x["hidden"]) for x in au["messages"]], [(m2["id"], False), (m1["id"], True)])
        self.assertNotIn(a["id"], json.dumps(au))
        # bannir 7 jours : ses messages des dernières 24 h masqués, il ne peut plus écrire, il sait pourquoi et jusqu'à quand
        t0 = self.T + 6000
        until = serveur.chat_admin_ban(m1["a"], 7, "Spam", t0)["until"]
        self.assertEqual(until, t0 + 7 * JOUR)
        self.assertEqual([x["id"] for x in self.lire()["msgs"]], [mb["id"]])
        st = serveur.chat_status(a, until - 1)
        self.assertEqual((st["can_write"], st["why"], st["ban"]), (False, "banned", {"until": until, "reason": "Spam"}))
        self.refus("banned", self.poste, a, "let me in", until - 1)
        self.assertTrue(serveur.chat_status(a, until)["can_write"])            # fini à l'heure dite
        # définitif, puis levé
        self.assertIsNone(serveur.chat_admin_ban(m1["a"], 0, "Hate", t0 + 1)["until"])
        self.assertEqual(serveur.chat_status(a, until + 365 * JOUR)["ban"], {"until": None, "reason": "Hate"})
        self.assertEqual(adm(action="reports")["bans"][0]["a"], m1["a"])
        adm(action="unban", a=m1["a"])
        self.assertTrue(serveur.chat_status(a, self.T + 60_000)["can_write"])
        with self.assertRaises(HTTPException) as e:
            adm(action="ban", a="inconnu", days=1)
        self.assertEqual(e.exception.status_code, 404)
        # message de l'équipe : badge, pas de pseudo de joueur
        m = serveur.chat_admin_post("general", "Welcome to the chat!", t0 + 2)["msg"]
        self.assertEqual((m["n"], m["a"], m["adm"]), ("Snapline", "snapline", 1))
        self.assertEqual(self.lire(after=mb["id"])["msgs"][-1]["id"], m["id"])
        # l'administration marche chat coupé
        os.environ["GC_CHAT"] = "off"
        self.assertIn("reports", adm(action="reports"))

    def test_json_obligatoire(self):
        a = self.joueur()
        with self.assertRaises(HTTPException) as e:
            run(serveur.api_chat_post, {"token": a["token"], "room": "general", "body": "hi"}, ct="text/plain")
        self.assertEqual(e.exception.status_code, 415)
        with self.assertRaises(HTTPException) as e:
            run(serveur.api_chat_post, {"token": a["token"]}, ct="application/x-www-form-urlencoded")
        self.assertEqual(e.exception.status_code, 415)
        self.assertEqual(run(serveur.api_chat_status, {"token": a["token"]})["a"], serveur.chat_author(a["id"]))

    # ---- conservation ----
    def test_purge(self):
        a, b = self.joueur(), self.joueur()
        vieux = self.poste(a, "old news", self.T)
        rep = self.joueur()
        serveur.chat_report(rep, vieux["id"], "spam", self.T)
        recent = self.poste(b, "fresh", self.T + 20 * JOUR)
        self.assertEqual(serveur.chat_purge(self.T + 30 * JOUR - 1), 0)
        self.assertEqual(serveur.chat_purge(self.T + 30 * JOUR + 1), 1)
        ids = [x["id"] for x in self.lire(t=self.T + 30 * JOUR + 2)["msgs"]]
        self.assertEqual(ids, [recent["id"]])
        with serveur.db() as c:                                   # le signalement reste (6 mois)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM chat_reports").fetchone()[0], 1)
        serveur.chat_purge(self.T + 181 * JOUR)
        with serveur.db() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM chat_reports").fetchone()[0], 0)
        os.environ["GC_CHAT_DAYS"] = "7"
        self.poste(a, "week old", self.T + 200 * JOUR)
        self.assertEqual(serveur.chat_purge(self.T + 207 * JOUR + 1), 1)
        os.environ["GC_CHAT_DAYS"] = "pas un nombre"
        self.assertEqual(serveur.chat_days(), 30)
        # plafond : les plus anciens partent
        vieux_plafond = serveur.CHAT_MAX_ROWS
        try:
            serveur.CHAT_MAX_ROWS = 3
            ms = [self.poste(self.joueur(), f"m{i}", self.T + 300 * JOUR + i) for i in range(5)]
            self.assertEqual(serveur.chat_purge(self.T + 300 * JOUR + 10), 2)
            self.assertEqual([x["id"] for x in self.lire(t=self.T + 300 * JOUR + 11)["msgs"]], [m["id"] for m in ms[2:]])
        finally:
            serveur.CHAT_MAX_ROWS = vieux_plafond
        # compteurs de débit en mémoire : vidés quand ils ne comptent plus
        self.assertEqual(len(serveur._CHAT["rate"]), 5)                  # les 5 auteurs d'il y a 10 ms
        serveur.chat_purge(self.T + 301 * JOUR + 10)                     # un jour plus tard
        self.assertEqual(serveur._CHAT["rate"], {})
        self.assertEqual(serveur._CHAT["dup"], {})
        # bannissement temporaire fini : retiré
        m = self.poste(a, "x", self.T + 400 * JOUR)
        serveur.chat_admin_ban(m["a"], 1, "spam", self.T + 400 * JOUR)
        serveur.chat_purge(self.T + 402 * JOUR)
        self.assertIsNone(serveur.chat_status(a, self.T + 400 * JOUR)["ban"])

    def test_purge_a_la_lecture(self):
        a = self.joueur()
        self.poste(a, "old", self.T)
        serveur._CHAT["purged"] = self.T + 31 * JOUR - 1000       # purgé il y a moins d'une heure : rien
        self.assertEqual(len(self.lire(t=self.T + 31 * JOUR, after=0)["msgs"]), 1)
        serveur._CHAT["purged"] = self.T + 30 * JOUR
        self.assertEqual(self.lire(t=self.T + 31 * JOUR)["msgs"], [])

    # ---- salon de match ----
    def score_change(self, far):
        """Une position k < far où le score n'est pas 0-0, et ce score."""
        for k in range(far - 1, 0, -1):
            sc = serveur._chat_score_at(self.w, self.g, k)
            if sc != (0, 0) and sc[0] != sc[1]:
                return k, sc
        self.skipTest("pas de point marqué avant ce moment")

    def test_salon_de_match_position(self):
        a = self.joueur()
        T, salle = self.T, self.salle
        far = self.w.revealed_plays(self.g, T)
        self.assertGreater(far, 20)
        t = iter(range(T, T + 10 ** 6, 7000))
        self.assertEqual(self.poste(a, "nice", next(t), salle, at=far + 50)["at"], far)   # jamais plus loin que le direct
        self.assertEqual(self.poste(a, "good run", next(t), salle, at=-3)["at"], 0)
        self.assertEqual(self.poste(a, "big hit", next(t), salle)["at"], far)              # sans position : le direct
        self.assertEqual(self.poste(a, "what a block", next(t), salle, at=5)["at"], 5)
        k, (h, aw) = self.score_change(far)
        self.assertEqual(self.poste(a, f"it's {h}-{aw} now", next(t), salle, at=k)["at"], k)     # le score à ce moment
        self.assertEqual(self.poste(a, f"it's {aw} to {h} now", next(t), salle, at=k)["at"], k)
        self.assertEqual(self.poste(a, f"ends {h + 7}-{aw}", next(t), salle, at=k)["at"], far)   # un autre score
        self.assertEqual(self.poste(a, "they won it", next(t), salle, at=3)["at"], far)          # fin de match
        self.assertEqual(self.poste(a, "overtime incoming", next(t), salle, at=3)["at"], far)
        self.assertEqual(self.poste(a, "Grand Final next", next(t), salle, at=3)["at"], far)

    def test_salon_de_match_ouverture(self):
        a = self.joueur()
        ko = self.g["ko"]
        self.assertEqual(self.refus("room_closed", self.poste, a, "soon", ko - 31 * 60 * 1000, self.salle), 403)
        self.assertEqual(self.poste(a, "soon", ko - 29 * 60 * 1000, self.salle)["at"], 0)
        for salle in ("m:2000-01-01:x", f"m:{self.w.start}:nope", "random", "", "m:" + self.w.start):
            self.assertEqual(self.refus("room_not_found", self.poste, a, "hi", self.T, salle), 404)
            self.refus("room_not_found", serveur.chat_read, salle, t=self.T)
        # finale : affiche inconnue tant que les demi-finales ne sont pas jouées
        f = self.w.final
        if not self.w.teams_known(f, self.T):
            self.refus("room_closed", self.poste, a, "hi", self.T, f"m:{self.w.start}:{f['id']}")

    def test_replay_a_sa_position(self):
        T, salle = self.T, self.salle
        far = self.w.revealed_plays(self.g, T)
        ats = [0, 3, 3, 10, 15, far]
        ms = [self.poste(self.joueur(), f"play note {i}", T + i, salle, at=x) for i, x in enumerate(ats)]
        r = self.lire(salle, after=0, upto=3)
        self.assertEqual([x["id"] for x in r["msgs"]], [m["id"] for m in ms[:3]])
        self.assertEqual([x["id"] for x in r["pending"]], [m["id"] for m in ms[3:]])
        self.assertEqual(r["last"], ms[-1]["id"])
        self.assertEqual(r["far"], far)
        self.assertFalse(r["pend_more"])
        r = self.lire(salle, after=0)                             # le direct : tout
        self.assertEqual(len(r["msgs"]), 6)
        self.assertNotIn("pending", r)
        nouveau = self.poste(self.joueur(), "live now", T + 100, salle, at=far)
        r = self.lire(salle, after=ms[-1]["id"], upto=3)          # ensuite : ce qui arrive, à toutes les positions
        self.assertEqual([(x["id"], x["at"]) for x in r["msgs"]], [(nouveau["id"], far)])
        self.assertNotIn("at", self.poste(self.joueur(), "general", T, "general"))

    # ---- General : équipes citées, spoilers ----
    def test_equipes_et_spoilers(self):
        a = self.joueur()
        t = iter(range(self.T, self.T + 10 ** 6, 4000))
        m = self.poste(a, "CTX 21-17 at the half", next(t))
        self.assertEqual((m["teams"], m["sc"]), (["CTX"], 1))
        m = self.poste(a, "The cortex foxes are rolling", next(t))
        self.assertEqual(m["teams"], ["CTX"])
        self.assertNotIn("sc", m)
        m = self.poste(a, "Comet Stingrays won!", next(t))
        self.assertEqual((m["teams"], m["sc"]), (["CMT"], 1))
        m = self.poste(a, "pls ctx no", next(t))                  # « pls », « ctx » en minuscules : pas des équipes
        self.assertNotIn("teams", m)
        self.assertTrue(serveur.chat_spoilery("final score 31:28"))
        self.assertFalse(serveur.chat_spoilery("great catch by the tight end"))

    # ---- tampon et retraits ----
    def test_tampon_et_pages(self):
        t = iter(range(self.T, self.T + 10 ** 7, 4000))
        gens = [self.joueur() for _ in range(5)]
        ms = [self.poste(gens[i % 5], f"n{i}", next(t)) for i in range(serveur.CHAT_BUF + 60)]
        r = self.lire()
        self.assertEqual([x["id"] for x in r["msgs"]], [m["id"] for m in ms[-serveur.CHAT_FIRST:]])
        r = self.lire(after=ms[-3]["id"])                         # chemin chaud : le tampon
        self.assertEqual([x["id"] for x in r["msgs"]], [m["id"] for m in ms[-2:]])
        self.assertFalse(r["more"])
        r = self.lire(after=ms[5]["id"])                          # très en retard : la base, par pages
        self.assertEqual(len(r["msgs"]), serveur.CHAT_PAGE)
        self.assertTrue(r["more"])
        self.assertEqual(r["msgs"][0]["id"], ms[6]["id"])
        serveur._CHAT["rooms"].clear()                            # rechargé depuis la base (redémarrage)
        self.assertEqual(serveur.chat_last(), ms[-1]["id"])
        # trop de retraits manqués : la page recharge
        rev = self.lire()["rev"]
        for i in range(serveur._CHAT["gone"].maxlen + 5):
            serveur.chat_admin_hide(ms[i % len(ms)]["id"], True, "x", self.T)
        r = self.lire(rev=rev)
        self.assertTrue(r.get("reset"))
        self.assertFalse(self.lire(rev=r["rev"]).get("reset"))


if __name__ == "__main__":
    unittest.main()
