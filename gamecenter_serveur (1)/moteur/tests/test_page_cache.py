"""Page d'accueil gardée quelques secondes et préchauffage au démarrage (section 133 de serveur.py) : une seule
construction par période, page compressée servie telle quelle, refaite après la période ou quand une variable change,
coupée sous le crochet des tests du site.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import glob
import gzip
import os
import sys
import tempfile
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
SEMAINES = sorted(glob.glob(os.path.join(RACINE, "data", "weeks", "week_*")))

try:                                    # le serveur (fastapi) n'est pas installé partout : tests sautés
    os.environ.setdefault("GC_DATA", tempfile.mkdtemp(prefix="gc-pc-"))
    os.environ.setdefault("GC_PUSH_LOOP", "0")
    sys.path.insert(0, RACINE)
    import serveur
except Exception:                       # pragma: no cover
    serveur = None


class Req:
    def __init__(self, gzip_ok=True):
        self.headers = {"accept-encoding": "gzip, br"} if gzip_ok else {}


@unittest.skipIf(serveur is None or not SEMAINES, "serveur.py non importable ou aucune semaine")
class TestPageCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = serveur.Week(SEMAINES[-1])

    def setUp(self):
        self.avant = (serveur.load_weeks, serveur.now_ms, serveur._page_html)
        self.env = {k: os.environ.get(k) for k in ("GC_PAGE_CACHE", "GC_TEST_HOOK", "GC_PRECHAUFFAGE", "GC_ZZ_TEST")}
        serveur.load_weeks = lambda: {self.w.start: self.w}
        self.t = self.w.sched[0]["ko"] + 60_000
        serveur.now_ms = lambda: self.t
        self.n = 0
        vraie = self.avant[2]

        def comptee():
            self.n += 1
            return vraie()
        serveur._page_html = comptee
        serveur._PAGE_HTML.update(cle=None, t=0, html=None, gz=None)
        os.environ.pop("GC_TEST_HOOK", None)
        os.environ["GC_PAGE_CACHE"] = "15"

    def tearDown(self):
        serveur.load_weeks, serveur.now_ms, serveur._page_html = self.avant
        serveur._PAGE_HTML.update(cle=None, t=0, html=None, gz=None)
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_une_construction_par_periode(self):
        r1 = serveur.page(Req())
        self.t += 14_000
        r2 = serveur.page(Req())
        self.assertEqual(self.n, 1)
        self.assertEqual(r1.body, r2.body)
        self.assertEqual(r1.headers["content-encoding"], "gzip")
        html = gzip.decompress(r1.body).decode("utf-8")
        self.assertIn("<title>", html)
        self.assertEqual(serveur.page(Req(gzip_ok=False)).body.decode("utf-8"), html)   # sans gzip : la même page
        self.t += 2_000                              # 16 s : refaite
        serveur.page(Req())
        self.assertEqual(self.n, 2)

    def test_variable_changee(self):
        serveur.page(Req())
        os.environ["GC_ZZ_TEST"] = "1"               # une variable GC_* change : la page est refaite tout de suite
        serveur.page(Req())
        self.assertEqual(self.n, 2)

    def test_ancienne_page_pendant_la_construction(self):
        serveur.page(Req())
        self.t += 20_000
        serveur._PAGE_HTML["verrou"].acquire()       # quelqu'un la refait : l'ancienne page, sans attendre
        try:
            serveur.page(Req())
        finally:
            serveur._PAGE_HTML["verrou"].release()
        self.assertEqual(self.n, 1)

    def test_coupe(self):
        os.environ["GC_PAGE_CACHE"] = "0"
        serveur.page(Req())
        serveur.page(Req())
        self.assertEqual(self.n, 2)
        os.environ.pop("GC_PAGE_CACHE")
        os.environ["GC_TEST_HOOK"] = "1"             # tests du site : chaque page refaite, pas de préchauffage
        self.assertEqual(serveur.page_cache_s(), 0)
        self.assertFalse(serveur.prechauffage_on())
        os.environ["GC_PRECHAUFFAGE"] = "on"
        self.assertTrue(serveur.prechauffage_on())


if __name__ == "__main__":
    unittest.main()
