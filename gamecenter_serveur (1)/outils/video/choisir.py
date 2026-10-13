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
  joueur_de_la_semaine(...), champion(...) : le joueur de la semaine (score « fantasy ») et le champion de la Grand
                        Final, avec leurs plus belles actions (étape 8.6 a) ;
  match_hors_norme(...), franchise(...) : le match hors norme de la semaine (record ou 100 points cumulés) et la
                        franchise de la semaine (ordre fixe sur 24 semaines), étape 8.6 b ;
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
FINI_APRES = timedelta(hours=1)   # un match est terminé 1 h après son coup d'envoi (il dure ≈ 25 min à l'écran ; 1 h :
                                  # la Grand Final du dimanche 22 h, Bruxelles, est finie au tournage de 22 h 30 UTC l'hiver)


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


# ------------------------------------------------------------------ étape 8.6 a : joueur de la semaine, champion
def _termines(doc, maintenant):
    return [g for g in doc["schedule"] if datetime.fromisoformat(g["kickoff"]) + FINI_APRES <= maintenant]


def _histoire_module():
    import sys
    racine = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    if racine not in sys.path:
        sys.path.insert(0, racine)
    from moteur import histoire
    return histoire


def _feuille(feed):
    """Statistiques par joueur d'un match : moteur/histoire.py (mêmes règles que le site et l'onglet History)."""
    import sys
    racine = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    if racine not in sys.path:
        sys.path.insert(0, racine)
    from moteur.histoire import feuille_de_match
    return feuille_de_match(feed)


def score_fantasy(j):
    """Le score du joueur de la semaine : passe (yards / 25 + 4 par TD − 2 par interception), course et réception
    (yards / 10 + 6 par TD + 0,5 par réception), retours (yards / 25 + 6 par TD), défense (plaquage 1, sack 4,
    interception 6, passe défendue 1), coups de pied (field goal 3, transformation 1)."""
    return round(j["pyd"] / 25 + 4 * j["ptd"] - 2 * j["pint"] + j["ryd"] / 10 + 6 * j["rtd"] + j["yd"] / 10 + 6 * j["td"]
                 + 0.5 * j["rec"] + j["kry"] / 25 + 6 * j["krtd"] + j["tk"] + 4 * j["sk"] + 6 * j["int"] + j["pd"]
                 + 3 * j["fgm"] + j["xpm"], 2)


def _implique(P, g, joueur):
    """L'action est un beau moment du joueur : touchdown ou gain de 15 yards et plus qu'il porte ou lance ; interception,
    sack ou fumble récupéré par lui en défense."""
    pl = P.get("players") or {}
    r, gain = P.get("result"), P.get("gain") or 0
    attaque = (pl.get("carrier") or {}).get("id") == joueur["id"] or (pl.get("passer") or {}).get("id") == joueur["id"]
    if attaque:
        return r == "touchdown" or (r in ("complete", "run") and gain >= 15)
    defense = g["away"] if P.get("offense") == "home" else g["home"]
    return ((pl.get("defender") or {}).get("name") == joueur["name"] and defense == joueur["team"]
            and r in ("interception", "sack", "fumble_lost"))


def joueur_de_la_semaine(dossier, maintenant, n_actions=3):
    """Le meilleur joueur de la semaine (une semaine = une saison) au score fantasy, matchs terminés seulement :
    {"joueur": stats cumulées (id, name, team, pos, games, …), "score", "actions": ses plus belles actions (ordre du
    calendrier)}. None si aucun match n'est terminé."""
    doc, feeds = charger_semaine(dossier)
    jeux = _termines(doc, maintenant)
    if not jeux:
        return None
    tot = {}
    for g in jeux:
        for j in _feuille(feeds[g["id"]])["joueurs"].values():
            q = tot.setdefault((j["id"], j["name"]), dict(id=j["id"], name=j["name"], team=j["team"], pos=j["pos"], games=0))
            for k, v in j.items():
                if isinstance(v, (int, float)) and k not in ("lng", "fg_lng", "kr_lng"):
                    q[k] = q.get(k, 0) + v
            q["games"] += 1
    best = max(tot.values(), key=lambda q: (score_fantasy(q), q["id"]))
    cand = []
    for g in jeux:
        F = feeds[g["id"]]
        for i, P in enumerate(F["plays"]):
            if _implique(P, g, best):
                n, why = interet(F, i)
                cand.append({"game": g["id"], "index": i, "note": n, "why": why, "play": P, "dossier": dossier,
                             "ko": g["kickoff"]})
    cand.sort(key=lambda a: (-a["note"], a["ko"], a["index"]))
    actions = sorted(cand[:n_actions], key=lambda a: (a["ko"], a["index"]))
    return {"joueur": best, "score": score_fantasy(best), "actions": actions}


def champion(dossier, maintenant, toutes=(), n_actions=4):
    """Le champion de la semaine, une fois la Grand Final terminée : {"team", "opp", "final" (identifiant), "score"
    (champion, adversaire), "bilan" (saison régulière : w, l, t), "titres" (dans les semaines données, celle-ci
    comprise), "actions" : ses plus belles actions des demi-finales et de la finale (touchdowns, gains de 25 yards et
    plus, pertes de balle provoquées), dans l'ordre}. None avant la fin de la Grand Final."""
    doc, feeds = charger_semaine(dossier)
    fin = next((g for g in doc["schedule"] if g["phase"] == "ai_bowl"), None)
    if not fin or fin not in _termines(doc, maintenant):
        return None
    F = feeds[fin["id"]]
    fs = F["game"].get("final_score") or F["plays"][-1]["after"]["score"]
    cote = "home" if fs["home"] > fs["away"] else "away"
    equipe = doc.get("champion") or fin[cote]
    cote = "home" if fin["home"] == equipe else "away"
    autre = "away" if cote == "home" else "home"
    ligne = next((r for r in doc.get("standings") or [] if r.get("team") == equipe), {})
    titres = 0                                          # une fois par semaine (nom du dossier), celle-ci comprise
    par_nom = {os.path.basename(os.path.normpath(d)): d for d in toutes}
    par_nom[os.path.basename(os.path.normpath(dossier))] = dossier
    for nom in sorted(par_nom):
        if nom > os.path.basename(os.path.normpath(dossier)):
            continue
        with open(os.path.join(par_nom[nom], "week.json"), encoding="utf-8") as fh:
            if json.load(fh).get("champion") == equipe:
                titres += 1
    cand = []
    for g in doc["schedule"]:
        if g["phase"] not in ("semifinal", "ai_bowl") or equipe not in (g["home"], g["away"]):
            continue
        G = feeds[g["id"]]
        cote_g = "home" if g["home"] == equipe else "away"
        for i, P in enumerate(G["plays"]):
            r, gain = P.get("result"), P.get("gain") or 0
            pour = P.get("offense") == cote_g and (r == "touchdown" or (r in ("complete", "run") and gain >= 25))
            contre = P.get("offense") != cote_g and r in ("interception", "fumble_lost")
            if pour or contre or ((P.get("kick_return") or {}).get("td") and P.get("offense") != cote_g):
                n, why = interet(G, i)
                cand.append({"game": g["id"], "index": i, "note": n, "why": why, "play": P, "dossier": dossier,
                             "ko": g["kickoff"]})
    cand.sort(key=lambda a: (-a["note"], a["ko"], a["index"]))
    return {"team": equipe, "opp": fin[autre], "final": fin["id"], "score": (fs[cote], fs[autre]),
            "bilan": {k: ligne.get(k, 0) for k in ("w", "l", "t")}, "titres": titres,
            "actions": sorted(cand[:n_actions], key=lambda a: (a["ko"], a["index"]))}


# ------------------------------------------------------------------ étape 8.6 b : match hors norme, franchise
SEUIL_POINTS = 100        # un match hors norme sans record : 100 points cumulés ou plus
RECORDS = (("total", "combined points"), ("pts", "points by one team"), ("margin", "point margin"))


def _valeurs(g):
    r = g.get("result") or {}
    h, a = r.get("home", 0), r.get("away", 0)
    return {"total": h + a, "pts": max(h, a), "margin": abs(h - a)}


def match_hors_norme(dossier, maintenant, toutes=()):
    """Le match hors norme de la semaine (matchs terminés) : un record de tous les temps battu au moment où il a été
    joué (total des deux équipes, points d'une équipe, écart — dans cet ordre de priorité ; égaler ne suffit pas), sinon
    le plus gros total s'il atteint SEUIL_POINTS. {"game", "kind", "label", "value", "previous" (record d'avant, None
    sans record), "dossier", "result"} ou None si la semaine n'en a pas."""
    tous = []
    for d in sorted(set(toutes) | {dossier}):
        with open(os.path.join(d, "week.json"), encoding="utf-8") as fh:
            w = json.load(fh)
        for g in _termines(w, maintenant):
            if g.get("result"):
                tous.append((g["kickoff"], g, os.path.basename(os.path.normpath(d))))
    tous.sort(key=lambda x: (x[0], x[1]["id"]))
    semaine = os.path.basename(os.path.normpath(dossier))
    meilleur, choix = {k: None for k, _ in RECORDS}, None
    for ko, g, nom in tous:
        v = _valeurs(g)
        if nom == semaine:
            for rang, (k, label) in enumerate(RECORDS):
                if meilleur[k] is not None and v[k] > meilleur[k]:
                    c = {"game": g["id"], "kind": k, "label": label, "value": v[k], "previous": meilleur[k],
                         "dossier": dossier, "result": g["result"], "rang": rang}
                    if choix is None or (c["rang"], -c["value"]) < (choix["rang"], -choix["value"]):
                        choix = c
                    break
        for k in meilleur:
            meilleur[k] = v[k] if meilleur[k] is None else max(meilleur[k], v[k])
    if choix is None:
        gros = [(_valeurs(g)["total"], g) for ko, g, nom in tous if nom == semaine]
        if gros:
            total, g = max(gros, key=lambda x: (x[0], x[1]["id"]))
            if total >= SEUIL_POINTS:
                choix = {"game": g["id"], "kind": "total", "label": "combined points", "value": total,
                         "previous": None, "dossier": dossier, "result": g["result"], "rang": 9}
    return choix


def actions_du_score(feed, n_max=8):
    """Les actions qui ont fait le score (touchdowns, y compris sur retour, et field goals réussis) ; au plus n_max
    (d'abord les touchdowns, puis les mieux notées), dans l'ordre du match."""
    P = feed["plays"]
    sc = [i for i, p in enumerate(P) if p.get("result") in ("touchdown", "field_goal_good") or (p.get("kick_return") or {}).get("td")]
    garde = sorted(sc, key=lambda i: (P[i].get("result") != "touchdown" and not (P[i].get("kick_return") or {}).get("td"),
                                       -interet(feed, i)[0], i))[:n_max]
    return sorted(garde)


def franchise_de_la_semaine(dossier, toutes, maintenant, n_actions=2):
    """La franchise de la semaine : l'ordre est fixe (les 24 équipes par abréviation, une par semaine depuis la première
    semaine enregistrée). {"team", "fiche" (week.json : nom, style, identité, coordinateurs, conférence, division),
    "bilan" (histoire.py : saisons, w, l, t, playoffs, finales, titres), "legende" (meilleur joueur de son histoire
    au score fantasy, saisons avec elle seulement), "actions" (ses plus belles actions de tous les temps, matchs
    terminés)}."""
    H = _histoire_module()
    toutes = sorted(set(toutes) | {dossier}, key=lambda d: os.path.basename(os.path.normpath(d)))
    docs = {}
    for d in toutes:
        with open(os.path.join(d, "week.json"), encoding="utf-8") as fh:
            docs[d] = json.load(fh)
    doc = docs[dossier]
    equipes = sorted(doc["teams"])
    debut = min(datetime.fromisoformat(w["week"]["start"]) for w in docs.values())
    rang = ((datetime.fromisoformat(doc["week"]["start"]) - debut).days // 7) % len(equipes)
    t = equipes[rang]
    semaines, feeds_de = [], {}
    for k, d in enumerate(toutes):
        w, fd = charger_semaine(d)
        feeds_de[d] = (w, fd)
        jeux = _termines(w, maintenant)
        semaines.append({"index": k + 1, "start": w["week"]["start"], "doc": w,
                         "matchs": [(g, H.feuille_de_match(fd[g["id"]])) for g in jeux],
                         "terminee": any(g["phase"] == "ai_bowl" for g in jeux)})
    h = H.histoire(semaines)
    bilan = next((f for f in h["franchises"] if f["team"] == t), {"team": t, "seasons": 0, "w": 0, "l": 0, "t": 0,
                                                                     "playoffs": 0, "finals": 0, "titles": 0})
    legende = None
    for c in h["careers"].values():
        avec = [x for x in c["seasons"] if x.get("team") == t]
        if not avec:
            continue
        tot = {k: sum(x.get(k, 0) for x in avec) for k in avec[0] if isinstance(avec[0][k], (int, float)) and k != "week"}
        q = dict(tot, id=c["id"], name=c["name"], pos=c["pos"], team=t, seasons=len(avec))
        if legende is None or (score_fantasy(q), q["id"]) > (score_fantasy(legende), legende["id"]):
            legende = q
    cand = []
    for d, (w, fd) in feeds_de.items():
        for g in _termines(w, maintenant):
            if t not in (g["home"], g["away"]):
                continue
            F, cote = fd[g["id"]], ("home" if g["home"] == t else "away")
            for i, P in enumerate(F["plays"]):
                r, gain = P.get("result"), P.get("gain") or 0
                if (P.get("offense") == cote and (r == "touchdown" or (r in ("complete", "run") and gain >= 25))) or \
                   (P.get("offense") != cote and r in ("interception", "fumble_lost")):
                    n, why = interet(F, i)
                    cand.append({"game": g["id"], "index": i, "note": n, "why": why, "play": P, "dossier": d,
                                 "ko": g["kickoff"]})
    cand.sort(key=lambda a: (-a["note"], a["ko"], a["index"]))
    return {"team": t, "fiche": doc["teams"][t], "bilan": bilan, "legende": legende,
            "actions": sorted(cand[:n_actions], key=lambda a: (a["ko"], a["index"]))}
