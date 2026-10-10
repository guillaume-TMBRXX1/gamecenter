"""Pauses de retransmission (10/10/2026) : fin du Q1 / Q3, mi-temps, fin du match. Temps de PRÉSENTATION seulement.

Vérifie, sur toutes les semaines de data/weeks : les pauses repérées sur l'action qui termine la période, leurs durées,
la ligne de temps du serveur (actions révélées, fin des matchs) et la même ligne de temps calculée par le site
(gamecenter_source.html, exécuté dans Node si Node est installé). Quelques secondes :

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
SEMAINES = sorted(glob.glob(os.path.join(RACINE, "data", "weeks", "week_*")))
PAGE = os.path.join(RACINE, "gamecenter_source.html")

try:                                    # le serveur (fastapi) n'est pas installé partout : tests du serveur sautés
    os.environ.setdefault("GC_DATA", tempfile.mkdtemp(prefix="gc-pauses-"))
    sys.path.insert(0, RACINE)
    import serveur
except Exception as e:                  # pragma: no cover
    serveur, ERREUR = None, e


def feeds():
    for w in SEMAINES:
        for f in sorted(glob.glob(os.path.join(w, "games", "*.json"))):
            with open(f, encoding="utf-8") as fh:
                yield os.path.basename(f), json.load(fh)


@unittest.skipIf(serveur is None, "serveur.py non importable (fastapi absent)")
class TestServeur(unittest.TestCase):
    def test_pauses_reperees(self):
        """Une pause après chaque fin de Q1 et de Q3, une mi-temps, aucune après la dernière action."""
        n = 0
        for nom, f in feeds():
            P = f["plays"]
            kinds = [(serveur.break_kind(p), p["quarter"]) for p in P if serveur.break_kind(p)]
            # fin de période ⇔ changement de quart-temps à l'action suivante
            for i, p in enumerate(P[:-1]):
                self.assertEqual(bool(serveur.break_kind(p)), P[i + 1]["quarter"] != p["quarter"], (nom, i))
            self.assertIsNone(serveur.break_kind(P[-1]), nom)
            self.assertEqual([k for k, _ in kinds][:3], ["q", "half", "q"], nom)
            self.assertEqual([q for _, q in kinds][:3], [1, 2, 3], nom)
            n += 1
        self.assertGreater(n, 100)

    def test_durees(self):
        self.assertTrue(8 <= serveur.BREAK_SEC["q"] <= 12)
        self.assertTrue(30 <= serveur.BREAK_SEC["half"] <= 45)

    def test_ligne_de_temps(self):
        """Fin du match = n·6,5 s + les pauses ; l'action qui termine la mi-temps est révélée AVANT la pause, la
        suivante 40 s plus tard ; pendant la pause, rien de nouveau."""
        w = serveur.Week(SEMAINES[-1])
        g = w.reg[0]
        P = w.feeds[g["id"]]["plays"]
        tot = sum(serveur.BREAK_SEC[serveur.break_kind(p)] for p in P if serveur.break_kind(p))
        self.assertEqual(g["end"], g["ko"] + int((len(P) * serveur.PLAY_SEC + tot) * 1000))
        h = next(i for i, p in enumerate(P) if serveur.break_kind(p) == "half")
        fin_h = g["ko"] + g["ends"][h] * 1000              # l'action h finit son temps d'écran
        self.assertEqual(w.revealed_plays(g, fin_h - 1), h)
        self.assertEqual(w.revealed_plays(g, fin_h), h + 1)
        for dt in (1000, 20000, 39000):                    # pause : toujours h + 1 actions révélées
            self.assertEqual(w.revealed_plays(g, fin_h + dt), h + 1)
        reprise = fin_h + (serveur.BREAK_SEC["half"] + serveur.PLAY_SEC) * 1000
        self.assertEqual(w.revealed_plays(g, reprise - 1), h + 1)
        self.assertEqual(w.revealed_plays(g, reprise), h + 2)
        self.assertEqual(w.revealed_plays(g, g["end"]), len(P))
        self.assertEqual(w.status(g, g["end"] - 1), "live")
        self.assertEqual(w.status(g, g["end"]), "final")

    def test_sans_pause_identique(self):
        """Avant la première fin de quart-temps, la ligne de temps est celle d'avant (une action toutes les 6,5 s)."""
        w = serveur.Week(SEMAINES[-1])
        g = w.reg[1]
        q1 = next(i for i, p in enumerate(w.feeds[g["id"]]["plays"]) if serveur.break_kind(p))
        for k in range(0, q1 + 1):
            t = g["ko"] + int(k * serveur.PLAY_SEC * 1000) + 3000
            self.assertEqual(w.revealed_plays(g, t), k)

    def test_actions_inchangees(self):
        """Les pauses n'ajoutent ni ne modifient aucune action : le flux public est une tranche du flux du moteur."""
        w = serveur.Week(SEMAINES[-1])
        g = w.reg[2]
        P = w.feeds[g["id"]]["plays"]
        for t in (g["ko"] + 60000, (g["ko"] + g["end"]) // 2, g["end"]):
            pub = w.public_feed(g, t)["plays"]
            self.assertEqual(pub, P[:len(pub)])


@unittest.skipUnless(shutil.which("node") and os.path.isfile(PAGE), "Node ou la page du site absents")
class TestParite(unittest.TestCase):
    """Le site calcule la même ligne de temps que le serveur (brkKind, BRK_SEC, tlOf extraits de la page)."""

    def test_meme_ligne_de_temps(self):
        h = open(PAGE, encoding="utf-8").read()
        m = re.search(r"const BRK_SEC=\{q:(\d+),half:(\d+)\};", h)
        self.assertIsNotNone(m)
        if serveur is not None:
            self.assertEqual({"q": int(m.group(1)), "half": int(m.group(2))}, serveur.BREAK_SEC)
        code = "\n".join([
            "const num=(v,f)=>(typeof v==='number'&&isFinite(v))?v:f; const PLAY_SEC=6.5;",
            m.group(0),
            h[h.index("function brkKind(P)"):h.index("/* breaks are for the match itself")],
            h[h.index("const _tl=new WeakMap();"):h.index("/* where the broadcast of game s is at t")],
            "const fs=require('fs'); const out={};",
            "for(const p of process.argv.slice(2)){ const f=JSON.parse(fs.readFileSync(p)); const L=tlOf(f);",
            "  out[p]={ends:L.st.map(x=>x+PLAY_SEC),total:L.total,bk:L.bk}; }",
            "process.stdout.write(JSON.stringify(out));",
        ])
        files = [os.path.join(w, "games", f) for w in SEMAINES for f in sorted(os.listdir(os.path.join(w, "games")))][:120]
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
            fh.write(code)
        try:
            res = json.loads(subprocess.run(["node", fh.name, *files], capture_output=True, text=True, check=True).stdout)
        finally:
            os.unlink(fh.name)
        for p in files:
            P = json.load(open(p, encoding="utf-8"))["plays"]
            if serveur is not None:
                ends = serveur.play_ends(P)
                self.assertEqual(len(ends), len(res[p]["ends"]))
                for a, b in zip(ends, res[p]["ends"]):
                    self.assertAlmostEqual(a, b, places=6)
                self.assertEqual(res[p]["bk"], [serveur.break_kind(x) for x in P])
            self.assertEqual(res[p]["total"], int(m.group(1)) * 2 + int(m.group(2)))


if __name__ == "__main__":
    unittest.main()
