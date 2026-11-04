"""« Week in review », l'émission du week-end (moteur/recap_semaine.py, /api/review, README section 92).

  Notes        interet et spectacle identiques à ceux des vidéos (outils/video/choisir.py) sur toute une semaine
  Playlist     rubriques, extra points exclus, 2 actions au plus par match dans « Plays of the week », éditions
               (saison régulière, demi-finales, finale), toujours la même
  Direct       /api/review : rien avant le verrou du vendredi, seulement des matchs terminés, interrupteur

    python -m unittest moteur.tests.test_recap_semaine        (depuis « gamecenter_serveur (1) »)
"""
import collections
import glob
import json
import os
import sys
import unittest
from unittest import mock

from moteur import recap_semaine as R
from moteur.tests import test_serveur as ts

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
SEMAINE = sorted(glob.glob(os.path.join(RACINE, "data", "weeks", "week_*")))[-1]
sys.path.insert(0, os.path.join(RACINE, "outils", "video"))
import choisir as C  # noqa: E402


def _semaine():
    with open(os.path.join(SEMAINE, "week.json"), encoding="utf-8") as fh:
        doc = json.load(fh)
    jeux = []
    for g in doc["schedule"]:
        with open(os.path.join(SEMAINE, g["feed"]), encoding="utf-8") as fh:
            jeux.append((g, json.load(fh)))
    return doc, jeux


class Calcul(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc, cls.jeux = _semaine()

    def test_memes_notes_que_les_videos(self):
        for g, f in self.jeux[::7]:
            self.assertEqual(R.spectacle(f, g), C.spectacle(f, g), g["id"])
            for i in range(len(f["plays"])):
                self.assertEqual(R.interet(f, i), C.interet(f, i), (g["id"], i))

    def test_playlist_complete(self):
        r = R.calculer(self.jeux, "CPH")
        self.assertEqual(r["edition"], "final")
        cles = [s["key"] for s in r["segments"]]
        self.assertEqual(cles[:2], ["final", "semis"])                               # les playoffs d'abord
        for k in ("plays", "game", "takeaways", "shootouts", "franchise"):
            self.assertIn(k, cles)
        F = {g["id"]: f for g, f in self.jeux}
        for s in r["segments"]:
            self.assertTrue(s["title"] and s["clips"])
            for c in s["clips"]:
                P = F[c["game"]]["plays"][c["index"]]
                self.assertFalse(R._pat(P), c)                                     # pas d'extra point
                self.assertEqual(c["text"], str(P.get("text") or ""))
        plays = next(s for s in r["segments"] if s["key"] == "plays")["clips"]
        self.assertEqual(len(plays), R.N_PLAYS)
        self.assertLessEqual(max(collections.Counter(c["game"] for c in plays).values()), R.PAR_MATCH)
        reg = {g["id"] for g, _ in self.jeux if g["phase"] == "regular"}
        self.assertTrue(all(c["game"] in reg for c in plays))
        fr = next(s for s in r["segments"] if s["key"] == "franchise")
        self.assertTrue(all("CPH" in (c["away"], c["home"]) for c in fr["clips"]))
        self.assertEqual(R.calculer(list(reversed(self.jeux)), "CPH"), r)              # toujours la même

    def test_editions(self):
        reg = [(g, f) for g, f in self.jeux if g["phase"] == "regular"]
        r = R.calculer(reg)
        self.assertEqual(r["edition"], "regular")
        self.assertNotIn("final", [s["key"] for s in r["segments"]])
        r2 = R.calculer(reg + [(g, f) for g, f in self.jeux if g["phase"] == "semifinal"])
        self.assertEqual((r2["edition"], r2["segments"][0]["key"]), ("semis", "semis"))
        self.assertEqual(R.calculer([])["segments"], [])

    def test_blessures_et_remontees(self):
        r = R.calculer(self.jeux)
        F = {g["id"]: f for g, f in self.jeux}
        inj = next((s for s in r["segments"] if s["key"] == "injuries"), None)
        if inj:
            w = [F[c["game"]]["plays"][c["index"]]["injury"]["weeks"] for c in inj["clips"]]
            self.assertEqual(w, sorted(w, reverse=True))
            self.assertTrue(all(x >= 1 for x in w))
        cb = next((s for s in r["segments"] if s["key"] == "comebacks"), None)
        if cb:
            for c in cb["clips"]:
                self.assertGreaterEqual(F[c["game"]]["plays"][c["index"]].get("quarter") or 0, 3)

    def test_franchise_du_rang(self):
        eq = {t: {} for t in ("AAA", "BBB", "CCC")}
        self.assertEqual(R.franchise_du_rang(eq, "2026-09-28", "2026-09-28"), "AAA")
        self.assertEqual(R.franchise_du_rang(eq, "2026-09-28", "2026-10-12"), "CCC")
        self.assertEqual(R.franchise_du_rang(eq, "2026-09-28", "2026-10-19"), "AAA")


class Serveur(ts.Base):
    def setUp(self):
        ts.serveur._REV_CACHE.clear()

    def _get(self):
        return json.loads(ts.serveur.api_review().body)

    def test_rien_avant_le_verrou(self):
        ts.a_l_heure(self.w.lock - 60_000)
        d = self._get()
        self.assertFalse(d["on"])
        self.assertNotIn("segments", d)

    def test_seulement_les_matchs_finis(self):
        sf = self.w.semis[0]
        for t in (self.w.lock + 60_000, sf["ko"] + 60_000, self.w.final["end"] + 60_000):
            ts.a_l_heure(t)
            ts.serveur._REV_CACHE.clear()
            d = self._get()
            self.assertTrue(d["on"])
            finis = {g["id"] for g in self.w.sched if self.w.status(g, t) == "final"}
            for s in d["segments"]:
                for c in s["clips"]:
                    self.assertIn(c["game"], finis)
        self.assertEqual(d["edition"], "final")
        ts.a_l_heure(sf["ko"] + 60_000)
        ts.serveur._REV_CACHE.clear()
        self.assertEqual(self._get()["edition"], "regular")                         # demi-finales en cours : pas encore

    def test_interrupteur(self):
        with mock.patch.dict(os.environ, {"GC_WEEK_REVIEW": "off"}):
            self.refus(404, ts.serveur.api_review)
            self.assertFalse(ts.serveur.week_review_on())


if __name__ == "__main__":
    unittest.main()
