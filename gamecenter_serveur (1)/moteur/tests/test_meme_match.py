"""Combinés sur un même match (moteur/meme_match.py, README section 86).

    python -m unittest moteur.tests.test_meme_match        (depuis « gamecenter_serveur (1) »)
"""
import math
import random
import unittest

from moteur import meme_match as MM

MARGE = 0.045
SPREAD, TOTAL = -2.5, 44.5


def _semaine(n=120_000, graine=1, rho_t=0.0):
    """Matchs fictifs (écart, total) et la cote d'avant-match qu'en tirerait le moteur."""
    rng = random.Random(graine)
    sims = []
    for _ in range(n):
        a, b = rng.gauss(24, 9), rng.gauss(21, 9)
        h, w = max(0, round(a + rho_t * rng.gauss(0, 6))), max(0, round(b))
        sims.append((h - w, h + w))
    M = [m for m, _ in sims]
    ties = sum(m == 0 for m in M)
    T = [t for _, t in sims]
    mm, mt = sum(M) / n, sum(T) / n
    rho = (sum((m - mm) * (t - mt) for m, t in sims) / n
           / math.sqrt(sum((m - mm) ** 2 for m in M) / n * sum((t - mt) ** 2 for t in T) / n))
    o = {"p_home": sum(m > 0 for m in M) / (n - ties), "p_tie": ties / n, "spread_home": SPREAD,
         "p_home_cover": sum(m > -SPREAD for m in M) / n, "total": TOTAL,
         "p_over": sum(t > TOTAL for t in T) / n, "corr_mt": rho}
    return sims, o


def _dec(p):
    return 1 / (p * (1 + MARGE))


def _pj(o, mk, side):
    p = {"ml": o["p_home"], "sp": o["p_home_cover"], "tot": o["p_over"]}[mk]
    return p if side in ("home", "over") else 1 - p


def _gagne(mk, side, m, t):
    if mk == "ml":
        return None if m == 0 else (m > 0) == (side == "home")
    if mk == "sp":
        return (m > -SPREAD) if side == "home" else (m < -SPREAD)
    return (t > TOTAL) == (side == "over")


class Prix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sims, cls.o = _semaine()

    def _ev(self, legs):
        decs = [_dec(_pj(self.o, *l)) for l in legs]
        r = MM.prix(self.o, legs, decs)
        ev = 0.0
        for m, t in self.sims:
            res = [_gagne(mk, s, m, t) for mk, s in legs]
            if False in res:
                continue
            ev += r["push_price"] if None in res else r["price_dec"]
        return r, ev / len(self.sims), math.prod(d * _pj(self.o, *l) for l, d in zip(legs, decs))

    def test_marge_d_un_combine_ordinaire(self):
        for legs in ([("ml", "home"), ("tot", "over")], [("sp", "home"), ("tot", "under")],
                     [("ml", "home"), ("sp", "away"), ("tot", "over")]):
            r, ev, vise = self._ev(legs)
            self.assertNotIn("refus", r, legs)
            self.assertAlmostEqual(ev, vise, delta=0.012, msg=legs)       # aucune marge en plus, aucun cadeau

    def test_intervalle(self):
        """Win domicile + spread extérieur +2,5 : gagner de 1 à 2 points, cote bien au-dessus du produit."""
        r, ev, vise = self._ev([("ml", "home"), ("sp", "away")])
        self.assertGreater(r["price_dec"], 8)
        self.assertLessEqual(ev, vise + 0.012)                           # le plancher ne fait que baisser la cote

    def test_plancher(self):
        o = dict(self.o, p_home_cover=self.o["p_home"] * (1 - self.o["p_tie"]) - 0.005)   # 0,5 % entre 1 et 2 points
        legs = [("ml", "home"), ("sp", "away")]
        r = MM.prix(o, legs, [_dec(_pj(o, *l)) for l in legs])
        self.assertLessEqual(r["price_dec"], 1 / (2 * MM.PLANCHER_POINT) + 1e-6)

    def test_refus(self):
        d = lambda legs: [_dec(_pj(self.o, *l)) for l in legs]
        for legs, why in (([("ml", "home"), ("sp", "home")], "redundant"),           # −2,5 contient la victoire
                          ([("ml", "home"), ("sp", "home"), ("tot", "over")], "redundant"),   # = −2,5 + over
                          ([("ml", "away"), ("sp", "away"), ("tot", "under")], "redundant"),  # gagner couvre +2,5
                          ([("ml", "away"), ("sp", "home")], "impossible"),          # perdre et couvrir −2,5
                          ([("ml", "home"), ("ml", "away")], "same_market"),
                          ([("ml", "home")], "legs"),
                          ([("ml", "home"), ("sp", "home"), ("tot", "over"), ("tot", "under")], "legs")):
            self.assertEqual(MM.prix(self.o, legs, d(legs)).get("refus"), why, legs)

    def test_egalite(self):
        legs = [("ml", "home"), ("sp", "away"), ("tot", "over")]
        r = MM.prix(self.o, legs, [_dec(_pj(self.o, *l)) for l in legs])
        reste = MM.prix(self.o, legs[1:], [_dec(_pj(self.o, *l)) for l in legs[1:]])
        self.assertAlmostEqual(r["push_price"], reste["price_dec"], places=4)
        r2 = MM.prix(self.o, legs[:2], [_dec(_pj(self.o, *l)) for l in legs[:2]])
        self.assertAlmostEqual(r2["push_price"], _dec(_pj(self.o, "sp", "away")), places=4)

    def test_sans_probabilites_exportees(self):
        """Semaines d'avant le chantier : probabilités du spread et du total tirées des prix (marge retirée)."""
        am = lambda p: -round(100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)
        o = {k: self.o[k] for k in ("p_home", "p_tie", "spread_home", "total")}
        pc, po = self.o["p_home_cover"], self.o["p_over"]
        o["spread_prices"] = {"home": am(pc * 1.045), "away": am((1 - pc) * 1.045)}
        o["total_prices"] = {"over": am(po * 1.045), "under": am((1 - po) * 1.045)}
        m = MM.modele(o)
        self.assertAlmostEqual(m["p_cover"], pc, delta=0.01)
        self.assertAlmostEqual(m["p_over"], po, delta=0.01)
        self.assertEqual(m["rho"], MM.RHO_FAVORI)                         # domicile favori (−2,5)
        self.assertEqual(MM.modele(dict(o, spread_home=3.5))["rho"], -MM.RHO_FAVORI)

    def test_correlation(self):
        """Un ρ positif (domicile qui gagne large = match à points) rend « Win domicile + over » plus probable."""
        legs = [("ml", "home"), ("tot", "over")]
        decs = [_dec(_pj(self.o, *l)) for l in legs]
        p0 = MM.prix(dict(self.o, corr_mt=0.0), legs, decs)["p"]
        p1 = MM.prix(dict(self.o, corr_mt=0.4), legs, decs)["p"]
        self.assertGreater(p1, p0 + 0.02)


if __name__ == "__main__":
    unittest.main()
