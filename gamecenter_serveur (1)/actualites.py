"""Onglet News : l'édition du jour, écrite d'après les matchs TERMINÉS (README section 115, 12/11/2026).

Une édition par jour de match (Bruxelles), avec des quotas fixes (décision de Guillaume, 11/11) :
  upset    la plus grosse surprise du jour (vainqueur coté +150 ou plus)                       1 par jour au plus
  ref      une pénalité du 4e quart-temps (ou de la prolongation) d'un match serré, avec une
           QUESTION aux supporters (« right call? ») — le vote est rangé par le serveur          1 par jour au plus
  rivalry  match à trophée du jour (moteur/rivalites.py) quand le trophée change de mains (ou se gagne
           pour la première fois) ; sinon une brève                                              2 par jour au plus
  injury   blessure du jour : 3 semaines ou plus, ou un QB absent 2 semaines ou plus             2 par jour au plus
  ats / hot / cold  tendances de la semaine (spreads battus, séries) : un article chacune, réécrit
           après chaque journée (même identifiant), à partir du 2e jour
  playoff  chaque demi-finale et la Grand Final                                                  toujours
  brief    brèves : les autres blessures de 2 semaines ou plus, prolongations, larges victoires, blanchissages
                                                                                                  4 par jour au plus
Rien ici ne lit un match à venir ou en cours : le serveur ne passe que les matchs terminés, les blessures de la semaine
de ces matchs, et une fonction pour lire leurs données. Textes en anglais, comme le site ; tournures fixées par
l'identifiant (comptes_rendus._choix), donc la même édition pour tout le monde et à chaque calcul.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import comptes_rendus as _cr

VERSION = "actualites-1"
TZ = ZoneInfo("Europe/Brussels")
UPSET_ML = 150             # vainqueur coté +150 (décimal 2,50) ou plus
REF_MARGE, REF_ECART = 7, 8    # match fini à 7 points au plus ; pénalité à 8 points d'écart au plus
INJ_SEMAINES, INJ_QB = 3, 2
ATS_MIN, SERIE_MIN = 6, 4      # 6 matchs joués pour le classement des spreads ; série de 4 au moins
LARGE, BREVES_JOUR, INJ_JOUR, RIV_JOUR = 30, 4, 2, 2
SERIE_POINTS = 40              # courbe de probabilité de victoire : 40 points au plus


def _jour(ms):
    return datetime.fromtimestamp(ms / 1000, TZ).strftime("%Y-%m-%d")


def _ville(teams, a):
    """« Cortex Foxes » → « Cortex » (titres)."""
    return ((teams.get(a) or {}).get("name") or a).split(" ", 1)[0]


def _nom(teams, a):
    return (teams.get(a) or {}).get("name") or a


def _ml(am):
    return f"+{am}" if am > 0 else f"−{abs(am)}"


def _dec(am):
    return round(1 + (am / 100 if am > 0 else 100 / -am), 2)


def _un(mot):
    return ("an " if (mot or "")[:1].lower() in "aeiou" else "a ") + (mot or "")


def _mal(part):
    """« a concussion », « an ankle injury »."""
    return "a concussion" if part == "concussion" else _un(part or "unknown") + " injury"


def _numero(teams, a, pid):
    for r in (teams.get(a) or {}).get("roster") or []:
        if r.get("id") == pid:
            return r.get("number")
    return None


def _courbe(P, cote, p0):
    """Probabilité de victoire du côté « cote », du coup d'envoi à la fin, en SERIE_POINTS points au plus."""
    v = [p0 if p0 is not None else 0.5] + [p["win_prob_home"] for p in P if p.get("win_prob_home") is not None]
    if cote == "away":
        v = [1 - x for x in v]
    if len(v) > SERIE_POINTS:
        pas = (len(v) - 1) / (SERIE_POINTS - 1)
        v = [v[round(i * pas)] for i in range(SERIE_POINTS)]
    return [round(x, 3) for x in v]


def _wp(P, cote, p0):
    """Courbe allégée et vrai minimum (la courbe allégée peut sauter le point le plus bas)."""
    v = [p0 if p0 is not None else 0.5] + [p["win_prob_home"] for p in P if p.get("win_prob_home") is not None]
    bas = min(v) if cote != "away" else min(1 - x for x in v)
    return {"series": _courbe(P, cote, p0), "low": round(bas, 2)}     # arrondi comme le texte (_cr._pct)


def _score(g):
    r = g.get("result") or {}
    return {"home": g["home"], "away": g["away"], "hs": r.get("home", 0), "as": r.get("away", 0),
            "ot": bool(r.get("overtime"))}


def _vainqueur(g):
    r = g.get("result") or {}
    return "home" if r.get("home", 0) > r.get("away", 0) else "away" if r.get("away", 0) > r.get("home", 0) else None


def _joueur_du_match(fm, equipe):
    js = [j for j in (fm.get("joueurs") or {}).values() if j.get("team") == equipe]
    j = max(js, key=_cr._note, default=None)
    return (j, _cr._ligne(j)) if j and _cr._ligne(j) else (None, "")


def _article(id_, kind, g_or_ms, week, **kw):
    at = g_or_ms["end"] if isinstance(g_or_ms, dict) else g_or_ms
    a = {"id": id_, "kind": kind, "week": week, "at": at, "day": _jour(at), "kicker": "", "title": "", "dek": "",
         "body": [], "teams": [], "game": None, "score": None, "visual": None, "question": None, "impact": 0}
    a.update(kw)
    return a


# ------------------------------------------------------------------ rubriques d'un match
def _upset(g, A, fm, teams, week):
    s = _vainqueur(g)
    ml = ((g.get("odds") or {}).get("ml") or {}).get(s) if s else None
    if ml is None or ml < UPSET_ML:
        return None
    o = "away" if s == "home" else "home"
    W, L = g[s], g[o]
    sc = _score(g)
    ws, ls = sc["hs" if s == "home" else "as"], sc["as" if s == "home" else "hs"]
    j, ligne = _joueur_du_match(fm, W)
    wp_min = A.get("wp_min")
    titre = _cr._choix(g["id"], "nw-up", [
        f"{_ville(teams, W)} stun {_ville(teams, L)} at {_ml(ml)}",
        f"{_ville(teams, W)} {ws}, {_ville(teams, L)} {ls}: the upset of the day",
        f"Nobody gave {_ville(teams, W)} a chance. They won {ws}–{ls}",
    ])
    dek = f"The {_nom(teams, W)} were priced at {_ml(ml)} ({_dec(ml):.2f}) before kickoff."
    if wp_min is not None and wp_min < 0.3:
        dek += f" Their win chance fell to {_cr._pct(wp_min)} along the way."
    body = [dek]
    if j:
        body.append(f"{j['name']} ({j['pos']}) led the way: {ligne}.")
    if A.get("retard_max", 0) >= 7:
        body.append(f"They came back from {A['retard_max']} points down.")
    body.append(f"Final: {_ville(teams, W)} {ws}, {_ville(teams, L)} {ls}{' in overtime' if sc['ot'] else ''}.")
    return _article(f"{g['id']}-upset", "upset", g, week, kicker="Upset", title=titre, dek=" ".join(body[:2]),
                    body=body, teams=[W, L], game=g["id"], score=sc, impact=100 + ml / 10,
                    visual={"type": "wp", "team": W, **_wp(A["P"], s, A.get("p_dom")),
                            "label": f"{W} win prob."})


def _ref(g, A, teams, week):
    sc = _score(g)
    if abs(sc["hs"] - sc["as"]) > REF_MARGE:
        return None
    P, best, prev = A["P"], None, A.get("p_dom") if A.get("p_dom") is not None else 0.5
    avant = {"home": 0, "away": 0}
    for i, p in enumerate(P):
        w = p.get("win_prob_home")
        pen = p.get("penalty")
        if pen and (p.get("quarter") or 1) >= 4 and abs(avant["home"] - avant["away"]) <= REF_ECART and w is not None:
            d = abs(w - prev)
            if best is None or d > best[0]:
                best = (d, i, p, prev, w, dict(avant))
        if w is not None:
            prev = w
        avant = (p.get("after") or {}).get("score") or avant
    if best is None or best[0] < 0.03:
        return None
    _, i, p, w0, w1, avant = best
    pen = p["penalty"]
    off = p.get("offense")
    fautif = off if pen.get("team") == "offense" else ("away" if off == "home" else "home")
    pl = pen.get("player") or {}
    qui = f"{pl.get('name')} (#{pl['number']})" if pl.get("name") and pl.get("number") is not None else pl.get("name") or "a player"
    nomp = (pen.get("name") or "a penalty").lower()
    horloge = _cr._quand(p)
    mene = ("tied" if avant["home"] == avant["away"] else
            f"{_ville(teams, g['home'] if avant['home'] > avant['away'] else g['away'])} up "
            f"{max(avant['home'], avant['away'])}–{min(avant['home'], avant['away'])}")
    s = _vainqueur(g)
    titre = _cr._choix(g["id"], "nw-ref", [
        f"The flag at {_cr._horloge(p.get('clock_end'))}: did it decide {_ville(teams, g['away'])}–{_ville(teams, g['home'])}?",
        f"{(pen.get('name') or 'Penalty')} on {pl.get('name') or _ville(teams, g[fautif])}: right call?",
        f"One flag, one swing: {_ville(teams, g['away'])} at {_ville(teams, g['home'])}",
    ])
    if pen.get("declined"):
        suite = f"{_ville(teams, g[pen.get('chooser') == 'offense' and off or ('away' if off == 'home' else 'home')])} declined it and kept the play."
    else:
        suite = f"The flag stood{(', ' + str(pen['yards']) + ' yards') if pen.get('yards') else ''}."
    w_f = w1 if s == "home" else 1 - w1
    w_i = w0 if s == "home" else 1 - w0
    body = [f"{_cr._cap(horloge)}, {mene}, {qui} of the {_nom(teams, g[fautif])} was flagged for {nomp}. {suite}",
            f"The winners' chances moved from {_cr._pct(w_i)} to {_cr._pct(w_f)} on that snap." if s else
            f"Win probability moved by {round(100 * abs(w1 - w0))} points on that snap.",
            (f"{_ville(teams, g[s])} won {max(sc['hs'], sc['as'])}–{min(sc['hs'], sc['as'])}"
             f"{' in overtime' if sc['ot'] else ''}." if s else f"It finished {sc['hs']}–{sc['as']}.")]
    q = {"text": f"Was it {_cr._choix(g['id'], 'nw-q', ['the right call', 'a fair flag'])}?",
         "options": [{"id": "yes", "label": "Right call"}, {"id": "no", "label": "Bad call"}]}
    serie = _wp(P, s or "home", A.get("p_dom"))
    return _article(f"{g['id']}-ref", "ref", g, week, kicker="Officiating", title=titre, dek=body[0],
                    body=body, teams=[g["away"], g["home"]], game=g["id"], score=sc, question=q,
                    impact=80 + 100 * best[0],
                    visual={"type": "wp", "team": g[s] if s else g["home"], **serie,
                            "mark": round(min(1.0, (i + 1) / max(1, len(P))), 3),
                            "label": f"{g[s] if s else g['home']} win prob.",
                            "flag": {"name": pen.get("name"), "player": pl.get("name"), "number": pl.get("number"),
                                     "team": g[fautif], "clock": f"{_cr._q(p)} {_cr._horloge(p.get('clock_end'))}",
                                     "declined": bool(pen.get("declined"))}})


def _rivalry(g, teams, week, serie):
    from moteur import rivalites as _riv
    t = _riv.trophee(g["home"], g["away"])
    if not t:
        return None
    sc = _score(g)
    s = _vainqueur(g)
    S = serie(g["home"], g["away"], g["ko"] + 1) or {}          # les confrontations jusqu'à celle-ci comprise
    rec = S.get("record") or {}
    a, b = g["home"], g["away"]
    avant = [m for m in (S.get("recent") or []) if m.get("id") != g["id"]]
    tenant_avant = next((m["winner"] for m in avant if m.get("winner")), None)
    if s is None:
        return {"brief": f"{t} stays put: {_ville(teams, b)} and {_ville(teams, a)} tie {sc['as']}–{sc['hs']}.",
                "teams": [b, a]}
    else:
        W, L = g[s], g["away" if s == "home" else "home"]
        ws, ls = max(sc["hs"], sc["as"]), min(sc["hs"], sc["as"])
        if tenant_avant == W:
            return {"brief": f"{_ville(teams, W)} keep {t}, {ws}–{ls} over {_ville(teams, L)}.", "teams": [W, L]}
        titre = (f"{_ville(teams, W)} take {t} from {_ville(teams, L)}" if tenant_avant else f"{_ville(teams, W)} win {t}")
        dek = f"A {ws}–{ls} win{' in overtime' if sc['ot'] else ''} over {_ville(teams, L)}."
    body = [dek]
    if rec:
        tie = f", {rec.get('ties')} tie{'s' if rec.get('ties', 0) > 1 else ''}" if rec.get("ties") else ""
        body.append(f"All-time series: {_ville(teams, a)} {rec.get(a, 0)}, {_ville(teams, b)} {rec.get(b, 0)}{tie}.")
    st = S.get("streak")
    if st and st.get("n", 0) >= 2:
        body.append(f"{_ville(teams, st['team'])} have won the last {st['n']} meetings.")
    return _article(f"{g['id']}-rivalry", "rivalry", g, week, kicker=f"Rivalry · {t}", title=titre, dek=" ".join(body[:2]),
                    body=body, teams=[g["away"], g["home"]], game=g["id"], score=sc, impact=70,
                    visual={"type": "rivalry", "trophy": t, "record": {k: rec.get(k, 0) for k in (a, b, "ties")} if rec else None})


def _injury(x, g, teams, week):
    a, pos, n = x["team"], x.get("pos") or "", x.get("weeks") or 0
    num = _numero(teams, a, x.get("id"))
    titre = _cr._choix(x.get("id", "") + g["id"], "nw-inj", [
        f"{_ville(teams, a)} lose {x['name']} for {n} weeks",
        f"{x['name']} out {n} weeks: a blow for {_ville(teams, a)}",
    ])
    dek = (f"The {_nom(teams, a)} {pos} suffered {_mal(x.get('part'))} against "
           f"{_ville(teams, g['away'] if g['home'] == a else g['home'])} and will miss {n} weeks.")
    return _article(f"{g['id']}-inj-{x.get('id')}", "injury", g, week, kicker="Injury report", title=titre, dek=dek,
                    body=[dek], teams=[a], game=g["id"], impact=60 + n * 3 + (10 if pos == "QB" else 0),
                    visual={"type": "injury", "team": a, "number": num, "name": x["name"], "pos": pos,
                            "part": x.get("part"), "weeks": n})


def _playoff(g, A, fm, teams, week):
    s = _vainqueur(g)
    if s is None:
        return None
    sc = _score(g)
    W, L = g[s], g["away" if s == "home" else "home"]
    ws, ls = max(sc["hs"], sc["as"]), min(sc["hs"], sc["as"])
    j, ligne = _joueur_du_match(fm, W)
    finale = g["phase"] == "ai_bowl"
    titre = (f"{_nom(teams, W)} are champions" if finale else f"{_ville(teams, W)} are into the Grand Final")
    body = [f"{_ville(teams, W)} beat {_ville(teams, L)} {ws}–{ls}{' in overtime' if sc['ot'] else ''} in the "
            f"{'Grand Final' if finale else 'conference final'}."]
    if j:
        body.append(f"{j['name']} ({j['pos']}): {ligne}.")
    if A.get("retard_max", 0) >= 7:
        body.append(f"They were down {A['retard_max']} at one point.")
    return _article(f"{g['id']}-playoff", "playoff", g, week, kicker="Grand Final" if finale else "Conference final",
                    title=titre, dek=" ".join(body[:2]), body=body, teams=[W, L], game=g["id"], score=sc,
                    impact=200 if finale else 150,
                    visual={"type": "wp", "team": W, **_wp(A["P"], s, A.get("p_dom")), "label": f"{W} win prob."})


# ------------------------------------------------------------------ tendances de la semaine
def _tendances(jeux, teams, week, at):
    ordre = sorted((g for g in jeux if g["phase"] == "regular"), key=lambda g: g["ko"])
    ats, suite = {}, {}
    for g in ordre:
        sc, sp = _score(g), (g.get("odds") or {}).get("spread_home")
        for s, o in (("home", "away"), ("away", "home")):
            a = g[s]
            res = "W" if sc["hs" if s == "home" else "as"] > sc["as" if s == "home" else "hs"] else (
                "L" if sc["hs" if s == "home" else "as"] < sc["as" if s == "home" else "hs"] else "T")
            suite.setdefault(a, []).append(res)
            if sp is not None:
                m = (sc["hs"] - sc["as"] + sp) * (1 if s == "home" else -1)
                r = ats.setdefault(a, [0, 0])
                if m > 0:
                    r[0] += 1
                elif m < 0:
                    r[1] += 1
    out = []
    rows = sorted(((a, w, l) for a, (w, l) in ats.items() if w + l >= ATS_MIN), key=lambda x: (-x[1] / (x[1] + x[2]), -x[1], x[0]))
    if len(rows) >= 4:
        a, w, l = rows[0]
        z = rows[-1]
        out.append(_article(f"w{week}-ats", "ats", at, week, kicker="Against the spread",
                            title=f"{_ville(teams, a)} have covered {w} of {w + l}",
                            dek=(f"Best record against the engine's spread this week: {_nom(teams, a)}, {w}–{l}. "
                                 f"At the other end, {_nom(teams, z[0])} are {z[1]}–{z[2]}."),
                            teams=[a, z[0]], impact=40,
                            visual={"type": "bars", "rows": [{"team": r[0], "w": r[1], "l": r[2]} for r in rows[:3] + rows[-1:]]}))
        out[-1]["body"] = [out[-1]["dek"]]

    def serie(seq, c):
        n = 0
        for r in reversed(seq):
            if r != c:
                break
            n += 1
        return n
    for kind, c, mot in (("hot", "W", "won"), ("cold", "L", "lost")):
        best = max(((serie(seq, c), a) for a, seq in suite.items()), default=(0, None))
        if best[0] >= SERIE_MIN:
            n, a = best
            seq = suite[a]
            w, l = seq.count("W"), seq.count("L")
            t = seq.count("T")
            rec = f"{w}–{l}" + (f"–{t}" if t else "")
            titre = (f"{_ville(teams, a)} have {mot} {n} straight" if kind == "hot" else
                     f"{_ville(teams, a)}: {n} losses in a row")
            dek = f"The {_nom(teams, a)} are {rec} this week." + (
                " Nobody is hotter." if kind == "hot" else " Nobody is colder.")
            out.append(_article(f"w{week}-{kind}", kind, at, week, kicker="Form" if kind == "hot" else "Falling short",
                                title=titre, dek=dek, body=[dek], teams=[a], impact=35,
                                visual={"type": "streak", "team": a, "seq": "".join(seq[-10:]), "n": n}))
    return out


# ------------------------------------------------------------------ l'édition
def edition(jeux, teams, week, lire, serie, blessures=(), memo=None):
    """Les articles d'une semaine, du plus récent au plus ancien.
    jeux : matchs TERMINÉS du calendrier (avec ko, end, result, odds) ; lire(gid) -> (feed, feuille de match) ;
    serie(a, b, avant_ms) -> moteur.rivalites.serie des confrontations terminées avant avant_ms ;
    blessures : blessures de la semaine (week.json → injuries.in_week) dont le match est terminé.
    memo : dict gardé par l'appelant, les articles tirés des données d'un match terminé (ils ne changent plus)."""
    memo = {} if memo is None else memo
    jeux = sorted(jeux, key=lambda g: g["end"])
    by = {g["id"]: g for g in jeux}
    jours = {}
    for g in jeux:
        jours.setdefault(_jour(g["end"]), []).append(g)
    arts = []
    for j, gs in sorted(jours.items()):
        cand = {"upset": [], "ref": []}
        breves, rivs = [], []
        for g in gs:
            if g.get("home") is None or g.get("away") is None or not g.get("result"):
                continue
            r = _rivalry(g, teams, week, serie)
            if r and "brief" in r:
                breves.append((1, g, f"{r['teams'][0]}|{r['brief']}", r["teams"], "riv"))
            elif r:
                rivs.append(r)
            w = _vainqueur(g)
            ml = ((g.get("odds") or {}).get("ml") or {}).get(w) if w else None
            serre = abs(g["result"].get("home", 0) - g["result"].get("away", 0)) <= REF_MARGE
            po = g["phase"] in ("semifinal", "ai_bowl")
            if (ml is not None and ml >= UPSET_ML) or serre or po:
                if g["id"] not in memo:
                    feed, fm = lire(g["id"])
                    A = _cr.analyser(g, feed, fm)
                    memo[g["id"]] = (_playoff(g, A, fm, teams, week) if po else None,
                                     _upset(g, A, fm, teams, week) if ml is not None and ml >= UPSET_ML else None,
                                     _ref(g, A, teams, week) if serre else None)
                pa, u, f = memo[g["id"]]
                if pa:
                    arts.append(pa)
                if u:
                    cand["upset"].append(u)
                if f:
                    cand["ref"].append(f)
        arts += rivs[-RIV_JOUR:]                      # les plus récents du jour
        for k in cand:
            if cand[k]:
                arts.append(max(cand[k], key=lambda a: a["impact"]))
        # blessures du jour
        bl = sorted(((x, by[x["game"]]) for x in blessures if x.get("game") in by and _jour(by[x["game"]]["end"]) == j),
                    key=lambda xg: (-(xg[0].get("weeks") or 0), xg[0].get("pos") != "QB", xg[0].get("name", "")))
        grosses = [xg for xg in bl if (xg[0].get("weeks") or 0) >= INJ_SEMAINES
                   or (xg[0].get("pos") == "QB" and (xg[0].get("weeks") or 0) >= INJ_QB)][:INJ_JOUR]
        arts += [_injury(x, g, teams, week) for x, g in grosses]
        for x, g in bl:
            if (x, g) not in grosses and (x.get("weeks") or 0) >= 2:
                breves.append((5, g, f"{x['team']}|{x['name']} ({x.get('pos')}) out {x['weeks']} weeks with "
                                      f"{_mal(x.get('part'))}.", [x["team"]], f"inj-{x.get('id')}"))
        for g in gs:
            if not g.get("result"):
                continue
            sc, w = _score(g), _vainqueur(g)
            if w is None:
                continue
            W, L = g[w], g["away" if w == "home" else "home"]
            ws, ls = max(sc["hs"], sc["as"]), min(sc["hs"], sc["as"])
            if sc["ot"]:
                breves.append((4, g, f"{W}|{_ville(teams, W)} edge {_ville(teams, L)} {ws}–{ls} in overtime.", [W, L], "ot"))
            elif ls == 0:
                breves.append((3, g, f"{W}|{_ville(teams, W)} shut out {_ville(teams, L)}, {ws}–0.", [W, L], "so"))
            elif ws - ls >= LARGE:
                breves.append((2, g, f"{W}|{_ville(teams, W)} rout {_ville(teams, L)} {ws}–{ls}.", [W, L], "big"))
        breves.sort(key=lambda b: (-b[0], b[1]["end"]))
        for imp, g, txt, tms, k in breves[:BREVES_JOUR]:
            tm, txt = txt.split("|", 1)
            arts.append(_article(f"{g['id']}-b-{k}", "brief", g, week, title=txt, teams=tms, game=g["id"], impact=imp,
                                 kicker=tm))
    if len(jours) >= 2:          # tendances : à partir du 2e jour, réécrites après chaque journée
        arts += _tendances(jeux, teams, week, jeux[-1]["end"])
    arts.sort(key=lambda a: (a["day"], a["impact"], a["at"]), reverse=True)
    return arts
