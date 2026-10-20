"""Vidéos verticales (bloc 2, étape 8) : choix des actions et du match (outils/video/choisir.py), bandeaux et son du
stade (outils/video/faire_video.py, sans filmer : le tournage est vérifié à la main et par le workflow « Vidéos »).

    python -m unittest discover -s moteur/tests -t .        (depuis « gamecenter_serveur (1) »)
"""
import glob
import json
import os
import re
import sys
import unittest
from datetime import datetime, timedelta

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
sys.path.insert(0, os.path.join(RACINE, "outils", "video"))
import choisir as C  # noqa: E402
import faire_video as V  # noqa: E402

SEMAINES = sorted(glob.glob(os.path.join(RACINE, "data", "weeks", "week_*")))
PARIS = re.compile(r"\b(odds|bets?|betting|wagers?|parlays?|gambl\w*|picks?|casino|stakes?|cash.?out)\b", re.I)


def action(t, r, gain=0, wp=0.5, down=1, to_go=10, los=60, offense="home", q=2, clock=600, text="", **kw):
    return dict({"call": {"type": t}, "result": r, "gain": gain, "win_prob_home": wp, "down": down, "to_go": to_go,
                 "los_x": los, "offense": offense, "quarter": q, "clock_start": clock, "text": text,
                 "after": {"score": {"home": 0, "away": 0}}}, **kw)


def feed(plays, p_home=0.5):
    return {"game": {"pregame_odds": {"p_home": p_home}}, "plays": plays}


class TestInteret(unittest.TestCase):
    def test_touchdown_et_bascule(self):
        F = feed([action("run", "run", 4, wp=0.52), action("pass", "touchdown", 30, wp=0.70)])
        self.assertGreater(C.interet(F, 1)[0], C.interet(F, 0)[0])
        self.assertEqual(C.interet(F, 1)[1], "touchdown")

    def test_decision_folle(self):
        # 4e et 6 dans son propre camp (attaque « home », ballon à 45 < 60), tenté et réussi
        F = feed([action("run", "run", 2, wp=0.5), action("pass", "complete", 9, wp=0.55, down=4, to_go=6, los=45)])
        n, why = C.interet(F, 1)
        self.assertIn("4th-and-6 gamble", why)
        rate = feed([action("run", "run", 2, wp=0.5), action("pass", "incomplete", 0, wp=0.45, down=4, to_go=6, los=45)])
        self.assertNotIn("gamble", C.interet(rate, 1)[1])

    def test_fin_de_match(self):
        F = feed([action("run", "run", 2, wp=0.30, q=4, clock=20),
                  action("field_goal", "field_goal_good", 0, wp=0.95, q=4, clock=4, text="Field goal good, 58 yds")])
        n, why = C.interet(F, 1)
        self.assertTrue(why.startswith("game-winning"), why)
        self.assertIn("58-yard field goal", why)
        self.assertEqual(V.titre_action(why, F["plays"][1]), "Game-winner: 58-yard field goal")


class TestEnjeu(unittest.TestCase):
    """Étape 8.2 : l'accroche du haut de la vidéo (sans dévoiler le résultat) et la bascule de probabilité."""
    G = {"home": "AXM", "away": "AEG"}

    def avec_score(self, home, away, **kw):
        avant = action("run", "run", 2, wp=0.5)
        avant["after"]["score"] = {"home": home, "away": away}
        return feed([avant, action(**kw)])

    def test_fin_de_match(self):
        F = self.avec_score(31, 31, t="pass", r="interception", wp=0.19, q=4, clock=14)
        self.assertEqual(C.enjeu(F, 1, self.G), "Tied 31–31 · 0:14 left")
        F = self.avec_score(28, 31, t="pass", r="touchdown", wp=0.9, q=4, clock=62, offense="home")
        self.assertEqual(C.enjeu(F, 1, self.G), "AXM down 28–31 · 1:02 left")
        F = self.avec_score(24, 24, t="run", r="touchdown", wp=0.9, q=5, clock=200)
        self.assertEqual(C.enjeu(F, 1, self.G), "Overtime · tied 24–24")
        F = self.avec_score(24, 27, t="run", r="touchdown", wp=0.9, q=5, clock=200, offense="home")
        self.assertEqual(C.enjeu(F, 1, self.G), "Overtime · AXM down 24–27")

    def test_quatrieme_essai_et_milieu_de_match(self):
        F = self.avec_score(7, 3, t="pass", r="complete", gain=9, wp=0.55, down=4, to_go=6, los=45, q=2, clock=100)
        self.assertEqual(C.enjeu(F, 1, self.G), "4th & 6 · own 35")
        F = self.avec_score(14, 10, t="run", r="run", gain=3, wp=0.6, q=2, clock=95)
        self.assertEqual(C.enjeu(F, 1, self.G), "AEG 10–14 AXM · Q2 1:35")

    def test_bascule(self):
        F = feed([action("run", "run", 2, wp=0.74), action("pass", "interception", wp=0.19)])
        self.assertEqual(C.bascule(F, 1, self.G), {"team": "AEG", "avant": 26, "apres": 81})
        F = feed([action("pass", "touchdown", wp=0.80)], p_home=0.40)
        self.assertEqual(C.bascule(F, 0, self.G), {"team": "AXM", "avant": 40, "apres": 80})

    def test_legendes(self):
        txt = V.legendes("Tied 31–31 · 0:14 left… Game-winner 🏈", "Intercepted.", V.question("game-winning takeaway"),
                         "#playoftheday", "x" * 120)
        self.assertEqual([l for l in txt.splitlines() if l.startswith("===")],
                         ["=== TikTok ===", "=== Pinned comment (TikTok) ===", "=== Instagram ===", "=== YouTube Shorts ==="])
        self.assertIn("snapline.live", txt.split("=== Pinned comment (TikTok) ===\n")[1].splitlines()[0])
        self.assertIsNone(PARIS.search(V.EPINGLE))
        titre = txt.split("=== YouTube Shorts ===\n")[1].splitlines()[0]
        self.assertTrue(titre.endswith(" #Shorts") and len(titre) <= 100, titre)
        self.assertEqual(V.raison("4th-and-6 gamble · touchdown"), "4th-and-6 go-for-it · touchdown")
        self.assertIsNone(PARIS.search(V.question("4th-and-6 gamble")))


class TestSonEtBandeaux(unittest.TestCase):
    def test_horloge(self):
        self.assertEqual(V.horloge(action("pass", "complete", q=4, clock=125, down=3, to_go=7)), "Q4 2:05 · 3rd & 7")
        self.assertEqual(V.horloge(action("field_goal", "field_goal_good", q=5, clock=4, down=1, to_go=10)), "OT 0:04")

    def test_evenements(self):
        tl = {"end": 30, "segments": [
            {"type": "card", "from": 0, "to": 2.5},
            {"type": "play", "result": "touchdown", "call": "pass", "td": True, "snap": 3.5, "res": 7.0, "speed": 1},
            {"type": "play", "result": "touchdown", "call": "pass", "td": True, "snap": 12.0, "res": 20.0, "speed": 0.5},
            {"type": "card", "from": 25, "to": 28}]}
        ev = V.evenements_son(tl)
        kinds = [(round(t, 2), k) for t, k, g in ev]
        self.assertIn((3.5, "snap"), kinds)
        self.assertIn((7.0, "react_td"), kinds)
        self.assertNotIn((12.0, "snap"), kinds)                     # le ralenti : pas de snap ni de sifflet
        self.assertIn((20.0, "react_td"), kinds)
        self.assertIn((25.1, "cheer_medium"), kinds)                # carton final
        tl["segments"].insert(0, {"type": "card", "kind": "stats", "from": 0, "to": 3})
        self.assertIn((0.2, "cheer_medium"), [(round(t, 2), k) for t, k, g in V.evenements_son(tl)])
        self.assertTrue(all(t >= 0 for t, k, g in ev))
        assets = V._assets()
        self.assertTrue(all(k in assets for _, k, _ in ev), "chaque son existe dans audio/manifest.json")


@unittest.skipUnless(SEMAINES, "pas de semaine dans data/weeks")
class TestSemaineReelle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc, cls.feeds = C.charger_semaine(SEMAINES[-1])
        cls.jour = C.jour_du_match(cls.doc["schedule"][0])

    def test_action_du_jour(self):
        a = C.action_du_jour(self.doc, self.feeds, self.jour)
        g = next(x for x in self.doc["schedule"] if x["id"] == a["game"])
        self.assertEqual(C.jour_du_match(g), self.jour)
        meilleur = max(C.interet(self.feeds[x["id"]], i)[0] for x in self.doc["schedule"] if C.jour_du_match(x) == self.jour
                       for i in range(len(self.feeds[x["id"]]["plays"])))
        self.assertEqual(a["note"], meilleur)
        self.assertEqual(a, C.action_du_jour(self.doc, self.feeds, self.jour))     # déterministe
        self.assertIsNone(C.action_du_jour(self.doc, self.feeds, "1999-01-01"))

    def test_plus_beau_match_et_resume(self):
        b = C.plus_beau_match(self.doc, self.feeds)
        notes = [C.spectacle(self.feeds[g["id"]], g) for g in self.doc["schedule"]]
        self.assertEqual(b["note"], max(notes))
        F = self.feeds[b["game"]]
        idx = C.resume(F)
        self.assertEqual(idx, sorted(idx))
        self.assertIn(len(F["plays"]) - 1, idx)
        scores = [i for i, P in enumerate(F["plays"]) if P["result"] in ("touchdown", "field_goal_good")]
        self.assertTrue(set(scores) <= set(idx) or len(idx) >= int(C.RESUME_MAX // C.DUREE_ACTION))
        self.assertTrue(C.RESUME_MIN <= len(idx) * C.DUREE_ACTION <= C.RESUME_MAX + C.DUREE_ACTION, len(idx))

    def test_plans_sans_paris(self):
        """Le plan de l'action du jour : l'action d'abord (pas de carton fixe), le ralenti avec la bascule en haut, le
        carton snapline.live ; aucun mot de paris dans les textes à l'écran ni dans les légendes (étape 8.2)."""
        g, seg, top, info, leg = V.plan_action(self.doc, self.feeds, self.jour)
        self.assertEqual([x["type"] for x in seg], ["play", "play", "card"])
        self.assertEqual(seg[1]["speed"], 0.5)
        self.assertIn("win probability", seg[1]["top"]["kicker"])
        self.assertEqual(seg[-1]["title"], "snapline.live")
        self.assertEqual(top["title"], info["enjeu"])
        textes = [leg, str(top), str(seg)]
        g, seg, top, info, leg2 = V.plan_resume(self.doc, self.feeds)
        textes += [leg2, str(top), str(seg)]
        g, seg, top, info, leg3 = V.plan_resume(self.doc, self.feeds, long=True)
        textes += [leg3, str(top), str(seg)]
        for t in textes:
            self.assertIsNone(PARIS.search(t), PARIS.search(t))

    def test_meilleure_action_matchs_termines(self):
        """« Best play so far » : jamais un match pas encore terminé (la semaine en cours est calculée d'avance)."""
        tz = C.TZ
        ko = sorted(datetime.fromisoformat(g["kickoff"]) for g in self.doc["schedule"])
        self.assertIsNone(C.meilleure_action([SEMAINES[-1]], ko[0] - timedelta(minutes=1)))
        maintenant = ko[len(ko) // 2]
        m = C.meilleure_action([SEMAINES[-1]], maintenant)
        g = next(x for x in self.doc["schedule"] if x["id"] == m["game"])
        self.assertLessEqual(datetime.fromisoformat(g["kickoff"]) + C.FINI_APRES, maintenant)
        tout = C.meilleure_action(SEMAINES, datetime(2100, 1, 1, tzinfo=tz))
        self.assertGreaterEqual(tout["note"], m["note"])
        g, seg, top, info, leg = V.plan_action(*C.charger_semaine(tout["dossier"]), None, tout)
        self.assertEqual(top["kicker"], "AI vs AI · best play so far")      # habillage « AI broadcast » (20/10)
        self.assertEqual(info["type"], "meilleure")

    def test_resume_court(self):
        """Étape 8.3 : résumé court ≤ ≈ 60 s, tous les scores s'ils tiennent (sinon le maximum d'actions), la dernière
        action, l'ordre du match ; le plan s'ouvre sur une action (pas de carton) et finit sur le score final."""
        for gid, F in list(self.feeds.items())[:40]:
            idx = C.resume_court(F)
            self.assertEqual(idx, sorted(idx))
            self.assertIn(len(F["plays"]) - 1, idx)
            n_max = int(C.COURT_MAX // C.COURT_ACTION)
            self.assertLessEqual(len(idx), n_max)
            scores = [i for i, P in enumerate(F["plays"]) if P.get("result") == "touchdown" or (P.get("kick_return") or {}).get("td")]
            self.assertTrue(set(scores) <= set(idx) or len(idx) == n_max, gid)
        g, seg, top, info, leg = V.plan_resume(self.doc, self.feeds)
        self.assertEqual(seg[0]["type"], "play")
        self.assertNotIn("quarter", [x.get("kind") for x in seg])
        self.assertEqual(seg[-1]["type"], "card")
        self.assertTrue(seg[-1]["kicker"].startswith("Final"))
        self.assertEqual(top["kicker"], "AI vs AI · game in 60 seconds")
        self.assertEqual(info["type"], "resume_court")
        g, seg_long, top, info, leg = V.plan_resume(self.doc, self.feeds, long=True)
        self.assertEqual(seg_long[0]["type"], "card")
        self.assertGreater(len(seg_long), len(seg))

    def test_presentation(self):
        """« What is Snapline? » : trois actions de trois matchs différents, terminés ; aucun mot de paris."""
        maintenant = datetime(2100, 1, 1, tzinfo=C.TZ)
        choix = C.trois_actions(SEMAINES, maintenant)
        self.assertEqual(len(choix), 3)
        self.assertEqual(len({a["game"] for a in choix}), 3)
        self.assertEqual(choix, C.trois_actions(SEMAINES, maintenant))          # déterministe
        semaines = {a["dossier"]: C.charger_semaine(a["dossier"])[0] for a in choix}
        top, seg, info, leg = V.plan_presentation(choix, semaines)
        self.assertEqual([x["type"] for x in seg], ["play", "play", "play", "card"])
        self.assertEqual([x["top"]["title"] for x in seg[:3]], V.PRESENTATION)
        self.assertTrue(all(os.path.exists(x["feed"]) for x in seg[:3]))
        self.assertEqual(seg[-1]["title"], "snapline.live")
        for t in (leg, str(seg)):
            self.assertIsNone(PARIS.search(t), PARIS.search(t))
        ko = min(datetime.fromisoformat(g["kickoff"]) for g in self.doc["schedule"])
        for a in C.trois_actions([SEMAINES[-1]], ko + C.FINI_APRES + timedelta(hours=3)):
            g = next(x for x in self.doc["schedule"] if x["id"] == a["game"])
            self.assertLessEqual(datetime.fromisoformat(g["kickoff"]) + C.FINI_APRES, ko + C.FINI_APRES + timedelta(hours=3))

    def test_joueur_et_champion(self):
        """Étape 8.6 a : joueur de la semaine (score fantasy, ses actions) et champion (après la Grand Final seulement),
        sur une semaine terminée ; cartons de statistiques ; aucun mot de paris."""
        fini = [d for d in SEMAINES if json.load(open(os.path.join(d, "week.json"), encoding="utf-8")).get("champion")]
        if not fini:
            self.skipTest("aucune semaine terminée")
        d = fini[-1]
        doc, feeds = C.charger_semaine(d)
        plus_tard = datetime(2100, 1, 1, tzinfo=C.TZ)
        r = C.joueur_de_la_semaine(d, plus_tard)
        j = r["joueur"]
        self.assertEqual(r, C.joueur_de_la_semaine(d, plus_tard))                       # déterministe
        self.assertTrue(1 <= len(r["actions"]) <= 3)
        for a in r["actions"]:
            g = next(x for x in doc["schedule"] if x["id"] == a["game"])
            self.assertTrue(C._implique(a["play"], g, j))
        top, seg, info, leg = V.plan_joueur(r, doc)
        self.assertEqual(seg[0]["type"], "stats")
        self.assertEqual(len(seg[0]["stats"]), 4)
        self.assertEqual(seg[-1]["title"], "snapline.live")
        ko = min(datetime.fromisoformat(g["kickoff"]) for g in doc["schedule"])
        self.assertIsNone(C.joueur_de_la_semaine(d, ko))
        fin = next(g for g in doc["schedule"] if g["phase"] == "ai_bowl")
        self.assertIsNone(C.champion(d, datetime.fromisoformat(fin["kickoff"]), SEMAINES))   # finale pas finie
        c = C.champion(d, plus_tard, SEMAINES)
        self.assertEqual(c["team"], doc["champion"])
        noms = sorted(os.path.basename(x) for x in SEMAINES if os.path.basename(x) <= os.path.basename(d))
        attendu = sum(json.load(open(os.path.join(os.path.dirname(d), n, "week.json"), encoding="utf-8")).get("champion") == c["team"]
                      for n in noms)
        self.assertEqual(c["titres"], attendu)
        self.assertEqual(C.champion(os.path.relpath(d), plus_tard, SEMAINES)["titres"], attendu)   # chemins mélangés
        for a in c["actions"]:
            g = next(x for x in doc["schedule"] if x["id"] == a["game"])
            self.assertIn(g["phase"], ("semifinal", "ai_bowl"))
            self.assertIn(c["team"], (g["home"], g["away"]))
        top, seg2, info, leg2 = V.plan_champion(c, doc)
        self.assertEqual(seg2[0]["stats"][0]["v"], f"{c['score'][0]}–{c['score'][1]}")
        self.assertGreater(c["score"][0], c["score"][1])
        for t in (leg, leg2, str(seg), str(seg2)):
            self.assertIsNone(PARIS.search(t), PARIS.search(t))
            self.assertNotIn("🏆", str(seg2))                                           # pas d'emoji à l'écran

    def test_match_hors_norme(self):
        """Étape 8.6 b : un record battu au moment du match (égaler ne suffit pas), sinon 100 points cumulés ; jamais un
        match pas encore terminé ; actions du score dans l'ordre ; aucun mot de paris."""
        plus_tard = datetime(2100, 1, 1, tzinfo=C.TZ)
        d = SEMAINES[-1]
        r = C.match_hors_norme(d, plus_tard, SEMAINES)
        tous = []
        for x in SEMAINES:
            w = json.load(open(os.path.join(x, "week.json"), encoding="utf-8"))
            tous += [(g["kickoff"], g["id"], C._valeurs(g), os.path.basename(x)) for g in w["schedule"] if g.get("result")]
        tous.sort()
        if r is not None:
            g = next(t for t in tous if t[1] == r["game"])
            self.assertEqual(g[3], os.path.basename(d))
            if r["previous"] is not None:
                avant = [t[2][r["kind"]] for t in tous if (t[0], t[1]) < (g[0], g[1])]
                self.assertEqual(r["previous"], max(avant))
                self.assertGreater(r["value"], r["previous"])
            else:
                self.assertGreaterEqual(r["value"], C.SEUIL_POINTS)
            doc, feeds = C.charger_semaine(d)
            top, seg, info, leg = V.plan_chiffres(r, doc, feeds)
            self.assertEqual(seg[0]["type"], "stats")
            idx = [x["index"] for x in seg if x["type"] == "play"]
            self.assertEqual(idx, sorted(idx))
            self.assertTrue(all(feeds[r["game"]]["plays"][i]["result"] in ("touchdown", "field_goal_good")
                                or (feeds[r["game"]]["plays"][i].get("kick_return") or {}).get("td")
                                or (feeds[r["game"]]["plays"][i].get("punt_return") or {}).get("td") for i in idx))   # 18/10 : retour de punt TD (semaine du 19/10)
            for t in (leg, str(seg)):
                self.assertIsNone(PARIS.search(t), PARIS.search(t))
        ko = min(datetime.fromisoformat(g["kickoff"]) for g in json.load(open(os.path.join(d, "week.json")))["schedule"])
        self.assertIsNone(C.match_hors_norme(d, ko, SEMAINES))                         # rien de joué : rien

    def test_franchise(self):
        """Étape 8.6 b : une franchise par semaine, toujours la même pour une semaine, les 24 sur 24 semaines ; légende
        et actions de cette franchise ; aucun mot de paris, pas de texte français de la bible à l'écran."""
        plus_tard = datetime(2100, 1, 1, tzinfo=C.TZ)
        d = SEMAINES[-1]
        f = C.franchise_de_la_semaine(d, SEMAINES, plus_tard)
        self.assertEqual(f["team"], C.franchise_de_la_semaine(d, SEMAINES, plus_tard)["team"])
        doc = json.load(open(os.path.join(d, "week.json"), encoding="utf-8"))
        equipes = sorted(doc["teams"])
        debut = min(json.load(open(os.path.join(x, "week.json")))["week"]["start"] for x in SEMAINES)
        rang = (datetime.fromisoformat(doc["week"]["start"]) - datetime.fromisoformat(debut)).days // 7
        self.assertEqual(f["team"], equipes[rang % len(equipes)])
        if f["legende"]:
            self.assertEqual(f["legende"]["team"], f["team"])
        for a in f["actions"]:
            w = json.load(open(os.path.join(a["dossier"], "week.json"), encoding="utf-8"))
            g = next(x for x in w["schedule"] if x["id"] == a["game"])
            self.assertIn(f["team"], (g["home"], g["away"]))
        top, seg, info, leg = V.plan_franchise(f, doc)
        self.assertEqual(seg[0]["type"], "stats")
        self.assertEqual(seg[-1]["title"], "snapline.live")
        for t in (leg, str(seg)):
            self.assertIsNone(PARIS.search(t), PARIS.search(t))
            for fr in (f["fiche"].get("style"), f["fiche"].get("identity")):
                if fr:
                    self.assertNotIn(fr, t)

    def test_score_fantasy(self):
        base = {k: 0 for k in ("pyd", "ptd", "pint", "ryd", "rtd", "yd", "td", "rec", "kry", "krtd", "tk", "sk", "int",
                               "pd", "fgm", "xpm")}
        self.assertEqual(C.score_fantasy(dict(base, pyd=300, ptd=3, pint=1)), 22.0)
        self.assertEqual(C.score_fantasy(dict(base, ryd=120, rtd=2, rec=4, yd=30)), 29.0)
        self.assertEqual(C.score_fantasy(dict(base, tk=8, sk=2, int=1)), 22.0)
        ch = V.chiffres_joueur(dict(base, pos="RB", ryd=700, rtd=5, car=0, yd=200, cmp=0, att=0, fga=0))
        self.assertEqual([x["l"] for x in ch][-1], "Carries")                          # les nuls en dernier

    def test_semaine_du_jour(self):
        self.assertEqual(os.path.basename(V.semaine_du(self.jour)), os.path.basename(SEMAINES[-1]))


if __name__ == "__main__":
    unittest.main()
