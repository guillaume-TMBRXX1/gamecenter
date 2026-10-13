"""Vidéos verticales (bloc 2, étape 8) : quelles actions et quel match montrer.

Tout se lit dans les GameFeed d'une semaine (data/weeks/week_*/games) :
  interet(...)        : la note d'une action (bascule de la probabilité de victoire, touchdown, perte de balle, grand
                        gain, « décision folle » : 4e essai tenté loin de l'en-but, 2 points, long field goal ; plus la
                        fin de match) et ce qui la rend remarquable ;
  action_du_jour(...) : la plus belle action des matchs d'une journée (heure de Bruxelles) ;
  plus_beau_match(...): le match le plus spectaculaire de la semaine (bascules de probabilité, écart final, prolongation,
                        remontée, playoffs) ;
  resume(...)         : les actions d'un résumé de 2 à 3 minutes (tous les scores, les pertes de balle, les plus
                        grosses bascules, la dernière action), dans l'ordre du match ;
  resume_court(...)   : les actions du résumé court (≈ 60 s, étape 8.3) : touchdowns, pertes de balle, dernière action ;
  meilleure_action(...): la plus belle action de toutes les semaines, parmi les matchs déjà terminés (étape 8.2) ;
  trois_actions(...)  : trois belles actions de genres et de matchs différents (« What is Snapline? », étape 8.3) ;
  enjeu(...), bascule(...) : le texte de l'accroche (score, temps, 4e essai) et la probabilité de victoire avant /
                        après, pour le haut de la vidéo (étape 8.2).
Rien d'aléatoire : la même semaine donne toujours les mêmes vidéos.
"""
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Brussels")
DUREE_ACTION = 8.0           # secondes à l'écran par action dans un résumé (action, bannière, respiration)
RESUME_MIN, RESUME_MAX = 120.0, 175.0
COURT_ACTION, COURT_MAX = 5.4, 55.0   # résumé court : ≈ 5,4 s par action (avant le snap, l'action, 0,8 s après), 55 s
FINI_APRES = timedelta(hours=2)   # un match est terminé 2 h après son coup d'envoi (il dure ≈ 25 min à l'écran)


def charger_semaine(dossier):
    with open(os.path.join(dossier, "week.json"), encoding="utf-8") as fh:
        doc = json.load(fh)
    feeds = {}
    for g in doc["schedule"]:
        with open(os.path.join(dossier, g["feed"]), encoding="utf-8") as fh:
            feeds[g["id"]] = json.load(fh)
    return doc, feeds


def _wp_avant(feed, i):
    if i > 0:
        return feed["plays"][i - 1].get("win_prob_home")
    po = feed["game"].get("pregame_odds") or {}
    return po.get("p_home", 0.5)


def _fin_de_match(P):
    return (P.get("quarter") or 0) >= 5 or ((P.get("quarter") or 0) == 4 and (P.get("clock_start") or 0) <= 120)


def interet(feed, i):
    """(note, raison) d'une action. Raison : un court texte anglais (la vidéo et la légende sont en anglais)."""
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
    elif r == "touchdown":
        note += 15; raisons.append("touchdown")
    if r in ("interception", "fumble_lost"):
        note += 12; raisons.append("interception" if r == "interception" else "fumble")
    if t in ("run", "pass") and gain >= 40:
        note += gain / 3.0; raisons.append(f"{gain}-yard play")
    elif t == "kickoff" and not kr.get("td") and (kr.get("return") or 0) >= 40:
        note += kr["return"] / 4.0; raisons.append(f"{kr['return']}-yard return")
    # décision folle : 4e essai tenté loin de l'en-but adverse ou avec beaucoup à faire, et réussi
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


def jour_du_match(g):
    return datetime.fromisoformat(g["kickoff"]).astimezone(TZ).date().isoformat()


def action_du_jour(doc, feeds, jour):
    """La plus belle action des matchs joués le jour donné (AAAA-MM-JJ, Bruxelles). None si aucun match ce jour-là."""
    meilleur = None
    for g in doc["schedule"]:
        if jour_du_match(g) != jour:
            continue
        F = feeds[g["id"]]
        for i in range(len(F["plays"])):
            n, why = interet(F, i)
            if meilleur is None or n > meilleur["note"]:
                meilleur = {"game": g["id"], "index": i, "note": n, "why": why, "play": F["plays"][i]}
    return meilleur


def spectacle(feed, g=None):
    """Note d'un match : bascules cumulées, écart final serré, prolongation, remontée, playoffs."""
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
        note += 10                                                   # remontée
    if g and g.get("phase") in ("semifinal", "ai_bowl"):
        note += 6 if g["phase"] == "semifinal" else 10
    return round(note, 2)


def plus_beau_match(doc, feeds):
    notes = [(spectacle(feeds[g["id"]], g), g["id"]) for g in doc["schedule"]]
    notes.sort(key=lambda x: (-x[0], x[1]))
    return {"game": notes[0][1], "note": notes[0][0]}


def resume(feed, cible=150.0):
    """Indices des actions d'un résumé de RESUME_MIN à RESUME_MAX secondes, dans l'ordre du match.
    Toujours : chaque score (touchdown, field goal, safety, touchdown sur retour), chaque perte de balle et la dernière
    action ; puis les plus grosses bascules jusqu'à la durée visée."""
    P = feed["plays"]
    oblig = set()
    for i, p in enumerate(P):
        r = p.get("result")
        if r in ("touchdown", "field_goal_good", "safety", "interception", "fumble_lost") or (p.get("kick_return") or {}).get("td"):
            oblig.add(i)
    oblig.add(len(P) - 1)
    n_max = int(RESUME_MAX // DUREE_ACTION)
    n_vise = max(int(cible // DUREE_ACTION), int(RESUME_MIN // DUREE_ACTION))
    choisis = set(sorted(oblig, key=lambda i: -interet(feed, i)[0])[:n_max])
    reste = sorted((i for i in range(len(P)) if i not in choisis and (P[i].get("call") or {}).get("type") in ("run", "pass", "kickoff", "punt")),
                   key=lambda i: (-interet(feed, i)[0], i))
    for i in reste:
        if len(choisis) >= n_vise:
            break
        if interet(feed, i)[0] > 0:
            choisis.add(i)
    return sorted(choisis)


def meilleure_action(dossiers, maintenant):
    """La plus belle action de toutes les semaines (dossiers week_*), parmi les matchs terminés à l'instant maintenant
    (datetime avec fuseau) : la semaine en cours est calculée d'avance, ses matchs à venir ne doivent rien dévoiler."""
    meilleur = None
    for dossier in sorted(dossiers):
        doc, feeds = charger_semaine(dossier)
        for g in doc["schedule"]:
            if datetime.fromisoformat(g["kickoff"]) + FINI_APRES > maintenant:
                continue
            F = feeds[g["id"]]
            for i in range(len(F["plays"])):
                n, why = interet(F, i)
                if meilleur is None or n > meilleur["note"]:
                    meilleur = {"game": g["id"], "index": i, "note": n, "why": why, "play": F["plays"][i],
                                "dossier": dossier}
    return meilleur


def score_avant(feed, i):
    return dict(feed["plays"][i - 1]["after"]["score"]) if i > 0 else {"home": 0, "away": 0}


def _temps(P):
    q, s = P.get("quarter") or 1, int(P.get("clock_start") or 0)
    return f"{s // 60}:{s % 60:02d}"


def enjeu(feed, i, g):
    """L'accroche du haut de la vidéo, en anglais, sans dévoiler le résultat : le 4e essai tenté (« 4th & 6 · own 35 »),
    la fin de match (« Tied 31–31 · 0:14 left », « AXM down 28–31 · 1:02 left », « Overtime · … ») ou le score et
    l'horloge (« AEG 14–10 AXM · Q2 7:12 »)."""
    P = feed["plays"][i]
    sc = score_avant(feed, i)
    att = P.get("offense") or "home"
    dfn = "away" if att == "home" else "home"
    if P.get("down") == 4 and (P.get("call") or {}).get("type") in ("run", "pass") and "gamble" in interet(feed, i)[1]:
        los = P.get("los_x") or 60
        propre = (los < 60) if att == "home" else (los > 60)
        ligne = (los - 10 if att == "home" else 110 - los) if propre else (110 - los if att == "home" else los - 10)
        cote = "own" if propre else "opp"
        return f"4th & {P.get('to_go')} · {cote} {ligne}" if ligne != 50 else f"4th & {P.get('to_go')} · midfield"
    if _fin_de_match(P):
        q = P.get("quarter") or 4
        if sc["home"] == sc["away"]:
            t = f"{'tied' if q >= 5 else 'Tied'} {sc['away']}–{sc['home']}"
        else:
            etat = "up" if sc[att] > sc[dfn] else "down"
            t = f"{g[att]} {etat} {sc[att]}–{sc[dfn]}"
        return f"Overtime · {t}" if q >= 5 else f"{t} · {_temps(P)} left"
    q = P.get("quarter") or 1
    return f"{g['away']} {sc['away']}–{sc['home']} {g['home']} · Q{q} {_temps(P)}"


def bascule(feed, i, g):
    """Probabilité de victoire avant / après l'action, pour l'équipe qu'elle a aidée : {"team": "AEG", "avant": 26,
    "apres": 81} (en %), None si la probabilité manque. Texte : « AEG win probability 26% → 81% »."""
    wa, wb = _wp_avant(feed, i), feed["plays"][i].get("win_prob_home")
    if wa is None or wb is None:
        return None
    cote = "home" if wb >= wa else "away"
    a, b = (wa, wb) if cote == "home" else (1 - wa, 1 - wb)
    return {"team": g[cote], "avant": round(a * 100), "apres": round(b * 100)}


def resume_court(feed):
    """Indices du résumé court (« Game in 60 seconds »), dans l'ordre du match : chaque touchdown (y compris sur retour),
    chaque perte de balle, les field goals des 2 dernières minutes et de la prolongation, la dernière action ; au plus
    COURT_MAX secondes (d'abord les scores, puis les mieux notées ; la dernière action toujours), et au moins 6 actions."""
    P = feed["plays"]
    n_max = int(COURT_MAX // COURT_ACTION)
    dernier = len(P) - 1
    oblig = [i for i, p in enumerate(P)
             if p.get("result") in ("touchdown", "interception", "fumble_lost") or (p.get("kick_return") or {}).get("td")
             or (p.get("result") == "field_goal_good" and _fin_de_match(p))]
    marque = lambda i: P[i].get("result") in ("touchdown", "field_goal_good") or (P[i].get("kick_return") or {}).get("td")
    choisis = {dernier} | set(sorted((i for i in oblig if i != dernier),                  # les scores d'abord : le score
                                     key=lambda i: (not marque(i), -interet(feed, i)[0], i))[:n_max - 1])   # en haut se suit
    if len(choisis) < 6:
        reste = sorted((i for i in range(len(P)) if i not in choisis and (P[i].get("call") or {}).get("type") in ("run", "pass")),
                       key=lambda i: (-interet(feed, i)[0], i))
        choisis |= set(reste[:6 - len(choisis)])
    return sorted(choisis)


def _genre(why):
    if "gamble" in why:
        return "gamble"
    if "takeaway" in why or "interception" in why or "fumble" in why:
        return "takeaway"
    if "touchdown" in why:
        return "touchdown"
    return "autre"


def trois_actions(dossiers, maintenant):
    """Trois belles actions pour « What is Snapline? » : la meilleure de chaque genre (touchdown, perte de balle,
    4e essai tenté), de trois matchs différents, parmi les matchs terminés ; complétées par les mieux notées s'il manque
    un genre. [{game, index, note, why, play, dossier}], dans l'ordre : touchdown, perte de balle, 4e essai."""
    toutes = []
    for dossier in sorted(dossiers):
        doc, feeds = charger_semaine(dossier)
        for g in doc["schedule"]:
            if datetime.fromisoformat(g["kickoff"]) + FINI_APRES > maintenant:
                continue
            F = feeds[g["id"]]
            for i in range(len(F["plays"])):
                n, why = interet(F, i)
                if n > 0:
                    toutes.append({"game": g["id"], "index": i, "note": n, "why": why, "play": F["plays"][i],
                                   "dossier": dossier})
    toutes.sort(key=lambda a: (-a["note"], a["dossier"], a["game"], a["index"]))
    choix, matchs = [], set()
    for genre in ("touchdown", "takeaway", "gamble"):
        a = next((a for a in toutes if _genre(a["why"]) == genre and a["game"] not in matchs), None)
        if a:
            choix.append(a); matchs.add(a["game"])
    for a in toutes:
        if len(choix) >= 3:
            break
        if a["game"] not in matchs:
            choix.append(a); matchs.add(a["game"])
    return choix
