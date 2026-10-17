"""Tests du temps d'écran de la retransmission (moteur/ecran.py) et de la chronologie du serveur qui le lit.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import unittest

from moteur import ecran as ec


def jeu(seq, q, c0, c1, runoff=0, t="run", timeout=None, offense="home", score=(0, 0), result="run", clock=None, **kw):
    p = {"seq": seq, "quarter": q, "clock_start": c0, "clock_end": c1, "offense": offense, "result": result,
         "call": {"type": t}, "clock": clock or {"runoff": runoff, "stop": None, "timeout": timeout,
                                                 "timeouts": {"home": 3, "away": 3}},
         "after": {"score": {"home": score[0], "away": score[1]}, "status": "live"}}
    p.update(kw)
    return p


class TestChronologie(unittest.TestCase):
    def test_horloge_qui_tourne(self):
        # action 1 : 5 s de jeu puis 3 s de chrono (7 restantes au snap) ; action 2 : l'horloge part de 235, descend à 232
        C = ec.chronologie([jeu(1, 1, 240, 232, runoff=3), jeu(2, 1, 232, 226, t="pass", result="incomplete")])
        self.assertEqual((C[0]["pt"], C[1]["c0"], C[1]["pc"]), (5, 235, [10, 7]))
        self.assertAlmostEqual(C[1]["pre"], max(ec.AVANT_MIN, 3 / ec.VITESSE), places=2)
        self.assertEqual(C[1]["pt"], 6)

    def test_rythmes(self):
        # hurry-up : 0 s utilisée (10 restantes) ; tuer l'horloge : 10 (0 restante) — plus long avant le snap
        h = ec.chronologie([jeu(1, 2, 100, 95, runoff=0), jeu(2, 2, 95, 90)])[1]
        t = ec.chronologie([jeu(1, 4, 100, 85, runoff=10), jeu(2, 4, 85, 80)])[1]
        self.assertEqual((h["pc"], t["pc"]), ([10, 10], [10, 0]))
        self.assertLess(h["pre"], t["pre"])

    def test_horloge_arretee_rythme(self):
        # passe incomplète : l'horloge ne tourne pas avant le snap, le chrono au rythme de l'équipe
        normal = ec.chronologie([jeu(1, 1, 200, 194, result="incomplete", clock={"runoff": 0, "stop": "passe incomplète"}),
                                 jeu(2, 1, 194, 190)])[1]
        self.assertEqual((normal["c0"], normal["pc"]), (194, [10, 10 - ec.UTILISE_ARRETE["normal"]]))
        presse = ec.chronologie([jeu(1, 4, 90, 84, result="incomplete", score=(0, 7), clock={"runoff": 0, "stop": "x"}),
                                 jeu(2, 4, 84, 80, score=(0, 7))])[1]
        self.assertEqual(presse["pc"], [10, 10 - ec.UTILISE_ARRETE["presse"]])
        tue = ec.chronologie([jeu(1, 4, 100, 94, result="incomplete", score=(14, 0), clock={"runoff": 0, "stop": "x"}),
                              jeu(2, 4, 94, 90, score=(14, 0))])[1]
        self.assertEqual(tue["pc"], [10, 10 - ec.UTILISE_ARRETE["tue"]])
        self.assertLessEqual(presse["pre"], normal["pre"])
        self.assertLess(normal["pre"], tue["pre"])

    def test_temps_mort(self):
        C = ec.chronologie([jeu(1, 3, 100, 95, clock={"runoff": 0, "stop": "temps mort", "timeout": "away"}),
                            jeu(2, 3, 95, 90)])
        self.assertEqual((C[1]["to"], C[1]["tw"], C[1]["tl"], C[1]["pc"][0]), ("away", ec.TEMPS_MORT, 15, 10))
        self.assertAlmostEqual(C[1]["pre"], ec.TEMPS_MORT + max(ec.AVANT_MIN, ec.UTILISE_ARRETE["normal"] / ec.VITESSE), places=2)

    def test_speciales_et_score(self):
        C = ec.chronologie([jeu(1, 1, 200, 190, result="touchdown", clock={"runoff": 0, "stop": "changement de possession"}),
                            jeu(2, 1, 190, 190, t="extra_point", result="pat_good", conversion={"choice": "extra_point"}),
                            jeu(3, 1, 190, 190, t="kickoff", result="kickoff", kick_return={"touchback": False, "return": 36})])
        self.assertEqual(C[0]["post"], ec.APRES_SCORE)
        self.assertIsNone(C[1]["pc"])
        self.assertIsNone(C[2]["pc"])
        self.assertGreater(C[2]["act"], ec.ACTION["kickoff"])

    def test_nouveau_quart(self):
        C = ec.chronologie([jeu(1, 1, 5, 0, runoff=3), jeu(2, 2, 240, 234)])
        self.assertEqual((C[1]["c0"], C[1]["pc"]), (240, [10, 10 - ec.UTILISE_ARRETE["normal"]]))

    def test_somme_et_budget(self):
        C = ec.chronologie([jeu(i, 1, 240 - 10 * i, 230 - 10 * i, runoff=5) for i in range(20)])
        self.assertTrue(all(abs(c["sec"] - c["pre"] - c["act"] - c["post"]) < 0.02 for c in C))
        self.assertTrue(all(c["pc"] is None or 0 <= c["pc"][1] <= c["pc"][0] == ec.CHRONO for c in C))
        # 300 actions horloge arrêtée : le budget raccourcit les temps souples
        P = [jeu(i, 1 + i // 75, 240, 236, result="incomplete", clock={"runoff": 0, "stop": "x"}) for i in range(300)]
        self.assertLessEqual(sum(c["sec"] for c in ec.chronologie(P)) + ec.pauses(P), ec.BUDGET + 1)


try:                                     # le calcul de la semaine n'installe pas fastapi (requirements-semaine.txt)
    import fastapi                       # noqa: F401
except ImportError:
    fastapi = None


@unittest.skipUnless(fastapi is not None, "serveur.py non importable (fastapi absent)")
class TestServeur(unittest.TestCase):
    def test_play_ends(self):
        import serveur
        P = [{"show": {"sec": 4.0}, "after": {"status": "live"}, "clock_end": 10},
             {"show": {"sec": 5.5}, "after": {"status": "live"}, "clock_end": 0},          # fin du Q1 : pause
             {"after": {"status": "live"}, "clock_end": 800}]                            # sans show : PLAY_SEC
        self.assertEqual(serveur.play_ends(P), [4.0, 9.5, 9.5 + serveur.BREAK_SEC["q"] + serveur.PLAY_SEC])


if __name__ == "__main__":
    unittest.main()
