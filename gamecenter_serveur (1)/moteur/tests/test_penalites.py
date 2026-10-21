"""Tests des pénalités pendant l'action (moteur/penalites.py, étape 7.2) : qui commet la faute, ce qu'elle coûte (moitié
de la distance, premier essai, essai rejoué), accepter / refuser selon la probabilité de victoire, un drapeau au plus,
déterminisme. Aucun test ne dépend de l'heure.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import random
import unittest
from collections import Counter

from moteur import penalites as pe
from moteur.aleatoire import flux


def j(id_, pos):
    return {"id": id_, "name": id_, "pos": pos}


def action(**k):
    a = {"genre": "pass", "issue": "PASS_INCOMPLETE", "lance": True, "reception": "traffic", "profondeur": 12,
         "bloqueurs": [{"joueur": j(p, p), "marge": 0.0, "battu": False} for p in ("LT", "LG", "C", "RG", "RT")],
         "couvreurs": [{"joueur": j("CB1", "CB"), "discipline": 70}, {"joueur": j("CB2", "CB"), "discipline": 70},
                       {"joueur": j("S1", "S"), "discipline": 70}, {"joueur": j("LB1", "LB"), "discipline": 70}],
         "couvreur_cible": j("CB1", "CB"), "cible": j("WR1", "WR"), "rushers": [j("E1", "EDGE"), j("D1", "DT")],
         "rusher_gagnant": None, "pression": False, "k_att": 1.0, "k_def": 1.0}
    a.update(k)
    return a


def tirages(a, n=6000, graine=1):
    return [pe.tirer(a, flux(pe.FLUX, graine, i)) for i in range(n)]


class Coût(unittest.TestCase):
    def test_holding_offensif(self):
        a = pe.appliquer(pe.OFF_HOLDING, 40, 2, 7)
        self.assertEqual((a["yl"], a["down"], a["togo"], a["yards"]), (30, 2, 17, 10))
        self.assertTrue(a["replay_down"] and a["nullified"] and not a["auto_first"])

    def test_moitie_de_la_distance(self):
        self.assertEqual(pe.appliquer(pe.OFF_HOLDING, 8, 1, 10)["yl"], 4)           # 10 > 8/2 : 4 yards
        d = pe.appliquer(pe.DEF_HOLDING, 96, 1, 4)
        self.assertEqual((d["yl"], d["down"], d["togo"]), (98, 1, 2))               # 5 > 4/2 : 2 yards
        self.assertEqual(pe.appliquer(pe.OFF_HOLDING, 95, 1, 5)["togo"], 15)         # « and goal » : jusqu'à l'en-but

    def test_premier_essai_automatique(self):
        for t in (pe.DEF_HOLDING, pe.ILLEGAL_CONTACT):
            a = pe.appliquer(t, 30, 3, 12)
            self.assertEqual((a["yl"], a["down"], a["togo"]), (35, 1, 10))

    def test_interference_a_l_endroit_de_la_faute(self):
        a = pe.appliquer(pe.DPI, 30, 2, 10, profondeur=28)
        self.assertEqual((a["yl"], a["down"], a["yards"]), (58, 1, 28))
        self.assertEqual(pe.appliquer(pe.DPI, 80, 2, 10, profondeur=30)["yl"], 99)     # dans l'en-but : aux 1

    def test_roughing_apres_une_passe_completee(self):
        a = pe.appliquer(pe.ROUGHING, 40, 2, 10, gain=12, issue="PASS_COMPLETE")
        self.assertEqual((a["yl"], a["down"], a["yards"], a["nullified"]), (67, 1, 15, False))
        b = pe.appliquer(pe.ROUGHING, 40, 2, 10, issue="PASS_INCOMPLETE")
        self.assertEqual((b["yl"], b["nullified"]), (55, True))


class Valeur(unittest.TestCase):
    def test_points_attendus_ordonnes(self):
        ep = pe.points_attendus_essai
        self.assertGreater(ep(1, 10, 75), ep(2, 10, 75))
        self.assertGreater(ep(2, 10, 75), ep(3, 10, 75))
        self.assertGreater(ep(1, 10, 75), ep(1, 20, 75))
        self.assertGreater(ep(3, 2, 40), ep(3, 12, 40))
        self.assertGreater(ep(1, 10, 30), ep(1, 10, 70))

    def test_accepter_refuser(self):
        """L'équipe qui subit la faute garde le meilleur état pour elle."""
        def choix(t, yl, down, togo, gain, issue):
            rng = random.Random(0)
            a = action(issue=issue, genre="run" if issue == "RUN" else "pass")
            for _ in range(5000):
                p = pe.arbitrer(a, yl, down, togo, gain, 0, 0.5, rng)
                if p and p["type"] == t:
                    return p["accepted"]
            raise AssertionError("faute jamais tirée")
        self.assertTrue(choix(pe.OFF_HOLDING, 30, 1, 10, 25, "RUN"))              # gros gain annulé
        self.assertFalse(choix(pe.OFF_HOLDING, 30, 2, 8, -9, "SACK"))             # le sack vaut mieux pour la défense
        self.assertTrue(choix(pe.DPI, 30, 3, 10, 0, "PASS_INCOMPLETE"))           # l'attaque prend le premier essai
        self.assertFalse(choix(pe.DEF_HOLDING, 30, 2, 10, 30, "PASS_COMPLETE"))   # le gain vaut mieux pour l'attaque

    def test_jamais_accepte_contre_soi(self):
        rng = random.Random(3)
        for _ in range(4000):
            yl, down, togo, gain = rng.randint(5, 95), rng.randint(1, 4), rng.randint(1, 15), rng.randint(-8, 25)
            gain = min(gain, 99 - yl)
            p = pe.arbitrer(action(issue=rng.choice(["RUN", "PASS_COMPLETE", "PASS_INCOMPLETE", "SACK"])),
                            yl, down, togo, gain, rng.randint(-14, 14), rng.random(), rng)
            if p and p["wp"]["accept"] is not None:
                meilleur = (max if p["chooser"] == "offense" else min)(p["wp"]["accept"], p["wp"]["decline"])
                self.assertEqual(p["wp"]["accept" if p["accepted"] else "decline"], meilleur)


class Fautes(unittest.TestCase):
    def test_un_drapeau_au_plus_et_deterministe(self):
        a = action()
        self.assertEqual(tirages(a, 500), tirages(a, 500))
        self.assertLess(sum(p for _, p, _ in pe.candidats(action(reception="contested", profondeur=40,
                                                                  pression=True))), 0.5)

    def test_holding_du_bloqueur_battu(self):
        bl = [{"joueur": j(p, p), "marge": 2.0, "battu": p == "RT"} for p in ("LT", "LG", "C", "RG", "RT")]
        qui = Counter(p["joueur"]["id"] for p in tirages(action(bloqueurs=bl), 20000)
                      if p and p["type"] == pe.OFF_HOLDING)
        self.assertEqual(qui.most_common(1)[0][0], "RT")
        sans = sum(1 for p in tirages(action(), 20000) if p and p["type"] == pe.OFF_HOLDING)
        self.assertGreater(sum(qui.values()), sans * 1.5)                          # un duel perdu : plus de holdings

    def test_interference_sur_ballon_dispute(self):
        n = lambda rec, prof: sum(1 for p in tirages(action(reception=rec, profondeur=prof), 20000)
                                  if p and p["type"] == pe.DPI)
        self.assertGreater(n("contested", 20), n("open", 20) * 4)
        self.assertGreater(n("contested", 20), n("contested", 3) * 2)               # plus souvent loin
        qui = {p["joueur"]["id"] for p in tirages(action(reception="contested"), 6000) if p and p["type"] == pe.DPI}
        self.assertEqual(qui, {"CB1"})                                              # le défenseur de la cible

    def test_discipline(self):
        cv = [{"joueur": j("CB1", "CB"), "discipline": 92}, {"joueur": j("CB2", "CB"), "discipline": 50}]
        qui = Counter(p["joueur"]["id"] for p in tirages(action(couvreurs=cv, lance=False), 40000)
                      if p and p["type"] in (pe.DEF_HOLDING, pe.ILLEGAL_CONTACT))
        self.assertGreater(qui["CB2"], qui["CB1"] * 3)
        moins = sum(1 for p in tirages(action(k_def=pe.DISCIPLINE_EQUIPE, k_att=pe.DISCIPLINE_EQUIPE), 30000) if p)
        self.assertLess(moins, sum(1 for p in tirages(action(), 30000) if p))

    def test_roughing_sous_pression(self):
        n = lambda pr: sum(1 for p in tirages(action(pression=pr, rusher_gagnant=j("E1", "EDGE")), 30000)
                           if p and p["type"] == pe.ROUGHING)
        self.assertGreater(n(True), n(False) * 3)

    def test_exclusions(self):
        self.assertEqual(pe.candidats(action(safety=True)), [])
        types = {t for t, _, _ in pe.candidats(action(issue="INTERCEPTION"))}
        self.assertEqual(types, {pe.OFF_HOLDING, pe.OPI})                           # la défense garde son interception
        self.assertNotIn(pe.ROUGHING, {t for t, _, _ in pe.candidats(action(issue="PASS_COMPLETE", td=True))})
        self.assertEqual({t for t, _, _ in pe.candidats(action(genre="run", issue="RUN"))}, {pe.OFF_HOLDING})
        p = None
        rng = random.Random(5)
        while p is None or p["type"] != pe.OFF_HOLDING:
            p = pe.arbitrer(action(issue="INTERCEPTION"), 40, 2, 10, 0, 0, 0.5, rng)
        self.assertFalse(p["accepted"])

    def test_annonce(self):
        p = {"type": pe.OFF_HOLDING, "name": pe.NOMS[pe.OFF_HOLDING], "team": "offense", "accepted": True,
             "yards": 10, "replay_down": True}
        self.assertEqual(pe.annonce(p, 74), "Offensive holding, offense, #74, 10 yards, repeat the down")
        self.assertTrue(pe.annonce(dict(p, accepted=False)).endswith("declined"))

    def test_flux_dedie(self):
        self.assertNotEqual(flux(pe.FLUX, 1, 1).random(), flux("decision-passe", 1, 1).random())


if __name__ == "__main__":
    unittest.main()
