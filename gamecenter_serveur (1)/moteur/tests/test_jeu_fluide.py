"""Dessin naturel des actions (section 83 du README — serveur.py) : interrupteur GC_JEU_FLUIDE. Par défaut, rien dans la
page (le site dessine le nouveau) ; GC_JEU_FLUIDE=0 : « fluide_off » pour la page, qui dessine comme avant, à l'identique.
Le dessin lui-même est vérifié dans un navigateur par outils/site/test_actions.js.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import json
import os
import sys
import tempfile
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))

try:                                    # le serveur (fastapi) n'est pas installé partout : tests sautés
    os.environ.setdefault("GC_DATA", tempfile.mkdtemp(prefix="gc-fluide-"))
    os.environ.setdefault("GC_PUSH_LOOP", "0")
    sys.path.insert(0, RACINE)
    import serveur
except Exception:                       # pragma: no cover
    serveur = None


@unittest.skipIf(serveur is None, "serveur.py non importable")
class TestJeuFluide(unittest.TestCase):
    def setUp(self):
        self.avant = os.environ.get("GC_JEU_FLUIDE")
        semaines = os.path.join(RACINE, "data", "weeks")
        for d in sorted(os.listdir(semaines)) if os.path.isdir(semaines) else []:
            dst = os.path.join(serveur.WEEKS_DIR, d)
            if d.startswith("week_") and not os.path.exists(dst):
                os.makedirs(serveur.WEEKS_DIR, exist_ok=True)
                os.symlink(os.path.join(semaines, d), dst)
        serveur.load_weeks()
        if serveur.current_week() is None:
            self.skipTest("pas de semaine")

    def tearDown(self):
        if self.avant is None:
            os.environ.pop("GC_JEU_FLUIDE", None)
        else:
            os.environ["GC_JEU_FLUIDE"] = self.avant

    def srv(self, html):
        return json.loads(html.split('<script type="application/json" id="gf-server">', 1)[1].split("</script>", 1)[0])

    def test_interrupteur(self):
        for v in ("", "1", "on"):
            os.environ["GC_JEU_FLUIDE"] = v
            self.assertTrue(serveur.jeu_fluide_on(), v)
            self.assertNotIn("fluide_off", self.srv(serveur.page().body.decode()))
        for v in ("0", " 0 "):
            os.environ["GC_JEU_FLUIDE"] = v
            self.assertFalse(serveur.jeu_fluide_on(), v)
        html = serveur.page().body.decode()
        self.assertIs(self.srv(html)["fluide_off"], True)
        self.assertIn("if(SERVER&&SERVER.fluide_off) JEU_FLUIDE=false;", html)   # la page sait revenir au dessin d'avant


if __name__ == "__main__":
    unittest.main()
