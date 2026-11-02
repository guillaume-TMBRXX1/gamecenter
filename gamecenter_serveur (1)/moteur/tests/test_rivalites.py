"""Rivalités, bilans des confrontations et mémoire (moteur/rivalites.py, README section 88).

    python -m unittest moteur.tests.test_rivalites        (depuis « gamecenter_serveur (1) »)
"""
import glob
import json
import os
import unittest

from moteur import rivalites as R

ICI = os.path.dirname(os.path.abspath(__file__))
SEMAINE = sorted(glob.glob(os.path.join(ICI, "..", "..", "data", "weeks", "week_*", "week.json")))[-1]   # la dernière


def m(i, home, away, hs, as_, ot=False, phase="regular"):
    return {"id": f"g{i}", "week": i, "kickoff": f"2026-10-{10 + i:02d}T12:00:00+02:00", "phase": phase,
            "home": home, "away": away, "hs": hs, "as": as_, "ot": ot}


class Table(unittest.TestCase):
    def test_douze_rivalites_une_par_franchise_dans_sa_division(self):
        self.assertEqual(len(R.RIVALITES), 12)
        equipes = [x for a, b, _ in R.RIVALITES for x in (a, b)]
        self.assertEqual(len(equipes), 24)
        self.assertEqual(len(set(equipes)), 24)                         # chacune une seule fois
        with open(SEMAINE, encoding="utf-8") as fh:
            ligue = json.load(fh)["week"]["league"]
        div = {t: d for c in ligue.values() for d, ts in c.items() for t in ts}
        self.assertEqual(set(div), set(equipes))
        for a, b, t in R.RIVALITES:
            self.assertEqual(div[a], div[b], (a, b))                       # même division
            self.assertTrue(t)
        self.assertNotIn("Bowl", " ".join(t for _, _, t in R.RIVALITES))   # rien qui rappelle le Super Bowl

    def test_rival_et_trophee(self):
        self.assertEqual(R.rival("GLT"), "AEG")
        self.assertEqual(R.rival("AEG"), "GLT")
        self.assertEqual(R.trophee("GLT", "AEG"), "The Firewall")
        self.assertIsNone(R.trophee("GLT", "VEC"))


class Serie(unittest.TestCase):
    def test_bilan_serie_trophee(self):
        M = [m(1, "AEG", "GLT", 20, 10), m(2, "GLT", "AEG", 17, 17, ot=True), m(3, "GLT", "AEG", 24, 21),
             m(4, "AEG", "GLT", 9, 30), m(5, "VEC", "GLT", 3, 40)]
        s = R.serie(M, "AEG", "GLT")
        self.assertEqual(s["games"], 4)                                    # VEC–GLT n'en fait pas partie
        self.assertEqual(s["record"], {"AEG": 1, "GLT": 2, "ties": 1})
        self.assertEqual(s["streak"], {"team": "GLT", "n": 2})
        self.assertEqual(s["last"]["id"], "g4")
        self.assertEqual([x["id"] for x in s["recent"]], ["g4", "g3", "g2", "g1"])
        self.assertEqual((s["biggest"]["id"], s["biggest"]["margin"]), ("g4", 21))
        self.assertEqual(s["classic"]["id"], "g2")                         # la prolongation d'abord
        self.assertEqual(s["rivalry"], {"trophy": "The Firewall", "holder": "GLT"})

    def test_nul_ne_change_pas_le_detenteur(self):
        s = R.serie([m(1, "AEG", "GLT", 20, 10), m(2, "GLT", "AEG", 14, 14)], "AEG", "GLT")
        self.assertEqual(s["rivalry"]["holder"], "AEG")
        self.assertIsNone(s["streak"])                                     # le plus récent est un nul

    def test_classique_le_plus_serre(self):
        s = R.serie([m(1, "VEC", "MNL", 30, 29), m(2, "VEC", "MNL", 31, 28), m(3, "VEC", "MNL", 40, 10)], "VEC", "MNL")
        self.assertEqual(s["classic"]["id"], "g1")
        self.assertIsNone(s["rivalry"])                                    # pas une rivalité
        self.assertIsNone(R.serie([m(1, "VEC", "MNL", 40, 10)], "VEC", "MNL")["classic"])   # rien de serré

    def test_aucune_confrontation(self):
        s = R.serie([], "AEG", "GLT")
        self.assertEqual((s["games"], s["last"], s["classic"], s["streak"]), (0, None, None, None))
        self.assertEqual(s["rivalry"], {"trophy": "The Firewall", "holder": None})


if __name__ == "__main__":
    unittest.main()
