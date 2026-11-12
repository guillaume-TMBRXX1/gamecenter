"""Front office FO-5 : la draft des supporters (moteur/draft.py). Quelques secondes :

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)

Prospects (base du poste gardée, trois profils, déterminisme) · choix du coordinateur · choix des supporters (minimum,
égalité) · annonce pendant semaine_suivante (titulaires seulement, place tenue par le prospect du coordinateur) ·
application la semaine suivante (garde-fou tenu) · trajectoire longue · progression des trois profils.
"""
import collections
import json
import random
import statistics
import unittest

from moteur import developpement as dv
from moteur import draft as dr
from moteur.tests.test_bloc_e import joueur_isole, ligue, stats_neutres, unites
# réservoir de noms assez grand pour trois prospects par départ (le notebook : _FR_FIRST × _FR_LAST)
NOMS = ([f"Prenom{i}" for i in range(40)], [f"Nom{i}" for i in range(40)])

QB = {"throw_power": 80, "throw_accuracy": 80, "mobility": 80, "decision_making": 80}


def vieillir(E, pos="WR", banc_pos=None):
    """Les WR titulaires partent à la fin de la semaine ; les autres restent jeunes. banc_pos : un remplaçant qui part."""
    for pid, j in E["joueurs"].items():
        j["age0"] = 34.9 if j["pos"] == pos else 25.0
        if banc_pos and pid.endswith(banc_pos):
            j["banc"] = "veteran"
            j["age0"] = 34.9
    return E


def semaine(E, w=1, draft=True, noms_ligue=False):
    sj, se = stats_neutres(E)
    return dv.semaine_suivante(E, sj, se, unites, index=w, recrues=NOMS,
                               draft=dr.annonceur(noms_ligue) if draft else None)


class TestProspect(unittest.TestCase):
    def test_profils(self):
        j = joueur_isole(age=35.0, pos="QB", notes=QB)
        j["name"] = "Vieux QB"
        P = {p: dr.prospect(j, "AAA_QB1", 8, 3, p, NOMS) for p in dr.PROFILS}
        for p, r in P.items():
            self.assertEqual(r, dr.prospect(j, "AAA_QB1", 8, 3, p, NOMS))            # déterministe
            self.assertEqual(r["base"], j["base"])                                 # base du poste gardée
            self.assertEqual(r["recrue"], {"semaine": 3, "remplace": "Vieux QB", "profile": p, "drafted_by_fans": False})
            self.assertTrue(all(dv.NOTE_MIN <= r["actuelle"][k] <= dv.plafond(r, k) for k in r["base"]))
            g = dr.PROFIL[p]
            self.assertTrue(g["age"][0] <= dv.age(r, 8) <= g["age"][1], p)
            self.assertTrue(g["potentiel"][0] <= r["potentiel"] <= g["potentiel"][1], p)
            json.dumps(r)
        ecart = lambda r: statistics.mean(r["base"][k] - r["actuelle"][k] for k in r["base"])
        self.assertLess(ecart(P["pret"]), ecart(P["intelligence"]))
        self.assertLess(ecart(P["intelligence"]), ecart(P["potentiel"]))
        self.assertGreater(P["potentiel"]["potentiel"], P["pret"]["potentiel"])
        self.assertLess(dv.age(P["potentiel"], 8), dv.age(P["pret"], 8))
        self.assertGreaterEqual(P["intelligence"]["actuelle"]["decision_making"], 80)   # mental au-dessus de la base
        self.assertGreater(P["intelligence"]["apprentissage"], P["pret"]["apprentissage"])
        self.assertIn(P["potentiel"]["dev"], ("normal", "fast", "star"))
        # flux propres : un autre départ, une autre semaine, un autre profil -> d'autres tirages
        self.assertNotEqual(dr.prospect(j, "AAA_QB1", 8, 4, "pret", NOMS)["actuelle"], P["pret"]["actuelle"])
        self.assertNotEqual(dr.prospect(j, "BBB_QB1", 8, 3, "pret", NOMS)["actuelle"], P["pret"]["actuelle"])

    def test_resume(self):
        j = joueur_isole(age=35.0)
        r = dr.prospect(j, "AAA_WR1", 0, 1, "potentiel", NOMS)
        s = dr.resume(r, 0)
        self.assertEqual(set(s), {"name", "age", "ovr", "dev", "potential", "ratings", "iq"})
        self.assertLess(s["ovr"], dv.ovr(j["base"]))
        self.assertGreater(s["potential"], dv.ovr(j["base"]))


class TestFootballIQ(unittest.TestCase):
    """FO-6 (décision du 12/11) : la décision d'un QB, sinon OVR + 3 points par point de bonus d'expérience."""

    def test_note(self):
        qb = joueur_isole(pos="QB", notes=QB)
        qb["actuelle"]["decision_making"] = 86.4
        self.assertEqual(dr.football_iq(qb), 86)
        wr = joueur_isole()
        self.assertEqual(dr.football_iq(wr, 0.0), dv.ovr(dv.notes_effectives(wr)))
        self.assertEqual(dr.football_iq(wr, 2.0), dv.ovr(dv.notes_effectives(wr)) + 6)
        self.assertEqual(dr.football_iq(wr, 99.0), 99)

    def test_profil_iq_au_dessus(self):
        E = dv.etat_initial(ligue())
        for j in E["joueurs"].values():
            j["apprentissage"] = 1.8                                  # ligue d'expérience moyenne
        j = E["joueurs"]["AAA_CB1"] if "AAA_CB1" in E["joueurs"] else next(x for x in E["joueurs"].values() if x["pos"] == "CB")
        iq = {p: dr.resume(dr.prospect(j, "X_CB1", 0, 1, p, NOMS), 0, E)["iq"] for p in dr.PROFILS}
        self.assertGreater(iq["intelligence"], iq["pret"])
        self.assertGreater(iq["intelligence"], iq["potentiel"])


class TestChoix(unittest.TestCase):
    def test_coordinateur(self):
        self.assertEqual(dr.choix_coordinateur("SPK_WR1", "SPK", "WR", 3), "potentiel")
        self.assertEqual(dr.choix_coordinateur("CTD_QB1", "CTD", "QB", 3), "pret")
        self.assertEqual(dr.choix_coordinateur("CTX_QB1", "CTX", "QB", 3), "pret")
        self.assertEqual(dr.choix_coordinateur("CTX_WR1", "CTX", "WR", 3), dr.choix_coordinateur("CTX_WR1", "CTX", "WR", 3))
        n = collections.Counter(dr.choix_coordinateur(f"T{i}_WR1", f"T{i}", "WR", 5) for i in range(3000))
        self.assertAlmostEqual(n["pret"] / 3000, 0.5, delta=0.04)
        self.assertAlmostEqual(n["potentiel"] / 3000, 0.3, delta=0.04)
        self.assertAlmostEqual(n["intelligence"] / 3000, 0.2, delta=0.04)

    def test_supporters(self):
        a = {"coordinator": "pret"}
        ok = {"choice": "potentiel", "votes": 9, "counts": {"pret": 2, "potentiel": 5, "intelligence": 2}}
        self.assertEqual(dr.choix_supporters(a, ok), ("potentiel", "fans", 9))
        self.assertEqual(dr.choix_supporters(a, None), ("pret", "coordinators", 0))
        self.assertEqual(dr.choix_supporters(a, dict(ok, votes=4)), ("pret", "coordinators", 4))      # moins de 5 votes
        egal = {"choice": "potentiel", "votes": 8, "counts": {"pret": 4, "potentiel": 4}}
        self.assertEqual(dr.choix_supporters(a, egal), ("pret", "coordinators", 8))                 # égalité en tête
        self.assertEqual(dr.choix_supporters(a, dict(ok, choice="star")), ("pret", "coordinators", 9))
        faux = {"choice": "intelligence", "votes": 9, "counts": {"pret": 2, "potentiel": 5, "intelligence": 2}}
        self.assertEqual(dr.choix_supporters(a, faux), ("pret", "coordinators", 9))                 # pas en tête
        self.assertEqual(dr.choix_supporters(a, {"choice": "pret", "votes": "x"}), ("pret", "coordinators", 0))

    def test_lire_choix(self):
        d = {"week": "2026-11-23", "lever": "course_passe", "teams": {}, "draft": {"CTD_RB1": {"choice": "pret"}}}
        self.assertEqual(dr.lire_choix(d, "2026-11-23"), d["draft"])
        self.assertEqual(dr.lire_choix(d, "2026-11-30"), {})
        self.assertEqual(dr.lire_choix(None, "2026-11-23"), {})
        self.assertEqual(dr.lire_choix(dict(d, draft=[1]), "2026-11-23"), {})


class TestAnnonce(unittest.TestCase):
    def test_titulaires_seulement(self):
        E = vieillir(dv.etat_initial(ligue()), banc_pos="CB2")
        N, r = semaine(E)
        partis = {m["id"]: m for m in r["retirements"]}
        annonces = {a["id"]: a for a in r["draft"]}
        wr = {pid for pid, j in E["joueurs"].items() if j["pos"] == "WR" and not j.get("banc")}
        self.assertEqual(set(annonces), wr)                                       # les WR titulaires sont annoncés
        bancs = [pid for pid in partis if E["joueurs"][pid].get("banc")]
        self.assertTrue(bancs and not set(bancs) & set(annonces))                 # le banc : recrue d'aujourd'hui
        for pid in bancs:
            self.assertNotIn("draft", partis[pid])
            self.assertNotIn("profile", N["joueurs"][pid]["recrue"])
        for pid, a in annonces.items():
            self.assertTrue(partis[pid]["draft"])
            self.assertEqual(set(a["ratings"]), set(E["joueurs"][pid]["base"]))       # notes de sa dernière semaine
            self.assertEqual(a["seasons"], 0)
            self.assertEqual(a["iq"], dv.ovr(a["ratings"]) + round(dr.IQ_POINTS * E["joueurs"][pid]["bonus_iq"]))
            self.assertEqual([p["profile"] for p in a["prospects"]], list(dr.PROFILS))
            self.assertEqual(N["joueurs"][pid]["recrue"]["profile"], a["coordinator"])
            self.assertEqual(partis[pid]["rookie"], N["joueurs"][pid]["name"])
            self.assertEqual((a["retired"], a["week"]), (E["joueurs"][pid]["name"], 1))
        self.assertEqual(dr.controle(r["draft"], N), [])
        self.assertEqual(dv.controler(N, unites), [])
        json.dumps(r)
        noms = [p["name"] for a in r["draft"] for p in a["prospects"]]
        self.assertEqual(len(noms), len(set(noms)))

    def test_sans_draft_identique(self):
        E = vieillir(dv.etat_initial(ligue()))
        a, ra = semaine(E, draft=False)
        b, rb = semaine(E, draft=False)
        self.assertEqual(a, b)
        self.assertNotIn("draft", ra)
        self.assertTrue(all("profile" not in j.get("recrue", {}) for j in a["joueurs"].values()))
        # sans départ, avec ou sans draft : mêmes notes
        J = dv.etat_initial(ligue())
        for j in J["joueurs"].values():
            j["age0"] = 25.0
        self.assertEqual(semaine(J)[0]["joueurs"], semaine(J, draft=False)[0]["joueurs"])

    def test_controle(self):
        E = vieillir(dv.etat_initial(ligue()))
        N, r = semaine(E)
        a = r["draft"][0]
        self.assertTrue(dr.controle([dict(a, prospects=a["prospects"][:2])], N))
        self.assertTrue(dr.controle([dict(a, coordinator="x")], N))
        autre = dict(a, coordinator=next(p for p in dr.PROFILS if p != a["coordinator"]))
        self.assertTrue(dr.controle([autre], N))
        self.assertTrue(dr.controle(r["draft"] + [r["draft"][0]], N))            # noms en double


class TestAppliquer(unittest.TestCase):
    def preparer(self):
        E = vieillir(dv.etat_initial(ligue()))
        return semaine(E)

    def test_choix_des_supporters(self):
        N, r = self.preparer()
        a = r["draft"][0]
        autre = next(p for p in dr.PROFILS if p != a["coordinator"])
        choix = {a["id"]: {"choice": autre, "votes": 12, "counts": {autre: 9, a["coordinator"]: 3}}}
        avant = json.loads(json.dumps(N))
        out = dr.appliquer(N, r["draft"], choix, unites)
        rec = {o["id"]: o for o in out}
        self.assertEqual(rec[a["id"]]["source"], "fans")
        self.assertEqual(rec[a["id"]]["profile"], autre)
        j = N["joueurs"][a["id"]]
        self.assertEqual(j["name"], next(p for p in a["prospects"] if p["profile"] == autre)["name"])
        self.assertTrue(j["recrue"]["drafted_by_fans"])
        self.assertEqual(j["recrue"]["profile"], autre)
        for o in out[1:]:                                                         # les autres : le coordinateur
            self.assertEqual((o["source"], o["profile"]), ("coordinators", o["coordinator"]))
            self.assertFalse(N["joueurs"][o["id"]]["recrue"]["drafted_by_fans"])
        self.assertEqual(dv.controler(N, unites), [])                             # garde-fou tenu après l'échange
        self.assertEqual(set(N["joueurs"]), set(avant["joueurs"]))
        self.assertEqual(N["semaines"], avant["semaines"])

    def test_meme_choix_que_le_coordinateur(self):
        N, r = self.preparer()
        a = r["draft"][0]
        c = a["coordinator"]
        avant = json.loads(json.dumps(N))
        out = dr.appliquer(N, r["draft"], {a["id"]: {"choice": c, "votes": 6, "counts": {c: 6}}}, unites)
        self.assertEqual((out[0]["source"], out[0]["profile"]), ("fans", c))
        self.assertTrue(N["joueurs"][a["id"]]["recrue"]["drafted_by_fans"])
        N["joueurs"][a["id"]]["recrue"]["drafted_by_fans"] = False
        self.assertEqual(N, avant)                                                # rien d'autre ne bouge

    def test_sans_fichier(self):
        N, r = self.preparer()
        avant = json.loads(json.dumps(N))
        out = dr.appliquer(N, r["draft"], {}, unites)
        self.assertTrue(all(o["source"] == "coordinators" for o in out))
        self.assertEqual(N, avant)

    def test_place_inattendue(self):
        N, r = self.preparer()
        a = r["draft"][0]
        N["joueurs"][a["id"]]["name"] = "Quelqu'un d'autre"
        out = dr.appliquer(N, r["draft"], {a["id"]: {"choice": "potentiel", "votes": 9}}, unites)
        self.assertEqual(out[0]["source"], "missing")
        self.assertEqual(N["joueurs"][a["id"]]["name"], "Quelqu'un d'autre")


class TestTrajectoire(unittest.TestCase):
    def test_semaines_enchainees(self):
        """40 semaines, les supporters choisissent au hasard : autant de départs que sans draft (à quelques départs par
        déclin près : l'anti-inflation dépend des recrues), garde-fou tenu chaque semaine, chaque annonce appliquée la
        semaine suivante."""
        A = B = dv.etat_initial(ligue())
        nA = nB = 0
        rng = random.Random("draft-trajectoire")
        annonces = []
        for w in range(1, 41):
            if annonces:
                choix = {a["id"]: {"choice": (c := rng.choice(dr.PROFILS)), "votes": 7, "counts": {c: 7}}
                         for a in annonces if rng.random() < 0.7}
                out = dr.appliquer(A, annonces, choix, unites)
                self.assertTrue(all(o["source"] != "missing" for o in out))
                self.assertEqual(dv.controler(A, unites), [])
            sj, se = stats_neutres(A)
            A, ra = dv.semaine_suivante(A, sj, se, unites, index=w, recrues=NOMS, draft=dr.annonceur())
            self.assertEqual(dr.controle(ra["draft"], A), [])
            annonces = ra["draft"]
            sj, se = stats_neutres(B)
            B, rb = dv.semaine_suivante(B, sj, se, unites, index=w, recrues=NOMS)
            nA += len(ra["retirements"])
            nB += len(rb["retirements"])
            if w <= 20:                                   # avant les premiers déclins : exactement les mêmes départs
                self.assertEqual({m["id"] for m in ra["retirements"]}, {m["id"] for m in rb["retirements"]}, w)
        self.assertGreater(nA, 10)
        self.assertLessEqual(abs(nA - nB), max(2, nB // 10), (nA, nB))
        for t in {j["team"] for j in A["joueurs"].values()}:
            noms = [j["name"] for j in A["joueurs"].values() if j["team"] == t]
            self.assertEqual(len(noms), len(set(noms)), t)

    def test_progression_des_profils(self):
        """Sans anti-inflation, titulaire qui joue tout : le gros potentiel rattrape le prêt en 6 à 8 semaines."""
        bases = [r["ratings"] for r in ligue() if r["pos"] in ("WR", "CB", "QB")]
        pos = [r["pos"] for r in ligue() if r["pos"] in ("WR", "CB", "QB")]
        courbe = {p: [0.0] * 13 for p in dr.PROFILS}
        for i, (b, ps) in enumerate(zip(bases * 4, pos * 4)):
            j = joueur_isole(age=35.0, pos=ps, notes=b)
            for p in dr.PROFILS:
                r = dr.prospect(j, f"T_{ps}{i}", 0, i, p, NOMS)
                rng = random.Random(i)
                for w in range(13):
                    courbe[p][w] += dv.ovr(r["actuelle"]) - dv.ovr(r["base"])
                    for k in sorted(r["actuelle"]):
                        r["actuelle"][k] += dv.delta_note(r, k, dv.age(r, w) + 0.125, 1.0, rng)
                    dv._borner_actuelle(r)
        rattrape = next(w for w in range(13) if courbe["potentiel"][w] >= courbe["pret"][w])
        self.assertTrue(6 <= rattrape <= 8, (rattrape, courbe))
        self.assertLess(courbe["potentiel"][0], courbe["intelligence"][0])
        self.assertLess(courbe["intelligence"][0], courbe["pret"][0])
        self.assertGreater(courbe["potentiel"][12], courbe["pret"][12])


class TestAudit(unittest.TestCase):
    """audit_moteur.py, check_draft : annonce et draft appliquée."""

    def bloquants(self, w):
        import audit_moteur as audit
        A = audit.Audit()
        audit.check_draft(A, "w", w)
        return [m for lvl, *_, m in A.items if lvl == audit.BLOQUANT]

    def test_audit(self):
        E = vieillir(dv.etat_initial(ligue()))
        N, r = semaine(E)
        w = {"draft": {"version": 1, "for_week": "2026-11-23", "announcements": r["draft"]}, "players_next_week": N,
             "teams": {}}
        self.assertEqual(self.bloquants(w), [])
        a = r["draft"][0]
        N["joueurs"][a["id"]]["name"] = "Intrus"
        self.assertTrue(self.bloquants(w))
        self.assertEqual(self.bloquants({}), [])
        bon = {"id": a["id"], "team": a["team"], "profile": "pret", "coordinator": "pret", "source": "coordinators",
               "votes": 0, "name": "X"}
        roster = {a["team"]: {"roster": [{"id": a["id"], "name": "X"}]}}
        self.assertEqual(self.bloquants({"drafted": [bon], "teams": roster}), [])
        self.assertTrue(self.bloquants({"drafted": [dict(bon, source="fans", votes=3)], "teams": roster}))
        self.assertTrue(self.bloquants({"drafted": [dict(bon, profile="potentiel")], "teams": roster}))
        self.assertTrue(self.bloquants({"drafted": [dict(bon, source="missing")], "teams": roster}))
        self.assertTrue(self.bloquants({"drafted": [dict(bon, name="Y")], "teams": roster}))


if __name__ == "__main__":
    unittest.main()
