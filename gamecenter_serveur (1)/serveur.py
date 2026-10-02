"""GameCenter — serveur de direct (étape 9).

Le serveur garde les semaines produites par le notebook (section 15.1) et ne montre au public QUE ce qui
s'est déjà passé : les actions d'un match arrivent une par une, à l'heure (6,5 s par action, une action de
décalage), les résultats, le classement, les futures et les affiches des playoffs seulement quand ils sont
connus. Les paris sont pris, vérifiés (cote, marché ouvert, solde) et réglés ici, avec un classement commun.

Lancer :  uvicorn serveur:app --host 0.0.0.0 --port 8000
Variables : GC_DATA (dossier des données, défaut ./data) · GC_SITE (gamecenter_source.html)
            GC_DEMO_AT (ISO, ex. 2026-10-05T12:59:00+02:00 : l'horloge du serveur démarre à cet instant ;
            « auto » = lundi 12:45 de la semaine la plus récente) · GC_AUTOGEN=1 (produit la semaine suivante
            tout seul, voir generer_semaine.py)
"""
import json, os, re, secrets, sqlite3, threading, time, uuid, math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

PLAY_SEC = 6.5                 # une action toutes les 6,5 s (comme le site)
BANKROLL, MIN_STAKE = 1000.0, 1.0
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
        self.open = int(mon.timestamp() * 1000)
        self.reset = int((mon + timedelta(days=7)).timestamp() * 1000)
        self.reg = [g for g in self.sched if g["phase"] == "regular"]
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
        for k in range(1, 19):
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
        if cs == 18:
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
            close = {"regular_season": max(g["ko"] for g in self.reg if g["slot"] == 18),
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
    def settle(self, b, t):
        k = b["key"].split(":")
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
        else:
            g = self.by[k[0]]; at = g["end"]
            if t >= at:
                H, A = g["result"]["home"], g["result"]["away"]
                if k[1] == "ml":
                    res = "push" if H == A else ("won" if (H > A) == (k[2] == "home") else "lost")
                elif k[1] == "sp":
                    mg = (H - A if k[2] == "home" else A - H) + b["line"]
                    res = "won" if mg > 0 else "lost" if mg < 0 else "push"
                else:
                    dd = H + A - b["line"]
                    res = "push" if dd == 0 else ("won" if (dd > 0) == (k[2] == "over") else "lost")
        if res is None:
            return "open", 0.0
        ret = round(b["stake"] * b["price_dec"], 2) if res == "won" else b["stake"] if res == "push" else 0.0
        return res, ret


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
    return _WEEKS


def current_week(t=None):
    t = now_ms() if t is None else t
    ws = sorted(load_weeks().values(), key=lambda w: w.open)
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
        ws = sorted(load_weeks().values(), key=lambda w: w.open)
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


def player_bets(pid, week):
    with db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM bets WHERE player=? AND week=? ORDER BY pt", (pid, week.start))]


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


# ------------------------------------------------------------------ l'application
app = FastAPI(title="GameCenter live server", docs_url="/api/docs", openapi_url="/api/openapi.json")
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


def _enc(o):
    return json.dumps(o, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")


@app.get("/", response_class=HTMLResponse)
def page():
    w = _need_week(); t = now_ms()
    bundle = {"week": w.public_state(t), "feeds": {g["id"]: w.public_feed(g, t) for g in w.sched}}
    srv = {"api": "/api", "now": t, "play_sec": PLAY_SEC, "week_start": w.start}
    s = _page_source().replace("__GF_G1__", "null").replace("__WEEK__", _enc(bundle)).replace("__SERVER__", _enc(srv))
    if os.environ.get("GC_TEST_HOOK") == "1":   # tests automatiques seulement (même crochet que build_site.py test)
        s = s.replace("requestAnimationFrame(frame);\n})();", "requestAnimationFrame(frame);\nwindow.__gc={games,byId,views,computeStats,getModalView:()=>modalView,"
                      "season:{SCHED,setClock,nowMs,standingsAt,seasonAgg,setView,gStatus,futuresAt,bets:BETS_API},audio:AUDIO_API};\n})();")
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
    games = {g["id"]: w.public_feed(g, t, upto=0)["game"] for g in w.sched}
    return {"now": t, "week_start": w.start, "state": st, "games": games, "plays": plays}


@app.post("/api/players")
async def api_new_player(req: Request):
    body = await _json(req)
    pid, token = uuid.uuid4().hex, secrets.token_urlsafe(24)
    name = clean_name(body.get("name"))
    with _db_lock, db() as c:
        c.execute("INSERT INTO players VALUES(?,?,?,?)", (pid, token, name, now_ms()))
    return {"id": pid, "token": token, "name": name}


@app.post("/api/players/me")
async def api_rename(req: Request):
    body = await _json(req)
    p = player_by_token(body.get("token"))
    if not p:
        raise HTTPException(401, "Clé de joueur inconnue.")
    name = clean_name(body.get("name"))
    with _db_lock, db() as c:
        c.execute("UPDATE players SET name=? WHERE id=?", (name, p["id"]))
    return {"name": name}


@app.get("/api/me")
def api_me(token: str = ""):
    p = player_by_token(token)
    if not p:
        raise HTTPException(401, "Clé de joueur inconnue.")
    w = _need_week(); t = now_ms()
    L = ledger(w, player_bets(p["id"], w), t)
    return {"name": p["name"], "week": w.start, "now": t, **L}


@app.post("/api/bets")
async def api_bets(req: Request):
    body = await _json(req)
    p = player_by_token(body.get("token"))
    if not p:
        raise HTTPException(401, "Clé de joueur inconnue.")
    picks = body.get("picks") or []
    if not isinstance(picks, list) or not picks or len(picks) > 20:
        raise HTTPException(400, "Envoyez entre 1 et 20 paris.")
    w = _need_week()
    accepted, rejected = [], []
    with _db_lock:
        t = now_ms()
        if not (w.open <= t < w.reset):
            raise HTTPException(409, "Les paris de cette semaine sont fermés.")
        bal = ledger(w, player_bets(p["id"], w), t)["balance"]
        rows = []
        for pk in picks:
            key = str(pk.get("key", ""))
            q = w.quote(key, t)
            if q is None:
                rejected.append({"key": key, "reason": "unknown"}); continue
            if q["locked"]:
                rejected.append({"key": key, "reason": "closed", "why": q["locked"]}); continue
            try:
                stake = round(float(pk.get("stake")), 2); price = float(pk.get("price_dec")); line = pk.get("line")
                line = None if line is None else float(line)
            except (TypeError, ValueError):
                rejected.append({"key": key, "reason": "invalid"}); continue
            if abs(price - q["price_dec"]) > 0.006 or line != q["line"]:
                rejected.append({"key": key, "reason": "price", "price_dec": q["price_dec"], "line": q["line"]}); continue
            if not (stake >= MIN_STAKE):
                rejected.append({"key": key, "reason": "stake"}); continue
            if stake > bal + 1e-9:
                rejected.append({"key": key, "reason": "balance", "balance": bal}); continue
            bal = round(bal - stake, 2)
            b = {"id": "b" + uuid.uuid4().hex[:16], "player": p["id"], "week": w.start, "key": key,
                 "price_dec": q["price_dec"], "line": q["line"], "stake": stake, "pt": t,
                 "title": str(pk.get("title", ""))[:120], "sub": str(pk.get("sub", ""))[:120]}
            rows.append(b); accepted.append(b)
        if rows:
            with db() as c:
                c.executemany("INSERT INTO bets VALUES(:id,:player,:week,:key,:price_dec,:line,:stake,:pt,:title,:sub)", rows)
    return {"now": t, "accepted": accepted, "rejected": rejected, "balance": bal}


@app.get("/api/leaderboard")
def api_leaderboard(token: str = ""):
    w = _need_week(); t = now_ms()
    with db() as c:
        players = [dict(r) for r in c.execute("SELECT DISTINCT p.* FROM players p JOIN bets b ON b.player=p.id WHERE b.week=?", (w.start,))]
    me = player_by_token(token)
    rows = []
    for p in players:
        L = ledger(w, player_bets(p["id"], w), t)
        rows.append({"name": p["name"], "balance": L["balance"], "bets": len(L["bets"]), "won": L["won"], "lost": L["lost"],
                     "me": bool(me and me["id"] == p["id"])})
    rows.sort(key=lambda r: (-r["balance"], r["name"]))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    mine = next((r for r in rows if r["me"]), None)
    return {"week": w.start, "players": len(rows), "top": rows[:20], "me": mine}


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
