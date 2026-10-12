"""Vidéos verticales (bloc 2, étape 8) : choix des actions et du match (outils/video/choisir.py), bandeaux et son du
stade (outils/video/faire_video.py, sans filmer : le tournage est vérifié à la main et par le workflow « Vidéos »).

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import glob
import os
import sys
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
sys.path.insert(0, os.path.join(RACINE, "outils", "video"))
import choisir as C  # noqa: E402
import faire_video as V  # noqa: E402

SEMAINES = sorted(glob.glob(os.path.join(RACINE, "data", "weeks", "week_*")))


def action(t, r, gain=0, wp=0.5, down=1, to_go=10, los=60, offense="home", q=2, clock=600, text="", **kw):
    return dict({"call": {"type": t}, "result": r, "gain": gain, "win_prob_home": wp, "down": down, "to_go": to_go,
                 "los_x": los, "offense": offense, "quarter": q, "clock_start": clock, "text": text,
                 "after": {"score": {"home": 0, "away": 0}}}, **kw)


def feed(plays, p_home=0.5):
    return {"game": {"pregame_odds": {"p_home": p_home}}, "plays": plays}


class TestInteret(unittest.TestCase):
    def test_touchdown_et_bascule(self):
        F = feed([action("run", "run", 4, wp=0.52), action("pass", "touchdown", 30, wp=0.70)])
        self.assertGreater(C.interet(F, 1)[0], C.interet(F, 0)[0])
        self.assertEqual(C.interet(F, 1)[1], "touchdown")

    def test_decision_folle(self):
        # 4e et 6 dans son propre camp (attaque « home », ballon à 45 < 60), tenté et réussi
        F = feed([action("run", "run", 2, wp=0.5), action("pass", "complete", 9, wp=0.55, down=4, to_go=6, los=45)])
        n, why = C.interet(F, 1)
        self.assertIn("4th-and-6 gamble", why)
        rate = feed([action("run", "run", 2, wp=0.5), action("pass", "incomplete", 0, wp=0.45, down=4, to_go=6, los=45)])
        self.assertNotIn("gamble", C.interet(rate, 1)[1])

    def test_fin_de_match(self):
        F = feed([action("run", "run", 2, wp=0.30, q=4, clock=20),
                  action("field_goal", "field_goal_good", 0, wp=0.95, q=4, clock=4, text="Field goal good, 58 yds")])
        n, why = C.interet(F, 1)
        self.assertTrue(why.startswith("game-winning"), why)
        self.assertIn("58-yard field goal", why)
        self.assertEqual(V.titre_action(why, F["plays"][1]), "Game-winner: 58-yard field goal")


class TestSonEtBandeaux(unittest.TestCase):
    def test_horloge(self):
        self.assertEqual(V.horloge(action("pass", "complete", q=4, clock=125, down=3, to_go=7)), "Q4 2:05 · 3rd & 7")
        self.assertEqual(V.horloge(action("field_goal", "field_goal_good", q=5, clock=4, down=1, to_go=10)), "OT 0:04")

    def test_evenements(self):
        tl = {"end": 30, "segments": [
            {"type": "card", "from": 0, "to": 2.5},
            {"type": "play", "result": "touchdown", "call": "pass", "td": True, "snap": 3.5, "res": 7.0, "speed": 1},
            {"type": "play", "result": "touchdown", "call": "pass", "td": True, "snap": 12.0, "res": 20.0, "speed": 0.5},
            {"type": "card", "from": 25, "to": 28}]}
        ev = V.evenements_son(tl)
        kinds = [(round(t, 2), k) for t, k, g in ev]
        self.assertIn((3.5, "snap"), kinds)
        self.assertIn((7.0, "react_td"), kinds)
        self.assertNotIn((12.0, "snap"), kinds)                     # le ralenti : pas de snap ni de sifflet
        self.assertIn((20.0, "react_td"), kinds)
        self.assertIn((25.1, "cheer_medium"), kinds)                # carton final
        self.assertTrue(all(t >= 0 for t, k, g in ev))
        assets = V._assets()
        self.assertTrue(all(k in assets for _, k, _ in ev), "chaque son existe dans audio/manifest.json")


@unittest.skipUnless(SEMAINES, "pas de semaine dans data/weeks")
class TestSemaineReelle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc, cls.feeds = C.charger_semaine(SEMAINES[-1])
        cls.jour = C.jour_du_match(cls.doc["schedule"][0])

    def test_action_du_jour(self):
        a = C.action_du_jour(self.doc, self.feeds, self.jour)
        g = next(x for x in self.doc["schedule"] if x["id"] == a["game"])
        self.assertEqual(C.jour_du_match(g), self.jour)
        meilleur = max(C.interet(self.feeds[x["id"]], i)[0] for x in self.doc["schedule"] if C.jour_du_match(x) == self.jour
                       for i in range(len(self.feeds[x["id"]]["plays"])))
        self.assertEqual(a["note"], meilleur)
        self.assertEqual(a, C.action_du_jour(self.doc, self.feeds, self.jour))     # déterministe
        self.assertIsNone(C.action_du_jour(self.doc, self.feeds, "1999-01-01"))

    def test_plus_beau_match_et_resume(self):
        b = C.plus_beau_match(self.doc, self.feeds)
        notes = [C.spectacle(self.feeds[g["id"]], g) for g in self.doc["schedule"]]
        self.assertEqual(b["note"], max(notes))
        F = self.feeds[b["game"]]
        idx = C.resume(F)
        self.assertEqual(idx, sorted(idx))
        self.assertIn(len(F["plays"]) - 1, idx)
        scores = [i for i, P in enumerate(F["plays"]) if P["result"] in ("touchdown", "field_goal_good")]
        self.assertTrue(set(scores) <= set(idx) or len(idx) >= int(C.RESUME_MAX // C.DUREE_ACTION))
        self.assertTrue(C.RESUME_MIN <= len(idx) * C.DUREE_ACTION <= C.RESUME_MAX + C.DUREE_ACTION, len(idx))

    def test_semaine_du_jour(self):
        self.assertEqual(os.path.basename(V.semaine_du(self.jour)), os.path.basename(SEMAINES[-1]))


if __name__ == "__main__":
    unittest.main()
