"""Front office FO-1 : les leviers des supporters (moteur/supporters.py).

Catalogue et ordre des options, rotation des questions, placement dans les bornes de chaque coordinateur (les bands
du notebook, lues dans la cellule 12.1, et les tables des leviers 4-5), rien de reporté dans la semaine suivante
(restauration), fichier GC_FANS absent ou faux = les coordinateurs, poids de profondeur (budget conservé),
question de la semaine suivante (fan_vote), interrupteur du notebook.

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import ast
import copy
import json
import os
import re
import tempfile
import unittest
from types import SimpleNamespace as NS

from moteur import supporters as fo

ICI = os.path.dirname(os.path.abspath(__file__))
NOTEBOOK = os.path.join(ICI, "..", "..", "NFL_Sim_GameCenter.ipynb")
EQUIPES_24 = ["CTX", "VEC", "AEG", "MNL", "AXM", "GLT", "CPH", "NVA", "PLS", "ONX", "FRG", "MRD", "APX", "LTC", "ZPH",
              "BST", "GRZ", "MRG", "GMB", "PRM", "SPK", "CTD", "TDL", "CMT"]


def _cellules():
    nb = json.load(open(NOTEBOOK, encoding="utf-8"))
    return ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]


def _bands_du_notebook():
    """{abbr: (bands offensives, bands défensives, réglages)} lus dans FRANCHISE_SPECS (cellule 12.1)."""
    src = next(s for s in _cellules() if "12.1 — LIGUE IA" in s[:400])
    out, abbr = {}, None
    for ligne in src.splitlines():
        m = re.match(r'\s+"([A-Z]{3})": dict\(', ligne)
        if m:
            abbr = m.group(1)
            out[abbr] = {"off": {}, "def": {}}
        if abbr is None:
            continue
        b = re.search(r"bands=(\{[^}]*\})", ligne)
        if b:
            d = ast.literal_eval(b.group(1))
            out[abbr]["def" if "blitz_rate" in d else "off"].update(d)
        for k in ("go_max_to_go", "go_min_yard_line", "pass_shift", "blitz_rate"):
            v = re.search(rf"\b{k}=(-?[0-9.]+)", ligne)
            if v:
                out[abbr].setdefault("val", {})[k] = ast.literal_eval(v.group(1))
    return out


def staff(bo, bd, go=2, ps=0.0, br=0.15):
    return NS(offense=NS(go_max_to_go=go, go_min_yard_line=45, pass_shift=ps, bands=bo),
              defense=NS(blitz_rate=br, coverage_weights={"MAN": 1.0, "ZONE": 1.0}, bands=bd))


def staffs_24():
    B = _bands_du_notebook()
    out = {}
    for a in EQUIPES_24:
        v = B[a]["val"]
        out[a] = staff(B[a]["off"], B[a]["def"], go=v["go_max_to_go"], ps=v["pass_shift"], br=v["blitz_rate"])
    return out


class TestCatalogue(unittest.TestCase):
    def test_options_dans_l_ordre(self):
        attendu = {"quatrieme": ["prudent", "coordinateur", "agressif"],
                   "course_passe": ["plus_course", "coordinateur", "plus_passe"],
                   "blitz": ["moins", "coordinateur", "plus"],
                   "couverture": ["zone", "coordinateur", "homme"],
                   "profondeur": ["courtes", "coordinateur", "longues"]}
        self.assertEqual({lv: fo.options(lv) for lv in fo.LEVIERS}, attendu)
        for lv, d in fo.LEVIERS.items():
            self.assertIn(d["side"], ("offense", "defense"))
            self.assertTrue(d["label"] and d["question"])
            self.assertTrue(all(l.isascii() and l for _, l in d["options"]), lv)    # intitulés anglais (site)

    def test_rotation(self):
        self.assertEqual(sorted(fo.ROTATION), sorted(fo.LEVIERS))
        n = len(fo.ROTATION)
        self.assertEqual(fo.levier_de_semaine(fo.ORIGINE), "quatrieme")
        semaines = [fo.levier_de_semaine(i) for i in range(fo.ORIGINE, fo.ORIGINE + 2 * n)]
        self.assertEqual(semaines[:n], list(fo.ROTATION))
        self.assertEqual(semaines[n:], list(fo.ROTATION))                      # fixe, cyclique
        for i in range(1, 40):
            self.assertNotEqual(fo.levier_de_semaine(i), fo.levier_de_semaine(i + 1))   # alterne chaque semaine
            self.assertEqual(fo.levier_de_semaine(i), fo.levier_de_semaine(i))          # déterministe

    def test_controle_24(self):
        S = staffs_24()
        self.assertEqual(fo.controle(EQUIPES_24, S), [])
        self.assertEqual(set(fo.BORNES_COUVERTURE), set(EQUIPES_24))
        self.assertEqual(set(fo.BORNES_PROFONDEUR), set(EQUIPES_24))


class TestBornes(unittest.TestCase):
    def test_chaque_coordinateur_chaque_levier(self):
        for a, s in staffs_24().items():
            for lv in fo.LEVIERS:
                rec = {}
                vals = []
                for c in fo.options(lv):
                    sem = {}
                    s2 = copy.deepcopy(s)
                    rec = fo.appliquer(s2, a, lv, c, sem)
                    lo, hi = rec["bands"]
                    self.assertTrue(lo <= rec["value"] <= hi, (a, lv, c, rec))
                    if c == fo.COORD:
                        self.assertEqual(rec["value"], rec["coordinator"])
                        self.assertEqual(sem, {})
                        self.assertEqual(vars(s2.offense), vars(s.offense))
                        self.assertEqual(vars(s2.defense), vars(s.defense))
                    vals.append(rec["value"])
                self.assertTrue(vals[0] <= vals[1] <= vals[2], (a, lv, vals))      # bas ≤ coordinateur ≤ haut
                self.assertEqual(vals[0], rec["bands"][0])
                self.assertEqual(vals[2], rec["bands"][1])

    def test_entier_pour_le_4e_essai(self):
        s = staff({"go_max_to_go": (1, 3), "pass_shift": (-0.1, 0.1)}, {"blitz_rate": (0.1, 0.2)})
        fo.appliquer(s, "CTX", "quatrieme", "agressif", {})
        self.assertIsInstance(s.offense.go_max_to_go, int)
        self.assertEqual(s.offense.go_max_to_go, 3)
        self.assertEqual(fo.placer((1, 4), "milieu", entier=True), 3)
        self.assertEqual(fo.placer((0.1, 0.2), "milieu"), 0.15)

    def test_ligne_du_4e_essai(self):
        """Décision du 09/11 : la ligne (go_min_yard_line) bouge aussi de LIGNE_4E yards, bornée, puis restaurée."""
        self.assertEqual(fo.LIGNE_4E, 8)
        for a, s in staffs_24().items():
            ligne = s.offense.go_min_yard_line
            vus = {}
            for c in fo.options("quatrieme"):
                s2 = copy.deepcopy(s)
                rec = fo.appliquer(s2, a, "quatrieme", c, {})
                v = s2.offense.go_min_yard_line
                self.assertTrue(fo.LIGNE_4E_BORNES[0] <= v <= fo.LIGNE_4E_BORNES[1] or v == ligne, (a, c, v))
                vus[c] = v
                fo.restaurer(s2, a, "quatrieme", rec, {})
                self.assertEqual(s2.offense.go_min_yard_line, ligne)
            self.assertTrue(vus["prudent"] >= vus["coordinateur"] == ligne >= vus["agressif"], (a, vus))

    def test_leviers_sans_attribut(self):
        s = staff({}, {})
        sem = {}
        r = fo.appliquer(s, "BST", "couverture", "homme", sem)
        self.assertEqual(sem["man_weight"]["BST"], fo.BORNES_COUVERTURE["BST"][1])
        self.assertEqual(r["coordinator"], 1.0)
        fo.restaurer(s, "BST", "couverture", r, sem)
        self.assertEqual(sem, {"man_weight": {}})


class TestPasDeReport(unittest.TestCase):
    def test_restaurer_remet_le_coordinateur(self):
        for a, s in staffs_24().items():
            avant = copy.deepcopy((vars(s.offense), vars(s.defense)))
            for lv in fo.LEVIERS:
                for c in fo.options(lv):
                    sem = {}
                    rec = fo.appliquer(s, a, lv, c, sem)
                    fo.restaurer(s, a, lv, rec, sem)
                    self.assertFalse(any(sem.values()))
                    self.assertEqual((vars(s.offense), vars(s.defense)), avant, (a, lv, c))

    def test_notebook_restaure_avant_l_ajustement(self):
        """run_week (14.1) restaure les choix avant weekly_adjustment / staffs_next_week."""
        src = next(s for s in _cellules() if "14.1 — SAISON" in s[:400])
        i_r, i_a = src.index("supporters_restaurer"), src.index("weekly_adjustment(")
        i_n = src.index('week["staffs_next_week"]')
        self.assertLess(i_r, i_a)
        self.assertLess(i_a, i_n)


class TestFichier(unittest.TestCase):
    EQ = ["CTX", "VEC", "AEG"]

    def ok(self, **kw):
        d = {"version": 1, "week": "2026-11-16", "lever": "quatrieme",
             "teams": {"CTX": {"choice": "agressif", "votes": 12}, "VEC": {"choice": "prudent", "votes": 7}}}
        d.update(kw)
        return d

    def coordinateurs(self, r):
        return all(v["choice"] == fo.COORD and v["source"] == fo.SOURCE_COORD for v in r.values())

    def test_valide(self):
        r = fo.choix_de_semaine(self.ok(), "2026-11-16", "quatrieme", self.EQ)
        self.assertEqual(r["CTX"], {"choice": "agressif", "source": "fans", "votes": 12})
        self.assertEqual(r["VEC"]["choice"], "prudent")
        self.assertEqual(r["AEG"], {"choice": fo.COORD, "source": "coordinators", "votes": 0})

    def test_absent_ou_illisible(self):
        self.assertIsNone(fo.lire_fichier(None))
        self.assertIsNone(fo.lire_fichier("/nexiste/pas.json"))
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "f.json")
            open(p, "w").write("{pas du json")
            self.assertIsNone(fo.lire_fichier(p))
            open(p, "w").write("[1, 2]")
            self.assertIsNone(fo.lire_fichier(p))
            json.dump(self.ok(), open(p, "w"))
            self.assertEqual(fo.lire_fichier(p)["lever"], "quatrieme")
        self.assertTrue(self.coordinateurs(fo.choix_de_semaine(None, "2026-11-16", "quatrieme", self.EQ)))

    def test_faux(self):
        cas = [self.ok(lever="blitz"), self.ok(week="2026-11-09"), self.ok(teams=[1]), self.ok(teams=None),
               self.ok(teams={"CTX": {"choice": "nimporte", "votes": 50}}),
               self.ok(teams={"CTX": {"choice": "agressif", "votes": 4}}),                  # moins de 5 votes
               self.ok(teams={"CTX": {"choice": "agressif", "votes": "x"}}),
               self.ok(teams={"CTX": "agressif"}),
               self.ok(teams={"XXX": {"choice": "agressif", "votes": 50}}),                 # franchise inconnue
               self.ok(teams={"CTX": {"choice": "agressif", "votes": 10,
                                      "counts": {"prudent": 5, "agressif": 5}}})]          # égalité
        for d in cas:
            self.assertTrue(self.coordinateurs(fo.choix_de_semaine(d, "2026-11-16", "quatrieme", self.EQ)), d)
        self.assertTrue(self.coordinateurs(fo.choix_de_semaine(self.ok(), "2026-11-16", "inconnu", self.EQ)))


class TestProfondeur(unittest.TestCase):
    def test_budget_et_sens(self):
        lignes = [("a", "DEEP_POST", 2.0), ("b", "QUICK_SLANT", 3.0), ("c", "PLAY_ACTION", 1.0), ("d", "SCREEN", 1.0)]
        for k in (0.7, 1.3):
            w = fo.poids_profondeur(lignes, k)
            self.assertAlmostEqual(sum(w), 7.0)
            part = w[0] / sum(w)
            self.assertTrue(part > 2 / 7 if k > 1 else part < 2 / 7)
        self.assertEqual(fo.poids_profondeur(lignes, 1.0), [2.0, 3.0, 1.0, 1.0])


class TestChiffres(unittest.TestCase):
    """FO-4 : les chiffres de la semaine (écran Front office) depuis les GameFeed."""

    def feed(self):
        jeu = lambda off, down, typ, k, dk=None: {"offense": off, "down": down,
                                                 "call": {"type": typ, "concept": k, "defense": {"concept": dk}}}
        return {"plays": [jeu("home", 1, "run", "INSIDE_RUN", "BLITZ"), jeu("home", 2, "pass", "DEEP_POST", "MAN"),
                          jeu("home", 3, "pass", "QUICK_SLANT", "COVER_2"), jeu("home", 4, "punt", None),
                          jeu("away", 4, "run", "POWER", "MAN"), jeu("away", 1, "pass", "SCREEN", "BLITZ"),
                          jeu("away", 4, "field_goal", None), jeu("home", 1, "run", "KNEEL")]}

    def test_mesurer_et_chiffres(self):
        m = fo.mesurer_match(self.feed(), "CTX", "VEC")
        self.assertEqual(m["CTX"], {"q4": 1, "go4": 0, "snaps": 3, "runs": 1, "passes": 2, "longs": 1, "dsnaps": 2,
                                    "blitz": 1, "man": 1})
        self.assertEqual(m["VEC"], {"q4": 2, "go4": 1, "snaps": 2, "runs": 1, "passes": 1, "longs": 0, "dsnaps": 3,
                                    "blitz": 1, "man": 1})
        c = fo.chiffres("course_passe", {a: [v] for a, v in m.items()})
        self.assertEqual(c["teams"]["CTX"], {"value": round(1 / 3, 4), "games": 1})
        self.assertAlmostEqual(c["league"], (1 / 3 + 1 / 2) / 2, places=3)       # moyenne des valeurs des franchises
        self.assertEqual(fo.chiffres("quatrieme", {"CTX": [m["CTX"]]})["teams"]["CTX"]["value"], 0.0)
        self.assertIsNone(fo.chiffres("profondeur", {"X": []})["teams"]["X"]["value"])
        self.assertEqual(set(fo.MESURE), set(fo.LEVIERS))


class TestQuestion(unittest.TestCase):
    def test_fan_vote(self):
        S = staffs_24()
        for lv in fo.LEVIERS:
            q = fo.question(lv, 9, "2026-11-23", S)
            self.assertEqual(q["lever"], lv)
            self.assertEqual([o["id"] for o in q["options"]], fo.options(lv))
            self.assertEqual(set(q["teams"]), set(EQUIPES_24))
            for a, t in q["teams"].items():
                v = [t["values"][o] for o in fo.options(lv)]
                self.assertTrue(t["bands"][0] <= v[0] <= v[1] <= v[2] <= t["bands"][1], (lv, a, t))
            json.dumps(q)


class TestAudit(unittest.TestCase):
    """audit_moteur.py : fans.applied dans les bornes, levier de la rotation, rien de reporté, game.fans_plan."""

    def semaine(self):
        idx = fo.ORIGINE
        applied = {"CTX": {"choice": "agressif", "source": "fans", "votes": 9, "setting": "go_max_to_go",
                           "coordinator": 2, "value": 3, "bands": [1, 3]},
                   "VEC": {"choice": fo.COORD, "source": "coordinators", "votes": 2, "setting": "go_max_to_go",
                           "coordinator": 4, "value": 4, "bands": [3, 5]}}
        return {"week": {"index": idx}, "teams": {"CTX": {}, "VEC": {}},
                "fans": {"lever": fo.levier_de_semaine(idx), "applied": applied},
                "fan_vote": {"lever": fo.levier_de_semaine(idx + 1)},
                "adjustments": {"CTX": {"before": {"go_max_to_go": 2}}, "VEC": {"before": {"go_max_to_go": 4}}}}

    def bloquants(self, w, feed=None):
        import audit_moteur as audit
        A = audit.Audit()
        audit.check_fans(A, "w", w)
        if feed is not None:
            audit.check_fans_plan(A, "w", {"id": "g1", "home": "CTX", "away": "VEC"}, feed, w.get("fans"))
        return [m for lvl, *_, m in A.items if lvl == audit.BLOQUANT]

    def test_semaine_valide(self):
        w = self.semaine()
        plan = {"lever": w["fans"]["lever"], "home": {"choice": "agressif", "source": "fans", "votes": 9},
                "away": {"choice": fo.COORD, "source": "coordinators", "votes": 2}}
        self.assertEqual(self.bloquants(w, {"game": {"fans_plan": plan}}), [])
        self.assertEqual(self.bloquants({"teams": {}}, {"game": {}}), [])           # semaine d'avant FO-1

    def test_anomalies(self):
        w = self.semaine(); w["fans"]["applied"]["CTX"]["value"] = 4                  # hors des bornes
        self.assertTrue(self.bloquants(w))
        w = self.semaine(); w["adjustments"]["CTX"]["before"]["go_max_to_go"] = 3     # reporté dans l'ajustement
        self.assertTrue(self.bloquants(w))
        w = self.semaine(); w["fans"]["lever"] = fo.levier_de_semaine(fo.ORIGINE + 1)
        self.assertTrue(self.bloquants(w))
        w = self.semaine(); w["fans"]["applied"]["CTX"]["votes"] = 3                  # trop peu de votes
        self.assertTrue(self.bloquants(w))
        self.assertTrue(self.bloquants(self.semaine(), {"game": {}}))                # fans_plan manquant


class TestNotebook(unittest.TestCase):
    def test_interrupteur_et_branchement(self):
        cs = _cellules()
        c = next(s for s in cs if "12.2 quinquatricies" in s[:400])
        self.assertIn('GC_SUPPORTERS", "1") != "0"', c)
        s15 = next(s for s in cs if "15.1 — SEMAINE À LA DEMANDE" in s[:400])
        self.assertIn("GC_FANS", s15)
        i_snap = s15.index("apply_staff_snapshots(prev")
        i_app = s15.index("supporters_appliquer")
        i_run = s15.index("run_week(")
        self.assertTrue(i_snap < i_app < i_run)                 # après la reprise des staffs, avant les cotes
        self.assertIn("SUPPORTERS_ENABLED", s15)
        s131 = next(s for s in cs if "13.1 — COTES DU MOTEUR" in s[:400])
        self.assertEqual(s131.count('globals().get("supporters_cle", lambda: None)()'), 2)   # les deux clés du cache


if __name__ == "__main__":
    unittest.main()
