"""Icône de l'onglet et des résultats Google (favicon, 14/10/2026 — serveur.py, static/favicon.ico, static/icons/favicon.*,
faites par outils/site/faire_favicon.js) : adresses servies avec le bon type, fichiers valides, déclarées dans la page
d'accueil et dans /legal ; l'icône de l'écran d'accueil (icon-180, bleu-vert) ne change pas.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import os
import struct
import sys
import tempfile
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))

try:                                    # le serveur (fastapi) n'est pas installé partout : tests sautés
    os.environ.setdefault("GC_DATA", tempfile.mkdtemp(prefix="gc-fav-"))
    os.environ.setdefault("GC_PUSH_LOOP", "0")
    sys.path.insert(0, RACINE)
    import serveur
    from fastapi import HTTPException
except Exception:                       # pragma: no cover
    serveur = None

LIENS = ('<link rel="icon" href="/favicon.ico" sizes="48x48">',
         '<link rel="icon" href="/icons/favicon.svg" type="image/svg+xml">',
         '<link rel="icon" href="/icons/favicon-192.png" type="image/png" sizes="192x192">')


@unittest.skipIf(serveur is None, "serveur.py non importable")
class TestFavicon(unittest.TestCase):
    def test_ico(self):
        r = serveur.favicon()
        self.assertEqual(r.media_type, "image/x-icon")
        with open(r.path, "rb") as fh:
            data = fh.read()
        reserve, typ, n = struct.unpack("<HHH", data[:6])
        self.assertEqual((reserve, typ), (0, 1))
        tailles = sorted(data[6 + 16 * i] for i in range(n))
        self.assertEqual(tailles, [16, 32, 48])
        for i in range(n):
            taille, debut = struct.unpack("<II", data[6 + 16 * i + 8: 6 + 16 * i + 16])
            self.assertEqual(data[debut:debut + 8], b"\x89PNG\r\n\x1a\n")

    def test_icones(self):
        for nom, typ in (("favicon.svg", "image/svg+xml"), ("favicon-48.png", "image/png"),
                         ("favicon-96.png", "image/png"), ("favicon-192.png", "image/png"),
                         ("icon-180.png", "image/png")):
            r = serveur.icons(nom)
            self.assertEqual(r.media_type, typ, nom)
            self.assertTrue(os.path.getsize(r.path) > 0, nom)
        with self.assertRaises(HTTPException):
            serveur.icons("../serveur.py")
        with open(os.path.join(RACINE, "static", "icons", "favicon-48.png"), "rb") as fh:
            entete = fh.read(24)
        self.assertEqual(struct.unpack(">II", entete[16:24]), (48, 48))      # carré, au moins 48 (Google)

    def test_pages(self):
        with open(os.path.join(RACINE, "gamecenter_source.html"), encoding="utf-8") as fh:
            accueil = fh.read()
        with open(os.path.join(RACINE, "static", "legal.html"), encoding="utf-8") as fh:
            legal = fh.read()
        for lien in LIENS:
            self.assertIn(lien, accueil.split("</head>")[0] if "</head>" in accueil else accueil[:4000])
            self.assertIn(lien, legal)
        self.assertIn('<link rel="apple-touch-icon" href="/icons/icon-180.png">', accueil)   # écran d'accueil inchangé


if __name__ == "__main__":
    unittest.main()
