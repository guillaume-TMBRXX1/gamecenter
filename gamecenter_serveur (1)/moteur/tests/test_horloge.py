"""Tests de l'horloge réelle (moteur/horloge.py) : temps entre les actions, arrêts, temps morts, genou, spike.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import unittest

from moteur import horloge as hz


def action(**kw):
    a = {"kind": "OFF", "play_type": "RUN", "outcome": "RUN", "yards_gained": 4, "down": 1, "distance": 10,
         "yard_line": 40, "quarter": 1, "offense": "AAA", "defense": "BBB", "play_id": "X"}
    a.update(kw)
    return a


def etat(quart=900):
    return hz.EtatHorloge(("AAA", "BBB"), quart)


class TestArrets(unittest.TestCase):
    def test_passe_incomplete(self):
        r = hz.apres_action(etat(), action(play_type="PASS", outcome="PASS_INCOMPLETE", yards_gained=0), 600, 0)
        self.assertEqual((r["runoff"], r["stop"]), (0, "passe incomplète"))

    def test_changement_de_possession(self):
        for a in (action(outcome="INTERCEPTION", play_type="PASS"), action(outcome="FUMBLE"),
                  action(yards_gained=60, yard_line=40),                       # touchdown
                  action(down=4, distance=3, yards_gained=1),                  # 4e essai manqué
                  action(kind="PUNT", play_type="PUNT", outcome="PUNT"), action(kind="FG", play_type="FIELD_GOAL")):
            r = hz.apres_action(etat(), a, 600, 0)
            self.assertEqual((r["runoff"], r["stop"]), (0, "changement de possession"), a)

    def test_horloge_qui_tourne(self):
        # Q1, course dans le terrain : 36 s (± sortie du terrain, tirage du flux dédié)
        vus = {hz.apres_action(etat(), action(), 600, 0, graine=1, numero=n)["runoff"] for n in range(200)}
        self.assertIn(36, vus)
        self.assertTrue(all(0 < v <= 36 for v in vus))

    def test_tempo(self):
        r = lambda **k: hz.apres_action(etat(), action(), 600, 0, graine=None, numero=0, **k)
        # sans graine : flux non reproductible — on compare les modes sur des actions sans sortie possible
        a = action(outcome="SACK", play_type="PASS", yards_gained=-6)
        h = hz.apres_action(etat(), a, 600, 0, mode="hurry")["runoff"]
        n = hz.apres_action(etat(), a, 600, 0)["runoff"]
        c = hz.apres_action(etat(), a, 600, 0, mode="clock")["runoff"]
        self.assertLess(h, n)
        self.assertLess(n, c)
        lent = hz.apres_action(etat(), a, 600, 0, tempo=1)["runoff"]
        rapide = hz.apres_action(etat(), a, 600, 0, tempo=-1)["runoff"]
        self.assertLess(rapide, n)
        self.assertGreater(lent, n)

    def test_echelle(self):
        a = action(outcome="SACK", play_type="PASS", yards_gained=-6)
        self.assertEqual(hz.apres_action(etat(900), a, 600, 0)["runoff"], 36)
        self.assertEqual(hz.apres_action(etat(180), a, 120, 0)["runoff"], 7)

    def test_fin_du_quart(self):
        a = action(outcome="SACK", play_type="PASS", yards_gained=-6)
        self.assertEqual(hz.apres_action(etat(), a, 12, 0)["runoff"], 12)
        self.assertEqual(hz.apres_action(etat(), a, 0, 0)["stop"], "fin du quart-temps")

    def test_avertissement_des_2_minutes(self):
        a = action(quarter=4, outcome="SACK", play_type="PASS", yards_gained=-6)
        # l'action passe sous 2:00 : arrêt après l'action
        r = hz.apres_action(etat(), a, 115, 0, secondes_avant=125)
        self.assertEqual((r["runoff"], r["stop"]), (0, "avertissement des 2 minutes"))
        # le huddle passerait sous 2:00 : l'horloge s'arrête à 2:00
        r = hz.apres_action(etat(), a, 135, 0, secondes_avant=141)
        self.assertEqual((r["runoff"], r["stop"]), (15, "avertissement des 2 minutes"))
        # Q3 : pas d'avertissement
        r = hz.apres_action(etat(), action(quarter=3, outcome="SACK", play_type="PASS"), 115, 0, secondes_avant=125)
        self.assertNotEqual(r["stop"], "avertissement des 2 minutes")

    def test_sortie_du_terrain(self):
        # Q4, 1:30 : une sortie arrête l'horloge ; Q1 : elle ne l'arrête qu'un moment
        st4 = {hz.apres_action(etat(), action(quarter=4, play_type="PASS", outcome="PASS_COMPLETE"), 90, 5,
                               graine=7, numero=n)["stop"] for n in range(300)}
        self.assertIn("sortie du terrain", st4)
        r1 = [hz.apres_action(etat(), action(play_type="PASS", outcome="PASS_COMPLETE"), 600, 0, graine=7, numero=n)
              for n in range(300)]
        sorties = [r for r in r1 if r["oob"]]
        self.assertTrue(sorties)
        self.assertTrue(all(0 < r["runoff"] < 36 for r in sorties))

    def test_deterministe(self):
        a = action(play_type="PASS", outcome="PASS_COMPLETE")
        self.assertEqual([hz.apres_action(etat(), a, 600, 0, graine=3, numero=n) for n in range(50)],
                         [hz.apres_action(etat(), a, 600, 0, graine=3, numero=n) for n in range(50)])


class TestTempsMorts(unittest.TestCase):
    def test_defense_menee_en_fin_de_match(self):
        e = etat()
        a = action(quarter=4, outcome="SACK", play_type="PASS", yards_gained=-3)      # l'attaque mène de 4
        poses = [hz.apres_action(e, a, 100 - 5 * i, 4)["timeout"] for i in range(5)]
        self.assertEqual(poses[:3], ["BBB"] * 3)                       # trois temps morts, puis plus rien
        self.assertEqual(poses[3:], [None, None])
        self.assertEqual(e.temps_morts["BBB"], 0)

    def test_attaque_menee(self):
        e = etat()
        r = hz.apres_action(e, action(quarter=4, outcome="SACK", play_type="PASS", yards_gained=-3), 100, -3)
        self.assertEqual(r["timeout"], "AAA")

    def test_pas_de_temps_mort_au_q3_ni_ecart_trop_grand(self):
        a = action(quarter=3, outcome="SACK", play_type="PASS", yards_gained=-3)
        self.assertIsNone(hz.apres_action(etat(), a, 100, 4)["timeout"])
        a = action(quarter=4, outcome="SACK", play_type="PASS", yards_gained=-3)
        self.assertIsNone(hz.apres_action(etat(), a, 100, 21)["timeout"])         # défense menée de 3 possessions

    def test_mi_temps(self):
        e = etat()
        e.temps_morts["AAA"] = 0
        e.suivre(3)
        self.assertEqual(e.temps_morts, {"AAA": 3, "BBB": 3})
        e.suivre(5)
        self.assertEqual(e.temps_morts, {"AAA": 2, "BBB": 2})


class TestGenouSpike(unittest.TestCase):
    def test_victory_formation(self):
        k = 1.0
        # 1er essai, mène, la défense n'a plus de temps mort : 3 genoux × (2 + 40) s
        self.assertTrue(hz.genou(4, 120, 1, 3, 70, 0, k))
        self.assertFalse(hz.genou(4, 130, 1, 3, 70, 0, k))
        # avec 3 temps morts adverses : seulement 3 × 2 s
        self.assertFalse(hz.genou(4, 40, 1, 3, 70, 3, k))
        self.assertTrue(hz.genou(4, 6, 1, 3, 70, 3, k))
        # menée : jamais (à égalité : seulement dans les 20 dernières secondes, voir test_genou_a_egalite) ;
        # 4e essai : jamais ; prolongation : jamais
        self.assertFalse(hz.genou(4, 20, 1, -1, 70, 0, k))
        self.assertFalse(hz.genou(4, 45, 1, 0, 70, 0, k))
        self.assertFalse(hz.genou(4, 20, 4, 3, 70, 0, k))
        self.assertFalse(hz.genou(5, 20, 1, 3, 70, 0, k))

    def test_genou_a_egalite(self):
        # Q4 à égalité, dans son camp, 15 s : genou ; trop de temps, trop près ou au 4e essai : on joue
        self.assertTrue(hz.genou(4, 15, 1, 0, 70, 1, 1.0))
        self.assertFalse(hz.genou(4, 40, 1, 0, 70, 1, 1.0))
        self.assertFalse(hz.genou(4, 15, 1, 0, 45, 1, 1.0))
        self.assertFalse(hz.genou(4, 15, 4, 0, 70, 1, 1.0))
        self.assertFalse(hz.genou(4, 15, 1, -3, 70, 1, 1.0))        # menée : jamais

    def test_genou_fin_de_q2(self):
        self.assertTrue(hz.genou(2, 20, 1, 0, 80, 3, 1.0))             # dans son camp, 20 s
        self.assertFalse(hz.genou(2, 20, 1, 0, 30, 3, 1.0))            # à portée : il joue (ou tire)
        self.assertFalse(hz.genou(2, 90, 1, 0, 80, 3, 1.0))
        self.assertFalse(hz.genou(2, 20, 4, 0, 96, 3, 1.0))            # 4e essai : jamais (ballon rendu)

    def test_spike(self):
        self.assertTrue(hz.spike(4, 40, 1, -3, 40, False, 0, 1.0))
        self.assertFalse(hz.spike(4, 40, 1, -3, 40, True, 0, 1.0))      # horloge déjà arrêtée
        self.assertFalse(hz.spike(4, 40, 1, -3, 40, False, 1, 1.0))     # il reste un temps mort
        self.assertFalse(hz.spike(4, 40, 2, -3, 40, False, 0, 1.0))     # pas sur 2e essai
        self.assertFalse(hz.spike(4, 40, 1, 7, 40, False, 0, 1.0))      # mène : il fait tourner l'horloge
        self.assertFalse(hz.spike(4, 90, 1, -3, 40, False, 0, 1.0))

    def test_avant_snap(self):
        e = etat()
        e.suivre(4)
        e.temps_morts["BBB"] = 0
        self.assertEqual(hz.avant_snap(e, 4, 60, 1, 7, 70, "AAA", "BBB"), "KNEEL")
        self.assertIsNone(hz.avant_snap(e, 1, 60, 1, 7, 70, "AAA", "BBB"))

    def test_genou_et_spike_font_ce_qu_ils_disent(self):
        e = etat()
        e.suivre(4)
        r = hz.apres_action(e, action(quarter=4, play_id="KNEEL", yards_gained=-1), 100, 7)
        self.assertEqual((r["runoff"], r["timeout"]), (0, "BBB"))         # la défense menée arrête l'horloge
        e.temps_morts["BBB"] = 0
        r = hz.apres_action(e, action(quarter=4, play_id="KNEEL", yards_gained=-1), 100, 7)
        self.assertEqual(r["runoff"], 40)
        r = hz.apres_action(e, action(quarter=4, play_id="SPIKE", play_type="PASS", outcome="PASS_INCOMPLETE",
                                      yards_gained=0), 30, -3)
        self.assertEqual((r["runoff"], r["stop"]), (0, "spike"))


class TestFireDrill(unittest.TestCase):
    def test_unite_de_field_goal(self):
        e = etat()
        e.suivre(2)
        e.temps_morts["AAA"] = 0
        a = action(quarter=2, outcome="SACK", play_type="PASS", yards_gained=-2, yard_line=72)   # 30 yards de l'en-but
        r = hz.apres_action(e, a, 25, 0)
        self.assertEqual((r["runoff"], r["stop"]), (22, "unité de field goal"))
        # trop peu de temps : la mi-temps arrive ; hors de portée : rien
        self.assertEqual(hz.apres_action(e, a, 15, 0)["runoff"], 15)
        loin = action(quarter=2, outcome="SACK", play_type="PASS", yards_gained=-2, yard_line=40)
        self.assertEqual(hz.apres_action(e, loin, 25, 0)["runoff"], 25)
        # Q4 : seulement si 3 points comptent
        e.suivre(4)
        e.temps_morts["AAA"] = 0
        a4 = dict(a, quarter=4)
        self.assertEqual(hz.apres_action(e, a4, 25, -2)["stop"], "unité de field goal")
        self.assertNotEqual(hz.apres_action(e, a4, 25, -7)["stop"], "unité de field goal")


class TestEquivalence(unittest.TestCase):
    def test_secondes_equivalentes(self):
        # sans temps entre les actions : identique ; avec : moins de secondes « du moteur d'avant »
        self.assertAlmostEqual(hz.secondes_equivalentes(90, 1.0, entre_moyen=0), 90)
        self.assertLess(hz.secondes_equivalentes(450, 1.0), 450)
        self.assertGreater(hz.secondes_equivalentes(450, 1.0), 60)


if __name__ == "__main__":
    unittest.main()
