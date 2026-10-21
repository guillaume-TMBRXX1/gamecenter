"""Tests de la poche et de la ligne offensive (moteur/poche.py, étape 7.1) : duels, duel perdu au temps avant la
pression, forme de la poche, réaction du QB, lancer en courant, poche absente = bloc B à l'identique. Aucun test ne
dépend de l'heure.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import random
import unittest

from moteur import poche as po
from moteur import decider_passe
from moteur.aleatoire import flux
from moteur.intelligence_qb import attributs_qb
from moteur.decision_qb import B as _B

B_HATE = _B["hate"]


def j(id_, pos, **notes):
    return {"id": id_, "name": id_, "pos": pos, "ratings": notes}


def ligne(pb=80, st=80):
    return {p: j(p, p, pass_block=pb, strength=st) for p in po.OL}


def rushers(pr=80, st=80, edge=None):
    e = edge if edge is not None else pr
    return {"EDGE": [j("E1", "EDGE", pass_rush=e, strength=st), j("E2", "EDGE", pass_rush=e, strength=st)],
            "DT": [j("D1", "DT", pass_rush=pr, strength=st), j("D2", "DT", pass_rush=pr, strength=st)],
            "LB": [j("L1", "LB"), j("L2", "LB"), j("L3", "LB")], "S": [j("S1", "S")], "CB": [j("C1", "CB")]}


def poche(seed, n=4, ligne_=None, rush=None, rushers_=None, ttp=2.6, protecteurs=()):
    P = po.Poche(po.affecter(ligne_ or ligne(), rushers_ or rushers(), n, protecteurs), random.Random(seed), rush=rush)
    return P.armer(ttp)


class Duels(unittest.TestCase):
    def test_quatre_rushers(self):
        d = po.affecter(ligne(), rushers(), 4)
        self.assertEqual([(x["rusher"]["id"], x["bloqueur"]["id"], x["type"]) for x in d],
                         [("E1", "LT", "edge"), ("E2", "RT", "edge"), ("D1", "LG", "interior"), ("D2", "RG", "interior")])
        self.assertEqual(sum(x["double"] for x in d), 1)                # le centre double un DT

    def test_blitz_et_protecteurs(self):
        d = po.affecter(ligne(), rushers(), 6, protecteurs=[j("RB1", "RB", strength=70)])
        self.assertEqual(len(d), 6)
        self.assertFalse(any(x["double"] for x in d))                   # le centre prend un blitzeur
        self.assertEqual([x["bloqueur"]["id"] for x in d[4:]], ["C", "RB1"])
        d7 = po.affecter(ligne(), rushers(), 7)
        self.assertEqual(sum(x["libre"] for x in d7), 2)                # personne pour les deux derniers

    def test_rush_a_trois(self):
        self.assertEqual(len(po.affecter(ligne(), rushers(), 3)), 3)


class Pression(unittest.TestCase):
    def test_au_temps_avant_la_pression(self):
        P = poche(1)
        self.assertEqual(P.premier["t"], 2.6)                            # le temps du moteur n'est pas changé
        self.assertTrue(all(d["t"] >= 2.6 for d in P.duels))
        self.assertIn(P.forme, ("edge", "interior", "collapse"))

    def test_profil_pas_niveau(self):
        """Des bords dominants gagnent plus souvent leur duel ; le moment, lui, ne bouge pas."""
        forts = sum(poche(s, rushers_=rushers(edge=92)).premier["type"] == "edge" for s in range(600))
        faibles = sum(poche(s, rushers_=rushers(edge=66)).premier["type"] == "edge" for s in range(600))
        self.assertGreater(forts, faibles + 120)

    def test_jeu_de_rush(self):
        inter = sum(poche(s, rush="INTERIOR_COLLAPSE").premier["type"] == "interior" for s in range(600))
        bord = sum(poche(s, rush="EDGE_RUSH").premier["type"] == "interior" for s in range(600))
        self.assertGreater(inter, bord + 100)

    def test_libre_et_effondrement(self):
        libres = sum(poche(s, n=7).premier["libre"] for s in range(300))
        self.assertGreater(libres, 150)                                  # un blitzeur libre arrive le plus souvent
        faible = ligne(pb=60, st=62)
        col_f = sum(poche(s, ligne_=faible).forme == "collapse" for s in range(600))
        col = sum(poche(s).forme == "collapse" for s in range(600))
        self.assertGreater(col_f, col)                                   # une ligne faible cède en série

    def test_deterministe(self):
        a, b = poche(42), poche(42)
        self.assertEqual([d["t"] for d in a.duels], [d["t"] for d in b.duels])
        self.assertEqual(a.journal(), b.journal())


class Reaction(unittest.TestCase):
    def test_monte_glisse_sort(self):
        qb = {"pocket_awareness": 92}
        kinds = {}
        for s in range(600):
            P = poche(s)
            k = P.reagir(qb, 75)["kind"]
            kinds.setdefault((P.forme, k), 0)
            kinds[(P.forme, k)] += 1
        self.assertTrue(kinds.get(("edge", "step_up")))
        self.assertTrue(kinds.get(("interior", "slide")))
        self.assertFalse(kinds.get(("interior", "step_up")))             # on ne monte pas dans un DT
        self.assertFalse(kinds.get(("edge", "slide")))

    def test_mobilite(self):
        sorties = lambda mob: sum(poche(s).reagir({"pocket_awareness": 80}, mob)["kind"] == "escape" for s in range(800))
        self.assertGreater(sorties(92), sorties(55) + 60)

    def test_sortie_du_cote_libre(self):
        for s in range(300):
            P = poche(s)
            r = P.reagir({"pocket_awareness": 50}, 99)
            if r["kind"] == "escape" and P.cote in ("left", "right"):
                self.assertNotEqual(r["side"], P.cote)


QB = {"id": "QB1", "name": "QB", "ratings": {"throw_accuracy": 80, "throw_power": 80, "decision_making": 80, "mobility": 82,
                                            "awareness": 80}}


def passe(seed, poche_=None, concept="FOUR_VERTS"):
    qb = dict(QB, iq=attributs_qb(QB, "CTX"))
    rec = {r: {"id": r, "name": r, "ratings": {"route_running": 78, "speed": 84, "catching": 80}} for r in ("WR1", "WR2", "WR3", "TE", "RB")}
    de = {"CB": [{"id": "C1", "name": "C1", "ratings": {"coverage": 82, "speed": 86}}] * 2,
          "S": [{"id": "S1", "name": "S1", "ratings": {"coverage": 78}}] * 2, "LB": [{"id": "L1", "name": "L1", "ratings": {}}] * 3}
    return decider_passe(concept, "SHOTGUN", "COVER_3", rec, de, qb, 0.6, seed, 7,
                         **({"poche": poche_} if poche_ else {}))


class Chaine(unittest.TestCase):
    ENTREE = {"ligne": ligne(), "rushers": rushers(), "roles": {}}

    def test_sans_poche_identique(self):
        for s in range(40):
            a, b = passe(s)[2], passe(s)[2]
            self.assertEqual(a.to_dict(), b.to_dict())
            self.assertFalse(hasattr(a, "poche"))

    def test_avant_la_pression_rien_ne_change(self):
        """Tant que le QB lance avant que la poche cède (et avant d'être pressé), la décision est celle du bloc B."""
        for s in range(200):
            a, b = passe(s)[2], passe(s, self.ENTREE)[2]
            if a.temps_lancer < b.temps_poche - B_HATE - 0.01 and a.action == "LANCER":   # avant la fenêtre de hâte
                self.assertEqual((a.cible, a.temps_lancer, a.statut), (b.cible, b.temps_lancer, b.statut))
                self.assertEqual(b.poche.journal(b)["shape"], "clean")

    def test_reactions_et_lancer_en_courant(self):
        vu = {"en_courant": 0, "reaction": set()}
        for s in range(400):
            d = passe(s, self.ENTREE)[2]
            if d.reaction:
                vu["reaction"].add(d.reaction)
            if d.en_courant:
                vu["en_courant"] += 1
                self.assertEqual(d.action, "LANCER")
                self.assertGreater(d.mod_inc, 1.0)                       # moins précis en courant
                self.assertEqual(d.poche.journal(d)["reaction"], "escape")
        self.assertGreater(vu["en_courant"], 0)
        self.assertIn("escape", vu["reaction"])
        self.assertTrue(vu["reaction"] & {"step_up", "slide"})

    def test_flux_dedie(self):
        self.assertNotEqual(flux(po.FLUX, 1, 1).random(), flux("decision-passe", 1, 1).random())


if __name__ == "__main__":
    unittest.main()
