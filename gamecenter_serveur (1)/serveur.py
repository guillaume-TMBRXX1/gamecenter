"""GameCenter — serveur de direct (étape 9).

Le serveur garde les semaines produites par le notebook (section 15.1) et ne montre au public QUE ce qui
s'est déjà passé : les actions d'un match arrivent une par une, à l'heure (6,5 s par action, une action de
décalage), les résultats, le classement, les futures et les affiches des playoffs seulement quand ils sont
connus. Les paris sont pris, vérifiés (cote, marché ouvert, solde) et réglés ici, avec un classement commun.
Comptes (étape 1, 03/10/2026) : pseudo + mot de passe facultatifs, posés sur la clé du joueur ; classement de la
saison = somme des gains nets de chaque semaine (comptes seulement). Voir /api/account/* et /api/leaderboard?scope=season.
Paris plus riches (étape 2, 03/10/2026) : combinés 2-6 sélections (une par match, pas de futures), cash-out à la valeur
juste − 5 % (/api/cashout), historique des semaines passées (/api/history).

Lancer :  uvicorn serveur:app --host 0.0.0.0 --port 8000
Variables : GC_DATA (dossier des données, défaut ./data) · GC_SITE (gamecenter_source.html)
            GC_DEMO_AT (ISO, ex. 2026-10-05T12:59:00+02:00 : l'horloge du serveur démarre à cet instant ;
            « auto » = lundi 12:45 de la semaine la plus récente) · GC_AUTOGEN=1 (produit la semaine suivante
            tout seul, voir generer_semaine.py) · GC_ADMIN_KEY (sauvegarde, réinitialisation de mot de passe)
            GC_SEASON_START (facultatif, ex. 2026-10-05 : semaines plus anciennes hors classement de la saison)
Audio System (V0.1, 03/10/2026) : /static/audio/gc-audio.js (modules de static/audio assemblés, versionnés) et /audio/*
(fichiers sons pré-générés hors ligne, noms à empreinte, cache 1 an). Aucune clé ElevenLabs ici, jamais.
"""
import hashlib, hmac, json, os, re, secrets, sqlite3, threading, time, uuid, math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse
from fastapi.middleware.gzip import GZipMiddleware

PLAY_SEC = 6.5                 # une action toutes les 6,5 s (comme le site)
OPEN_AFTER_FINAL_MIN = 30      # une semaine ouvre aux paris 30 min après l'AI Bowl de la précédente (au plus tard le lundi 00:00)
BANKROLL, MIN_STAKE = 1000.0, 1.0
CASH_FEE = 0.05                # cash-out : valeur juste − 5 % (étape 2)
COMBO_MIN, COMBO_MAX = 2, 6    # combinés : 2 à 6 sélections, une par match, pas de futures
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
class Week:
    def __init__(self, folder):
        self.folder = folder
        with open(os.path.join(folder, "week.json"), encoding="utf-8") as fh:
            self.doc = json.load(fh)
        self.start = self.doc["week"]["start"]
        self.feeds, self.sched = {}, []
        for g in self.doc["schedule"]:
            with open(os.path.join(folder, g["feed"]), encoding="utf-8") as fh:
                f = json.load(fh)
            f["game"].pop("player_stats", None)
            self.feeds[g["id"]] = f
            ko = iso_ms(g["kickoff"]); n = len(f["plays"])
            self.sched.append(dict(g, ko=ko, n=n, end=ko + int(n * PLAY_SEC * 1000)))
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

    # ---- ce qui est connu à l'instant t ----
    def status(self, g, t):
        return "upcoming" if t < g["ko"] else "live" if t < g["end"] else "final"

    def revealed_plays(self, g, t):
        """Action i visible à partir de ko + (i+1)·6,5 s (une action de décalage : personne ne la voit avant qu'elle soit jouée)."""
        if t < g["ko"]:
            return 0
        return min(g["n"], int((t - g["ko"]) // (PLAY_SEC * 1000)))

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
        f = self.feeds[g["id"]]
        known = self.teams_known(g, t)
        game = {k: v for k, v in f["game"].items() if k not in ("final_score", "overtime", "seed")}
        if self.status(g, t) == "final":
            game["final_score"] = f["game"].get("final_score")
            if "overtime" in f["game"]:
                game["overtime"] = f["game"]["overtime"]
        if not known:
            game = {"id": game.get("id"), "home": None, "away": None, "phase": g["phase"], "kickoff": g["kickoff"]}
        k = self.revealed_plays(g, t) if upto is None else upto
        return {"schema": f.get("schema"), "game": game, "plays": f["plays"][:k] if known else []}

    def public_state(self, t):
        d = self.doc
        cs = self.completed_slots(t)
        out = {"schema": d["schema"], "week": d["week"], "teams": d["teams"],
               "schedule": [self.public_game(g, t) for g in self.sched],
               "standings_by_slot": d["standings_by_slot"][:cs],
               "futures": [f for f in d["futures"] if f["after_slot"] <= cs],
               "standings": None, "seeds": None, "champion": None, "runner_up": None}
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
        f = self.feeds[g["id"]]
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
    les suivantes, OPEN_AFTER_FINAL_MIN après la fin de l'AI Bowl de la semaine d'avant (sans dépasser le lundi 00:00).
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
    if live:
        return live[-1]
    past = [w for w in ws if w.open <= t]
    return past[-1] if past else ws[0]


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


@app.get("/", response_class=HTMLResponse)
def page():
    w = _need_week(); t = now_ms()
    bundle = {"week": w.public_state(t), "feeds": {g["id"]: w.public_feed(g, t) for g in w.sched}}
    srv = {"api": "/api", "now": t, "play_sec": PLAY_SEC, "week_start": w.start, "open_ms": w.open}
    s = _page_source().replace("__AUDIO_V__", _audio_bundle()["ver"]).replace("__GF_G1__", "null").replace("__WEEK__", _enc(bundle)).replace("__SERVER__", _enc(srv))
    if os.environ.get("GC_TEST_HOOK") == "1":   # tests automatiques seulement (même crochet que build_site.py test)
        s = s.replace("requestAnimationFrame(frame);\n})();", "requestAnimationFrame(frame);\nwindow.__gc={games,byId,views,computeStats,getModalView:()=>modalView,"
                      "season:{SCHED,setClock,nowMs,standingsAt,seasonAgg,setView,gStatus,futuresAt,bets:BETS_API},audio:AUDIO_API,"
                      "playerCardHTML,openPlayerCard};\n})();")
    return HTMLResponse(s, headers={"Cache-Control": "no-store"})


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
            plays[g["id"]] = {"from": h, "plays": w.feeds[g["id"]]["plays"][h:r]}
    st = w.public_state(t)
    st.pop("teams", None)
    # le navigateur ne lit « games » que pour les affiches de playoffs dont les équipes étaient cachées : les rosters des
    # 276 matchs de saison régulière (≈ 9 Mo) ne sont plus renvoyés toutes les 3 s
    games = {g["id"]: w.public_feed(g, t, upto=0)["game"] for g in w.sched if g["phase"] != "regular"}
    return {"now": t, "week_start": w.start, "state": st, "games": games, "plays": plays}


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


@app.get("/api/teams/history")
def api_teams_history():
    """Semaines TERMINÉES (AI Bowl joué) : champion, finaliste, têtes de série et classement final de chaque équipe —
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
            if len({k.split(":")[0] for k in keys}) != len(keys):
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


# ------------------------------------------------------------------ exhibitions (matchs hors calendrier)
EXH_DIR = os.path.join(HERE, "data", "exhibitions")     # produits par outils/exhibition/simuler_exhibition.py, dans le dépôt
_EXH_ID = re.compile(r"^[a-z0-9-]{3,60}$")


@app.get("/api/exhibitions")
def api_exhibitions():
    """Liste des matchs d'exhibition (sans score : pas de spoiler)."""
    try:
        with open(os.path.join(EXH_DIR, "index.json"), encoding="utf-8") as fh:
            idx = json.load(fh)
    except Exception:
        idx = {"exhibitions": []}
    return JSONResponse(idx, headers={"Cache-Control": "no-cache"})


@app.get("/api/exhibitions/{gid}")
def api_exhibition(gid: str):
    if not _EXH_ID.match(gid):
        raise HTTPException(404)
    p = os.path.join(EXH_DIR, gid + ".json")
    if not os.path.isfile(p):
        raise HTTPException(404)
    return FileResponse(p, media_type="application/json", headers={"Cache-Control": "no-cache"})


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
        for root, _, files in os.walk(WEEKS_DIR):
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
