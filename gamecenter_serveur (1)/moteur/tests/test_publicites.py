"""Publicités (étape 7 de la feuille de route — serveur.py) : variables AdSense (identifiant d'éditeur, blocs par
emplacement), /ads.txt, page /legal (règles, confidentialité, mentions légales avec l'éditeur des variables, échappé),
plan du site. Le rendu dans le site est vérifié par outils/site/test_publicites.js.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import os
import sys
import tempfile
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))

try:                                    # le serveur (fastapi) n'est pas installé partout : tests sautés
    os.environ.setdefault("GC_DATA", tempfile.mkdtemp(prefix="gc-pub-"))
    os.environ.setdefault("GC_PUSH_LOOP", "0")
    sys.path.insert(0, RACINE)
    import serveur
    from fastapi import HTTPException
except Exception as e:                  # pragma: no cover
    serveur = None


class Req:
    base_url = "http://localhost:8000/"


@unittest.skipIf(serveur is None, "serveur.py non importable")
class TestPublicites(unittest.TestCase):
    def setUp(self):
        self.avant = (serveur.ADS_CLIENT, serveur.ADS_SLOTS)
        self.avant_cf = serveur.CF_ANALYTICS
        self.env = {k: os.environ.get(k) for k in ("GC_EDITEUR", "GC_EDITEUR_ADRESSE", "GC_CONTACT")}

    def tearDown(self):
        serveur.ADS_CLIENT, serveur.ADS_SLOTS = self.avant
        serveur.CF_ANALYTICS = self.avant_cf
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_variables(self):
        self.assertEqual(serveur._ads_client(" ca-pub-1234567890123456 "), "ca-pub-1234567890123456")
        for faux in ("", "pub-1234567890123456", "ca-pub-12", 'ca-pub-1234567890"><script>'):
            self.assertEqual(serveur._ads_client(faux), "", faux)
        self.assertEqual(serveur._ads_slots("half=1234567, home = 7654321,page=x,autre=1234567,page=99"),
                         {"half": "1234567", "home": "7654321"})
        self.assertEqual(serveur._ads_slots(""), {})

    def test_statistiques_cloudflare(self):
        jeton = "0123456789abcdef0123456789abcdef"
        self.assertEqual(serveur._cf_token(" " + jeton + " "), jeton)
        for faux in ("", "0123", jeton.upper(), jeton[:-1] + '"', jeton + "'><script>"):
            self.assertEqual(serveur._cf_token(faux), "", faux)
        serveur.CF_ANALYTICS = ""
        self.assertNotIn("cloudflareinsights", serveur.legal().body.decode())
        serveur.CF_ANALYTICS = jeton
        s = serveur.legal().body.decode()
        self.assertIn('static.cloudflareinsights.com/beacon.min.js', s)
        self.assertIn('data-cf-beacon=\'{"token": "' + jeton + '"}\'', s)
        self.assertIn("Cloudflare Web Analytics", s)

    def test_ads_txt(self):
        serveur.ADS_CLIENT = ""
        with self.assertRaises(HTTPException) as e:
            serveur.ads_txt()
        self.assertEqual(e.exception.status_code, 404)
        serveur.ADS_CLIENT = "ca-pub-1234567890123456"
        r = serveur.ads_txt()
        self.assertEqual(r.body.decode(), "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0\n")
        self.assertEqual(r.media_type, "text/plain")

    def test_legal(self):
        for k in self.env:
            os.environ.pop(k, None)
        serveur.ADS_CLIENT = ""
        s = serveur.legal().body.decode()
        self.assertIn("Play money · No real winnings · 18+ only", s)
        self.assertNotIn("__", s)                                      # tous les champs remplacés
        self.assertEqual(s.count("<i>not set</i>"), 3)
        self.assertIn("Advertising is currently <b>off</b>", s)
        os.environ.update(GC_EDITEUR="A <b>Name</b>", GC_EDITEUR_ADRESSE="Rue 1, 1000 Bruxelles", GC_CONTACT="x@y.be")
        serveur.ADS_CLIENT = "ca-pub-1234567890123456"
        s = serveur.legal().body.decode()
        self.assertIn("A &lt;b&gt;Name&lt;/b&gt;", s)
        self.assertIn('<a href="mailto:x@y.be">x@y.be</a>', s)
        self.assertIn("Advertising is currently <b>on</b>", s)
        for id_ in ('id="rules"', 'id="privacy"', 'id="legal"', 'id="privacyChoices"'):
            self.assertIn(id_, s)

    def test_plan_du_site(self):
        xml = serveur.sitemap(Req()).body.decode()
        self.assertIn("<loc>http://localhost:8000/legal</loc>", xml)


if __name__ == "__main__":
    unittest.main()
