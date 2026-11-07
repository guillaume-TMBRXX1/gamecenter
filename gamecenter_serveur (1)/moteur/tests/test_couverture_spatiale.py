"""Causal léger, bloc 3 : la couverture (moteur/couverture_spatiale.py) et son branchement au bloc A.

  Homme       un receveur rapide qui court bien ses routes se sépare plus qu'un receveur lent ; un meilleur défenseur
              le serre davantage ; la presse réduit la séparation d'une route courte
  Zone        séparation positive, plus grande pour un meilleur receveur à rôle égal
  Échelle     droite par famille / classe / groupe de rôle (RB et TE ont la leur, les autres rôles celle des WR)
  Hasard      flux dédié : mêmes graine, action et rôle -> même duel
  Bloc A      sans DUEL, le moteur d'avant (mêmes séparations) ; avec, le terme de duel vient du terrain

    python -m unittest moteur.tests.test_couverture_spatiale        (depuis « gamecenter_serveur (1) »)
"""
import random
import statistics
import unittest

from moteur import couverture_spatiale as CV
from moteur import reaction_defensive as RD

ELITE = {"speed": 93, "acceleration": 91, "route_running": 90}
MOYEN = {"speed": 78, "acceleration": 76, "route_running": 70}
CB = {"speed": 86, "coverage": 82}


def _moy(route, classe, ouv, rec, de, famille="homme", couverture="Cover 2", role="WR1", n=300):
    ds = [{"ratings": de}] * (1 if famille == "homme" else 3)
    return statistics.mean(CV.separation(role, route, classe, ouv, {"ratings": rec}, ds, famille, couverture, 3, k)[0]
                           for k in range(n))


class Homme(unittest.TestCase):
    def test_receveur_elite(self):
        for route, classe, ouv in (("OUT", "moyen", 1.3), ("CURL", "moyen", 1.4), ("POST", "profond", 2.1)):
            self.assertGreater(_moy(route, classe, ouv, ELITE, CB), _moy(route, classe, ouv, MOYEN, CB), route)

    def test_meilleur_defenseur(self):
        fort, faible = {"speed": 92, "coverage": 92}, {"speed": 78, "coverage": 68}
        self.assertLess(_moy("OUT", "moyen", 1.3, ELITE, fort), _moy("OUT", "moyen", 1.3, ELITE, faible))


class Zone(unittest.TestCase):
    def test_positive_et_selon_le_receveur(self):
        e = _moy("CURL", "moyen", 1.4, ELITE, CB, "zone", "Cover 3")
        m = _moy("CURL", "moyen", 1.4, MOYEN, CB, "zone", "Cover 3")
        self.assertGreater(m, 0.0)
        self.assertGreater(e, m)


class Echelle(unittest.TestCase):
    def test_droites(self):
        self.assertEqual(CV.en_pas(2.0, "zone", "moyen", "WR3"), CV.en_pas(2.0, "zone", "moyen", "WR1"))
        self.assertNotEqual(CV.en_pas(2.0, "zone", "court", "RB"), CV.en_pas(2.0, "zone", "court", "WR1"))
        self.assertGreater(CV.en_pas(4.0, "homme", "court", "WR1"), CV.en_pas(1.0, "homme", "court", "WR1"))


class Hasard(unittest.TestCase):
    def test_deterministe(self):
        a = CV.separation("WR2", "SLANT", "court", 1.0, {"ratings": ELITE}, [{"ratings": CB}], "homme", "Cover 1", 9, 4)
        b = CV.separation("WR2", "SLANT", "court", 1.0, {"ratings": ELITE}, [{"ratings": CB}], "homme", "Cover 1", 9, 4)
        self.assertEqual(a, b)


class BlocA(unittest.TestCase):
    def _etat(self, cle=None):
        lectures = [{"role": "WR1", "route": "OUT", "classe": "moyen", "niveau": "primaire", "ouverture": 1.3},
                    {"role": "TE", "route": "DRAG", "classe": "court", "niveau": "checkdown", "ouverture": 1.1}]
        rec = {"WR1": {"id": "W", "ratings": ELITE}, "TE": {"id": "T", "ratings": {"speed": 80, "route_running": 74}}}
        de = {"CB": [{"id": "C1", "ratings": CB}, {"id": "C2", "ratings": CB}], "S": [{"id": "S1", "ratings": CB}],
              "LB": [{"id": "L1", "ratings": {"speed": 80, "coverage": 75}}]}
        return RD.DefensiveReactionEngine().react("MAN", lectures, rec, de, 0.5, random.Random(5), **({"cle": cle} if cle else {}))

    def test_sans_duel_inchange(self):
        RD.DUEL = None
        a = self._etat().to_dict()
        b = self._etat(cle=(1, 2)).to_dict()           # sans DUEL, la clé ne change rien
        self.assertEqual(a, b)

    def test_avec_duel(self):
        vus = []

        def duel(**k):
            vus.append(k["role"])
            return 3.0
        RD.DUEL = duel
        try:
            e = self._etat(cle=(1, 2))
        finally:
            RD.DUEL = None
        self.assertEqual(sorted(vus), ["TE", "WR1"])
        self.assertEqual(e.receveurs["WR1"].statut, RD.LIBRE)


if __name__ == "__main__":
    unittest.main()


class Trace(unittest.TestCase):
    """Trajectoires, étape 6 : la trace du duel pour le dessin du site (play.geo.cov), sans rien changer au duel."""

    CAS = (("SLANT", "court", 1.2, "homme", "Cover 1"), ("GO", "profond", 2.4, "homme", "Cover 0"),
           ("CURL", "moyen", 1.8, "zone", "Cover 3"), ("POST", "profond", 2.6, "zone", "Cover 2"),
           ("OUT", "court", 1.4, "zone", "Cover 4"))

    def test_meme_duel(self):
        for route, classe, ouv, fam, cov in self.CAS:
            ds = [{"id": f"D{i}", "ratings": CB} for i in range(1 if fam == "homme" else 3)]
            for k in range(40):
                a = CV.separation("WR1", route, classe, ouv, {"ratings": ELITE}, ds, fam, cov, 7, k)
                b = CV.separation("WR1", route, classe, ouv, {"ratings": ELITE}, ds, fam, cov, 7, k, trace=True)
                self.assertEqual(a[0], b[0], (route, k))
                self.assertNotIn("trace", a[1])
                tr = b[1]["trace"]
                self.assertEqual(len(tr["r"]), len(tr["d"]))
                self.assertIn(tr["id"], {d["id"] for d in ds})
                self.assertEqual(tr["r"][0], CV.DEPART_ROLE["WR1"])

    def test_compacte(self):
        ds = [{"id": "PRM_CB1", "ratings": CB}]
        y, det = CV.separation("WR1", "GO", "profond", 2.4, {"ratings": ELITE}, ds, "homme", "Cover 3", 7, 1, trace=True)
        c = CV.trace_compacte(det)
        self.assertEqual(c[2], "PRM_CB1")
        self.assertEqual(len(c[3]), len(c[4]))
        self.assertGreaterEqual(len(c[3]), 3)
        r, d = det["trace"]["r"][-1], det["trace"]["d"][-1]
        self.assertEqual(c[3][-1], [round(r[0] * 10), round(r[1] * 10)])
        self.assertEqual(c[4][-1], [round(d[0] * 10), round(d[1] * 10)])
        self.assertTrue(all(isinstance(v, int) for q in c[3] + c[4] for v in q))
        self.assertIsNone(CV.trace_compacte({"t": 1.0}))
