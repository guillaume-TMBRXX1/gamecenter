"""Première visite (promotion, étape 9.3 — serveur.py) : interrupteur GC_ACCUEIL. Sans lui, la page d'avant à
l'identique (bandeau caché, aucun script, pas de « accueil » pour la page) ; avec lui, le bandeau visible, le script du
<head> (blocs retenus jusqu'au 1er dessin, au plus 10 s ; bandeau caché pour qui est déjà venu) et « accueil » pour la
page. Le comportement dans un navigateur est vérifié par outils/site/test_accueil.js.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))

try:                                    # le serveur (fastapi) n'est pas installé partout : tests sautés
    os.environ.setdefault("GC_DATA", tempfile.mkdtemp(prefix="gc-accueil-"))
    os.environ.setdefault("GC_PUSH_LOOP", "0")
    sys.path.insert(0, RACINE)
    import serveur
except Exception:                       # pragma: no cover
    serveur = None


@unittest.skipIf(serveur is None, "serveur.py non importable")
class TestAccueil(unittest.TestCase):
    def setUp(self):
        self.avant = os.environ.get("GC_ACCUEIL")
        semaines = os.path.join(RACINE, "data", "weeks")
        for d in sorted(os.listdir(semaines)) if os.path.isdir(semaines) else []:
            dst = os.path.join(serveur.WEEKS_DIR, d)
            if d.startswith("week_") and not os.path.exists(dst):
                os.makedirs(serveur.WEEKS_DIR, exist_ok=True)
                os.symlink(os.path.join(semaines, d), dst)
        serveur.load_weeks()
        if serveur.current_week() is None:
            self.skipTest("pas de semaine")
        # horloge figée : sans elle, une action révélée entre les deux pages comparées change leur longueur (un autre test
        # de la suite a pu placer l'horloge au milieu d'une journée de matchs)
        t = serveur.now_ms()
        p = mock.patch.object(serveur, "now_ms", lambda: t)
        p.start()
        self.addCleanup(p.stop)

    def tearDown(self):
        if self.avant is None:
            os.environ.pop("GC_ACCUEIL", None)
        else:
            os.environ["GC_ACCUEIL"] = self.avant

    def srv(self, html):
        return json.loads(html.split('<script type="application/json" id="gf-server">', 1)[1].split("</script>", 1)[0])

    def test_interrupteur(self):
        self.assertEqual(serveur._page_source().count(serveur._ACCUEIL_CACHE), 1)   # le bandeau du site, caché
        for v in ("", "0", "on", "true"):
            os.environ["GC_ACCUEIL"] = v
            self.assertFalse(serveur.accueil_on(), v)
        os.environ.pop("GC_ACCUEIL", None)
        off = serveur.page().body.decode()
        self.assertIn(serveur._ACCUEIL_CACHE, off)
        self.assertNotIn(serveur._ACCUEIL_TETE, off)
        self.assertNotIn("classList.add('gc-boot')", off)
        self.assertNotIn("accueil", self.srv(off))
        os.environ["GC_ACCUEIL"] = "1"
        on = serveur.page().body.decode()
        self.assertNotIn(serveur._ACCUEIL_CACHE, on)
        self.assertIn('<section class="card welcome" id="welcome" aria-labelledby="welcomeTitle">', on)
        tete = on.split("</head>")[0]
        self.assertIn(serveur._ACCUEIL_TETE, tete)
        for mot in ("gc-boot", "gc-seen", "gc-welcome-v1", "gc-player-v1", "10000"):
            self.assertIn(mot, serveur._ACCUEIL_TETE)
        self.assertIs(self.srv(on)["accueil"], True)
        self.assertEqual(len(on) - len(off), len(serveur._ACCUEIL_TETE) + 1 - len(" hidden") + len(',"accueil":true'))

    def test_terrain_d_abord(self):
        """Section 127 : le script spect-boot (html.spect avant le 1er dessin) est dans le <head> par défaut ;
        GC_ACCUEIL_TERRAIN=off le retire et pose « spect_off » pour la page. Navigateur : outils/site/test_terrain.js."""
        avant = os.environ.get("GC_ACCUEIL_TERRAIN")
        try:
            os.environ.pop("GC_ACCUEIL_TERRAIN", None)
            self.assertTrue(serveur.accueil_terrain_on())
            on = serveur.page().body.decode()
            tete = on.split("</head>")[0]
            self.assertEqual(tete.count('<script id="spect-boot">'), 1)
            for mot in ("gc-bettor", "gc-slip-v1", "gc-player-v1", "spect"):
                self.assertIn(mot, tete.split('<script id="spect-boot">', 1)[1].split("</script>", 1)[0])
            self.assertNotIn("spect_off", self.srv(on))
            for v in ("off", "0", "no", "OFF"):
                os.environ["GC_ACCUEIL_TERRAIN"] = v
                self.assertFalse(serveur.accueil_terrain_on(), v)
            off = serveur.page().body.decode()
            self.assertNotIn('id="spect-boot"', off)
            self.assertIs(self.srv(off)["spect_off"], True)
            self.assertIn("html.spect", off)                      # les règles restent, sans effet sans la classe
        finally:
            if avant is None:
                os.environ.pop("GC_ACCUEIL_TERRAIN", None)
            else:
                os.environ["GC_ACCUEIL_TERRAIN"] = avant


    def test_decisions_interrupteur(self):
        """Section 128 : la carte de décision du coach IA ; GC_DECISIONS=off pose « coach_off » pour la page.
        Navigateur : outils/site/test_decisions.js."""
        avant = os.environ.get("GC_DECISIONS")
        try:
            os.environ.pop("GC_DECISIONS", None)
            self.assertTrue(serveur.decisions_on())
            on = serveur.page().body.decode()
            self.assertNotIn("coach_off", self.srv(on))
            self.assertIn('data-f="coach"', on)                   # l'emplacement de la carte, dans le modèle du terrain
            for v in ("off", "0", "no"):
                os.environ["GC_DECISIONS"] = v
                self.assertFalse(serveur.decisions_on(), v)
            self.assertIs(self.srv(serveur.page().body.decode())["coach_off"], True)
        finally:
            if avant is None:
                os.environ.pop("GC_DECISIONS", None)
            else:
                os.environ["GC_DECISIONS"] = avant

if __name__ == "__main__":
    unittest.main()
