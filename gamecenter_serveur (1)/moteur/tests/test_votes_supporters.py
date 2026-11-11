"""Front office FO-3 : du serveur au moteur (outils/ci/votes_supporters.py, generer_semaine.py, audit_moteur.py).

Vérifie, avec un faux serveur HTTP local (aucun accès au réseau) :
  - la récupération : fichier data/fans/fans_<lundi>.json écrit et lisible par le moteur ; clé dans l'en-tête
    X-Admin-Key, jamais dans l'adresse ; pas de question (information), vote pas fermé, clé refusée, serveur en panne
    (trois essais), réponse invalide, secrets absents : aucune erreur, aucun fichier, une annotation ; rien à produire ;
  - generer_semaine.py : GC_FANS passé au notebook quand le fichier existe, vide sinon ; la semaine à produire est la
    même pour la récupération et pour le calcul ;
  - audit_moteur.py : fans.applied correspond au fichier (même règle que le moteur), fichier présent mais pas lu,
    fichier lu mais absent du dépôt.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
sys.path.insert(0, RACINE)
sys.path.insert(0, os.path.join(RACINE, "outils", "ci"))

import audit_moteur as audit                     # noqa: E402
import generer_semaine as gs                     # noqa: E402
import votes_supporters as vs                    # noqa: E402
from moteur import supporters as fo              # noqa: E402

CLE = "cle-admin-de-test-0123456789"
LUNDI = "2026-11-23"
DOC = {"version": 1, "week": LUNDI, "lever": "course_passe", "closed_at": "2026-11-20T23:30:00+01:00",
       "teams": {"CTX": {"choice": "plus_passe", "votes": 7, "counts": {"plus_course": 2, "coordinateur": 1,
                                                                           "plus_passe": 4}},
                 "VEC": {"choice": "coordinateur", "votes": 3, "counts": {"plus_course": 3}}}}


class Faux(BaseHTTPRequestHandler):
    reponses, vus = [], []

    def do_GET(self):
        Faux.vus.append((self.path, self.headers.get("X-Admin-Key")))
        code, corps = Faux.reponses.pop(0) if len(Faux.reponses) > 1 else Faux.reponses[0]
        b = json.dumps(corps).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


class TestRecuperation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Faux)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.site = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        self.data = tempfile.mkdtemp(prefix="gc-fo3-")
        os.makedirs(os.path.join(self.data, "weeks", "week_2026-11-16"))
        with open(os.path.join(self.data, "weeks", "week_2026-11-16", "week.json"), "w") as fh:
            fh.write("{}")
        Faux.vus.clear()
        for p in (mock.patch.object(vs, "PAUSE", 0),
                  mock.patch.dict(os.environ, {"no_proxy": "127.0.0.1,localhost", "NO_PROXY": "127.0.0.1,localhost"})):
            p.start()
            self.addCleanup(p.stop)

    def lancer(self, reponses, env=None, args=("--lundi", LUNDI)):
        Faux.reponses = list(reponses)
        env = {"GC_SITE_URL": self.site, "GC_ADMIN_KEY": CLE} if env is None else env
        out = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=False), contextlib.redirect_stdout(out):
            for k in ("GC_SITE_URL", "GC_ADMIN_KEY"):
                if k not in env:
                    os.environ.pop(k, None)
            code = vs.main(["--data", self.data, *args])
        return code, out.getvalue(), os.path.join(self.data, "fans", f"fans_{LUNDI}.json")

    def test_fichier_ecrit(self):
        code, out, f = self.lancer([(200, DOC)])
        self.assertEqual(code, 0)
        with open(f) as fh:
            self.assertEqual(json.load(fh), DOC)
        chemin, cle = Faux.vus[0]
        self.assertEqual(chemin, f"/api/admin/fans?week={LUNDI}")
        self.assertEqual(cle, CLE)                       # dans l'en-tête…
        self.assertNotIn(CLE, chemin)                    # … jamais dans l'adresse
        self.assertNotIn(CLE, out)
        lu = fo.choix_de_semaine(fo.lire_fichier(f), LUNDI, "course_passe", ["CTX", "VEC", "AEG"])
        self.assertEqual({a: (r["choice"], r["source"]) for a, r in lu.items()},
                         {"CTX": ("plus_passe", "fans"), "VEC": ("coordinateur", "coordinators"),
                          "AEG": ("coordinateur", "coordinators")})

    def test_pas_de_question(self):
        code, out, f = self.lancer([(404, {"detail": "no_question"})])
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(f))
        self.assertIn("::notice::", out)

    def test_refus_et_pannes(self):
        cas = [([(409, {"detail": "not_closed"})], "pas encore fermé", 1),
               ([(403, {"detail": "Non autorisé."})], "clé ou adresse", 1),
               ([(500, {"detail": "x"})], "après 3 essais", 3),
               ([(500, {}), (200, DOC)], None, 2),                       # une panne passagère : deuxième essai
               ([(200, dict(DOC, week="2026-11-16"))], "fichier refusé", 1),
               ([(200, [1, 2])], "fichier refusé", 1)]
        for reps, msg, n in cas:
            Faux.vus.clear()
            code, out, f = self.lancer(reps)
            self.assertEqual(code, 0, reps)
            self.assertEqual(len(Faux.vus), n, reps)
            if msg is None:
                self.assertTrue(os.path.exists(f))
                os.unlink(f)
            else:
                self.assertIn("::warning::", out)
                self.assertIn(msg, out)
                self.assertFalse(os.path.exists(f), reps)

    def test_serveur_injoignable(self):
        Faux.vus.clear()
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"GC_SITE_URL": "http://127.0.0.1:9", "GC_ADMIN_KEY": CLE}), \
                contextlib.redirect_stdout(out):
            code = vs.main(["--data", self.data, "--lundi", LUNDI])
        self.assertEqual(code, 0)
        self.assertIn("injoignable", out.getvalue())

    def test_secrets_absents(self):
        code, out, f = self.lancer([(200, DOC)], env={})
        self.assertEqual(code, 0)
        self.assertIn("secrets GC_SITE_URL / GC_ADMIN_KEY absents", out)
        self.assertEqual(Faux.vus, [])
        self.assertFalse(os.path.exists(f))

    def test_semaine_a_produire(self):
        """Sans --lundi : la semaine que generer_semaine.py --suivante produira (la même règle)."""
        jeudi = int(datetime(2026, 11, 19, 12, tzinfo=gs.TZ).timestamp() * 1000)        # trop tôt : rien
        samedi = int(datetime(2026, 11, 21, 2, tzinfo=gs.TZ).timestamp() * 1000)
        Faux.reponses = [(200, DOC)]
        with mock.patch.dict(os.environ, {"GC_SITE_URL": self.site, "GC_ADMIN_KEY": CLE}), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(vs.main(["--data", self.data], now_ms=jeudi), 0)
            self.assertEqual(Faux.vus, [])
            self.assertEqual(vs.main(["--data", self.data], now_ms=samedi), 0)
        self.assertEqual(Faux.vus[0][0], f"/api/admin/fans?week={LUNDI}")
        self.assertEqual(gs.week_to_produce(os.path.join(self.data, "weeks"), samedi, 72)[0].isoformat(), LUNDI)
        self.assertIsNone(gs.week_to_produce(os.path.join(self.data, "weeks"), jeudi, 72))

    def test_gc_fans_passe_au_notebook(self):
        weeks = os.path.join(self.data, "weeks")
        self.assertEqual(gs.notebook_env(LUNDI, weeks)["GC_FANS"], "")
        os.makedirs(os.path.join(self.data, "fans"))
        f = os.path.join(self.data, "fans", f"fans_{LUNDI}.json")
        with open(f, "w") as fh:
            json.dump(DOC, fh)
        env = gs.notebook_env(LUNDI, weeks, os.path.join(weeks, "week_2026-11-16", "week.json"))
        self.assertEqual(env["GC_FANS"], os.path.abspath(f))
        self.assertEqual(env["GC_WEEK_START"], LUNDI)
        self.assertEqual(gs.notebook_env("2026-11-30", weeks)["GC_FANS"], "")      # autre semaine : rien
        # generate_next appelle le notebook avec la semaine à produire (run_notebook remplacé)
        samedi = int(datetime(2026, 11, 21, 2, tzinfo=gs.TZ).timestamp() * 1000)
        with mock.patch.object(gs, "run_notebook", lambda m, w, p: (m, w, p)) as _:
            m, w, p = gs.generate_next(weeks, samedi, lead_hours=72)
        self.assertEqual((m.isoformat(), w), (LUNDI, weeks))
        self.assertTrue(p.endswith(os.path.join("week_2026-11-16", "week.json")))


class TestAuditFichier(unittest.TestCase):
    def semaine(self, applied, file_read=True):
        return {"week": {"start": LUNDI, "index": 9},
                "fans": {"lever": "course_passe", "file": f"fans_{LUNDI}.json", "file_read": file_read,
                         "applied": applied}}

    def bloquants(self, w, avec_fichier=True, doc=DOC):
        d = tempfile.mkdtemp(prefix="gc-fo3a-")
        folder = os.path.join(d, "weeks", f"week_{LUNDI}")
        os.makedirs(folder)
        if avec_fichier:
            os.makedirs(os.path.join(d, "fans"))
            with open(os.path.join(d, "fans", f"fans_{LUNDI}.json"), "w") as fh:
                json.dump(doc, fh)
        A = audit.Audit()
        audit.check_fans_fichier(A, "w", w, folder)
        return [(lvl, m) for lvl, *_, m in A.items]

    def test_correspondance(self):
        ok = {"CTX": {"choice": "plus_passe", "source": "fans", "votes": 7},
              "VEC": {"choice": "coordinateur", "source": "coordinators", "votes": 3},
              "AEG": {"choice": "coordinateur", "source": "coordinators", "votes": 0}}
        self.assertEqual(self.bloquants(self.semaine(ok)), [])
        faux = dict(ok, CTX={"choice": "plus_course", "source": "fans", "votes": 7})
        r = self.bloquants(self.semaine(faux))
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0][0], audit.BLOQUANT)
        self.assertIn("CTX", r[0][1])

    def test_fichier_et_lecture(self):
        ok = {"CTX": {"choice": "coordinateur", "source": "coordinators", "votes": 0}}
        r = self.bloquants(self.semaine(ok, file_read=False))                 # présent mais pas lu
        self.assertEqual([x[0] for x in r], [audit.BLOQUANT])
        r = self.bloquants(self.semaine(ok), avec_fichier=False)              # lu mais absent du dépôt
        self.assertEqual([x[0] for x in r], [audit.ALERTE])
        self.assertEqual(self.bloquants(self.semaine(ok, file_read=False), avec_fichier=False), [])   # ni l'un ni l'autre
        self.assertEqual(self.bloquants({"week": {"start": LUNDI}}), [])      # semaine d'avant FO-1


if __name__ == "__main__":
    unittest.main()
