"""Tests du bloc A (état post-snap, progression du QB, cible réelle). Quelques secondes :

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import random
import unittest

import moteur
from moteur import resolution
from moteur.decision_qb import QBDecisionEngine, LANCER, THROWAWAY, SCRAMBLE, SACK
from moteur.progressions import progression, PROGRESSIONS, ROUTES
from moteur.reaction_defensive import (DefensiveReactionEngine, PostSnapState, EtatReceveur,
                                       LIBRE, SERRE, COUVERT, DOUBLE)
from moteur.stats import stats_decisions


def joueur(pid, **ratings):
    return {"id": pid, "name": pid, "ratings": ratings}


QB = joueur("QB1", decision_making=80, mobility=70, throw_accuracy=80)
QB_MOBILE = joueur("QB2", decision_making=80, mobility=95)
RECEVEURS = {
    "WR1": joueur("WR1", speed=88, acceleration=88, route_running=90, catching=85),
    "WR2": joueur("WR2", speed=80, acceleration=80, route_running=80, catching=78),
    "WR3": joueur("WR3", speed=76, acceleration=77, route_running=76, catching=75),
    "TE": joueur("TE1", speed=76, route_running=78, catching=78),
    "RB": joueur("RB1", speed=84, acceleration=84),
}
DEFENSEURS = {
    "CB": [joueur("CB1", speed=84, coverage=82), joueur("CB2", speed=82, coverage=78)],
    "S": [joueur("S1", speed=82, coverage=80), joueur("S2", speed=80, coverage=76)],
    "LB": [joueur("LB1", speed=78, coverage=74), joueur("LB2", speed=76, coverage=72), joueur("LB3", speed=75, coverage=70)],
}


def etat_fixe(statuts, ttp=3.5, concept="QUICK_SLANT"):
    """PostSnapState construit à la main : statuts dans l'ordre de la progression du concept."""
    lect = progression(concept)
    rec = {}
    for l, st in zip(lect, statuts):
        sep = {LIBRE: 1.5, SERRE: 0.4, COUVERT: -0.8, DOUBLE: -1.5}[st]
        rec[l["role"]] = EtatReceveur(l["role"], l["role"], l["role"], l["route"], l["classe"], l["niveau"],
                                      "d", sep, st)
    return lect, PostSnapState("MAN", "homme", "Cover 1", 4, False, "", ttp, rec)


def distribution(statuts, n=3000, ttp=3.5, qb=QB, concept="QUICK_SLANT"):
    lect, etat = etat_fixe(statuts, ttp, concept)
    eng, rng, out = QBDecisionEngine(), random.Random(1), {}
    for _ in range(n):
        d = eng.decide(etat, lect, qb, rng)
        k = (d.action, d.cible)
        out[k] = out.get(k, 0) + 1
    return {k: v / n for k, v in out.items()}


class TestProgressions(unittest.TestCase):
    def test_chaque_concept_a_quatre_lectures_et_un_checkdown(self):
        for c in PROGRESSIONS:
            lect = progression(c)
            self.assertEqual(len(lect), 4, c)
            self.assertEqual(lect[-1]["niveau"], "checkdown", c)
            self.assertEqual(len({l["role"] for l in lect}), 4, c)
            self.assertTrue(all(l["route"] in ROUTES for l in lect), c)

    def test_heavy_wr1_ineligible(self):
        roles = [l["role"] for l in progression("BOOT", "HEAVY")]
        self.assertNotIn("WR1", roles)
        self.assertEqual(len(roles), 4)

    def test_role_absent_remplace(self):
        roles = [l["role"] for l in progression("QUICK_SLANT", None, ("WR1", "WR2", "RB"))]
        self.assertEqual(roles[0], "WR1")
        self.assertIn("RB", roles)
        self.assertNotIn("TE", roles)


class TestQB(unittest.TestCase):
    def test_primaire_libre(self):
        d = distribution([LIBRE, COUVERT, COUVERT, COUVERT])
        self.assertGreater(d.get((LANCER, "WR1"), 0), 0.88)

    def test_primaire_couvert_secondaire_libre(self):
        d = distribution([COUVERT, LIBRE, COUVERT, COUVERT])
        self.assertGreater(d.get((LANCER, "WR2"), 0), 0.80)
        self.assertLess(d.get((LANCER, "WR1"), 0), 0.08)

    def test_tout_couvert_checkdown_libre(self):
        d = distribution([COUVERT, COUVERT, COUVERT, LIBRE])
        self.assertGreater(d.get((LANCER, "RB"), 0), 0.75)

    def test_tout_couvert_sans_solution(self):
        d = distribution([COUVERT, COUVERT, COUVERT, COUVERT], ttp=2.6)
        fins = sum(v for (a, _), v in d.items() if a in (THROWAWAY, SACK, SCRAMBLE))
        self.assertGreater(fins, 0.6)
        self.assertGreater(sum(v for (a, _), v in d.items() if a == THROWAWAY), 0.15)
        self.assertGreater(sum(v for (a, _), v in d.items() if a == SACK), 0.15)

    def test_double_couverture_sur_le_primaire(self):
        d = distribution([DOUBLE, LIBRE, SERRE, LIBRE])
        self.assertLess(d.get((LANCER, "WR1"), 0), 0.05)
        self.assertGreater(d.get((LANCER, "WR2"), 0), 0.8)

    def test_qb_mobile_scramble_plus(self):
        lent = distribution([COUVERT] * 4, ttp=2.0)
        mobile = distribution([COUVERT] * 4, ttp=2.0, qb=QB_MOBILE)
        scr = lambda d: sum(v for (a, _), v in d.items() if a == SCRAMBLE)
        self.assertGreater(scr(mobile), scr(lent) + 0.1)

    def test_pression_precoce_coupe_la_progression(self):
        lect, etat = etat_fixe([COUVERT, LIBRE, LIBRE, LIBRE], ttp=1.3, concept="DEEP_POST")
        rng, eng = random.Random(3), QBDecisionEngine()
        for _ in range(200):
            d = eng.decide(etat, lect, QB, rng)
            self.assertLessEqual(d.lectures, 1)
            self.assertTrue(d.sous_pression or d.action != LANCER)


class TestReaction(unittest.TestCase):
    def _statuts(self, concept_def, concept="DEEP_POST", n=2000, pression=0.5):
        eng, rng, out = DefensiveReactionEngine(), random.Random(5), {}
        lect = progression(concept)
        for _ in range(n):
            e = eng.react(concept_def, lect, RECEVEURS, DEFENSEURS, pression, rng)
            for r, x in e.receveurs.items():
                out.setdefault(r, {}).setdefault(x.statut, 0)
                out[r][x.statut] += 1
        return out, n

    def test_blitz_moins_de_temps_et_plus_de_rushers(self):
        eng, lect = DefensiveReactionEngine(), progression("QUICK_SLANT")
        t_blitz = [eng.react("BLITZ", lect, RECEVEURS, DEFENSEURS, 0.7, random.Random(i)).temps_pression for i in range(400)]
        t_base = [eng.react("COVER_3", lect, RECEVEURS, DEFENSEURS, 0.5, random.Random(i)).temps_pression for i in range(400)]
        self.assertLess(sum(t_blitz) / 400, sum(t_base) / 400 - 0.5)
        e = eng.react("BLITZ", lect, RECEVEURS, DEFENSEURS, 0.7, random.Random(0))
        self.assertGreaterEqual(e.rushers, 5)
        self.assertTrue(e.blitz)

    def test_cover2_double_wr1_parfois(self):
        out, n = self._statuts("COVER_2")
        self.assertGreater(out["WR1"].get(DOUBLE, 0) / n, 0.1)
        out3, _ = self._statuts("COVER_3")
        self.assertLess(out3["WR1"].get(DOUBLE, 0), out["WR1"].get(DOUBLE, 0))

    def test_cover4_ferme_le_fond_ouvre_le_court(self):
        out, n = self._statuts("COVER_4", concept="FOUR_VERTS")
        libre_fond = out["WR2"].get(LIBRE, 0) / n            # GO
        libre_court = out["RB"].get(LIBRE, 0) / n            # FLAT (checkdown)
        self.assertGreater(libre_court, libre_fond + 0.2)

    def test_meilleur_receveur_plus_souvent_libre_en_homme(self):
        out, n = self._statuts("MAN", concept="FOUR_VERTS")
        self.assertGreater(out["WR1"].get(LIBRE, 0), out["WR2"].get(LIBRE, 0))


class TestDeterminisme(unittest.TestCase):
    def test_meme_graine_meme_decision(self):
        a = moteur.decider_passe("DEEP_POST", "SHOTGUN", "COVER_2", RECEVEURS, DEFENSEURS, QB, 0.55, 1234, 57)
        b = moteur.decider_passe("DEEP_POST", "SHOTGUN", "COVER_2", RECEVEURS, DEFENSEURS, QB, 0.55, 1234, 57)
        self.assertEqual(a[1].to_dict(), b[1].to_dict())
        self.assertEqual(a[2].to_dict(), b[2].to_dict())

    def test_actions_differentes_flux_differents(self):
        ds = {moteur.decider_passe("DEEP_POST", "SHOTGUN", "COVER_2", RECEVEURS, DEFENSEURS, QB, 0.55, 1234, k)[1].temps_pression
              for k in range(30)}
        self.assertGreater(len(ds), 20)

    def test_flux_independant_du_hasard_global(self):
        random.seed(1)
        a = moteur.decider_passe("CURL", None, "MAN", RECEVEURS, DEFENSEURS, QB, 0.5, 9, 3)[2].to_dict()
        random.seed(99); random.random()
        b = moteur.decider_passe("CURL", None, "MAN", RECEVEURS, DEFENSEURS, QB, 0.5, 9, 3)[2].to_dict()
        self.assertEqual(a, b)


class TestResolution(unittest.TestCase):
    BASE = resolution.probabilites_base(0.03, 0.10, 0.35)

    def _d(self, action, statut="", pression=False):
        from moteur.decision_qb import QBDecision
        return QBDecision(action, "WR1", "WR1" if action == LANCER else "", 1, 1, statut, pression, False, 2.0)

    def test_base(self):
        self.assertAlmostEqual(sum(self.BASE.values()), 1.0)
        self.assertAlmostEqual(self.BASE["sack"], 0.07)

    def test_libre_meilleur_que_couvert(self):
        lib = resolution.probabilites_ajustees(self.BASE, self._d(LANCER, LIBRE))
        cov = resolution.probabilites_ajustees(self.BASE, self._d(LANCER, COUVERT))
        self.assertGreater(lib["comp"], cov["comp"] + 0.2)
        self.assertLess(lib["int"], cov["int"])

    def test_throwaway_jamais_complete_ni_interceptee(self):
        p = resolution.probabilites_ajustees(self.BASE, self._d(THROWAWAY))
        self.assertEqual(p["comp"], 0.0)
        self.assertEqual(p["int"], 0.0)

    def test_sack_majoritaire_sans_solution(self):
        self.assertGreater(resolution.probabilites_ajustees(self.BASE, self._d(SACK))["sack"], 0.7)

    def test_probabilites_valides(self):
        for a in (LANCER, THROWAWAY, SACK, SCRAMBLE):
            for st in (LIBRE, SERRE, COUVERT, DOUBLE):
                for pr in (False, True):
                    p = resolution.probabilites_ajustees(self.BASE, self._d(a, st, pr))
                    self.assertTrue(all(v >= 0 for v in p.values()))
                    self.assertAlmostEqual(sum(p.values()), 1.0)
                    s = resolution.seuils(p)
                    self.assertTrue(s[0] <= s[1] <= s[2] <= 1.0 + 1e-9)


class TestStats(unittest.TestCase):
    def test_agregation(self):
        log = [
            {"play_type": "PASS", "outcome": "PASS_COMPLETE", "yards_gained": 12,
             "decision": {"action": "LANCER", "target": {"role": "WR2", "id": "X_WR2"}, "read": 2, "status": "LIBRE",
                          "coverage": "Cover 2", "pressure": False, "forced": False, "throw_time": 2.4}},
            {"play_type": "PASS", "outcome": "PASS_INCOMPLETE", "yards_gained": 0,
             "decision": {"action": "THROWAWAY", "target": None, "read": 0}},
            {"play_type": "PASS", "outcome": "SACK", "yards_gained": -6, "decision": {"action": "SACK", "read": 0}},
            {"play_type": "RUN", "outcome": "RUN", "yards_gained": 4},
        ]
        s = stats_decisions([log])
        self.assertEqual(s["dropbacks"], 3)
        self.assertEqual(s["lancers"], 1)
        self.assertEqual(s["throwaways"], 1)
        self.assertEqual(s["sacks"], 1)
        self.assertEqual(s["par_role"]["WR2"]["completes"], 1)
        self.assertEqual(s["taux_premiere_lecture"], 0.0)


if __name__ == "__main__":
    unittest.main()
