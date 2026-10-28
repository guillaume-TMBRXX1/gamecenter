"""Onglet « Insights » du site : les statistiques de la semaine en cours, pour parier plus intelligemment.

Tout se calcule sur les matchs TERMINÉS à l'instant demandé (le serveur ne passe que ceux-là) : jamais un résultat,
une action ou une cote d'après-match avant l'heure. Rien ne change dans le moteur ni dans le calcul du samedi.

  calculer(jeux) : jeux = [(match du calendrier, GameFeed)] des matchs terminés, dans l'ordre des coups d'envoi.
                   -> {"league", "rows", "hints", "recaps"}
     league  quatre chiffres de la ligue (points par match, victoires à domicile, des favoris, overs)
     rows    une ligne par franchise, triée par force (« rating » : marge moyenne corrigée du calendrier, SRS)
     hints   au plus six indices nets (contre le spread, over / under, chance), échantillon d'au moins MIN_MATCHS
     recaps  le récap de chaque journée (surprises, meilleures performances, match le plus prolifique, le plus serré)

« Luck » = victoires réelles moins les victoires que les cotes du moteur d'avant-match attendaient (somme des chances de
victoire). Textes en anglais, comme le site.
"""
import collections

VERSION = "insights-1"
MIN_MATCHS = 8                  # un indice ne porte que sur au moins 8 matchs de l'équipe
SEUIL = 0.7                     # 70 % de couverture (spread, over / under) au moins
SEUIL_LUCK = 1.5                # au moins 1,5 victoire d'écart avec les cotes
PAR_GENRE, MAX_HINTS = 2, 6
SERRE = 8                       # match serré : 8 points d'écart au plus
GRANDE = 20                     # grosse action : 20 yards ou plus

_COUPS_DE_PIED = {"kickoff", "punt", "pat_good", "pat_missed", "two_point_good", "two_point_failed",
                  "field_goal_good", "field_goal_missed"}
_SCRIMMAGE = {"run", "complete", "incomplete", "sack", "interception", "fumble_lost", "touchdown"}
_PASSES = {"complete", "incomplete", "sack", "interception"}


def _pct(a, b):
    return round(a / b, 3) if b else None


def _cotes(g, F):
    return (F.get("game") or {}).get("pregame_odds") or g.get("odds") or {}


def _actions(g, F, S):
    """Statistiques d'action par équipe (attaque et défense) d'un match."""
    h, a = g["home"], g["away"]
    side = {"home": h, "away": a}
    zone = None                                  # (match, équipe) : entrée dans les 20 derniers yards comptée une fois
    for P in F.get("plays") or []:
        off = side.get(P.get("offense"))
        if not off:
            continue
        de = a if off == h else h
        res, gain, call = P.get("result"), P.get("gain") or 0, P.get("call") or {}
        if res in _COUPS_DE_PIED or res not in _SCRIMMAGE or call.get("type") in ("kneel", "spike"):
            continue
        o, d = S[off], S[de]
        o["plays"] += 1; o["yds"] += gain; d["plays_a"] += 1; d["yds_a"] += gain
        passe = call.get("type") == "pass" or res in _PASSES or bool((P.get("players") or {}).get("passer"))
        o["pass"] += passe
        if gain >= GRANDE and res in ("run", "complete", "touchdown"):
            o["xpl"] += 1; d["xpl_a"] += 1
        if res in ("interception", "fumble_lost"):
            o["give"] += 1; d["take"] += 1
        if res == "sack":
            d["sk"] += 1
        if P.get("down") == 3:
            o["d3"] += 1
            af = P.get("after") or {}
            if res == "touchdown" or (af.get("offense") == P.get("offense") and af.get("down") == 1):
                o["d3c"] += 1
        x = P.get("los_x")
        if x is None:
            continue
        reste = 110 - x if P["offense"] == "home" else x - 10       # yards jusqu'à l'en-but
        if reste <= 20:
            if zone != off:
                zone = off; o["rz"] += 1
            if res == "touchdown":
                o["rz_td"] += 1; zone = None
        elif zone and zone != off:
            zone = None


def _force(marges, adversaires):
    """Rating SRS : marge moyenne + force moyenne des adversaires (itérations), centré sur 0."""
    moy = {t: sum(m) / len(m) for t, m in marges.items() if m}
    r = dict(moy)
    for _ in range(30):
        r = {t: moy[t] + sum(r[o] for o in adversaires[t]) / len(adversaires[t]) for t in moy}
    if not r:
        return {}
    m0 = sum(r.values()) / len(r)
    return {t: v - m0 for t, v in r.items()}


def _indices(rows):
    out = []
    for x in rows:
        t, n = x["team"], sum(x["ats"])
        if n >= MIN_MATCHS and x["ats"][0] / n >= SEUIL:
            out.append({"kind": "ats", "team": t, "score": x["ats"][0] / n,
                        "text": f"{t} covers the spread {x['ats'][0]} of {n}",
                        "sub": "Beats the engine line more often than not: the price may still be too long."})
        if n >= MIN_MATCHS and x["ats"][1] / n >= SEUIL:
            out.append({"kind": "ats", "team": t, "score": x["ats"][1] / n,
                        "text": f"{t} fails to cover {x['ats'][1]} of {n}",
                        "sub": "Wins on paper, loses against the line: think twice before laying the points."})
        m = sum(x["ou"])
        if m >= MIN_MATCHS and max(x["ou"]) / m >= SEUIL:
            over = x["ou"][0] > x["ou"][1]
            out.append({"kind": "ou", "team": t, "score": max(x["ou"]) / m,
                        "text": f"{'Overs' if over else 'Unders'} hit in {max(x['ou'])} of {m} {t} games",
                        "sub": f"Their games run {'higher' if over else 'lower'} than the engine total."})
        if x["gp"] >= MIN_MATCHS and abs(x["luck"]) >= SEUIL_LUCK:
            plus = x["luck"] > 0
            out.append({"kind": "luck", "team": t, "score": 0.5 + abs(x["luck"]) / 20,
                        "text": f"{t} has won {abs(x['luck'])} {'more' if plus else 'fewer'} games than the engine expected",
                        "sub": ("Close wins and turnovers: results ahead of the play, a candidate to cool off." if plus else
                                "Plays better than the record says: value when the price is long.")})
    out.sort(key=lambda h: (-h["score"], h["team"], h["kind"]))
    pris, n = [], collections.Counter()
    for h in out:
        if n[h["kind"]] < PAR_GENRE and len(pris) < MAX_HINTS:
            pris.append({k: v for k, v in h.items() if k != "score"}); n[h["kind"]] += 1
    return pris


def _recap(jeux):
    """Récap d'une journée : surprises (plus grosses cotes d'abord), meilleure performance d'un match (passe,
    course, réception), match le plus prolifique et le plus serré."""
    surprises, perf, noms, pts = [], collections.Counter(), {}, 0
    for g, F in jeux:
        rs, o = g["result"], _cotes(g, F)
        pts += rs["home"] + rs["away"]
        ml = o.get("ml") or {}
        for c, autre in (("home", "away"), ("away", "home")):
            if rs[c] > rs[autre] and (ml.get(c) or 0) > 0:
                surprises.append({"game": g["id"], "winner": g[c], "loser": g[autre], "ml": ml[c],
                                  "score": f"{rs[c]}-{rs[autre]}"})
        for P in F.get("plays") or []:
            pl = P.get("players") or {}
            car, pas, res = pl.get("carrier") or {}, pl.get("passer") or {}, P.get("result")
            gain = P.get("gain") or 0
            if res in ("complete", "touchdown") and pas.get("id"):
                perf[("pass", g["id"], pas["id"])] += gain; noms[pas["id"]] = pas.get("name") or pas["id"]
                if car.get("id"):
                    perf[("rec", g["id"], car["id"])] += gain; noms[car["id"]] = car.get("name") or car["id"]
            elif res in ("run", "touchdown") and car.get("id") and not pas.get("id"):
                perf[("rush", g["id"], car["id"])] += gain; noms[car["id"]] = car.get("name") or car["id"]
    par_id = {g["id"]: g for g, _ in jeux}

    def tops(genre):
        v = sorted(((y, pid, gid) for (k, gid, pid), y in perf.items() if k == genre), key=lambda z: (-z[0], z[1]))
        out = []
        for y, pid, gid in v[:1]:
            G, eq = par_id[gid], pid.split("_")[0]
            out.append({"id": pid, "name": noms[pid], "team": eq, "yds": y, "game": gid,
                        "vs": G["away"] if G["home"] == eq else G["home"]})
        return out

    def court(g):
        return {"id": g["id"], "home": g["home"], "away": g["away"], "hs": g["result"]["home"], "as": g["result"]["away"]}
    prolifique = max(jeux, key=lambda j: (j[0]["result"]["home"] + j[0]["result"]["away"], j[0]["id"]))[0]
    serre = min(jeux, key=lambda j: (abs(j[0]["result"]["home"] - j[0]["result"]["away"]), j[0]["id"]))[0]
    return {"games": len(jeux), "ppg": round(pts / len(jeux), 1), "n_upsets": len(surprises),
            "upsets": sorted(surprises, key=lambda u: (-u["ml"], u["game"]))[:3],
            "top": {k: tops(k) for k in ("pass", "rush", "rec")},
            "shootout": court(prolifique), "thriller": court(serre)}


def calculer(jeux):
    S = collections.defaultdict(collections.Counter)
    forme, adv, marges = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
    fav = ov = n_ov = n_fav = dom = 0
    for g, F in jeux:
        h, a = g["home"], g["away"]
        hs, as_ = g["result"]["home"], g["result"]["away"]
        o = _cotes(g, F)
        dom += hs > as_
        ml = o.get("ml") or {}
        if ml.get("home") is not None and ml.get("away") is not None:
            n_fav += 1
            fav += (hs > as_) if ml["home"] < ml["away"] else (as_ > hs)
        if o.get("total") is not None:
            n_ov += 1; ov += hs + as_ > o["total"]
        for t, us, them, c in ((h, hs, as_, "home"), (a, as_, hs, "away")):
            s = S[t]
            s["gp"] += 1; s["pf"] += us; s["pa"] += them
            s["w"] += us > them; s["l"] += us < them; s["t"] += us == them
            forme[t].append("W" if us > them else "L" if us < them else "T")
            adv[t].append(a if c == "home" else h)
            marges[t].append(us - them)
            sp = o.get("spread_home")
            if sp is not None:
                v = us - them + (sp if c == "home" else -sp)
                s["ats_w"] += v > 0; s["ats_l"] += v < 0; s["ats_p"] += v == 0
            if o.get("total") is not None:
                s["ov"] += hs + as_ > o["total"]; s["un"] += hs + as_ < o["total"]
            ph = o.get("p_home")
            if ph is not None:
                s["xw"] += ph if c == "home" else 1 - ph - (o.get("p_tie") or 0)
            if abs(us - them) <= SERRE:
                s["close_gp"] += 1; s["close_w"] += us > them
        _actions(g, F, S)
    force = _force(marges, adv)
    rows = []
    for t, s in S.items():
        gp = s["gp"]
        if not gp:
            continue
        rows.append({"team": t, "gp": gp, "w": s["w"], "l": s["l"], "t": s["t"],
                     "ppg": round(s["pf"] / gp, 1), "papg": round(s["pa"] / gp, 1),
                     "ats": [s["ats_w"], s["ats_l"], s["ats_p"]], "ou": [s["ov"], s["un"]],
                     "xw": round(s["xw"], 1), "luck": round(s["w"] + 0.5 * s["t"] - s["xw"], 1),
                     "close": [s["close_w"], s["close_gp"]],
                     "ypp": round(s["yds"] / s["plays"], 2) if s["plays"] else None,
                     "ypp_a": round(s["yds_a"] / s["plays_a"], 2) if s["plays_a"] else None,
                     "pass": _pct(s["pass"], s["plays"]), "d3": _pct(s["d3c"], s["d3"]), "rz": _pct(s["rz_td"], s["rz"]),
                     "to": s["take"] - s["give"], "xpl": round(s["xpl"] / gp, 1), "sk": round(s["sk"] / gp, 1),
                     "form": forme[t][-5:], "rating": round(force.get(t, 0), 1)})
    rows.sort(key=lambda x: (-x["rating"], x["team"]))
    n = len(jeux)
    league = {"games": n, "ppg": round(sum(g["result"]["home"] + g["result"]["away"] for g, _ in jeux) / n, 1) if n else None,
              "home_w": _pct(dom, n), "fav_w": _pct(fav, n_fav), "over": _pct(ov, n_ov)}
    jours = collections.OrderedDict()
    for g, F in jeux:
        jours.setdefault(g["kickoff"][:10], []).append((g, F))   # date locale du coup d'envoi (heure de Bruxelles)
    return {"version": VERSION, "league": league, "rows": rows, "hints": _indices(rows),
            "recaps": {d: _recap(j) for d, j in jours.items()}}
