"""Front office FO-2 : le vote des supporters côté serveur (serveur.py, section « Front office FO-2 »).

Vérifie : comptes seulement ; vote pour sa franchise favorite seulement ; vote modifiable jusqu'au verrou du vendredi,
refusé après ; pourcentages cachés avant le verrou ; résultat après (moins de 5 votes ou égalité : le coordinateur) ;
changer de franchise retire le vote et n'autorise le vote qu'au lundi suivant ; export GC_FANS pour le calcul (clé
d'administration, après le verrou, lu tel quel par moteur.supporters) ; limite de votes en série ; résultats de la
semaine d'avant (choix en vigueur) ; interrupteur GC_FRONT_OFFICE=off.

Les semaines publiées n'ont pas encore de question (FO-1 l'écrit à partir de la semaine du 16/11) : une question est
posée sur les deux dernières semaines du dépôt, en mémoire, le temps du test.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import asyncio
import copy
import glob
import json
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
    os.environ.setdefault("GC_DATA", tempfile.mkdtemp(prefix="gc-fans-"))
    os.environ.setdefault("GC_PUSH_LOOP", "0")
    sys.path.insert(0, RACINE)
    import serveur
    from fastapi import HTTPException
    from moteur import supporters as fo
except Exception:                       # pragma: no cover
    serveur = None

ADMIN = "cle-admin-de-test-0123456789"
HEURE = 3600 * 1000


class Req:
    def __init__(self, body=None, ip="1.2.3.4"):
        self.body, self.headers, self.client = body or {}, {"x-forwarded-for": ip}, None

    async def json(self):
        return self.body


def question(semaine_suivante, index):
    lv = fo.levier_de_semaine(index)
    d = fo.LEVIERS[lv]
    return {"version": fo.VERSION, "index": index, "week": semaine_suivante, "lever": lv, "label": d["label"],
            "question": d["question"], "side": d["side"], "setting": d["setting"],
            "options": [{"id": o, "label": l} for o, l in d["options"]],
            "teams": {a: {"current": 2, "bands": [1, 3], "values": {}} for a in ("CTX", "VEC", "AEG", "MNL")}}


@unittest.skipIf(serveur is None or len(SEMAINES) < 2, "serveur.py non importable ou moins de deux semaines")
class TestVoteSupporters(unittest.TestCase):
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
        cls.docs = {id(x): copy.deepcopy({k: x.doc.get(k) for k in ("fan_vote", "fans")}) for x in (cls.prev, cls.w)}
        cls.lundi_suivant = serveur.datetime.fromtimestamp(cls.w.reset / 1000, serveur.TZ).date().isoformat()
        idx = cls.w.doc["week"]["index"]
        cls.prev.doc["fan_vote"] = question(cls.w.start, idx)
        cls.w.doc["fan_vote"] = question(cls.lundi_suivant, idx + 1)
        cls.w.doc["fans"] = {"lever": cls.prev.doc["fan_vote"]["lever"],
                             "applied": {"CTX": {"choice": "agressif", "source": "fans", "votes": 9}}}

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
            c.execute("DELETE FROM players WHERE id LIKE 'fo-%'")
        serveur.LOGIN_FAILS.clear()
        self.n = 0
        self.t = self.w.lock - 24 * HEURE                    # jeudi soir : le vote est ouvert
        p = mock.patch.object(serveur, "now_ms", lambda: self.t)
        p.start()
        self.addCleanup(p.stop)

    # ---------- outils ----------
    def joueur(self, equipe="CTX", compte=True, depuis=None):
        self.n += 1
        pid, tok = f"fo-{self.n}-{uuid.uuid4().hex[:6]}", uuid.uuid4().hex
        with serveur._db_lock, serveur.db() as c:
            c.execute("INSERT INTO players(id, token, name, created, login, fav_team, fav_team_at) VALUES(?,?,?,0,?,?,?)",
                      (pid, tok, f"Fan {self.n}", f"fan {self.n} {pid}" if compte else None, equipe, depuis))
        return tok

    def vote(self, tok, choix, ip="1.2.3.4"):
        return asyncio.run(serveur.api_fans_vote(Req({"token": tok, "choice": choix}, ip)))

    def refus(self, f, *a, **k):
        with self.assertRaises(HTTPException) as e:
            f(*a, **k)
        return e.exception.status_code, e.exception.detail

    # ---------- règles ----------
    def test_question_et_vote(self):
        tok = self.joueur()
        r = serveur.api_fans(tok)
        self.assertTrue(r["open"])
        self.assertIsNone(r["reason"])
        self.assertEqual(r["question"]["lever"], fo.levier_de_semaine(self.w.doc["week"]["index"] + 1))
        self.assertEqual(r["question"]["week"], self.lundi_suivant)
        self.assertEqual(r["question"]["team"]["abbr"], "CTX")
        self.assertEqual([o["id"] for o in r["question"]["options"]], fo.options(r["question"]["lever"]))
        self.assertIsNone(r["my_vote"])
        self.assertNotIn("result", r)                                 # pourcentages cachés avant le verrou
        ops = fo.options(r["question"]["lever"])
        self.assertEqual(self.vote(tok, ops[2])["my_vote"], ops[2])
        self.assertEqual(self.vote(tok, ops[0])["my_vote"], ops[0])   # vote modifiable
        self.assertEqual(serveur.api_fans(tok)["my_vote"], ops[0])
        with serveur.db() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM fan_votes").fetchone()[0], 1)   # une ligne par joueur
        self.assertEqual(serveur.api_fans(tok)["in_force"]["choice"], "agressif")         # le choix de cette semaine

    def test_comptes_seulement(self):
        invite = self.joueur(compte=False)
        self.assertEqual(serveur.api_fans(invite)["reason"], "account_required")
        self.assertEqual(serveur.api_fans("")["reason"], "account_required")
        self.assertEqual(self.refus(self.vote, invite, fo.COORD), (403, "account_required"))
        self.assertEqual(self.refus(self.vote, "inconnu", fo.COORD)[0], 401)
        sans = self.joueur(equipe=None)
        self.assertEqual(self.refus(self.vote, sans, fo.COORD), (409, "no_team"))
        autre = self.joueur(equipe="ZZZ")
        self.assertEqual(self.refus(self.vote, autre, fo.COORD), (409, "unknown_team"))

    def test_choix_inconnu(self):
        tok = self.joueur()
        self.assertEqual(self.refus(self.vote, tok, "nimporte"), (400, "unknown_choice"))

    def test_verrou(self):
        tok = self.joueur()
        ops = fo.options(self.w.doc["fan_vote"]["lever"])
        self.vote(tok, ops[2])
        self.t = self.w.lock                                          # vendredi 23:30 : fermé
        self.assertEqual(self.refus(self.vote, tok, ops[0]), (409, "vote_closed"))
        r = serveur.api_fans(tok)
        self.assertFalse(r["open"])
        self.assertTrue(r["closed"])
        self.assertEqual(r["my_vote"], ops[2])
        self.assertEqual(r["result"]["votes"], 1)
        self.assertEqual(r["result"]["choice"], fo.COORD)            # 1 vote : le coordinateur
        self.assertEqual(r["result"]["source"], "coordinators")

    def test_resultat_minimum_et_egalite(self):
        lv = self.w.doc["fan_vote"]["lever"]
        ops = fo.options(lv)
        r = serveur.fans_result({ops[2]: 4}, ops)
        self.assertEqual((r["choice"], r["source"], r["votes"]), (fo.COORD, "coordinators", 4))
        r = serveur.fans_result({ops[2]: 5}, ops)
        self.assertEqual((r["choice"], r["source"], r["pct"][ops[2]]), (ops[2], "fans", 100))
        r = serveur.fans_result({ops[0]: 4, ops[2]: 4, fo.COORD: 1}, ops)
        self.assertEqual((r["choice"], r["source"]), (fo.COORD, "coordinators"))           # égalité en tête
        r = serveur.fans_result({ops[0]: 3, ops[2]: 6, fo.COORD: 1}, ops)
        self.assertEqual((r["choice"], r["pct"]), (ops[2], {ops[0]: 30, fo.COORD: 10, ops[2]: 60}))
        r = serveur.fans_result({fo.COORD: 7, ops[2]: 2}, ops)
        self.assertEqual((r["choice"], r["source"]), (fo.COORD, "coordinators"))
        # même règle que le moteur
        for cts in ({ops[2]: 4}, {ops[2]: 5}, {ops[0]: 4, ops[2]: 4}, {ops[0]: 2, ops[2]: 6}):
            r = serveur.fans_result(cts, ops)
            m = fo.choix_de_semaine({"lever": lv, "teams": {"CTX": {"choice": max(cts, key=cts.get), "votes": sum(cts.values()),
                                                                     "counts": cts}}}, None, lv, ["CTX"])["CTX"]
            self.assertEqual((r["choice"], r["source"]), (m["choice"], m["source"]), cts)

    def test_changer_de_franchise(self):
        tok = self.joueur()
        ops = fo.options(self.w.doc["fan_vote"]["lever"])
        self.vote(tok, ops[2])
        asyncio.run(serveur.api_fav_team(Req({"token": tok, "team": "VEC"})))
        r = serveur.api_fans(tok)
        self.assertIsNone(r["my_vote"])                               # le vote de la semaine est retiré
        self.assertEqual(r["reason"], "team_changed")
        self.assertEqual(self.refus(self.vote, tok, ops[2]), (409, "team_changed"))
        with serveur.db() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM fan_votes").fetchone()[0], 0)
        asyncio.run(serveur.api_fav_team(Req({"token": tok, "team": "VEC"})))   # même équipe : rien ne change
        # tenue depuis avant le lundi : peut voter
        ancien = self.joueur(depuis=self.w.monday - HEURE)
        self.assertEqual(self.vote(ancien, ops[0])["team"], "CTX")

    def test_limite(self):
        tok = self.joueur()
        ops = fo.options(self.w.doc["fan_vote"]["lever"])
        for i in range(serveur.FAN_VOTE_MAX_JOUEUR):
            self.vote(tok, ops[i % 3])
        self.assertEqual(self.refus(self.vote, tok, ops[0]), (429, "too_many_attempts"))

    # ---------- résultats et export ----------
    def votes(self, equipe, repart):
        for choix, n in repart.items():
            for _ in range(n):
                self.vote(self.joueur(equipe), choix)

    def test_resultats_et_export(self):
        lv = self.w.doc["fan_vote"]["lever"]
        ops = fo.options(lv)
        self.votes("CTX", {ops[2]: 4, ops[0]: 2, fo.COORD: 1})
        self.votes("VEC", {ops[0]: 3})
        self.votes("AEG", {ops[0]: 3, ops[2]: 3})
        with mock.patch.dict(os.environ, {"GC_ADMIN_KEY": ADMIN}):
            self.assertEqual(self.refus(serveur.api_admin_fans, key="faux", week=self.lundi_suivant)[0], 403)
            self.assertEqual(self.refus(serveur.api_admin_fans, key=ADMIN, week=self.lundi_suivant), (409, "not_closed"))
            self.t = self.w.lock + HEURE
            doc = serveur.api_admin_fans(key=ADMIN, week=self.lundi_suivant)
            self.assertEqual(doc, serveur.api_admin_fans(key=ADMIN))          # défaut : la dernière question fermée
            entete = Req(); entete.headers = {"x-admin-key": ADMIN}            # FO-3 : la clé dans l'en-tête X-Admin-Key
            self.assertEqual(doc, serveur.api_admin_fans(week=self.lundi_suivant, request=entete))
            entete.headers = {"x-admin-key": "faux"}
            self.assertEqual(self.refus(serveur.api_admin_fans, week=self.lundi_suivant, request=entete)[0], 403)
            self.assertEqual(self.refus(serveur.api_admin_fans, key=ADMIN, week="2000-01-03"), (404, "no_question"))
        self.assertEqual((doc["version"], doc["week"], doc["lever"]), (1, self.lundi_suivant, lv))
        self.assertEqual(set(doc["teams"]), {"CTX", "VEC", "AEG"})           # seulement les franchises qui ont voté
        self.assertEqual(doc["teams"]["CTX"], {"choice": ops[2], "votes": 7, "counts": {ops[0]: 2, fo.COORD: 1, ops[2]: 4}})
        self.assertEqual(doc["teams"]["VEC"]["choice"], fo.COORD)            # 3 votes
        self.assertEqual(doc["teams"]["AEG"]["choice"], fo.COORD)            # égalité
        # le moteur lit l'export tel quel (GC_FANS)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(doc, fh)
        self.addCleanup(os.unlink, fh.name)
        lu = fo.choix_de_semaine(fo.lire_fichier(fh.name), self.lundi_suivant, lv, ["CTX", "VEC", "AEG", "MNL"])
        self.assertEqual({a: (r["choice"], r["source"], r["votes"]) for a, r in lu.items()},
                         {"CTX": (ops[2], "fans", 7), "VEC": (fo.COORD, "coordinators", 3),
                          "AEG": (fo.COORD, "coordinators", 6), "MNL": (fo.COORD, "coordinators", 0)})
        # résultats publics (page Teams), après le verrou
        r = serveur.api_fans_results()
        self.assertEqual(r["week"], self.lundi_suivant)
        self.assertEqual(set(r["teams"]), set(self.w.doc["fan_vote"]["teams"]))
        self.assertEqual(r["teams"]["CTX"]["pct"], {ops[0]: 29, fo.COORD: 14, ops[2]: 57})
        self.assertEqual(serveur.api_fans_results("vec")["teams"]["VEC"]["votes"], 3)
        self.assertEqual(self.refus(serveur.api_fans_results, "ZZZ")[0], 404)

    def test_resultats_avant_le_verrou(self):
        """Avant le verrou : la question fermée est celle de la semaine d'avant (le choix en vigueur cette semaine)."""
        lv = self.prev.doc["fan_vote"]["lever"]
        ops = fo.options(lv)
        with serveur._db_lock, serveur.db() as c:
            for i in range(5):
                c.execute("INSERT INTO fan_votes(player, week, team, lever, choice, at) VALUES(?,?,?,?,?,0)",
                          (f"fo-v{i}", self.w.start, "MNL", lv, ops[0]))
        r = serveur.api_fans_results("MNL")
        self.assertEqual((r["week"], r["lever"]), (self.w.start, lv))
        self.assertEqual((r["teams"]["MNL"]["choice"], r["teams"]["MNL"]["votes"]), (ops[0], 5))

    def test_pas_de_question(self):
        fv = self.w.doc.pop("fan_vote")
        try:
            tok = self.joueur()
            r = serveur.api_fans(tok)
            self.assertEqual((r["open"], r["reason"]), (False, "no_question"))
            self.assertEqual(self.refus(self.vote, tok, fo.COORD), (409, "no_question"))
        finally:
            self.w.doc["fan_vote"] = fv

    def test_interrupteur(self):
        tok = self.joueur()
        with mock.patch.dict(os.environ, {"GC_FRONT_OFFICE": "off", "GC_ADMIN_KEY": ADMIN}):
            for f, a in ((serveur.api_fans, (tok,)), (serveur.api_fans_results, ()),
                         (lambda: serveur.api_admin_fans(key=ADMIN), ()), (lambda: self.vote(tok, fo.COORD), ())):
                self.assertEqual(self.refus(f, *a), (404, "front_office_off"))
        with serveur.db() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM fan_votes").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
