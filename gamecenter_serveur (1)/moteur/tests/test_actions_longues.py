"""Actions longues et retours d'interception (moteur/actions_longues.py, README section 85).

    python -m unittest moteur.tests.test_actions_longues        (depuis « gamecenter_serveur (1) »)
"""
import random
import unittest

from moteur import actions_longues as AL

RAPIDE, LENT = {"speed": 95, "acceleration": 94, "elusiveness": 93}, {"speed": 70, "acceleration": 70, "elusiveness": 70}
DEF = [{"speed": 82}] * 5


def _taux(kind, gain, porteur, defense=DEF, n=20_000, graine=1):
    rng = random.Random(graine)
    plus = [AL.ajout(kind, gain, porteur, defense, rng)[0] for _ in range(n)]
    return sum(1 for p in plus if p > 0) / n, plus


class Ajout(unittest.TestCase):
    def test_seuils(self):
        rng = random.Random(3)
        self.assertTrue(all(AL.ajout("run", AL.SEUIL_COURSE - 1, RAPIDE, DEF, rng) == (0, None) for _ in range(2000)))
        self.assertTrue(all(AL.ajout("pass", AL.SEUIL_YAC - 1, RAPIDE, DEF, rng) == (0, None) for _ in range(2000)))

    def test_vitesse_compte(self):
        vite, _ = _taux("run", 10, RAPIDE)
        lent, _ = _taux("run", 10, LENT)
        moyen, plus = _taux("run", 10, {})
        self.assertGreater(vite, moyen)
        self.assertGreater(moyen, lent)
        self.assertAlmostEqual(moyen, AL.P_COURSE, delta=0.01)
        longs = [p for p in plus if p > 0]
        self.assertAlmostEqual(sum(longs) / len(longs), AL.MOY_COURSE, delta=1.5)
        self.assertGreater(max(longs), 40)                    # la queue existe

    def test_passe_profonde_et_yac(self):
        prof, _ = _taux("pass", AL.SEUIL_PROFOND, {})
        yac, _ = _taux("pass", AL.SEUIL_YAC, {})
        self.assertAlmostEqual(prof, AL.P_PROFOND, delta=0.012)
        self.assertAlmostEqual(yac, AL.P_YAC, delta=0.006)

    def test_rabot(self):
        rng = random.Random(5)
        lo, hi = AL.RABOT["run"]
        self.assertEqual({AL.rabot("run", g, 1.0, rng) for g in range(lo, hi + 1)}, {-1})
        self.assertEqual({AL.rabot("run", g, 1.0, rng) for g in (lo - 1, hi + 1, 30)}, {0})
        self.assertEqual({AL.rabot("run", 5, 0.0, rng) for _ in range(100)}, {0})
        moy = sum(AL.rabot("pass", 8, 1.4, rng) for _ in range(20_000)) / 20_000
        self.assertAlmostEqual(moy, -1.4, delta=0.03)                      # p > 1 : 1 ou 2 yards

    def test_flux_dedie(self):
        a = [AL.tirer_ajout(77, n, "run", 12, RAPIDE, DEF, 0.1) for n in range(200)]
        b = [AL.tirer_ajout(77, n, "run", 12, RAPIDE, DEF, 0.1) for n in range(200)]
        self.assertEqual(a, b)                                # même graine, même n° d'action -> même tirage


class Interception(unittest.TestCase):
    def test_retour(self):
        rng = random.Random(9)
        R = [AL.retour_interception(30, 12, {"speed": 85}, [{"speed": 80}] * 6, rng) for _ in range(20_000)]
        for r in R:
            self.assertEqual(r["point"], 42)
            self.assertEqual(r["fin"], 0 if r["td"] else r["point"] - r["retour"])
            self.assertGreaterEqual(r["retour"], 0)
        moy = sum(r["retour"] for r in R) / len(R)
        six = sum(r["td"] for r in R) / len(R)
        self.assertTrue(6 < moy < 20, moy)
        self.assertTrue(0.005 < six < 0.15, six)              # pick-six possibles, pas systématiques
        self.assertTrue(any(r["retour"] >= 30 and not r["td"] for r in R))

    def test_plus_pres_plus_de_pick_six(self):
        def six(ligne):
            rng = random.Random(4)
            return sum(AL.retour_interception(ligne, 8, {}, [], rng)["td"] for _ in range(10_000))
        self.assertGreater(six(10), six(60))                 # interception près de l'en-but de l'attaque

    def test_dans_l_en_but(self):
        rng = random.Random(2)
        R = [AL.retour_interception(90, 15, {}, [], rng) for _ in range(2000)]
        self.assertTrue(any(r["touchback"] and r["fin"] == 100 and r["retour"] == 0 for r in R))
        self.assertTrue(all(r["fin"] <= 100 for r in R))

    def test_flux_dedie(self):
        self.assertEqual([AL.tirer_retour(5, n, 40, 10, {}, []) for n in range(50)],
                         [AL.tirer_retour(5, n, 40, 10, {}, []) for n in range(50)])


class FinDePeriode(unittest.TestCase):
    def test_pick_six_a_la_mi_temps(self):
        """Comme un touchdown ordinaire : la transformation, dans la même période, horloge à 0, termine la mi-temps."""
        P = [{"quarter": 2, "result": "interception", "int_return": {"td": True}, "try_follows": True,
              "after": {"status": "half"}, "clock_end": 0},
             {"quarter": 3, "result": "pat_good", "clock_start": 240, "clock_end": 240, "after": {"status": "live"}},
             {"quarter": 3, "result": "kickoff", "after": {"status": "live"}}]
        self.assertEqual(AL.fin_de_periode(P), 1)
        self.assertEqual([(p["quarter"], p["after"]["status"]) for p in P], [(2, "live"), (2, "half"), (3, "live")])
        self.assertEqual((P[1]["clock_start"], P[1]["clock_end"]), (0, 0))
        self.assertEqual(AL.fin_de_periode(P), 0)                    # déjà en ordre : rien

    def test_sans_pick_six(self):
        P = [{"quarter": 2, "result": "touchdown", "after": {"status": "live"}},
             {"quarter": 2, "result": "pat_good", "after": {"status": "half"}}]
        self.assertEqual(AL.fin_de_periode(P), 0)


if __name__ == "__main__":
    unittest.main()
