"""Audit (audit_moteur.py) : une semaine est contrôlée avec les bornes du garde-fou en vigueur quand elle a été
produite (progression.guard_bounds), pas avec celles d'aujourd'hui ; idée 6 : le film de scouting et ce que la défense
en sait. Quelques millisecondes :

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import json
import os
import tempfile
import unittest

import audit_moteur as audit
from moteur import developpement as dev
from moteur import scouting as sc


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


class FilmDeScouting(unittest.TestCase):
    """Idée 6 : scouting_next_week.json dans ses bornes, play.scout.def.film cohérent avec le rapport d'avant-match."""

    def film(self):
        f = sc.film_vide()
        obs = [sc.observation(1, 10, 35, "I_FORM", "21", "RUN", "INSIDE_RUN", "inside")] * 5
        sc.film_match(f, "CTX", "VEC", obs, (3, 2))
        return sc.film_suivant(None, f)

    def bloquants_film(self, film, ref=None):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "scouting_next_week.json"), "w") as fh:
                json.dump(film, fh)
            w = {"teams": {"CTX": {}, "VEC": {}},
                 "scouting_next_week": ref or {"file": "scouting_next_week.json", "weeks": film.get("semaines")}}
            A = audit.Audit()
            audit.check_film(A, "w", d, w)
        return [m for lvl, *_, m in A.items if lvl == audit.BLOQUANT]

    def test_film_dans_ses_bornes(self):
        self.assertEqual(self.bloquants_film(self.film()), [])

    def test_film_hors_bornes(self):
        f = self.film()
        f["attaques"]["CTX"]["cles"]["dd|1"][1] = -3.0
        self.assertTrue(self.bloquants_film(f))
        f = self.film()
        f["defenses"]["ZZZ"] = {"matchs": 1.0, "key": 1.0, "juste": 1.0}
        self.assertTrue(self.bloquants_film(f))
        self.assertTrue(self.bloquants_film(self.film(), {"file": "scouting_next_week.json", "weeks": 7}))

    def test_lecture_sur_le_film(self):
        def feed(film, mem=True):
            g = {"scout_film": {"home": {"games": 12, "own": 1}}}
            if mem:
                g["scout_memory"] = {"film": sc.FILM_VERSION}
            return {"game": g, "plays": [{"seq": 4, "scout": {"version": "scouting-2",
                                                               "def": {"team": "home", "film": film}}}]}
        def n(fd):
            A = audit.Audit()
            audit.check_scout(A, "w", {"id": "g"}, fd)
            return A.counts[audit.BLOQUANT]
        self.assertEqual(n(feed({"games": 12, "own": 1, "part": 0.8})), 0)
        self.assertEqual(n(feed({"games": 12, "own": 1, "part": 0.8}, mem=False)), 2)
        self.assertEqual(n(feed({"games": 12, "own": 14, "part": 0.8})), 1)
        self.assertEqual(n(feed({"games": 9, "own": 1, "part": 0.8})), 1)


if __name__ == "__main__":
    unittest.main()
