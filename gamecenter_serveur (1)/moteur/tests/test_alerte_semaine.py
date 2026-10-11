"""Alerte et relance du calcul du samedi (outils/ci/alerte_semaine.py, README section 37).

Classement de l'étape fautive (étapes réelles de l'exécution n° 7 du 10/10, push refusé), relance unique, puis les
commandes analyser / signaler / relancer / cloturer contre une fausse API GitHub locale (aucun accès réseau).
"""
import importlib.util
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

ICI = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.normpath(os.path.join(ICI, "..", "..", "outils", "ci", "alerte_semaine.py"))
_spec = importlib.util.spec_from_file_location("alerte_semaine", SCRIPT)
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

NOMS = ["Set up job", "Run actions/checkout@v4", "Run actions/setup-python@v5", "Installer le moteur",
        "Tester les modules du moteur (quelques secondes)", "Calculer la semaine (≈ 45 min si elle est à produire)",
        "Contrôler le moteur (audit de toutes les semaines)", "Ajouter la semaine au dépôt",
        "Garder la semaine calculée (le push a échoué)", "Post Run actions/checkout@v4", "Complete job"]


def job(echec=None, conclusion="failure", en_cours=None):
    """Job « produire » : l'étape `echec` a échoué (les suivantes sont sautées) ; `en_cours` = étape coupée."""
    steps, apres = [], False
    for i, n in enumerate(NOMS, 1):
        if n.startswith("Post") or n == "Complete job":
            c, st = "success", "completed"
        elif apres:
            c, st = "skipped", "completed"
        elif echec and n.startswith(echec):
            c, st, apres = "failure", "completed", True
        elif en_cours and n.startswith(en_cours):
            c, st, apres = None, "in_progress", True
        else:
            c, st = "success", "completed"
        steps.append({"name": n, "status": st, "conclusion": c, "number": i})
    return {"id": 114195441300, "name": "produire", "conclusion": conclusion, "steps": steps}


class Classement(unittest.TestCase):
    def test_push_refuse_du_10_10(self):
        i = A.classer(job("Ajouter la semaine"))
        self.assertEqual((i["categorie"], i["relancer"]), ("push", "push"))
        self.assertEqual(i["etape"], "Ajouter la semaine au dépôt")
        # repousser la semaine calculée reste permis dans une relance (même exécution, sans recalcul)
        self.assertEqual(A.classer(job("Ajouter la semaine"), relance=True, tentative=2)["relancer"], "push")

    def test_machine_une_seule_relance(self):
        for etape in ("Run actions/checkout", "Run actions/setup-python", "Installer le moteur", "Set up job"):
            self.assertEqual(A.classer(job(etape))["relancer"], "workflow", etape)
            self.assertEqual(A.classer(job(etape))["categorie"], "machine", etape)
        self.assertEqual(A.classer(job("Installer le moteur"), relance=True)["relancer"], "")
        self.assertEqual(A.classer(job("Installer le moteur"), tentative=2)["relancer"], "")
        self.assertEqual(A.classer(job("Installer le moteur"), tentative="2")["relancer"], "")

    def test_machine_perdue(self):
        i = A.classer(job(None, conclusion="failure"))
        self.assertEqual((i["categorie"], i["relancer"]), ("machine", "workflow"))
        self.assertIn("machine perdue", i["etape"])

    def test_pas_de_relance_tests_calcul_audit(self):
        for etape, cat in (("Tester les modules", "tests"), ("Calculer la semaine", "calcul"),
                           ("Contrôler le moteur", "audit")):
            i = A.classer(job(etape))
            self.assertEqual((i["categorie"], i["relancer"]), (cat, ""), etape)

    def test_depassement_des_75_min(self):
        i = A.classer(job(None, conclusion="cancelled", en_cours="Calculer la semaine"))
        self.assertEqual((i["categorie"], i["relancer"], i["depassement"]), ("calcul", "", True))
        j = job(None, conclusion="cancelled")
        j["steps"][5]["conclusion"] = "cancelled"
        self.assertEqual(A.classer(j)["etape"], NOMS[5])
        # même pendant l'installation : un job annulé n'est jamais relancé
        self.assertEqual(A.classer(job(None, conclusion="cancelled", en_cours="Installer"))["relancer"], "")

    def test_toutes_les_etapes_du_workflow_sont_classees(self):
        wf = os.path.normpath(os.path.join(ICI, "..", "..", "..", ".github", "workflows", "semaine.yml"))
        if not os.path.exists(wf):
            self.skipTest("workflow absent")
        with open(wf, encoding="utf-8") as f:
            noms = [l.split("- name:", 1)[1].strip() for l in f if "- name:" in l]
        produire = noms[:noms.index("Garder la semaine calculée (le push a échoué)")]
        attendu = ["machine", "tests", "calcul", "audit", "push"]
        self.assertEqual([A.categorie_etape(n) for n in produire], attendu)

    def test_fin_du_log(self):
        brut = "\n".join(f"2026-10-10T11:30:{i % 60:02d}.1Z ligne {i}" for i in range(100))
        brut += "\n2026-10-10T11:30:11.2Z [command]/usr/bin/git version\n2026-10-10T11:30:11.3Z ```fin```"
        f = A.fin_du_log(brut, 5).splitlines()
        self.assertEqual(f, ["ligne 96", "ligne 97", "ligne 98", "ligne 99", "ʼʼʼfinʼʼʼ"])


class FausseAPI(BaseHTTPRequestHandler):
    etat = {}

    def log_message(self, *a):
        pass

    def _repondre(self, code, corps=None, brut=None, entetes=()):
        donnees = brut.encode() if brut is not None else (json.dumps(corps).encode() if corps is not None else b"")
        self.send_response(code)
        for k, v in entetes:
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(donnees)))
        self.end_headers()
        self.wfile.write(donnees)

    def _noter(self):
        n = int(self.headers.get("Content-Length") or 0)
        corps = json.loads(self.rfile.read(n)) if n else None
        self.etat["appels"].append((self.command, self.path, corps, self.headers.get("Authorization")))
        return corps

    def do_GET(self):
        self._noter()
        p, e = self.path, self.etat
        if "/attempts/" in p:
            return self._repondre(200, {"jobs": [{"id": 1, "name": "suivi"}, e["job"]]})
        if p.endswith("/logs"):
            return self._repondre(302, entetes=[("Location", f"http://127.0.0.1:{e['port']}/stockage/log.txt")])
        if p == "/stockage/log.txt":
            return self._repondre(200, brut="2026-10-10T11:30:11.1Z  ! [rejected]        HEAD -> main (fetch first)")
        if "/labels/" in p:
            return self._repondre(200 if e["etiquette"] else 404, {})
        if "/issues?" in p:
            return self._repondre(200, e["issues"])
        return self._repondre(404, {})

    def do_POST(self):
        corps, p = self._noter(), self.path
        if p.endswith("/labels"):
            self.etat["etiquette"] = True
        if p.endswith("/issues"):
            return self._repondre(201, {"number": 51})
        return self._repondre(201 if not p.endswith("/dispatches") else 204, {} if not p.endswith("/dispatches") else None)

    def do_PATCH(self):
        self._noter()
        return self._repondre(200, {})


class Commandes(unittest.TestCase):
    def setUp(self):
        self.srv = HTTPServer(("127.0.0.1", 0), FausseAPI)
        port = self.srv.server_address[1]
        FausseAPI.etat = {"appels": [], "port": port, "etiquette": False, "issues": [], "job": job("Ajouter la semaine")}
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.tmp = tempfile.mkdtemp(prefix="alerte-")
        self.env = {"GITHUB_API_URL": f"http://127.0.0.1:{port}", "GITHUB_TOKEN": "jeton", "GITHUB_REPOSITORY": "o/r",
                    "GITHUB_REPOSITORY_OWNER": "o", "GITHUB_RUN_ID": "38045962883", "GITHUB_RUN_ATTEMPT": "1",
                    "GITHUB_RUN_NUMBER": "7", "GITHUB_EVENT_NAME": "schedule", "GITHUB_REF_NAME": "main",
                    "GITHUB_OUTPUT": os.path.join(self.tmp, "out"), "ALERTE_INFO": os.path.join(self.tmp, "info.json")}

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def sortie(self):
        with open(self.env["GITHUB_OUTPUT"], encoding="utf-8") as f:
            return f.read()

    def lancer(self, cmd, **env):
        with mock.patch.dict(os.environ, dict(self.env, **env)), mock.patch("builtins.print"):
            getattr(A, cmd)()
        return FausseAPI.etat["appels"]

    def test_push_repousse_issue_ouverte_puis_fermee(self):
        self.lancer("analyser")
        sortie = self.sortie()
        self.assertIn("categorie=push\n", sortie)
        self.assertIn("relancer=push\n", sortie)
        appels = self.lancer("signaler", ISSUE_RELANCE="push-ok")
        log = [a for a in appels if a[1] == "/stockage/log.txt"][0]
        self.assertIsNone(log[3], "le jeton ne doit pas suivre la redirection vers le stockage des logs")
        cree = [a for a in appels if a[0] == "POST" and a[1] == "/repos/o/r/issues"][0][2]
        self.assertEqual(cree["labels"], ["calcul-semaine"])
        self.assertIn("@o ", cree["body"])
        self.assertIn("**Ajouter la semaine au dépôt**", cree["body"])
        self.assertIn("[rejected]", cree["body"])
        self.assertIn("repoussée depuis l'artefact", cree["body"])
        self.assertIn(("POST", "/repos/o/r/labels"), [a[:2] for a in appels])
        self.assertEqual([a[2] for a in appels if a[0] == "PATCH"], [{"state": "closed", "state_reason": "completed"}])

    def test_audit_commente_l_issue_deja_ouverte(self):
        FausseAPI.etat.update(job=job("Contrôler le moteur"), etiquette=True, issues=[{"number": 50}])
        self.lancer("analyser")
        appels = self.lancer("signaler", TEST_ECHEC="audit")
        com = [a for a in appels if a[1] == "/repos/o/r/issues/50/comments"]
        self.assertEqual(len(com), 1)
        self.assertIn("essai simulé", com[0][2]["body"])
        self.assertIn("aucune (relancer donnerait le même résultat)", com[0][2]["body"])
        self.assertFalse([a for a in appels if a[0] == "PATCH" or a[1] == "/repos/o/r/issues"])

    def test_machine_relance_le_workflow(self):
        FausseAPI.etat["job"] = job("Installer le moteur")
        self.lancer("analyser")
        self.assertIn("relancer=workflow\n", self.sortie())
        appels = self.lancer("relancer", GITHUB_REF_NAME="claude/essai")
        d = [a for a in appels if a[1].endswith("/actions/workflows/semaine.yml/dispatches")][0]
        self.assertEqual(d[2], {"ref": "claude/essai", "inputs": {"relance": "oui"}})
        self.assertEqual(d[3], "Bearer jeton")

    def test_cloturer(self):
        self.assertFalse([a for a in self.lancer("cloturer") if a[0] != "GET"])   # rien d'ouvert : rien à faire
        FausseAPI.etat["issues"] = [{"number": 50}, {"number": 9, "pull_request": {}}]
        appels = self.lancer("cloturer")
        com = [a for a in appels if a[1] == "/repos/o/r/issues/50/comments"][0][2]["body"]
        self.assertIn("Résolu par l'exécution [n° 7]", com)
        self.assertIn(("PATCH", "/repos/o/r/issues/50"), [a[:2] for a in appels])


if __name__ == "__main__":
    unittest.main()
