"""Tests du bloc F (moteur/course.py) : boîte, point d'attaque, duels, lecture du porteur, contact.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import statistics
import unittest

from moteur import course as rf


def joueur(i, pos, **r):
    return {"id": i, "pos": pos, "ratings": r}


def attaque(ol=75, te=75, porteur=None):
    bl = [joueur(p, p, run_block=ol, strength=ol) for p in ("LT", "LG", "C", "RG", "RT")]
    bl.append(joueur("TE", "TE", run_block=te, strength=te))
    return {"bloqueurs": bl, "porteur": porteur or joueur("RB1", "RB", speed=80, acceleration=80, elusiveness=80, power=80)}


def defense(dl=75, lb=75, s=75):
    d = [joueur("E1", "EDGE", strength=dl, tackling=dl), joueur("E2", "EDGE", strength=dl, tackling=dl),
         joueur("D1", "DT", strength=dl, tackling=dl), joueur("D2", "DT", strength=dl, tackling=dl)]
    d += [joueur(f"L{i}", "LB", strength=lb, tackling=lb, speed=lb) for i in (1, 2, 3)]
    d += [joueur(f"S{i}", "S", run_support=s, tackling=s, speed=s) for i in (1, 2)]
    d += [joueur(f"C{i}", "CB", tackling=70, speed=85) for i in (1, 2)]
    return {"defenseurs": d}


def moyenne(n=400, **kw):
    a, d = kw.pop("a", attaque()), kw.pop("d", defense())
    b, classe, front, rb1 = kw.get("b", 7), kw.get("classe", "inside"), kw.get("front"), kw.get("rb1")
    return statistics.mean(rf.courir("X", classe, a, d, b, 1, i, front=front, rb1=rb1)["delta"] for i in range(n))


class TestBoite(unittest.TestCase):
    def test_boite(self):
        self.assertEqual(rf.boite("4_3"), 7)
        self.assertEqual(rf.boite("4_3", "BOX_STACK"), 8)
        self.assertEqual(rf.boite("NICKEL"), 6)
        self.assertEqual(rf.boite("DIME"), 5)
        self.assertEqual(rf.boite("GOAL_LINE", "BOX_STACK", front="SHORT_YARDAGE"), 9)
        self.assertEqual(rf.boite("4_3", "BOX_STACK", "COVER_3_SKY", "BEAR"), 9)      # borné

    def test_plus_de_monde_moins_de_yards(self):
        ms = [moyenne(b=b) for b in (5, 6, 7, 8, 9)]
        self.assertTrue(all(a > b for a, b in zip(ms, ms[1:])), ms)
        self.assertLess(ms[0] - ms[-1], 4.0)                    # un effet, pas un mur


class TestDuels(unittest.TestCase):
    def test_lignes(self):
        # bonne ligne offensive contre faible ligne défensive : plus de yards (au-delà du niveau : relatif aux moyennes ;
        # ici les deux lignes sont homogènes, donc l'effet passe par le côté choisi et le bruit — on compare des
        # attaques où un seul joueur diffère)
        a = attaque()
        faible = attaque()
        faible["bloqueurs"][1]["ratings"] = {"run_block": 55, "strength": 55}           # LG faible
        mf = statistics.mean(rf.courir("X", "inside", faible, defense(), 7, 1, i)["delta"] for i in range(600))
        self.assertGreater(moyenne(n=600, a=a), mf - 0.6)
        # l'attaque choisit le côté où ses duels sont meilleurs : le côté du LG faible est évité le plus souvent
        cotes = [rf.courir("X", "inside", faible, defense(), 7, 1, i)["cote"] for i in range(600)]
        self.assertGreater(cotes.count("R"), 360)

    def test_front_contre_classe(self):
        self.assertLess(moyenne(front="BEAR", classe="inside"), moyenne(front="BEAR", classe="outside"))
        self.assertGreater(moyenne(front="NASCAR", classe="inside"), moyenne(classe="inside"))


class TestPorteur(unittest.TestCase):
    def test_rb2_moins_bon(self):
        rb1 = {"speed": 88, "acceleration": 88, "elusiveness": 88, "power": 88}
        rb2 = joueur("RB2", "RB", speed=74, acceleration=74, elusiveness=74, power=74)
        self.assertLess(moyenne(a=attaque(porteur=rb2), rb1=rb1), moyenne(rb1=None) + 0.0)

    def test_vision(self):
        # trou fermé : plus de vision -> plus de cutbacks
        def coupes(v):
            p = joueur("RB", "RB", speed=80, acceleration=v, elusiveness=v, power=80)
            res = [rf.courir("X", "inside", attaque(porteur=p), defense(dl=80, lb=80), 9, 2, i) for i in range(800)]
            fermes = [r for r in res if r["trou"] == "ferme"]
            return sum(r["lecture"] == "cutback" for r in fermes) / max(1, len(fermes))
        self.assertGreater(coupes(92), coupes(66) + 0.10)

    def test_plaqueur(self):
        res = [rf.courir("X", "inside", attaque(), defense(), 8, 3, i) for i in range(300)]
        for r in res:
            self.assertIn(r["plaqueur"], {j["id"] for j in defense()["defenseurs"]})
            if r["lecture"] == "bloque":
                self.assertEqual(r["contact"], "ligne")
            if r["trou"] == "ouvert":
                self.assertIn(r["plaqueur"], ("S1", "S2", "C1", "C2"))


class TestDeterminisme(unittest.TestCase):
    def test_meme_graine(self):
        self.assertEqual(rf.courir("X", "gap", attaque(), defense(), 7, 5, 9),
                         rf.courir("X", "gap", attaque(), defense(), 7, 5, 9))

    def test_bornes_et_arrondi(self):
        for i in range(300):
            r = rf.courir("X", "outside", attaque(), defense(), 9, 6, i)
            self.assertLessEqual(abs(r["delta"]), rf.BORNE)
        # arrondi sans biais
        self.assertAlmostEqual(statistics.mean(rf.entier(0.3, 1, i) for i in range(4000)), 0.3, delta=0.03)


if __name__ == "__main__":
    unittest.main()
