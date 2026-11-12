"""Image du serveur (Dockerfile) : chaque module de la racine importé par le serveur y est copié.

12/11/2026 : actualites.py (onglet News, section 115) manquait à la ligne COPY ; le site ne démarrait plus sur Railway
(« ModuleNotFoundError: No module named 'actualites' ») alors que les tests, lancés depuis le dépôt, passaient.
Le test reconstruit le dossier /app de l'image (lignes COPY) et y importe le serveur.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))


def copies():
    """(sources, destination) de chaque ligne COPY du Dockerfile."""
    out = []
    for ligne in open(os.path.join(RACINE, "Dockerfile"), encoding="utf-8"):
        m = re.match(r"\s*COPY\s+(.+)$", ligne)
        if m:
            *src, dst = m.group(1).split()
            out.append((src, dst))
    return out


class TestDockerfile(unittest.TestCase):
    def test_modules_de_la_racine_copies(self):
        copie = {s for src, _ in copies() for s in src}
        racine = {f[:-3] for f in os.listdir(RACINE) if f.endswith(".py")}
        texte = open(os.path.join(RACINE, "serveur.py"), encoding="utf-8").read()
        # imports du premier niveau (au démarrage) ; generer_semaine n'est importé que sous GC_AUTOGEN=1, que l'image coupe
        importes = set(re.findall(r"^(?:import|from)\s+(\w+)", texte, re.M)) & racine
        self.assertIn("comptes_rendus", importes)                     # le test voit bien les imports
        for nom in sorted(importes):
            self.assertIn(f"{nom}.py", copie, f"{nom}.py est importé par serveur.py mais pas copié dans l'image")

    def test_serveur_importable_dans_l_image(self):
        try:
            import fastapi  # noqa: F401
        except ImportError:                                           # pragma: no cover
            self.skipTest("fastapi absent")
        app = tempfile.mkdtemp(prefix="gc-image-")
        self.addCleanup(shutil.rmtree, app, True)
        for src, dst in copies():
            for s in src:
                if s in ("requirements.txt",) or s.startswith("data"):
                    continue                                          # dépendances installées à part ; semaines lourdes
                p = os.path.join(RACINE, s)
                cible = os.path.join(app, dst) if dst not in ("./", ".") else app
                if os.path.isdir(p):
                    shutil.copytree(p, cible if dst not in ("./", ".") else os.path.join(app, s), dirs_exist_ok=True)
                else:
                    shutil.copy(p, app if dst in ("./", ".") else cible)
        data = tempfile.mkdtemp(prefix="gc-image-data-")
        self.addCleanup(shutil.rmtree, data, True)
        env = dict(os.environ, GC_DATA=data, GC_PUSH_LOOP="0", PYTHONPATH="")
        r = subprocess.run([sys.executable, "-c", "import serveur"], cwd=app, env=env,
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])


if __name__ == "__main__":
    unittest.main()
