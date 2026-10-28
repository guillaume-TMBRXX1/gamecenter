"""Identité de jeu des franchises (moteur/identite_franchises.py — refonte des playbooks, étape 2).

Tables cohérentes avec le catalogue de l'extension (formations, concepts, paquets, fronts, jeux de rush) ; playbook
d'identité (exclusifs des autres retirés sans perte de poids, bonus de l'exclusif, multiplicateurs, menu resserré,
budget de la famille conservé) ; feuille d'appel ; motion (déterministe, son propre flux) ; personnel de ZPH ;
couvertures et styles défensifs ; SALEM et SPILL_PROTECTION sortis de la réserve.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import copy
import unittest

from moteur import identite_franchises as idf
from moteur import playbook_expansion as xp

BASE_FORMATIONS = {"SHOTGUN", "TRIPS", "EMPTY", "SINGLEBACK", "PISTOL", "I_FORM", "ACE", "JUMBO", "BUNCH", "HEAVY", "PONY"}
BASE_CONCEPTS = {"INSIDE_RUN", "OUTSIDE_RUN", "POWER", "COUNTER", "DRAW", "TRAP", "READ_OPTION", "JET_SWEEP",
                 "QUICK_SLANT", "SHORT_OUT", "CROSS", "SCREEN", "FOUR_VERTS", "DEEP_POST", "PLAY_ACTION", "CORNER", "IN",
                 "DRAG", "STICK", "CURL", "CHAMP", "DAGGER", "SAIL", "MESH", "BOOT", "POP"}


class TestTables(unittest.TestCase):
    def test_controle(self):
        err = idf.controle(set(xp.FORMATIONS) | BASE_FORMATIONS, set(xp.CONCEPTS) | BASE_CONCEPTS, xp.PAQUETS, xp.RUSH,
                           xp.FRONTS, set(xp.FRANCHISES))
        self.assertEqual(err, [])

    def test_une_fiche_par_franchise(self):
        self.assertEqual(set(idf.SYSTEMES), set(xp.FRANCHISES))
        self.assertEqual(set(idf.EXCLUSIFS), set(xp.FRANCHISES))
        self.assertEqual(set(idf.ATTAQUE), set(xp.FRANCHISES))

    def test_exclusifs(self):
        tous = [pid for d in idf.EXCLUSIFS.values() for pid in d]
        self.assertEqual(len(tous), len(set(tous)), "un play exclusif appartient à une seule franchise")
        self.assertGreaterEqual(len(tous), 96)
        for a, d in idf.EXCLUSIFS.items():
            for pid, (f, c) in d.items():
                self.assertEqual(idf.proprietaire(pid), a)
                if pid in xp.PLAYS:                                 # play de l'extension réservé : même combinaison
                    self.assertEqual(xp.PLAYS[pid], (f, c), pid)
                self.assertNotIn(c, xp.EXCLUS_CONCEPTS.get(a, set()), pid)     # pas contre l'identité
                self.assertNotIn(f, xp.EXCLUS_FORMATIONS.get(a, set()), pid)

    def test_parts_en_plus(self):
        for a, parts in idf.PARTS_EN_PLUS.items():
            for c in parts:
                self.assertIn(c, xp.CONCEPTS)
                self.assertNotIn(c, xp.PARTS.get(a, {}), (a, c))   # concept sans budget avant

    def test_motion_types(self):
        for a, (p, types) in idf.MOTION.items():
            self.assertTrue(0 < p < 1)
            self.assertAlmostEqual(sum(types.values()), 1.0)
            for m in types:
                self.assertIn(m, xp.MOTIONS)


class TestPlaybook(unittest.TestCase):
    # (play, concept, formation, poids) : deux variantes de STICK, un exclusif d'AXM (BUNCH_SPOT) et un de VEC
    PLAYS = [("A_STICK", "STICK", "SHOTGUN", 2.0), ("B_STICK", "STICK", "TRIPS", 2.0),
             ("BUNCH_SPOT", "SPOT_SNAG", "BUNCH", 1.0), ("X_SPOT", "SPOT_SNAG", "SHOTGUN", 1.0),
             ("VEC_EMPTY_DIVIDE", "DIVIDE", "EMPTY", 1.0), ("Z_DIVIDE", "DIVIDE", "SHOTGUN", 3.0)]

    def test_exclusif_des_autres_retire_sans_perte(self):
        out = dict(idf.playbook("CTX", "PASS", self.PLAYS))
        self.assertNotIn("BUNCH_SPOT", out)
        self.assertNotIn("VEC_EMPTY_DIVIDE", out)
        self.assertAlmostEqual(sum(out.values()), sum(w for *_, w in self.PLAYS))

    def test_exclusif_de_la_franchise(self):
        out = dict(idf.playbook("AXM", "PASS", self.PLAYS))
        self.assertIn("BUNCH_SPOT", out)
        self.assertNotIn("VEC_EMPTY_DIVIDE", out)
        self.assertGreater(out["BUNCH_SPOT"], out["X_SPOT"])          # bonus de l'exclusif
        self.assertAlmostEqual(sum(out.values()), sum(w for *_, w in self.PLAYS))

    def test_multiplicateurs(self):
        sauve = copy.deepcopy(idf.ATTAQUE)
        try:
            idf.ATTAQUE["CTX"] = {"concepts": {"STICK": 3.0}, "formations": {}}
            out = dict(idf.playbook("CTX", "PASS", self.PLAYS))
            stick = out["A_STICK"] + out["B_STICK"]
            self.assertGreater(stick / sum(out.values()), 4.0 / 10.0)   # STICK pesait 4 sur 10
            idf.ATTAQUE["CTX"] = {"concepts": {}, "formations": {"TRIPS": 2.0}}
            out = dict(idf.playbook("CTX", "PASS", self.PLAYS))
            self.assertAlmostEqual(out["B_STICK"], 2 * out["A_STICK"])
        finally:
            idf.ATTAQUE.clear()
            idf.ATTAQUE.update(sauve)

    def test_menu_resserre(self):
        sauve = copy.deepcopy(idf.MENU)
        try:
            idf.MENU["CTX"] = {"PASS": 2}
            out = dict(idf.playbook("CTX", "PASS", self.PLAYS))
            self.assertEqual(len(out), 2)
            self.assertAlmostEqual(sum(out.values()), sum(w for *_, w in self.PLAYS))
        finally:
            idf.MENU.clear()
            idf.MENU.update(sauve)

    def test_famille_vide(self):
        self.assertEqual(idf.playbook("CTX", "RUN", []), [])


class TestSnap(unittest.TestCase):
    def test_situation(self):
        k = idf.multiplicateur_situation("APX", ["red_zone"], "MESH_WHEEL", "GUN_STACK")
        self.assertGreater(k, 3.0)
        self.assertEqual(idf.multiplicateur_situation("APX", ["long"], "MESH_WHEEL", "GUN_STACK"), 1.0)
        self.assertEqual(idf.multiplicateur_situation("CTX", ["red_zone"], "MESH_WHEEL", "GUN_STACK"), 1.0)

    def test_motion_deterministe(self):
        vus = [idf.motion("PRM", 1234, n) for n in range(400)]
        self.assertEqual(vus, [idf.motion("PRM", 1234, n) for n in range(400)])
        part = sum(m is not None for m in vus) / len(vus)
        self.assertAlmostEqual(part, idf.MOTION["PRM"][0], delta=0.08)
        self.assertTrue(set(vus) - {None} <= set(idf.MOTION["PRM"][1]))
        self.assertIsNone(idf.motion("CTX", 1234, 0))

    def test_personnel(self):
        self.assertEqual(idf.personnel("ZPH", "GUN_QUADS", "11"), "10")
        self.assertEqual(idf.personnel("ZPH", "SHOTGUN", "11"), "11")
        self.assertEqual(idf.personnel("ZPH", "ACE", "12"), "12")
        self.assertEqual(idf.personnel("VEC", "SHOTGUN", "11"), "11")
        self.assertEqual(xp.compatibilite("10", {"RB": 3, "TE": 2, "WR": 4})[0], "PRIMARY")   # roster + banc de ZPH


class TestDefense(unittest.TestCase):
    def test_couvertures(self):
        poids = {"MAN": 1.0, "ZONE": 1.0, "COVER_2": 1.0, "COVER_4": 1.0}
        cov, blitz = idf.couvertures("BST", poids, 0.10)
        self.assertGreater(cov["MAN"] / sum(cov.values()), 0.4)
        self.assertLess(blitz, 0.10)
        self.assertEqual(poids["MAN"], 1.0, "poids du coordinateur non modifiés")
        self.assertEqual(idf.couvertures("CTX", poids, 0.10), (poids, 0.10))

    def test_styles(self):
        p, r, f = copy.deepcopy(xp.PAQUETS_STYLE), copy.deepcopy(xp.RUSH_STYLE), copy.deepcopy(xp.FRONTS_STYLE)
        idf.appliquer_styles(p, r, f)
        self.assertIn("SPILL_PROTECTION", p["GRZ"]["BOX_STACK"])
        self.assertGreater(p["ONX"]["MAN"]["COVER_1_ROBBER"], xp.PAQUETS_STYLE["ONX"]["MAN"]["COVER_1_ROBBER"])
        self.assertGreater(r["FRG"]["INTERIOR_COLLAPSE"], xp.RUSH_STYLE["FRG"]["INTERIOR_COLLAPSE"])
        self.assertGreater(f["GRZ"]["BEAR"], xp.FRONTS_STYLE["GRZ"]["BEAR"])
        self.assertEqual(p["CTX"], xp.PAQUETS_STYLE["CTX"])
        self.assertNotIn("SPILL_PROTECTION", xp.PAQUETS_STYLE["GRZ"]["BOX_STACK"], "styles d'origine intacts")


class TestSortisDeLaReserve(unittest.TestCase):
    def test_salem(self):
        self.assertNotIn("SALEM", xp.RESERVE)
        d = xp.CONCEPTS["SALEM"]
        self.assertEqual((d["famille"], d["ancre"]), ("PASS", "SAIL"))
        self.assertEqual([r for _, r in xp.PROGRESSIONS["SALEM"]], ["DIG", "FLAT", "GO", "DRAG"])
        self.assertIn("SALEM", xp.DESSIN_PASSE)
        self.assertFalse(any(c == "SALEM" for _, c in xp.PLAYS.values()), "SALEM n'est joué que par l'identité")

    def test_spill_protection(self):
        self.assertNotIn("SPILL_PROTECTION", xp.RESERVE)
        base, fam, coq, rushers, pres, eff = xp.PAQUETS["SPILL_PROTECTION"]
        self.assertEqual(rushers, 5)
        self.assertLess(eff["scramble"], 1)
        self.assertLess(xp.effet_course("POWER", paquet="SPILL_PROTECTION"), 0)
        self.assertGreater(xp.effet_course("OUTSIDE_RUN", paquet="SPILL_PROTECTION"), 0)
        self.assertEqual(xp.effet_course("POWER", paquet="FIRE_ZONE"), xp.effet_course("POWER"))
        self.assertFalse(any("SPILL_PROTECTION" in d.get(c, {}) for d in xp.PAQUETS_STYLE.values() for c in d))


if __name__ == "__main__":
    unittest.main()
