"""Comptes rendus écrits des matchs (AdSense, 29/10/2026) : /games/<id> (un match terminé), /weeks/<n> (les résultats
d'une semaine) et /games (toutes les semaines).

Suite de pages_franchises.py : pages rendues par le serveur, lisibles sans JavaScript, en anglais comme le site. Le
texte est écrit à partir du GameFeed du match (actions, probabilité de victoire, plan de jeu, blessures) et de sa
feuille de match (moteur/histoire.py) : scénario (remontée, dernière seconde, large victoire, surprise, match nul…),
déroulé, action décisive (le plus grand écart de probabilité de victoire), meilleurs joueurs, plan de jeu, ce que le
résultat change ; puis le résumé des points, les statistiques d'équipe et les feuilles individuelles. Les tournures
varient d'un match à l'autre (choix fixé par l'identifiant du match : la page ne change pas d'une visite à l'autre).

Rien d'un match pas encore terminé : serveur.py ne demande ces pages que pour des matchs « final ».
"""
import hashlib
import html
import re

import pages_franchises as pf

e = pf.e
PHASES = {"regular": "Regular season", "semifinal": "Conference final", "ai_bowl": "Grand Final"}
QUARTS = {1: "first quarter", 2: "second quarter", 3: "third quarter", 4: "fourth quarter"}


# ------------------------------------------------------------------ petits outils
def _choix(gid, cle, options):
    """Une tournure parmi plusieurs, toujours la même pour un match donné."""
    h = int(hashlib.sha1(f"{gid}:{cle}".encode()).hexdigest()[:8], 16)
    return options[h % len(options)]


def _horloge(sec):
    sec = max(0, int(round(sec or 0)))
    return f"{sec // 60}:{sec % 60:02d}"


def _quand(p):
    q = p.get("quarter") or 1
    if q > 4:
        return f"in overtime with {_horloge(p.get('clock_end'))} left"
    return f"with {_horloge(p.get('clock_end'))} left in the {QUARTS.get(q, 'game')}"


def _q(p):
    q = p.get("quarter") or 1
    return "OT" if q > 4 else f"Q{q}"


def _pct(x):
    return f"{round(100 * x)}%"


def _nom_court(nom):
    """« Cortex Foxes » → « Foxes » (le surnom, comme on dit dans un compte rendu)."""
    return (nom or "").split(" ", 1)[-1]


def _un(n):
    """« a 4-yard », « an 8-yard », « an 11-yard »."""
    return ("an " if str(n).startswith("8") or n in (11, 18) else "a ") + f"{n}-yard"


def _yds(p):
    m = re.search(r"(\d+)[ -]y", p.get("text") or "")
    return int(m.group(1)) if m else abs(int(p.get("gain") or 0))


def _action(p):
    """Une action racontée (texte HTML échappé), d'après ses champs plutôt que le texte du direct (parfois coupé)."""
    r, typ = p.get("result"), (p.get("call") or {}).get("type")
    pl = p.get("players") or {}
    porteur = ((pl.get("carrier") or {}).get("name"))
    passeur = ((pl.get("passer") or {}).get("name"))
    defenseur = ((pl.get("defender") or {}).get("name"))
    txt = p.get("text") or ""
    if r == "touchdown" and typ == "kickoff":
        m = re.match(r"(.+?) (\d+)-yd kickoff return", txt)
        if m:
            return f"{_un(int(m.group(2)))} kickoff return touchdown by {e(m.group(1))}"
    elif r == "touchdown" and "fumble" in txt:
        return f"a touchdown on a fumble recovered in the end zone"
    elif r == "touchdown" and typ == "pass" and porteur:
        return (f"{_un(_yds(p))} touchdown pass from {e(passeur)} to {e(porteur)}" if passeur
                else f"{_un(_yds(p))} touchdown catch by {e(porteur)}")
    elif r == "touchdown" and typ == "run" and porteur:
        return f"{_un(_yds(p))} touchdown run by {e(porteur)}"
    elif r == "field_goal_good":
        return f"{_un(_yds(p))} field goal" + (f" by {e(porteur)}" if porteur else "")
    elif r == "field_goal_missed":
        return f"a missed {_yds(p)}-yard field goal" + (f" by {e(porteur)}" if porteur else "")
    elif r == "safety":
        return "a safety" + (f", {e(passeur)} sacked in the end zone" if "Sacked" in txt and passeur else "")
    elif r == "interception":
        return f"an interception by {e(defenseur)}" + (f" off {e(passeur)}" if passeur else "") if defenseur else "an interception"
    elif r == "fumble_lost":
        return f"a fumble by {e(porteur)}, recovered by the defense" if porteur else "a lost fumble"
    elif r == "sack":
        return f"a sack by {e(defenseur)}" if defenseur else "a sack"
    elif r == "incomplete":
        return "an incomplete pass" + (" on fourth down" if p.get("down") == 4 else "")
    elif r == "complete" and porteur:
        return f"{_un(max(0, int(p.get('gain') or 0)))} catch by {e(porteur)}" + (" on fourth down" if p.get("down") == 4 else "")
    elif r == "run" and porteur:
        return f"{_un(max(0, int(p.get('gain') or 0)))} run by {e(porteur)}" + (" on fourth down" if p.get("down") == 4 else "")
    elif r == "two_point_good":
        return "a two-point conversion"
    elif r == "two_point_failed":
        return "a failed two-point conversion attempt"
    elif r == "pat_missed":
        return "a missed extra point"
    if "…" in txt:                                   # texte du direct coupé : rien plutôt qu'un bout de phrase
        return {"kickoff": "the kickoff", "punt": "a punt"}.get(typ, "the play")
    return e(txt)


def _verges(n):
    return f"{n} yard" + ("" if abs(n) == 1 else "s")


def _cap(t):
    return t[:1].upper() + t[1:]


def _pl(n, mot):
    return f"{n:g} {mot}" + ("" if n == 1 else "es" if mot.endswith("ch") else "s")


def _bilan(r):
    w, l, t = r
    return f"{w}-{l}" + (f"-{t}" if t else "")


# ------------------------------------------------------------------ analyse du match
def analyser(g, feed, fm):
    """Tout ce que le texte et les tableaux utilisent, calculé une fois."""
    P = feed.get("plays") or []
    G = feed.get("game") or {}
    cote = {"home": g["home"], "away": g["away"]}
    fin = (G.get("final_score") or (P[-1]["after"]["score"] if P else {"home": 0, "away": 0}))
    sh, sa = fin.get("home", 0), fin.get("away", 0)
    gagnant = "home" if sh > sa else "away" if sa > sh else None

    # points marqués (le côté dont le score monte), en regroupant la transformation avec son touchdown
    marques, avant = [], {"home": 0, "away": 0}
    for p in P:
        sc = (p.get("after") or {}).get("score") or avant
        for s in ("home", "away"):
            d = sc.get(s, 0) - avant.get(s, 0)
            if d > 0:
                if p["result"] in ("pat_good", "two_point_good") and marques and marques[-1]["side"] == s:
                    marques[-1]["pts"] += d
                    marques[-1]["extra"] = "2-pt conversion" if p["result"] == "two_point_good" else "extra point"
                    marques[-1]["score"] = dict(sc)
                else:
                    marques.append({"p": p, "side": s, "pts": d, "score": dict(sc), "extra": None})
        if p["result"] in ("pat_missed", "two_point_failed") and marques:
            marques[-1]["extra"] = "extra point missed" if p["result"] == "pat_missed" else "2-pt try failed"
        avant = dict(sc)

    # menées : changements, plus grande avance, score à la mi-temps, quand le gagnant a pris l'avance pour de bon
    changements, plus_grande, mene, decisif = 0, {"home": 0, "away": 0}, None, None
    mi_temps = {"home": 0, "away": 0}
    for m in marques:
        sc = m["score"]
        if (m["p"].get("quarter") or 1) <= 2:
            mi_temps = dict(sc)
        for s, o in (("home", "away"), ("away", "home")):
            plus_grande[s] = max(plus_grande[s], sc[s] - sc[o])
        n = "home" if sc["home"] > sc["away"] else "away" if sc["away"] > sc["home"] else None
        if n and n != mene:
            if mene is not None:
                changements += 1
            if n == gagnant:
                decisif = m
        if n is None and mene is not None and gagnant:
            decisif = None
        mene = n if n else (None if sc["home"] == sc["away"] else mene)
    if gagnant and decisif is None:
        decisif = next((m for m in reversed(marques) if m["side"] == gagnant), None)
    retard_max = plus_grande.get({"home": "away", "away": "home"}[gagnant], 0) if gagnant else 0

    # probabilité de victoire : avant le match, la plus basse du gagnant, la plus grande bascule
    cotes = G.get("pregame_odds") or g.get("odds") or {}
    p_dom = cotes.get("p_home")
    wp_prev, bascule, wp_min = p_dom if p_dom is not None else 0.5, None, 1.0
    for p in P:
        w = p.get("win_prob_home")
        if w is None:
            continue
        if gagnant:
            wp_min = min(wp_min, w if gagnant == "home" else 1 - w)
        d = w - wp_prev
        fin_du_temps = (p.get("after") or {}).get("status") == "final" or (
            (p.get("quarter") or 1) >= 4 and not p.get("clock_end"))
        pour = d if gagnant == "home" else -d if gagnant == "away" else abs(d)    # vers le gagnant seulement
        if not fin_du_temps and pour > 0 and (bascule is None or pour > bascule[4]):
            bascule = (p, d, wp_prev, w, pour)
        wp_prev = w

    # statistiques d'équipe
    stats = {s: {"plays": 0, "yds": 0, "pyd": 0, "ryd": 0, "to": 0, "sacked": 0, "top": 0.0, "pen": 0,
                 "d3": 0, "c3": 0, "d4": 0, "c4": 0, "cmp": 0, "att": 0} for s in ("home", "away")}
    for i, p in enumerate(P):
        s = p.get("offense")
        if s not in stats:
            continue
        T = stats[s]
        typ, r = (p.get("call") or {}).get("type"), p["result"]
        T["top"] += max(0, (p.get("clock_start") or 0) - (p.get("clock_end") or 0))
        if r == "penalty":
            T["pen"] += 1
            continue
        if typ in ("run", "pass"):
            T["plays"] += 1
            if r in ("interception", "fumble_lost"):
                T["to"] += 1
            if r in ("sack", "safety") and typ == "pass":
                T["sacked"] += 1
            if p.get("down") in (3, 4):
                k = "3" if p["down"] == 3 else "4"
                a = p.get("after") or {}
                ok = r == "touchdown" or (a.get("offense") == s and a.get("down") == 1 and r not in ("interception", "fumble_lost"))
                T["d" + k] += 1
                T["c" + k] += 1 if ok else 0
    for j in fm.get("joueurs", {}).values():
        s = "home" if j.get("team") == cote["home"] else "away" if j.get("team") == cote["away"] else None
        if s:
            for k in ("pyd", "ryd", "cmp", "att"):
                stats[s][k] += j.get(k, 0)
    for s in stats:
        stats[s]["yds"] = stats[s]["pyd"] + stats[s]["ryd"]

    # quatrièmes tentés
    quatriemes = [p for p in P if (p.get("fourth_down") or {}).get("choice") == "go"]
    longue = max((p for p in P if (p.get("call") or {}).get("type") in ("run", "pass")
                  and p["result"] in ("run", "complete", "touchdown")), key=lambda p: p.get("gain") or 0, default=None)
    return {"P": P, "G": G, "cote": cote, "sh": sh, "sa": sa, "gagnant": gagnant, "marques": marques,
            "changements": changements, "plus_grande": plus_grande, "mi_temps": mi_temps, "decisif": decisif,
            "retard_max": retard_max, "p_dom": p_dom, "wp_min": wp_min if gagnant else None, "bascule": bascule,
            "stats": stats, "quatriemes": quatriemes, "longue": longue,
            "ot": any((p.get("quarter") or 1) > 4 for p in P)}


def _note(j):
    """Note d'un joueur pour « joueur du match »."""
    return (j.get("pyd", 0) / 25 + j.get("ptd", 0) * 4 - j.get("pint", 0) * 2.5 + j.get("ryd", 0) / 10
            + j.get("rtd", 0) * 6 + j.get("yd", 0) / 10 + j.get("td", 0) * 6 + j.get("rec", 0) * 0.5
            + j.get("sk", 0) * 3 + j.get("int", 0) * 4.5 + j.get("tk", 0) * 0.4 + j.get("pd", 0) * 0.8
            + j.get("fgm", 0) * 2 - (j.get("fga", 0) - j.get("fgm", 0)) * 1.5 + j.get("krtd", 0) * 6)


def _ligne(j):
    """Ligne de statistiques d'un joueur, en anglais."""
    out = []
    if j.get("att"):
        out.append(f"{j['cmp']} of {j['att']} passing for {_verges(j['pyd'])}" + (f", {j['ptd']} TD" if j.get("ptd") else "")
                   + (f", {j['pint']} INT" if j.get("pint") else ""))
    if j.get("car"):
        out.append(f"{_pl(j['car'], 'carry').replace('carrys', 'carries')} for {_verges(j['ryd'])}" + (f" and {j['rtd']} TD" if j.get("rtd") else ""))
    if j.get("rec"):
        out.append(f"{_pl(j['rec'], 'catch')} for {_verges(j['yd'])}" + (f" and {j['td']} TD" if j.get("td") else ""))
    if j.get("sk") or j.get("int") or (j.get("tk", 0) >= 6 and not out):
        d = [f"{j['tk']} tackles"] if j.get("tk") else []
        if j.get("sk"):
            d.append(f"{j['sk']:g} sack{'s' if j['sk'] != 1 else ''}")
        if j.get("int"):
            d.append(f"{j['int']} interception{'s' if j['int'] > 1 else ''}")
        out.append(", ".join(d))
    if j.get("fga") and not out:
        out.append(f"{j['fgm']} of {j['fga']} field goals" + (f" (long {j['fg_lng']})" if j.get("fg_lng") else ""))
    return "; ".join(out)


# ------------------------------------------------------------------ le texte
def recit(g, A, teams, contexte):
    """Paragraphes du compte rendu (liste de chaînes HTML déjà échappées)."""
    gid = g["id"]
    H, V = A["cote"]["home"], A["cote"]["away"]
    nom = {"home": teams.get(H, {}).get("name", H), "away": teams.get(V, {}).get("name", V)}
    court = {s: _nom_court(nom[s]) for s in nom}
    sh, sa, gw = A["sh"], A["sa"], A["gagnant"]
    autre = {"home": "away", "away": "home"}
    marge = abs(sh - sa)
    total = sh + sa
    score_txt = f"{max(sh, sa)}-{min(sh, sa)}"
    phase = g.get("phase")
    ou = {"regular": f"in round {g.get('slot')} of Week {contexte['semaine']}",
          "semifinal": f"in the {contexte.get('conference') or 'conference'} final of Week {contexte['semaine']}",
          "ai_bowl": f"in the Grand Final of Week {contexte['semaine']}"}.get(phase, f"in Week {contexte['semaine']}")
    paras = []

    # 1. l'attaque : le scénario du match
    p_gw = None
    if gw and A["p_dom"] is not None:
        p_gw = A["p_dom"] if gw == "home" else 1 - A["p_dom"]
    dec = A["decisif"]
    tard = bool(dec and gw and ((dec["p"].get("quarter") or 1) > 4 or ((dec["p"].get("quarter") or 1) == 4
                                                                       and (dec["p"].get("clock_end") or 999) <= 45)))
    if gw is None:
        dern = A["marques"][-1] if A["marques"] else None
        if dern and (dern["p"].get("quarter") or 1) == 4 and (dern["p"].get("clock_end") or 999) <= 60:
            fin = f"The {e(court[dern['side']])} tied it with {_action(dern['p'])} {_quand(dern['p'])}."
        else:
            fin = "Neither offense could find the winning score before the final whistle."
        tete = _choix(gid, "nul", [
            f"Nothing could separate the {e(nom['home'])} and the {e(nom['away'])} {ou}: the game ended in a {sh}-{sa} tie. ",
            f"The {e(nom['home'])} and the {e(nom['away'])} shared the points {ou}, finishing level at {sh}-{sa}. ",
            f"It finished all square {ou}: {e(nom['home'])} {sh}, {e(nom['away'])} {sa}. "])
        paras.append(tete + fin)
    else:
        W, L = nom[gw], nom[autre[gw]]
        if tard:
            debut = _choix(gid, "tard", [
                f"The {e(W)} beat the {e(L)} {score_txt} {ou}, and they needed every second to do it.",
                f"It came down to the final moments {ou}: the {e(W)} edged the {e(L)} {score_txt}.",
                f"The {e(W)} snatched a {score_txt} win over the {e(L)} {ou} at the very end."])
            suite = f" The decisive score was {_action(dec['p'])} {_quand(dec['p'])}."
        elif A["retard_max"] >= 10 or (A["wp_min"] is not None and A["wp_min"] < 0.2):
            debut = _choix(gid, "remontee", [
                f"The {e(W)} came back to beat the {e(L)} {score_txt} {ou}.",
                f"Down but not out, the {e(W)} rallied past the {e(L)} for a {score_txt} win {ou}.",
                f"The {e(W)} turned the game around and beat the {e(L)} {score_txt} {ou}."])
            suite = (f" They trailed by as many as {A['retard_max']} points"
                     + (f", and their chance of winning dropped as low as {_pct(A['wp_min'])}." if A["wp_min"] is not None and A["wp_min"] < 0.35 else "."))
        elif marge >= 21:
            debut = _choix(gid, "large", [
                f"The {e(W)} overwhelmed the {e(L)} {score_txt} {ou}.",
                f"It was one-way traffic {ou}: the {e(W)} routed the {e(L)} {score_txt}.",
                f"The {e(W)} dominated from start to finish and beat the {e(L)} {score_txt} {ou}."])
            suite = f" The {e(court[gw])} led by as many as {A['plus_grande'][gw]} points."
        elif total <= 24:
            debut = _choix(gid, "defense", [
                f"Defense ruled {ou}, where the {e(W)} beat the {e(L)} {score_txt}.",
                f"Points were hard to come by {ou}: the {e(W)} outlasted the {e(L)} {score_txt}.",
                f"The {e(W)} won a low-scoring battle with the {e(L)}, {score_txt}, {ou}."])
            suite = f" The two offenses combined for just {total} points."
        elif total >= 60:
            debut = _choix(gid, "festival", [
                f"The {e(W)} won a shoot-out against the {e(L)}, {score_txt}, {ou}.",
                f"Neither defense had an answer {ou}, but the {e(W)} scored last and best, beating the {e(L)} {score_txt}.",
                f"The {e(W)} outscored the {e(L)} {score_txt} in a high-scoring game {ou}."])
            suite = f" The teams combined for {total} points" + (f" and {A['changements']} lead changes." if A["changements"] >= 2 else ".")
        elif marge <= 8:
            debut = _choix(gid, "serre", [
                f"The {e(W)} held off the {e(L)} {score_txt} {ou}.",
                f"The {e(W)} edged the {e(L)} {score_txt} in a one-score game {ou}.",
                f"In a tight contest {ou}, the {e(W)} beat the {e(L)} {score_txt}."])
            suite = (f" The lead changed hands {A['changements']} times." if A["changements"] >= 2
                     else f" The go-ahead score came {_quand(dec['p'])}." if dec else "")
        else:
            debut = _choix(gid, "net", [
                f"The {e(W)} beat the {e(L)} {score_txt} {ou}.",
                f"The {e(W)} earned a {score_txt} win over the {e(L)} {ou}.",
                f"The {e(W)} took care of the {e(L)} {score_txt} {ou}."])
            suite = f" They led by as many as {A['plus_grande'][gw]} points."
        if p_gw is not None and p_gw < 0.38:
            suite += _choix(gid, "surprise", [
                f" It was an upset: before kickoff the engine gave the {e(court[gw])} only a {_pct(p_gw)} chance of winning.",
                f" Few expected it: the pregame odds gave the {e(court[gw])} a {_pct(p_gw)} chance.",
                f" The result went against the odds, which had the {e(court[gw])} at {_pct(p_gw)} before kickoff."])
        elif p_gw is not None and p_gw > 0.68:
            suite += f" The {e(court[gw])} were clear favourites before kickoff ({_pct(p_gw)}), and they delivered."
        paras.append(debut + suite)

    # 2. le déroulé : premiers points, mi-temps, dernier quart
    M = A["marques"]
    if M:
        m0 = M[0]
        t = f"The {e(court[m0['side']])} opened the scoring with {_action(m0['p'])} {_quand(m0['p'])}. "
        mt = A["mi_temps"]
        if mt["home"] == mt["away"]:
            t += f"It was {mt['home']}-{mt['away']} at halftime. "
        else:
            s = "home" if mt["home"] > mt["away"] else "away"
            t += _choix(gid, "mitemps", [f"The {e(court[s])} led {max(mt.values())}-{min(mt.values())} at halftime. ",
                                          f"At the break the {e(court[s])} were up {max(mt.values())}-{min(mt.values())}. "])
        q4 = [m for m in M if (m["p"].get("quarter") or 1) >= 4]
        if q4:
            bouts = []
            for m in q4[:5]:
                sc = m["score"]
                bouts.append(f"{_action(m['p'])} for the {e(court[m['side']])} ({_horloge(m['p'].get('clock_end'))} left, "
                             f"{max(sc.values())}-{min(sc.values())})")
            t += (_choix(gid, "q4", ["The fourth quarter brought ", "Then came the fourth quarter: ", "In the fourth quarter: "])
                  + "; ".join(bouts) + ".")
        else:
            t += "Nobody scored in the fourth quarter."
        paras.append(t)

    # 3. l'action décisive (le plus grand écart de probabilité de victoire)
    b = A["bascule"]
    if b and abs(b[1]) >= 0.12:
        p, d, w0, w1, _ = b
        s = "home" if d > 0 else "away"
        avant_s, apres_s = (w0, w1) if s == "home" else (1 - w0, 1 - w1)
        paras.append(_choix(gid, "bascule", ["The biggest swing of the game came ", "The play that tilted the game came ",
                                             "The key moment arrived "])
                     + f"{_quand(p)}: {_action(p)}. It moved the {e(court[s])}' chance of winning from "
                       f"{_pct(avant_s)} to {_pct(apres_s)}.")

    # 4. les joueurs
    J = [j for j in contexte["joueurs"] if j.get("team") in (H, V)]
    if J:
        pool = [j for j in J if gw is None or j.get("team") == A["cote"][gw]]
        mvp = max(pool, key=_note)
        cote_mvp = "home" if mvp.get("team") == H else "away"
        t = (_choix(gid, "mvp", ["Player of the game: ", "The standout was ", "Top performer: "])
             + f"{e(mvp['name'])} ({e(mvp.get('pos', ''))}, {e(court[cote_mvp])}), with {e(_ligne(mvp) or 'a decisive performance')}. ")
        autres, vus = [], {id(mvp)}
        for s in ("home", "away"):
            eq = [j for j in J if j.get("team") == A["cote"][s] and j is not mvp]
            qb = max((j for j in eq if j.get("att")), key=lambda j: j["att"], default=None)
            ru = max((j for j in eq if j.get("car")), key=lambda j: j["ryd"], default=None)
            re_ = max((j for j in eq if j.get("rec")), key=lambda j: j["yd"], default=None)
            for j in (qb, ru, re_):
                if j and _note(j) >= 6 and id(j) not in vus:
                    vus.add(id(j))
                    autres.append(f"{e(j['name'])} ({e(court[s])}) had {e(_ligne(j))}")
        if autres:
            t += "Elsewhere, " + "; ".join(autres[:4]) + "."
        paras.append(t)

    # 5. le plan de jeu des coordinateurs
    gp = A["G"].get("gameplan") or {}
    bouts = []
    for s in ("home", "away"):
        o = (gp.get(s) or {}).get("offense") or {}
        d = (gp.get(s) or {}).get("defense") or {}
        if o.get("summary") or d.get("summary"):
            x = f"the {e(court[s])}' game plan was " + "; ".join(
                f"{k}: {e(v)}" for k, v in (("on offense", o.get("summary")), ("on defense", d.get("summary"))) if v)
            cible = o.get("focus")
            j = next((j for j in J if j.get("name") == cible and j.get("team") == A["cote"][s]), None) if cible else None
            if j and (j.get("rec") or j.get("car")):
                x += f" ({e(cible)} finished with {e(_ligne(j))})"
            bouts.append(x)
    if bouts:
        paras.append("Before kickoff, " + ". Meanwhile, ".join(bouts) + ".")

    # 6. ce que ça change : bilans, qualification, titre ; quatrièmes tentés, blessures
    t = ""
    if phase == "regular" and contexte.get("bilans"):
        bl = contexte["bilans"]
        t += (f"The {e(court['home'])} move to {_bilan(bl['home'])} and the {e(court['away'])} to {_bilan(bl['away'])} "
              f"this week. ")
    elif phase == "semifinal" and gw:
        t += f"The {e(court[gw])} advance to the Grand Final; the {e(court[autre[gw]])}' week is over. "
    elif phase == "ai_bowl" and gw:
        t += f"The {e(nom[gw])} are the champions of Week {contexte['semaine']}. "
    Q = A["quatriemes"]
    if Q:
        ok = sum(1 for p in Q if p["result"] not in ("punt", "incomplete", "interception", "fumble_lost", "sack")
                 and ((p.get("after") or {}).get("offense") == p.get("offense") or p["result"] == "touchdown"))
        fois = "once" if len(Q) == 1 else "twice" if len(Q) == 2 else f"{len(Q)} times"
        t += (f"The coaches went for it on fourth down {fois}"
              + (", without success. " if ok == 0 else ", and it worked. " if ok == len(Q) == 1 else f", converting {ok}. "))
    bl = [b for b in A["G"].get("injuries") or [] if b.get("severity") != "minor" or b.get("weeks")]
    if bl:
        t += "Injuries: " + "; ".join(f"{e(b['name'])} ({e(b.get('pos', ''))}, {e(court.get(b.get('team'), ''))}) "
                                      f"{e(b.get('part', ''))} injury" + (f", out {b['weeks']} week{'s' if b['weeks'] > 1 else ''}" if b.get("weeks") else "")
                                      for b in bl[:3]) + "."
    if t:
        paras.append(t.strip())
    return paras


# ------------------------------------------------------------------ les pages
def _lien_equipe(a, teams):
    t = teams.get(a) or {}
    return f'<a href="/teams/{pf.slug(t.get("name", a))}">{e(t.get("name", a))}</a>'


def titre_match(g, sh, sa, teams):
    H, V = teams.get(g["home"], {}).get("name", g["home"]), teams.get(g["away"], {}).get("name", g["away"])
    if sh == sa:
        return f"{H} {sh}, {V} {sa}"
    w, l = (H, V) if sh > sa else (V, H)
    return f"{w} {max(sh, sa)}, {l} {min(sh, sa)}"


def page_match(g, feed, fm, teams, contexte, origine, tete=""):
    """/games/<id> : le compte rendu écrit d'un match terminé."""
    A = analyser(g, feed, fm)
    contexte = dict(contexte, joueurs=list((fm.get("joueurs") or {}).values()))
    H, V = g["home"], g["away"]
    nom = {"home": teams.get(H, {}).get("name", H), "away": teams.get(V, {}).get("name", V)}
    court = {s: _nom_court(nom[s]) for s in nom}
    sem = contexte["semaine"]
    titre = titre_match(g, A["sh"], A["sa"], teams)
    phase = PHASES.get(g.get("phase"), "")
    etiquette = f"Week {sem} · {phase}" + (f" · round {g.get('slot')}" if g.get("phase") == "regular" else "")
    parts = [f'<a class="back" href="/">← Back to Snapline</a><a class="back" href="/weeks/{sem}">Week {sem} results</a>',
             f"<h1>{e(titre)}</h1>", f'<p class="lead">{e(etiquette)} · {e(contexte.get("date", ""))}</p>']
    # tableau de marque par quart
    qs = sorted({(p.get("quarter") or 1) for p in A["P"]} | {1, 2, 3, 4})
    par_q = {s: {q: 0 for q in qs} for s in ("home", "away")}
    for m in A["marques"]:
        par_q[m["side"]][m["p"].get("quarter") or 1] += m["pts"]
    tete_q = "".join(f'<th class="n">{"OT" if q > 4 else q}</th>' for q in qs)
    lignes = "".join(f'<tr><td style="--tc:{pf.COULEURS.get(A["cote"][s], "#1E5C78")}"><span class="badge sm">{e(A["cote"][s])}</span> '
                     f'{_lien_equipe(A["cote"][s], teams)}</td>'
                     + "".join(f'<td class="n">{par_q[s][q]}</td>' for q in qs)
                     + f'<td class="n"><b>{A["sh"] if s == "home" else A["sa"]}</b></td></tr>' for s in ("away", "home"))
    parts.append(f'<section><table><thead><tr><th>Team</th>{tete_q}<th class="n">Final</th></tr></thead>'
                 f"<tbody>{lignes}</tbody></table></section>")
    paras = recit(g, A, teams, contexte)
    parts.append("<section><h2>Game recap</h2>" + "".join(f"<p>{p}</p>" for p in paras) + "</section>")
    # résumé des points
    if A["marques"]:
        li = "".join(f"<tr><td>{_q(m['p'])} {_horloge(m['p'].get('clock_end'))}</td><td>{e(court[m['side']])}</td>"
                     f"<td>{_cap(_action(m['p']))}" + (f" ({e(m['extra'])})" if m["extra"] else "") + "</td>"
                     f"<td class=\"n\">{m['score']['away']}-{m['score']['home']}</td></tr>" for m in A["marques"])
        parts.append("<section><h2>Scoring summary</h2><table><thead><tr><th>Time</th><th>Team</th><th>Play</th>"
                     f'<th class="n">{e(V)}-{e(H)}</th></tr></thead><tbody>{li}</tbody></table></section>')
    # statistiques d'équipe
    S = A["stats"]

    def taux(s, k):
        return f"{S[s]['c' + k]} of {S[s]['d' + k]}" if S[s]["d" + k] else "—"
    rangs = [("Total yards", lambda s: S[s]["yds"]), ("Passing yards", lambda s: S[s]["pyd"]),
             ("Rushing yards", lambda s: S[s]["ryd"]), ("Completions", lambda s: f"{S[s]['cmp']} of {S[s]['att']}"),
             ("Offensive plays", lambda s: S[s]["plays"]), ("Third downs", lambda s: taux(s, "3")),
             ("Fourth downs", lambda s: taux(s, "4")), ("Turnovers", lambda s: S[s]["to"]),
             ("Sacks allowed", lambda s: S[s]["sacked"]),
             ("Time of possession", lambda s: _horloge(S[s]["top"]))]
    li = "".join(f'<tr><td>{lab}</td><td class="n">{f("away")}</td><td class="n">{f("home")}</td></tr>' for lab, f in rangs)
    parts.append(f'<section><h2>Team stats</h2><table><thead><tr><th></th><th class="n">{e(V)}</th><th class="n">{e(H)}</th>'
                 f"</tr></thead><tbody>{li}</tbody></table></section>")
    # feuilles individuelles
    J = contexte["joueurs"]
    for s in ("away", "home"):
        eq = [j for j in J if j.get("team") == A["cote"][s]]
        if not eq:
            continue
        blocs = []
        for lab, filtre, cols in (
                ("Passing", lambda j: j.get("att"), (("C/ATT", lambda j: f"{j['cmp']}/{j['att']}"), ("YDS", "pyd"), ("TD", "ptd"), ("INT", "pint"))),
                ("Rushing", lambda j: j.get("car"), (("CAR", "car"), ("YDS", "ryd"), ("TD", "rtd"), ("LNG", "lng"))),
                ("Receiving", lambda j: j.get("rec"), (("REC", "rec"), ("YDS", "yd"), ("TD", "td"), ("TGT", "tgt"))),
                ("Defense", lambda j: j.get("tk") or j.get("sk") or j.get("int"), (("TK", "tk"), ("SK", "sk"), ("INT", "int"), ("PD", "pd"))),
                ("Kicking", lambda j: j.get("fga") or j.get("xpa"), (("FG", lambda j: f"{j['fgm']}/{j['fga']}"), ("LNG", "fg_lng"), ("XP", lambda j: f"{j['xpm']}/{j['xpa']}")))):
            ls = [j for j in eq if filtre(j)]
            if not ls:
                continue
            tri = {"Passing": "att", "Rushing": "ryd", "Receiving": "yd", "Kicking": "fga"}.get(lab)
            ls.sort(key=lambda j: -(j.get(tri, 0) if tri else j.get("tk", 0) + 4 * j.get("sk", 0) + 5 * j.get("int", 0)))
            ls = ls[:6 if lab == "Defense" else 4]
            th = "".join(f'<th class="n">{c}</th>' for c, _ in cols)
            td = "".join("<tr><td>" + e(j["name"]) + "</td>" + "".join(
                f'<td class="n">{e(str(v(j) if callable(v) else (round(j.get(v, 0), 1) if isinstance(j.get(v), float) else j.get(v, 0))))}</td>'
                for _, v in cols) + "</tr>" for j in ls)
            blocs.append(f"<h3>{lab}</h3><table><thead><tr><th>Player</th>{th}</tr></thead><tbody>{td}</tbody></table>")
        if blocs:
            parts.append(f'<section><h2>{e(nom[s])} box score</h2>{"".join(blocs)}</section>')
    parts.append(f'<section><h2>Watch the replay</h2><p>Every play of this game can be replayed on the big screen, with '
                 f'the play calls, the win probability and the commentary: <a href="/?watch={e(g["id"])}">replay '
                 f'{e(titre)} on Snapline</a>. More about the teams: {_lien_equipe(H, teams)} · {_lien_equipe(V, teams)}.</p></section>')
    desc = (paras[0] if paras else titre)
    desc = re.sub(r"<[^>]+>", "", desc)
    desc = html.unescape(desc)[:300]
    return pf._page(f"{titre} · Week {sem} {phase} recap · Snapline", desc, f"/games/{g['id']}",
                    "\n".join(parts), origine, tete)


def ligne_resultat(g, teams):
    """Une ligne de résultat avec lien vers le compte rendu."""
    r = g.get("result") or {}
    return (f'<li><a href="/games/{e(g["id"])}">{e(titre_match(g, r.get("home", 0), r.get("away", 0), teams))}</a></li>')


def page_semaine(sem, jeux, total, teams, resume, origine, tete=""):
    """/weeks/<n> : les résultats d'une semaine (matchs terminés seulement), par tour, avec liens vers les comptes rendus.
    jeux : matchs terminés (entrées du calendrier, avec « result ») ; total : nombre de matchs de la semaine ;
    resume : {"champion", "runner_up", "best_record", "leaders"} de la saison (semaine terminée) ou None."""
    parts = ['<a class="back" href="/">← Back to Snapline</a><a class="back" href="/games">All weeks</a>',
             f"<h1>Week {sem} results</h1>"]
    reste = total - len(jeux)
    parts.append(f'<p class="lead">Every Snapline week is a full season of American football: a regular season in which '
                 f"each of the 24 franchises plays all the others once, two conference finals and the Grand Final. "
                 + (f"{len(jeux)} of {total} games have been played so far; the others are still to come."
                    if reste > 0 else f"All {total} games have been played.") + "</p>")
    if resume and resume.get("champion"):
        c, ru = resume["champion"], resume.get("runner_up")
        t = f"<p>The {_lien_equipe(c, teams)} won the Grand Final" + (f" against the {_lien_equipe(ru, teams)}" if ru else "") + ". "
        br = resume.get("best_record")
        if br:
            t += (f"The best regular-season record belonged to the {_lien_equipe(br['team'], teams)} "
                  f"({_bilan((br['w'], br['l'], br.get('t', 0)))}). ")
        t += "</p>"
        ld = resume.get("leaders") or {}
        noms = dict(pf_categories())
        li = "".join(f"<li><b>{e(noms[k])}:</b> {e(v['name'])} ({e(teams.get(v['team'], {}).get('name', v['team']))}), "
                     f"{e(str(round(v['value'], 1) if isinstance(v['value'], float) else v['value']))}</li>"
                     for k, v in ld.items() if k in noms)
        parts.append(f"<section><h2>Season summary</h2>{t}" + (f"<h3>Season leaders</h3><ul>{li}</ul>" if li else "") + "</section>")
    po = [g for g in jeux if g.get("phase") != "regular"]
    if po:
        po.sort(key=lambda g: g["ko"], reverse=True)
        parts.append("<section><h2>Playoffs</h2><ul>" + "".join(
            f"{ligne_resultat(g, teams)[:-5]} · {PHASES.get(g['phase'], '')}</li>" for g in po) + "</ul></section>")
    tours = {}
    for g in jeux:
        if g.get("phase") == "regular":
            tours.setdefault(g.get("slot"), []).append(g)
    for k in sorted(tours, reverse=True):
        parts.append(f"<section><h2>Round {k}</h2><ul>" + "".join(ligne_resultat(g, teams) for g in tours[k]) + "</ul></section>")
    return pf._page(f"Week {sem} results and game recaps · Snapline",
                    f"Results and written recaps of every game of Week {sem} on Snapline: regular season, conference "
                    "finals and the Grand Final of simulated American football.", f"/weeks/{sem}", "\n".join(parts), origine, tete)


def page_index(semaines, derniers, teams, origine, tete=""):
    """/games : les semaines (avec leur champion) et les derniers matchs terminés."""
    parts = ['<a class="back" href="/">← Back to Snapline</a><a class="back" href="/teams">All franchises</a>',
             "<h1>Results and game recaps</h1>",
             '<p class="lead">Every game played on Snapline gets a written recap: how it was won, the play that swung it, '
             "the best players, the coaches' game plans, the scoring summary and the full box score.</p>"]
    if derniers:
        parts.append("<section><h2>Latest games</h2><ul>" + "".join(ligne_resultat(g, teams) for g in derniers) + "</ul></section>")
    li = "".join(f'<li><a href="/weeks/{s["index"]}">Week {s["index"]}</a>'
                 + (f" · champion: {e(teams.get(s['champion'], {}).get('name', s['champion']))}" if s.get("champion") else
                    f" · {s['played']} of {s['total']} games played")
                 + "</li>" for s in semaines)
    parts.append(f"<section><h2>Weeks</h2><ul>{li}</ul></section>")
    return pf._page("Results and game recaps · Snapline", "Written recaps, scoring summaries and box scores of every "
                    "Snapline game: simulated American football played live by AI-coached teams.", "/games",
                    "\n".join(parts), origine, tete)


def pf_categories():
    from moteur.histoire import CATEGORIES
    return CATEGORIES
