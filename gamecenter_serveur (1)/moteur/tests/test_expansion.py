"""Tests de l'extension du playbook V0.1 (moteur/playbook_expansion.py). Quelques secondes :

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)

Pas de doublon avec l'existant · catalogue cohérent (plays, progressions, routes, dessins, parts) · compatibilité de
personnel · brancher() idempotent et réversible · lectures RPO / option, paquets, fronts, motion : en distribution et
déterministes · sans appel, le moteur est celui du bloc E.
"""
import copy
import statistics
import unittest

import moteur
from moteur import playbook_expansion as xp
from moteur import progressions, reaction_defensive, plan_de_jeu
from moteur.reaction_defensive import DefensiveReactionEngine
from moteur.aleatoire import flux
from moteur.tests.test_bloc_a import RECEVEURS, DEFENSEURS
from moteur.tests.test_bloc_b import qb_iq

# ce que le notebook avait avant l'extension (cellules 04, 10.5, 12.2 bis, 12.2 ter)
FORMATIONS_EXISTANTES = {"SHOTGUN", "SINGLEBACK", "I_FORM", "PISTOL", "EMPTY", "TRIPS", "ACE", "JUMBO", "BUNCH", "HEAVY",
                         "PONY"}
CONCEPTS_EXISTANTS = {"INSIDE_RUN", "OUTSIDE_RUN", "POWER", "COUNTER", "DRAW", "QB_SNEAK", "QUICK_SLANT", "SHORT_OUT",
                      "CURL", "CROSS", "SCREEN", "COMEBACK", "FOUR_VERTS", "DEEP_POST", "PLAY_ACTION", "CORNER", "IN",
                      "DRAG", "STICK", "CHAMP", "DAGGER", "SAIL", "MESH", "BOOT", "POP", "TRAP", "READ_OPTION",
                      "JET_SWEEP"}
COUVERTURES_EXISTANTES = {"MAN", "ZONE", "COVER_2", "COVER_3", "COVER_4", "BLITZ", "BOX_STACK"}
FRONTS_EXISTANTS = {"4_3", "3_4", "NICKEL", "DIME", "GOAL_LINE"}
PORTEURS = {"INSIDE_RUN", "OUTSIDE_RUN", "POWER", "COUNTER", "DRAW", "QB_SNEAK", "QUICK_SLANT", "SHORT_OUT", "CURL",
            "CROSS", "SCREEN", "COMEBACK", "FOUR_VERTS", "DEEP_POST", "PLAY_ACTION"}


def _etat_modules():
    return (copy.deepcopy(progressions.ROUTES), copy.deepcopy(progressions.PROGRESSIONS),
            copy.deepcopy(progressions.PROGRESSIONS_B), copy.deepcopy(reaction_defensive.AVANTAGE),
            copy.deepcopy(reaction_defensive.AVANTAGE_ROUTE), dict(reaction_defensive.DOUBLE_BASE),
            {f: set(getattr(plan_de_jeu, f)) for f in ("QUICK", "PROFONDS", "BATTRE_HOMME", "BATTRE_ZONE")})


def _restaurer(e):
    for cible, val in zip((progressions.ROUTES, progressions.PROGRESSIONS, progressions.PROGRESSIONS_B,
                           reaction_defensive.AVANTAGE, reaction_defensive.AVANTAGE_ROUTE,
                           reaction_defensive.DOUBLE_BASE), e[:6]):
        cible.clear()
        cible.update(val)
    for f, v in e[6].items():
        getattr(plan_de_jeu, f).clear()
        getattr(plan_de_jeu, f).update(v)


class Branche(unittest.TestCase):
    """Les tests qui ont besoin des tables branchées les restaurent ensuite (les autres blocs restent intacts)."""

    def setUp(self):
        self._avant = _etat_modules()
        xp.brancher()

    def tearDown(self):
        _restaurer(self._avant)


class TestPasDeDoublon(unittest.TestCase):
    def test_formations_nouvelles(self):
        self.assertFalse(set(xp.FORMATIONS) & FORMATIONS_EXISTANTES)
        self.assertFalse(set(xp.FORMATIONS) & set(xp.ALIAS["formations"]))

    def test_concepts_nouveaux(self):
        self.assertFalse(set(xp.CONCEPTS) & CONCEPTS_EXISTANTS)
        self.assertFalse(set(xp.CONCEPTS) & set(xp.ALIAS["concepts"]))
        self.assertFalse(set(xp.PAQUETS) & COUVERTURES_EXISTANTES)
        self.assertFalse(set(xp.PAQUETS) & set(xp.ALIAS["concepts"]) - {"BOX_ROBBER", "BOX_SKY"})
        self.assertFalse(set(xp.FRONTS) & FRONTS_EXISTANTS)
        self.assertFalse(set(xp.FRONTS) & set(xp.ALIAS["formations"]))

    def test_routes_nouvelles(self):
        self.assertFalse(set(xp.ROUTES) & set(progressions.ROUTES))
        self.assertFalse(set(xp.ROUTES) & set(xp.ALIAS["routes"]))

    def test_aucun_play_en_double(self):
        vus = set()
        for pid, (f, c) in xp.PLAYS.items():
            self.assertNotIn((f, c), vus, pid)          # une seule variante par (formation, concept)
            vus.add((f, c))


class TestCatalogue(unittest.TestCase):
    def test_plays_valides(self):
        for pid, (f, c) in xp.PLAYS.items():
            self.assertTrue(f in xp.FORMATIONS or f in FORMATIONS_EXISTANTES, pid)
            self.assertTrue(c in xp.CONCEPTS or c in CONCEPTS_EXISTANTS, pid)
            if f in xp.FORMATIONS and xp.FORMATIONS[f].get("passes") is False:
                fam = xp.CONCEPTS[c]["famille"] if c in xp.CONCEPTS else "RUN"
                self.assertEqual(fam, "RUN", pid)
            self.assertTrue(xp.nom_play(pid))

    def test_chaque_concept_et_formation_joue(self):
        from moteur import identite_franchises
        joues_c = {c for _, c in xp.PLAYS.values()}
        joues_c |= {c for d in identite_franchises.EXCLUSIFS.values() for _, c in d.values()}   # SALEM (identité)
        joues_f = {f for f, _ in xp.PLAYS.values()}
        for c, d in xp.CONCEPTS.items():
            if not d.get("rpo_de"):
                self.assertIn(c, joues_c, c)
        self.assertEqual(set(xp.FORMATIONS) - joues_f, set())

    def test_formations(self):
        for f, d in xp.FORMATIONS.items():
            self.assertIn(d["type"], {"SHOTGUN", "SINGLEBACK", "I_FORM", "PISTOL", "EMPTY"}, f)
            self.assertIn(d["personnel"], xp.PERSONNEL, f)
            self.assertEqual(set(d["align"]), {"TE", "QB", "RB", "WR1", "WR2", "WR3"}, f)
            self.assertNotEqual(xp.compatibilite(d["personnel"], {"RB": 2, "TE": 1, "WR": 3})[0], "INVALID", f)

    def test_concepts(self):
        toutes_routes = set(progressions.ROUTES) | set(xp.ROUTES)
        for c, d in xp.CONCEPTS.items():
            self.assertIn(d["porteur"], PORTEURS, c)
            if d.get("ancre"):
                self.assertIn(d["ancre"], CONCEPTS_EXISTANTS, c)
            if d["famille"] == "PASS":
                self.assertIn(c, xp.PROGRESSIONS, c)
                self.assertIn(c, xp.DESSIN_PASSE, c)
                for role, route in xp.PROGRESSIONS[c]:
                    self.assertIn(role, progressions.ROLES, c)
                    self.assertIn(route, toutes_routes, (c, route))
            if d.get("option"):
                self.assertAlmostEqual(sum(d["option"].values()), 1.0, places=6)
            if d.get("rpo"):
                self.assertNotIn("RB", {r for r, _ in xp.PROGRESSIONS[c + "_THROW"]})   # le RB porte la feinte

    def test_parts_et_styles(self):
        for a in xp.FRANCHISES:
            for anc, tot in xp.parts_par_ancre(a).items():
                self.assertLessEqual(tot, xp.PART_MAX_ANCRE + 1e-9, (a, anc))
            self.assertEqual(set(xp.FORMATIONS_STYLE[a]), set(xp.FORMATIONS), a)
            for base, parts in xp.PAQUETS_STYLE[a].items():
                self.assertLess(sum(parts.values()), 1.0, (a, base))
                for p in parts:
                    b = xp.PAQUETS[p][0]
                    self.assertIn(base, b if isinstance(b, tuple) else (b,), (a, p))
            self.assertLess(sum(xp.RUSH_STYLE[a].values()), 1.0)
            for c in xp.PARTS[a]:
                self.assertNotIn(c, xp.EXCLUS_CONCEPTS[a], (a, c))      # pas de part pour un concept exclu

    def test_identites(self):
        # MNL : ses courses restent à ses RB (aucun QB / receveur / option / RPO)
        for pid, (f, c) in xp.PLAYS.items():
            d = xp.CONCEPTS.get(c, {})
            if d.get("porteur_course") or d.get("option") or d.get("rpo"):
                self.assertTrue(xp.exclu("MNL", pid), pid)
        self.assertTrue(xp.exclu("VEC", "WILDCAT_POWER"))
        self.assertFalse(xp.exclu("CTX", "WILDCAT_POWER"))

    def test_situations_connues(self):
        for s, m in xp.SITUATIONS.items():
            self.assertIn(s, {"short", "long", "red_zone", "goal_line", "backed_up", "first_down"})
            for k in m:
                if k.startswith("@"):
                    self.assertIn(k[1:], xp.FORMATIONS, (s, k))
                else:
                    self.assertIn(k, xp.CONCEPTS, (s, k))

    def test_resume(self):
        r = xp.resume()
        self.assertEqual(r["formations"], len(xp.FORMATIONS))
        self.assertGreater(r["plays"], 100)


class TestDessinDuSite(unittest.TestCase):
    """Chaque route dessinée par un nouveau concept existe dans la bibliothèque de formes du site (RT)."""

    def test_routes_du_site(self):
        import os
        import re
        page = os.path.join(os.path.dirname(__file__), "..", "..", "gamecenter_source.html")
        if not os.path.isfile(page):
            self.skipTest("gamecenter_source.html absent")
        h = open(page, encoding="utf-8").read()
        rt = set(re.findall(r"\b([A-Z_]+):\[\[0,0\]", h[h.index("const RT={"):h.index("const PASS_ASSIGN={")]))
        rt |= set(re.findall(r'"([A-Z_]+)":\[\[0,0\]', h[h.index("Object.assign(RT,"):h.index("const PASS_ASSIGN={")]))
        for c, (assign, cible) in xp.DESSIN_PASSE.items():
            for slot, route in assign.items():
                self.assertIn(route, rt, (c, slot))
            self.assertIn(cible, rt, c)
        for c, d in xp.CONCEPTS.items():
            if d["famille"] == "RUN":
                self.assertIn(d["dessin"], {"INSIDE_RUN", "OUTSIDE_RUN", "POWER", "COUNTER", "DRAW", "TRAP", "JET_SWEEP",
                                            "READ_OPTION"}, c)


class TestCompatibilite(unittest.TestCase):
    ROSTER = {"RB": 2, "TE": 1, "WR": 3}

    def test_niveaux(self):
        self.assertEqual(xp.compatibilite("11", self.ROSTER)[0], "PRIMARY")
        self.assertEqual(xp.compatibilite("21", self.ROSTER)[0], "PRIMARY")
        self.assertEqual(xp.compatibilite("12", self.ROSTER)[0], "SUPPORTED")       # un WR en 2e TE
        self.assertEqual(xp.compatibilite("22", self.ROSTER)[0], "SUPPORTED")
        self.assertEqual(xp.compatibilite("12", {"RB": 1, "TE": 0, "WR": 4})[0], "UNNATURAL")

    def test_invalide_avec_raison(self):
        niveau, raison = xp.compatibilite("10", self.ROSTER)
        self.assertEqual(niveau, "INVALID")
        self.assertIn("WR", raison)
        self.assertEqual(xp.compatibilite("10", {"RB": 1, "TE": 1, "WR": 4})[0], "PRIMARY")
        self.assertEqual(xp.compatibilite("99", self.ROSTER)[0], "INVALID")


class TestBrancher(Branche):
    def test_inscrit(self):
        self.assertIn("HITCH", progressions.ROUTES)
        self.assertIn("LEVELS", progressions.PROGRESSIONS)
        self.assertIn("Tampa 2", reaction_defensive.AVANTAGE)
        self.assertIn("HITCH", plan_de_jeu.QUICK)
        self.assertIn("DEEP_CROSS", plan_de_jeu.PROFONDS)
        lect = progressions.progression("Y_CROSS", "GUN_Y_OFF")
        self.assertEqual([l["role"] for l in lect], ["TE", "WR1", "WR2", "RB"])
        self.assertEqual(lect[-1]["niveau"], "checkdown")

    def test_idempotent_et_existant_intact(self):
        avant = (copy.deepcopy(progressions.PROGRESSIONS["CURL"]), dict(reaction_defensive.AVANTAGE["Cover 2"]))
        xp.brancher()
        xp.brancher()
        self.assertEqual(progressions.PROGRESSIONS["CURL"], avant[0])
        self.assertEqual(reaction_defensive.AVANTAGE["Cover 2"], avant[1])


class TestSansBrancher(unittest.TestCase):
    def test_modules_intacts_par_defaut(self):
        """Ces tables viennent des modules du bloc E : rien de l'extension tant que brancher() n'a pas été appelé."""
        self.assertNotIn("HITCH", progressions.ROUTES)
        self.assertNotIn("Tampa 2", reaction_defensive.AVANTAGE)
        self.assertNotIn("HITCH", plan_de_jeu.QUICK)


def _passe(appel, n, concept="CURL", defensif="COVER_3", qb=None):
    return moteur.decider_passe(concept, "SHOTGUN", defensif, RECEVEURS, DEFENSEURS, qb or qb_iq(), 0.5, 7, n,
                                appel=appel)


class TestPasse(Branche):
    N = 600

    def test_sans_appel_identique(self):
        for n in range(40):
            a = moteur.decider_passe("CURL", "SHOTGUN", "BLITZ", RECEVEURS, DEFENSEURS, qb_iq(), 0.5, 7, n)
            b = _passe(None, n, defensif="BLITZ")
            self.assertEqual(a[1].to_dict(), b[1].to_dict())
            self.assertEqual(a[2].to_dict(), b[2].to_dict())

    def test_deterministe(self):
        ap = xp.appel_passe("LEVELS", paquet="FIRE_ZONE", rush=None, motion="ACROSS")
        for n in range(30):
            self.assertEqual(_passe(ap, n, "LEVELS", "BLITZ")[2].to_dict(), _passe(ap, n, "LEVELS", "BLITZ")[2].to_dict())

    def test_pression_reelle_contre_presentee(self):
        sept = xp.appel_passe("CURL", paquet="SEVEN_MAN_PRESSURE")
        sim = xp.appel_passe("CURL", paquet="SIM_PRESSURE")
        t7 = statistics.mean(_passe(sept, n, defensif="BLITZ")[1].temps_pression for n in range(self.N))
        tb = statistics.mean(_passe(None, n, defensif="BLITZ")[1].temps_pression for n in range(self.N))
        ts = statistics.mean(_passe(sim, n, defensif="ZONE")[1].temps_pression for n in range(self.N))
        self.assertLess(t7, tb)                              # 7 rushers : la pression arrive plus vite
        self.assertGreater(ts, tb)                           # pression simulée : 4 rushers seulement
        e = _passe(sim, 1, defensif="ZONE")[1]
        self.assertEqual((e.rushers, e.paquet, e.presente), (4, "SIM_PRESSURE", "mug"))
        self.assertGreater(e.deguisement, 0)

    def test_presentation_trompe_le_qb(self):
        def erreurs(ap):
            d = [_passe(ap, n, defensif="ZONE")[2] for n in range(self.N)]
            return sum(x.erreur_lecture for x in d) / max(1, sum(1 for x in d if x.action == "LANCER"))
        self.assertGreater(erreurs(xp.appel_passe("CURL", paquet="SIM_PRESSURE")), erreurs(None))

    def test_motion_revele_l_homme(self):
        nu = xp.appel_passe("CURL", paquet="PRESS_MAN")
        mo = xp.appel_passe("CURL", paquet="PRESS_MAN", motion="ACROSS")
        self.assertLess(_passe(mo, 0, defensif="MAN")[1].deguisement, _passe(nu, 0, defensif="MAN")[1].deguisement)

    def test_protection_max(self):
        ap = xp.appel_passe("DOUBLE_POST")
        self.assertEqual(ap["protection"], "SEVEN_MAN_MAX")
        lect, etat, _ = _passe(ap, 3, "DOUBLE_POST")
        self.assertFalse({"RB", "TE"} & {l["role"] for l in lect})
        self.assertEqual(lect[-1]["niveau"], "checkdown")

    def test_blitz_qui_laisse_un_receveur(self):
        ap = xp.appel_passe("CURL", paquet="CORNER_BLITZ")
        base = [_passe(None, n, defensif="BLITZ")[1].receveurs["WR1"].separation for n in range(200)]
        cb = [_passe(ap, n, defensif="BLITZ")[1].receveurs["WR1"].separation for n in range(200)]
        self.assertGreater(statistics.mean(cb), statistics.mean(base))

    def test_nouvelles_coquilles(self):
        for p in ("TAMPA_2", "COVER_6", "MATCH_QUARTERS", "COVER_2_MAN", "FIRE_ZONE", "BANJO", "PALMS", "COVER_8"):
            base = xp.PAQUETS[p][0]
            base = base[0] if isinstance(base, tuple) else base
            e = _passe(xp.appel_passe("CURL", paquet=p), 2, defensif=base)[1]
            self.assertEqual(e.couverture, xp.PAQUETS[p][2][0][0])


class TestLectures(unittest.TestCase):
    N = 2000

    def test_rpo_selon_la_boite(self):
        qb = {"ratings": {"decision_making": 85}}
        part = lambda d: sum(xp.lecture_rpo("RPO_INSIDE_ZONE", d, qb, 11, n)[0] == "THROW" for n in range(self.N)) / self.N
        self.assertGreater(part("BOX_STACK"), part("COVER_4") + 0.3)
        self.assertEqual(xp.lecture_rpo("RPO_READ", "MAN", qb, 5, 9), xp.lecture_rpo("RPO_READ", "MAN", qb, 5, 9))

    def test_rpo_le_qb_se_trompe(self):
        bon = {"ratings": {"decision_making": 95}}
        mauvais = {"ratings": {"decision_making": 60}}
        err = lambda qb: sum(not xp.lecture_rpo("RPO_ALERT", "MAN", qb, 3, n)[1] for n in range(self.N)) / self.N
        self.assertLess(err(bon), err(mauvais))
        self.assertGreater(err(bon), 0)

    def test_option_le_bord_qui_ferme(self):
        qb = {"ratings": {"decision_making": 80}}
        garde = lambda d: sum(xp.lecture_option("INVERTED_VEER", d, qb, 4, n) == "QB" for n in range(self.N)) / self.N
        self.assertGreater(garde("BOX_STACK"), garde("COVER_4"))
        roles = {xp.lecture_option("TRIPLE_OPTION", "ZONE", qb, 4, n) for n in range(300)}
        self.assertEqual(roles, {"QB", "RB", "WR3"})


class TestDefense(unittest.TestCase):
    def test_paquets_parts(self):
        N = 4000
        cnt = {}
        for n in range(N):
            p = xp.choisir_paquet("AEG", "COVER_4", "SHOTGUN", 21, n)
            cnt[p] = cnt.get(p, 0) + 1
        for p, share in xp.PAQUETS_STYLE["AEG"]["COVER_4"].items():
            self.assertAlmostEqual(cnt.get(p, 0) / N, share, delta=0.03)
        self.assertEqual(xp.choisir_paquet("AEG", "COVER_4", "SHOTGUN", 21, 5),
                         xp.choisir_paquet("AEG", "COVER_4", "SHOTGUN", 21, 5))

    def test_banjo_seulement_contre_les_groupes(self):
        groupe = {xp.choisir_paquet("CTX", "MAN", "BUNCH", 3, n) for n in range(200)}
        large = {xp.choisir_paquet("CTX", "MAN", "SHOTGUN", 3, n) for n in range(200)}
        self.assertIn("BANJO", groupe)
        self.assertNotIn("BANJO", large)

    def test_fronts_de_situation(self):
        long_ = {xp.choisir_front("VEC", "NICKEL", ["long"], "SHOTGUN", 1, n) for n in range(300)}
        court = {xp.choisir_front("VEC", "NICKEL", ["short"], "SHOTGUN", 1, n) for n in range(300)}
        self.assertIn("NASCAR", long_)
        self.assertNotIn("NASCAR", court)
        vide = {xp.choisir_front("AEG", "DIME", [], "EMPTY", 1, n) for n in range(100)}
        self.assertIn("EMPTY_SPECIFIC", vide)
        self.assertNotIn("EMPTY_SPECIFIC", {xp.choisir_front("AEG", "DIME", [], "SHOTGUN", 1, n) for n in range(100)})
        self.assertIsNone(xp.choisir_front("AEG", "GOAL_LINE", ["short"], "JUMBO", 1, 0))

    def test_rush_jamais_sur_un_blitz(self):
        self.assertIsNone(xp.choisir_rush("VEC", "BLITZ", None, 1, 1))
        self.assertIsNone(xp.choisir_rush("VEC", "MAN", "SEVEN_MAN_PRESSURE", 1, 1))

    def test_mouvement_moyenne_nulle(self):
        ys = [xp.tirer_mouvement("VEC", 9, n)[1] for n in range(6000)]
        self.assertAlmostEqual(statistics.mean(ys), 0.0, delta=0.05)


class TestCourses(unittest.TestCase):
    def test_bear_ferme_l_interieur(self):
        self.assertLess(xp.effet_course("INSIDE_RUN", front="BEAR"), 0)
        self.assertGreater(xp.effet_course("JET_SWEEP", front="BEAR"), 0)
        self.assertGreater(xp.effet_course("OUTSIDE_RUN", motion="JET"), xp.effet_course("OUTSIDE_RUN"))
        self.assertEqual(xp.effet_course("INSIDE_RUN"), 0.0)

    def test_motion_et_shift(self):
        self.assertEqual(xp.choisir_motion("PISTOL_WING_JET_ACTION", 1, 2), "JET")
        self.assertEqual(xp.choisir_motion("GUN_Y_OFF_LEVELS", 1, 2), xp.choisir_motion("GUN_Y_OFF_LEVELS", 1, 2))
        self.assertIsNone(xp.choisir_motion("GUN_TIGHT_INSIDE_ZONE", 1, 2))
        shifts = [xp.choisir_shift("STRONG", 4, n) for n in range(2000)]
        self.assertAlmostEqual(shifts.count("I_FORM") / 2000, xp.P_SHIFT, delta=0.03)
        self.assertIsNone(xp.choisir_shift("GUN_TIGHT", 4, 1))

    def test_enchainement(self):
        m, rep = xp.enchainement("BOOT", ["INSIDE_RUN"], ["INSIDE_RUN", "PASS", "INSIDE_RUN"])
        self.assertGreater(m, 1.0)
        self.assertEqual(rep, "INSIDE_RUN")
        self.assertEqual(xp.enchainement("BOOT", ["CURL"], ["INSIDE_RUN"]), (1.0, None))
        self.assertEqual(xp.enchainement("CURL", [], []), (1.0, None))


if __name__ == "__main__":
    unittest.main()
