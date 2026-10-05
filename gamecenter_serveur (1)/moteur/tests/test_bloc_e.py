"""Tests du bloc E (progression des joueurs). Quelques secondes :

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)

Progression · régression · potentiel · forme · évolution par attribut · expérience (intelligence) · déterminisme ·
anti-inflation (moyenne de la ligue, plafonds, écart d'équipe) · persistance (JSON) · courbe par semaine.
"""
import json
import random
import statistics
import unittest
from unittest import mock

from moteur import developpement as dv

GABARIT = {
    "QB": ["throw_power", "throw_accuracy", "mobility", "decision_making"],
    "RB": ["speed", "acceleration", "elusiveness", "power"],
    "WR": ["speed", "acceleration", "route_running", "catching"],
    "TE": ["speed", "route_running", "catching", "run_block"],
    "LT": ["run_block", "pass_block", "strength"], "C": ["run_block", "pass_block", "strength"],
    "EDGE": ["strength", "pass_rush", "tackling"], "LB": ["speed", "strength", "coverage", "tackling"],
    "CB": ["speed", "acceleration", "coverage", "tackling"], "S": ["speed", "coverage", "tackling", "run_support"],
    "K": ["leg_power", "accuracy"],
}
PROFONDEUR = {"QB": 1, "RB": 2, "WR": 3, "TE": 1, "LT": 1, "C": 1, "EDGE": 2, "LB": 2, "CB": 2, "S": 2, "K": 1}
EQUIPES = ("AAA", "BBB", "CCC", "DDD")


def ligue(niveau=80):
    """4 équipes de 17 joueurs, notes de base déterministes."""
    rng = random.Random("ligue-test")
    out = []
    for t in EQUIPES:
        for pos, n in PROFONDEUR.items():
            for i in range(1, n + 1):
                out.append({"id": f"{t}_{pos}{i}", "name": f"{t} {pos}{i}", "pos": pos, "team": t,
                            "ratings": {k: niveau + rng.randint(-6, 6) for k in GABARIT[pos]}})
    return out


def unites(_t, notes):
    """Notes d'unité simplifiées (moyennes par côté) pour le garde-fou d'équipe."""
    cote = lambda pid: dv.COTE[dv.UNITE[dv.decoder_id(pid)[1]]]
    moy = lambda c: statistics.mean(v for p, n in notes.items() if cote(p) == c for v in n.values())
    o, d = moy("off"), moy("def")
    return {"pass_off": o, "run_off": o, "pass_def": d, "run_def": d, "special_teams": moy("st")}


def stats_neutres(etat):
    sj = {pid: {"pass_att": 300, "pass_yds": 2100, "pass_td": 12, "ints": 7, "rush_att": 120, "rush_yds": 600,
                "targets": 50, "rec_yds": 500, "tackles": 30, "sacks": 3, "def_int": 1, "passes_defended": 3,
                "fg_att": 20, "fg_made": 17} for pid in etat["joueurs"]}
    se = {t: {"games": 18, "rush_att": 400, "rush_yds": 2000, "pass_att": 600, "sacks_taken": 45} for t in EQUIPES}
    return sj, se


def joueur_isole(age=24.0, potentiel=6.0, dev="normal", pos="WR", notes=None):
    return {"age0": age, "dev": dev, "potentiel": potentiel, "carriere": max(0.0, age - 21.5), "pos": pos,
            "team": "AAA", "name": "x", "base": dict(notes or {"speed": 80, "acceleration": 80, "route_running": 80,
                                                                 "catching": 80}),
            "actuelle": {k: float(v) for k, v in (notes or {"speed": 80, "acceleration": 80, "route_running": 80,
                                                           "catching": 80}).items()},
            "forme": 0.0, "apprentissage": 0.0, "bonus_iq": 0.0, "historique": []}


def moyenne_delta(j, attribut, age, participation=1.0, n=400):
    return statistics.mean(dv.delta_note(j, attribut, age, participation, random.Random(i)) for i in range(n))


def avancer(etat, semaines, depart=1, stats=True):
    for w in range(depart, depart + semaines):
        sj, se = stats_neutres(etat) if stats else (None, None)
        etat, _ = dv.semaine_suivante(etat, sj, se, unites, index=w)
    return etat


class TestDepart(unittest.TestCase):
    def test_etat_initial_identique_au_roster(self):
        L = ligue()
        E = dv.etat_initial(L)
        for j in L:
            self.assertEqual(dv.notes_effectives(E["joueurs"][j["id"]]), j["ratings"])
        self.assertEqual(dv.controler(E, unites), [])

    def test_profil_deterministe_et_borne(self):
        a, b = dv.profil_initial("CTX_WR2", "WR", 2), dv.profil_initial("CTX_WR2", "WR", 2)
        self.assertEqual(a, b)
        for pid in (f"T_{p}{i}" for p in ("QB", "WR", "K", "CB") for i in range(1, 30)):
            pr = dv.profil_initial(pid, dv.decoder_id(pid)[1], 1)
            self.assertTrue(21.0 <= pr["age0"] <= 36.0 and pr["potentiel"] >= 0 and pr["dev"] in dv.DEV_MULT)

    def test_jeunes_plus_de_potentiel(self):
        pr = [dv.profil_initial(f"T_WR{i}", "WR", 1) for i in range(300)]
        jeunes = [p["potentiel"] for p in pr if p["age0"] < 24]
        vieux = [p["potentiel"] for p in pr if p["age0"] > 29]
        self.assertGreater(statistics.mean(jeunes), statistics.mean(vieux) + 4)

    def test_decoder_id(self):
        self.assertEqual(dv.decoder_id("CTX_EDGE2"), ("CTX", "EDGE", 2))
        self.assertEqual(dv.decoder_id("MNL_QB1"), ("MNL", "QB", 1))


class TestProgressionRegression(unittest.TestCase):
    def test_jeune_progresse(self):
        j = joueur_isole(age=22.0, potentiel=8.0)
        self.assertGreater(moyenne_delta(j, "route_running", 22.0), 0.5)
        self.assertGreater(moyenne_delta(j, "speed", 22.0), 0.5)

    def test_rythme_de_developpement(self):
        lent, star = joueur_isole(dev="slow"), joueur_isole(dev="star")
        self.assertGreater(moyenne_delta(star, "catching", 23.0), moyenne_delta(lent, "catching", 23.0) + 0.3)

    def test_vieux_regresse_physique_plus_que_technique(self):
        j = joueur_isole(age=32.0, potentiel=0.0)
        physique, technique = moyenne_delta(j, "speed", 32.0), moyenne_delta(j, "route_running", 32.0)
        self.assertLess(physique, -0.5)
        self.assertLess(physique, technique - 0.3)

    def test_rb_s_use_plus_tot(self):
        rb = joueur_isole(age=28.0, potentiel=0.0, pos="RB", notes={"speed": 85, "power": 85})
        wr = joueur_isole(age=28.0, potentiel=0.0, pos="WR", notes={"speed": 85, "catching": 85})
        self.assertLess(moyenne_delta(rb, "speed", 28.0), moyenne_delta(wr, "speed", 28.0) - 0.2)

    def test_mental_progresse_avec_l_experience(self):
        qb = joueur_isole(age=31.0, potentiel=0.0, pos="QB",
                          notes={"throw_power": 85, "throw_accuracy": 85, "mobility": 80, "decision_making": 80})
        self.assertGreater(moyenne_delta(qb, "decision_making", 31.0, 1.0), 0.1)
        self.assertLess(moyenne_delta(qb, "throw_power", 31.0, 1.0), -0.1)
        self.assertGreater(moyenne_delta(qb, "decision_making", 31.0, 1.0),
                           moyenne_delta(qb, "decision_making", 31.0, 0.0) + 0.1)    # jouer fait apprendre

    def test_jouer_fait_progresser(self):
        j = joueur_isole(age=22.0, potentiel=8.0)
        self.assertGreater(moyenne_delta(j, "catching", 22.0, 1.0), moyenne_delta(j, "catching", 22.0, 0.0) + 0.2)

    def test_potentiel_plafonne(self):
        j = joueur_isole(age=21.0, potentiel=4.0, dev="star")
        rng = random.Random(3)
        for _ in range(80):
            for k in j["actuelle"]:
                j["actuelle"][k] += dv.delta_note(j, k, 21.0, 1.0, rng)
            dv._borner_actuelle(j)
        for k, v in j["actuelle"].items():
            self.assertLessEqual(v, j["base"][k] + 4.0 + 1e-9)
        self.assertGreater(min(j["actuelle"].values()), 82.5)        # il a atteint (presque) son plafond

    def test_sans_potentiel_pas_de_croissance(self):
        j = joueur_isole(age=22.0, potentiel=0.0)
        self.assertAlmostEqual(moyenne_delta(j, "catching", 22.0), 0.0, delta=0.05)

    def test_age_un_an_toutes_les_4_semaines(self):
        E = avancer(dv.etat_initial(ligue()), 8, stats=False)
        j = E["joueurs"]["AAA_WR1"]
        self.assertAlmostEqual(dv.age(j, E["semaines"]) - j["age0"], 2.0)


class TestForme(unittest.TestCase):
    def test_bonne_semaine_bonne_forme(self):
        E = dv.etat_initial(ligue())
        sj, se = stats_neutres(E)
        qbs = [p for p in E["joueurs"] if "_QB" in p]
        sj[qbs[0]].update(pass_yds=3200, pass_td=28, ints=2)        # le meilleur QB de la semaine
        sj[qbs[1]].update(pass_yds=1500, pass_td=4, ints=16)        # le pire
        perf = dv.performances(E, sj, se)
        self.assertGreater(perf[qbs[0]][1], 0.8)
        self.assertLess(perf[qbs[1]][1], -0.8)
        bons = mauvais = 0
        for w in range(40):
            E2, _ = dv.semaine_suivante(E, sj, se, unites, index=w)
            bons += E2["joueurs"][qbs[0]]["forme"]
            mauvais += E2["joueurs"][qbs[1]]["forme"]
        self.assertGreater(bons / 40, 1.0)
        self.assertLess(mauvais / 40, -1.0)

    def test_forme_bornee_et_centree(self):
        E = avancer(dv.etat_initial(ligue()), 6)
        formes = [j["forme"] for j in E["joueurs"].values()]
        self.assertTrue(all(abs(f) <= dv.FORME_MAX for f in formes))
        par_unite = {}
        for j in E["joueurs"].values():
            par_unite.setdefault(dv.UNITE[j["pos"]], []).append(j["forme"])
        for u, fs in par_unite.items():
            self.assertAlmostEqual(statistics.mean(fs), 0.0, delta=0.6, msg=u)

    def test_forme_sur_toutes_les_notes(self):
        j = joueur_isole()
        j["forme"] = 2.0
        self.assertEqual(dv.notes_effectives(j), {k: 82 for k in j["base"]})

    def test_bilan_de_l_equipe(self):
        E = dv.etat_initial(ligue())
        sj, se = stats_neutres(E)
        perf = dv.performances(E, sj, se, bilans={"AAA": 1.0, "BBB": 0.0})
        self.assertGreater(perf["AAA_LT1"][1], perf["BBB_LT1"][1])

    def test_participation(self):
        E = dv.etat_initial(ligue())
        sj, se = stats_neutres(E)
        sj["AAA_RB1"]["rush_att"], sj["AAA_RB2"]["rush_att"] = 300, 60
        perf = dv.performances(E, sj, se)
        self.assertEqual(perf["AAA_RB1"][0], 1.0)
        self.assertLess(perf["AAA_RB2"][0], 0.4)
        perf0 = dv.performances(E, None, None)                      # sans stats : RB2 en rotation, titulaires pleins
        self.assertEqual((perf0["AAA_QB1"][0], perf0["AAA_RB2"][0]), (1.0, 0.3))


class TestAntiInflation(unittest.TestCase):
    def test_moyenne_de_la_ligue_stable(self):
        E = avancer(dv.etat_initial(ligue()), 30)
        r = dv.rapport_semaine(E)
        self.assertLess(r["league_drift_max"], 0.6, r["league_drift"])
        self.assertEqual(dv.controler(E, unites), [])

    def test_ecart_d_equipe_borne(self):
        L = ligue()
        E = dv.etat_initial(L)
        for pid, j in E["joueurs"].items():          # AAA : que des jeunes stars, les autres : des vétérans
            if pid.startswith("AAA"):
                j.update(age0=21.0, dev="star", potentiel=12.0)
            else:
                j.update(age0=30.0, dev="slow", potentiel=0.0)
        gardes = 0
        for w in range(1, 25):
            E, R = dv.semaine_suivante(E, *stats_neutres(E), unites, index=w)
            gardes += bool(R["team_guard"])
            for t, us in dv.ecarts_unites(E, unites).items():
                for u, d in us.items():
                    self.assertLessEqual(abs(d), dv.ECART_EQUIPE_MAX + 1e-6, (w, t, u, d))
                self.assertLessEqual(abs(dv.force(us)), dv.FORCE_EQUIPE_MAX + 1e-6, (w, t))
        self.assertGreater(gardes, 0)               # le garde-fou a bien servi
        forces = {t: dv.force(u) for t, u in dv.ecarts_unites(E, unites).items()}
        self.assertEqual(max(forces, key=forces.get), "AAA")             # AAA reste la plus forte...
        self.assertLessEqual(forces["AAA"], dv.FORCE_EQUIPE_MAX + 1e-6)  # ... dans la borne de force

    def test_rb_titulaires_a_part(self):
        E = dv.etat_initial(ligue())
        for pid, j in E["joueurs"].items():          # RB1 jeunes, RB2 vétérans : la moyenne des RB1 ne monte pas
            if "_RB" in pid:
                j.update(age0=21.5 if pid.endswith("1") else 32.0, potentiel=9.0 if pid.endswith("1") else 0.0)
        E = avancer(E, 16)
        for prof in (1, 2):
            rbs = [j for p, j in E["joueurs"].items() if f"_RB{prof}" in p]
            for k in ("speed", "power"):
                self.assertAlmostEqual(statistics.mean(j["actuelle"][k] for j in rbs),
                                       statistics.mean(j["base"][k] for j in rbs), delta=0.6, msg=(prof, k))

    def test_force_d_equipe_bornee_sans_effacer_les_joueurs(self):
        E = dv.etat_initial(ligue())
        for pid, j in E["joueurs"].items():          # AAA : vétérans sauf un jeune ; les autres : des jeunes
            vieux = pid.startswith("AAA") and pid != "AAA_WR1"
            j.update(age0=33.0 if vieux else 21.5, dev="normal" if vieux else "fast", potentiel=0.0 if vieux else 9.0)
        with mock.patch.object(dv, "FORCE_EQUIPE_MAX", 0.3):
            gardes = 0
            for w in range(1, 17):
                E, R = dv.semaine_suivante(E, *stats_neutres(E), unites, index=w)
                gardes += any("force" in g for g in R["team_guard"].values())
                for t, us in dv.ecarts_unites(E, unites).items():
                    self.assertLessEqual(abs(dv.force(us)), 0.3 + 1e-6, (w, t))
            self.assertEqual(dv.controler(E, unites), [])
        self.assertGreater(gardes, 0)
        jeune = dv.ovr(dv.notes_effectives(E["joueurs"]["AAA_WR1"])) - dv.ovr(E["joueurs"]["AAA_WR1"]["base"])
        vieux = dv.ovr(dv.notes_effectives(E["joueurs"]["AAA_WR2"])) - dv.ovr(E["joueurs"]["AAA_WR2"]["base"])
        self.assertGreater(jeune - vieux, 4)        # le décalage commun garde l'écart entre ses joueurs

    def test_bornes_40_99(self):
        L = ligue(niveau=95)
        E = avancer(dv.etat_initial(L), 12)
        for j in E["joueurs"].values():
            self.assertTrue(all(40 <= v <= 99 for v in dv.notes_effectives(j).values()))


class TestExperience(unittest.TestCase):
    def test_bonus_iq_relatif(self):
        E = dv.etat_initial(ligue())
        self.assertEqual(dv.bonus_intelligence(E, "AAA_QB1", "processing"), 0.0)
        E["joueurs"]["AAA_CB1"].update(age0=22.0, carriere=0.5)
        E["joueurs"]["BBB_CB1"].update(age0=33.0, carriere=11.0)
        E = avancer(E, 12)
        jeune, vieux = (dv.bonus_intelligence(E, p, "zone_iq") for p in ("AAA_CB1", "BBB_CB1"))
        self.assertGreater(jeune, vieux)
        groupe = [j["bonus_iq"] for j in E["joueurs"].values() if dv.IQ_GROUPE.get(j["pos"]) == "def"]
        self.assertAlmostEqual(statistics.mean(groupe), 0.0, delta=0.05)          # somme nulle
        self.assertTrue(all(abs(b) <= dv.IQ_MAX for b in groupe))

    def test_bonus_seulement_sur_les_attributs_mentaux(self):
        E = dv.etat_initial(ligue())
        E["joueurs"]["AAA_WR1"]["bonus_iq"] = 3.0
        iq = dv.appliquer_bonus_iq(E, "AAA_WR1", {"route_iq": 80, "separation": 80, "contested_catch": 70})
        self.assertEqual(iq, {"route_iq": 83, "separation": 80, "contested_catch": 70})
        self.assertEqual(dv.appliquer_bonus_iq(E, "INCONNU", {"route_iq": 80}), {"route_iq": 80})


class TestDeterminisme(unittest.TestCase):
    def test_meme_entree_meme_sortie(self):
        E0 = dv.etat_initial(ligue())
        a = avancer(json.loads(json.dumps(E0)), 5)
        b = avancer(json.loads(json.dumps(E0)), 5)
        self.assertEqual(a, b)

    def test_flux_propre(self):
        E0 = dv.etat_initial(ligue())
        random.seed(1); x = random.random()
        random.seed(1); dv.semaine_suivante(E0, *stats_neutres(E0), unites, index=1); y = random.random()
        self.assertEqual(x, y)                      # le hasard global n'est pas consommé
        a, _ = dv.semaine_suivante(E0, *stats_neutres(E0), unites, index=1)
        b, _ = dv.semaine_suivante(E0, *stats_neutres(E0), unites, index=2)
        self.assertNotEqual(a["joueurs"]["AAA_WR1"]["actuelle"], b["joueurs"]["AAA_WR1"]["actuelle"])

    def test_n_altere_pas_l_entree(self):
        E0 = dv.etat_initial(ligue())
        copie = json.loads(json.dumps(E0))
        dv.semaine_suivante(E0, *stats_neutres(E0), unites, index=1)
        self.assertEqual(E0, copie)

    def test_completer_le_roster(self):
        L = ligue()
        neufs = {"DDD_WR3", "DDD_LB2", "CCC_S2"}            # 3 joueurs inconnus de l'état (nouvelles recrues, étape 6)
        E = avancer(dv.etat_initial([j for j in L if j["id"] not in neufs]), 2)
        roster = [j for j in L if j["id"] != "AAA_WR3"]     # ... et un joueur parti
        E2 = dv.completer(E, roster)
        self.assertEqual(set(E2["joueurs"]), {j["id"] for j in roster})
        for j in L:
            if j["id"] in neufs:
                self.assertEqual(dv.notes_effectives(E2["joueurs"][j["id"]]), j["ratings"])
        self.assertEqual(E2["joueurs"]["AAA_WR1"], E["joueurs"]["AAA_WR1"])
        self.assertIn("AAA_WR3", E["joueurs"])              # l'état d'origine n'est pas modifié

    def test_persistance_json(self):
        E = avancer(dv.etat_initial(ligue()), 3)
        rond = json.loads(json.dumps(E))
        self.assertEqual(dv.semaine_suivante(E, *stats_neutres(E), unites, index=4)[0],
                         dv.semaine_suivante(rond, *stats_neutres(rond), unites, index=4)[0])


class TestCourbe(unittest.TestCase):
    def test_marquer_semaine_idempotent(self):
        E = dv.etat_initial(ligue())
        dv.marquer_semaine(E, 1, "2026-10-12")
        dv.marquer_semaine(E, 1, "2026-10-12")
        self.assertEqual(len(E["joueurs"]["AAA_QB1"]["historique"]), 1)
        for w in range(2, 60):
            E = avancer(E, 1, depart=w, stats=False)
            dv.marquer_semaine(E, w)
        h = E["joueurs"]["AAA_QB1"]["historique"]
        self.assertEqual(len(h), dv.HISTORIQUE_MAX)
        self.assertEqual(h[-1]["week"], 59)

    def test_resume_joueur(self):
        E = avancer(dv.etat_initial(ligue()), 4)
        dv.marquer_semaine(E, 5)
        r = dv.resume_joueur(E, "AAA_WR1")
        for k in ("age", "ovr", "ovr_base", "potential", "form", "dev", "experience", "base", "delta", "history"):
            self.assertIn(k, r)
        n = dv.notes_effectives(E["joueurs"]["AAA_WR1"])
        self.assertEqual(r["ovr"], dv.ovr(n))
        self.assertEqual(r["delta"], {k: n[k] - r["base"][k] for k in n})
        self.assertIsNone(dv.resume_joueur(E, "INCONNU"))


if __name__ == "__main__":
    unittest.main()
