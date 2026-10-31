"""GameCenter — serveur de direct (étape 9).

Le serveur garde les semaines produites par le notebook (section 15.1) et ne montre au public QUE ce qui
s'est déjà passé : les actions d'un match arrivent une par une, à l'heure (6,5 s par action, une action de
décalage), les résultats, le classement, les futures et les affiches des playoffs seulement quand ils sont
connus. Les paris sont pris, vérifiés (cote, marché ouvert, solde) et réglés ici, avec un classement commun.
Comptes (étape 1, 03/10/2026) : pseudo + mot de passe facultatifs, posés sur la clé du joueur ; classement de la
saison = somme des gains nets de chaque semaine (comptes seulement). Voir /api/account/* et /api/leaderboard?scope=season.
Paris plus riches (étape 2, 03/10/2026) : combinés 2-6 sélections (une par match, pas de futures), cash-out à la valeur
juste − 5 % (/api/cashout), historique des semaines passées (/api/history).
Combinés sur un même match (section 86, 30/10/2026) : 2 ou 3 sélections d'un match (une par marché), avant le coup
d'envoi, cote calculée par moteur/meme_match.py (key = « sgp ») ; GC_SAME_GAME=off : refusés comme avant.

Lancer :  uvicorn serveur:app --host 0.0.0.0 --port 8000
Variables : GC_DATA (dossier des données, défaut ./data) · GC_SITE (gamecenter_source.html)
            GC_DEMO_AT (ISO, ex. 2026-10-05T12:59:00+02:00 : l'horloge du serveur démarre à cet instant ;
            « auto » = lundi 12:45 de la semaine la plus récente) · GC_AUTOGEN=1 (produit la semaine suivante
            tout seul, voir generer_semaine.py) · GC_ADMIN_KEY (sauvegarde, réinitialisation de mot de passe)
            GC_SEASON_START (facultatif, ex. 2026-10-05 : semaines plus anciennes hors classement de la saison)
            GC_CHAT (off par défaut, read, on : le chat, section « chat ») · GC_CHAT_DAYS (conservation, défaut 30 j)
Audio System (V0.1, 03/10/2026) : /static/audio/gc-audio.js (modules de static/audio assemblés, versionnés) et /audio/*
(fichiers sons pré-générés hors ligne, noms à empreinte, cache 1 an). Aucune clé ElevenLabs ici, jamais.
"""
import bisect, hashlib, hmac, html, json, os, re, secrets, sqlite3, threading, time, uuid, math
from collections import OrderedDict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse, RedirectResponse
from fastapi.middleware.gzip import GZipMiddleware
from moteur import histoire as _histoire
from moteur import insights as _insights
from moteur import meme_match as _mm
import pages_franchises as _franchises
import comptes_rendus as _recaps

PLAY_SEC = 6.5                 # une action toutes les 6,5 s (comme le site)
# Pauses de retransmission (10/10/2026), en secondes : fin du Q1 / Q3 (et du temps réglementaire avant la
# prolongation), mi-temps. Temps de PRÉSENTATION seulement : les actions du moteur ne changent pas ; l'action qui suit
# la pause est révélée plus tard. Même règle que le site (BRK_SEC, envoyé dans #gf-server).
BREAK_SEC = {"q": 10, "half": 40}


def break_kind(p):
    """Pause après l'action p : « half » (mi-temps), « q » (fin d'un quart-temps, horloge à 0, match en cours), None."""
    a = p.get("after") or {}
    if p.get("try_follows"):            # bloc 2 : la transformation suit le touchdown, la pause vient après elle
        return None
    if a.get("status") == "half":
        return "half"
    if a.get("status") == "live" and p.get("clock_end") is not None and p["clock_end"] <= 0:
        return "q"
    return None


def play_sec(p):
    """Durée d'une action à l'écran : play.show.sec (horloge continue, moteur/ecran.py, 14/10/2026), sinon PLAY_SEC
    (matchs calculés avant)."""
    s = (p.get("show") or {}).get("sec")
    return float(s) if isinstance(s, (int, float)) and s > 0 else PLAY_SEC


def play_ends(plays):
    """Fin (s après le coup d'envoi) de chaque action à l'écran : l'action i commence après les actions 0..i-1 (chacune
    play_sec) et les pauses qui les suivent. Croissant : révélées à l'instant t = bisect(ends, t)."""
    ends, t = [], 0.0
    for p in plays:
        t += play_sec(p)
        ends.append(t)
        b = break_kind(p)
        if b:
            t += BREAK_SEC[b]
    return ends


OPEN_AFTER_FINAL_MIN = 30      # une semaine ouvre aux paris 30 min après la Grand Final de la précédente (au plus tard le lundi 00:00)
BANKROLL, MIN_STAKE = 1000.0, 1.0
CASH_FEE = 0.05                # cash-out : valeur juste − 5 % (étape 2)
COMBO_MIN, COMBO_MAX = 2, 6    # combinés : 2 à 6 sélections, une par match, pas de futures


def same_game_on():
    """Combinés sur un même match (section 86) : GC_SAME_GAME=off, refusés (« same_game ») comme avant."""
    return os.environ.get("GC_SAME_GAME", "on").strip().lower() not in ("off", "0", "non", "no")


def quick_bet_on():
    """Pari rapide depuis l'écran d'un match (section 86) : GC_PARI_RAPIDE=off, la page d'avant."""
    return os.environ.get("GC_PARI_RAPIDE", "on").strip().lower() not in ("off", "0", "non", "no")
TZ = ZoneInfo("Europe/Brussels")
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("GC_DATA", os.path.join(HERE, "data"))
SITE = os.environ.get("GC_SITE", os.path.join(HERE, "gamecenter_source.html"))
WEEKS_DIR = os.path.join(DATA, "weeks")
os.makedirs(WEEKS_DIR, exist_ok=True)

# ------------------------------------------------------------------ horloge
_OFFSET_MS = 0


def now_ms():
    return int(time.time() * 1000) + _OFFSET_MS


def iso_ms(s):
    return int(datetime.fromisoformat(s).timestamp() * 1000)


# ------------------------------------------------------------------ semaines
# GameFeed en mémoire (17/10/2026 : Railway, 1 Go, tombait en « out of memory » — toutes les semaines gardaient leurs
# 279 GameFeed en objets Python, ≈ 700 Mo dès la 4e semaine) : ceux de la semaine en cours restent en mémoire (le direct
# les lit toutes les 3 s) ; ceux des autres semaines sont relus à la demande (replay, feuilles de match de l'histoire,
# mises en cache à part) et gardés dans un petit cache des FEEDS_CACHE derniers.
try:
    FEEDS_CACHE = max(1, int(os.environ.get("GC_FEEDS_CACHE", "40")))
except ValueError:
    FEEDS_CACHE = 40
_FEEDS_LRU, _FEEDS_LOCK = {}, threading.Lock()      # (dossier, id) -> GameFeed ; ordre d'insertion = ancienneté
_PINNED = {"week": None}                            # la semaine en cours (current_week)


def _read_feed(path):
    with open(path, encoding="utf-8") as fh:
        f = json.load(fh)
    f["game"].pop("player_stats", None)
    return f


class _FeedsView:
    def __init__(self, w):
        self.w = w

    def __getitem__(self, gid):
        return self.w.feed(gid)

    def __contains__(self, gid):
        return gid in self.w._files

    def __iter__(self):
        return iter(self.w._files)

    def __len__(self):
        return len(self.w._files)

    def keys(self):
        return self.w._files.keys()


class Week:
    def __init__(self, folder):
        self.folder = folder
        with open(os.path.join(folder, "week.json"), encoding="utf-8") as fh:
            self.doc = json.load(fh)
        self.start = self.doc["week"]["start"]
        self.sched, self._files, self._feeds = [], {}, {}
        for g in self.doc["schedule"]:
            self._files[g["id"]] = os.path.join(folder, g["feed"])
            f = _read_feed(self._files[g["id"]])         # lu une fois pour le calendrier, puis libéré
            ko = iso_ms(g["kickoff"]); n = len(f["plays"]); ends = play_ends(f["plays"])
            # fin arrondie à la ms supérieure : à l'instant de la fin, la dernière action est révélée (temps d'écran
            # fractionnaires, play.show)
            self.sched.append(dict(g, ko=ko, n=n, ends=ends, end=ko + math.ceil((ends[-1] if ends else 0) * 1000)))
            del f
        self.by = {g["id"]: g for g in self.sched}
        self.lock = iso_ms(self.doc["week"]["standings_locked_at"])
        mon = datetime.fromisoformat(self.start).replace(tzinfo=TZ)
        self.monday = int(mon.timestamp() * 1000)
        self.open = self.monday     # recalculé par _assign_opens : paris ouverts dès la publication de la semaine
        self.reset = int((mon + timedelta(days=7)).timestamp() * 1000)
        self.reg = [g for g in self.sched if g["phase"] == "regular"]
        self.nslots = max(g["slot"] for g in self.reg)          # 18 créneaux à 4 équipes, 14 à 8 (étape 6)
        self.semis = [g for g in self.sched if g["phase"] == "semifinal"]
        self.final = next(g for g in self.sched if g["phase"] == "ai_bowl")

    @property
    def feeds(self):
        """Compatibilité (tests, outils) : w.feeds[id] = w.feed(id)."""
        return _FeedsView(self)

    def feed(self, gid):
        """Le GameFeed d'un match : en mémoire pour la semaine en cours, sinon relu (petit cache commun)."""
        if _PINNED["week"] is self:
            f = self._feeds.get(gid)
            if f is None:
                f = self._feeds[gid] = _read_feed(self._files[gid])
            return f
        if self._feeds:
            self._feeds = {}                         # n'est plus la semaine en cours : libérée
        key = (self.folder, gid)
        with _FEEDS_LOCK:
            f = _FEEDS_LRU.pop(key, None)
            if f is None:
                f = _read_feed(self._files[gid])
            _FEEDS_LRU[key] = f
            while len(_FEEDS_LRU) > FEEDS_CACHE:
                _FEEDS_LRU.pop(next(iter(_FEEDS_LRU)))
        return f

    # ---- ce qui est connu à l'instant t ----
    def status(self, g, t):
        return "upcoming" if t < g["ko"] else "live" if t < g["end"] else "final"

    def revealed_plays(self, g, t):
        """Action i visible à la fin de son temps d'écran : ko + (i+1)·6,5 s + les pauses de retransmission avant elle
        (une action de décalage : personne ne la voit avant qu'elle soit jouée)."""
        if t < g["ko"]:
            return 0
        return min(g["n"], bisect.bisect_right(g["ends"], (t - g["ko"]) / 1000))

    def teams_known(self, g, t):
        if g["phase"] == "regular":
            return True
        if g["phase"] == "semifinal":
            return t >= self.lock
        return all(self.status(s, t) == "final" for s in self.semis)

    def completed_slots(self, t):
        s = 0
        for k in range(1, self.nslots + 1):
            if all(self.status(g, t) == "final" for g in self.reg if g["slot"] == k):
                s = k
            else:
                break
        return s

    def any_live(self, t):
        return any(self.status(g, t) == "live" for g in self.sched)

    def public_game(self, g, t):
        st, known = self.status(g, t), self.teams_known(g, t)
        out = {k: g[k] for k in ("id", "phase", "slot", "kickoff", "feed")}
        out.update(home=g["home"] if known else None, away=g["away"] if known else None,
                   odds=g.get("odds") if known else None, status=st)
        if st == "final":
            out.update(result=g["result"], n=g["n"], end_ms=g["end"])
        return out

    def public_feed(self, g, t, upto=None):
        f = self.feed(g["id"])
        known = self.teams_known(g, t)
        game = {k: v for k, v in f["game"].items() if k not in ("final_score", "overtime", "seed")}
        if self.status(g, t) == "final":
            game["final_score"] = f["game"].get("final_score")
            if "overtime" in f["game"]:
                game["overtime"] = f["game"]["overtime"]
        if not known:
            game = {"id": game.get("id"), "home": None, "away": None, "phase": g["phase"], "kickoff": g["kickoff"]}
        k = self.revealed_plays(g, t) if upto is None else upto
        if known and "injuries" in game:            # étape 7.4 : pas de blessure d'une action encore à venir
            game["injuries"] = [b for b in game["injuries"] if b.get("seq", 0) < k]
            for side in ("home", "away"):
                if isinstance(game.get(side), dict) and game[side].get("roster"):
                    game[side] = dict(game[side], roster=[
                        {x: v for x, v in r.items() if x != "injury"} if (r.get("injury") or {}).get("seq", 0) >= k
                        else r for r in game[side]["roster"]])
        return {"schema": f.get("schema"), "game": game, "plays": f["plays"][:k] if known else []}

    def public_state(self, t):
        d = self.doc
        cs = self.completed_slots(t)
        out = {"schema": d["schema"], "week": d["week"], "teams": d["teams"],
               "schedule": [self.public_game(g, t) for g in self.sched],
               "standings_by_slot": d["standings_by_slot"][:cs],
               "futures": [f for f in d["futures"] if f["after_slot"] <= cs],
               "standings": None, "seeds": None, "champion": None, "runner_up": None}
        if d.get("injuries"):                       # étape 7.4 : le rapport d'avant les cotes (pas les blessures à venir)
            out["injuries"] = {k: d["injuries"].get(k) for k in ("model", "published", "out", "signings")}
            by = {g["id"]: g for g in self.sched}

            def joue(x):                             # un blessé de la semaine : une fois son action jouée
                g = by.get(x.get("game"))
                return bool(g) and (self.status(g, t) == "final" or self.revealed_plays(g, t) > x.get("seq", 0))
            for k in ("in_week", "in_week_signings"):
                out["injuries"][k] = [x for x in d["injuries"].get(k) or [] if joue(x)]
        if cs == self.nslots:
            out["standings"], out["seeds"] = d["standings"], d["seeds"]
        if self.status(self.final, t) == "final":
            out["champion"], out["runner_up"] = d["champion"], d["runner_up"]
        return out

    # ---- prix du moment (les mêmes que le site) ----
    def quote(self, key, t):
        k = key.split(":")
        if k[0] == "fut":
            if len(k) != 3 or k[1] not in ("regular_season", "reach_final", "ai_bowl") or k[2] not in self.doc["teams"]:
                return None
            m, a = k[1], k[2]
            cs = self.completed_slots(t)
            snap = next((f for f in reversed(self.doc["futures"]) if f["after_slot"] <= cs), self.doc["futures"][0])
            v = snap["markets"][m].get(a) or {}
            close = {"regular_season": max(g["ko"] for g in self.reg if g["slot"] == self.nslots),
                     "reach_final": min(g["ko"] for g in self.semis), "ai_bowl": self.final["ko"]}[m]
            q = {"price_dec": v.get("decimal"), "line": None, "locked": None}
            if t < self.open: q["locked"] = "opens"
            elif t >= close: q["locked"] = "closed"
            elif not v.get("decimal"): q["locked"] = "na"
            elif self.any_live(t): q["locked"] = "live"
            return q
        if len(k) != 3 or k[0] not in self.by or k[1] not in ("ml", "sp", "tot"):
            return None
        g, mk, side = self.by[k[0]], k[1], k[2]
        if (mk in ("ml", "sp") and side not in ("home", "away")) or (mk == "tot" and side not in ("over", "under")):
            return None
        st = self.status(g, t)
        q = {"price_dec": None, "line": None, "locked": None}
        if t < self.open: q["locked"] = "opens"; return q
        if st == "final": q["locked"] = "final"; return q
        if not self.teams_known(g, t): q["locked"] = "seeds"; return q
        f = self.feed(g["id"])
        r = self.revealed_plays(g, t)
        if st == "upcoming" or r == 0:
            o = f["game"].get("pregame_odds") or {}
            if mk == "ml" and o.get("ml"): q["price_dec"], q["line"] = dec(o["ml"][side]), None
            elif mk == "sp" and o.get("spread_home") is not None:
                q["line"] = o["spread_home"] if side == "home" else -o["spread_home"]
                q["price_dec"] = dec((o.get("spread_prices") or {}).get(side, -110))
            elif mk == "tot" and o.get("total") is not None:
                q["line"] = o["total"]; q["price_dec"] = dec((o.get("total_prices") or {}).get(side, -110))
        else:
            o = f["plays"][r - 1].get("odds") or {}
            if mk == "ml" and o.get("ml"): q["price_dec"] = dec(o["ml"][side])
            elif mk == "sp" and o.get("spread_home") is not None:
                q["line"] = o["spread_home"] if side == "home" else -o["spread_home"]; q["price_dec"] = dec(-110)
            elif mk == "tot" and o.get("total") is not None:
                q["line"] = o["total"]; q["price_dec"] = dec(-110)
        if q["price_dec"] is None:
            q["locked"] = "na"
        return q

    # ---- règlement (mêmes règles que le site) ----
    def settle_leg(self, key, line, t):
        """Résultat d'une sélection à l'instant t : (« won » | « lost » | « push » | None si pas encore réglée, instant du règlement)."""
        k = key.split(":")
        res, at = None, 0
        if k[0] == "fut":
            m, a = k[1], k[2]
            if m == "regular_season":
                at = max(g["end"] for g in self.reg)
                if t >= at: res = "won" if self.doc["standings"][0]["team"] == a else "lost"
            elif m == "reach_final":
                at = max(g["end"] for g in self.semis)
                if t >= at: res = "won" if a in (self.final["home"], self.final["away"]) else "lost"
            else:
                at = self.final["end"]
                if t >= at: res = "won" if self.doc["champion"] == a else "lost"
            return res, at
        g = self.by.get(k[0])
        if g is None:                  # match qui n'existe plus (semaine re-produite) : sélection remboursée
            return "push", 0
        at = g["end"]
        if t >= at:
            H, A = g["result"]["home"], g["result"]["away"]
            if k[1] == "ml":
                res = "push" if H == A else ("won" if (H > A) == (k[2] == "home") else "lost")
            elif k[1] == "sp":
                mg = (H - A if k[2] == "home" else A - H) + line
                res = "won" if mg > 0 else "lost" if mg < 0 else "push"
            else:
                dd = H + A - line
                res = "push" if dd == 0 else ("won" if (dd > 0) == (k[2] == "over") else "lost")
        return res, at

    def settle(self, b, t):
        """Simple ou combiné (étape 2). Combiné : perdu dès qu'une sélection est perdue ; gagné quand toutes sont
        réglées, au produit des cotes des sélections gagnées (une sélection remboursée compte 1) ; tout remboursé = push.
        Un pari encaissé (cash-out) rend le montant encaissé à l'instant du cash-out."""
        if b.get("cashed_at") is not None and t >= b["cashed_at"]:
            return "cashed", b["cashed_amt"]
        legs = b.get("legs")
        if legs and b.get("key") == "sgp":           # même match (section 86) : égalité = moneyline remboursée,
            res = [self.settle_leg(L["key"], L.get("line"), t)[0] for L in legs]     # le reste à sa cote ensemble
            if "lost" in res:
                return "lost", 0.0
            if None in res:
                return "open", 0.0
            if "push" in res:
                L = legs[res.index("push")]
                return "won", round(b["stake"] * float(L.get("push_price") or 1.0), 2)
            return "won", round(b["stake"] * b["price_dec"], 2)
        if legs:
            prod, pending, all_push = 1.0, False, True
            for L in legs:
                res, _ = self.settle_leg(L["key"], L.get("line"), t)
                if res == "lost":
                    return "lost", 0.0
                if res is None:
                    pending = True
                elif res == "won":
                    prod *= L["price_dec"]; all_push = False
            if pending:
                return "open", 0.0
            return ("push", b["stake"]) if all_push else ("won", round(b["stake"] * prod, 2))
        res, _ = self.settle_leg(b["key"], b["line"], t)
        if res is None:
            return "open", 0.0
        ret = round(b["stake"] * b["price_dec"], 2) if res == "won" else b["stake"] if res == "push" else 0.0
        return res, ret

    def cash_value(self, b, t):
        """Cash-out : valeur juste − CASH_FEE. Par sélection encore ouverte : cote prise ÷ cote du moment (même ligne
        exigée pour spread / total) ; sélection gagnée : sa cote ; remboursée : 1. Renvoie (montant, None) ou (None, raison)."""
        st, _ = self.settle(b, t)
        if st != "open":
            return None, "settled"
        legs = b.get("legs") or [{"key": b["key"], "price_dec": b["price_dec"], "line": b["line"]}]
        if b.get("key") == "sgp":                    # même match : avant le coup d'envoi seulement (cote inchangée)
            g = self.by.get(legs[0]["key"].split(":")[0])
            if g is None or self.status(g, t) != "upcoming":
                return None, "sgp"
            amt = round(b["stake"] * (1 - CASH_FEE), 2)
            return (amt, None) if amt >= 0.01 else (None, "zero")
        f = 1.0
        for L in legs:
            res, _ = self.settle_leg(L["key"], L.get("line"), t)
            if res == "won":
                f *= L["price_dec"]; continue
            if res == "push":
                continue
            q = self.quote(L["key"], t)
            if q is None:
                return None, "unknown"
            if q["locked"]:
                return None, q["locked"]
            if q["line"] != L.get("line"):
                return None, "line"
            f *= L["price_dec"] / q["price_dec"]
        amt = round(b["stake"] * f * (1 - CASH_FEE), 2)
        return (amt, None) if amt >= 0.01 else (None, "zero")


def dec(am):
    return round(1 + (am / 100 if am > 0 else 100 / -am), 4)


_WEEKS, _WEEKS_LOCK = {}, threading.Lock()


def load_weeks():
    with _WEEKS_LOCK:
        for name in sorted(os.listdir(WEEKS_DIR)):
            p = os.path.join(WEEKS_DIR, name)
            if name.startswith("week_") and os.path.exists(os.path.join(p, "week.json")) and name[5:] not in _WEEKS:
                try:
                    _WEEKS[name[5:]] = Week(p)
                except Exception as e:  # une semaine incomplète ne bloque pas les autres
                    print("semaine illisible", name, e)
        _assign_opens()
    return _WEEKS


def _assign_opens():
    """Ouverture des paris d'une semaine : la toute première semaine est ouverte dès qu'elle est sur le serveur ;
    les suivantes, OPEN_AFTER_FINAL_MIN après la fin de la Grand Final de la semaine d'avant (sans dépasser le lundi 00:00).
    La page bascule sur la nouvelle semaine à ce moment-là (current_week)."""
    ws = sorted(_WEEKS.values(), key=lambda w: w.monday)
    for i, w in enumerate(ws):
        w.open = 0 if i == 0 else min(w.monday, ws[i - 1].final["end"] + OPEN_AFTER_FINAL_MIN * 60 * 1000)


def current_week(t=None):
    t = now_ms() if t is None else t
    ws = sorted(load_weeks().values(), key=lambda w: w.monday)
    if not ws:
        return None
    live = [w for w in ws if w.open <= t < w.reset]
    past = [w for w in ws if w.open <= t]
    w = live[-1] if live else past[-1] if past else ws[0]
    if t >= now_ms() - 60_000 and _PINNED["week"] is not w:   # l'heure réelle : la semaine en cours est épinglée,
        old, _PINNED["week"] = _PINNED["week"], w                 # celle d'avant libère ses GameFeed
        if old is not None:
            old._feeds = {}
    return w


def _init_clock():
    global _OFFSET_MS
    at = os.environ.get("GC_DEMO_AT")
    if not at:
        return
    if at == "auto":
        ws = sorted(load_weeks().values(), key=lambda w: w.monday)
        if not ws:
            return
        target = ws[-1].sched[0]["ko"] - 15 * 60 * 1000
    else:
        target = iso_ms(at)
    _OFFSET_MS = target - int(time.time() * 1000)


# ------------------------------------------------------------------ joueurs et paris (SQLite)
DB = os.path.join(DATA, "gamecenter.db")
_db_lock = threading.Lock()


def db():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


with db() as _c:
    _c.executescript("""
    CREATE TABLE IF NOT EXISTS players(id TEXT PRIMARY KEY, token TEXT UNIQUE, name TEXT, created INTEGER);
    CREATE TABLE IF NOT EXISTS bets(id TEXT PRIMARY KEY, player TEXT, week TEXT, key TEXT, price_dec REAL, line REAL,
                                    stake REAL, pt INTEGER, title TEXT, sub TEXT);
    CREATE INDEX IF NOT EXISTS bets_pw ON bets(player, week);
    """)
    # Comptes (étape 1 de la feuille de route) : un joueur reste une clé ; un compte = pseudo + mot de passe posés sur
    # ce joueur. Sans compte on parie comme avant (« invité ») ; le compte garde le portefeuille sur tous les appareils
    # et donne une place au classement de la saison. Migration douce : colonnes ajoutées à la base existante.
    _cols = {r[1] for r in _c.execute("PRAGMA table_info(players)")}
    for _col, _typ in (("login", "TEXT"), ("pw", "TEXT"), ("acct_at", "INTEGER"), ("fav_team", "TEXT")):
        if _col not in _cols:
            _c.execute(f"ALTER TABLE players ADD COLUMN {_col} {_typ}")
    _c.execute("CREATE UNIQUE INDEX IF NOT EXISTS players_login ON players(login) WHERE login IS NOT NULL")
    # Étape 2 : combinés (legs = sélections en JSON, key = « combo ») et cash-out.
    _bcols = {r[1] for r in _c.execute("PRAGMA table_info(bets)")}
    for _col, _typ in (("legs", "TEXT"), ("cashed_at", "INTEGER"), ("cashed_amt", "REAL")):
        if _col not in _bcols:
            _c.execute(f"ALTER TABLE bets ADD COLUMN {_col} {_typ}")
    # Bloc 2, étape 6 : rappels « ton équipe joue dans 10 min » (Web Push). Un abonnement par appareil (endpoint) ;
    # cloches = matchs choisis par un joueur (tous ses appareils) ; envois déjà faits (aucun doublon après un redémarrage).
    _c.executescript("""
    CREATE TABLE IF NOT EXISTS push_subs(endpoint TEXT PRIMARY KEY, player TEXT, p256dh TEXT, auth TEXT, fav INTEGER,
                                         created INTEGER);
    CREATE INDEX IF NOT EXISTS push_subs_p ON push_subs(player);
    CREATE TABLE IF NOT EXISTS push_bells(player TEXT, week TEXT, game TEXT, PRIMARY KEY(player, week, game));
    CREATE TABLE IF NOT EXISTS push_sent(endpoint TEXT, week TEXT, game TEXT, at INTEGER, PRIMARY KEY(endpoint, week, game));
    """)
    # Bloc 2, étape 7 : ligues privées entre amis (comptes seulement) : un code d'invitation par ligue.
    _c.executescript("""
    CREATE TABLE IF NOT EXISTS leagues(id TEXT PRIMARY KEY, name TEXT, code TEXT UNIQUE, owner TEXT, created INTEGER);
    CREATE TABLE IF NOT EXISTS league_members(league TEXT, player TEXT, joined INTEGER, PRIMARY KEY(league, player));
    CREATE INDEX IF NOT EXISTS league_members_p ON league_members(player);
    """)

NAME_RE = re.compile(r"[^\w .'\-]", re.UNICODE)


def clean_name(s):
    s = NAME_RE.sub("", str(s or "")).strip()[:24]
    return s or f"Player {secrets.randbelow(9000) + 1000}"


def player_by_token(token):
    if not token:
        return None
    with db() as c:
        r = c.execute("SELECT * FROM players WHERE token=?", (token,)).fetchone()
    return dict(r) if r else None


# ---- comptes : pseudo + mot de passe ----
PSEUDO_MIN, PW_MIN, PW_MAX = 3, 8, 128
LOGIN_FAILS = {}                       # (« pseudo » | « ip », clé) -> instants des échecs récents
FAIL_WINDOW, FAIL_MAX_PSEUDO, FAIL_MAX_IP = 15 * 60, 8, 30
SEASON_START = os.environ.get("GC_SEASON_START", "")   # ex. 2026-10-05 : semaines plus anciennes hors classement de la saison


def login_key(name):
    return re.sub(r"\s+", " ", name).strip().casefold()


def clean_pseudo(s):
    """Pseudo = nom affiché au classement ET identifiant de connexion (sans tenir compte des majuscules)."""
    raw = re.sub(r"\s+", " ", str(s or "")).strip()
    if NAME_RE.search(raw):
        raise HTTPException(400, "pseudo_chars")   # codes : la page les traduit (site en anglais)
    if not (PSEUDO_MIN <= len(raw) <= 24):
        raise HTTPException(400, "pseudo_length")
    return raw


def check_new_password(pw):
    pw = str(pw or "")
    if not (PW_MIN <= len(pw) <= PW_MAX):
        raise HTTPException(400, "password_length")
    return pw


def hash_pw(pw):
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${salt.hex()}${h.hex()}"


def verify_pw(pw, stored):
    try:
        algo, n, r, p, salt, h = stored.split("$")
        got = hashlib.scrypt(str(pw).encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=len(h) // 2)
        return algo == "scrypt" and hmac.compare_digest(got.hex(), h)
    except Exception:
        return False


def player_by_login(name):
    with db() as c:
        r = c.execute("SELECT * FROM players WHERE login=?", (login_key(name),)).fetchone()
    return dict(r) if r else None


def _too_many_fails(*keys):
    now = time.time()
    for k, mx in keys:
        lst = [x for x in LOGIN_FAILS.get(k, []) if now - x < FAIL_WINDOW]
        LOGIN_FAILS[k] = lst
        if len(lst) >= mx:
            return True
    return False


def _note_fail(*keys):
    for k in keys:
        LOGIN_FAILS.setdefault(k, []).append(time.time())


def account_public(p):
    return {"token": p["token"], "name": p["name"], "account": bool(p.get("login")), "fav_team": p.get("fav_team")}


def bet_row(r):
    b = dict(r)
    b["legs"] = json.loads(b["legs"]) if b.get("legs") else None
    return b


def player_bets(pid, week):
    with db() as c:
        return [bet_row(r) for r in c.execute("SELECT * FROM bets WHERE player=? AND week=? ORDER BY pt", (pid, week.start))]


def ledger(week, bets, t):
    staked = back = 0.0; won = lost = open_ = 0; rows = []
    for b in bets:
        if b["pt"] > t:
            continue
        st, ret = week.settle(b, t)
        staked += b["stake"]
        if st == "open":
            open_ += 1
        else:
            back += ret; won += st == "won"; lost += st == "lost"
        rows.append(dict(b, st=st, ret=ret))
    return {"bets": rows, "balance": round(BANKROLL - staked + back, 2), "won": won, "lost": lost, "open": open_}


# ---- classement de la saison : somme des gains nets de chaque semaine ----
def season_weeks(t):
    ws = sorted(load_weeks().values(), key=lambda w: w.monday)
    return [w for w in ws if w.open <= t and w.start >= SEASON_START]


def _season_agg(bets, weeks, t):
    """Gains nets = somme (retour − mise) des paris RÉGLÉS ; un pari encore ouvert compte quand il est réglé.
    Une semaine finie : gains nets = solde final − 1 000 $. L'argent non misé ne compte pas."""
    by = {w.start: w for w in weeks}
    net, won, lost, nb, played = 0.0, 0, 0, 0, set()
    for b in bets:
        w = by.get(b["week"])
        if w is None or b["pt"] > t:
            continue
        nb += 1; played.add(b["week"])
        st, ret = w.settle(b, t)
        if st == "open":
            continue
        net += ret - b["stake"]; won += st == "won"; lost += st == "lost"
    return {"net": round(net, 2), "weeks": len(played), "bets": nb, "won": won, "lost": lost}


def season_rows(t):
    """Comptes seulement (les invités n'entrent pas au classement de la saison), classés par gains nets."""
    weeks = season_weeks(t)
    with db() as c:
        names = {r["id"]: r["name"] for r in c.execute("SELECT id, name FROM players WHERE login IS NOT NULL")}
        bets = [bet_row(r) for r in c.execute("SELECT b.* FROM bets b JOIN players p ON p.id = b.player WHERE p.login IS NOT NULL")]
    per = {}
    for b in bets:
        per.setdefault(b["player"], []).append(b)
    rows = []
    for pid, bl in per.items():
        a = _season_agg(bl, weeks, t)
        if a["bets"]:
            rows.append(dict(a, id=pid, name=names.get(pid, "?")))
    rows.sort(key=lambda r: (-r["net"], -r["weeks"], r["name"].casefold()))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows


def season_net(pid, t):
    with db() as c:
        bets = [bet_row(r) for r in c.execute("SELECT * FROM bets WHERE player=?", (pid,))]
    return _season_agg(bets, season_weeks(t), t)


# ------------------------------------------------------------------ l'application
app = FastAPI(title="GameCenter live server", docs_url="/api/docs", openapi_url="/api/openapi.json")
# compression : page ≈ 53 Mo -> ≈ 6 Mo, /api/delta (toutes les 3 s) ≈ 1 Mo -> quelques Ko ; un onglet trop lourd était
# rechargé (ou tué) par le navigateur du téléphone, en plein match
app.add_middleware(GZipMiddleware, minimum_size=1024)
_init_clock()

# Domaine du site (Railway : variable GC_DOMAINE=snapline.live). L'ancienne adresse *.up.railway.app y est redirigée,
# chemin et paramètres compris (308 : une requête POST reste une POST). Sans la variable (local, tests) : aucune redirection.
DOMAINE = os.environ.get("GC_DOMAINE", "").strip().lower()


@app.middleware("http")
async def _vers_le_domaine(request: Request, call_next):
    hote = (request.headers.get("host") or "").split(":")[0].lower()
    if DOMAINE and hote.endswith(".up.railway.app"):
        url = "https://" + DOMAINE + request.url.path + (("?" + request.url.query) if request.url.query else "")
        return RedirectResponse(url, status_code=308)
    return await call_next(request)


def _need_week():
    w = current_week()
    if w is None:
        raise HTTPException(503, "Aucune semaine n'est encore disponible sur le serveur.")
    return w


_PAGE_CACHE = {"src": None, "mtime": 0}


def _page_source():
    m = os.path.getmtime(SITE)
    if _PAGE_CACHE["mtime"] != m:
        with open(SITE, encoding="utf-8") as fh:
            _PAGE_CACHE.update(src=fh.read(), mtime=m)
    return _PAGE_CACHE["src"]


# ------------------------------------------------------------------ audio system (V0.1)
AUDIO_JS_DIR = os.path.join(HERE, "static", "audio")
AUDIO_DIR = os.path.realpath(os.environ.get("GC_AUDIO_DIR") or os.path.join(HERE, "audio"))   # GC_AUDIO_DIR : tests seulement
# ordre d'assemblage : chaque module s'inscrit dans window.GCAudioLib
AUDIO_MODULES = ["AudioMixer.js", "ProceduralAudio.js", "SFXManager.js", "CrowdManager.js", "MusicManager.js", "CommentaryCues.js", "CommentaryManager.js", "AudioEventMapper.js", "AssetLoader.js", "AudioManager.js"]
_AUDIO_JS = {"key": None, "src": b"", "ver": ""}
_AUDIO_TYPES = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".ogg": "audio/ogg", ".webm": "audio/webm", ".wav": "audio/wav", ".json": "application/json"}
_HASHED = re.compile(r"\.[0-9a-f]{6,}\.[a-z0-9]+$")


def _audio_bundle():
    paths = [os.path.join(AUDIO_JS_DIR, f) for f in AUDIO_MODULES]
    key = tuple(os.path.getmtime(p) if os.path.exists(p) else 0 for p in paths)
    if _AUDIO_JS["key"] != key:
        parts = []
        for p in paths:
            if os.path.exists(p):
                with open(p, "rb") as fh:
                    parts.append(b"/* --- " + os.path.basename(p).encode() + b" --- */\n" + fh.read())
        src = b"\n".join(parts)
        _AUDIO_JS.update(key=key, src=src, ver=hashlib.sha1(src).hexdigest()[:12] if src else "")
    return _AUDIO_JS


@app.get("/static/audio/gc-audio.js")
def audio_js(v: str = ""):
    b = _audio_bundle()
    if not b["src"]:
        raise HTTPException(404)
    # l'URL versionnée (?v=<empreinte>) ne change jamais de contenu : cache d'un an ; sinon toujours revalider
    cc = "public, max-age=31536000, immutable" if v == b["ver"] else "no-cache"
    return Response(b["src"], media_type="application/javascript; charset=utf-8", headers={"Cache-Control": cc, "ETag": '"' + b["ver"] + '"'})


@app.get("/audio/ecoute", response_class=HTMLResponse)
def audio_ecoute():
    """Écoute des prises enregistrées (lecture seule, aucune clé) : cocher celles à refaire, copier la liste dans
    le workflow GitHub « Commentaire audio » (champ « Prises à refaire »)."""
    import html as _h
    m = {}
    try:
        with open(os.path.join(AUDIO_DIR, "manifest.json"), encoding="utf-8") as fh:
            m = json.load(fh)
    except Exception:
        pass
    com = [a for a in m.get("assets", []) if a.get("cat") in ("commentary", "crowd", "sfx", "music")]
    order = {"commentary": 0, "crowd": 1, "sfx": 2, "music": 3}
    com.sort(key=lambda a: order[a["cat"]])
    label = {"commentary": "Commentaire", "crowd": "Foule", "sfx": "Effets", "music": "Musique (originale, CC0)"}
    rows, cur = "", None
    for a in com:
        if a["cat"] != cur:
            cur = a["cat"]; rows += f'<tr class=sec><td colspan=4><h2>{label[cur]} · {sum(1 for x in com if x["cat"] == cur)}</h2></td></tr>'
        head = a.get("cue") or a.get("state") or a.get("kind", "")
        sub = a.get("tier") or ("boucle" if a.get("loop") or a.get("kind") == "loop" else (f'{a.get("dur")} s' if a.get("dur") else "jingle"))
        rows += (f'<tr><td><input type="checkbox" value="{_h.escape(a["id"][2:])}" aria-label="refaire"></td><td><b>{_h.escape(head)}</b><br><small>{_h.escape(str(sub))}'
                 f'{(" · " + _h.escape(" ".join(a.get("tags") or []))) if a.get("tags") else ""}</small></td><td>{_h.escape(a["text"])}<br><small>{_h.escape(a["id"][2:])}</small></td>'
                 f'<td><audio controls preload="none" src="/audio/{_h.escape(a["file"])}"></audio></td></tr>')
    empty = "" if com else "<p><b>Aucune prise pour l'instant.</b> GitHub → Actions → « Commentaire audio » → Run workflow.</p>"
    page = ("<!doctype html><html lang=fr><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            "<title>GameCenter — écoute du commentaire</title><style>body{font:15px system-ui,sans-serif;margin:16px;max-width:1000px;color:#17202d;background:#f4f2ee}"
            "table{border-collapse:collapse;width:100%}td{padding:8px 6px;border-bottom:1px solid #ddd;vertical-align:middle}small{color:#667}"
            "audio{width:220px;max-width:100%;height:34px}input[type=checkbox]{width:22px;height:22px}"
            "#bar{position:sticky;top:0;background:#f4f2ee;padding:10px 0;border-bottom:2px solid #17202d;margin-bottom:6px}"
            "#ids{width:100%;font:13px ui-monospace,monospace;padding:8px;box-sizing:border-box}"
            "@media(max-width:700px){table,tbody{display:block}tr{display:grid;grid-template-columns:34px 1fr;gap:4px 8px;padding:10px 0;border-bottom:1px solid #ddd}"
            "td{display:block;border:0;padding:0;min-width:0;overflow-wrap:anywhere}td:first-child{grid-row:span 3}audio{width:100%}tr.sec{display:block}}"
            "tr.sec h2{margin:18px 0 4px;font-size:18px}</style>"
            f"<h1>Sons enregistrés · {len(com)} prises</h1>{empty}"
            "<div id=bar>Prises à refaire (cocher, puis copier dans GitHub → Actions → « Commentaire audio » → <i>Prises à refaire</i>) :"
            "<input id=ids readonly placeholder='aucune'></div>"
            f"<table>{rows}</table>"
            "<script>const ids=document.getElementById('ids');document.addEventListener('change',()=>{ids.value=[...document.querySelectorAll('input[type=checkbox]:checked')].map(x=>x.value).join(',');});"
            "ids.addEventListener('focus',()=>ids.select());</script></html>")
    return HTMLResponse(page, headers={"Cache-Control": "no-cache"})


@app.get("/audio/{path:path}")
def audio_asset(path: str):
    full = os.path.realpath(os.path.join(AUDIO_DIR, path))
    if not full.startswith(AUDIO_DIR + os.sep) or not os.path.isfile(full):
        raise HTTPException(404)
    ext = os.path.splitext(full)[1].lower()
    if ext not in _AUDIO_TYPES:
        raise HTTPException(404)
    # nom à empreinte (td_huge_03.a1b2c3.mp3) → immuable ; manifest.json et le reste → revalidés
    cc = "public, max-age=31536000, immutable" if _HASHED.search(full) else "no-cache"
    return FileResponse(full, media_type=_AUDIO_TYPES[ext], headers={"Cache-Control": cc})


def _enc(o):
    return json.dumps(o, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")


# Page allégée (09/10, iPad : onglet tué faute de mémoire en plein replay). Les matchs terminés, sauf les plus récents
# (ceux de l'accueil), n'emportent que ce que l'accueil, les classements, les stats de la saison et les moments forts
# lisent ; le détail (appel complet, décision du QB, ajustements, cotes action par action) arrive avec /api/feed/{id}
# quand on ouvre le replay. Les rosters (identiques pour toute la semaine) ne sont écrits qu'une fois par équipe.
FULL_RECENT_FINALS = 12
_LIGHT_DROP = ("decision", "clock_decision", "adjust", "tracks", "spot", "odds")


def _light_play(p):
    q = {k: v for k, v in p.items() if k not in _LIGHT_DROP}
    if isinstance(p.get("call"), dict):
        q["call"] = {"type": p["call"].get("type")}
    return q


def _page_bundle(w, t):
    finals = sorted((g for g in w.sched if w.status(g, t) == "final"), key=lambda g: g["end"], reverse=True)
    full = {g["id"] for g in finals[:FULL_RECENT_FINALS]}
    feeds, rosters = {}, {}
    for g in w.sched:
        f = w.public_feed(g, t)
        if w.status(g, t) == "final" and g["id"] not in full:
            f = dict(f, plays=[_light_play(p) for p in f["plays"]], light=True)
        game = f.get("game") or {}
        for side in ("home", "away"):
            tm = game.get(side)
            if isinstance(tm, dict) and tm.get("abbr") and isinstance(tm.get("roster"), list):
                ref = rosters.setdefault(tm["abbr"], tm["roster"])
                if ref == tm["roster"]:
                    game = dict(game, **{side: dict(tm, roster="@" + tm["abbr"])})
        feeds[g["id"]] = dict(f, game=game) if game else f
    return {"week": w.public_state(t), "feeds": feeds, "rosters": rosters}


@app.get("/api/feed/{gid}")
def api_feed(gid: str):
    """Le GameFeed complet d'un match déjà joué (ou en cours, jusqu'à l'action révélée) : le replay d'un match allégé."""
    w = _need_week(); t = now_ms()
    g = w.by.get(gid)
    if not g or w.status(g, t) == "upcoming" or not w.teams_known(g, t):
        raise HTTPException(404)
    return w.public_feed(g, t)


@app.get("/", response_class=HTMLResponse)
def page(request: Request = None):
    if request is not None and mesure_on():         # mesure de l'audience (étape 9.1) : rien sans GC_MESURE=1
        compter_visite(request)
    w = _need_week(); t = now_ms()
    bundle = _page_bundle(w, t)
    srv = {"api": "/api", "now": t, "play_sec": PLAY_SEC, "breaks": BREAK_SEC, "week_start": w.start, "open_ms": w.open}
    if ADS_CLIENT:
        srv["ads"] = {"client": ADS_CLIENT, "slots": ADS_SLOTS}
    if chat_mode() != "off":                         # chat (section « chat ») : sans lui, la page ne le dessine pas
        srv["chat"] = chat_mode()
    if insights_on():                                # onglet Insights (section 78) : sans lui, la page ne le dessine pas
        srv["insights"], srv["hist_since"] = True, HIST_DEPUIS
    if os.environ.get("GC_SCHEDULE_PLUS", "on").strip().lower() in ("off", "0", "non", "no"):
        srv["schedule_plus"] = False                 # Schedule (section 84) : sans filtre par franchise ni paris sous un match
    if not same_game_on():                           # combinés sur un même match (section 86)
        srv["same_game"] = False
    if not quick_bet_on():                           # pari rapide depuis l'écran d'un match (section 86)
        srv["quick_bet"] = False
    if accueil_on():                                 # première visite (étape 9.3) : sans GC_ACCUEIL=1, la page d'avant
        srv["accueil"] = True
    if not jeu_fluide_on():                          # dessin des actions (section 83) : GC_JEU_FLUIDE=0, celui d'avant
        srv["fluide_off"] = True
    s = _page_source().replace("__AUDIO_V__", _audio_bundle()["ver"]).replace("__GF_G1__", "null").replace("__WEEK__", _enc(bundle)).replace("__SERVER__", _enc(srv))
    if os.environ.get("GC_TEST_HOOK") == "1":   # tests automatiques seulement (même crochet que build_site.py test)
        s = s.replace("requestAnimationFrame(frame);\n})();", "requestAnimationFrame(frame);\nwindow.__gc={games,byId,views,computeStats,getModalView:()=>modalView,"
                      "season:{SCHED,setClock,nowMs,standingsAt,seasonAgg,setView,gStatus,futuresAt,bets:BETS_API,sw:()=>SW},audio:AUDIO_API,"
                      "playerCardHTML,openPlayerCard,depthChartHTML,rotLineups,slotMap,injuryReportHTML,injSpot,rosterCardHTML,openReplayFeed,stepGame,updateGameUI,rpDone,rpSeek,replayGame:()=>replayGame,fluide:v=>{if(v!==undefined)JEU_FLUIDE=!!v;return JEU_FLUIDE;},psBubble,playLine,nameTags,scBubbles,adjLine,rpChip,rpFeedItem,caption,showChip,"
                      "brk:{BRK_SEC,brkKind,tlOf,timelineAt,topPerformers,perfStats,perfScore,liveBreakLeft},"
                      "fx:(d,glow)=>{FX_DPR=d;FX_GLOW=glow;PERF.t0=Infinity;for(const v of views)v.resize();}};\n})();")
    if GOOGLE_VERIFY:                                # Search Console, vérification par balise (sinon : TXT dans le DNS)
        s = s.replace("</title>", '</title>\n<meta name="google-site-verification" content="' + html.escape(GOOGLE_VERIFY, quote=True) + '">', 1)
    if CF_ANALYTICS:                                 # statistiques d'audience : rien sans GC_CF_ANALYTICS
        s = s.replace("</title>", "</title>\n" + _cf_beacon(CF_ANALYTICS), 1)
    if accueil_on():
        s = s.replace(_ACCUEIL_CACHE, _ACCUEIL_CACHE[:-len(" hidden>")] + ">", 1).replace("</title>", "</title>\n" + _ACCUEIL_TETE, 1)
    if ADS_CLIENT:                                   # publicités (bloc 2 bis) : rien sans GC_ADSENSE_CLIENT
        s = s.replace("</title>", '</title>\n<meta name="google-adsense-account" content="' + ADS_CLIENT + '">\n'
                      '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + ADS_CLIENT
                      + '" crossorigin="anonymous"></script>', 1)
    return HTMLResponse(s, headers={"Cache-Control": "no-store"})


# Première visite (promotion, étape 9.3, README section 81) : GC_ACCUEIL=1 montre le bandeau des nouveaux venus (ce
# qu'est Snapline, un bouton pour voir un match tout de suite) et retient les blocs sous la grille des matchs jusqu'à son
# 1er dessin (CLS). Le script du <head> décide avant la 1re image : bandeau caché pour qui est déjà venu (gc-welcome-v1
# ou gc-player-v1 dans le navigateur), blocs retenus au plus 10 s (si le site ne démarre pas, la page reste lisible).
# Sans la variable : la page d'avant, à l'identique (le bandeau reste caché, aucun script).
# Dessin naturel des actions sur le terrain (section 83, 30/10/2026) : actif par défaut ; GC_JEU_FLUIDE=0 rend le dessin
# d'avant, à l'identique (passes, course après la réception, interceptions, couverture homme, fumbles).
def jeu_fluide_on():
    return os.environ.get("GC_JEU_FLUIDE", "").strip() != "0"


def accueil_on():
    return os.environ.get("GC_ACCUEIL", "").strip() == "1"


_ACCUEIL_CACHE = '<section class="card welcome" id="welcome" aria-labelledby="welcomeTitle" hidden>'
_ACCUEIL_TETE = ("<script>(function(){var d=document.documentElement;d.classList.add('gc-boot');"
                 "setTimeout(function(){d.classList.remove('gc-boot');},10000);"
                 "try{if(localStorage.getItem('gc-welcome-v1')||localStorage.getItem('gc-player-v1'))d.classList.add('gc-seen');}"
                 "catch(e){}})();</script>")


# Référencement (bloc 2, étape 8) : robots.txt, plan du site, image de partage (Open Graph, 1200×630)
GOOGLE_VERIFY = os.environ.get("GC_GOOGLE_VERIFY", "").strip()

# Publicités (étape 7 de la feuille de route) : Google AdSense. GC_ADSENSE_CLIENT = identifiant d'éditeur
# (« ca-pub-1234567890123456 ») : sans lui, aucune publicité ni script de régie, et /ads.txt n'existe pas.
# GC_ADSENSE_SLOTS = blocs d'annonces créés dans AdSense, par emplacement : « half=123,home=456,page=789 »
# (mi-temps du grand écran, accueil, bas des onglets Schedule / Standings / Teams / History) ; un emplacement sans bloc
# reste vide (rien n'est réservé à l'écran).
ADS_EMPLACEMENTS = ("half", "home", "page")


def _ads_client(v):
    v = (v or "").strip()
    return v if re.fullmatch(r"ca-pub-\d{10,20}", v) else ""


def _ads_slots(v):
    out = {}
    for part in (v or "").split(","):
        k, _, n = part.strip().partition("=")
        if k.strip() in ADS_EMPLACEMENTS and re.fullmatch(r"\d{5,20}", n.strip()):
            out[k.strip()] = n.strip()
    return out


# Statistiques d'audience : Cloudflare Web Analytics (sans cookies, sans identifiant de visiteur : pas de consentement
# à demander). GC_CF_ANALYTICS = jeton du site (Cloudflare → Analytics & Logs → Web Analytics → Add a site → JS snippet,
# la valeur « token ») : sans lui, aucun script. Le script est aussi posé sur /legal pour compter cette page.
def _cf_token(v):
    v = (v or "").strip()
    return v if re.fullmatch(r"[0-9a-f]{32}", v) else ""


def _cf_beacon(token):
    return ("<script defer src=\"https://static.cloudflareinsights.com/beacon.min.js\" "
            "data-cf-beacon='{\"token\": \"" + token + "\"}'></script>")


CF_ANALYTICS = _cf_token(os.environ.get("GC_CF_ANALYTICS"))

ADS_CLIENT = _ads_client(os.environ.get("GC_ADSENSE_CLIENT"))
ADS_SLOTS = _ads_slots(os.environ.get("GC_ADSENSE_SLOTS")) if ADS_CLIENT else {}


@app.get("/ads.txt")
def ads_txt():
    if not ADS_CLIENT:
        raise HTTPException(404)
    return Response("google.com, " + ADS_CLIENT[3:] + ", DIRECT, f08c47fec0942fa0\n", media_type="text/plain",
                    headers={"Cache-Control": "public, max-age=86400"})


# Page « Rules, privacy & legal » (anglais, comme le site) : static/legal.html. L'éditeur (mentions légales, droit belge)
# vient des variables GC_EDITEUR (nom), GC_EDITEUR_ADRESSE (adresse) et GC_CONTACT (adresse e-mail) ; sans elles, la
# ligne correspondante dit « not set ».
@app.get("/legal", response_class=HTMLResponse)
def legal():
    with open(os.path.join(HERE, "static", "legal.html"), encoding="utf-8") as fh:
        s = fh.read()
    val = lambda k: html.escape(os.environ.get(k, "").strip()) or "<i>not set</i>"
    contact = os.environ.get("GC_CONTACT", "").strip()
    s = (s.replace("__EDITEUR__", val("GC_EDITEUR")).replace("__ADRESSE__", val("GC_EDITEUR_ADRESSE"))
         .replace("__CONTACT__", f'<a href="mailto:{html.escape(contact, quote=True)}">{html.escape(contact)}</a>' if contact else "<i>not set</i>")
         .replace("__ADS__", "on" if ADS_CLIENT else "off"))
    if chat_mode() != "off":                         # règles du chat et données gardées : seulement chat allumé
        s = _legal_chat(s)
    if mesure_on():                                  # mesure de l'audience (étape 9.1) : la page le dit
        s = s.replace(_LEGAL_CF_FIN, _LEGAL_CF_FIN + _LEGAL_MESURE, 1)
    if CF_ANALYTICS:
        s = s.replace("</title>", "</title>\n" + _cf_beacon(CF_ANALYTICS), 1)
    return HTMLResponse(s, headers={"Cache-Control": "no-cache"})


_LEGAL_CF_FIN = "collects the page, the referring site, the country and the type of browser and device.</p>"
_LEGAL_MESURE = ("\n    <p>Our server also counts, for each day, how many times the home page is opened, the name of the site "
                 "the visitor came from (for example \u201cgoogle\u201d or \u201ctiktok\u201d) and how many times our short "
                 "links are used (<code>snapline.live/tt</code>, <code>/ig</code>, <code>/yt</code>). These are totals "
                 "only: no cookie is set and no IP address or identifier is kept for them.</p>")


def _legal_chat(s):
    """Page légale, chat allumé : règles du chat (section #chat), messages dans « ce que nous gardons », durées."""
    with open(os.path.join(HERE, "static", "legal_chat.html"), encoding="utf-8") as fh:
        parts = dict(re.findall(r"<!--(\w+)-->\n(.*?)<!--/\1-->", fh.read(), re.S))
    s = s.replace('  <section id="legal">', parts["section"].replace("__DAYS__", str(chat_days())) + '  <section id="legal">', 1)
    s = s.replace("      <li>Technical logs of our host", parts["privacy"].replace("__DAYS__", str(chat_days()))
                  + "      <li>Technical logs of our host", 1)
    return s.replace("Game data is kept while the service runs;", parts["keep"].replace("__DAYS__", str(chat_days())), 1)


def _origine(request):
    return "https://" + DOMAINE if DOMAINE else str(request.base_url).rstrip("/")


# Pages des franchises (AdSense, 29/10/2026 : pages écrites, lisibles sans JavaScript — pages_franchises.py) : /teams
# et /teams/<nom> (« cortex-foxes » ; l'abréviation « ctx » y renvoie). Effectif et notes de la semaine en cours (début
# de semaine), histoire des semaines TERMINÉES seulement (pas de spoiler).
def _franchises_tete():
    return "\n" + _cf_beacon(CF_ANALYTICS) + "\n" if CF_ANALYTICS else ""


def _derniers_matchs(a, t, n=6):
    """Les n derniers matchs terminés d'une franchise (semaines ouvertes), pour sa page."""
    out = []
    for w in reversed(_semaines_ouvertes(t)):
        jeux = sorted((g for g in w.sched if a in (g["home"], g["away"]) and w.status(g, t) == "final"),
                      key=lambda g: g["end"], reverse=True)
        for g in jeux:
            r = g.get("result") or {}
            out.append({"id": g["id"], "texte": f"Week {w.doc['week']['index']} · "
                        + _recaps.titre_match(g, r.get("home", 0), r.get("away", 0), w.doc["teams"])})
            if len(out) >= n:
                return out
    return out


@app.get("/teams", response_class=HTMLResponse)
def teams_index(request: Request):
    d = _need_week().doc
    s = _franchises.page_index(d["teams"], d["week"].get("league"), _origine(request), _franchises_tete())
    return HTMLResponse(s, headers={"Cache-Control": "public, max-age=3600"})


@app.get("/teams/{nom}", response_class=HTMLResponse)
def teams_page(nom: str, request: Request):
    d = _need_week().doc
    teams = d["teams"]
    par_slug = {_franchises.slug(t["name"]): a for a, t in teams.items()}
    if nom not in par_slug:
        a = nom.upper()
        if a in teams:
            return RedirectResponse("/teams/" + _franchises.slug(teams[a]["name"]), status_code=301)
        raise HTTPException(404)
    a = par_slug[nom]
    h = league_history(now_ms(), True)
    histo = next((f for f in h.get("franchises") or [] if f.get("team") == a), None)
    s = _franchises.page_equipe(a, teams, d["week"].get("league"), histo, h.get("seasons"), _origine(request),
                                _franchises_tete(), _derniers_matchs(a, now_ms()))
    return HTMLResponse(s, headers={"Cache-Control": "public, max-age=3600"})


# Comptes rendus des matchs (AdSense, 29/10/2026 — comptes_rendus.py) : /games (les semaines, derniers matchs),
# /weeks/<n> (résultats d'une semaine) et /games/<id> (compte rendu écrit). Matchs TERMINÉS seulement : un match à
# venir ou en cours répond 404, une semaine pas encore ouverte aussi. Un compte rendu ne change plus : gardé en mémoire.
_RECAPS, _RECAPS_MAX = OrderedDict(), 64
_JOURS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def _semaines_ouvertes(t):
    return [w for w in sorted(load_weeks().values(), key=lambda w: w.monday) if w.open <= t]


def _match(gid, t):
    for w in _semaines_ouvertes(t):
        g = w.by.get(gid)
        if g is not None:
            return (w, g) if w.status(g, t) == "final" else (None, None)
    return None, None


def _recap_contexte(w, g):
    d = w.doc
    ko = datetime.fromtimestamp(g["ko"] / 1000, TZ)
    ctx = {"semaine": d["week"]["index"], "date": f"{_JOURS[ko.weekday()]} {ko.day} {ko.strftime('%B %Y')}"}
    conf = {a: c for c, ds in (d["week"].get("league") or {}).items() for l in ds.values() for a in l}
    if g["phase"] == "semifinal" and conf.get(g["home"]):
        ctx["conference"] = conf[g["home"]]
    if g["phase"] == "regular":                      # bilans de la semaine après ce match (tours précédents compris)
        b = {g["home"]: [0, 0, 0], g["away"]: [0, 0, 0]}
        for x in w.reg:
            if x["slot"] > g["slot"]:
                continue
            r = x.get("result") or {}
            for s, o in (("home", "away"), ("away", "home")):
                if x[s] in b:
                    b[x[s]][0 if r.get(s, 0) > r.get(o, 0) else 1 if r.get(s, 0) < r.get(o, 0) else 2] += 1
        ctx["bilans"] = {"home": tuple(b[g["home"]]), "away": tuple(b[g["away"]])}
    return ctx


@app.get("/games/{gid}", response_class=HTMLResponse)
def game_recap(gid: str, request: Request):
    w, g = _match(gid, now_ms())
    if g is None:
        raise HTTPException(404)
    cle = (w.folder, gid, _origine(request), CF_ANALYTICS)
    s = _RECAPS.get(cle)
    if s is None:
        s = _recaps.page_match(g, w.feed(gid), _feuille(w, gid), w.doc["teams"], _recap_contexte(w, g),
                               _origine(request), _franchises_tete())
        _RECAPS[cle] = s
        while len(_RECAPS) > _RECAPS_MAX:
            _RECAPS.popitem(last=False)
    return HTMLResponse(s, headers={"Cache-Control": "public, max-age=86400"})


@app.get("/weeks/{index}", response_class=HTMLResponse)
def week_results(index: int, request: Request):
    t = now_ms()
    w = next((w for w in _semaines_ouvertes(t) if w.doc["week"]["index"] == index), None)
    if w is None:
        raise HTTPException(404)
    jeux = [g for g in w.sched if w.status(g, t) == "final"]
    resume = None
    if w.status(w.final, t) == "final":
        resume = next((x for x in league_history(t, True).get("seasons") or [] if x.get("week") == index), None)
        resume = resume or {"champion": w.doc.get("champion"), "runner_up": w.doc.get("runner_up")}
    s = _recaps.page_semaine(index, jeux, len(w.sched), w.doc["teams"], resume, _origine(request), _franchises_tete())
    return HTMLResponse(s, headers={"Cache-Control": "public, max-age=600"})


@app.get("/games", response_class=HTMLResponse)
def games_index(request: Request):
    t = now_ms()
    ws = _semaines_ouvertes(t)
    sem = []
    for w in reversed(ws):
        fin = w.status(w.final, t) == "final"
        n = sum(1 for g in w.sched if w.status(g, t) == "final")
        if n:
            sem.append({"index": w.doc["week"]["index"], "champion": w.doc.get("champion") if fin else None,
                        "played": n, "total": len(w.sched)})
    derniers = []
    for w in reversed(ws):
        derniers += sorted((g for g in w.sched if w.status(g, t) == "final"), key=lambda g: g["end"], reverse=True)
        if len(derniers) >= 12:
            break
    teams = ws[-1].doc["teams"] if ws else {}
    s = _recaps.page_index(sem, derniers[:12], teams, _origine(request), _franchises_tete())
    return HTMLResponse(s, headers={"Cache-Control": "public, max-age=600"})


@app.get("/robots.txt")
def robots(request: Request):
    txt = "User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /audio/ecoute\n\nSitemap: " + _origine(request) + "/sitemap.xml\n"
    return Response(txt, media_type="text/plain", headers={"Cache-Control": "public, max-age=86400"})


def _sitemap_recaps():
    """/games, /weeks/<n> et /games/<id> des matchs terminés."""
    t = now_ms()
    out = ["/games"]
    for w in _semaines_ouvertes(t):
        jeux = [g["id"] for g in w.sched if w.status(g, t) == "final"]
        if jeux:
            out.append("/weeks/" + str(w.doc["week"]["index"]))
            out += ["/games/" + gid for gid in jeux]
    return out


def _sitemap_teams():
    w = current_week()
    return list(w.doc["teams"].values()) if w is not None else []


@app.get("/sitemap.xml")
def sitemap(request: Request):
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           "  <url><loc>" + _origine(request) + "/</loc><changefreq>hourly</changefreq><priority>1.0</priority></url>\n"
           "  <url><loc>" + _origine(request) + "/teams</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>\n"
           + "".join("  <url><loc>" + _origine(request) + "/teams/" + _franchises.slug(t["name"]) + "</loc><changefreq>weekly</changefreq>"
                     "<priority>0.7</priority></url>\n" for t in _sitemap_teams())
           + "".join("  <url><loc>" + _origine(request) + u + "</loc></url>\n" for u in _sitemap_recaps())
           + "  <url><loc>" + _origine(request) + "/legal</loc><changefreq>monthly</changefreq><priority>0.3</priority></url>\n</urlset>\n")
    return Response(xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/og.png")
def og_image():
    return FileResponse(os.path.join(HERE, "static", "og.png"), media_type="image/png",
                        headers={"Cache-Control": "public, max-age=86400"})


# ------------------------------------------------------------------ mesure de l'audience (promotion, étape 9.1)
# GC_MESURE=1 : liens courts comptés (/tt, /ig, /yt, /r/<source>) qui renvoient à l'accueil, accueil compté par jour et
# par site d'origine (nom du site seulement : « google », « tiktok »…), tableau de bord /admin/stats (GC_ADMIN_KEY).
# Rien que des totaux par jour : ni cookie, ni adresse IP, ni identifiant (pas de consentement à demander ; /legal le
# dit). Sans la variable : rien n'est compté, ces adresses répondent 404 et /legal est inchangée.
# GC_STATS_EXCLURE = pseudos des comptes à ne pas compter (les siens, séparés par des virgules).
def mesure_on():
    return os.environ.get("GC_MESURE", "").strip() == "1"


LIENS_COURTS = ("tt", "ig", "yt")                    # TikTok, Instagram, YouTube (bios des réseaux)
_SOURCE_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,23}")  # /r/<source> : hn, reddit-sideproject, ph…
_ROBOT_RE = re.compile(r"bot|crawl|spider|slurp|preview|scan|monitor|uptime|lighthouse|headless|python|curl|wget|"
                       r"httpx|go-http|java/|okhttp|axios|node-fetch|facebookexternalhit|embedly|whatsapp|telegram|"
                       r"discord|skype", re.I)
# Site d'origine (en-tête Referer) → source : un des noms de l'adresse (www.google.be → google), quelques adresses
# exactes, sinon « autre ». Les applications Android envoient « android-app://com.zhiliaoapp.musically » (TikTok).
_SOURCES_NOM = {"google": "google", "bing": "bing", "duckduckgo": "duckduckgo", "yahoo": "yahoo", "ecosia": "ecosia",
                "qwant": "qwant", "brave": "brave", "tiktok": "tiktok", "musically": "tiktok", "instagram": "instagram",
                "facebook": "facebook", "fb": "facebook", "youtube": "youtube", "reddit": "reddit",
                "ycombinator": "hackernews", "producthunt": "producthunt", "twitter": "x", "bsky": "bluesky",
                "linkedin": "linkedin", "operationsports": "operationsports"}
_SOURCES_ADRESSE = {"t.co": "x", "x.com": "x", "youtu.be": "youtube"}


def _jour(ms=None):
    return datetime.fromtimestamp((time.time() if ms is None else ms / 1000), TZ).strftime("%Y-%m-%d")


def _robot(req):
    ua = req.headers.get("user-agent") or ""
    return not ua or bool(_ROBOT_RE.search(ua))


def source_visite(referer, hote=""):
    """Nom de la source d'une visite d'après son Referer : direct, site (une page de Snapline), google, tiktok… autre."""
    from urllib.parse import urlparse
    try:
        h = (urlparse(referer or "").hostname or "").lower()
    except ValueError:
        h = ""
    if not h:
        return "direct"
    h = h[4:] if h.startswith("www.") else h
    if h in {d for d in (DOMAINE, (hote or "").split(":")[0].lower()) if d}:
        return "site"
    if h in _SOURCES_ADRESSE:
        return _SOURCES_ADRESSE[h]
    for nom in h.split("."):
        if nom in _SOURCES_NOM:
            return _SOURCES_NOM[nom]
    return "autre"


def compter(*cles, jour=None):
    """+1 sur chaque total du jour (heure de Bruxelles). Une erreur de la base ne gêne jamais la page."""
    j = jour or _jour()
    try:
        with _db_lock, db() as c:
            c.executemany("INSERT INTO stats_day(day, k, n) VALUES(?,?,1) ON CONFLICT(day, k) DO UPDATE SET n = n + 1",
                          [(j, k) for k in cles])
    except sqlite3.Error as e:
        print("mesure :", e)


def compter_visite(req):
    """Accueil ouvert : « robot » pour les robots (moteurs, aperçus de liens, sondes), sinon « visite » et sa source.
    Les préchargements du navigateur (Sec-Purpose: prefetch) ne comptent pas."""
    if req.method != "GET" or "prefetch" in (req.headers.get("sec-purpose") or req.headers.get("purpose") or ""):
        return
    if _robot(req):
        compter("robot")
    else:
        compter("visite", "visite:" + source_visite(req.headers.get("referer"), req.headers.get("host")))


with db() as _c:
    _c.execute("CREATE TABLE IF NOT EXISTS stats_day(day TEXT, k TEXT, n INTEGER, PRIMARY KEY(day, k))")


def _lien_court(req, src):
    if not mesure_on() or not _SOURCE_RE.fullmatch(src or ""):
        raise HTTPException(404)
    if req.method == "GET" and not _robot(req):
        compter("lien:" + src)
    return RedirectResponse("/", status_code=302, headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex"})


@app.get("/tt")
def lien_tt(request: Request):
    return _lien_court(request, "tt")


@app.get("/ig")
def lien_ig(request: Request):
    return _lien_court(request, "ig")


@app.get("/yt")
def lien_yt(request: Request):
    return _lien_court(request, "yt")


@app.get("/r/{src}")
def lien_r(request: Request, src: str):
    return _lien_court(request, src)


def _semaines(n, now=None):
    """Les n dernières semaines (lundi 00:00 → lundi suivant, heure de Bruxelles), la plus récente d'abord."""
    d = datetime.fromtimestamp((time.time() if now is None else now / 1000), TZ)
    lundi = datetime(d.year, d.month, d.day, tzinfo=TZ) - timedelta(days=d.weekday())
    out = []
    for i in range(n):
        a = lundi - timedelta(weeks=i)
        b = a + timedelta(weeks=1)
        b = datetime(b.year, b.month, b.day, tzinfo=TZ)   # changement d'heure : minuit du lundi suivant
        out.append((a.strftime("%Y-%m-%d"), int(a.timestamp() * 1000), int(b.timestamp() * 1000)))
    return out


def stats_admin(n_semaines=12, now=None):
    """Tableau de bord : par semaine, les totaux comptés (visites, sources, liens courts) et ce que la base sait déjà
    depuis le début (nouveaux joueurs, comptes, joueurs actifs, paris, ligues, rappels, messages du chat)."""
    n_semaines = max(1, min(52, int(n_semaines)))
    exclus = [login_key(x) for x in os.environ.get("GC_STATS_EXCLURE", "").split(",") if x.strip()]
    with db() as c:
        ids = [r[0] for r in c.execute("SELECT id FROM players WHERE login IN (%s)" % ",".join("?" * len(exclus)),
                                       exclus)] if exclus else []
        hors = (" AND %s NOT IN (" + ",".join("?" * len(ids)) + ")") if ids else ""
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}

        def un(sql, col, *args):
            q = sql + (hors % col if ids else "")
            return c.execute(q, args + tuple(ids)).fetchone()[0] or 0

        def actifs(a, b):
            q = "SELECT player FROM bets WHERE pt >= ? AND pt < ?"
            args = [a, b]
            if "chat_messages" in tables:
                q += " UNION SELECT player FROM chat_messages WHERE adm = 0 AND created >= ? AND created < ?"
                args += [a, b]
            return len({r[0] for r in c.execute(q, args)} - set(ids))

        totaux = {r["day"] + "|" + r["k"]: r["n"] for r in c.execute("SELECT day, k, n FROM stats_day")}
        depuis = c.execute("SELECT MIN(day) FROM stats_day").fetchone()[0]
        semaines = []
        for debut, a, b in _semaines(n_semaines, now):
            jours = {(datetime.fromtimestamp(a / 1000, TZ) + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)}
            comptes = {}
            for cle, v in totaux.items():
                j, k = cle.split("|", 1)
                if j in jours:
                    comptes[k] = comptes.get(k, 0) + v
            semaines.append({
                "debut": debut,
                "visites": comptes.get("visite", 0), "robots": comptes.get("robot", 0),
                "sources": {k[7:]: v for k, v in comptes.items() if k.startswith("visite:")},
                "liens": {k[5:]: v for k, v in comptes.items() if k.startswith("lien:")},
                "joueurs": un("SELECT COUNT(*) FROM players WHERE created >= ? AND created < ?", "id", a, b),
                "comptes": un("SELECT COUNT(*) FROM players WHERE acct_at >= ? AND acct_at < ?", "id", a, b),
                "actifs": actifs(a, b),
                "paris": un("SELECT COUNT(*) FROM bets WHERE pt >= ? AND pt < ?", "player", a, b),
                "ligues": un("SELECT COUNT(*) FROM leagues WHERE created >= ? AND created < ?", "owner", a, b),
                "adhesions": un("SELECT COUNT(*) FROM league_members m JOIN leagues l ON l.id = m.league "
                                "WHERE m.player != l.owner AND m.joined >= ? AND m.joined < ?", "m.player", a, b),
                "rappels": un("SELECT COUNT(*) FROM push_subs WHERE created >= ? AND created < ?", "player", a, b),
                "messages": un("SELECT COUNT(*) FROM chat_messages WHERE adm = 0 AND created >= ? AND created < ?",
                               "player", a, b) if "chat_messages" in tables else 0,
            })
        total = {
            "joueurs": un("SELECT COUNT(*) FROM players WHERE 1", "id"),
            "comptes": un("SELECT COUNT(*) FROM players WHERE login IS NOT NULL", "id"),
            "ligues": un("SELECT COUNT(*) FROM leagues WHERE 1", "owner"),
            "rappels": un("SELECT COUNT(*) FROM push_subs WHERE 1", "player"),
        }
    return {"depuis": depuis, "exclus": len(ids), "semaines": semaines, "total": total}


@app.post("/api/admin/stats")
async def api_admin_stats(req: Request):
    """Tableau de bord (GC_ADMIN_KEY ; seulement avec GC_MESURE=1). {key, semaines (12 par défaut)}."""
    if not mesure_on():
        raise HTTPException(404)
    body = await _json(req)
    ip = _ip(req)
    if _too_many_fails((("admin-stats", ip), 10)):
        raise HTTPException(429, "too_many")
    admin = os.environ.get("GC_ADMIN_KEY", "")
    if len(admin) < 16 or not secrets.compare_digest(str(body.get("key") or ""), admin):
        _note_fail(("admin-stats", ip))
        raise HTTPException(403, "forbidden")
    try:
        n = int(body.get("semaines") or 12)
    except (TypeError, ValueError):
        n = 12
    return JSONResponse(stats_admin(n), headers={"Cache-Control": "no-store"})


@app.get("/admin/stats", response_class=HTMLResponse)
def admin_stats_page():
    """Tableau de bord de la promotion (en français : pour l'administrateur). La clé est tapée dans la page."""
    if not mesure_on():
        raise HTTPException(404)
    with open(os.path.join(HERE, "static", "admin_stats.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow",
                                                "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY"})


@app.get("/api/time")
def api_time():
    return {"now": now_ms()}


@app.get("/api/delta")
def api_delta(have: str = ""):
    """État public + actions nouvelles. have = « id:nb,id:nb » (actions déjà reçues par le navigateur)."""
    w = _need_week(); t = now_ms()
    got = {}
    for part in filter(None, have.split(",")):
        gid, _, n = part.partition(":")
        if gid in w.by and n.isdigit():
            got[gid] = int(n)
    plays = {}
    for g in w.sched:
        r = w.revealed_plays(g, t) if w.teams_known(g, t) else 0
        h = got.get(g["id"], 0)
        if r > h:
            plays[g["id"]] = {"from": h, "plays": w.feed(g["id"])["plays"][h:r]}
    st = w.public_state(t)
    st.pop("teams", None)
    # le navigateur ne lit « games » que pour les affiches de playoffs dont les équipes étaient cachées : les rosters des
    # 276 matchs de saison régulière (≈ 9 Mo) ne sont plus renvoyés toutes les 3 s
    games = {g["id"]: w.public_feed(g, t, upto=0)["game"] for g in w.sched if g["phase"] != "regular"}
    out = {"now": t, "week_start": w.start, "state": st, "games": games, "plays": plays}
    if chat_mode() != "off":                       # chat : dernier message de General (badge des non-lus), retraits
        out["chat"] = {"general": chat_last(), "rev": _CHAT["rev"]}
    return out


_DIAG = {}                                          # ip -> [début de la minute, lots reçus]


@app.post("/api/diag")
async def api_diag(req: Request):
    """Journal de diagnostic de l'écran du match (bannières, taille de la fenêtre, état du son, erreurs) : une ligne
    « DIAG » dans les journaux du serveur, pour comprendre un bug vu dans un navigateur qu'on ne peut pas tester ici.
    Rien n'est stocké ; 20 lots par minute et par adresse au plus, 8 Ko par lot."""
    ip = req.client.host if req.client else "?"
    now = time.time()
    m = _DIAG.get(ip)
    if not m or now - m[0] > 60:
        m = _DIAG[ip] = [now, 0]
    m[1] += 1
    if m[1] > 20:
        return {"ok": False}
    raw = (await req.body())[:8192]
    try:
        body = json.loads(raw)
    except Exception:
        return {"ok": False}
    if len(_DIAG) > 5000:
        _DIAG.clear()
    print("DIAG", json.dumps({"ua": str(req.headers.get("user-agent", ""))[:160], "d": body}, ensure_ascii=False)[:9000],
          flush=True)
    return {"ok": True}


@app.post("/api/players")
async def api_new_player(req: Request):
    body = await _json(req)
    pid, token = uuid.uuid4().hex, secrets.token_urlsafe(24)
    name = clean_name(body.get("name"))
    if player_by_login(name):                      # un invité ne prend pas le pseudo d'un compte
        name = clean_name("")
    with _db_lock, db() as c:
        c.execute("INSERT INTO players(id, token, name, created) VALUES(?,?,?,?)", (pid, token, name, now_ms()))
    return {"id": pid, "token": token, "name": name}


@app.post("/api/players/me")
async def api_rename(req: Request):
    body = await _json(req)
    p = player_by_token(body.get("token"))
    if not p:
        raise HTTPException(401, "Clé de joueur inconnue.")
    if p.get("login"):                             # compte : le pseudo change, il reste unique (et sert à se connecter)
        name = clean_pseudo(body.get("name"))
        other = player_by_login(name)
        if other and other["id"] != p["id"]:
            raise HTTPException(409, "pseudo_taken")
        with _db_lock, db() as c:
            c.execute("UPDATE players SET name=?, login=? WHERE id=?", (name, login_key(name), p["id"]))
        return {"name": name, "account": True}
    name = clean_name(body.get("name"))
    if player_by_login(name):
        raise HTTPException(409, "pseudo_taken")
    with _db_lock, db() as c:
        c.execute("UPDATE players SET name=? WHERE id=?", (name, p["id"]))
    return {"name": name, "account": False}


@app.post("/api/account/register")
async def api_register(req: Request):
    """Crée un compte. Avec la clé d'invité du navigateur (token), le compte est posé sur ce joueur : ses paris
    (cette semaine et les précédentes) sont repris tels quels."""
    body = await _json(req)
    name, pw = clean_pseudo(body.get("pseudo")), check_new_password(body.get("password"))
    h = hash_pw(pw)
    with _db_lock:
        if player_by_login(name):
            raise HTTPException(409, "pseudo_taken")
        p = player_by_token(body.get("token"))
        with db() as c:
            if p:
                if p.get("login"):
                    raise HTTPException(409, "already_account")
                c.execute("UPDATE players SET name=?, login=?, pw=?, acct_at=? WHERE id=?",
                          (name, login_key(name), h, now_ms(), p["id"]))
                tok = p["token"]
            else:
                tok = secrets.token_urlsafe(24)
                c.execute("INSERT INTO players(id, token, name, created, login, pw, acct_at) VALUES(?,?,?,?,?,?,?)",
                          (uuid.uuid4().hex, tok, name, now_ms(), login_key(name), h, now_ms()))
    return account_public(player_by_token(tok))


@app.post("/api/account/login")
async def api_login(req: Request):
    """Connexion. Si le navigateur avait une clé d'invité avec des paris, ces paris passent sur le compte pour
    chaque semaine où le compte n'a encore rien joué (jamais deux portefeuilles mélangés dans une même semaine)."""
    body = await _json(req)
    name, pw = str(body.get("pseudo") or ""), str(body.get("password") or "")
    ip = req.client.host if req.client else "?"
    kp, ki = ("pseudo", login_key(name)), ("ip", ip)
    if _too_many_fails((kp, FAIL_MAX_PSEUDO), (ki, FAIL_MAX_IP)):
        raise HTTPException(429, "too_many_attempts")
    p = player_by_login(name) if name.strip() else None
    if not p or not p.get("pw") or not verify_pw(pw, p["pw"]):
        _note_fail(kp, ki)
        raise HTTPException(401, "bad_login")
    LOGIN_FAILS.pop(kp, None)
    moved, kept = 0, 0
    guest = player_by_token(body.get("token"))
    if guest and not guest.get("login") and guest["id"] != p["id"]:
        with _db_lock, db() as c:
            mine = {r[0] for r in c.execute("SELECT DISTINCT week FROM bets WHERE player=?", (p["id"],))}
            for (wk,) in c.execute("SELECT DISTINCT week FROM bets WHERE player=?", (guest["id"],)).fetchall():
                n = c.execute("SELECT COUNT(*) FROM bets WHERE player=? AND week=?", (guest["id"], wk)).fetchone()[0]
                if wk in mine:
                    kept += n
                else:
                    c.execute("UPDATE bets SET player=? WHERE player=? AND week=?", (p["id"], guest["id"], wk)); moved += n
    return dict(account_public(p), moved=moved, left_behind=kept)


@app.post("/api/account/password")
async def api_password(req: Request):
    """Changer de mot de passe : la clé change aussi, les autres appareils sont déconnectés."""
    body = await _json(req)
    p = player_by_token(body.get("token"))
    if not p or not p.get("login"):
        raise HTTPException(401, "Clé de joueur inconnue.")
    if not verify_pw(body.get("old", ""), p["pw"]):
        raise HTTPException(401, "bad_password")
    h, tok = hash_pw(check_new_password(body.get("new"))), secrets.token_urlsafe(24)
    with _db_lock, db() as c:
        c.execute("UPDATE players SET pw=?, token=? WHERE id=?", (h, tok, p["id"]))
    return account_public(player_by_token(tok))


@app.post("/api/admin/password")
async def api_admin_password(req: Request):
    """Mot de passe oublié : réinitialisé par l'administrateur (GC_ADMIN_KEY). La clé du joueur change.
    Usage : POST /api/admin/password {"key": "<GC_ADMIN_KEY>", "pseudo": "...", "password": "nouveau"}"""
    body = await _json(req)
    admin = os.environ.get("GC_ADMIN_KEY", "")
    if len(admin) < 16 or not secrets.compare_digest(str(body.get("key", "")), admin):
        raise HTTPException(403, "Non autorisé.")
    p = player_by_login(str(body.get("pseudo") or ""))
    if not p:
        raise HTTPException(404, "Pseudo inconnu.")
    h, tok = hash_pw(check_new_password(body.get("password"))), secrets.token_urlsafe(24)
    with _db_lock, db() as c:
        c.execute("UPDATE players SET pw=?, token=? WHERE id=?", (h, tok, p["id"]))
    return {"ok": True, "pseudo": p["name"]}


@app.get("/api/me")
def api_me(token: str = ""):
    p = player_by_token(token)
    if not p:
        raise HTTPException(401, "Clé de joueur inconnue.")
    w = _need_week(); t = now_ms()
    L = ledger(w, player_bets(p["id"], w), t)
    rows = season_rows(t)
    mine = next((r for r in rows if r["id"] == p["id"]), None)
    season = {"rank": mine["rank"] if mine else None, "net": mine["net"] if mine else season_net(p["id"], t)["net"],
              "players": len(rows)}
    return {"name": p["name"], "account": bool(p.get("login")), "fav_team": p.get("fav_team"), "week": w.start, "now": t,
            "season": season, **L}


# ------------------------------------------------------------------ « My team » : équipe favorite d'un compte
_TEAM_RE = re.compile(r"^[A-Z]{2,4}$")


@app.post("/api/account/team")
async def api_fav_team(req: Request):
    """Équipe favorite (rubrique « My team » du site) : comptes seulement ; team vide = aucune."""
    body = await _json(req)
    p = player_by_token(body.get("token"))
    if not p or not p.get("login"):
        raise HTTPException(401, "account_required")
    team = str(body.get("team") or "").strip().upper() or None
    if team is not None:
        known = {a for w in load_weeks().values() for a in w.doc["teams"]}
        if not _TEAM_RE.match(team) or team not in known:
            raise HTTPException(400, "unknown_team")
    with _db_lock, db() as c:
        c.execute("UPDATE players SET fav_team=? WHERE id=?", (team, p["id"]))
    return {"fav_team": team}


# ------------------------------------------------------------------ rappels avant le coup d'envoi (bloc 2, étape 6)
# Web Push (standard des navigateurs) : le serveur prévient chaque appareil abonné RAPPEL_MIN minutes avant le coup
# d'envoi des matchs de l'équipe favorite du compte (si « My team's games » est coché sur l'appareil) et des matchs
# choisis d'une cloche dans le calendrier (comptes et invités). Rien d'un score : les équipes et l'heure seulement.
# Clés VAPID dans les variables (Railway) : GC_VAPID_PUBLIC, GC_VAPID_PRIVATE (base64url), GC_VAPID_SUBJECT (mailto:…).
# Les changer coupe tous les abonnements. Sans clés : pas de rappel (le site le dit dans Réglages).
RAPPEL_MIN = 10
PUSH_TICK = float(os.environ.get("GC_PUSH_TICK", "30"))   # secondes entre deux tours de la boucle d'envoi (tests : moins)
PUSH_MAX_PAR_JOUEUR = 10             # appareils abonnés par joueur
VAPID_PUBLIC = os.environ.get("GC_VAPID_PUBLIC", "").strip()
VAPID_PRIVATE = os.environ.get("GC_VAPID_PRIVATE", "").strip()
VAPID_SUBJECT = os.environ.get("GC_VAPID_SUBJECT", "").strip() or "mailto:contact@snapline.live"
_B64URL = re.compile(r"^[A-Za-z0-9_-]{8,200}={0,2}$")
PUSH_LOG = []                        # GC_PUSH_FAKE=1 (tests) : les envois sont notés ici au lieu de partir
PHASE_NOM = {"regular": "Regular season", "semifinal": "Conference final", "ai_bowl": "Grand Final"}


def push_ok():
    return bool(VAPID_PUBLIC and VAPID_PRIVATE) or os.environ.get("GC_PUSH_FAKE") == "1"


def rappel_texte(w, g, t):
    """Titre, texte et lien d'un rappel (équipes et heure : jamais de score)."""
    T = w.doc["teams"]
    a, h = T.get(g["away"], {}), T.get(g["home"], {})
    mins = max(1, round((g["ko"] - t) / 60000))
    ko = datetime.fromtimestamp(g["ko"] / 1000, TZ).strftime("%H:%M")
    phase = PHASE_NOM.get(g["phase"], "")
    if g["phase"] == "semifinal" and not w.doc["week"].get("league"):
        phase = "Semi-final"
    return {"title": f"{g['away']} @ {g['home']} · kickoff in {mins} min",
            "body": f"{a.get('name', g['away'])} @ {h.get('name', g['home'])} · {phase} · {ko}. Tap to watch live.",
            "url": f"/?watch={g['id']}", "tag": f"ko-{g['id']}"}


def rappels_dus(t, subs, bells, sent):
    """Rappels à envoyer à l'instant t (fonction pure, testée) :
    subs  : [{endpoint, player, fav (0/1), fav_team}] ; bells : {(player, week, game)} ; sent : {(endpoint, week, game)}.
    Un match est dû entre RAPPEL_MIN minutes avant son coup d'envoi et le coup d'envoi, s'il est révélé (équipes des
    playoffs connues). Renvoie [(sub, week, match)]."""
    out = []
    for w in load_weeks().values():
        if w.open > t:
            continue
        for g in w.sched:
            if not (g["ko"] - RAPPEL_MIN * 60000 <= t < g["ko"]) or not w.teams_known(g, t):
                continue
            for s in subs:
                if (s["endpoint"], w.start, g["id"]) in sent:
                    continue
                mien = s.get("fav") and s.get("fav_team") in (g["home"], g["away"])
                if mien or (s["player"], w.start, g["id"]) in bells:
                    out.append((s, w, g))
    return out


def _push_envoyer(sub, data):
    """Un envoi. Renvoie True (parti), False (abonnement à supprimer : 404 / 410) ; lève sinon (réessayé au tour suivant)."""
    if os.environ.get("GC_PUSH_FAKE") == "1":
        PUSH_LOG.append({"endpoint": sub["endpoint"], **data})
        return True
    from pywebpush import webpush, WebPushException
    try:
        webpush({"endpoint": sub["endpoint"], "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]}},
                data=json.dumps(data), vapid_private_key=VAPID_PRIVATE, vapid_claims={"sub": VAPID_SUBJECT},
                ttl=RAPPEL_MIN * 60, timeout=10)
        return True
    except WebPushException as e:
        if e.response is not None and e.response.status_code in (404, 410):
            return False
        raise


def _push_oublier(endpoint):
    with _db_lock, db() as c:
        c.execute("DELETE FROM push_subs WHERE endpoint=?", (endpoint,))
        c.execute("DELETE FROM push_sent WHERE endpoint=?", (endpoint,))


def push_tour(t=None):
    """Un tour de la boucle : envoie les rappels dus, note chaque envoi (aucun doublon). Renvoie le nombre d'envois."""
    t = now_ms() if t is None else t
    with db() as c:
        subs = [dict(r) for r in c.execute("SELECT s.*, p.fav_team FROM push_subs s LEFT JOIN players p ON p.id=s.player")]
        bells = {tuple(r) for r in c.execute("SELECT player, week, game FROM push_bells")}
        sent = {tuple(r) for r in c.execute("SELECT endpoint, week, game FROM push_sent")}
    n = 0
    for s, w, g in rappels_dus(t, subs, bells, sent):
        try:
            ok = _push_envoyer(s, rappel_texte(w, g, t))
        except Exception as e:
            print("rappel non envoyé :", g["id"], str(e)[:200])
            continue
        if not ok:
            _push_oublier(s["endpoint"])
            continue
        n += 1
        with _db_lock, db() as c:
            c.execute("INSERT OR IGNORE INTO push_sent(endpoint, week, game, at) VALUES(?,?,?,?)",
                      (s["endpoint"], w.start, g["id"], t))
    return n


def _push_loop():
    while True:
        try:
            if push_ok() and os.environ.get("GC_PUSH_LOOP", "1") == "1":   # GC_PUSH_LOOP=0 : arrêtée (tests)
                push_tour()
        except Exception as e:
            print("rappels :", e)
        time.sleep(PUSH_TICK)


def _push_sub_from(body):
    s = body.get("subscription") or {}
    ep, keys = str(s.get("endpoint") or ""), s.get("keys") or {}
    p256, auth = str(keys.get("p256dh") or ""), str(keys.get("auth") or "")
    if not (ep.startswith("https://") and len(ep) <= 1000 and _B64URL.match(p256) and _B64URL.match(auth)):
        raise HTTPException(400, "bad_subscription")
    return ep, p256, auth


def _push_player(body):
    p = player_by_token(body.get("token"))
    if not p:
        raise HTTPException(401, "Clé de joueur inconnue.")
    return p


@app.get("/api/push/key")
def api_push_key():
    cle = VAPID_PUBLIC or ("BPushFakeTestKey0123456789" if os.environ.get("GC_PUSH_FAKE") == "1" else None)   # tests
    return {"public_key": cle, "enabled": push_ok(), "minutes": RAPPEL_MIN}


@app.post("/api/push/subscribe")
async def api_push_subscribe(req: Request):
    """Abonne cet appareil (ou met à jour son réglage « My team's games »)."""
    body = await _json(req)
    p = _push_player(body)
    ep, p256, auth = _push_sub_from(body)
    fav = 1 if body.get("fav") else 0
    with _db_lock, db() as c:
        if c.execute("SELECT COUNT(*) FROM push_subs WHERE player=? AND endpoint<>?", (p["id"], ep)).fetchone()[0] >= PUSH_MAX_PAR_JOUEUR:
            raise HTTPException(429, "too_many_devices")
        c.execute("INSERT INTO push_subs(endpoint, player, p256dh, auth, fav, created) VALUES(?,?,?,?,?,?) "
                  "ON CONFLICT(endpoint) DO UPDATE SET player=excluded.player, p256dh=excluded.p256dh, "
                  "auth=excluded.auth, fav=excluded.fav", (ep, p["id"], p256, auth, fav, now_ms()))
    return {"ok": True, "fav": bool(fav), "fav_team": p.get("fav_team")}


@app.post("/api/push/unsubscribe")
async def api_push_unsubscribe(req: Request):
    body = await _json(req)
    p = _push_player(body)
    ep = str(body.get("endpoint") or "")
    with _db_lock, db() as c:
        c.execute("DELETE FROM push_subs WHERE endpoint=? AND player=?", (ep, p["id"]))
    return {"ok": True}


_PUSH_TEST_AT = {}


@app.post("/api/push/test")
async def api_push_test(req: Request):
    """« Send a test » (Réglages) : une notification tout de suite sur cet appareil."""
    body = await _json(req)
    p = _push_player(body)
    ep = str(body.get("endpoint") or "")
    with db() as c:
        r = c.execute("SELECT * FROM push_subs WHERE endpoint=? AND player=?", (ep, p["id"])).fetchone()
    if not r:
        raise HTTPException(404, "not_subscribed")
    if not push_ok():
        raise HTTPException(503, "push_disabled")
    if time.time() - _PUSH_TEST_AT.get(ep, 0) < 10:
        raise HTTPException(429, "too_soon")
    _PUSH_TEST_AT[ep] = time.time()
    try:
        ok = _push_envoyer(dict(r), {"title": "Snapline · test", "url": "/", "tag": "test",
                                     "body": f"Reminders arrive like this, {RAPPEL_MIN} minutes before kickoff."})
    except Exception as e:
        print("test de rappel :", str(e)[:200])
        raise HTTPException(502, "push_failed")
    if not ok:
        _push_oublier(ep)
        raise HTTPException(410, "subscription_gone")
    return {"ok": True}


@app.get("/api/push/bells")
def api_push_bells(token: str = ""):
    p = player_by_token(token)
    if not p:
        raise HTTPException(401, "Clé de joueur inconnue.")
    w = _need_week()
    with db() as c:
        games = [r[0] for r in c.execute("SELECT game FROM push_bells WHERE player=? AND week=?", (p["id"], w.start))]
    return {"week": w.start, "games": games}


@app.post("/api/push/bell")
async def api_push_bell(req: Request):
    """Cloche d'un match du calendrier (on = prévenir, sinon non) : semaine en cours, match pas encore commencé."""
    body = await _json(req)
    p = _push_player(body)
    w, t = _need_week(), now_ms()
    g = w.by.get(str(body.get("game") or ""))
    if not g or w.status(g, t) != "upcoming":
        raise HTTPException(400, "bad_game")
    with _db_lock, db() as c:
        if body.get("on"):
            c.execute("INSERT OR IGNORE INTO push_bells(player, week, game) VALUES(?,?,?)", (p["id"], w.start, g["id"]))
        else:
            c.execute("DELETE FROM push_bells WHERE player=? AND week=? AND game=?", (p["id"], w.start, g["id"]))
    return {"ok": True, "game": g["id"], "on": bool(body.get("on"))}


@app.get("/api/push/_log")
def api_push_log():
    """Tests seulement (GC_TEST_HOOK=1 et GC_PUSH_FAKE=1) : les rappels « envoyés »."""
    if os.environ.get("GC_TEST_HOOK") != "1":
        raise HTTPException(404)
    return {"sent": PUSH_LOG}


# service worker (à la racine : il reçoit les rappels pour tout le site), manifeste et icônes (écran d'accueil iPhone)
@app.get("/sw.js")
def service_worker():
    return FileResponse(os.path.join(HERE, "static", "sw.js"), media_type="text/javascript",
                        headers={"Cache-Control": "no-cache"})


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(os.path.join(HERE, "static", "manifest.webmanifest"), media_type="application/manifest+json")


@app.get("/icons/{name}")
def icons(name: str):
    # favicon.* : l'icône de l'onglet et de Google (dégradé du logo, outils/site/faire_favicon.js) ; icon-* : l'écran
    # d'accueil du téléphone (bleu-vert)
    if name not in ("icon-180.png", "icon-192.png", "icon-512.png", "icon-maskable-512.png", "favicon.svg",
                    "favicon-48.png", "favicon-96.png", "favicon-192.png"):
        raise HTTPException(404)
    return FileResponse(os.path.join(HERE, "static", "icons", name),
                        media_type="image/svg+xml" if name.endswith(".svg") else "image/png",
                        headers={"Cache-Control": "public, max-age=86400"})


@app.get("/favicon.ico")
def favicon():
    """L'icône demandée d'office par les navigateurs et les robots (Google) : PNG 16, 32 et 48 dans un .ico."""
    return FileResponse(os.path.join(HERE, "static", "favicon.ico"), media_type="image/x-icon",
                        headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/teams/history")
def api_teams_history():
    """Semaines TERMINÉES (Grand Final jouée) : champion, finaliste, têtes de série et classement final de chaque équipe —
    rien d'une semaine en cours (pas de spoiler)."""
    t = now_ms()
    out = []
    for w in sorted(load_weeks().values(), key=lambda w: w.monday):
        if w.open > t or w.status(w.final, t) != "final":
            continue
        d = w.doc
        out.append({"week": w.start, "index": d["week"]["index"], "champion": d.get("champion"),
                    "runner_up": d.get("runner_up"), "seeds": d.get("seeds"),
                    "standings": [{k: r.get(k) for k in ("rank", "team", "w", "l", "t", "pf", "pa")}
                                  for r in d.get("standings") or []]})
    return {"now": t, "weeks": out}


# ------------------------------------------------------------------ histoire, records, carrières (bloc 2, étape 5)
_HIST, _HIST_LOCK = {}, threading.Lock()
# première semaine comptée dans l'histoire (décision de Guillaume, 14/10) : la semaine 1 n'avait que 4 franchises, qui
# auraient une saison de plus que les autres dans les franchises, records et carrières. GC_HIST_DEPUIS=1 : toutes.
try:
    HIST_DEPUIS = max(1, int(os.environ.get("GC_HIST_DEPUIS", "2")))
except ValueError:
    HIST_DEPUIS = 2


def _feuille(w, gid):
    """Feuille de match d'un match (moteur/histoire.py), calculée une fois par match."""
    fm = w.__dict__.setdefault("feuilles", {})
    if gid not in fm:
        fm[gid] = _histoire.feuille_de_match(w.feed(gid))
    return fm[gid]


def league_history(t, finished_weeks=False):
    """Histoire de la ligue à l'instant t : semaines publiées, matchs TERMINÉS seulement (rien d'un match pas encore joué).
    finished_weeks : seulement les semaines dont la Grand Final est jouée (réglage « Hide scores » du site).
    À partir de la semaine HIST_DEPUIS. Mis en cache tant qu'aucun match ne se termine."""
    ws = [w for w in sorted(load_weeks().values(), key=lambda w: w.monday)
          if w.open <= t and w.doc["week"]["index"] >= HIST_DEPUIS]
    sem, cle = [], []
    for w in ws:
        fini = w.status(w.final, t) == "final"
        if finished_weeks and not fini:
            continue
        gs = [g for g in w.sched if w.status(g, t) == "final"]
        if not gs:
            continue
        cle.append((w.start, len(gs)))
        sem.append((w, gs, fini))
    cle = tuple(cle)
    with _HIST_LOCK:
        if cle not in _HIST:
            if len(_HIST) > 8:
                _HIST.clear()
            _HIST[cle] = _histoire.histoire([{"index": w.doc["week"]["index"], "start": w.start, "doc": w.doc,
                                               "terminee": fini, "matchs": [(g, _feuille(w, g["id"])) for g in gs]}
                                              for w, gs, fini in sem])
        return _HIST[cle]


@app.get("/api/league/history")
def api_league_history(finished_weeks: int = 0):
    """Saisons (une par semaine), franchises, records (un match, une saison, une carrière). Sans les carrières détaillées
    (voir /api/league/career/{id})."""
    t = now_ms()
    h = league_history(t, bool(finished_weeks))
    return {"now": t, "since_week": HIST_DEPUIS, **{k: v for k, v in h.items() if k != "careers"}}


@app.get("/api/league/career/{pid}")
def api_league_career(pid: str, finished_weeks: int = 0):
    """Les carrières d'une place de roster (identifiant) : le joueur actuel et ceux qui l'ont tenue avant lui."""
    if not re.fullmatch(r"[A-Z0-9]{2,4}_[A-Z]{1,4}\d{1,2}", pid):
        raise HTTPException(400, "bad_id")
    t = now_ms()
    return {"now": t, "careers": _histoire.carriere(league_history(t, bool(finished_weeks)), pid)}


def _check_pick(w, pk, t):
    """Une sélection envoyée par la page : (sélection validée, None) ou (None, refus)."""
    key = str(pk.get("key", ""))
    q = w.quote(key, t)
    if q is None:
        return None, {"key": key, "reason": "unknown"}
    if q["locked"]:
        return None, {"key": key, "reason": "closed", "why": q["locked"]}
    try:
        price = float(pk.get("price_dec")); line = pk.get("line")
        line = None if line is None else float(line)
    except (TypeError, ValueError):
        return None, {"key": key, "reason": "invalid"}
    if abs(price - q["price_dec"]) > 0.006 or line != q["line"]:
        return None, {"key": key, "reason": "price", "price_dec": q["price_dec"], "line": q["line"]}
    return {"key": key, "price_dec": q["price_dec"], "line": q["line"],
            "title": str(pk.get("title", ""))[:120], "sub": str(pk.get("sub", ""))[:120]}, None


def _sgp(w, p, cb, raw, t):
    """Combiné sur un même match (section 86) : (pari, None) ou (None, refus). Cote recalculée ici (meme_match) ;
    la page envoie celle qu'elle affiche (price_dec) : si elle diffère, refus « sgp_price » avec la bonne."""
    if not (_mm.MIN_LEGS <= len(raw) <= _mm.MAX_LEGS):
        return None, {"reason": "legs"}
    legs, bads = [], []
    for x in raw:
        leg, bad = _check_pick(w, x, t)
        (bads.append(bad) if bad else legs.append(leg))
    if bads:
        return None, {"reason": "legs_changed", "legs": bads}
    g = w.by[legs[0]["key"].split(":")[0]]
    if w.status(g, t) != "upcoming":
        return None, {"reason": "sgp_live"}
    o = w.feed(g["id"])["game"].get("pregame_odds") or {}
    if o.get("p_home") is None or o.get("spread_home") is None or o.get("total") is None:
        return None, {"reason": "sgp_na"}
    sel = [tuple(L["key"].split(":")[1:]) for L in legs]
    r = _mm.prix(o, sel, [L["price_dec"] for L in legs])
    if "refus" in r:
        return None, {"reason": r["refus"]}
    D = r["price_dec"]
    try:
        vu = float(cb.get("price_dec"))
    except (TypeError, ValueError):
        vu = float("nan")
    if not abs(vu - D) <= max(0.01, 0.003 * D):
        return None, {"reason": "sgp_price", "price_dec": D}
    for L, (mk, _) in zip(legs, sel):
        if mk == "ml" and r.get("push_price"):
            L["push_price"] = r["push_price"]
    n = len(legs)
    return {"id": "c" + uuid.uuid4().hex[:16], "player": p["id"], "week": w.start, "key": "sgp", "price_dec": D,
            "line": None, "stake": _stake(cb.get("stake")), "pt": t, "title": f"{n}-leg Same Game Combo",
            "sub": " · ".join(l["title"] for l in legs)[:120], "legs": legs}, None


def _stake(x):
    try:
        return round(float(x), 2)
    except (TypeError, ValueError):
        return float("nan")


@app.post("/api/bets")
async def api_bets(req: Request):
    """picks = paris simples ; combos = [{stake, legs: [sélections]}] (2 à 6 sélections, une par match, pas de futures)."""
    body = await _json(req)
    p = player_by_token(body.get("token"))
    if not p:
        raise HTTPException(401, "Clé de joueur inconnue.")
    picks, combos = body.get("picks") or [], body.get("combos") or []
    if not isinstance(picks, list) or not isinstance(combos, list) or not (1 <= len(picks) + len(combos) <= 20):
        raise HTTPException(400, "Envoyez entre 1 et 20 paris.")
    w = _need_week()
    accepted, rejected = [], []
    with _db_lock:
        t = now_ms()
        if not (w.open <= t < w.reset):
            raise HTTPException(409, "Les paris de cette semaine sont fermés.")
        bal = ledger(w, player_bets(p["id"], w), t)["balance"]
        rows = []

        def take(stake, rej):
            nonlocal bal
            if not (stake >= MIN_STAKE):
                rejected.append(dict(rej, reason="stake")); return False
            if stake > bal + 1e-9:
                rejected.append(dict(rej, reason="balance", balance=bal)); return False
            bal = round(bal - stake, 2); return True

        for pk in picks:
            leg, bad = _check_pick(w, pk, t)
            if bad:
                rejected.append(bad); continue
            stake = _stake(pk.get("stake"))
            if not take(stake, {"key": leg["key"]}):
                continue
            b = dict(leg, id="b" + uuid.uuid4().hex[:16], player=p["id"], week=w.start, stake=stake, pt=t, legs=None)
            rows.append(b); accepted.append(b)
        for ci, cb in enumerate(combos):
            raw = cb.get("legs") if isinstance(cb, dict) else None
            if not isinstance(raw, list) or not (COMBO_MIN <= len(raw) <= COMBO_MAX):
                rejected.append({"combo": ci, "reason": "legs"}); continue
            keys = [str(x.get("key", "")) for x in raw]
            if any(k.startswith("fut:") for k in keys):
                rejected.append({"combo": ci, "reason": "futures"}); continue
            gids = {k.split(":")[0] for k in keys}
            if len(gids) == 1 and same_game_on():
                b, bad = _sgp(w, p, cb, raw, t)
                if bad:
                    rejected.append(dict(bad, combo=ci)); continue
                if not take(b["stake"], {"combo": ci}):
                    continue
                rows.append(b); accepted.append(b); continue
            if len(gids) != len(keys):
                rejected.append({"combo": ci, "reason": "same_game"}); continue
            legs, bads = [], []
            for x in raw:
                leg, bad = _check_pick(w, x, t)
                (bads.append(bad) if bad else legs.append(leg))
            if bads:
                rejected.append({"combo": ci, "reason": "legs_changed", "legs": bads}); continue
            stake = _stake(cb.get("stake"))
            if not take(stake, {"combo": ci}):
                continue
            prod = 1.0
            for leg in legs:
                prod *= leg["price_dec"]
            n = len(legs)
            b = {"id": "c" + uuid.uuid4().hex[:16], "player": p["id"], "week": w.start, "key": "combo",
                 "price_dec": round(prod, 4), "line": None, "stake": stake, "pt": t,
                 "title": f"{n}-leg combo", "sub": " · ".join(l["title"] for l in legs)[:120], "legs": legs}
            rows.append(b); accepted.append(b)
        if rows:
            with db() as c:
                c.executemany("INSERT INTO bets(id, player, week, key, price_dec, line, stake, pt, title, sub, legs) "
                              "VALUES(:id,:player,:week,:key,:price_dec,:line,:stake,:pt,:title,:sub,:legs)",
                              [dict(r, legs=json.dumps(r["legs"], ensure_ascii=False) if r["legs"] else None) for r in rows])
    return {"now": t, "accepted": accepted, "rejected": rejected, "balance": bal}


@app.post("/api/cashout")
async def api_cashout(req: Request):
    """Cash-out d'un pari ouvert de la semaine en cours. La page envoie le montant qu'elle affiche ; s'il ne correspond
    plus (cote qui a bougé), rien n'est fait et le nouveau montant est renvoyé."""
    body = await _json(req)
    p = player_by_token(body.get("token"))
    if not p:
        raise HTTPException(401, "Clé de joueur inconnue.")
    w = _need_week()
    with _db_lock:
        t = now_ms()
        with db() as c:
            r = c.execute("SELECT * FROM bets WHERE id=? AND player=?", (str(body.get("id", "")), p["id"])).fetchone()
        if not r:
            raise HTTPException(404, "Pari inconnu.")
        b = bet_row(r)
        if b["week"] != w.start or not (w.open <= t < w.reset) or b["pt"] > t:
            return {"ok": False, "reason": "closed"}
        amt, why = w.cash_value(b, t)
        if amt is None:
            return {"ok": False, "reason": "unavailable", "why": why}
        try:
            want = float(body.get("amount"))
        except (TypeError, ValueError):
            want = -1.0
        if abs(want - amt) > max(0.02, 0.002 * amt):
            return {"ok": False, "reason": "value", "amount": amt}
        with db() as c:
            c.execute("UPDATE bets SET cashed_at=?, cashed_amt=? WHERE id=?", (t, amt, b["id"]))
        bal = ledger(w, player_bets(p["id"], w), t)["balance"]
    return {"ok": True, "id": b["id"], "amount": amt, "at": t, "balance": bal}


@app.get("/api/history")
def api_history(token: str = "", week: str = ""):
    """Historique : sans « week », une ligne par semaine où le joueur a parié ; avec « week », tous ses paris de cette semaine."""
    p = player_by_token(token)
    if not p:
        raise HTTPException(401, "Clé de joueur inconnue.")
    t = now_ms(); cur = current_week(t)
    weeks = {w.start: w for w in load_weeks().values() if w.open <= t}
    if week:
        w = weeks.get(week)
        if w is None:
            raise HTTPException(404, "Semaine inconnue.")
        L = ledger(w, player_bets(p["id"], w), t)
        return {"week": w.start, "index": w.doc["week"]["index"], "current": w is cur, "now": t, **L}
    with db() as c:
        played = {r[0] for r in c.execute("SELECT DISTINCT week FROM bets WHERE player=?", (p["id"],))}
    out = []
    for start in sorted(played & set(weeks), reverse=True):
        w = weeks[start]
        L = ledger(w, player_bets(p["id"], w), t)
        a = _season_agg(L["bets"], [w], t)
        out.append({"week": start, "index": w.doc["week"]["index"], "current": w is cur, "balance": L["balance"],
                    "net": a["net"], "bets": len(L["bets"]), "won": L["won"], "lost": L["lost"], "open": L["open"]})
    return {"now": t, "weeks": out}


@app.get("/api/leaderboard")
def api_leaderboard(token: str = "", scope: str = "week"):
    """scope=week : soldes de la semaine en cours (tous les joueurs) ; scope=season : gains nets cumulés (comptes)."""
    w = _need_week(); t = now_ms()
    me = player_by_token(token)
    if scope == "season":
        rows = season_rows(t)
        out = [{k: r[k] for k in ("rank", "name", "net", "weeks", "bets", "won", "lost")} | {"me": bool(me and me["id"] == r["id"])}
               for r in rows]
        mine = next((r for r in out if r["me"]), None)
        if me and not mine:                         # invité, ou compte sans pari : sa ligne sans rang
            a = season_net(me["id"], t)
            mine = dict(a, rank=None, name=me["name"], me=True, account=bool(me.get("login")))
        return {"scope": "season", "week": w.start, "weeks": [x.start for x in season_weeks(t)], "players": len(out),
                "top": out[:50], "me": mine}
    with db() as c:
        players = [dict(r) for r in c.execute("SELECT DISTINCT p.* FROM players p JOIN bets b ON b.player=p.id WHERE b.week=?", (w.start,))]
    rows = []
    for p in players:
        L = ledger(w, player_bets(p["id"], w), t)
        if not L["bets"]:
            continue
        rows.append({"name": p["name"], "balance": L["balance"], "bets": len(L["bets"]), "won": L["won"], "lost": L["lost"],
                     "account": bool(p.get("login")), "me": bool(me and me["id"] == p["id"])})
    rows.sort(key=lambda r: (-r["balance"], r["name"]))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    mine = next((r for r in rows if r["me"]), None)
    return {"scope": "week", "week": w.start, "players": len(rows), "top": rows[:20], "me": mine}


# ------------------------------------------------------------------ ligues privées (bloc 2, étape 7)
# Une ligue = des comptes qui se classent entre eux, avec les mêmes mesures que le classement général : solde de la
# semaine et gains nets de la saison (leurs paris restent les leurs). On rejoint avec un code (ou le lien ?join=CODE).
# Le créateur renomme, retire un membre, change le code (l'ancien lien ne marche plus) et supprime ; tout membre peut
# partir (si le créateur part, la ligue passe au membre le plus ancien ; vide, elle disparaît).
LIGUE_MAX_MEMBRES = 50
LIGUE_MAX_PAR_COMPTE = 10
LIGUE_CODE_ALPHA = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"     # sans 0/O ni 1/I : se dicte et se recopie sans erreur
LIGUE_CODE_LEN = 6
_CODE_RE = re.compile(r"^[A-Z2-9]{6}$")
JOIN_FAIL_MAX_JOUEUR, JOIN_FAIL_MAX_IP = 10, 40          # codes faux en 15 min (essais en série refusés)


def _ligue_code():
    return "".join(secrets.choice(LIGUE_CODE_ALPHA) for _ in range(LIGUE_CODE_LEN))


def _ligue_nom(s):
    nom = re.sub(r"\s+", " ", str(s or "")).strip()
    if NAME_RE.search(nom):
        raise HTTPException(400, "league_name_chars")
    if not (3 <= len(nom) <= 32):
        raise HTTPException(400, "league_name_length")
    return nom


def _compte(token):
    p = player_by_token(token)
    if not p:
        raise HTTPException(401, "Clé de joueur inconnue.")
    if not p.get("login"):
        raise HTTPException(403, "account_required")
    return p


def _ligue(c, lid):
    r = c.execute("SELECT * FROM leagues WHERE id=?", (str(lid or ""),)).fetchone()
    if not r:
        raise HTTPException(404, "league_not_found")
    return dict(r)


def _membres(c, lid):
    return [dict(r) for r in c.execute(
        "SELECT p.id, p.name, m.joined FROM league_members m JOIN players p ON p.id=m.player WHERE m.league=? ORDER BY m.joined, p.name",
        (lid,))]


def _ligue_public(c, L, pid):
    n = c.execute("SELECT COUNT(*) FROM league_members WHERE league=?", (L["id"],)).fetchone()[0]
    return {"id": L["id"], "name": L["name"], "code": L["code"], "owner": L["owner"] == pid, "members": n,
            "max": LIGUE_MAX_MEMBRES}


def _ip(req):
    return (req.headers.get("x-forwarded-for") or (req.client.host if req.client else "") or "?").split(",")[0].strip()


@app.get("/api/leagues")
def api_leagues(token: str = ""):
    """Mes ligues (comptes)."""
    p = _compte(token)
    with db() as c:
        ls = [dict(r) for r in c.execute("SELECT l.* FROM leagues l JOIN league_members m ON m.league=l.id WHERE m.player=? "
                                         "ORDER BY m.joined", (p["id"],))]
        return {"leagues": [_ligue_public(c, L, p["id"]) for L in ls], "max": LIGUE_MAX_PAR_COMPTE}


@app.post("/api/leagues/create")
async def api_league_create(req: Request):
    body = await _json(req)
    p = _compte(body.get("token"))
    nom = _ligue_nom(body.get("name"))
    with _db_lock, db() as c:
        if c.execute("SELECT COUNT(*) FROM league_members WHERE player=?", (p["id"],)).fetchone()[0] >= LIGUE_MAX_PAR_COMPTE:
            raise HTTPException(409, "too_many_leagues")
        lid, t = uuid.uuid4().hex[:12], now_ms()
        for _ in range(20):
            code = _ligue_code()
            if not c.execute("SELECT 1 FROM leagues WHERE code=?", (code,)).fetchone():
                break
        c.execute("INSERT INTO leagues(id, name, code, owner, created) VALUES(?,?,?,?,?)", (lid, nom, code, p["id"], t))
        c.execute("INSERT INTO league_members(league, player, joined) VALUES(?,?,?)", (lid, p["id"], t))
        return {"league": _ligue_public(c, _ligue(c, lid), p["id"])}


def _code_essai(req, pid, code):
    """Un code d'invitation : la ligue, ou None (essai faux noté : trop d'essais faux = refus pendant 15 min)."""
    keys = (("join", pid or "?"), JOIN_FAIL_MAX_JOUEUR), (("joinip", _ip(req)), JOIN_FAIL_MAX_IP)
    if _too_many_fails(*keys):
        raise HTTPException(429, "too_many_attempts")
    code = str(code or "").strip().upper()
    with db() as c:
        r = c.execute("SELECT * FROM leagues WHERE code=?", (code,)).fetchone() if _CODE_RE.match(code) else None
    if not r:
        _note_fail(*(k for k, _ in keys))
        raise HTTPException(404, "bad_code")
    return dict(r)


@app.get("/api/leagues/preview")
def api_league_preview(req: Request, code: str = "", token: str = ""):
    """Ce qu'on rejoint (lien d'invitation) : nom, nombre de membres, créateur. Sans compte aussi."""
    p = player_by_token(token)
    L = _code_essai(req, p and p["id"], code)
    with db() as c:
        n = c.execute("SELECT COUNT(*) FROM league_members WHERE league=?", (L["id"],)).fetchone()[0]
        own = c.execute("SELECT name FROM players WHERE id=?", (L["owner"],)).fetchone()
        mine = bool(p and c.execute("SELECT 1 FROM league_members WHERE league=? AND player=?", (L["id"], p["id"])).fetchone())
    return {"id": L["id"], "name": L["name"], "members": n, "max": LIGUE_MAX_MEMBRES, "owner": own[0] if own else None,
            "member": mine}


@app.post("/api/leagues/join")
async def api_league_join(req: Request):
    body = await _json(req)
    p = _compte(body.get("token"))
    L = _code_essai(req, p["id"], body.get("code"))
    with _db_lock, db() as c:
        if c.execute("SELECT 1 FROM league_members WHERE league=? AND player=?", (L["id"], p["id"])).fetchone():
            return {"league": _ligue_public(c, L, p["id"]), "already": True}
        if c.execute("SELECT COUNT(*) FROM league_members WHERE player=?", (p["id"],)).fetchone()[0] >= LIGUE_MAX_PAR_COMPTE:
            raise HTTPException(409, "too_many_leagues")
        if c.execute("SELECT COUNT(*) FROM league_members WHERE league=?", (L["id"],)).fetchone()[0] >= LIGUE_MAX_MEMBRES:
            raise HTTPException(409, "league_full")
        c.execute("INSERT INTO league_members(league, player, joined) VALUES(?,?,?)", (L["id"], p["id"], now_ms()))
        return {"league": _ligue_public(c, L, p["id"]), "already": False}


def _membre_ou_403(c, lid, pid):
    L = _ligue(c, lid)
    if not c.execute("SELECT 1 FROM league_members WHERE league=? AND player=?", (L["id"], pid)).fetchone():
        raise HTTPException(403, "not_a_member")
    return L


def _createur_ou_403(c, lid, pid):
    L = _membre_ou_403(c, lid, pid)
    if L["owner"] != pid:
        raise HTTPException(403, "owner_only")
    return L


@app.post("/api/leagues/leave")
async def api_league_leave(req: Request):
    body = await _json(req)
    p = _compte(body.get("token"))
    with _db_lock, db() as c:
        L = _membre_ou_403(c, body.get("league"), p["id"])
        c.execute("DELETE FROM league_members WHERE league=? AND player=?", (L["id"], p["id"]))
        rest = _membres(c, L["id"])
        if not rest:
            c.execute("DELETE FROM leagues WHERE id=?", (L["id"],))
        elif L["owner"] == p["id"]:
            c.execute("UPDATE leagues SET owner=? WHERE id=?", (rest[0]["id"], L["id"]))
    return {"ok": True}


@app.post("/api/leagues/rename")
async def api_league_rename(req: Request):
    body = await _json(req)
    p = _compte(body.get("token"))
    nom = _ligue_nom(body.get("name"))
    with _db_lock, db() as c:
        L = _createur_ou_403(c, body.get("league"), p["id"])
        c.execute("UPDATE leagues SET name=? WHERE id=?", (nom, L["id"]))
        return {"league": _ligue_public(c, _ligue(c, L["id"]), p["id"])}


@app.post("/api/leagues/code")
async def api_league_code(req: Request):
    """Nouveau code : l'ancien lien d'invitation ne marche plus (les membres restent)."""
    body = await _json(req)
    p = _compte(body.get("token"))
    with _db_lock, db() as c:
        L = _createur_ou_403(c, body.get("league"), p["id"])
        for _ in range(20):
            code = _ligue_code()
            if not c.execute("SELECT 1 FROM leagues WHERE code=?", (code,)).fetchone():
                break
        c.execute("UPDATE leagues SET code=? WHERE id=?", (code, L["id"]))
        return {"league": _ligue_public(c, _ligue(c, L["id"]), p["id"])}


@app.post("/api/leagues/kick")
async def api_league_kick(req: Request):
    body = await _json(req)
    p = _compte(body.get("token"))
    with _db_lock, db() as c:
        L = _createur_ou_403(c, body.get("league"), p["id"])
        m = str(body.get("member") or "")
        if m == p["id"]:
            raise HTTPException(400, "cannot_kick_self")
        c.execute("DELETE FROM league_members WHERE league=? AND player=?", (L["id"], m))
    return {"ok": True}


@app.post("/api/leagues/delete")
async def api_league_delete(req: Request):
    body = await _json(req)
    p = _compte(body.get("token"))
    with _db_lock, db() as c:
        L = _createur_ou_403(c, body.get("league"), p["id"])
        c.execute("DELETE FROM league_members WHERE league=?", (L["id"],))
        c.execute("DELETE FROM leagues WHERE id=?", (L["id"],))
    return {"ok": True}


def ligue_classement(lid, scope, t):
    """Classement d'une ligue : scope week (solde de la semaine en cours) ou season (gains nets cumulés, comme le
    classement général). Tous les membres y figurent ; ceux qui n'ont pas encore parié viennent après, sans rang."""
    with db() as c:
        L = _ligue(c, lid)
        membres = _membres(c, L["id"])
    rows = []
    if scope == "season":
        weeks = season_weeks(t)
        for m in membres:
            with db() as c:
                bets = [bet_row(r) for r in c.execute("SELECT * FROM bets WHERE player=?", (m["id"],))]
            a = _season_agg(bets, weeks, t)
            rows.append(dict(a, id=m["id"], name=m["name"], owner=m["id"] == L["owner"]))
        rows.sort(key=lambda r: (not r["bets"], -r["net"], -r["weeks"], r["name"].casefold()))
    else:
        w = _need_week()
        for m in membres:
            Lg = ledger(w, player_bets(m["id"], w), t)
            rows.append({"id": m["id"], "name": m["name"], "owner": m["id"] == L["owner"], "balance": Lg["balance"],
                         "bets": len(Lg["bets"]), "won": Lg["won"], "lost": Lg["lost"]})
        rows.sort(key=lambda r: (not r["bets"], -r["balance"], r["name"].casefold()))
    k = 0
    for r in rows:
        r["rank"] = (k := k + 1) if r["bets"] else None
    return L, rows


@app.get("/api/leagues/{lid}/standings")
def api_league_standings(lid: str, token: str = "", scope: str = "week"):
    p = _compte(token)
    with db() as c:
        L = _membre_ou_403(c, lid, p["id"])
        pub = _ligue_public(c, L, p["id"])
    t = now_ms()
    _, rows = ligue_classement(L["id"], "season" if scope == "season" else "week", t)
    for r in rows:
        r["me"] = r["id"] == p["id"]
    return {"league": pub, "scope": "season" if scope == "season" else "week", "rows": rows, "now": t}


# ------------------------------------------------------------------ chat (bloc 3 ; README sections 71 et 72)
# Salons : « general » (en direct) et un salon par match « m:<semaine>:<id> » (direct puis replay). Lecture libre, écriture
# réservée aux comptes. Interrupteur GC_CHAT : off (défaut : routes en 404, /api/delta et la page inchangés), read
# (lecture seule) ou on. Temps réel = interrogation courte : /api/delta porte le dernier numéro de General (badge des
# non-lus), le panneau ouvert lit /api/chat?room=…&after=… toutes les 3 s, servi par un tampon en mémoire (un seul
# processus uvicorn). Anti-spoiler : un message de salon de match porte « at », le nombre d'actions que l'auteur avait vues
# (borné au direct) ; un spectateur n'en voit que les messages où at ≤ sa position. Un score qui ne correspond pas à cette
# position, ou un mot de fin de match, renvoie le message au point le plus loin connu. Modération : filtre de mots
# (static/chat_filtre.txt), liens et coordonnées refusés, débit limité, signalements (masqué au 3e), masquage / bannissement
# par l'administrateur (GC_ADMIN_KEY, motif montré à l'auteur), purge après GC_CHAT_DAYS jours. Ni id interne, ni IP,
# ni e-mail dans une réponse : l'auteur est un identifiant opaque « a » (HMAC de l'id du joueur, clé tirée une fois).
# Les fonctions qui dépendent du temps prennent l'instant t (tests sans horloge).
import unicodedata
from collections import OrderedDict, deque

CHAT_MAX_LEN, CHAT_RAW_MAX = 280, 2000           # caractères d'un message (après nettoyage) ; au-delà, refusé sans lire
CHAT_GAP_MS, CHAT_PER_MIN, CHAT_PER_DAY = 3000, 10, 300
CHAT_DUP_MS = 2 * 60 * 1000                      # même message répété : refusé pendant 2 min
CHAT_IP_PER_MIN = 30                             # tous comptes d'une même adresse (garde-fou ; adresse jamais stockée)
CHAT_NEW_ACCOUNT_MS = 10 * 60 * 1000             # un compte de moins de 10 min n'écrit pas encore
CHAT_REPORTS_HIDE = 3                            # signalements de comptes différents : message masqué, à revoir
CHAT_REPORTS_PER_HOUR = 20
CHAT_BUF, CHAT_ROOMS_CACHE, CHAT_PAGE, CHAT_FIRST, CHAT_PENDING = 300, 32, 100, 50, 300   # pire cas ≈ 9 Mo
CHAT_PREGAME_MS = 30 * 60 * 1000                 # salon d'un match ouvert à l'écriture 30 min avant le coup d'envoi
CHAT_KEEP_ACTIONS_MS = 180 * 24 * 3600 * 1000    # signalements et décisions : 6 mois
CHAT_MAX_ROWS = 200_000                          # plafond dur : les plus anciens partent
CHAT_PURGE_EVERY_MS = 3600 * 1000
CHAT_RESERVED_PREFIX = ("admin", "snapline", "moderat")              # « Adm1nJoe », « Administrator », « Moderateur »
CHAT_RESERVED_WORDS = ("modo", "staff", "support", "official", "system", "team")   # mot entier seulement (« supporter » passe)
CHAT_REPORT_REASONS = ("spam", "abuse", "hate", "spoiler", "other")
CHAT_FILTRE = os.path.join(HERE, "static", "chat_filtre.txt")
_CHAT_ROOM_RE = re.compile(r"^m:(\d{4}-\d{2}-\d{2}):([A-Za-z0-9_-]{1,40})$")


def chat_mode():
    m = os.environ.get("GC_CHAT", "off").strip().lower()
    return m if m in ("read", "on") else "off"


def chat_days():
    try:
        return max(1, int(os.environ.get("GC_CHAT_DAYS", "30")))
    except ValueError:
        return 30


_CHAT_LOCK = threading.Lock()
_CHAT = {"init": False, "secret": None, "rooms": OrderedDict(), "rev": 0, "gone": deque(maxlen=1000),
         "rate": {}, "ip": {}, "dup": {}, "reports": {}, "purged": None}


def _chat_init():
    if _CHAT["init"]:
        return
    with _db_lock, db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS chat_messages(id INTEGER PRIMARY KEY AUTOINCREMENT, room TEXT, player TEXT, a TEXT,
            name TEXT, team TEXT, body TEXT, at INTEGER, teams TEXT, sc INTEGER, adm INTEGER, created INTEGER,
            hidden INTEGER DEFAULT 0, reason TEXT, reviewed INTEGER DEFAULT 0);
        CREATE INDEX IF NOT EXISTS chat_messages_room ON chat_messages(room, id);
        CREATE INDEX IF NOT EXISTS chat_messages_at ON chat_messages(room, at, id);
        CREATE INDEX IF NOT EXISTS chat_messages_a ON chat_messages(a, id);
        CREATE INDEX IF NOT EXISTS chat_messages_created ON chat_messages(created);
        CREATE TABLE IF NOT EXISTS chat_reports(msg INTEGER, reporter TEXT, reason TEXT, created INTEGER,
            PRIMARY KEY(msg, reporter));
        CREATE TABLE IF NOT EXISTS chat_bans(a TEXT PRIMARY KEY, player TEXT, until INTEGER, reason TEXT, created INTEGER);
        CREATE TABLE IF NOT EXISTS chat_actions(id INTEGER PRIMARY KEY AUTOINCREMENT, created INTEGER, action TEXT,
            msg INTEGER, a TEXT, body TEXT, reason TEXT);
        CREATE TABLE IF NOT EXISTS chat_meta(k TEXT PRIMARY KEY, v TEXT);
        """)
        r = c.execute("SELECT v FROM chat_meta WHERE k='secret'").fetchone()
        if r:
            sec = r[0]
        else:
            sec = secrets.token_hex(32)
            c.execute("INSERT INTO chat_meta(k, v) VALUES('secret', ?)", (sec,))
    _CHAT["secret"] = bytes.fromhex(sec)
    _CHAT["init"] = True


def chat_author(pid):
    """Identifiant public d'un auteur : opaque, stable, sans lien visible avec l'id interne."""
    _chat_init()
    return hmac.new(_CHAT["secret"], str(pid).encode(), hashlib.sha256).hexdigest()[:10]


# ---- texte : nettoyage, filtre de mots, liens, spoilers ----
_CHAT_DROP_CATS = ("Cc", "Cf", "Co", "Cs", "Cn", "Zl", "Zp")    # contrôle, format (sens d'écriture, largeur nulle)…
_LEET = str.maketrans({"0": "o", "1": "i", "!": "i", "|": "i", "3": "e", "4": "a", "@": "a", "5": "s", "$": "s",
                       "7": "t", "+": "t", "8": "b", "9": "g",
                       # sosies cyrilliques et grecs des lettres latines (« fuсk » avec un с cyrillique)
                       "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j",
                       "к": "k", "м": "m", "н": "h", "т": "t", "в": "b", "ѕ": "s", "ο": "o", "α": "a", "ε": "e",
                       "ι": "i", "κ": "k", "ν": "v", "ρ": "p", "τ": "t", "υ": "u", "χ": "x"})


def chat_clean(raw):
    """Texte d'un message : une ligne, sans caractère invisible ni de direction, au plus un signe diacritique par lettre
    (pas de « zalgo »), espaces réduits. Les émojis restent."""
    s = unicodedata.normalize("NFC", str(raw or "")[:CHAT_RAW_MAX])
    out, marks = [], 0
    for ch in s:
        cat = unicodedata.category(ch)
        if ch in "\t\r\n\u2028\u2029\x0b\x0c":
            out.append(" "); marks = 0
        elif cat in _CHAT_DROP_CATS:
            continue
        elif cat in ("Mn", "Me"):
            if marks < 1 or ch in "\ufe0e\ufe0f":
                out.append(ch)
            marks += 1
        else:
            out.append(ch); marks = 0
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _chat_norm(word):
    """Forme comparée par le filtre : sans accent, minuscules, chiffres « leet » et sosies ramenés aux lettres latines."""
    s = unicodedata.normalize("NFKD", word.casefold().translate(_LEET))
    return "".join(ch for ch in s if "a" <= ch <= "z")


def _chat_pattern(entry):
    """Entrée de la liste -> motif : chaque groupe de lettres veut au moins autant de lettres (« fuck » attrape
    « fuuuck », « ass » n'attrape pas « as ») ; « * » final = début de mot ; une expression = des mots qui se suivent."""
    pre = entry.endswith("*")
    words = [_chat_norm(x) for x in entry.rstrip("*").split()]
    if not all(words):
        return None
    pat = " ".join("".join(re.escape(m.group(1)) + ("+" if len(m.group(0)) == 1 else "{%d,}" % len(m.group(0)))
                           for m in re.finditer(r"(.)\1*", w)) for w in words)
    return pat + ("[a-z]*" if pre else ""), len(words) > 1


def _chat_load_filter():
    lists = {"[bloque]": ([], []), "[masque]": ([], [])}
    part = None
    try:
        with open(CHAT_FILTRE, encoding="utf-8") as fh:
            for line in fh:
                line = line.split("#", 1)[0].strip()
                if not line:
                    continue
                if line in lists:
                    part = lists[line]
                elif part is not None:
                    pp = _chat_pattern(line)
                    if pp:
                        part[1 if pp[1] else 0].append(pp[0])
    except OSError:
        pass

    def comp(words, phrases):
        return (re.compile("^(?:" + "|".join(words) + ")$") if words else None,
                re.compile("(?:^| )(?:" + "|".join(phrases) + ")(?: |$)") if phrases else None)
    return comp(*lists["[bloque]"]), comp(*lists["[masque]"])


_CHAT_FILTER = {"mtime": None, "lists": ((None, None), (None, None))}


def _chat_filter():
    try:
        m = os.path.getmtime(CHAT_FILTRE)
    except OSError:
        m = None
    if _CHAT_FILTER["mtime"] != m:
        _CHAT_FILTER.update(mtime=m, lists=_chat_load_filter())
    return _CHAT_FILTER["lists"]


def _chat_hit(norm, lst):
    return bool(norm) and lst[0] is not None and lst[0].match(norm) is not None


_CHAT_TOKEN_RE = re.compile(r"[\w@$]+(?:[!|+][\w@$]+)*", re.UNICODE)    # « sh!t » est un mot, « shit! » aussi
# lettres isolées séparées par des espaces, points, tirets… (« f u c k », « f.u.c.k ») : lues comme un seul mot
_CHAT_SPACED_RE = re.compile(r"(?<!\w)(?:[\w@$][\s.*_\-]+){2,}[\w@$](?!\w)", re.UNICODE)


def chat_filter(text):
    """(texte, masqué) ; HTTPException 400 « message_blocked » pour un mot de la liste dure. Les mots de la liste
    « masque » deviennent des astérisques (un par lettre, au plus 6)."""
    hard, soft = _chat_filter()
    masked = False

    def check(m):
        nonlocal masked
        n = _chat_norm(m.group(0))
        if _chat_hit(n, hard):
            raise HTTPException(400, "message_blocked")
        if _chat_hit(n, soft):
            masked = True
            return "*" * min(6, max(3, len(m.group(0).strip())))
        return m.group(0)

    words = " ".join(filter(None, (_chat_norm(m.group(0)) for m in _CHAT_TOKEN_RE.finditer(text))))
    if hard[1] is not None and hard[1].search(words):
        raise HTTPException(400, "message_blocked")
    text = _CHAT_SPACED_RE.sub(lambda m: check(m) if len(_chat_norm(m.group(0))) >= 3 else m.group(0), text)
    text = _CHAT_TOKEN_RE.sub(check, text)
    return text, masked


_CHAT_TLDS = ("com|net|org|io|gg|co|me|ly|tv|xyz|ru|fr|be|de|uk|us|info|biz|app|link|site|online|shop|store|club|top|"
              "tk|ml|ga|cf|gq|pw|cc|to|in|eu|nl|es|it|pl|ch|ca|au|br|cn|jp|kr|vip|win|bet|casino|porn|sex|news|fun|"
              "click|pro|live|ai|dev|lol|art|one|life|world|online|space|website|page|ws|su|ua|tr|id|ph|vn|lt|lv|ee")
_CHAT_LINK_RE = re.compile(r"(?i)(?:\bhttps?://\S+|\bwww\.\S+|\b[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.(?:" + _CHAT_TLDS
                           + r")\b(?:/\S*)?)")
_CHAT_OK_LINK_RE = re.compile(r"(?i)^(?:https?://)?(?:www\.)?snapline\.live(?:/\S*)?$")
_CHAT_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_CHAT_PHONE_RE = re.compile(r"(?:\+?\d[\s.\-()]*){9,}")


def chat_links(text):
    """Pas de lien (sauf snapline.live), ni d'adresse e-mail ou de numéro de téléphone (spam, données personnelles)."""
    if _CHAT_EMAIL_RE.search(text) or _CHAT_PHONE_RE.search(text):
        raise HTTPException(400, "contact_not_allowed")
    for m in _CHAT_LINK_RE.finditer(text):
        if not _CHAT_OK_LINK_RE.match(m.group(0).rstrip(".,;:!?)")):
            raise HTTPException(400, "links_not_allowed")


_CHAT_SCORE_RE = re.compile(r"(?<![\d:.])(\d{1,2})\s*(?:[-–—:]|\bto\b)\s*(\d{1,2})(?![\d:.])", re.IGNORECASE)
_CHAT_END_RE = re.compile(r"(?i)\b(?:won|wins?|winner|beat|beats|beaten|lost|loses?|loser|final|full[\s-]?time|"
                          r"comeback|blowout|overtime|ot|champions?|walk[\s-]?off|game over)\b")


def chat_scores(text):
    return [(int(a), int(b)) for a, b in _CHAT_SCORE_RE.findall(text)]


def chat_spoilery(text):
    """Un message qui ressemble à un score ou à une fin de match."""
    return bool(chat_scores(text) or _CHAT_END_RE.search(text))


def _chat_team_words(w):
    """Mots qui désignent une équipe : abréviation (majuscules exactes), nom complet, ville et surnom (4 lettres et plus)."""
    out = []
    for abbr, T in (w.doc.get("teams") or {}).items():
        name = str(T.get("name") or "")
        words = {name.casefold()} | {x.casefold() for x in name.split() if len(x) >= 4}
        out.append((abbr, words))
    return out


def chat_teams(text, w):
    if w is None:
        return []
    low = {x.casefold() for x in re.findall(r"[^\W\d_]+", text)}
    full = text.casefold()
    found = []
    for abbr, words in _chat_team_words(w):
        if re.search(r"(?<![A-Za-z])" + re.escape(abbr) + r"(?![A-Za-z])", text) or \
                any((x in full) if " " in x else (x in low) for x in words):
            found.append(abbr)
    return found[:4]


def _chat_score_at(w, g, k):
    """Score (domicile, extérieur) après k actions."""
    if k <= 0:
        return (0, 0)
    plays = w.feed(g["id"])["plays"]
    sc = ((plays[min(k, len(plays)) - 1].get("after") or {}).get("score")) or {}
    return (int(sc.get("home") or 0), int(sc.get("away") or 0))


def chat_at(w, g, at, text, t):
    """Position d'un message dans un salon de match : ce que l'auteur dit avoir vu, borné au direct ; un score qui n'est
    pas celui de cette position, ou un mot de fin de match, renvoie le message au point le plus loin connu."""
    far = w.revealed_plays(g, t) if w.teams_known(g, t) else 0
    try:
        k = int(at)
    except (TypeError, ValueError):
        k = far
    k = max(0, min(k, far))
    if k < far:
        sc = _chat_score_at(w, g, k)
        if _CHAT_END_RE.search(text) or any(sorted(p) != sorted(sc) for p in chat_scores(text)):
            k = far
    return k


# ---- salons ----
def chat_room(room, t=None):
    """(semaine, match) d'un salon ; (None, None) pour General ; HTTPException 404 si le salon n'existe pas."""
    room = str(room or "")
    if room == "general":
        return None, None
    m = _CHAT_ROOM_RE.match(room)
    w = load_weeks().get(m.group(1)) if m else None
    if not w or m.group(2) not in w.by:
        raise HTTPException(404, "room_not_found")
    return w, w.by[m.group(2)]


def _chat_pub(r):
    """Message public (aucun id interne, aucune adresse)."""
    d = {"id": r["id"], "a": r["a"], "n": r["name"], "b": r["body"], "ts": r["created"]}
    if r["team"]:
        d["t"] = r["team"]
    if r["room"] != "general":
        d["at"] = r["at"] or 0
    if r["sc"]:
        d["sc"] = 1
    if r["teams"]:
        d["teams"] = r["teams"].split(",")
    if r["adm"]:
        d["adm"] = 1
    return d


def _chat_buf(room):
    """Tampon des derniers messages visibles d'un salon (chargé à la demande, CHAT_ROOMS_CACHE salons au plus)."""
    rooms = _CHAT["rooms"]
    b = rooms.get(room)
    if b is not None:
        rooms.move_to_end(room)
        return b
    with db() as c:
        rows = c.execute("SELECT * FROM chat_messages WHERE room=? AND hidden=0 ORDER BY id DESC LIMIT ?",
                         (room, CHAT_BUF + 1)).fetchall()
    b = {"msgs": [_chat_pub(r) for r in reversed(rows[:CHAT_BUF])], "all": len(rows) <= CHAT_BUF}
    rooms[room] = b
    while len(rooms) > CHAT_ROOMS_CACHE:
        rooms.popitem(last=False)
    return b


def _chat_gone(room, mid):
    """Message retiré (masqué, supprimé) : les navigateurs le retirent au prochain appel."""
    _CHAT["rev"] += 1
    _CHAT["gone"].append((_CHAT["rev"], room, mid))
    b = _CHAT["rooms"].get(room)
    if b is not None:
        b["msgs"] = [m for m in b["msgs"] if m["id"] != mid]


def chat_last(room="general"):
    with _CHAT_LOCK:
        _chat_init()
        b = _chat_buf(room)
        return b["msgs"][-1]["id"] if b["msgs"] else 0


def chat_read(room, after=0, upto=None, rev=None, t=None):
    """Messages d'un salon. after = 0 : premier chargement (les derniers ; dans un salon de match, ceux que la position
    upto laisse voir, plus ceux d'après, « pending », que la page montre quand le spectateur y arrive). after > 0 : les
    messages arrivés depuis (toutes positions). rev : retraits (masqués, supprimés) depuis ce numéro."""
    t = now_ms() if t is None else t
    w, g = chat_room(room, t)
    _chat_init()
    out = {"room": room, "msgs": []}
    with _CHAT_LOCK:
        _chat_maybe_purge(t)
        b = _chat_buf(room)
        last = b["msgs"][-1]["id"] if b["msgs"] else 0
        if after > 0 and (b["all"] or (b["msgs"] and b["msgs"][0]["id"] <= after + 1)):
            new = [m for m in b["msgs"] if m["id"] > after]
            out["msgs"], out["more"] = new[:CHAT_PAGE], len(new) > CHAT_PAGE
            after = -1                                   # servi par le tampon
        cur, gone = _CHAT["rev"], list(_CHAT["gone"])
    if after > 0:                                        # très en retard : lu dans la base
        with db() as c:
            rows = c.execute("SELECT * FROM chat_messages WHERE room=? AND hidden=0 AND id>? ORDER BY id LIMIT ?",
                             (room, after, CHAT_PAGE + 1)).fetchall()
        out["msgs"], out["more"] = [_chat_pub(r) for r in rows[:CHAT_PAGE]], len(rows) > CHAT_PAGE
    elif after == 0:
        with db() as c:
            if g is None or upto is None:
                rows = c.execute("SELECT * FROM chat_messages WHERE room=? AND hidden=0 AND id<=? ORDER BY id DESC LIMIT ?",
                                 (room, last, CHAT_FIRST)).fetchall()
                out["msgs"] = [_chat_pub(r) for r in reversed(rows)]
            else:
                k = max(0, int(upto))
                rows = c.execute("SELECT * FROM chat_messages WHERE room=? AND hidden=0 AND id<=? AND at<=? "
                                 "ORDER BY at DESC, id DESC LIMIT ?", (room, last, k, CHAT_FIRST)).fetchall()
                out["msgs"] = [_chat_pub(r) for r in reversed(rows)]
                pend = c.execute("SELECT * FROM chat_messages WHERE room=? AND hidden=0 AND id<=? AND at>? "
                                 "ORDER BY at, id LIMIT ?", (room, last, k, CHAT_PENDING + 1)).fetchall()
                out["pending"] = [_chat_pub(r) for r in pend[:CHAT_PENDING]]
                out["pend_more"] = len(pend) > CHAT_PENDING      # la page relira à sa position plus tard
    out["last"] = max([last] + [m["id"] for m in out["msgs"]])
    out["rev"] = cur
    if rev is not None and rev >= 0:
        if gone and rev < gone[0][0] - 1 and len(gone) == _CHAT["gone"].maxlen:
            out["reset"] = True                          # trop de retraits manqués : la page recharge le salon
        out["gone"] = [mid for (n, r, mid) in gone if n > rev and r == room]
    if g is not None:
        out["far"] = w.revealed_plays(g, t) if w.teams_known(g, t) else 0
    return out


# ---- écrire ----
def _chat_ban(c, a, t):
    r = c.execute("SELECT * FROM chat_bans WHERE a=?", (a,)).fetchone()
    if r and (r["until"] == 0 or r["until"] > t):
        return {"until": r["until"] or None, "reason": r["reason"]}
    return None


def chat_why_not(p, t):
    """Pourquoi ce joueur ne peut pas écrire (code), ou None."""
    if chat_mode() != "on":
        return "chat_read_only"
    if not p or not p.get("login"):
        return "account_required"
    if p.get("acct_at") and t - p["acct_at"] < CHAT_NEW_ACCOUNT_MS:
        return "account_too_new"
    if chat_reserved(p.get("name")):
        return "pseudo_reserved"
    with db() as c:
        if _chat_ban(c, chat_author(p["id"]), t):
            return "banned"
    return None


def chat_reserved(name):
    """Pseudo qui pourrait passer pour l'équipe du site (mots coupés aux majuscules : « SnaplineTeam », « Adm1n_Joe »)."""
    words = re.split(r"[\W_]+", re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(name or "")))
    whole = _chat_norm(str(name or ""))
    if "snapline" in whole:
        return True
    for x in filter(None, (_chat_norm(w) for w in words)):
        if x.startswith(CHAT_RESERVED_PREFIX) or x in CHAT_RESERVED_WORDS:
            return True
    return False


def _chat_rate(pid, ip, norm, t):
    """Débit : 1 message toutes les 3 s, 10 par minute, 300 par jour, le même message pas deux fois en 2 min,
    30 par minute depuis une même adresse."""
    ts = _CHAT["rate"].setdefault(pid, deque(maxlen=CHAT_PER_DAY))
    while ts and t - ts[0] >= 24 * 3600 * 1000:
        ts.popleft()
    if ts and t - ts[-1] < CHAT_GAP_MS:
        raise HTTPException(429, "too_fast")
    if sum(1 for x in ts if t - x < 60_000) >= CHAT_PER_MIN or len(ts) >= CHAT_PER_DAY:
        raise HTTPException(429, "too_many")
    dup = _CHAT["dup"].get(pid)
    if dup and dup[1] == norm and t - dup[0] < CHAT_DUP_MS:
        raise HTTPException(429, "duplicate")
    if ip:
        q = _CHAT["ip"].setdefault(ip, deque(maxlen=CHAT_IP_PER_MIN))
        if len(q) >= CHAT_IP_PER_MIN and t - q[0] < 60_000:
            raise HTTPException(429, "too_many")
        q.append(t)
        if len(_CHAT["ip"]) > 5000:
            _CHAT["ip"].clear()
    ts.append(t)
    _CHAT["dup"][pid] = (t, norm)


def chat_post(p, room, body, at=None, ip=None, t=None):
    """Nouveau message ; renvoie {"msg": public, "masked": bool}. Codes d'erreur (la page les traduit) : chat_read_only,
    account_required, account_too_new, pseudo_reserved, banned, room_not_found, room_closed, empty, too_long,
    message_blocked, links_not_allowed, contact_not_allowed, too_fast, too_many, duplicate."""
    t = now_ms() if t is None else t
    _chat_init()
    why = chat_why_not(p, t)
    if why:
        raise HTTPException(403, why)
    w, g = chat_room(room, t)
    if g is not None and not (w.teams_known(g, t) and t >= g["ko"] - CHAT_PREGAME_MS):
        raise HTTPException(403, "room_closed")
    text = chat_clean(body)
    if not text:
        raise HTTPException(400, "empty")
    if len(text) > CHAT_MAX_LEN:
        raise HTTPException(400, "too_long")
    chat_links(text)
    text, masked = chat_filter(text)
    sc = chat_spoilery(text)
    teams = chat_teams(text, w or current_week(t))
    k = chat_at(w, g, at, text, t) if g is not None else 0
    a = chat_author(p["id"])
    with _CHAT_LOCK:
        _chat_rate(p["id"], ip, re.sub(r"[\W_]+", "", text.casefold()) or text, t)
        with _db_lock, db() as c:
            cur = c.execute("INSERT INTO chat_messages(room, player, a, name, team, body, at, teams, sc, adm, created) "
                            "VALUES(?,?,?,?,?,?,?,?,?,0,?)", (room, p["id"], a, p["name"], p.get("fav_team"), text, k,
                                                              ",".join(teams) or None, 1 if sc else 0, t))
            r = c.execute("SELECT * FROM chat_messages WHERE id=?", (cur.lastrowid,)).fetchone()
        msg = _chat_pub(r)
        b = _chat_buf(room)
        if not b["msgs"] or b["msgs"][-1]["id"] < msg["id"]:
            b["msgs"].append(msg)
        if len(b["msgs"]) > CHAT_BUF:
            del b["msgs"][:-CHAT_BUF]
            b["all"] = False
    return {"msg": msg, "masked": masked}


def chat_delete(p, mid, t=None):
    """L'auteur efface son message (et ses signalements) : il disparaît partout."""
    with _CHAT_LOCK, _db_lock, db() as c:
        r = c.execute("SELECT room, player FROM chat_messages WHERE id=?", (int(mid),)).fetchone()
        if not r or r["player"] != p["id"]:
            raise HTTPException(404, "message_not_found")
        c.execute("DELETE FROM chat_messages WHERE id=?", (int(mid),))
        c.execute("DELETE FROM chat_reports WHERE msg=?", (int(mid),))
        _chat_gone(r["room"], int(mid))
    return {"ok": True}


def chat_report(p, mid, reason, t=None):
    """Signalement (comptes ; un par compte et par message). Au CHAT_REPORTS_HIDE-ième de comptes différents, le message
    est masqué en attendant l'administrateur (sauf s'il l'a déjà revu et laissé)."""
    t = now_ms() if t is None else t
    if not p or not p.get("login"):
        raise HTTPException(403, "account_required")
    reason = reason if reason in CHAT_REPORT_REASONS else "other"
    with _CHAT_LOCK:
        q = _CHAT["reports"].setdefault(p["id"], deque(maxlen=CHAT_REPORTS_PER_HOUR))
        if len(q) >= CHAT_REPORTS_PER_HOUR and t - q[0] < 3600 * 1000:
            raise HTTPException(429, "too_many")
        with _db_lock, db() as c:
            r = c.execute("SELECT * FROM chat_messages WHERE id=?", (int(mid),)).fetchone()
            if not r:
                raise HTTPException(404, "message_not_found")
            if r["player"] == p["id"]:
                raise HTTPException(400, "own_message")
            new = c.execute("INSERT OR IGNORE INTO chat_reports(msg, reporter, reason, created) VALUES(?,?,?,?)",
                            (r["id"], p["id"], reason, t)).rowcount
            n = c.execute("SELECT COUNT(*) FROM chat_reports WHERE msg=?", (r["id"],)).fetchone()[0]
            hidden = bool(r["hidden"])
            if new and not hidden and not r["reviewed"] and n >= CHAT_REPORTS_HIDE:
                why = "Hidden after several reports, pending review"
                c.execute("UPDATE chat_messages SET hidden=1, reason=? WHERE id=?", (why, r["id"]))
                c.execute("INSERT INTO chat_actions(created, action, msg, a, body, reason) VALUES(?,?,?,?,?,?)",
                          (t, "auto_hide", r["id"], r["a"], r["body"], why))
                _chat_gone(r["room"], r["id"])
                hidden = True
        if new:
            q.append(t)
    return {"ok": True, "hidden": hidden}


def chat_status(p, t=None):
    """Ce que la page doit savoir pour ce joueur : son identifiant public (pour « mes messages »), s'il peut écrire
    (et sinon pourquoi), un bannissement en cours et ses messages masqués par la modération, avec le motif."""
    t = now_ms() if t is None else t
    _chat_init()
    out = {"mode": chat_mode(), "max_len": CHAT_MAX_LEN, "a": None, "can_write": False, "why": None, "ban": None,
           "notices": []}
    out["why"] = chat_why_not(p, t)
    out["can_write"] = out["why"] is None
    if p:
        a = out["a"] = chat_author(p["id"])
        with db() as c:
            out["ban"] = _chat_ban(c, a, t)
            out["notices"] = [{"id": r["id"], "room": r["room"], "b": r["body"], "reason": r["reason"], "ts": r["created"]}
                              for r in c.execute("SELECT * FROM chat_messages WHERE a=? AND hidden=1 ORDER BY id DESC "
                                                 "LIMIT 10", (a,))]
    return out


# ---- conservation ----
def chat_purge(t=None):
    """Messages : GC_CHAT_DAYS jours (30 par défaut), CHAT_MAX_ROWS au plus ; signalements et décisions : 6 mois ;
    bannissements temporaires finis : retirés."""
    t = now_ms() if t is None else t
    _chat_init()
    lim = t - chat_days() * 24 * 3600 * 1000
    with _db_lock, db() as c:
        n = c.execute("DELETE FROM chat_messages WHERE created<?", (lim,)).rowcount
        over = c.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0] - CHAT_MAX_ROWS
        if over > 0:
            n += c.execute("DELETE FROM chat_messages WHERE id IN (SELECT id FROM chat_messages ORDER BY id LIMIT ?)",
                           (over,)).rowcount
        c.execute("DELETE FROM chat_reports WHERE created<?", (t - CHAT_KEEP_ACTIONS_MS,))
        c.execute("DELETE FROM chat_actions WHERE created<?", (t - CHAT_KEEP_ACTIONS_MS,))
        c.execute("DELETE FROM chat_bans WHERE until>0 AND until<=?", (t,))
    _CHAT["rooms"].clear()
    # compteurs de débit en mémoire : seulement ceux qui comptent encore (sinon un par auteur, pour toujours)
    for k, keep in (("rate", 24 * 3600 * 1000), ("ip", 60_000), ("reports", 3600 * 1000)):
        for x in [x for x, q in _CHAT[k].items() if not q or t - q[-1] >= keep]:
            del _CHAT[k][x]
    for x in [x for x, d in _CHAT["dup"].items() if t - d[0] >= CHAT_DUP_MS]:
        del _CHAT["dup"][x]
    _CHAT["purged"] = t
    return n


def _chat_maybe_purge(t):
    if _CHAT["purged"] is None or t - _CHAT["purged"] >= CHAT_PURGE_EVERY_MS:
        _CHAT["purged"] = t
        try:
            chat_purge(t)
        except Exception as e:                       # la lecture ne doit pas tomber pour une purge ratée
            print("purge du chat :", e)


# ---- administration (GC_ADMIN_KEY) ----
def _chat_admin(req, body):
    ip = _ip(req)
    if _too_many_fails((("admin-chat", ip), 10)):
        raise HTTPException(429, "too_many")
    admin = os.environ.get("GC_ADMIN_KEY", "")
    if len(admin) < 16 or not secrets.compare_digest(str(body.get("key") or ""), admin):
        _note_fail(("admin-chat", ip))
        raise HTTPException(403, "forbidden")
    _chat_init()


def _chat_admin_row(c, r):
    d = _chat_pub(r)
    d.update(room=r["room"], hidden=bool(r["hidden"]), reason=r["reason"], reviewed=bool(r["reviewed"]))
    d["reports"] = {x["reason"]: x["n"] for x in c.execute(
        "SELECT reason, COUNT(*) n FROM chat_reports WHERE msg=? GROUP BY reason", (r["id"],))}
    return d


def chat_admin_reports():
    with db() as c:
        rows = c.execute("SELECT m.* FROM chat_messages m WHERE m.reviewed=0 AND (m.hidden=1 OR EXISTS "
                         "(SELECT 1 FROM chat_reports r WHERE r.msg=m.id)) ORDER BY m.id DESC LIMIT 200").fetchall()
        bans = [dict(r) for r in c.execute("SELECT a, until, reason, created FROM chat_bans ORDER BY created DESC")]
        return {"reports": [_chat_admin_row(c, r) for r in rows], "bans": bans}


def chat_admin_author(a):
    with db() as c:
        rows = c.execute("SELECT * FROM chat_messages WHERE a=? ORDER BY id DESC LIMIT 100", (str(a),)).fetchall()
        ban = c.execute("SELECT a, until, reason, created FROM chat_bans WHERE a=?", (str(a),)).fetchone()
        return {"a": a, "messages": [_chat_admin_row(c, r) for r in rows], "ban": dict(ban) if ban else None}


def chat_admin_hide(mid, hide, reason, t=None):
    t = now_ms() if t is None else t
    reason = str(reason or "").strip()[:200] or ("Breaks the chat rules" if hide else None)
    with _CHAT_LOCK, _db_lock, db() as c:
        r = c.execute("SELECT * FROM chat_messages WHERE id=?", (int(mid),)).fetchone()
        if not r:
            raise HTTPException(404, "message_not_found")
        c.execute("UPDATE chat_messages SET hidden=?, reason=?, reviewed=1 WHERE id=?", (1 if hide else 0, reason, r["id"]))
        c.execute("INSERT INTO chat_actions(created, action, msg, a, body, reason) VALUES(?,?,?,?,?,?)",
                  (t, "hide" if hide else "unhide", r["id"], r["a"], r["body"], reason))
        if hide:
            _chat_gone(r["room"], r["id"])
        else:
            _CHAT["rooms"].pop(r["room"], None)      # rechargé : le message revient à sa place
    return {"ok": True}


def chat_admin_ban(a, days, reason, t=None):
    """Bannit un auteur (days = 0 : définitif) et masque ses messages des dernières 24 h."""
    t = now_ms() if t is None else t
    a = str(a or "")
    reason = str(reason or "").strip()[:200] or "Breaks the chat rules"
    try:
        days = max(0, int(days))
    except (TypeError, ValueError):
        raise HTTPException(400, "bad_days")
    until = 0 if days == 0 else t + days * 24 * 3600 * 1000
    with _CHAT_LOCK, _db_lock, db() as c:
        r = c.execute("SELECT player FROM chat_messages WHERE a=? LIMIT 1", (a,)).fetchone()
        if not r:
            raise HTTPException(404, "author_not_found")
        c.execute("INSERT OR REPLACE INTO chat_bans(a, player, until, reason, created) VALUES(?,?,?,?,?)",
                  (a, r["player"], until, reason, t))
        c.execute("INSERT INTO chat_actions(created, action, msg, a, body, reason) VALUES(?,?,?,?,?,?)",
                  (t, "ban" if days == 0 else f"ban_{days}d", None, a, None, reason))
        for m in c.execute("SELECT id, room FROM chat_messages WHERE a=? AND hidden=0 AND created>=?",
                           (a, t - 24 * 3600 * 1000)).fetchall():
            c.execute("UPDATE chat_messages SET hidden=1, reason=?, reviewed=1 WHERE id=?", (reason, m["id"]))
            _chat_gone(m["room"], m["id"])
    return {"ok": True, "until": until or None}


def chat_admin_unban(a, t=None):
    t = now_ms() if t is None else t
    with _db_lock, db() as c:
        c.execute("DELETE FROM chat_bans WHERE a=?", (str(a or ""),))
        c.execute("INSERT INTO chat_actions(created, action, msg, a, body, reason) VALUES(?,?,?,?,?,?)",
                  (t, "unban", None, str(a or ""), None, None))
    return {"ok": True}


def chat_admin_post(room, body, t=None):
    """Message de l'équipe (« Snapline », badge) : annonces, rappel des règles. Ni filtre ni débit."""
    t = now_ms() if t is None else t
    chat_room(room, t)
    text = chat_clean(body)
    if not text or len(text) > CHAT_MAX_LEN:
        raise HTTPException(400, "too_long" if text else "empty")
    with _CHAT_LOCK:
        with _db_lock, db() as c:
            cur = c.execute("INSERT INTO chat_messages(room, player, a, name, team, body, at, teams, sc, adm, created) "
                            "VALUES(?,?,?,?,?,?,?,?,?,1,?)", (room, "", "snapline", "Snapline", None, text, 0, None, 0, t))
            r = c.execute("SELECT * FROM chat_messages WHERE id=?", (cur.lastrowid,)).fetchone()
        msg = _chat_pub(r)
        b = _chat_buf(room)
        b["msgs"].append(msg)
        del b["msgs"][:-CHAT_BUF]
    return {"msg": msg}


# ---- routes ----
def _chat_on():
    if chat_mode() == "off":
        raise HTTPException(404, "chat_off")


async def _chat_body(req):
    """Corps JSON obligatoire (un formulaire d'un autre site ne peut pas l'envoyer : pas de CSRF possible)."""
    ct = str((req.headers.get("content-type") if hasattr(req.headers, "get") else "") or "application/json")
    if not ct.lower().startswith("application/json"):
        raise HTTPException(415, "json_required")
    return await _json(req)


@app.get("/api/chat")
def api_chat(room: str = "general", after: int = 0, upto: int = -1, rev: int = -1):
    """Messages d'un salon (lecture libre). upto : position du spectateur dans un salon de match (-1 : le direct)."""
    _chat_on()
    return chat_read(room, max(0, after), None if upto < 0 else upto, rev)


@app.post("/api/chat/status")
async def api_chat_status(req: Request):
    _chat_on()
    body = await _chat_body(req)
    return chat_status(player_by_token(body.get("token")))


@app.post("/api/chat/post")
async def api_chat_post(req: Request):
    _chat_on()
    body = await _chat_body(req)
    p = player_by_token(body.get("token"))
    if not p:
        raise HTTPException(403, "account_required")
    return chat_post(p, body.get("room"), body.get("body"), body.get("at"), _ip(req))


@app.post("/api/chat/delete")
async def api_chat_delete(req: Request):
    _chat_on()
    body = await _chat_body(req)
    p = player_by_token(body.get("token"))
    if not p:
        raise HTTPException(403, "account_required")
    try:
        return chat_delete(p, int(body.get("id")))
    except (TypeError, ValueError):
        raise HTTPException(404, "message_not_found")


@app.post("/api/chat/report")
async def api_chat_report(req: Request):
    _chat_on()
    body = await _chat_body(req)
    try:
        mid = int(body.get("id"))
    except (TypeError, ValueError):
        raise HTTPException(404, "message_not_found")
    return chat_report(player_by_token(body.get("token")), mid, body.get("reason"))


@app.post("/api/admin/chat")
async def api_admin_chat(req: Request):
    """Modération (GC_ADMIN_KEY ; marche aussi chat coupé). {key, action, …} : reports · author {a} · hide {id, reason}
    · unhide {id} · ban {a, days (0 = définitif), reason} · unban {a} · post {room, body} · purge."""
    body = await _chat_body(req)
    _chat_admin(req, body)
    act = body.get("action")
    try:
        if act == "reports":
            return chat_admin_reports()
        if act == "author":
            return chat_admin_author(body.get("a"))
        if act in ("hide", "unhide"):
            return chat_admin_hide(int(body.get("id")), act == "hide", body.get("reason"))
        if act == "ban":
            return chat_admin_ban(body.get("a"), body.get("days", 0), body.get("reason"))
        if act == "unban":
            return chat_admin_unban(body.get("a"))
        if act == "post":
            return chat_admin_post(body.get("room") or "general", body.get("body"))
        if act == "purge":
            return {"deleted": chat_purge()}
    except (TypeError, ValueError):
        raise HTTPException(400, "bad_request")
    raise HTTPException(400, "unknown_action")


@app.get("/admin/chat", response_class=HTMLResponse)
def admin_chat_page():
    """Page de modération (en français : pour l'administrateur). La clé est tapée dans la page, jamais dans l'adresse."""
    _chat_on()
    with open(os.path.join(HERE, "static", "admin_chat.html"), encoding="utf-8") as fh:
        return HTMLResponse(fh.read(), headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow",
                                                "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY"})


# ------------------------------------------------------------------ Insights (README section 78)
# Statistiques de la semaine en cours, calculées sur les seuls matchs terminés (moteur/insights.py), gardées tant
# qu'aucun nouveau match ne se termine. Le récap du jour est ouvert à tous ; « This week » et « Head-to-head » aux
# comptes de GC_INSIGHTS_USERS (pseudos séparés par des virgules) : les autres reçoivent seulement le récap, l'aperçu
# du site est dessiné avec des chiffres factices. GC_INSIGHTS=off : ni onglet ni API (le site d'avant).
_INS_CACHE, _INS_LOCK = {}, threading.Lock()


def insights_on():
    return os.environ.get("GC_INSIGHTS", "on").strip().lower() not in ("off", "0", "non", "no")


def insights_pro(p):
    """Le compte p a-t-il tout l'onglet ? (pseudo dans GC_INSIGHTS_USERS ; un invité, jamais)"""
    if not p or not p.get("login"):
        return False
    noms = {login_key(x) for x in os.environ.get("GC_INSIGHTS_USERS", "").split(",") if x.strip()}
    return p["login"] in noms


def insights_data(w, t):
    """Les statistiques de la semaine w à l'instant t (matchs terminés seulement), en cache par nombre de matchs finis."""
    finis = sorted((g for g in w.sched if w.status(g, t) == "final" and g.get("result")), key=lambda g: (g["ko"], g["id"]))
    cle = (w.start, len(finis))
    with _INS_LOCK:
        d = _INS_CACHE.get(cle)
        if d is None:
            d = _insights.calculer([(g, w.feed(g["id"])) for g in finis])
            _INS_CACHE.clear(); _INS_CACHE[cle] = d
    return d, len(finis)


@app.get("/api/insights")
def api_insights(token: str = ""):
    if not insights_on():
        raise HTTPException(404, "insights_off")
    w = _need_week(); t = now_ms()
    d, n = insights_data(w, t)
    pro = insights_pro(player_by_token(token) if token else None)
    out = {"week": w.start, "now": t, "final": n, "games": len(w.sched), "pro": pro, "recaps": d["recaps"]}
    if pro:
        out.update(league=d["league"], rows=d["rows"], hints=d["hints"])
    return JSONResponse(out, headers={"Cache-Control": "no-store"})


_TEAM_INS = re.compile(r"^[A-Z]{2,4}$")


def insights_roster(w, team):
    """Le roster d'avant-match d'une franchise cette semaine (son premier match : rien de joué)."""
    for g in sorted(w.reg, key=lambda g: (g["ko"], g["id"])):
        for side in ("home", "away"):
            if g.get(side) == team:
                tm = (w.feed(g["id"]).get("game") or {}).get(side)
                return tm.get("roster") if isinstance(tm, dict) else None
    return None


@app.get("/api/insights/h2h")
def api_insights_h2h(a: str = "", b: str = "", token: str = ""):
    """Face-à-face (comptes de GC_INSIGHTS_USERS) : toutes leurs confrontations terminées depuis la semaine
    HIST_DEPUIS (comme History), et les joueurs en forme / clés en méforme de chaque franchise cette semaine."""
    if not insights_on():
        raise HTTPException(404, "insights_off")
    if not insights_pro(player_by_token(token) if token else None):
        raise HTTPException(403, "insights_locked")
    w = _need_week(); t = now_ms()
    if not (_TEAM_INS.match(a) and _TEAM_INS.match(b)) or a == b or a not in w.doc["teams"] or b not in w.doc["teams"]:
        raise HTTPException(400, "bad_teams")
    ws = [x for x in sorted(load_weeks().values(), key=lambda x: x.monday)
          if x.open <= t and x.monday <= w.monday and x.doc["week"]["index"] >= HIST_DEPUIS]
    sem = [(x.doc["week"]["index"], [g for g in x.sched if x.status(g, t) == "final" and x.teams_known(g, t)]) for x in ws]
    return JSONResponse({"a": a, "b": b, "meetings": _insights.confrontations(sem, a, b),
                         "players": {k: _insights.joueurs(insights_roster(w, k)) for k in (a, b)}},
                        headers={"Cache-Control": "no-store"})


@app.get("/api/health")
def api_health():
    w = current_week()
    return {"ok": w is not None, "now": now_ms(), "week": w.start if w else None, "weeks": sorted(load_weeks())}


@app.get("/api/backup")
def api_backup(key: str = ""):
    """Sauvegarde complète (base des paris + semaines) en .zip. Protégée par la variable GC_ADMIN_KEY :
    sans elle, la sauvegarde est désactivée. Usage : https://<site>/api/backup?key=<GC_ADMIN_KEY>"""
    import io, zipfile
    from fastapi.responses import Response
    admin = os.environ.get("GC_ADMIN_KEY", "")
    if len(admin) < 16 or not secrets.compare_digest(key, admin):
        raise HTTPException(403, "Sauvegarde non autorisée.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        snap = os.path.join(DATA, ".backup.db")         # copie cohérente de la base, même pendant des paris
        src, dst = db(), sqlite3.connect(snap)
        with dst:
            src.backup(dst)
        src.close(); dst.close()
        z.write(snap, "gamecenter.db"); os.remove(snap)
        for root, _, files in os.walk(WEEKS_DIR, followlinks=True):     # semaines : liens vers l'image (Dockerfile)
            for fn in files:
                p = os.path.join(root, fn)
                z.write(p, os.path.relpath(p, DATA))
    stamp = datetime.now(TZ).strftime("%Y-%m-%d_%H%M")
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="gamecenter_backup_{stamp}.zip"'})


async def _json(req):
    try:
        b = await req.json()
        return b if isinstance(b, dict) else {}
    except Exception:
        return {}


# ------------------------------------------------------------------ semaine suivante produite toute seule
def _autogen_loop():
    from generer_semaine import generate_next
    while True:
        try:
            generate_next(WEEKS_DIR, now_ms())
            load_weeks()
        except Exception as e:
            print("génération de semaine :", e)
        time.sleep(1800)


if os.environ.get("GC_AUTOGEN") == "1":
    threading.Thread(target=_autogen_loop, daemon=True).start()
if os.environ.get("GC_PUSH_LOOP", "1") == "1":       # rappels avant le coup d'envoi (bloc 2, étape 6)
    threading.Thread(target=_push_loop, daemon=True).start()
