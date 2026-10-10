"""Audit (audit_moteur.py) : une semaine est contrôlée avec les bornes du garde-fou en vigueur quand elle a été
produite (progression.guard_bounds), pas avec celles d'aujourd'hui. Quelques millisecondes :

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import unittest

import audit_moteur as audit
from moteur import developpement as dev


def semaine(units, strength, bounds=None):
    rap = {"team_units": {"CTX": units}, "team_strength": {"CTX": strength}}
    if bounds is not None:
        rap["guard_bounds"] = bounds
    return {"teams": {}, "players_next_week": {"semaines": 1, "joueurs": {}}, "progression": rap}


def bloquants(w):
    A = audit.Audit()
    audit.check_progression(A, "w", w)
    return [m for lvl, *_, m in A.items if lvl == audit.BLOQUANT]


class BornesDuGardeFou(unittest.TestCase):
    def test_semaine_d_avant_le_0910_gardee(self):
        # semaine du 05/10 : produite à ± 0,75 / 0,2, sans guard_bounds -> pas refusée après le resserrement
        self.assertEqual(bloquants(semaine({"run_off": 0.7}, -0.2)), [])

    def test_semaine_d_avant_le_0910_hors_de_ses_bornes(self):
        self.assertEqual(len(bloquants(semaine({"run_off": 0.8}, -0.25))), 2)

    def test_nouvelle_semaine_bornes_actuelles(self):
        b = {"unit": dev.ECART_EQUIPE_MAX, "force": dev.FORCE_EQUIPE_MAX}
        self.assertEqual(bloquants(semaine({"run_off": 0.5}, 0.15, b)), [])
        self.assertEqual(len(bloquants(semaine({"run_off": 0.7}, -0.2, b))), 2)


if __name__ == "__main__":
    unittest.main()
