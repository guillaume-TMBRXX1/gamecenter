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
        # action 1 : 5 s de jeu puis 7 s avant le snap suivant ; action 2 : l'horloge part de 235 et descend à 228
        C = ec.chronologie([jeu(1, 1, 240, 228, runoff=7), jeu(2, 1, 228, 222, t="pass", result="incomplete")])
        self.assertEqual((C[0]["pt"], C[1]["c0"], C[1]["pc"]), (5, 235, [10, 3]))
        self.assertEqual(C[1]["pre"], 7)                                   # temps réel : 7 s d'écran
        self.assertEqual(C[0]["post"], 1.0 * 0 + max(0, 5 - C[0]["act"]))  # pas de pause, le chrono repart aussitôt
        self.assertEqual(C[1]["pt"], 6)

    def test_une_seconde_par_seconde(self):
        # horloge qui tourne d'un snap à l'autre : l'écran dure exactement le temps de match écoulé
        P = [jeu(i, 1, 240 - 12 * i, 228 - 12 * i, runoff=7) for i in range(15)]
        C = ec.chronologie(P)
        for i in range(1, 14):
            self.assertAlmostEqual(C[i]["act"] + C[i]["post"] + C[i + 1]["pre"], 12, places=1)

    def test_horloge_arretee_rythme(self):
        # passe incomplète : l'horloge ne tourne pas avant le snap, le chrono au rythme de l'équipe
        normal = ec.chronologie([jeu(1, 1, 200, 194, result="incomplete"), jeu(2, 1, 194, 190)])[1]
        self.assertEqual((normal["c0"], normal["pc"]), (194, [10, 10 - ec.UTILISE_ARRETE["normal"]]))
        presse = ec.chronologie([jeu(1, 4, 90, 84, result="incomplete", score=(0, 7)),
                                 jeu(2, 4, 84, 80, score=(0, 7))])[1]
        self.assertEqual(presse["pc"], [10, 10 - ec.UTILISE_ARRETE["presse"]])
        tue = ec.chronologie([jeu(1, 4, 100, 94, result="incomplete", score=(14, 0)),
                              jeu(2, 4, 94, 90, score=(14, 0))])[1]
        self.assertEqual(tue["pc"], [10, 10 - ec.UTILISE_ARRETE["tue"]])
        self.assertLess(presse["pre"], normal["pre"])
        self.assertLess(normal["pre"], tue["pre"])

    def test_temps_mort(self):
        C = ec.chronologie([jeu(1, 3, 100, 95, timeout="away"), jeu(2, 3, 95, 90)])
        self.assertEqual((C[1]["to"], C[1]["tw"], C[1]["pc"][0]), ("away", 15, 10))
        self.assertEqual(C[1]["pre"], 15 + ec.UTILISE_ARRETE["normal"])
        self.assertEqual(C[0]["post"], ec.APRES)

    def test_speciales_et_score(self):
        C = ec.chronologie([jeu(1, 1, 200, 190, result="touchdown"),
                            jeu(2, 1, 190, 190, t="extra_point", result="pat_good", conversion={"choice": "extra_point"}),
                            jeu(3, 1, 190, 190, t="kickoff", result="kickoff", kick_return={"touchback": False, "return": 36})])
        self.assertEqual(C[0]["post"], ec.APRES_SCORE + max(0, 10 - C[0]["act"]))
        self.assertIsNone(C[1]["pc"])
        self.assertIsNone(C[2]["pc"])
        self.assertGreater(C[2]["act"], ec.ACTION["kickoff"])

    def test_nouveau_quart(self):
        C = ec.chronologie([jeu(1, 1, 5, 0, runoff=3), jeu(2, 2, 240, 234)])
        self.assertEqual((C[1]["c0"], C[1]["pc"]), (240, [10, 10 - ec.UTILISE_ARRETE["normal"]]))
        self.assertEqual(C[0]["post"], ec.APRES)                       # fin du quart : l'horloge ne tourne plus

    def test_somme(self):
        C = ec.chronologie([jeu(i, 1, 240 - 10 * i, 230 - 10 * i, runoff=5) for i in range(20)])
        self.assertTrue(all(abs(c["sec"] - c["pre"] - c["act"] - c["post"]) < 0.02 for c in C))
        self.assertTrue(all(c["pc"] is None or 0 <= c["pc"][1] <= c["pc"][0] == ec.CHRONO for c in C))


class TestServeur(unittest.TestCase):
    def test_play_ends(self):
        import serveur
        P = [{"show": {"sec": 4.0}, "after": {"status": "live"}, "clock_end": 10},
             {"show": {"sec": 5.5}, "after": {"status": "live"}, "clock_end": 0},          # fin du Q1 : pause
             {"after": {"status": "live"}, "clock_end": 800}]                            # sans show : PLAY_SEC
        self.assertEqual(serveur.play_ends(P), [4.0, 9.5, 9.5 + serveur.BREAK_SEC["q"] + serveur.PLAY_SEC])


if __name__ == "__main__":
    unittest.main()
