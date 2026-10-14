"""Tests du temps d'écran de la retransmission (moteur/ecran.py) et de la chronologie du serveur qui le lit.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import unittest

from moteur import ecran as ec


def jeu(seq, q, c0, c1, runoff=0, t="run", timeout=None, offense="home", score=(0, 0), result="run", **kw):
    p = {"seq": seq, "quarter": q, "clock_start": c0, "clock_end": c1, "offense": offense, "result": result,
         "call": {"type": t}, "clock": {"runoff": runoff, "timeout": timeout, "timeouts": {"home": 3, "away": 3}},
         "after": {"score": {"home": score[0], "away": score[1]}, "status": "live"}}
    p.update(kw)
    return p


class TestChronologie(unittest.TestCase):
    def test_horloge_qui_tourne(self):
        # action 1 : 5 s de jeu puis 36 s avant le snap suivant ; action 2 : l'horloge part de 859 et descend à 823
        C = ec.chronologie([jeu(1, 1, 900, 859, runoff=36), jeu(2, 1, 859, 850, runoff=0, t="pass", result="incomplete")])
        self.assertEqual((C[0]["pt"], C[1]["c0"], C[1]["pc"]), (5, 895, [40, 4]))
        self.assertEqual(C[1]["pt"], 9)
        self.assertAlmostEqual(C[1]["pre"], ec.AVANT_MIN + 36 / ec.VITESSE, places=2)

    def test_horloge_arretee_rythme(self):
        # passe incomplète : l'horloge ne tourne pas avant le snap, le chrono au rythme de l'équipe
        normal = ec.chronologie([jeu(1, 1, 600, 594, result="incomplete"), jeu(2, 1, 594, 590)])[1]
        self.assertEqual((normal["c0"], normal["pc"]), (594, [40, 40 - ec.UTILISE_ARRETE["normal"]]))
        presse = ec.chronologie([jeu(1, 4, 90, 84, result="incomplete", score=(0, 7)),
                                 jeu(2, 4, 84, 80, score=(0, 7))])[1]
        self.assertEqual(presse["pc"], [40, 40 - ec.UTILISE_ARRETE["presse"]])
        tue = ec.chronologie([jeu(1, 4, 200, 194, result="incomplete", score=(14, 0)),
                              jeu(2, 4, 194, 190, score=(14, 0))])[1]
        self.assertEqual(tue["pc"], [40, 40 - ec.UTILISE_ARRETE["tue"]])
        self.assertLess(presse["pre"], normal["pre"])
        self.assertLess(normal["pre"], tue["pre"])

    def test_temps_mort(self):
        C = ec.chronologie([jeu(1, 4, 100, 95, timeout="away"), jeu(2, 4, 95, 90)])
        self.assertEqual((C[1]["to"], C[1]["pc"][0]), ("away", ec.CHRONO_COURT))
        self.assertGreaterEqual(C[1]["pre"], ec.AVANT_MIN + ec.TEMPS_MORT)

    def test_speciales_et_score(self):
        C = ec.chronologie([jeu(1, 1, 300, 290, result="touchdown"),
                            jeu(2, 1, 290, 290, t="extra_point", result="pat_good", conversion={"choice": "extra_point"}),
                            jeu(3, 1, 290, 290, t="kickoff", result="kickoff", kick_return={"touchback": False, "return": 36})])
        self.assertEqual(C[0]["post"], ec.APRES_SCORE)
        self.assertIsNone(C[1]["pc"])
        self.assertIsNone(C[2]["pc"])
        self.assertGreater(C[2]["act"], ec.ACTION["kickoff"] * ec.FACTEUR)

    def test_nouveau_quart(self):
        C = ec.chronologie([jeu(1, 1, 5, 0, runoff=3), jeu(2, 2, 900, 894)])
        self.assertEqual((C[1]["c0"], C[1]["pc"][0]), (900, ec.CHRONO_COURT))

    def test_somme(self):
        C = ec.chronologie([jeu(i, 1, 900 - 10 * i, 890 - 10 * i, runoff=5) for i in range(20)])
        self.assertTrue(all(abs(c["sec"] - c["pre"] - c["act"] - c["post"]) < 0.02 for c in C))


class TestServeur(unittest.TestCase):
    def test_play_ends(self):
        import serveur
        P = [{"show": {"sec": 4.0}, "after": {"status": "live"}, "clock_end": 10},
             {"show": {"sec": 5.5}, "after": {"status": "live"}, "clock_end": 0},          # fin du Q1 : pause
             {"after": {"status": "live"}, "clock_end": 800}]                            # sans show : PLAY_SEC
        self.assertEqual(serveur.play_ends(P), [4.0, 9.5, 9.5 + serveur.BREAK_SEC["q"] + serveur.PLAY_SEC])


if __name__ == "__main__":
    unittest.main()
