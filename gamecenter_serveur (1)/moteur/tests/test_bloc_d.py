"""Tests du bloc D (adaptation en match et plan de jeu). Quelques secondes :

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)

Détection de tendance · ajustement offensif · ajustement défensif · contre-ajustement · plan de jeu par adversaire ·
effets sur la passe (en distribution) · déterminisme · sans plan = bloc C à l'identique.
"""
import random
import statistics
import unittest

import moteur
from moteur import plan_de_jeu as pj
from moteur.plan_de_jeu import (AdaptiveGameplanEngine, MemoireTendances, EtatAdaptation, PROFILS, plan_de_jeu,
                                plan_passe, appliquer_progression, multiplicateur_concept)
from moteur.progressions import progression
from moteur.reaction_defensive import DefensiveReactionEngine, DOUBLE
from moteur.decision_qb import LANCER
from moteur.tests.test_bloc_a import RECEVEURS, DEFENSEURS, joueur
from moteur.tests.test_bloc_b import qb_iq
from moteur.tests.test_bloc_c import attaque, defense

MOTEUR = AdaptiveGameplanEngine()


def passe(cible="", down=1, blitz=False, double="", reussite=True, yards=8, concept="CURL", sack=False, presse=False):
    return {"type": "PASS", "down": down, "concept": concept, "blitz": blitz, "cible": cible, "double": double,
            "reussite": reussite, "yards": yards, "sack": sack, "presse": presse, "complete": reussite and not sack}


def etat(abbr="CTX"):
    return EtatAdaptation(PROFILS[abbr])


class TestMemoire(unittest.TestCase):
    """Détection de tendance : ce que la mémoire retient."""

    def test_cibles_sur_la_fenetre(self):
        m = MemoireTendances(fenetre=8)
        for r in ["WR2"] * 5 + ["WR1"] * 6 + ["TE"] * 2:
            m.observer(passe(r))
        c = m.cibles()
        self.assertEqual(c["WR1"][0], 6)          # les 8 dernières : 6 WR1 + 2 TE
        self.assertEqual(c["TE"][0], 2)
        self.assertNotIn("WR2", c)
        self.assertEqual(sum(v[0] for v in m.cibles(depuis=5).values()), 8)

    def test_blitz_sur_troisieme_essai(self):
        m = MemoireTendances()
        for k in range(4):
            m.observer(passe("WR1", down=3, blitz=k != 1))
            m.observer(passe("WR1", down=1, blitz=False))
        self.assertEqual(m.blitz_troisiemes(), (3, 4))
        self.assertEqual(m.blitz_recents(), (3, 8))

    def test_courses_ignorees_et_doubles(self):
        m = MemoireTendances()
        m.observer({"type": "RUN", "down": 1})
        m.observer(passe("WR2", double="WR1"))
        m.observer(passe("TE", double="WR1"))
        self.assertEqual(m.n, 3)
        self.assertEqual(m.doubles(), {"WR1": 2})


class TestAjustementOffensif(unittest.TestCase):
    def test_blitz_repetes_quick_game(self):
        m, e = MemoireTendances(), etat("CTX")
        m.observer(passe("WR1", down=3, blitz=True))
        self.assertEqual(MOTEUR.attaque(m, e), [])          # un seul blitz : rien
        m.observer(passe("WR1", down=3, blitz=True))
        ev = MOTEUR.attaque(m, e)
        self.assertEqual([x["kind"] for x in ev], ["o_quick"])
        self.assertIn("third downs", ev[0]["reason"])
        self.assertIn("o_quick", e.actifs)
        # le jeu rapide pèse plus, surtout sur 3e essai ; les passes profondes moins
        self.assertGreater(multiplicateur_concept({}, e, "QUICK_SLANT", 3), multiplicateur_concept({}, e, "QUICK_SLANT", 1))
        self.assertGreater(multiplicateur_concept({}, e, "QUICK_SLANT", 1), 1.0)
        self.assertGreater(multiplicateur_concept({}, e, "DRAW", 3), 1.0)
        self.assertLess(multiplicateur_concept({}, e, "FOUR_VERTS", 3), 1.0)
        self.assertEqual(multiplicateur_concept({}, e, "CROSS", 3), 1.0)

    def test_identite_aeg_plus_lente_que_ctx(self):
        for abbr, attendu in (("CTX", True), ("AEG", False)):
            m, e = MemoireTendances(), etat(abbr)
            for _ in range(2):
                m.observer(passe("WR1", down=3, blitz=True))
            self.assertEqual("o_quick" in e.actifs or bool(MOTEUR.attaque(m, e)), attendu, abbr)

    def test_protection_apres_pression_sur_blitz(self):
        m, e = MemoireTendances(), etat("CTX")
        m.observer(passe("", blitz=True, sack=True, reussite=False))
        m.observer(passe("WR1", blitz=True, presse=True))
        self.assertNotIn("o_protect", [x["kind"] for x in MOTEUR.attaque(m, e)])      # deux : pas encore
        m.observer(passe("TE", blitz=True, presse=True))
        kinds = [x["kind"] for x in MOTEUR.attaque(m, e)]
        self.assertIn("o_protect", kinds)
        self.assertTrue(plan_passe({}, e, {}, None).get("protection"))

    def test_vec_ne_protege_pas(self):
        m, e = MemoireTendances(), etat("VEC")
        for _ in range(4):
            m.observer(passe("", blitz=True, sack=True, reussite=False))
        self.assertNotIn("o_protect", [x["kind"] for x in MOTEUR.attaque(m, e)])

    def test_bascule_hors_du_double(self):
        m, e = MemoireTendances(), etat("CTX")
        m.observer(passe("WR1", double="WR1", reussite=False))
        m.observer(passe("WR1", double="WR1", reussite=False))
        self.assertEqual(MOTEUR.attaque(m, e), [])             # deux doubles : pas encore une tendance
        m.observer(passe("WR2", double="WR1"))
        ev = MOTEUR.attaque(m, e, noms={"WR1": "Rafe Ellison"})
        self.assertEqual(ev[0]["kind"], "o_away")
        self.assertEqual(ev[0]["label"], "Rafe Ellison")
        self.assertEqual(ev[0]["text"], "Works away from the double on Rafe Ellison")
        self.assertEqual(plan_passe({}, e, {}, None)["evite"], "WR1")

    def test_ajustement_expire(self):
        m, e = MemoireTendances(), etat("VEC")
        for _ in range(3):
            m.observer(passe("WR1", down=3, blitz=True))
        MOTEUR.attaque(m, e)
        self.assertIn("o_quick", e.actifs)
        m2 = MemoireTendances()                          # plus de blitz vu
        for _ in range(PROFILS["VEC"]["tenue"]):
            MOTEUR.attaque(m2, e)
        self.assertNotIn("o_quick", e.actifs)


class TestAjustementDefensif(unittest.TestCase):
    def test_wr1_trop_cible_bracket(self):
        m, e = MemoireTendances(), etat("CTX")
        for r in ["WR1", "WR2", "WR1", "TE", "WR1"]:
            m.observer(passe(r))
        ev = MOTEUR.defense(m, e, noms={"WR1": "Nico Saint-Clair"})
        self.assertEqual([x["kind"] for x in ev], ["d_bracket"])
        self.assertEqual(ev[0]["text"], "Brackets Nico Saint-Clair")
        self.assertEqual(ev[0]["reason"], "3 of the last 5 targets")
        self.assertEqual(e.bracket, "WR1")
        p = plan_passe({}, None, {}, e)
        self.assertEqual((p["bracket"], p["p_bracket"]), ("WR1", PROFILS["CTX"]["bracket"]))

    def test_cible_frequente_mais_inefficace_pas_de_bracket(self):
        m, e = MemoireTendances(), etat("CTX")
        for r in ["WR1", "WR2", "WR1", "TE", "WR1", "WR1"]:
            m.observer(passe(r, reussite=r != "WR1", yards=4))
        self.assertEqual(MOTEUR.defense(m, e), [])

    def test_le_rb_n_est_pas_bracke(self):
        m, e = MemoireTendances(), etat("CTX")
        for _ in range(6):
            m.observer(passe("RB"))
        self.assertEqual(MOTEUR.defense(m, e), [])

    def test_bracket_plus_de_doubles_sur_la_cible(self):
        lect = progression("CURL")
        eng = DefensiveReactionEngine()

        def taux(**kw):
            n = 0
            for k in range(3000):
                st = eng.react("COVER_2", lect, RECEVEURS, DEFENSEURS, 0.5, random.Random(f"b|{k}"), **kw)
                n += st.double_sur == "WR2"
            return n / 3000

        sans, avec = taux(), taux(bracket="WR2", p_bracket=0.5)
        self.assertLess(sans, 0.02)                     # WR2 n'est jamais la meilleure menace
        self.assertGreater(avec, 0.4)
        self.assertGreater(taux(bracket="WR2", p_bracket_bonus=0.08), 0.1)

    def test_pas_de_bracket_en_cover_0(self):
        lect, eng = progression("CURL"), DefensiveReactionEngine()
        for k in range(300):
            st = eng.react("BLITZ", lect, RECEVEURS, DEFENSEURS, 0.5, random.Random(f"z|{k}"), bracket="WR1", p_bracket=0.7)
            if st.couverture == "Cover 0":
                self.assertEqual(st.double_sur, "")

    def test_deguise_quand_le_jeu_rapide_punit_le_blitz(self):
        m, e = MemoireTendances(), etat("CTX")
        m.observer(passe("WR1", blitz=True, concept="QUICK_SLANT"))
        m.observer(passe("TE", blitz=True, concept="STICK"))
        self.assertIn("d_disguise", [x["kind"] for x in MOTEUR.defense(m, e)])
        self.assertTrue(plan_passe({}, None, {}, e).get("deguise"))


class TestContreAjustement(unittest.TestCase):
    def test_l_attaque_bascule_puis_le_bracket_suit(self):
        """WR1 brackété -> l'attaque lit ailleurs (TE) -> la défense fait tourner le bracket sur le TE ; l'attaque,
        qui voit le double partir, ne l'évite plus et peut revenir au WR1."""
        noms = {"WR1": "W. One", "TE": "T. End"}
        md, ed = MemoireTendances(), etat("CTX")
        for r in ["WR1", "WR1", "WR2", "WR1", "WR1"]:
            md.observer(passe(r))
        self.assertEqual(MOTEUR.defense(md, ed, noms)[0]["kind"], "d_bracket")
        # attaque : le double sur WR1 -> o_away, la progression évite WR1
        ma, ea = MemoireTendances(), etat("CTX")
        for _ in range(PROFILS["CTX"]["doubles"]):
            ma.observer(passe("TE", double="WR1"))
        self.assertEqual(MOTEUR.attaque(ma, ea, noms)[0]["kind"], "o_away")
        lect, notes = appliquer_progression(progression("CURL"), plan_passe({}, ea, {}, ed), random.Random(1))
        self.assertNotEqual(lect[0]["role"], "WR1")
        self.assertEqual(notes["away"], "WR1")
        # la défense voit les cibles partir vers le TE -> rotation
        for r in ["TE", "TE", "WR2"]:
            md.observer(passe(r))
        ev = MOTEUR.defense(md, ed, noms)
        self.assertEqual([x["kind"] for x in ev], ["d_rotate"])
        self.assertEqual(ev[0]["text"], "Rotates the bracket to T. End")
        self.assertEqual(ed.bracket, "TE")
        # l'attaque ne voit plus de double sur WR1 : l'évitement expire
        for _ in range(8):
            ma.observer(passe("WR1", double="TE"))
        for _ in range(PROFILS["CTX"]["tenue"]):
            MOTEUR.attaque(ma, ea, noms)
        self.assertNotEqual(ea.evite, "WR1")

    def test_affichage_limite(self):
        e = etat("CTX")
        self.assertTrue(e.montrer("d_rotate") and e.montrer("d_rotate"))
        self.assertFalse(e.montrer("d_rotate"))
        self.assertTrue(e.montrer("o_quick"))
        self.assertFalse(e.montrer("o_quick"))


def equipe_att(abbr, rec):
    return {"abbr": abbr, "receveurs": rec, "units": {"pass_off": 82, "run_off": 82}}


def equipe_def(abbr, defs, blitz=0.15, couv=None, **units):
    u = {"pass_def": 82, "run_def": 82}
    u.update(units)
    return {"abbr": abbr, "defenseurs": defs, "units": u, "blitz_rate": blitz,
            "couvertures": couv or {"MAN": 1.0, "ZONE": 1.0, "COVER_2": 1.0, "COVER_4": 1.0}}


class TestPlanDeJeu(unittest.TestCase):
    def test_blitz_frequent_plus_de_jeu_rapide(self):
        calme = plan_de_jeu(equipe_att("A", RECEVEURS), equipe_def("D", DEFENSEURS, blitz=0.06))
        chaud = plan_de_jeu(equipe_att("A", RECEVEURS), equipe_def("D", DEFENSEURS, blitz=0.33))
        self.assertEqual(calme["concepts"]["SCREEN"], 1.0)
        self.assertGreater(chaud["concepts"]["SCREEN"], 1.2)
        self.assertIn("quick game vs the blitz", chaud["resume_attaque"])

    def test_homme_ou_zone(self):
        homme = plan_de_jeu(equipe_att("A", RECEVEURS), equipe_def("D", DEFENSEURS, couv={"MAN": 2.2, "ZONE": 0.5}))
        zone = plan_de_jeu(equipe_att("A", RECEVEURS), equipe_def("D", DEFENSEURS, couv={"COVER_2": 2.0, "COVER_4": 2.5}))
        self.assertGreater(homme["concepts"]["MESH"], 1.0)
        self.assertLess(homme["concepts"]["CURL"], 1.0)
        self.assertGreater(zone["concepts"]["CURL"], 1.0)
        self.assertLess(zone["concepts"]["MESH"], 1.0)

    def test_cible_favorite_le_meilleur_mismatch(self):
        defs = dict(DEFENSEURS, CB=[joueur("CB1", speed=95, coverage=95), joueur("CB2", speed=60, coverage=55)])
        p = plan_de_jeu(equipe_att("A", RECEVEURS), equipe_def("D", defs))
        self.assertEqual(p["favori"], "WR2")             # WR2 face au CB le plus faible
        self.assertGreater(p["favori_ecart"], 3)
        self.assertEqual(p["menace"], "WR1")             # la défense, elle, craint le meilleur receveur

    def test_course_ou_passe_selon_les_unites(self):
        a = equipe_att("A", RECEVEURS)
        a["units"] = {"pass_off": 80, "run_off": 92}
        bonne_couverture = equipe_def("D", DEFENSEURS, pass_def=86, run_def=80)
        self.assertLess(plan_de_jeu(a, bonne_couverture)["pass_shift"], 0)
        self.assertIn("lean on the run", plan_de_jeu(a, bonne_couverture)["resume_attaque"])
        a["units"] = {"pass_off": 90, "run_off": 76}
        self.assertGreater(plan_de_jeu(a, equipe_def("D", DEFENSEURS, pass_def=78, run_def=88))["pass_shift"], 0)

    def test_fond_du_terrain(self):
        lents = dict(DEFENSEURS, S=[joueur("S1", speed=70, coverage=65), joueur("S2", speed=70, coverage=65)])
        rapides = dict(DEFENSEURS, S=[joueur("S1", speed=95, coverage=95), joueur("S2", speed=95, coverage=95)])
        att = equipe_att("A", RECEVEURS)
        self.assertGreater(plan_de_jeu(att, equipe_def("D", lents))["concepts"]["FOUR_VERTS"], 1.1)
        self.assertLess(plan_de_jeu(att, equipe_def("D", rapides))["concepts"]["FOUR_VERTS"], 0.95)

    def test_plan_deterministe(self):
        a, d = equipe_att("A", RECEVEURS), equipe_def("D", DEFENSEURS, blitz=0.3)
        self.assertEqual(plan_de_jeu(a, d), plan_de_jeu(a, d))


class TestProgression(unittest.TestCase):
    def test_protection_retire_le_rb_et_allonge_la_poche(self):
        lect, notes = appliquer_progression(progression("CURL"), {"protection": True}, random.Random(1))
        self.assertNotIn("RB", [l["role"] for l in lect])
        self.assertEqual(lect[-1]["niveau"], "checkdown")
        self.assertTrue(notes["protection"])
        eng = DefensiveReactionEngine()
        t = lambda **kw: statistics.mean(eng.react("BLITZ", lect, RECEVEURS, DEFENSEURS, 0.5, random.Random(f"p{k}"),
                                                   **kw).temps_pression for k in range(500))
        self.assertGreater(t(bonus_poche=pj.PROTECTION["poche"], bonus_rusher5=pj.PROTECTION["rusher5"]) - t(), 0.25)

    def test_screen_garde_son_rb(self):
        lect, notes = appliquer_progression(progression("SCREEN"), {"protection": True}, random.Random(1))
        self.assertEqual(lect[0]["role"], "RB")
        self.assertEqual(notes, {})

    def test_cible_favorite_lue_en_premier_une_fois_sur_trois(self):
        n = sum(appliquer_progression(progression("CURL"), {"favori": "TE", "p_favori": 0.33},
                                      random.Random(f"f{k}"))[0][0]["role"] == "TE" for k in range(3000))
        self.assertAlmostEqual(n / 3000, 0.33, delta=0.03)

    def test_sans_plan_rien_ne_change(self):
        L = progression("DEEP_POST")
        self.assertEqual(appliquer_progression(L, {}, random.Random(1)), (L, {}))
        self.assertEqual(appliquer_progression(L, None, random.Random(1)), (L, {}))


class TestChaine(unittest.TestCase):
    def args(self, n, concept="CURL", defense_concept="COVER_2"):
        return (concept, "SHOTGUN", defense_concept, attaque(), defense(), qb_iq(), 0.5, 4242, n)

    def test_sans_plan_bloc_c_a_l_identique(self):
        for n in range(150):
            a = moteur.decider_passe(*self.args(n))
            b = moteur.decider_passe(*self.args(n), plan=None)
            c = moteur.decider_passe(*self.args(n), plan={})
            self.assertEqual(a[2], b[2])
            self.assertEqual(a[2], c[2])
            self.assertIsNone(a[2].plan)
            self.assertEqual(a[1].to_dict(), b[1].to_dict())

    def test_plan_deterministe_et_note(self):
        plan = {"bracket": "WR1", "p_bracket": 0.5, "protection": True, "favori": "TE", "p_favori": 0.33}
        for n in range(150):
            a = moteur.decider_passe(*self.args(n), plan=plan)
            b = moteur.decider_passe(*self.args(n), plan=plan)
            self.assertEqual(a[2], b[2])
            self.assertEqual(a[1].to_dict(), b[1].to_dict())
            self.assertTrue(a[2].plan["protection"])
            self.assertEqual(a[2].plan["bracket"], "WR1")
            self.assertEqual(a[2].plan["bracketed"], a[1].double_sur == "WR1")
            self.assertNotIn("RB", a[1].receveurs)

    def test_le_bracket_detourne_les_lancers(self):
        """En distribution : brackéter WR1 réduit sa part des cibles (l'attaque lit ailleurs)."""
        def part_wr1(plan):
            ds = [moteur.decider_passe(*self.args(n), plan=plan)[2] for n in range(2500)]
            l = [d for d in ds if d.action == LANCER]
            return sum(d.cible == "WR1" for d in l) / len(l)
        self.assertLess(part_wr1({"bracket": "WR1", "p_bracket": 0.6}), part_wr1(None) - 0.05)

    def test_le_bracket_coute_cher_au_receveur_double(self):
        ds = [moteur.decider_passe(*self.args(n), plan={"bracket": "WR1", "p_bracket": 0.6}) for n in range(2500)]
        dbl = [d for _, e, d in ds if d.action == LANCER and d.cible == "WR1" and e.double_sur == "WR1"]
        libre = [d for _, e, d in ds if d.action == LANCER and d.cible == "WR1" and not e.double_sur]
        self.assertTrue(dbl and libre)
        self.assertGreater(sum(d.statut == DOUBLE for d in dbl) / len(dbl), 0.5)

    def test_flux_du_plan_separe(self):
        plan = {"favori": "WR2", "p_favori": 0.33}         # progression CURL du bloc B : WR1, WR2, WR3, RB
        a = [moteur.decider_passe(*self.args(n), plan=plan)[2] for n in range(60)]
        random.seed(5)
        random.random()
        b = [moteur.decider_passe(*self.args(n), plan=plan)[2] for n in range(60)]
        self.assertEqual(a, b)
        self.assertTrue(any((d.plan or {}).get("focus") == "WR2" for d in a))


if __name__ == "__main__":
    unittest.main()
