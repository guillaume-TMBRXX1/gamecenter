"""Identité de jeu des franchises (outils/moteur/identite_playbooks.py — refonte des playbooks, étape 1).

Vérifie sur deux matchs fabriqués : classement par concept appelé (un scramble sur une passe reste une passe, genou et
spike exclus), familles, situations (1er & 10, 3e et long, courte distance, zone rouge selon le sens d'attaque), 4e essais
tentés (punt et field goal au dénominateur), défense attribuée à l'équipe qui défend (blitz, homme, ballons récupérés),
plays exclusifs, signatures, divergence de Jensen-Shannon (0 identique, 1 disjoint), rapport Markdown.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import json
import os
import sys
import tempfile
import unittest
from collections import Counter

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
sys.path.insert(0, os.path.join(RACINE, "outils", "moteur"))
import identite_playbooks as ip  # noqa: E402


def action(off, concept, typ, play_id, formation="SHOTGUN", down=1, to_go=10, los_x=50, gain=4, result="run",
           defense=None, motion=None, personnel="11"):
    return {"offense": off, "down": down, "to_go": to_go, "los_x": los_x, "gain": gain, "result": result,
            "call": {"type": typ, "concept": concept, "play_id": play_id, "formation": formation, "personnel": personnel,
                     "motion": motion, "defense": defense or {"concept": "COVER_3", "formation": "NICKEL"}}}


class TestIdentite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="gc-identite-")
        sem = os.path.join(cls.tmp, "week_2026-01-05")
        os.makedirs(os.path.join(sem, "games"))
        # match 1 : AAA (domicile) contre BBB ; AAA court en force et passe court, BBB lance profond
        p1 = [
            action("home", "POWER", "run", "I_POWER", formation="I_FORM", personnel="21"),
            action("home", "POWER", "run", "I_POWER", formation="I_FORM", personnel="21", down=3, to_go=1),
            action("home", "STICK", "pass", "GUN_STICK", down=3, to_go=8, result="complete"),
            action("home", "CORNER", "run", "GUN_CORNER", result="run", gain=12),        # scramble : reste une passe
            action("home", "INSIDE_RUN", "run", "GUN_IZ", los_x=95, gain=3),             # domicile : 15 yards du but
            action("home", "KNEEL", "run", "KNEEL"),                                     # exclu
            action("home", "POWER", "run", "I_POWER", down=4, to_go=1, formation="I_FORM", personnel="21"),
            {"offense": "home", "down": 4, "to_go": 6, "los_x": 40, "result": "punt", "call": {"type": "punt"}},
            action("away", "DEEP_POST", "pass", "TRIPS_POST", formation="TRIPS", gain=35, result="complete",
                   defense={"concept": "BLITZ", "formation": "NICKEL", "package": "FIRE_ZONE", "rush": "TEX_STUNT"}),
            action("away", "DEEP_POST", "pass", "TRIPS_POST", formation="TRIPS", result="interception",
                   defense={"concept": "MAN", "formation": "DIME"}),
            action("away", "FOUR_VERTS", "pass", "EMPTY_VERTS", formation="EMPTY", los_x=25, result="incomplete",
                   motion="JET"),                                                        # extérieur : 15 yards du but
        ]
        # match 2 : BBB (domicile) contre AAA, une action chacun
        p2 = [action("home", "DEEP_POST", "pass", "TRIPS_POST", formation="TRIPS"),
              action("away", "STICK", "pass", "GUN_STICK")]
        for i, plays in enumerate((p1, p2)):
            json.dump({"game": {"home": {"abbr": ("AAA", "BBB")[i]}, "away": {"abbr": ("BBB", "AAA")[i]}}, "plays": plays},
                      open(os.path.join(sem, "games", f"g{i}.json"), "w"))
        json.dump({"schedule": [{"id": "g0", "feed": "games/g0.json"}, {"id": "g1", "feed": "games/g1.json"}]},
                  open(os.path.join(sem, "week.json"), "w"))
        cls.E = ip.mesurer(ip.semaines(0, cls.tmp))
        cls.R, cls.L = ip.analyser(cls.E)

    def test_classement_par_concept_appele(self):
        self.assertEqual(ip.famille("CORNER"), "profonde")
        self.assertEqual(ip.famille("RPO_READ"), "rpo")
        self.assertEqual(ip.famille("INCONNU"), "autre")
        self.assertTrue(ip.est_passe("CORNER"))
        self.assertTrue(ip.est_passe("RPO_READ_THROW"))
        self.assertFalse(ip.est_passe("RPO_READ"))
        self.assertFalse(ip.est_passe("POWER"))
        a = self.E["AAA"]
        self.assertEqual(a["snaps"], 7)                     # genou exclu, punt pas compté comme appel
        self.assertEqual(a["passes"], 3)                    # STICK ×2 et le scramble sur CORNER
        self.assertEqual(a["familles"]["profonde"], 1)
        self.assertEqual(a["formations"]["I_FORM"], 3)

    def test_situations(self):
        a, b = self.R["AAA"], self.R["BBB"]
        self.assertEqual(ip.yards_a_marquer({"offense": "home", "los_x": 95}), 15)
        self.assertEqual(ip.yards_a_marquer({"offense": "away", "los_x": 25}), 15)
        self.assertIsNone(ip.yards_a_marquer({"offense": "home"}))
        self.assertAlmostEqual(a["passe_3e_long"], 1.0)     # 3e et 8 : STICK
        self.assertAlmostEqual(a["course_courte_distance"], 1.0)   # 3e et 1, 4e et 1 : POWER
        self.assertEqual(a["zone_rouge"], {"course_interieure": 1.0})
        self.assertEqual(b["zone_rouge"], {"profonde": 1.0})
        self.assertAlmostEqual(a["quatrieme_tente"], 0.5)   # 4e et 1 tenté, 4e et 6 : punt
        self.assertAlmostEqual(b["motion"], 1 / 4)
        self.assertAlmostEqual(b["gros_gains"], 1 / 4)

    def test_defense_attribuee_a_l_equipe_qui_defend(self):
        d = self.R["AAA"]["def"]                            # AAA défend contre les passes de BBB
        self.assertEqual(d["snaps"], 4)
        self.assertAlmostEqual(d["blitz"], 1 / 4)
        self.assertAlmostEqual(d["homme"], 1 / 4)
        self.assertAlmostEqual(d["stunts"], 1 / 4)
        self.assertEqual(d["paquets"], [("FIRE_ZONE", 0.25)])
        self.assertAlmostEqual(d["ballons_par_match"], 0.5)   # 1 interception en 2 matchs
        self.assertEqual(self.R["BBB"]["def"]["ballons_par_match"], 0.0)

    def test_exclusifs_signatures_ecarts(self):
        self.assertIn("I_POWER", self.R["AAA"]["plays_exclusifs"])
        self.assertNotIn("TRIPS_POST", self.R["AAA"]["plays_exclusifs"])
        self.assertIn("TRIPS_POST", self.R["BBB"]["plays_exclusifs"])
        self.assertEqual(self.L["plays_distincts"], 6)
        self.assertEqual(self.L["plays_exclusifs"], 6)
        self.assertIn("POWER", [k for k, _, _ in self.R["AAA"]["signatures"]])
        self.assertEqual(self.R["AAA"]["plus_proche"][0], "BBB")
        self.assertEqual(ip.js(Counter(a=2, b=1), Counter(a=4, b=2)), 0.0)
        self.assertAlmostEqual(ip.js(Counter(a=1), Counter(b=1)), 1.0)
        self.assertIsNone(ip.js(Counter(), Counter(a=1)))

    def test_rapport_markdown(self):
        md = ip.markdown(self.R, self.L, "essai")
        self.assertIn("# Identité de jeu des franchises — essai", md)
        self.assertIn("## AAA", md)
        self.assertIn("| BBB |", md)
        self.assertIn("passes profondes", md)


if __name__ == "__main__":
    unittest.main()
