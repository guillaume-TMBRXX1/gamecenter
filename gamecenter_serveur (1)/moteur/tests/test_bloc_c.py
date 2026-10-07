"""Tests du bloc C (intelligence des joueurs : receveurs et défenseurs). Quelques secondes :

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)

Comme au bloc B, chaque comparaison porte sur une DISTRIBUTION (milliers de tirages dans la même situation).
"""
import random
import statistics
import unittest

import moteur
from moteur import intelligence_joueurs as ij, resolution
from moteur.decision_qb import QBDecision, LANCER
from moteur.intelligence_joueurs import (ATTRIBUTS_RECEVEUR, ATTRIBUTS_DEFENSEUR, PROFILS, attributs_joueur,
                                         attributs_receveur, attributs_defenseur, ajuster_post_snap,
                                         modificateurs_reception, yards_apres_reception, OUVERT, TRAFIC, DISPUTE)
from moteur.progressions import progression
from moteur.reaction_defensive import DefensiveReactionEngine, LIBRE, SERRE, COUVERT, DOUBLE
from moteur.stats import stats_decisions
from moteur.tests.test_bloc_a import RECEVEURS, DEFENSEURS, joueur
from moteur.tests.test_bloc_b import qb_iq


def rec_iq(pid="WR1", **over):
    iq = {a: 80 for a in ATTRIBUTS_RECEVEUR}
    iq.update(over)
    return {"id": pid, "name": pid, "ratings": {"speed": 80, "route_running": 80, "catching": 80}, "iq": iq}


def def_iq(pid="CB1", **over):
    iq = {a: 80 for a in ATTRIBUTS_DEFENSEUR}
    iq.update(over)
    return {"id": pid, "name": pid, "ratings": {"speed": 80, "coverage": 80}, "iq": iq}


def defense(cb1=None, **over):
    """Défense moyenne (attributs à 80) ; cb1 remplace le CB1 (vis-à-vis du WR1 en homme)."""
    d = {"CB": [cb1 or def_iq("CB1"), def_iq("CB2")], "S": [def_iq("S1"), def_iq("S2")],
         "LB": [def_iq("LB1"), def_iq("LB2"), def_iq("LB3")]}
    d.update(over)
    return d


def attaque(wr1=None):
    return {"WR1": wr1 or rec_iq("WR1"), "WR2": rec_iq("WR2"), "WR3": rec_iq("WR3"), "TE": rec_iq("TE"),
            "RB": rec_iq("RB")}


def etats(concept_def, concept, receveurs, defenseurs, n=3000, graine=7):
    """n états post-snap du bloc C dans la même situation (flux différents)."""
    lect = progression(concept)
    eng, out = DefensiveReactionEngine(), []
    for k in range(n):
        rng = random.Random(f"{graine}|{k}")
        etat = eng.react(concept_def, lect, receveurs, defenseurs, 0.5, rng, bruit=ij.BRUIT_C)
        ajuster_post_snap(etat, lect, receveurs, defenseurs, concept, random.Random(f"c|{graine}|{k}"))
        out.append(etat)
    return out


def sep_moy(es, role="WR1"):
    return statistics.mean(e.receveurs[role].separation for e in es)


def part(es, cond):
    return sum(1 for e in es if cond(e)) / len(es)


class TestAttributs(unittest.TestCase):
    WR = joueur("CTX_WR1", speed=82, acceleration=84, route_running=88, catching=82)
    CB = joueur("CTX_CB1", speed=84, acceleration=83, coverage=86, tackling=82)

    def test_attributs_bornes_et_deterministes(self):
        a, b = attributs_receveur(self.WR, "WR", "CTX"), attributs_receveur(self.WR, "WR", "CTX")
        self.assertEqual(a, b)
        self.assertEqual(set(a), set(ATTRIBUTS_RECEVEUR))
        d = attributs_defenseur(self.CB, "CB", "CTX")
        self.assertEqual(set(d), set(ATTRIBUTS_DEFENSEUR))
        self.assertTrue(all(30 <= v <= 99 for v in list(a.values()) + list(d.values())))

    def test_postes(self):
        self.assertIsNone(attributs_joueur(self.WR, "QB"))
        self.assertIsNone(attributs_joueur(self.WR, "OL"))
        for p in ("WR", "TE", "RB"):
            self.assertIn("contested_catch", attributs_joueur(self.WR, p))
        for p in ("CB", "S", "LB"):
            self.assertIn("discipline", attributs_joueur(self.CB, p))

    def test_identite_de_la_franchise(self):
        self.assertGreater(attributs_receveur(self.WR, "WR", "MNL")["contested_catch"],
                           attributs_receveur(self.WR, "WR", "VEC")["contested_catch"])
        self.assertGreater(attributs_defenseur(self.CB, "CB", "AEG")["discipline"],
                           attributs_defenseur(self.CB, "CB", "VEC")["discipline"] + 8)
        self.assertGreater(attributs_defenseur(self.CB, "CB", "VEC")["reaction"],
                           attributs_defenseur(self.CB, "CB", "MNL")["reaction"])
        self.assertEqual(set(PROFILS), {"CTX", "VEC", "AEG", "MNL", "AXM", "GLT", "CPH", "NVA",
                                         "PLS", "ONX", "FRG", "MRD", "APX", "LTC", "ZPH", "BST"})   # palier 3 : 16

    def test_note_presente_prise_telle_quelle(self):
        self.assertEqual(attributs_receveur(joueur("X", route_running=80, route_iq=61))["route_iq"], 61)

    def test_meilleures_notes_meilleurs_attributs(self):
        bon = attributs_receveur(joueur("A", speed=92, acceleration=92, route_running=92, catching=92))
        faible = attributs_receveur(joueur("B", speed=68, acceleration=68, route_running=68, catching=68))
        for k in ATTRIBUTS_RECEVEUR:
            self.assertGreater(bon[k], faible[k], k)
        bon = attributs_defenseur(joueur("C", speed=92, acceleration=92, coverage=92, tackling=92), "CB")
        faible = attributs_defenseur(joueur("D", speed=68, acceleration=68, coverage=68, tackling=68), "CB")
        for k in ATTRIBUTS_DEFENSEUR:
            self.assertGreater(bon[k], faible[k], k)


class TestProfil(unittest.TestCase):
    """Le niveau du joueur est déjà dans le duel de notes du bloc A : le bloc C ne fait peser que son PROFIL."""

    def test_le_niveau_n_est_pas_compte_deux_fois(self):
        for notes in ((92, 92, 92, 92), (70, 70, 70, 70)):
            cb = joueur("CB", speed=notes[0], acceleration=notes[1], coverage=notes[2], tackling=notes[3])
            cb["iq"] = {a: ij.niveau(cb) for a in ATTRIBUTS_DEFENSEUR}
            self.assertTrue(all(abs(ij._e(cb, a)) < 1e-9 for a in ATTRIBUTS_DEFENSEUR))
        bon, faible = joueur("A", coverage=92, speed=92), joueur("B", coverage=70, speed=70)
        self.assertGreater(ij.niveau(bon), ij.niveau(faible) + 8)

    def test_profil_au_dela_du_niveau(self):
        # même niveau de notes, profils différents : le CB discipliné et bon en homme se distingue
        base = dict(speed=84, acceleration=84, coverage=84, tackling=84)
        cb = joueur("CB", **base)
        homme = dict(cb, iq={a: 82 for a in ATTRIBUTS_DEFENSEUR}, id="H")
        homme["iq"].update(man_iq=92, reaction=90)
        zone = dict(cb, iq={a: 82 for a in ATTRIBUTS_DEFENSEUR}, id="Z")
        zone["iq"].update(man_iq=72, reaction=74)
        a = etats("MAN", "QUICK_SLANT", attaque(), defense(homme))
        b = etats("MAN", "QUICK_SLANT", attaque(), defense(zone))
        self.assertLess(sep_moy(a), sep_moy(b) - 0.1)


class TestDefenseurs(unittest.TestCase):
    """Le cœur du bloc C : deux défenseurs de notes différentes, face à la même situation, réagissent différemment."""

    def test_man_iq_et_reaction_en_homme(self):
        bon = etats("MAN", "QUICK_SLANT", attaque(), defense(def_iq("CB1", man_iq=94, reaction=94)))
        faible = etats("MAN", "QUICK_SLANT", attaque(), defense(def_iq("CB1", man_iq=64, reaction=64)))
        self.assertLess(sep_moy(bon), sep_moy(faible) - 0.15)
        self.assertLess(part(bon, lambda e: e.receveurs["WR1"].statut == LIBRE),
                        part(faible, lambda e: e.receveurs["WR1"].statut == LIBRE) - 0.04)
        # les autres receveurs ne sont pas concernés (même CB2, mêmes safeties)
        self.assertAlmostEqual(sep_moy(bon, "WR2"), sep_moy(faible, "WR2"), delta=0.05)

    def test_zone_iq_en_zone(self):
        lb = [def_iq("LB1", zone_iq=94), def_iq("LB2", zone_iq=94), def_iq("LB3", zone_iq=94)]
        lb_f = [def_iq("LB1", zone_iq=62), def_iq("LB2", zone_iq=62), def_iq("LB3", zone_iq=62)]
        cb = [def_iq("CB1", zone_iq=94), def_iq("CB2", zone_iq=94)]
        cb_f = [def_iq("CB1", zone_iq=62), def_iq("CB2", zone_iq=62)]
        bon = etats("COVER_3", "SHORT_OUT", attaque(), defense(LB=lb, CB=cb))
        faible = etats("COVER_3", "SHORT_OUT", attaque(), defense(LB=lb_f, CB=cb_f))
        self.assertLess(sep_moy(bon), sep_moy(faible) - 0.1)
        # en zone, le man IQ ne compte presque pas
        h = etats("COVER_3", "SHORT_OUT", attaque(), defense(def_iq("CB1", man_iq=94)))
        b = etats("COVER_3", "SHORT_OUT", attaque(), defense(def_iq("CB1", man_iq=64)))
        self.assertLess(abs(sep_moy(h) - sep_moy(b)), 0.06)

    def test_discipline_et_play_recognition_coverage_bust(self):
        sage = etats("MAN", "PLAY_ACTION", attaque(), defense(def_iq("CB1", discipline=95, play_recognition=95)), n=6000)
        mord = etats("MAN", "PLAY_ACTION", attaque(), defense(def_iq("CB1", discipline=58, play_recognition=58)), n=6000)
        p_sage = part(sage, lambda e: e.receveurs["WR1"].bust)
        p_mord = part(mord, lambda e: e.receveurs["WR1"].bust)
        self.assertGreater(p_mord, 2.5 * p_sage)
        self.assertGreater(p_sage, 0.0)                 # même un défenseur discipliné se fait avoir, rarement
        # un bust laisse le receveur seul
        b = [e for e in mord if e.receveurs["WR1"].bust]
        self.assertGreater(sum(e.receveurs["WR1"].statut == LIBRE for e in b) / len(b), 0.8)

    def test_play_action_plus_de_busts(self):
        cb = defense(def_iq("CB1", discipline=70))
        pa = etats("MAN", "PLAY_ACTION", attaque(), cb, n=6000)
        court = etats("MAN", "QUICK_SLANT", attaque(), cb, n=6000)
        self.assertGreater(part(pa, lambda e: e.receveurs["WR1"].bust),
                           2 * part(court, lambda e: e.receveurs["WR1"].bust))

    def test_play_recognition_contre_le_screen(self):
        lb = lambda v: [def_iq("LB1", play_recognition=v), def_iq("LB2"), def_iq("LB3")]
        bon = etats("ZONE", "SCREEN", attaque(), defense(LB=lb(95)))
        faible = etats("ZONE", "SCREEN", attaque(), defense(LB=lb(60)))
        self.assertLess(sep_moy(bon, "RB"), sep_moy(faible, "RB") - 0.15)

    def test_awareness_sur_la_soupape(self):
        lb = lambda v: [def_iq("LB1", awareness=v), def_iq("LB2", awareness=v), def_iq("LB3", awareness=v)]
        bon = etats("MAN", "QUICK_SLANT", attaque(), defense(LB=lb(95)))
        faible = etats("MAN", "QUICK_SLANT", attaque(), defense(LB=lb(60)))
        self.assertLess(sep_moy(bon, "RB"), sep_moy(faible, "RB") - 0.05)


class TestReceveurs(unittest.TestCase):
    def test_route_iq_ecart_de_route(self):
        bon = etats("MAN", "CURL", attaque(rec_iq("WR1", route_iq=95)), defense())
        faible = etats("MAN", "CURL", attaque(rec_iq("WR1", route_iq=62)), defense())
        eb = [e.receveurs["WR1"].ecart_route for e in bon]
        ef = [e.receveurs["WR1"].ecart_route for e in faible]
        self.assertLess(statistics.pstdev(eb), statistics.pstdev(ef) - 0.1)     # route plus fidèle
        self.assertGreater(statistics.mean(eb), statistics.mean(ef))

    def test_release_compte_surtout_en_homme(self):
        h = etats("MAN", "CURL", attaque(rec_iq("WR1", release=95)), defense())
        b = etats("MAN", "CURL", attaque(rec_iq("WR1", release=62)), defense())
        hz = etats("COVER_3", "CURL", attaque(rec_iq("WR1", release=95)), defense())
        bz = etats("COVER_3", "CURL", attaque(rec_iq("WR1", release=62)), defense())
        self.assertGreater(sep_moy(h) - sep_moy(b), 2 * (sep_moy(hz) - sep_moy(bz)))
        self.assertGreater(sep_moy(h), sep_moy(b) + 0.1)

    def test_coverage_recognition_en_zone(self):
        h = etats("COVER_3", "CURL", attaque(rec_iq("WR1", coverage_recognition=95)), defense())
        b = etats("COVER_3", "CURL", attaque(rec_iq("WR1", coverage_recognition=62)), defense())
        self.assertGreater(sep_moy(h), sep_moy(b) + 0.15)

    def test_reception(self):
        star = rec_iq("WR1", contested_catch=95, catch_in_traffic=95)
        faible = rec_iq("WR1", contested_catch=62, catch_in_traffic=62)
        cb, cb_vif = def_iq(), def_iq(reaction=95, awareness=95, man_iq=95)
        self.assertEqual(modificateurs_reception(star, cb, LIBRE, "homme")[2], OUVERT)
        self.assertEqual(modificateurs_reception(star, cb, SERRE, "homme")[2], TRAFIC)
        self.assertEqual(modificateurs_reception(star, cb, COUVERT, "homme")[2], DISPUTE)
        self.assertEqual(modificateurs_reception(star, cb, DOUBLE, "zone")[2], DISPUTE)
        for st in (SERRE, COUVERT):
            i_s, inc_s, _ = modificateurs_reception(star, cb, st, "homme")
            i_f, inc_f, _ = modificateurs_reception(faible, cb, st, "homme")
            self.assertLess(inc_s, inc_f, st)
            self.assertLess(i_s, i_f, st)
        # un défenseur vif et attentif : plus d'interceptions sur le ballon disputé
        self.assertGreater(modificateurs_reception(faible, cb_vif, COUVERT, "homme")[0],
                           modificateurs_reception(faible, cb, COUVERT, "homme")[0])
        # résolution : le contested catch d'une star se complète plus souvent
        base = resolution.probabilites_base(0.03, 0.10, 0.35)
        comp = {}
        for nom, r in (("star", star), ("faible", faible)):
            m_int, m_inc, _ = modificateurs_reception(r, cb, COUVERT, "homme")
            d = QBDecision(LANCER, "WR1", "WR1", 1, 1, COUVERT, False, True, 2.0, mod_int=m_int, mod_inc=m_inc, bloc="C")
            comp[nom] = resolution.probabilites_ajustees(base, d, resolution.CALIBRATION_C)["comp"]
        self.assertGreater(comp["star"], comp["faible"] + 0.03)

    def test_yards_apres_reception(self):
        self.assertGreater(yards_apres_reception(rec_iq(separation=95), def_iq(pursuit=65)), 0.5)
        self.assertLess(yards_apres_reception(rec_iq(separation=65), def_iq(pursuit=95)), -0.5)
        self.assertEqual(yards_apres_reception(rec_iq(), def_iq()), 0.0)


class TestChaine(unittest.TestCase):
    def args(self, receveurs, defenseurs, qb, n):
        return ("DEEP_POST", "SHOTGUN", "MAN", receveurs, defenseurs, qb, 0.5, 4242, n)

    def test_bloc_c_deterministe_et_complet(self):
        rc, dc = attaque(), defense()
        for n in range(200):
            a = moteur.decider_passe(*self.args(rc, dc, qb_iq(), n))
            b = moteur.decider_passe(*self.args(rc, dc, qb_iq(), n))
            self.assertEqual(a[2], b[2])
            self.assertEqual(a[1].to_dict(), b[1].to_dict())
            d = a[2]
            self.assertEqual(d.bloc, "C")
            if d.action == LANCER:
                self.assertIn(d.reception, (OUVERT, TRAFIC, DISPUTE))
                self.assertTrue(d.couvreur_id)

    def test_sans_attributs_bloc_b_a_l_identique(self):
        # receveurs sans "iq" : décision du bloc B, état post-snap du bloc A-B (même bruit, aucun champ du bloc C)
        rb = {r: {k: v for k, v in j.items() if k != "iq"} for r, j in attaque().items()}
        for n in range(200):
            _, etat, d = moteur.decider_passe(*self.args(rb, DEFENSEURS, qb_iq(), n))
            self.assertEqual(d.bloc, "B")
            self.assertEqual(d.reception, "")
            self.assertFalse(any(e.couvreur_id or e.bust for e in etat.receveurs.values()))
            _, etat_a, d_a = moteur.decider_passe(*self.args(rb, DEFENSEURS, None, n))
            self.assertEqual(d_a.bloc, "A")

    def test_flux_du_bloc_c_separe(self):
        # attributs tous à 80 (écart effectif nul) : seuls le bruit réduit, l'écart de route et les busts diffèrent ;
        # le flux du QB n'est pas consommé par le bloc C -> la chaîne reste reproductible action par action
        rc = attaque()
        a = [moteur.decider_passe(*self.args(rc, defense(), qb_iq(), n))[2] for n in range(50)]
        random.seed(999)
        random.random()
        b = [moteur.decider_passe(*self.args(rc, defense(), qb_iq(), n))[2] for n in range(50)]
        self.assertEqual(a, b)

    def test_stats_du_bloc_c(self):
        log = [
            {"play_type": "PASS", "outcome": "PASS_COMPLETE", "yards_gained": 12, "decision": {
                "action": "LANCER", "read": 1, "target": {"role": "WR1", "id": "W"}, "status": "COUVERT",
                "reception": "contested", "coverer": {"id": "C1", "name": "C One"}, "bust": False, "busts": []}},
            {"play_type": "PASS", "outcome": "PASS_INCOMPLETE", "yards_gained": 0, "decision": {
                "action": "LANCER", "read": 2, "target": {"role": "WR2", "id": "W2"}, "status": "SERRE",
                "reception": "traffic", "coverer": {"id": "C1", "name": "C One"}, "bust": False, "busts": ["TE"]}},
            {"play_type": "PASS", "outcome": "PASS_COMPLETE", "yards_gained": 40, "decision": {
                "action": "LANCER", "read": 1, "target": {"role": "WR1", "id": "W"}, "status": "LIBRE",
                "reception": "open", "coverer": {"id": "S1", "name": "S One"}, "bust": True, "busts": ["WR1"]}},
        ]
        s = stats_decisions([log])
        self.assertEqual(s["bloc_c"], 3)
        self.assertEqual(s["busts"], 2)
        self.assertEqual(s["busts_cible"], 1)
        self.assertEqual(s["par_reception"]["contested"]["completes"], 1)
        self.assertEqual(s["par_couvreur"]["C1"]["cibles"], 2)
        self.assertEqual(s["par_couvreur"]["S1"]["yards"], 40)
        self.assertAlmostEqual(s["taux_bust"], 1 / 3)


if __name__ == "__main__":
    unittest.main()
