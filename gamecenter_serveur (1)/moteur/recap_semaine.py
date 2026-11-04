"""« Week in review » : l'émission du week-end (README section 92, 04/11/2026).

Le samedi (et le dimanche avant la Grand Final, et après elle), quand aucun match n'est en direct, le tableau du site
joue une playlist d'actions de la semaine, chacune précédée d'un carton titre. Ce module compose la playlist à partir
des seuls matchs TERMINÉS (le serveur ne passe que ceux-là) : jamais une action d'un match en cours ou à venir.

Rubriques, dans l'ordre (une rubrique sans matière est omise) :
  final      Grand Final : ses 4 plus belles actions, dans l'ordre du match (après la finale)
  semis      Semi-finals : les 3 plus belles de chaque demi-finale
  plays      Plays of the week : les 8 plus belles actions (2 au plus par match)
  game       Game of the week : le match le plus spectaculaire, ses 3 plus belles actions
  comebacks  Comebacks : 3 remontées au plus (le vainqueur est tombé à 15 % de chances ou moins), l'action qui a le
             plus fait remonter le vainqueur dans la seconde mi-temps
  takeaways  Takeaways : les 4 plus belles interceptions et fumbles récupérés
  shootouts  Shootouts : les 3 matchs aux plus gros totaux, le plus beau touchdown de chacun
  injuries   Injury report : 3 blessures au plus, absences de plusieurs semaines d'abord (QB, puis RB / WR / TE)
  franchise  Franchise of the week (même ordre fixe que la vidéo, outils/video/choisir.py) : ses 2 plus belles actions

La note d'une action (interet) et celle d'un match (spectacle) sont celles des vidéos (outils/video/choisir.py, que
l'image du serveur n'embarque pas) : moteur/tests/test_recap_semaine.py vérifie qu'elles restent identiques.
Textes en anglais, comme le site. Rien d'aléatoire : les mêmes matchs donnent toujours la même playlist.
"""
from datetime import datetime

VERSION = "recap-semaine-1"
N_PLAYS, PAR_MATCH = 8, 2
N_GAME, N_SEMI, N_FINAL = 3, 3, 4
N_COMEBACK, SEUIL_COMEBACK = 3, 0.15
N_TAKEAWAYS, N_SHOOTOUTS, N_INJURIES, N_FRANCHISE = 4, 3, 3, 2
_POSTE = {"QB": 0, "RB": 1, "WR": 1, "TE": 1}


# ------------------------------------------------------------------ notes (identiques à outils/video/choisir.py)
def _retour_td(p):
    return bool((p.get("kick_return") or {}).get("td") or (p.get("punt_return") or {}).get("td"))


def _wp_avant(feed, i):
    if i > 0:
        return feed["plays"][i - 1].get("win_prob_home")
    po = feed["game"].get("pregame_odds") or {}
    return po.get("p_home", 0.5)


def _fin_de_match(P):
    return (P.get("quarter") or 0) >= 5 or ((P.get("quarter") or 0) == 4 and (P.get("clock_start") or 0) <= 120)


def interet(feed, i):
    """(note, raison) d'une action — copie de outils/video/choisir.interet."""
    P = feed["plays"][i]
    t = (P.get("call") or {}).get("type")
    r = P.get("result")
    wa, wb = _wp_avant(feed, i), P.get("win_prob_home")
    bascule = abs((wb if wb is not None else 0.5) - (wa if wa is not None else 0.5))
    note, raisons = bascule * 100.0, []
    gain = P.get("gain") or 0
    kr = P.get("kick_return") or {}
    conv = P.get("conversion") or {}
    if t == "kickoff" and kr.get("td"):
        note += 30; raisons.append("kick return touchdown")
    elif t == "punt" and (P.get("punt_return") or {}).get("td"):
        note += 30; raisons.append("punt return touchdown")
    elif r == "touchdown":
        note += 15; raisons.append("touchdown")
    if r in ("interception", "fumble_lost"):
        note += 12; raisons.append("interception" if r == "interception" else "fumble")
    if t in ("run", "pass") and gain >= 40:
        note += gain / 3.0; raisons.append(f"{gain}-yard play")
    elif t == "kickoff" and not kr.get("td") and (kr.get("return") or 0) >= 40:
        note += kr["return"] / 4.0; raisons.append(f"{kr['return']}-yard return")
    if P.get("down") == 4 and t in ("run", "pass"):
        yards_a_faire = P.get("to_go") or 0
        los = P.get("los_x") or 60
        propre_moitie = (los < 60) if P.get("offense") == "home" else (los > 60)
        reussi = r == "touchdown" or gain >= yards_a_faire
        if reussi and (propre_moitie or yards_a_faire >= 4):
            note += 20; raisons.append(f"4th-and-{yards_a_faire} gamble")
    if conv.get("choice") == "two_point" and conv.get("good"):
        note += 8; raisons.append("2-point conversion")
    if r == "field_goal_good":
        try:
            yds = int(str(P.get("text") or "").split(",")[-1].split()[0])
        except (ValueError, IndexError):
            yds = 0
        if yds >= 55:
            note += 15; raisons.append(f"{yds}-yard field goal")
    if _fin_de_match(P) and note > 0:
        note *= 1.5
        if bascule >= 0.25 and r in ("touchdown", "field_goal_good", "interception", "fumble_lost"):
            raisons.insert(0, "game-winning " + ("score" if r != "interception" and r != "fumble_lost" else "takeaway"))
    if t in ("extra_point",) and not conv:
        note = 0
    return round(note, 2), (" · ".join(raisons[:2]) if raisons else "momentum swing")


def spectacle(feed, g=None):
    """Note d'un match — copie de outils/video/choisir.spectacle."""
    tot, wp, mini, maxi = 0.0, _wp_avant(feed, 0) or 0.5, 1.0, 0.0
    for P in feed["plays"]:
        w = P.get("win_prob_home")
        if w is None:
            continue
        tot += abs(w - wp); wp = w
        mini, maxi = min(mini, w), max(maxi, w)
    fs = feed["game"].get("final_score") or feed["plays"][-1]["after"]["score"]
    ecart = abs(fs["home"] - fs["away"])
    note = tot * 10 + max(0, 10 - ecart) * 1.5
    if feed["game"].get("overtime") or any((P.get("quarter") or 0) >= 5 for P in feed["plays"]):
        note += 12
    gagnant_home = fs["home"] > fs["away"]
    if (gagnant_home and mini < 0.15) or (not gagnant_home and fs["home"] != fs["away"] and maxi > 0.85):
        note += 10
    if g and g.get("phase") in ("semifinal", "ai_bowl"):
        note += 6 if g["phase"] == "semifinal" else 10
    return round(note, 2)


# ------------------------------------------------------------------ la playlist
def _score(feed):
    return feed["game"].get("final_score") or feed["plays"][-1]["after"]["score"]


def _ot(feed):
    return bool(feed["game"].get("overtime")) or any((P.get("quarter") or 0) >= 5 for P in feed["plays"])


def _ligne(g, feed):
    s = _score(feed)
    return f"{g['away']} {s['away']} – {s['home']} {g['home']}" + (" · OT" if _ot(feed) else "")


def _clip(g, feed, i, caption):
    P = feed["plays"][i]
    return {"game": g["id"], "index": i, "caption": caption, "text": str(P.get("text") or ""),
            "away": g["away"], "home": g["home"], "q": P.get("quarter"), "clock": P.get("clock_start")}


def _pat(P):
    """Un extra point : il suit le touchdown, qui est déjà dans la playlist."""
    return (P.get("conversion") or {}).get("choice") == "extra_point" or P.get("result") in ("pat_good", "pat_missed")


def _meilleures(g, feed, n, filtre=None):
    """Les n plus belles actions d'un match (note > 0, extra points exclus), dans l'ordre du match."""
    c = []
    for i in range(len(feed["plays"])):
        if _pat(feed["plays"][i]) or (filtre and not filtre(feed["plays"][i])):
            continue
        note, why = interet(feed, i)
        if note > 0:
            c.append((note, i, why))
    c.sort(key=lambda x: (-x[0], x[1]))
    return sorted(c[:n], key=lambda x: x[1])


def _ordre(jeux):
    return sorted(jeux, key=lambda gf: (gf[0]["kickoff"], gf[0]["id"]))


def franchise_du_rang(equipes, debut, start):
    """La franchise de la semaine : les franchises par abréviation, une par semaine depuis la première semaine."""
    eq = sorted(equipes)
    rang = ((datetime.fromisoformat(start) - datetime.fromisoformat(debut)).days // 7) % len(eq)
    return eq[rang]


def calculer(jeux, franchise=None):
    """jeux = [(match du calendrier, GameFeed complet)] des matchs terminés. -> {"edition", "segments": [...]}"""
    jeux = _ordre(jeux)
    reg = [(g, f) for g, f in jeux if g.get("phase") == "regular"]
    semis = [(g, f) for g, f in jeux if g.get("phase") == "semifinal"]
    fin = [(g, f) for g, f in jeux if g.get("phase") == "ai_bowl"]
    seg = []

    def ajoute(key, title, sub, clips):
        if clips:
            seg.append({"key": key, "title": title, "sub": sub, "clips": clips})

    for g, f in fin:
        s = _score(f)
        champ = g["home"] if s["home"] > s["away"] else g["away"]
        ajoute("final", "Grand Final", f"{_ligne(g, f)} · {champ} are the champions",
               [_clip(g, f, i, why) for _, i, why in _meilleures(g, f, N_FINAL)])
    if semis:
        ajoute("semis", "Semi-finals", " · ".join(_ligne(g, f) for g, f in semis),
               [_clip(g, f, i, f"{_ligne(g, f)} · {why}") for g, f in semis for _, i, why in _meilleures(g, f, N_SEMI)])

    # Plays of the week (saison régulière), 2 au plus par match
    cand = []
    for g, f in reg:
        for i in range(len(f["plays"])):
            if _pat(f["plays"][i]):
                continue
            note, why = interet(f, i)
            if note > 0:
                cand.append((note, g["kickoff"], g["id"], i, why, g, f))
    cand.sort(key=lambda x: (-x[0], x[1], x[2], x[3]))
    pris, par = [], {}
    for note, _, gid, i, why, g, f in cand:
        if par.get(gid, 0) >= PAR_MATCH:
            continue
        par[gid] = par.get(gid, 0) + 1
        pris.append(_clip(g, f, i, f"{_ligne(g, f)} · {why}"))
        if len(pris) >= N_PLAYS:
            break
    ajoute("plays", "Plays of the week", "The best of the regular season", pris)

    if reg:
        g, f = max(reg, key=lambda gf: (spectacle(gf[1], gf[0]), gf[0]["id"]))
        ajoute("game", "Game of the week", _ligne(g, f), [_clip(g, f, i, why) for _, i, why in _meilleures(g, f, N_GAME)])

    # Comebacks : le vainqueur est tombé bas, puis l'action qui l'a le plus fait remonter en seconde mi-temps
    cb = []
    for g, f in reg:
        s = _score(f)
        if s["home"] == s["away"]:
            continue
        home = s["home"] > s["away"]
        wps = [(P.get("win_prob_home") if P.get("win_prob_home") is not None else 0.5) for P in f["plays"]]
        bas = min((w if home else 1 - w) for w in wps) if wps else 1
        if bas > SEUIL_COMEBACK:
            continue
        best = None
        for i, P in enumerate(f["plays"]):
            if (P.get("quarter") or 0) < 3:
                continue
            avant = _wp_avant(f, i)
            d = (wps[i] - (avant if avant is not None else 0.5)) * (1 if home else -1)
            if best is None or d > best[0]:
                best = (d, i)
        if best:
            cb.append((bas, g["id"], g, f, best[1]))
    cb.sort(key=lambda x: (x[0], x[1]))
    ajoute("comebacks", "Comebacks", "Down and almost out, then back",
           [_clip(g, f, i, f"{_ligne(g, f)} · down to {max(1, round(bas * 100))}% win chance")
            for bas, _, g, f, i in cb[:N_COMEBACK]])

    # Takeaways
    tk = []
    for g, f in reg + semis + fin:
        for i, P in enumerate(f["plays"]):
            if P.get("result") in ("interception", "fumble_lost"):
                note, why = interet(f, i)
                tk.append((note, g["kickoff"], g["id"], i, why, g, f))
    tk.sort(key=lambda x: (-x[0], x[1], x[2], x[3]))
    ajoute("takeaways", "Takeaways", "The biggest interceptions and fumbles",
           [_clip(g, f, i, f"{_ligne(g, f)} · {why}") for _, _, _, i, why, g, f in tk[:N_TAKEAWAYS]])

    # Shootouts
    so = sorted(reg, key=lambda gf: (-(_score(gf[1])["home"] + _score(gf[1])["away"]), gf[0]["kickoff"], gf[0]["id"]))
    clips = []
    for g, f in so[:N_SHOOTOUTS]:
        td = _meilleures(g, f, 1, lambda P: P.get("result") == "touchdown" or _retour_td(P))
        if td:
            s = _score(f)
            clips.append(_clip(g, f, td[0][1], f"{_ligne(g, f)} · {s['home'] + s['away']} points"))
    ajoute("shootouts", "Shootouts", "The highest-scoring games", clips)

    # Injury report
    inj = []
    for g, f in jeux:
        for i, P in enumerate(f["plays"]):
            j = P.get("injury")
            if not j or j.get("severity") != "weeks" or not j.get("weeks"):
                continue
            inj.append((-(j.get("weeks") or 0), _POSTE.get(j.get("pos"), 2), g["kickoff"], g["id"], i, j, g, f))
    inj.sort(key=lambda x: x[:5])
    clips = []
    for *_, i, j, g, f in inj[:N_INJURIES]:
        team = g[j["team"]] if j.get("team") in ("home", "away") else ""
        w = j["weeks"]
        clips.append(_clip(g, f, i, f"{team} {j.get('pos', '')} {j.get('name', '')} · {j.get('part', 'injury')} · "
                                     f"out {w} week{'s' if w > 1 else ''}".strip()))
    ajoute("injuries", "Injury report", "The big losses of the week", clips)

    # Franchise of the week
    if franchise:
        fc = []
        for g, f in jeux:
            if franchise not in (g["home"], g["away"]):
                continue
            cote = "home" if g["home"] == franchise else "away"
            for i, P in enumerate(f["plays"]):
                r, gain = P.get("result"), P.get("gain") or 0
                if (P.get("offense") == cote and (r == "touchdown" or (r in ("complete", "run") and gain >= 25))) or \
                   (P.get("offense") != cote and r in ("interception", "fumble_lost")):
                    note, why = interet(f, i)
                    fc.append((note, g["kickoff"], g["id"], i, why, g, f))
        fc.sort(key=lambda x: (-x[0], x[1], x[2], x[3]))
        ajoute("franchise", "Franchise of the week", franchise,
               [_clip(g, f, i, f"{_ligne(g, f)} · {why}")
                for _, _, _, i, why, g, f in sorted(fc[:N_FRANCHISE], key=lambda x: (x[1], x[3]))])

    edition = "final" if fin else "semis" if semis else "regular"
    return {"version": VERSION, "edition": edition, "segments": seg}


# ------------------------------------------------------------------ programme du dimanche (README section 93)
# Heures comptées depuis le coup d'envoi de la Grand Final (dimanche 18:00) : deux « Sunday Classic » (rediffusions
# calées sur l'horloge, comme un direct), puis « Road to the Final », l'avant-match, jusqu'au coup d'envoi.
CLASSIC_AVANT = (3 * 3600, 2 * 3600 + 15 * 60)       # 15:00 et 15:45
ROAD_AVANT = 90 * 60                                   # 16:30
N_PARCOURS = 3                                         # actions par demi-finale dans « Road to the Final »


def _remontee(g, feed):
    """Le plus bas qu'est tombé le vainqueur (chances de victoire), ou None (nul)."""
    s = _score(feed)
    if s["home"] == s["away"]:
        return None
    home = s["home"] > s["away"]
    wps = [(P.get("win_prob_home") if P.get("win_prob_home") is not None else 0.5) for P in feed["plays"]]
    return min((w if home else 1 - w) for w in wps) if wps else None


def classiques(jeux):
    """Les deux matchs rediffusés : le plus spectaculaire de la saison régulière (« Game of the week »), puis la plus
    grosse remontée parmi les autres (à défaut, le deuxième plus spectaculaire). [{game, why, line}]"""
    reg = _ordre([(g, f) for g, f in jeux if g.get("phase") == "regular"])
    if not reg:
        return []
    tri = sorted(reg, key=lambda gf: (-spectacle(gf[1], gf[0]), gf[0]["id"]))
    g1, f1 = tri[0]
    out = [{"game": g1["id"], "why": "Game of the week", "line": _ligne(g1, f1)}]
    autres = [(g, f, _remontee(g, f)) for g, f in tri[1:]]
    cb = sorted(((b, g["id"], g, f) for g, f, b in autres if b is not None and b <= SEUIL_COMEBACK), key=lambda x: x[:2])
    if cb:
        b, _, g2, f2 = cb[0]
        out.append({"game": g2["id"], "why": f"Comeback of the week · down to {max(1, round(b * 100))}% win chance",
                    "line": _ligne(g2, f2)})
    elif len(tri) > 1:
        g2, f2 = tri[1]
        out.append({"game": g2["id"], "why": "One more classic", "line": _ligne(g2, f2)})
    return out


def parcours(jeux):
    """Les actions des demi-finales, pour « Road to the Final » : N_PARCOURS par demi-finale, dans l'ordre."""
    semis = _ordre([(g, f) for g, f in jeux if g.get("phase") == "semifinal"])
    return [_clip(g, f, i, f"{_ligne(g, f)} · {why}") for g, f in semis for _, i, why in _meilleures(g, f, N_PARCOURS)]
