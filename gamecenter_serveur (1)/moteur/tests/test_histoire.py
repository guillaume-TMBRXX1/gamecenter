"""Histoire de la ligue, records et carrières (moteur/histoire.py, bloc 2, étape 5).

Vérifie : la feuille de match (passe, course, réception, défense, field goals, point après touchdown, retours), les
carrières séparées par le nom quand une recrue reprend la place d'un retraité, une saison en cours (pas de champion),
les records, et sur la dernière semaine de data/weeks : totaux de saison = statistiques du notebook (week.json).

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import copy
import glob
import json
import os
import unittest

from moteur import histoire as H

ICI = os.path.dirname(os.path.abspath(__file__))
SEMAINES = sorted(glob.glob(os.path.join(ICI, "..", "..", "data", "weeks", "week_*")))


def joueur(pid, nom, pos):
    return {"id": pid, "name": nom, "pos": pos}


def feed(gid, plays, score, home="AAA", away="BBB", qb_a="Al Arm"):
    roster = {"home": [joueur(f"{home}_QB1", qb_a, "QB"), joueur(f"{home}_WR1", "Wes Hands", "WR"),
                       joueur(f"{home}_K1", "Kip Boot", "K"), joueur(f"{home}_RB1", "Rex Run", "RB")],
              "away": [joueur(f"{away}_LB1", "Lou Hit", "LB"), joueur(f"{away}_WR2", "Ray Back", "WR")]}
    return {"game": {"id": gid, "home": {"abbr": home, "roster": roster["home"]},
                     "away": {"abbr": away, "roster": roster["away"]}, "final_score": score}, "plays": copy.deepcopy(plays)}


def action(o, t, res, gain=0, car=None, pas=None, df=None, text="", **kw):
    return dict({"offense": o, "call": {"type": t}, "result": res, "gain": gain,
                 "players": {"carrier": car or {}, "passer": pas, "defender": df or {}}, "text": text}, **kw)


QB = {"id": "AAA_QB1", "name": "Al Arm"}
WR = {"id": "AAA_WR1", "name": "Wes Hands"}
K = {"id": "AAA_K1", "name": "Kip Boot"}
RB = {"id": "AAA_RB1", "name": "Rex Run"}

PLAYS = [
    action("away", "kickoff", "kickoff", car={"id": "BBB_WR2", "name": "Ray Back"},
           kick_return={"kick": 64, "return": 31, "touchback": False, "td": False}),
    action("home", "pass", "complete", 22, car=WR, pas=QB, df={"name": "Lou Hit", "credit": "TACKLE"}),
    action("home", "pass", "touchdown", 41, car=WR, pas=QB),
    action("home", "extra_point", "pat_good", car=K, conversion={"choice": "extra_point", "good": True}),
    action("home", "pass", "sack", -7, pas=QB, df={"name": "Lou Hit", "credit": "SACK"}),
    action("home", "pass", "interception", 0, car=WR, pas=QB, df={"name": "Lou Hit", "credit": "INTERCEPTION"}),
    action("home", "pass", "incomplete", 0, car=WR, pas=QB),
    action("home", "run", "run", 12, car=RB),
    action("home", "run", "touchdown", 3, car=RB),
    action("home", "two_point", "two_point_good", 2, car=RB, conversion={"choice": "two_point", "good": True}),
    action("home", "field_goal", "field_goal_good", car=K, text="Field goal good, 47 yds"),
    action("home", "field_goal", "field_goal_missed", car=K, text="Field goal missed, 55 yds"),
]


class TestFeuille(unittest.TestCase):
    def setUp(self):
        self.F = H.feuille_de_match(feed("w9-r01", PLAYS, {"home": 18, "away": 0}))
        self.J = {j["name"]: j for j in self.F["joueurs"].values()}

    def test_passe_reception(self):
        q, w = self.J["Al Arm"], self.J["Wes Hands"]
        self.assertEqual((q["cmp"], q["att"], q["pyd"], q["ptd"], q["pint"]), (2, 4, 63, 1, 1))   # sack à part
        self.assertEqual((w["tgt"], w["rec"], w["yd"], w["td"], w["lng"]), (4, 2, 63, 1, 41))

    def test_course_et_transformation_a_2_points(self):
        b = self.J["Rex Run"]
        self.assertEqual((b["car"], b["ryd"], b["rtd"], b["lng"]), (2, 15, 1, 12))   # 2 points : ni yards ni TD

    def test_defense_coups_de_pied_retours(self):
        d, k, r = self.J["Lou Hit"], self.J["Kip Boot"], self.J["Ray Back"]
        self.assertEqual((d["tk"], d["sk"], d["int"], d["team"]), (1, 1, 1, "BBB"))
        self.assertEqual((k["fgm"], k["fga"], k["fg_lng"], k["xpm"], k["xpa"]), (1, 2, 47, 1, 1))
        self.assertEqual((r["kr"], r["kry"], r["kr_lng"], r["team"]), (1, 31, 31, "BBB"))
        self.assertEqual(self.F["score"], {"home": 18, "away": 0})


def semaine(index, matchs, champion=None, terminee=False):
    sched = [g for g, _ in matchs]
    return {"index": index, "start": f"2026-10-{index:02d}", "terminee": terminee,
            "doc": {"teams": {"AAA": {}, "BBB": {}}, "schedule": sched, "champion": champion,
                    "runner_up": ("BBB" if champion == "AAA" else "AAA") if champion else None},
            "matchs": [(g, H.feuille_de_match(f)) for g, f in matchs]}


class TestHistoire(unittest.TestCase):
    def setUp(self):
        f1 = feed("w1-r01", PLAYS, {"home": 18, "away": 0})
        f2 = feed("w1-final", PLAYS[:3], {"home": 7, "away": 3})
        # semaine 2 : la recrue « Bo New » a repris la place AAA_QB1 (retraite de Al Arm)
        f3 = feed("w2-r01", PLAYS[1:3], {"home": 7, "away": 10}, qb_a="Bo New")
        for P in f3["plays"]:
            P["players"]["passer"] = {"id": "AAA_QB1", "name": "Bo New"}
        self.h = H.histoire([
            semaine(1, [({"id": "w1-r01", "phase": "regular"}, f1),
                        ({"id": "w1-final", "phase": "ai_bowl", "home": "AAA", "away": "BBB"}, f2)],
                    champion="AAA", terminee=True),
            semaine(2, [({"id": "w2-r01", "phase": "regular"}, f3)])])

    def test_saisons(self):
        s1, s2 = self.h["seasons"]
        self.assertEqual((s1["champion"], s1["runner_up"], s1["final"]["score"]), ("AAA", "BBB", {"home": 7, "away": 3}))
        self.assertEqual(s1["best_record"], {"team": "AAA", "w": 1, "l": 0, "t": 0})   # saison régulière seulement
        self.assertFalse(s2["complete"])
        self.assertIsNone(s2["champion"])                                              # saison en cours : pas de champion
        self.assertEqual(s1["leaders"]["pyd"]["value"], 126)

    def test_franchises(self):
        f = {x["team"]: x for x in self.h["franchises"]}
        self.assertEqual((f["AAA"]["titles"], f["AAA"]["finals"], f["AAA"]["w"], f["AAA"]["l"]), (1, 1, 1, 1))
        self.assertEqual((f["BBB"]["titles"], f["BBB"]["finals"], f["BBB"]["w"]), (0, 1, 1))
        self.assertEqual(self.h["franchises"][0]["team"], "AAA")

    def test_carrieres_recrue_separee(self):
        c = H.carriere(self.h, "AAA_QB1")
        self.assertEqual([x["name"] for x in c], ["Bo New", "Al Arm"])                 # le plus récent d'abord
        al = c[1]
        self.assertEqual([s["week"] for s in al["seasons"]], [1])
        self.assertEqual((al["total"]["pyd"], al["total"]["games"]), (126, 2))
        self.assertEqual(al["ranks"]["pyd"], [1, 2])
        self.assertEqual(c[0]["total"]["pyd"], 63)

    def test_records(self):
        r = self.h["records"]
        top = r["game"]["players"]["pyd"]
        self.assertEqual([(x["name"], x["value"], x["game"]) for x in top[:2]],
                         [("Al Arm", 63, "w1-r01"), ("Al Arm", 63, "w1-final")])
        self.assertEqual(r["game"]["players"]["lng"][0]["value"], 41)
        self.assertEqual(r["game"]["players"]["fg_lng"][0]["value"], 47)
        self.assertEqual(r["game"]["teams"]["margin"][0], {"week": 1, "game": "w1-r01", "phase": "regular",
                                                           "team": "AAA", "opp": "BBB", "value": 18, "score": "18-0"})
        self.assertEqual(r["season"]["players"]["pyd"][0]["value"], 126)
        self.assertEqual([x["name"] for x in r["career"]["pyd"]], ["Al Arm", "Bo New"])
        self.assertTrue(all(len(v) <= H.TOP for v in r["career"].values()))


@unittest.skipUnless(SEMAINES, "pas de semaine dans data/weeks")
class TestDonneesReelles(unittest.TestCase):
    """Les totaux de saison recalculés depuis les GameFeed = les statistiques du notebook (week.json, playoffs compris)."""
    CORRESP = {"pass_att": "att", "comp": "cmp", "pass_yds": "pyd", "pass_td": "ptd", "ints": "pint", "rush_att": "car",
               "rush_yds": "ryd", "rush_td": "rtd", "targets": "tgt", "rec": "rec", "rec_yds": "yd", "rec_td": "td",
               "tackles": "tk", "sacks": "sk", "def_int": "int", "passes_defended": "pd", "fg_made": "fgm",
               "fg_att": "fga"}

    def test_totaux_egaux_au_notebook(self):
        d = SEMAINES[-1]
        with open(os.path.join(d, "week.json"), encoding="utf-8") as fh:
            doc = json.load(fh)
        matchs = []
        for g in doc["schedule"]:
            with open(os.path.join(d, g["feed"]), encoding="utf-8") as fh:
                matchs.append((g, H.feuille_de_match(json.load(fh))))
        h = H.histoire([{"index": doc["week"]["index"], "start": doc["week"]["start"], "doc": doc,
                         "matchs": matchs, "terminee": True}])
        tot = {}
        for c in h["careers"].values():
            tot[c["id"]] = c["total"]
        ecarts = [(p["id"], a, p[a], tot.get(p["id"], {}).get(b, 0)) for p in doc["stats"]["all_games"]["players"]
                  for a, b in self.CORRESP.items() if tot.get(p["id"], {}).get(b, 0) != p[a]]
        self.assertEqual(ecarts, [])
        self.assertEqual(h["seasons"][0]["champion"], doc["champion"])
        f = {x["team"]: x for x in h["franchises"]}
        for r in doc["standings"]:
            self.assertEqual((f[r["team"]]["w"], f[r["team"]]["l"], f[r["team"]]["t"]), (r["w"], r["l"], r["t"]), r["team"])


if __name__ == "__main__":
    unittest.main()
