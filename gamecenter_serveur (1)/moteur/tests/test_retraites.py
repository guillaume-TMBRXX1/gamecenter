"""Tests des retraites et recrues (étape 6, bloc E). Quelques secondes :

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)

Âge de la retraite · déclin · recrue (base du poste gardée, notes en dessous, grand potentiel, nom unique) ·
déterminisme · sans noms : bloc E à l'identique · trajectoire longue (personne au-delà de l'âge, garde-fou tenu).
"""
import json
import unittest

from moteur import developpement as dv
from moteur.tests.test_bloc_e import joueur_isole, ligue, stats_neutres, unites

NOMS = (["Adrien", "Bastien", "Cyrus", "Dorian", "Emeric", "Fabian"], ["Ashford", "Bellamy", "Castellan", "Delacroix"])


def avancer(etat, semaines, depart=1, noms=NOMS):
    rapports = []
    for w in range(depart, depart + semaines):
        sj, se = stats_neutres(etat)
        etat, r = dv.semaine_suivante(etat, sj, se, unites, index=w, recrues=noms)
        rapports.append(r)
    return etat, rapports


class TestRetraite(unittest.TestCase):
    def test_age_du_poste(self):
        self.assertFalse(dv.doit_partir(joueur_isole(age=34.9), 0))
        self.assertTrue(dv.doit_partir(joueur_isole(age=35.0), 0))
        self.assertTrue(dv.doit_partir(joueur_isole(age=33.0), 8))          # 8 semaines = 2 ans
        qb = joueur_isole(age=36.0, pos="QB", notes={"throw_power": 80, "throw_accuracy": 80, "mobility": 80,
                                                      "decision_making": 80})
        self.assertFalse(dv.doit_partir(qb, 0))                              # QB : 38 ans
        self.assertTrue(dv.doit_partir(qb, 8))

    def test_declin(self):
        j = joueur_isole(age=33.0)
        self.assertFalse(dv.doit_partir(j, 0))
        j["actuelle"] = {k: v - 10 for k, v in j["actuelle"].items()}
        self.assertTrue(dv.doit_partir(j, 0))
        j2 = joueur_isole(age=30.0)                                         # avant AGE_DECLIN : il reste
        j2["actuelle"] = {k: v - 12 for k, v in j2["actuelle"].items()}
        self.assertFalse(dv.doit_partir(j2, 0))


class TestRecrue(unittest.TestCase):
    def test_recrue(self):
        j = joueur_isole(age=36.0)
        j["name"] = "Vieux Joueur"
        r = dv.recrue(j, "AAA_WR1", 12, 7, NOMS, pris={"Adrien Ashford"})
        self.assertEqual(r, dv.recrue(j, "AAA_WR1", 12, 7, NOMS, pris={"Adrien Ashford"}))      # déterministe
        self.assertEqual(r["base"], j["base"])                                # base du poste gardée
        self.assertTrue(all(r["actuelle"][k] < r["base"][k] for k in r["base"]))
        self.assertTrue(dv.RECRUE_AGE[0] <= dv.age(r, 12) <= dv.RECRUE_AGE[1])
        self.assertTrue(dv.RECRUE_POTENTIEL[0] <= r["potentiel"] <= dv.RECRUE_POTENTIEL[1])
        self.assertNotEqual(r["name"], "Adrien Ashford")
        self.assertEqual(r["recrue"], {"semaine": 7, "remplace": "Vieux Joueur"})
        self.assertEqual((r["carriere"], r["historique"], r["forme"]), (0.0, [], 0.0))
        self.assertTrue(all(r["actuelle"][k] <= dv.plafond(r, k) for k in r["base"]))
        json.dumps(r)                                                         # persistable (week.json)

    def test_sans_noms_bloc_e_identique(self):
        E = dv.etat_initial(ligue())
        sj, se = stats_neutres(E)
        a, ra = dv.semaine_suivante(E, sj, se, unites, index=1)
        self.assertNotIn("retirements", ra)
        for pid, j in E["joueurs"].items():               # aucun départ au départ : mêmes notes avec ou sans noms
            j["age0"] = min(j["age0"], 30.0)
        b, rb = dv.semaine_suivante(E, sj, se, unites, index=1, recrues=NOMS)
        a2, _ = dv.semaine_suivante(E, sj, se, unites, index=1)
        self.assertEqual(rb["retirements"], [])
        self.assertEqual(b["joueurs"], a2["joueurs"])


class TestTrajectoire(unittest.TestCase):
    def test_trajectoire_longue(self):
        E = dv.etat_initial(ligue())
        ids = set(E["joueurs"])
        E, rap = avancer(E, 40)
        self.assertEqual(set(E["joueurs"]), ids)                            # mêmes places au roster
        mouv = [m for r in rap for m in r["retirements"]]
        self.assertTrue(mouv, "40 semaines (10 ans) : des départs")
        for m in mouv:
            self.assertGreaterEqual(m["age"], dv.AGE_DECLIN)
            self.assertLess(m["rookie_age"], 24)
        for j in E["joueurs"].values():
            self.assertLess(dv.age(j, E["semaines"]), dv.AGE_RETRAITE.get(j["pos"], dv.AGE_RETRAITE_DEFAUT) + 0.5)
        self.assertEqual(dv.controler(E, unites), [])
        # noms uniques dans chaque équipe
        for t in {j["team"] for j in E["joueurs"].values()}:
            noms = [j["name"] for j in E["joueurs"].values() if j["team"] == t]
            self.assertEqual(len(noms), len(set(noms)), t)

    def test_recrue_absente_des_hausses(self):
        E = dv.etat_initial(ligue())
        for j in E["joueurs"].values():
            j["age0"] = 34.9 if j["pos"] == "WR" else 25.0
        E, rap = avancer(E, 1)
        partis = {m["id"] for m in rap[0]["retirements"]}
        self.assertTrue(partis)
        self.assertFalse(partis & {x["id"] for x in rap[0]["risers"] + rap[0]["fallers"]})
        self.assertTrue(all(dv.resume_joueur(E, pid)["rookie"]["week"] == 1 for pid in partis))

    def test_deterministe(self):
        a, _ = avancer(dv.etat_initial(ligue()), 20)
        b, _ = avancer(dv.etat_initial(ligue()), 20)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
