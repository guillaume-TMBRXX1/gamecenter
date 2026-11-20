"""Badges (moteur/badges.py, programme/Badges_plan.md, BD-1).

  Règles      chaque badge du catalogue, ses paliers et sa progression ; semaines actives (visites, paris, votes) et
              séries avec des trous ; rien pour un invité ; rien pour la mise, le volume, les recharges ou le solde
  Écriture    nouveaux() : un badge nouveau ou un palier plus haut, jamais une baisse
  Serveur     /api/me note le jour de visite (une ligne par jour) ; badges_donnees lit les paris réglés (type, cote,
              sélections), le compte, les jours ; un invité n'a aucun badge ; GC_BADGES=off n'écrit rien

    python -m unittest moteur.tests.test_badges        (depuis « gamecenter_serveur (1) »)
"""
import os
import unittest
from datetime import datetime
from unittest import mock

from moteur import badges as B
from moteur.tests import test_serveur as ts


def ms(s):
    return int(datetime.fromisoformat(s).replace(tzinfo=B.TZ).timestamp() * 1000)


def par_cle(D):
    return {b["key"]: b for b in B.evaluer(D)}


class Catalogue(unittest.TestCase):
    def test_complet(self):
        cles = [c[0] for c in B.CATALOGUE]
        self.assertEqual(len(cles), len(set(cles)))
        self.assertEqual(len(cles), 20)
        for c in B.CATALOGUE:
            self.assertIn(c[2], B.CATEGORIES)
            self.assertEqual(list(c[3]), sorted(c[3]))
        out = B.evaluer({"account": True})
        self.assertEqual([b["key"] for b in out], cles)
        self.assertFalse(any(b["earned"] for b in out))          # un compte neuf : rien


class Fidelite(unittest.TestCase):
    def test_founding_fan(self):
        self.assertTrue(par_cle({"account": True, "acct_at": ms("2026-12-31T23:59:00")})["founding_fan"]["earned"])
        self.assertFalse(par_cle({"account": True, "acct_at": ms("2027-01-01T00:00:00")})["founding_fan"]["earned"])

    def test_semaines_actives_et_series(self):
        # visites en semaines 1, 2, 3, 5 ; un pari en semaine 6 ; un vote en semaine 7 (lundi où il s'applique)
        D = {"account": True, "days": ["2026-11-02", "2026-11-10", "2026-11-17", "2026-11-30"],
             "bets": [{"week": "2026-12-07", "day": "2026-12-08", "status": "open", "kind": "ml", "price_dec": 2.0}],
             "fan_votes": [{"week": "2026-12-14", "majority": False}]}
        self.assertEqual(len(B.semaines_actives(D)), 6)
        b = par_cle(D)
        self.assertEqual((b["season_ticket"]["value"], b["season_ticket"]["tier"], b["season_ticket"]["next"]), (6, 1, 12))
        self.assertEqual(b["season_ticket"]["tier_name"], "bronze")
        self.assertEqual((b["streak"]["value"], b["streak"]["tier"]), (3, 1))   # 30/11, 07/12, 14/12 (le trou du 23/11)

    def test_tous_les_jours_lundi_et_finale(self):
        D = {"account": True, "days": ["2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-22"],
             "weeks": [{"start": "2026-11-16", "final_day": "2026-11-22"}]}
        b = par_cle(D)
        self.assertTrue(b["every_day"]["earned"])
        self.assertTrue(b["opening_day"]["earned"] and b["final_night"]["earned"])
        D["days"] = D["days"][1:4]
        b = par_cle(D)
        self.assertFalse(b["every_day"]["earned"] or b["opening_day"]["earned"] or b["final_night"]["earned"])
        self.assertEqual(b["every_day"]["value"], 3)


class Supporter(unittest.TestCase):
    def test_true_fan_votes_draft(self):
        now = ms("2026-11-20T12:00:00")
        D = {"account": True, "fav_team_at": now - 12 * B.SEMAINE_MS - 1, "now": now,
             "fan_votes": [{"week": w, "majority": i % 2 == 0}
                           for i, w in enumerate(("2026-08-03", "2026-08-10", "2026-08-17", "2026-08-24", "2026-08-31"))] +
                          [{"week": "2026-11-23", "majority": True}] * 3,
             "draft_votes": [{"week": "2026-11-16", "picked": False}]}
        b = par_cle(D)
        self.assertEqual((b["true_fan"]["value"], b["true_fan"]["tier_name"]), (12, "silver"))
        self.assertEqual((b["front_office"]["value"], b["front_office"]["tier"]), (6, 1))
        self.assertEqual(b["called_vote"]["value"], 6)
        self.assertTrue(b["called_vote"]["earned"])
        self.assertTrue(b["draft_day"]["earned"])
        self.assertFalse(b["scouts_pick"]["earned"])
        D["draft_votes"].append({"week": "2026-11-23", "picked": True})
        self.assertTrue(par_cle(D)["scouts_pick"]["earned"])


class LectureDuJeu(unittest.TestCase):
    def b(self, **k):
        x = {"week": "2026-11-16", "day": "2026-11-17", "status": "won", "kind": "ml", "price_dec": 2.0, "legs": 1}
        x.update(k)
        return x

    def test_upset_combo_perfect(self):
        D = {"account": True, "bets": [self.b(price_dec=2.95), self.b(kind="sp", price_dec=3.5)]}
        self.assertFalse(par_cle(D)["upset_caller"]["earned"])           # +195 ; un spread ne compte pas
        D["bets"].append(self.b(price_dec=3.0))
        self.assertTrue(par_cle(D)["upset_caller"]["earned"])            # +200 pile
        self.assertTrue(par_cle(D)["perfect_day"]["earned"])             # 3 paris gagnés le 17
        D["bets"].append(self.b(status="lost"))
        self.assertFalse(par_cle(D)["perfect_day"]["earned"])
        D["bets"] += [self.b(day="2026-11-18"), self.b(day="2026-11-18"), self.b(day="2026-11-18", status="open")]
        self.assertFalse(par_cle(D)["perfect_day"]["earned"])            # 2 réglés seulement le 18
        D["bets"].append(self.b(day="2026-11-18", status="cashed"))
        self.assertFalse(par_cle(D)["perfect_day"]["earned"])            # un cash-out n'est pas un pari gagné
        self.assertFalse(par_cle(D)["combo"]["earned"])
        D["bets"].append(self.b(kind="combo", legs=2))
        self.assertFalse(par_cle(D)["combo"]["earned"])
        D["bets"].append(self.b(kind="sgp", legs=3))
        self.assertTrue(par_cle(D)["combo"]["earned"])

    def test_classements(self):
        b = par_cle({"account": True, "league_wins": 1, "top10_weeks": 2})
        self.assertTrue(b["top_league"]["earned"] and b["top10"]["earned"])

    def test_rien_pour_la_mise(self):
        """Mises énormes, centaines de paris perdus, recharges, solde : aucun badge de lecture du jeu."""
        D = {"account": True, "stake_total": 1e6, "refills": 50, "balance": 1e7,
             "bets": [self.b(status="lost", price_dec=10.0, stake=1e5) for _ in range(500)]}
        b = par_cle(D)
        for k in ("upset_caller", "perfect_day", "combo", "top_league", "top10"):
            self.assertFalse(b[k]["earned"], k)


class Communaute(unittest.TestCase):
    def test_ligues_news_pro(self):
        b = par_cle({"account": True, "leagues_owned": [2, 4], "news_votes": 51, "pro": True})
        self.assertTrue(b["league_founder"]["earned"])
        self.assertEqual((b["recruiter"]["value"], b["recruiter"]["earned"]), (4, False))   # 1 + 3, le fondateur exclu
        self.assertEqual((b["newsroom"]["tier_name"], b["newsroom"]["next"]), ("silver", 150))
        self.assertTrue(b["insights_pro"]["earned"])
        self.assertFalse(par_cle({"account": True, "leagues_owned": [2]})["league_founder"]["earned"])


class Invite(unittest.TestCase):
    def test_progression_sans_badge(self):
        D = {"account": False, "days": ["2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20"],
             "news_votes": 12, "pro": True}
        out = par_cle(D)
        self.assertFalse(any(b["earned"] for b in out.values()))
        self.assertEqual((out["every_day"]["value"], out["newsroom"]["value"]), (5, 12))
        self.assertEqual(B.gagnes(D), {})


class Ecriture(unittest.TestCase):
    def test_jamais_une_baisse(self):
        self.assertEqual(B.nouveaux({"season_ticket": 2}, {"season_ticket": 2, "combo": 1}), {"combo": 1})
        self.assertEqual(B.nouveaux({"season_ticket": 2}, {"season_ticket": 3}), {"season_ticket": 3})
        self.assertEqual(B.nouveaux({"season_ticket": 3}, {"season_ticket": 1}), {})
        D = {"account": True, "news_votes": 60}
        self.assertEqual(B.gagnes(D), B.gagnes(D))                        # déterministe
        self.assertEqual(B.gagnes(D), {"newsroom": 2})


class Serveur(ts.Base):
    def _jours(self, pid):
        with ts.serveur.db() as c:
            return [r[0] for r in c.execute("SELECT day FROM player_days WHERE player=? ORDER BY day", (pid,))]

    def test_visites_paris_et_compte(self):
        g1, g2, g3 = self.reg[0], self.reg[1], self.reg[2]
        ts.a_l_heure(g1["ko"] - 120_000)
        tok = ts.appel(ts.serveur.api_register, {"pseudo": "Badge Test", "password": "motdepasse1"})["token"]
        p = ts.serveur.player_by_token(tok)
        ts.serveur._VUS.clear()
        ts.serveur.api_me(tok); ts.serveur.api_me(tok)
        self.assertEqual(len(self._jours(p["id"])), 1)                   # une ligne par jour, quel que soit le nombre d'appels
        r = self.parier(tok, [self.pick(g1["id"], stake=10), self.pick(g2["id"], "tot", "over", stake=10)],
                        combos=[{"stake": 5, "legs": [self.pick(g1["id"], "ml", "away"), self.pick(g2["id"]),
                                                      self.pick(g3["id"], "sp", "home")]}])
        self.assertEqual(len(r["accepted"]), 3, r)
        ts.a_l_heure(max(g["end"] for g in (g1, g2, g3)) + 1000)
        ts.serveur.api_me(tok)
        D = ts.serveur.badges_donnees(ts.serveur.player_by_token(tok), ts.serveur.now_ms())
        self.assertTrue(D["account"] and D["acct_at"])
        self.assertTrue(1 <= len(D["days"]) <= 2)
        self.assertEqual(sorted(b["kind"] for b in D["bets"]), ["combo", "ml", "tot"])
        combo = next(b for b in D["bets"] if b["kind"] == "combo")
        self.assertEqual(combo["legs"], 3)
        self.assertTrue(all(b["status"] in ("won", "lost", "push") for b in D["bets"]))
        out = {b["key"]: b for b in B.evaluer(D)}
        self.assertTrue(out["founding_fan"]["earned"] or D["acct_at"] >= ms("2027-01-01T00:00:00"))
        self.assertGreaterEqual(out["season_ticket"]["value"], 1)
        self.assertEqual(out["combo"]["earned"], combo["status"] == "won")

    def test_invite_et_interrupteur(self):
        ts.a_l_heure(self.reg[0]["ko"])
        tok = ts.appel(ts.serveur.api_new_player, {"name": "Invité"})["token"]
        p = ts.serveur.player_by_token(tok)
        ts.serveur._VUS.clear()
        with mock.patch.dict(os.environ, {"GC_BADGES": "off"}):
            ts.serveur.api_me(tok)
        self.assertEqual(self._jours(p["id"]), [])                         # coupé : rien d'écrit
        ts.serveur.api_me(tok)
        self.assertEqual(len(self._jours(p["id"])), 1)                     # un invité : ses jours comptent s'il crée un compte
        D = ts.serveur.badges_donnees(p, ts.serveur.now_ms())
        self.assertFalse(D["account"])
        self.assertEqual(B.gagnes(D), {})


if __name__ == "__main__":
    unittest.main()
