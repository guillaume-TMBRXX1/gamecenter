"""Tests du bloc B (intelligence du QB, poche et pression). Quelques secondes :

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)

Chaque comparaison porte sur une DISTRIBUTION (milliers de décisions dans la même situation), jamais sur un tirage.
"""
import random
import unittest

import moteur
from moteur import resolution
from moteur.decision_qb import (QBDecisionEngine, QBDecision, LANCER, THROWAWAY, SCRAMBLE, SACK, chrono_b,
                                p_erreur_lecture, percevoir)
from moteur.intelligence_qb import ATTRIBUTS, attributs_qb, PROFILS
from moteur.progressions import progression
from moteur.reaction_defensive import PostSnapState, EtatReceveur, LIBRE, SERRE, COUVERT, DOUBLE
from moteur.stats import stats_decisions
from moteur.tests.test_bloc_a import RECEVEURS, DEFENSEURS, joueur

MOYEN = {a: 75 for a in ATTRIBUTS}
MOYEN["aggressiveness"] = 50


def qb_iq(mobility=75, **over):
    iq = dict(MOYEN, **over)
    return {"id": "QB", "name": "QB", "ratings": {"decision_making": iq["decision_making"], "mobility": mobility},
            "iq": iq}


def etat_fixe(statuts, ttp=3.0, concept="DEEP_POST", famille="homme"):
    lect = progression(concept)
    rec = {}
    for l, st in zip(lect, statuts):
        sep = {LIBRE: 1.5, SERRE: 0.4, COUVERT: -0.8, DOUBLE: -1.5}[st]
        rec[l["role"]] = EtatReceveur(l["role"], l["role"], l["role"], l["route"], l["classe"], l["niveau"], "d", sep, st)
    return lect, PostSnapState("MAN", famille, "Cover 1" if famille == "homme" else "Cover 3", 4, False, "", ttp, rec)


def jouer(statuts, qb, n=4000, graine=1, **kw):
    lect, etat = etat_fixe(statuts, **kw)
    eng, rng = QBDecisionEngine(), random.Random(graine)
    return [eng.decide(etat, lect, qb, rng) for _ in range(n)]


def part(ds, cond):
    return sum(1 for d in ds if cond(d)) / len(ds)


class TestAttributs(unittest.TestCase):
    QB = joueur("CTX_QB1", throw_power=85, throw_accuracy=82, mobility=86, decision_making=94)

    def test_huit_attributs_bornes_et_deterministes(self):
        a, b = attributs_qb(self.QB, "CTX"), attributs_qb(self.QB, "CTX")
        self.assertEqual(a, b)
        self.assertEqual(set(a), set(ATTRIBUTS))
        self.assertTrue(all(30 <= v <= 99 for v in a.values()))
        self.assertEqual(a["decision_making"], 94)

    def test_identite_de_la_franchise(self):
        vec, aeg = attributs_qb(self.QB, "VEC"), attributs_qb(self.QB, "AEG")
        self.assertGreater(vec["aggressiveness"], aeg["aggressiveness"] + 30)
        self.assertGreater(aeg["pocket_awareness"], vec["pocket_awareness"])
        self.assertEqual(set(PROFILS), {"CTX", "VEC", "AEG", "MNL", "AXM", "GLT", "CPH", "NVA",
                                         "PLS", "ONX", "FRG", "MRD", "APX", "LTC", "ZPH", "BST",
                                         "GRZ", "MRG", "GMB", "PRM"})   # palier 4 : 20

    def test_note_presente_prise_telle_quelle(self):
        q = joueur("X", decision_making=80, processing=61)
        self.assertEqual(attributs_qb(q)["processing"], 61)

    def test_meilleures_notes_meilleure_lecture(self):
        bon = attributs_qb(joueur("A", decision_making=92, throw_accuracy=90))
        faible = attributs_qb(joueur("B", decision_making=68, throw_accuracy=70))
        for k in ("processing", "coverage_reading", "awareness", "anticipation"):
            self.assertGreater(bon[k], faible[k], k)


class TestProcessing(unittest.TestCase):
    def test_processing_90_contre_65_meme_situation(self):
        # primaire et secondaire couverts, la 3e lecture est libre : seul un QB rapide l'atteint avant la pression
        st = [COUVERT, COUVERT, LIBRE, LIBRE]
        vite = jouer(st, qb_iq(processing=90), ttp=3.2)
        lent = jouer(st, qb_iq(processing=65), ttp=3.2)
        lect = lambda ds: sum(d.lectures for d in ds) / len(ds)
        self.assertGreater(lect(vite), lect(lent) + 0.2)
        self.assertGreater(part(vite, lambda d: d.action == LANCER and d.lecture >= 3),
                           part(lent, lambda d: d.action == LANCER and d.lecture >= 3) + 0.10)
        fins = lambda d: d.action in (SACK, THROWAWAY, SCRAMBLE)
        self.assertLess(part(vite, fins), part(lent, fins))
        # le temps entre deux lectures suit le processing
        self.assertLess(chrono_b(qb_iq(processing=90))[1], chrono_b(qb_iq(processing=65))[1])

    def test_qb_elite_se_trompe_aussi(self):
        elite = qb_iq(**{a: 97 for a in ATTRIBUTS if a != "aggressiveness"})
        ds = jouer([SERRE, COUVERT, SERRE, LIBRE], elite, famille="zone")
        self.assertGreater(part(ds, lambda d: d.erreur_lecture), 0.0)
        self.assertGreater(part(ds, lambda d: d.action != LANCER or d.statut != LIBRE), 0.05)


class TestPression(unittest.TestCase):
    def test_pression_precoce(self):
        # la pression arrive avant même la deuxième lecture : progression coupée, fins d'action nombreuses
        st = [COUVERT, LIBRE, LIBRE, LIBRE]
        ds = jouer(st, qb_iq(), ttp=1.1)
        self.assertTrue(all(d.lectures <= 1 for d in ds))
        self.assertGreater(part(ds, lambda d: d.action in (SACK, THROWAWAY, SCRAMBLE)), 0.5)
        # un QB qui sent la pression (pocket awareness) gagne du temps et prend moins de sacks
        sent = jouer(st, qb_iq(pocket_awareness=95), ttp=1.1)
        sourd = jouer(st, qb_iq(pocket_awareness=55), ttp=1.1)
        self.assertLess(part(sent, lambda d: d.action == SACK), part(sourd, lambda d: d.action == SACK))
        self.assertGreater(sum(d.temps_poche for d in sent) / len(sent), sum(d.temps_poche for d in sourd) / len(sourd))

    def test_poche_qui_se_referme(self):
        # plus la poche se referme vite, moins le QB lit, plus il est pressé, plus il finit sans lancer
        st = [SERRE, COUVERT, SERRE, LIBRE]
        res = []
        for ttp in (3.6, 2.9, 2.2, 1.5):
            ds = jouer(st, qb_iq(), ttp=ttp)
            res.append((sum(d.lectures for d in ds) / len(ds), part(ds, lambda d: d.presse),
                        part(ds, lambda d: d.action in (SACK, THROWAWAY, SCRAMBLE))))
        for a, b in zip(res, res[1:]):
            self.assertGreaterEqual(a[0], b[0] - 0.02)          # lectures en baisse
            self.assertLessEqual(a[1], b[1] + 0.02)             # pressé plus souvent
            self.assertLessEqual(a[2], b[2] + 0.02)             # fins d'action en hausse
        self.assertGreater(res[-1][2], res[0][2] + 0.15)

    def test_pressure_response(self):
        # sous pression, la lecture se dégrade moins pour un QB qui garde son calme
        self.assertLess(p_erreur_lecture(qb_iq(pressure_response=92), "zone", True),
                        p_erreur_lecture(qb_iq(pressure_response=60), "zone", True))
        self.assertEqual(p_erreur_lecture(qb_iq(pressure_response=60), "homme", False),
                         p_erreur_lecture(qb_iq(pressure_response=92), "homme", False))
        calme = QBDecisionEngine._lancer_b(qb_iq(pressure_response=92), "WR1", progression("CURL")[0],
                                           EtatReceveur("WR1", "", "", "CURL", "moyen", "primaire", "", 0.4, SERRE),
                                           SERRE, 1, 1, True, 2.0, 2.2)
        nerveux = QBDecisionEngine._lancer_b(qb_iq(pressure_response=60), "WR1", progression("CURL")[0],
                                             EtatReceveur("WR1", "", "", "CURL", "moyen", "primaire", "", 0.4, SERRE),
                                             SERRE, 1, 1, True, 2.0, 2.2)
        self.assertLess(calme.mod_int, nerveux.mod_int)


class TestLectureEtStyle(unittest.TestCase):
    def test_coverage_reading(self):
        st = [SERRE, COUVERT, SERRE, LIBRE]
        bon = jouer(st, qb_iq(coverage_reading=95), famille="zone")
        faible = jouer(st, qb_iq(coverage_reading=62), famille="zone")
        err = lambda ds: part(ds, lambda d: d.erreur_lecture)
        self.assertLess(err(bon), err(faible))
        self.assertGreater(err(faible), 0.04)
        # la zone se lit moins bien que l'homme
        self.assertGreater(p_erreur_lecture(qb_iq(), "zone", False), p_erreur_lecture(qb_iq(), "homme", False))

    def test_erreur_optimiste_plus_d_interceptions(self):
        base = resolution.probabilites_base(0.03, 0.10, 0.35)
        q = qb_iq()
        lu = QBDecisionEngine._lancer_b(q, "WR1", progression("CURL")[0],
                                        EtatReceveur("WR1", "", "", "CURL", "moyen", "primaire", "", -0.8, COUVERT),
                                        COUVERT, 1, 1, False, 1.6, 3.0)
        mal_lu = QBDecisionEngine._lancer_b(q, "WR1", progression("CURL")[0],
                                            EtatReceveur("WR1", "", "", "CURL", "moyen", "primaire", "", -0.8, COUVERT),
                                            SERRE, 1, 1, False, 1.6, 3.0)
        self.assertTrue(mal_lu.erreur_lecture and mal_lu.forcee)
        self.assertGreater(resolution.probabilites_ajustees(base, mal_lu)["int"],
                           resolution.probabilites_ajustees(base, lu)["int"])

    def test_agressivite(self):
        st = [SERRE, COUVERT, COUVERT, COUVERT]
        fonceur = jouer(st, qb_iq(aggressiveness=85))
        prudent = jouer(st, qb_iq(aggressiveness=25))
        self.assertGreater(part(fonceur, lambda d: d.action == LANCER and d.lecture == 1),
                           part(prudent, lambda d: d.action == LANCER and d.lecture == 1) + 0.1)
        self.assertGreater(part(fonceur, lambda d: d.forcee), part(prudent, lambda d: d.forcee))

    def test_decision_making_moins_de_passes_forcees(self):
        st = [COUVERT, COUVERT, COUVERT, COUVERT]
        sage = jouer(st, qb_iq(decision_making=95), ttp=4.0)
        tete_brulee = jouer(st, qb_iq(decision_making=60), ttp=4.0)
        self.assertLess(part(sage, lambda d: d.forcee), part(tete_brulee, lambda d: d.forcee))

    def test_anticipation_lance_plus_tot(self):
        st = [LIBRE, LIBRE, LIBRE, LIBRE]
        tot = jouer(st, qb_iq(anticipation=95), n=1000)
        tard = jouer(st, qb_iq(anticipation=60), n=1000)
        t = lambda ds: sum(d.temps_lancer for d in ds if d.action == LANCER) / max(1, part(ds, lambda d: d.action == LANCER) * len(ds))
        self.assertLess(t(tot), t(tard) - 0.08)

    def test_percevoir_reste_dans_l_echelle(self):
        rng = random.Random(0)
        for st in (LIBRE, SERRE, COUVERT, DOUBLE):
            for _ in range(200):
                self.assertIn(percevoir(st, 1.0, rng), (LIBRE, SERRE, COUVERT, DOUBLE))


class TestProgressionsB(unittest.TestCase):
    def test_slot_lu_au_bloc_b_seulement(self):
        from moteur.progressions import PROGRESSIONS_B
        for c in ("CURL", "FOUR_VERTS", "DAGGER"):
            self.assertIn("WR3", [l["role"] for l in progression(c, bloc="B")], c)
            self.assertNotIn("WR3", [l["role"] for l in progression(c)], c)
        for c in PROGRESSIONS_B:
            lect = progression(c, bloc="B")
            self.assertEqual(len({l["role"] for l in lect}), 4, c)
            self.assertEqual(lect[-1]["niveau"], "checkdown", c)


class TestCompatibiliteEtDeterminisme(unittest.TestCase):
    QB_A = {"id": "QB1", "name": "QB1", "ratings": {"decision_making": 80, "mobility": 70}}

    def test_sans_attributs_bloc_a(self):
        lect, etat = etat_fixe([SERRE, COUVERT, SERRE, LIBRE])
        d = QBDecisionEngine().decide(etat, lect, self.QB_A, random.Random(4))
        self.assertEqual((d.bloc, d.mod_int, d.mod_inc, d.percu), ("A", 1.0, 1.0, ""))

    def test_meme_graine_meme_decision_bloc_b(self):
        qb = dict(self.QB_A, iq=attributs_qb(self.QB_A, "CTX"))
        a = moteur.decider_passe("DEEP_POST", "SHOTGUN", "COVER_3", RECEVEURS, DEFENSEURS, qb, 0.6, 2024, 88)
        b = moteur.decider_passe("DEEP_POST", "SHOTGUN", "COVER_3", RECEVEURS, DEFENSEURS, qb, 0.6, 2024, 88)
        self.assertEqual(a[2].to_dict(), b[2].to_dict())
        self.assertEqual(a[2].bloc, "B")

    def test_probabilites_valides_bloc_b(self):
        base = resolution.probabilites_base(0.03, 0.10, 0.35)
        for d in jouer([SERRE, COUVERT, SERRE, LIBRE], qb_iq(aggressiveness=90, pressure_response=40), n=500, ttp=1.8):
            p = resolution.probabilites_ajustees(base, d, resolution.CALIBRATION_B)
            self.assertTrue(all(v >= 0 for v in p.values()))
            self.assertAlmostEqual(sum(p.values()), 1.0)


class TestStatsB(unittest.TestCase):
    def test_par_qb_et_decisions_fautives(self):
        q = {"id": "X_QB1", "name": "X"}
        log = [
            {"play_type": "PASS", "outcome": "INTERCEPTION", "yards_gained": 0,
             "decision": {"action": "LANCER", "target": {"role": "WR1", "id": "W"}, "read": 1, "status": "COUVERT",
                          "misread": True, "forced": True, "hurried": False, "throw_time": 1.9, "qb": q, "pocket_time": 2.8}},
            {"play_type": "PASS", "outcome": "SACK", "yards_gained": -7,
             "decision": {"action": "SACK", "read": 0, "qb": q, "pocket_time": 2.1}},
            {"play_type": "PASS", "outcome": "PASS_COMPLETE", "yards_gained": 9,
             "decision": {"action": "LANCER", "target": {"role": "TE", "id": "T"}, "read": 3, "status": "LIBRE",
                          "hurried": True, "throw_time": 2.6, "qb": q, "pocket_time": 2.9}},
        ]
        s = stats_decisions([log])
        self.assertEqual(s["erreurs_lecture"], 1)
        self.assertEqual(s["part_int_decision"], 1.0)
        self.assertEqual(s["part_sacks_decision"], 1.0)
        self.assertEqual(s["par_qb"]["X_QB1"]["dropbacks"], 3)
        self.assertEqual(s["par_qb"]["X_QB1"]["presses"], 1)
        self.assertAlmostEqual(s["temps_poche_moyen"], (2.8 + 2.1 + 2.9) / 3)


if __name__ == "__main__":
    unittest.main()
