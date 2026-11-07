"""Causal léger, bloc 1 : la course après le contact (moteur/course_spatiale.py).

  Départ      le contact est à la profondeur de son niveau, jamais plus loin que les yards déjà tirés
  Notes       un porteur rapide et puissant gagne plus qu'un lent ; une défense qui plaque bien en concède moins
  Fins        touche, en-but (touchdown = les yards jusqu'à l'en-but), plaqueur = un des défenseurs
  Hasard      flux dédié : mêmes graine et action -> même course

    python -m unittest moteur.tests.test_course_spatiale        (depuis « gamecenter_serveur (1) »)
"""
import statistics
import unittest

from moteur import course_spatiale as CS


def _defense(tackling=78, speed=82):
    out = []
    for k, pos in enumerate(("EDGE", "EDGE", "DT", "DT", "LB", "LB", "LB", "S", "S", "CB", "CB")):
        r = {"tackling": tackling, "strength": 80}
        if pos not in ("EDGE", "DT"):
            r["speed"] = speed
        out.append({"id": f"D{k}", "pos": pos, "ratings": r})
    return out


def _porteur(speed=84, power=80, elusiveness=80):
    return {"ratings": {"speed": speed, "acceleration": speed, "elusiveness": elusiveness, "power": power}}


def _serie(porteur, defense, niveau="linebacker", t_pre=6, n=600, but=75):
    return [CS.apres_contact(porteur, defense, niveau, t_pre, 30.0, "D4", but, 7, k) for k in range(n)]


class Depart(unittest.TestCase):
    def test_contact_jamais_plus_loin_que_les_yards_tires(self):
        for k in range(200):
            r = CS.apres_contact(_porteur(), _defense(), "second rideau", 2, 26.0, "D7", 80, 3, k)
            self.assertLessEqual(r["contact"], 2.0)

    def test_profondeur_selon_le_niveau(self):
        moy = {n: statistics.mean(r["contact"] for r in _serie(_porteur(), _defense(), n, t_pre=30))
               for n in ("ligne", "linebacker", "second rideau")}
        self.assertLess(moy["ligne"], moy["linebacker"])
        self.assertLess(moy["linebacker"], moy["second rideau"])


class Notes(unittest.TestCase):
    def test_porteur_rapide_et_puissant(self):
        fort = statistics.mean(r["yards"] for r in _serie(_porteur(95, 92, 92), _defense()))
        faible = statistics.mean(r["yards"] for r in _serie(_porteur(72, 65, 65), _defense()))
        self.assertGreater(fort, faible + 0.5)

    def test_defense_qui_plaque(self):
        dure = statistics.mean(r["yards"] for r in _serie(_porteur(), _defense(tackling=92, speed=90)))
        tendre = statistics.mean(r["yards"] for r in _serie(_porteur(), _defense(tackling=64, speed=74)))
        self.assertLess(dure, tendre)


class Fins(unittest.TestCase):
    def test_issues_coherentes(self):
        ids = {d["id"] for d in _defense()}
        for r in _serie(_porteur(95, 90, 95), _defense(tackling=60, speed=70), but=12):
            self.assertLessEqual(r["yards"], 12)
            if r["td"]:
                self.assertEqual(r["yards"], 12)
                self.assertIsNone(r["plaqueur"])
            if r["plaqueur"]:
                self.assertIn(r["plaqueur"], ids)
        self.assertTrue(any(r["td"] for r in _serie(_porteur(95, 90, 95), _defense(tackling=60, speed=70), but=12)))

    def test_course_stoppee(self):
        r = [x["yards"] for x in _serie(_porteur(), _defense(), "ligne", t_pre=-2)]
        self.assertLess(statistics.mean(r), 1.0)


class Hasard(unittest.TestCase):
    def test_deterministe(self):
        a = CS.apres_contact(_porteur(), _defense(), "linebacker", 5, 26.0, "D4", 60, 11, 42, trace=True)
        b = CS.apres_contact(_porteur(), _defense(), "linebacker", 5, 26.0, "D4", 60, 11, 42, trace=True)
        self.assertEqual(a, b)

    def test_flux_par_action(self):
        a = [CS.apres_contact(_porteur(), _defense(), "linebacker", 5, 26.0, "D4", 60, 11, k)["yards"] for k in range(50)]
        self.assertGreater(len(set(a)), 3)


class Trace(unittest.TestCase):
    """Export du dessin (play.geo.sim, 07/11/2026) : la trace ne change rien au résultat ; format compact."""

    def test_meme_resultat(self):
        for k in range(60):
            a = CS.apres_contact(_porteur(), _defense(), "linebacker", 6, 26.0, "D4", 60, 13, k)
            b = CS.apres_contact(_porteur(), _defense(), "linebacker", 6, 26.0, "D4", 60, 13, k, trace=True)
            self.assertEqual((a["yards"], a["plaqueur"], a["manques"]), (b["yards"], b["plaqueur"], b["manques"]))

    def test_format_compact(self):
        for k in range(60):
            r = CS.apres_contact(_porteur(95, 90, 95), _defense(tackling=64), "linebacker", 6, 26.0, "D4", 14, 13, k, trace=True)
            t = CS.trace_compacte(r)
            self.assertEqual(t["dt"], 0.2)
            self.assertGreaterEqual(len(t["c"]), 2)
            ids = {d[0] for d in t["d"]}
            for i, pts in t["d"]:
                self.assertEqual(len(pts), len(t["c"]))
            for tt, i, ok in t["ev"]:
                self.assertIn(i, ids)                    # chaque plaquage tenté a son défenseur dans la trace
            self.assertEqual(sum(1 for e in t["ev"] if e[2] == 0), r["manques"])
            self.assertEqual([e[1] for e in t["ev"] if e[2] == 1], [r["plaqueur"]] if r["plaqueur"] else [])
        self.assertIsNone(CS.trace_compacte(CS.apres_contact(_porteur(), _defense(), "ligne", 2, 26.0, "D4", 60, 13, 1)))


if __name__ == "__main__":
    unittest.main()
