"""Front office FO-6 : la draft des supporters côté serveur (serveur.py, section « Front office FO-6 »).

Vérifie : fenêtre (annoncée jusqu'au vendredi 12:00, ouverte jusqu'au verrou, fermée ensuite) ; avant l'ouverture, ni
noms ni notes des prospects ; votent les supporters de la franchise (comptes, franchise tenue depuis le lundi) ; vote
modifiable pendant la fenêtre ; parts après le verrou ; export GC_FANS avec le bloc « draft », lu par le moteur ;
les votes de draft ne se mêlent pas au vote de la semaine ; « Remind me » -> un rappel Web Push à l'ouverture, une
fois ; révélation du lundi (draft de la semaine d'avant) ; interrupteur GC_FRONT_OFFICE=off.

Les semaines publiées n'ont pas encore de draft : une annonce (CTX_WR1, trois prospects tirés par moteur/draft.py) est
posée en mémoire sur la dernière semaine du dépôt, une autre (draft appliquée) sur l'avant-dernière.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import asyncio
import copy
import glob
import os
import sys
import tempfile
import unittest
import uuid
from unittest import mock

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
SEMAINES = sorted(glob.glob(os.path.join(RACINE, "data", "weeks", "week_*")))

try:                                    # le serveur (fastapi) n'est pas installé partout : tests sautés
    os.environ.setdefault("GC_DATA", tempfile.mkdtemp(prefix="gc-draft-"))
    os.environ.setdefault("GC_PUSH_LOOP", "0")
    sys.path.insert(0, RACINE)
    import serveur
    from fastapi import HTTPException
    from moteur import draft as dr
    from moteur import supporters as fo
    from moteur.tests.test_supporters_serveur import Req, question
except Exception:                       # pragma: no cover
    serveur = None

HEURE = 3600 * 1000
NOMS = ([f"Prenom{i}" for i in range(30)], [f"Nom{i}" for i in range(30)])


def annonce(w, pid, cle):
    """Une annonce FO-5 pour `pid`, à partir de l'état des joueurs de la semaine `w`."""
    etat = copy.deepcopy(w.doc["players_next_week"])
    _, a = dr.annonceur()(etat, pid, etat["joueurs"][pid], cle, NOMS, set())
    return a


@unittest.skipIf(serveur is None or len(SEMAINES) < 2, "serveur.py non importable ou moins de deux semaines")
class TestDraftServeur(unittest.TestCase):
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
        cls.docs = {id(x): copy.deepcopy({k: x.doc.get(k) for k in ("fan_vote", "fans", "draft", "drafted")})
                    for x in (cls.prev, cls.w)}
        cls.lundi_suivant = serveur.datetime.fromtimestamp(cls.w.reset / 1000, serveur.TZ).date().isoformat()
        idx = cls.w.doc["week"]["index"]
        cls.w.doc["fan_vote"] = question(cls.lundi_suivant, idx + 1)
        cls.prev.doc["fan_vote"] = question(cls.w.start, idx)
        cls.a = annonce(cls.w, "CTX_WR1", idx)
        cls.w.doc["draft"] = {"version": 1, "for_week": cls.lundi_suivant, "announcements": [cls.a]}
        cls.pa = annonce(cls.prev, "CTX_CB1", idx - 1)            # la draft de la semaine d'avant, appliquée
        cls.prev.doc["draft"] = {"version": 1, "for_week": cls.w.start, "announcements": [cls.pa]}
        haut = next(p for p in cls.pa["prospects"] if p["profile"] == "potentiel")
        cls.w.doc["drafted"] = [{"id": "CTX_CB1", "team": "CTX", "pos": cls.pa["pos"], "retired": cls.pa["retired"],
                                 "profile": "potentiel", "name": haut["name"], "source": "fans", "votes": 6,
                                 "coordinator": cls.pa["coordinator"]}]

    @classmethod
    def tearDownClass(cls):
        for x in (cls.prev, cls.w):
            for k, v in cls.docs[id(x)].items():
                if v is None:
                    x.doc.pop(k, None)
                else:
                    x.doc[k] = v
        for lien in cls.liens:
            os.unlink(lien)
            serveur._WEEKS.pop(os.path.basename(lien)[5:], None)

    def setUp(self):
        with serveur._db_lock, serveur.db() as c:
            c.execute("DELETE FROM fan_votes")
            c.execute("DELETE FROM push_bells")
            c.execute("DELETE FROM push_subs")
            c.execute("DELETE FROM push_sent")
            c.execute("DELETE FROM players WHERE id LIKE 'dr-%'")
        serveur.LOGIN_FAILS.clear()
        self.n = 0
        self.ouv, self.ferm = serveur.draft_fenetre(self.w)
        self.t = self.ouv - 20 * HEURE                          # jeudi : la draft est annoncée
        p = mock.patch.object(serveur, "now_ms", lambda: self.t)
        p.start()
        self.addCleanup(p.stop)

    # ---------- outils ----------
    def joueur(self, equipe="CTX", compte=True, depuis=None):
        self.n += 1
        pid, tok = f"dr-{self.n}-{uuid.uuid4().hex[:6]}", uuid.uuid4().hex
        with serveur._db_lock, serveur.db() as c:
            c.execute("INSERT INTO players(id, token, name, created, login, fav_team, fav_team_at) VALUES(?,?,?,0,?,?,?)",
                      (pid, tok, f"Fan {self.n}", f"fan {self.n} {pid}" if compte else None, equipe, depuis))
        return tok

    def vote(self, tok, choix, pid="CTX_WR1", ip="1.2.3.4"):
        return asyncio.run(serveur.api_draft_vote(Req({"token": tok, "id": pid, "choice": choix}, ip)))

    def refus(self, f, *a, **k):
        with self.assertRaises(HTTPException) as e:
            f(*a, **k)
        return e.exception.status_code, e.exception.detail

    # ---------- fenêtre ----------
    def test_fenetre(self):
        j = serveur.datetime.fromtimestamp(self.ouv / 1000, serveur.TZ)
        self.assertEqual((j.hour, j.minute), (12, 0))
        self.assertEqual(j.date(), serveur.datetime.fromtimestamp(self.w.lock / 1000, serveur.TZ).date())
        self.assertEqual(self.ferm, self.w.lock)
        self.assertEqual(serveur.draft_phase(self.w, self.ouv - 1), "announced")
        self.assertEqual(serveur.draft_phase(self.w, self.ouv), "open")
        self.assertEqual(serveur.draft_phase(self.w, self.ferm), "closed")

    def test_annoncee(self):
        tok = self.joueur()
        r = serveur.api_draft(tok)
        self.assertEqual(r["phase"], "announced")
        self.assertEqual(r["week"], self.lundi_suivant)
        self.assertIsNone(r["reason"])
        d = r["drafts"][0]
        self.assertEqual((d["id"], d["retired"], d["team"]), ("CTX_WR1", self.a["retired"], "CTX"))
        self.assertEqual(set(d["ratings"]), set(self.a["ratings"]))
        self.assertEqual([p["profile"] for p in d["prospects"]], list(dr.PROFILS))
        for p in d["prospects"]:                                     # ni noms ni notes avant l'ouverture
            self.assertEqual(set(p), {"profile", "label"})
        self.assertNotIn("coordinator", d)
        self.assertNotIn("result", d)
        self.assertEqual(serveur.api_draft(self.joueur("VEC"))["drafts"], [])     # une autre franchise
        self.assertEqual(self.refus(self.vote, tok, "pret"), (409, "draft_not_open"))

    def test_ouverte_et_vote(self):
        self.t = self.ouv + HEURE
        tok = self.joueur()
        d = serveur.api_draft(tok)["drafts"][0]
        self.assertEqual([p["name"] for p in d["prospects"]], [p["name"] for p in self.a["prospects"]])
        self.assertTrue(all({"ovr", "potential", "dev", "ratings", "iq", "age"} <= set(p) for p in d["prospects"]))
        self.assertNotIn("result", d)                                # parts cachées jusqu'au verrou
        self.assertEqual(self.vote(tok, "potentiel")["my_pick"], "potentiel")
        self.assertEqual(self.vote(tok, "intelligence")["my_pick"], "intelligence")      # modifiable
        self.assertEqual(serveur.api_draft(tok)["my_picks"], {"CTX_WR1": "intelligence"})
        with serveur.db() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM fan_votes").fetchone()[0], 1)
        self.assertEqual(serveur.fans_counts(self.lundi_suivant), {})     # le vote de la semaine n'en voit rien
        self.assertEqual(self.refus(self.vote, self.joueur("VEC"), "pret"), (409, "not_your_team"))
        self.assertEqual(self.refus(self.vote, self.joueur(compte=False), "pret"), (403, "account_required"))
        self.assertEqual(self.refus(self.vote, self.joueur(depuis=self.w.monday + HEURE), "pret"), (409, "team_changed"))
        self.assertEqual(self.refus(self.vote, tok, "star"), (400, "unknown_choice"))
        self.assertEqual(self.refus(self.vote, tok, "pret", pid="CTX_QB1"), (404, "unknown_draft"))
        self.assertEqual(self.refus(self.vote, "inconnu", "pret")[0], 401)

    def test_fermee_resultat_et_export(self):
        self.t = self.ouv + HEURE
        toks = [self.joueur() for _ in range(7)]
        for i, tok in enumerate(toks):
            self.vote(tok, "potentiel" if i < 5 else "pret", ip=f"9.9.9.{i}")
        self.t = self.ferm
        self.assertEqual(self.refus(self.vote, toks[0], "pret"), (409, "draft_closed"))
        r = serveur.api_draft(toks[0])
        res = r["drafts"][0]["result"]
        self.assertEqual((res["votes"], res["choice"], res["source"]), (7, "potentiel", "fans"))
        self.assertEqual(res["pct"], {"pret": 29, "potentiel": 71, "intelligence": 0})
        self.assertEqual(r["my_picks"], {"CTX_WR1": "potentiel"})
        _, doc = serveur.fans_export(self.lundi_suivant)
        self.assertEqual(doc["draft"]["CTX_WR1"]["choice"], "potentiel")
        self.assertEqual(doc["draft"]["CTX_WR1"]["votes"], 7)
        choix = dr.lire_choix(doc, self.lundi_suivant)                          # lu tel quel par le moteur
        self.assertEqual(dr.choix_supporters(self.a, choix["CTX_WR1"]), ("potentiel", "fans", 7))
        self.assertEqual(doc["teams"], {})                                      # aucun vote sur le levier

    def test_moins_de_cinq_votes(self):
        self.t = self.ouv + HEURE
        for i in range(3):
            self.vote(self.joueur(), "intelligence", ip=f"8.8.8.{i}")
        self.t = self.ferm + 1
        res = serveur.api_draft(self.joueur())["drafts"][0]["result"]
        self.assertEqual((res["choice"], res["source"]), (self.a["coordinator"], "coordinators"))

    def test_rappel(self):
        tok = self.joueur()
        self.assertTrue(asyncio.run(serveur.api_draft_remind(Req({"token": tok, "on": True})))["on"])
        self.assertTrue(serveur.api_draft(tok)["reminder"])
        with serveur.db() as c:
            pid = c.execute("SELECT id FROM players WHERE token=?", (tok,)).fetchone()[0]
        with serveur._db_lock, serveur.db() as c:
            c.execute("INSERT INTO push_subs(endpoint, player, p256dh, auth, fav, created) VALUES(?,?,?,?,0,0)",
                      ("https://push.example/1", pid, "p" * 20, "a" * 20))
        with mock.patch.dict(os.environ, {"GC_PUSH_FAKE": "1"}):
            serveur.PUSH_LOG.clear()
            self.assertEqual(serveur.push_tour(self.ouv - 60_000), 0)          # pas avant l'ouverture
            self.t = self.ouv + 60_000
            n = serveur.push_tour(self.t)
            self.assertEqual(n, 1)
            msg = serveur.PUSH_LOG[-1]
            self.assertEqual(msg["title"], "Draft day is open")
            self.assertIn(self.a["retired"], msg["body"])
            self.assertEqual(msg["url"], "/?myteam=draft")
            self.assertEqual(serveur.push_tour(self.t + 60_000), 0)            # une seule fois
        self.assertEqual(self.refus(lambda: asyncio.run(serveur.api_draft_remind(Req({"token": tok, "on": True})))),
                         (409, "no_upcoming_draft"))                          # la draft est ouverte

    def test_revelation_du_lundi(self):
        tok = self.joueur()
        prev = serveur.api_draft(tok)["previous"]
        self.assertEqual(prev["week"], self.w.start)
        d = prev["drafts"][0]
        self.assertEqual((d["id"], d["drafted"]["source"], d["drafted"]["profile"]), ("CTX_CB1", "fans", "potentiel"))
        self.assertIn("result", d)
        self.assertTrue(all("name" in p for p in d["prospects"]))
        self.assertIsNone(serveur.api_draft(self.joueur("VEC"))["previous"])

    def test_interrupteur(self):
        with mock.patch.dict(os.environ, {"GC_FRONT_OFFICE": "off"}):
            self.assertEqual(self.refus(serveur.api_draft, self.joueur()), (404, "front_office_off"))
            self.assertEqual(self.refus(self.vote, self.joueur(), "pret")[0], 404)


if __name__ == "__main__":
    unittest.main()
