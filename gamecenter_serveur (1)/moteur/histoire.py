"""Histoire de la ligue, records et stats de carrière (bloc 2, étape 5).

Tout se calcule à partir de ce qui est déjà enregistré (week.json et GameFeed de chaque semaine) : rien ne change dans le
moteur ni dans le calcul du samedi. Chaque semaine est une saison complète (saison régulière, demi-finales, Grand Final).

  feuille_de_match(feed) : statistiques d'un match par joueur (mêmes règles que le Match centre du site, computeStats),
                           plus longue action, plus long field goal, plus long retour de coup d'envoi ;
  histoire(semaines)     : saisons, franchises, records (un match, une saison, une carrière), carrières.

Un joueur de carrière = identifiant + nom : une recrue reprend l'identifiant (la place) du retraité qu'elle remplace
(moteur/developpement.py), le nom les sépare. Transformations et retours de coups d'envoi : comptés depuis qu'ils
existent (semaine du 19/10/2026), sans revenir sur les saisons précédentes.
"""
import re

VERSION = "histoire-1"

_FG_YDS = re.compile(r"(\d+)\s*yds", re.I)
_CREDIT = {"TACKLE": "tk", "SACK": "sk", "INTERCEPTION": "int", "PASS_DEFENDED": "pd"}   # fumbles provoqués : absents des GameFeed

# statistiques d'un joueur (clés courtes, celles du site) : passe, course, réception, défense, coups de pied, retours
CHAMPS = ("cmp", "att", "pyd", "ptd", "pint", "car", "ryd", "rtd", "tgt", "rec", "yd", "td",
          "tk", "sk", "int", "pd", "fgm", "fga", "xpm", "xpa", "kr", "kry", "krtd")

# catégories de records et de classements de carrière : clé, libellé (anglais, comme le site)
CATEGORIES = (("pyd", "Passing yards"), ("ptd", "Passing TD"), ("ryd", "Rushing yards"), ("rtd", "Rushing TD"),
              ("yd", "Receiving yards"), ("rec", "Receptions"), ("td", "Receiving TD"), ("tk", "Tackles"),
              ("sk", "Sacks"), ("int", "Interceptions"), ("fgm", "Field goals"), ("kry", "Kick return yards"))
# plus longues actions d'un match (record « un match » seulement)
LONGUES = (("lng", "Longest play"), ("fg_lng", "Longest field goal"), ("kr_lng", "Longest kick return"))
# catégorie qui compte pour le rang de carrière d'un poste (la même que le rang de la semaine sur la fiche joueur)
RANG_POSTE = {"QB": "pyd", "RB": "ryd", "WR": "yd", "TE": "yd", "EDGE": "sk", "DT": "sk", "LB": "tk", "CB": "tk",
              "S": "tk", "K": "fgm"}
TOP = 10


def _n(x, d=0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def feuille_de_match(feed):
    """Statistiques d'un match (GameFeed complet). Mêmes règles que computeStatsNow (site) :
    passe (sack à part), course, réception, crédits défensifs (par nom, chez la défense), field goals (le kicker est le
    porteur), point après touchdown (la tentative à 2 points ne compte ni yards ni touchdown), retours de coups d'envoi.
    Renvoie {"home", "away", "score": {"home", "away"}, "joueurs": {clé: {...}}, "longues": {...}}."""
    g = feed["game"]
    roster = {s: {r["id"]: r for r in (g.get(s) or {}).get("roster") or []} for s in ("home", "away")}
    par_nom = {s: {r["name"]: r for r in roster[s].values()} for s in ("home", "away")}
    equipe = {s: (g.get(s) or {}).get("abbr") for s in ("home", "away")}
    J = {}

    def qui(side, pid, nom):
        r = (pid and roster[side].get(pid)) or par_nom[side].get(nom) or {}
        pid = r.get("id") or pid
        nom = nom or r.get("name")
        if not pid and not nom:
            return None
        k = (pid or "") + "|" + (nom or "")
        if k not in J:
            J[k] = dict({c: 0 for c in CHAMPS}, id=pid, name=nom, team=equipe[side], pos=r.get("pos") or "",
                        lng=0, fg_lng=0, kr_lng=0)
        return J[k]

    for P in feed["plays"]:
        o = P.get("offense")
        if o not in ("home", "away"):
            continue
        ds = "away" if o == "home" else "home"
        t = (P.get("call") or {}).get("type")
        r = (P.get("safety_via") or "run") if P.get("result") == "safety" else P.get("result")
        gain = int(round(_n(P.get("gain"))))
        pp = P.get("players") or {}
        car, pas, df = pp.get("carrier") or {}, pp.get("passer"), pp.get("defender") or {}
        if P.get("conversion"):
            c = P["conversion"]
            if c.get("choice") == "extra_point":
                k = qui(o, car.get("id"), car.get("name"))
                if k:
                    k["xpa"] += 1
                    k["xpm"] += 1 if c.get("good") else 0
            continue
        if t == "pass":
            q = qui(o, (pas or {}).get("id"), (pas or {}).get("name") or "QB")
            if r != "sack":
                pris = r in ("complete", "touchdown", "fumble_lost")
                q["att"] += 1
                if pris:
                    q["cmp"] += 1
                    q["pyd"] += gain
                if r == "touchdown":
                    q["ptd"] += 1
                if r == "interception":
                    q["pint"] += 1
                w = qui(o, car.get("id"), car.get("name"))
                if w:
                    w["tgt"] += 1
                    if pris:
                        w["rec"] += 1
                        w["yd"] += gain
                        w["lng"] = max(w["lng"], gain)
                    if r == "touchdown":
                        w["td"] += 1
        elif t == "run":
            b = qui(o, car.get("id"), car.get("name"))
            if b:
                b["car"] += 1
                b["ryd"] += gain
                b["lng"] = max(b["lng"], gain)
                if r == "touchdown":
                    b["rtd"] += 1
        elif t == "field_goal":
            k = qui(o, car.get("id"), car.get("name"))
            if k:
                k["fga"] += 1
                if r == "field_goal_good":
                    k["fgm"] += 1
                    m = _FG_YDS.search(P.get("text") or "")
                    if m:
                        k["fg_lng"] = max(k["fg_lng"], int(m.group(1)))
        if df.get("name") and df.get("credit") in _CREDIT:
            x = qui(ds, None, df["name"])
            x[_CREDIT[df["credit"]]] += 1
        kr = P.get("kick_return")
        if t == "kickoff" and kr and not kr.get("touchback"):
            b = qui(o, car.get("id"), car.get("name"))
            if b:
                y = int(_n(kr.get("return")))
                b["kr"] += 1
                b["kry"] += y
                b["kr_lng"] = max(b["kr_lng"], y)
                b["krtd"] += 1 if kr.get("td") else 0
    fs = g.get("final_score") or (feed["plays"][-1].get("after") or {}).get("score") or {}
    return {"home": equipe["home"], "away": equipe["away"],
            "score": {"home": int(_n(fs.get("home"))), "away": int(_n(fs.get("away")))}, "joueurs": J}


def _cle(j):
    return (j.get("id") or "") + "|" + (j.get("name") or "")


def _ajoute(dst, src):
    for c in CHAMPS:
        dst[c] += src[c]


def _top(lignes, cle, n=TOP):
    lignes = [x for x in lignes if x.get(cle, 0) > 0]
    lignes.sort(key=lambda x: (-x[cle], x.get("week") or 0, x.get("name") or ""))
    return lignes[:n]


def histoire(semaines):
    """semaines : [{"index", "start", "doc" (week.json), "matchs": [(entrée du calendrier, feuille_de_match)],
    "terminee": bool (Grand Final jouée)}], dans l'ordre. Seuls les matchs donnés comptent (matchs terminés).

    Renvoie {"version", "seasons", "franchises", "records": {"game", "season", "career"}, "careers"}."""
    saisons, franchises, carrieres = [], {}, {}
    rec_match = {c: [] for c, _ in CATEGORIES + LONGUES}
    rec_equipe = {"pts": [], "margin": [], "total": []}
    rec_saison = {c: [] for c, _ in CATEGORIES}
    rec_saison_eq = {"pts": [], "wins": []}

    for S in semaines:
        doc, idx = S["doc"], S["index"]
        equipes = doc.get("teams") or {}
        par_joueur, bilans = {}, {a: {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0} for a in equipes}
        finale = None
        for g, F in S["matchs"]:
            h, a, sc = F["home"], F["away"], F["score"]
            ph = g.get("phase")
            ctx = {"week": idx, "game": g["id"], "phase": ph}
            for j in F["joueurs"].values():
                adv = a if j["team"] == h else h
                q = par_joueur.setdefault(_cle(j), dict({c: 0 for c in CHAMPS}, id=j["id"], name=j["name"],
                                                        team=j["team"], pos=j["pos"], games=set()))
                _ajoute(q, j)
                q["games"].add(g["id"])
                for c, _ in CATEGORIES + LONGUES:
                    if j.get(c, 0) > 0:
                        rec_match[c].append(dict(ctx, id=j["id"], name=j["name"], team=j["team"], opp=adv, value=j[c]))
            for s, o in (("home", "away"), ("away", "home")):
                t = F[s]
                rec_equipe["pts"].append(dict(ctx, team=t, opp=F[o], value=sc[s], score=f"{sc[s]}-{sc[o]}"))
            m = abs(sc["home"] - sc["away"])
            gagnant = h if sc["home"] >= sc["away"] else a
            perdant = a if gagnant == h else h
            sco = f"{max(sc.values())}-{min(sc.values())}"
            rec_equipe["margin"].append(dict(ctx, team=gagnant, opp=perdant, value=m, score=sco))
            rec_equipe["total"].append(dict(ctx, team=h, opp=a, value=sc["home"] + sc["away"], score=f"{sc['away']}-{sc['home']}"))
            if ph == "regular":
                for s, o in (("home", "away"), ("away", "home")):
                    b = bilans.setdefault(F[s], {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0})
                    b["pf"] += sc[s]
                    b["pa"] += sc[o]
                    b["w" if sc[s] > sc[o] else "l" if sc[s] < sc[o] else "t"] += 1
            if ph == "ai_bowl":
                finale = {"home": h, "away": a, "score": sc, "game": g["id"]}

        # meilleur bilan de la saison régulière (matchs terminés) et leaders de la saison
        def pct(b):
            n = b["w"] + b["l"] + b["t"]
            return (b["w"] + 0.5 * b["t"]) / n if n else 0.0
        joues = {k: b for k, b in bilans.items() if b["w"] + b["l"] + b["t"]}
        meilleur = None
        if joues:
            k = max(sorted(joues), key=lambda a: (pct(joues[a]), joues[a]["pf"] - joues[a]["pa"]))
            meilleur = dict(team=k, **{x: joues[k][x] for x in ("w", "l", "t")})
        leaders = {}
        lignes = list(par_joueur.values())
        for c, _ in CATEGORIES:
            top = _top([dict(id=x["id"], name=x["name"], team=x["team"], value=x[c]) for x in lignes], "value", 1)
            if top:
                leaders[c] = top[0]
        semis = [g for g, _ in S["matchs"] if g.get("phase") == "semifinal"]
        termine = bool(S.get("terminee"))
        saisons.append({"week": idx, "start": S["start"], "teams": len(equipes), "complete": termine,
                        "games": len(S["matchs"]), "games_total": len(doc.get("schedule") or []),
                        "champion": doc.get("champion") if termine else None,
                        "runner_up": doc.get("runner_up") if termine else None,
                        "final": finale if termine else None, "best_record": meilleur, "leaders": leaders})

        # franchises : bilans, titres, finales, playoffs
        for t, b in bilans.items():
            fr = franchises.setdefault(t, {"team": t, "seasons": 0, "w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0,
                                           "playoffs": 0, "finals": 0, "titles": 0, "title_weeks": []})
            if b["w"] + b["l"] + b["t"]:
                fr["seasons"] += 1
            for x in ("w", "l", "t", "pf", "pa"):
                fr[x] += b[x]
        for g in semis:
            for s in ("home", "away"):
                if g.get(s) in franchises:
                    franchises[g[s]]["playoffs"] += 1
        if termine:
            for t in (doc.get("champion"), doc.get("runner_up")):
                if t in franchises:
                    franchises[t]["finals"] += 1
            if doc.get("champion") in franchises:
                franchises[doc["champion"]]["titles"] += 1
                franchises[doc["champion"]]["title_weeks"].append(idx)
        for t, b in bilans.items():
            if b["w"] + b["l"] + b["t"]:
                rec_saison_eq["pts"].append({"week": idx, "team": t, "value": b["pf"], "complete": termine})
                rec_saison_eq["wins"].append({"week": idx, "team": t, "value": b["w"], "record": f"{b['w']}-{b['l']}" + (f"-{b['t']}" if b["t"] else ""), "complete": termine})

        # saisons des joueurs : records d'une saison, carrières
        for k, x in par_joueur.items():
            ligne = dict({c: x[c] for c in CHAMPS}, week=idx, team=x["team"], games=len(x["games"]))
            for c, _ in CATEGORIES:
                if x[c] > 0:
                    rec_saison[c].append({"week": idx, "id": x["id"], "name": x["name"], "team": x["team"],
                                          "value": x[c], "complete": termine})
            cr = carrieres.setdefault(k, {"id": x["id"], "name": x["name"], "pos": x["pos"], "seasons": []})
            cr["pos"] = x["pos"] or cr["pos"]
            cr["seasons"].append(ligne)

    # carrières : totaux, classements de toujours
    for cr in carrieres.values():
        tot = {c: sum(s[c] for s in cr["seasons"]) for c in CHAMPS}
        tot["games"] = sum(s["games"] for s in cr["seasons"])
        cr["total"] = tot
        cr["team"] = cr["seasons"][-1]["team"]
    rec_carriere = {}
    for c, _ in CATEGORIES:
        lignes = [{"id": x["id"], "name": x["name"], "team": x["team"], "pos": x["pos"], "value": x["total"][c],
                   "seasons": len(x["seasons"])} for x in carrieres.values()]
        lignes = [x for x in lignes if x["value"] > 0]
        lignes.sort(key=lambda x: (-x["value"], x["name"] or ""))
        for i, x in enumerate(lignes):
            k = (x["id"] or "") + "|" + (x["name"] or "")
            carrieres[k].setdefault("ranks", {})[c] = [i + 1, len(lignes)]
        rec_carriere[c] = lignes[:TOP]

    return {"version": VERSION,
            "seasons": saisons,
            "franchises": sorted(franchises.values(), key=lambda f: (-f["titles"], -f["finals"], -f["w"], f["team"])),
            "records": {"labels": dict(CATEGORIES + LONGUES + (("pts", "Points by a team"), ("margin", "Winning margin"),
                                                                ("total", "Combined points"), ("wins", "Wins"))),
                        "game": {"players": {c: _top(v, "value") for c, v in rec_match.items()},
                                 "teams": {c: _top(v, "value") for c, v in rec_equipe.items()}},
                        "season": {"players": {c: _top(v, "value") for c, v in rec_saison.items()},
                                   "teams": {c: _top(v, "value") for c, v in rec_saison_eq.items()}},
                        "career": rec_carriere},
            "careers": carrieres}


def carriere(h, pid):
    """Les carrières d'une place (identifiant) : le joueur actuel et ceux qui l'ont tenue avant (retraités)."""
    out = [dict(c, rank_key=RANG_POSTE.get(c["pos"])) for c in h["careers"].values() if c["id"] == pid]
    return sorted(out, key=lambda c: c["seasons"][-1]["week"], reverse=True)
