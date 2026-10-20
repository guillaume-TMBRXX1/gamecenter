"""Vidéos verticales pour les réseaux (bloc 2, étape 8) : MP4 1080×1920 + légende, à publier à la main.

    python outils/video/faire_video.py action [--jour AAAA-MM-JJ]   l'action du jour (≈ 18 s) ; jour par défaut : la
                                                                      veille au soir (heure de Bruxelles, 3 h de marge)
    python outils/video/faire_video.py action --meilleure           la plus belle action de toutes les semaines, parmi
                                                                      les matchs terminés (« Best play so far »)
    python outils/video/faire_video.py resume [--match ID]          résumé court d'un match (≈ 60 s) ; par défaut : le
                                                                      plus beau match de la semaine ; --long : 2 à 3 min
    python outils/video/faire_video.py presentation                 « What is Snapline? » (≈ 20 s) : 3 actions
    python outils/video/faire_video.py joueur                       le joueur de la semaine (≈ 25 s, étape 8.6 a)
    python outils/video/faire_video.py champion                     le champion de la Grand Final (≈ 30 s, étape 8.6 a)
    python outils/video/faire_video.py chiffres                     le match hors norme de la semaine (≈ 35 s, 8.6 b) ;
                                                                      rien (sortie normale) s'il n'y en a pas
    python outils/video/faire_video.py franchise                    la franchise de la semaine (≈ 22 s, étape 8.6 b)
    options : --semaine data/weeks/week_AAAA-MM-JJ (défaut : la dernière), --sortie videos/ (défaut), --port 8150

Le site rejoue l'action sur son terrain (serveur local avec le crochet de test ; outils/video/filmer.js filme le
navigateur), ffmpeg assemble les images et le son du stade (foule et effets du dépôt, audio/crowd et audio/sfx, calés
sur le snap et le résultat de chaque action). Depuis « gamecenter_serveur (1) » ; il faut Python avec fastapi/uvicorn,
Node avec Playwright (Chromium) et ffmpeg. Pas de commentaire ni de musique (choix du 12/10 : la musique se met au
moment de publier).
Étape 8.2 (13/10) : format TikTok — la vidéo s'ouvre sur l'action (enjeu en grand en haut), la bascule de probabilité
s'affiche au ralenti, rien d'important dans les zones couvertes par l'interface des réseaux, terrain resserré ; la
légende (.txt) a trois blocs : TikTok, Instagram, YouTube Shorts. Jamais de paris dans les textes (README section 46).
Étape 8.3 (13/10) : tournage image par image à 60 images/s en 1080×1920 natif (filmer.js), encodage plus généreux ;
le résumé est court par défaut (≈ 60 s, le long seulement avec --long) ; « What is Snapline? » (presentation).
"""
import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timedelta

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
sys.path.insert(0, ICI)
import choisir as C  # noqa: E402

PHASE = {"regular": "Regular season", "semifinal": "Conference final", "ai_bowl": "Grand Final"}
ORD = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
HASHTAGS = "#americanfootball #football #simulation #ai"
FIN = {"type": "card", "kicker": "24 AI coaches · 1 league · live", "title": "snapline.live",
       "sub": "No human calls the plays. Watch the next game live — free, a new game every 30 min.", "dur": 2.2}
EPINGLE = "Watch the next game live → snapline.live (free, a new game every 30 min) 🏈"


def horloge(P):
    q = P.get("quarter") or 1
    s = int(P.get("clock_start") or 0)
    qn = f"Q{q}" if q <= 4 else "OT"
    jeu = (P.get("call") or {}).get("type") in ("run", "pass")          # l'essai n'a de sens que sur une course ou une passe
    d = f" · {ORD.get(P.get('down'), '')} & {P.get('to_go')}" if jeu and P.get("down") and P.get("to_go") is not None else ""
    return f"{qn} {s // 60}:{s % 60:02d}{d}"


def raison(why):
    """La raison en texte public : « gamble » (4e essai) devient « go-for-it » (aucun mot qui évoque les jeux d'argent)."""
    return why.replace("gamble", "go-for-it")


def question(why):
    """La question de la légende, selon le genre d'action (pour faire réagir en commentaire)."""
    if "gamble" in why:
        return "Would you have gone for it?"
    if "takeaway" in why or "interception" in why or "fumble" in why:
        return "Bad read or great defense?"
    if "return" in why:
        return "Best return you've seen?"
    if "field goal" in why:
        return "Would you trust your kicker from there?"
    if why.startswith("game-winning"):
        return "Clutch or lucky?"
    return "Which team are you rooting for?"


def legendes(accroche, detail, quest, tag, titre_yt):
    """Les blocs prêts à copier : TikTok, le commentaire à épingler sous la vidéo TikTok (étape 8.4 bis : sans lien
    cliquable avant 1 000 abonnés, l'adresse doit se lire partout), Instagram (quelques hashtags de plus), YouTube
    Shorts (titre ≤ 100 caractères avec #Shorts, puis la description)."""
    corps = f"{accroche}\n{detail}\n{quest}\n\nEvery game simulated and played live by AI coaches → snapline.live"
    yt = titre_yt if len(titre_yt) <= 91 else titre_yt[:90].rstrip() + "…"
    return (f"=== TikTok ===\n{corps}\n\n{HASHTAGS} {tag}\n\n"
            f"=== Pinned comment (TikTok) ===\n{EPINGLE}\n\n"
            f"=== Instagram ===\n{corps}\n\n{HASHTAGS} {tag} #snapline #gameday #footballseason\n\n"
            f"=== YouTube Shorts ===\n{yt} #Shorts\n\n{corps}\n\n{HASHTAGS} {tag}")


def titre_action(why, P):
    """Le grand titre du carton d'ouverture (court, en majuscules à l'écran)."""
    w = why.split(" · ")
    if w[0].startswith("game-winning") and len(w) > 1:
        return f"Game-winner: {w[1]}"
    if w[0].startswith("game-winning"):
        return "Game-winner"
    return w[0][:1].upper() + w[0][1:]


def coordinateurs(doc):
    """Les agents IA de chaque franchise (coordinateurs offensif et défensif de la semaine) : {ABR: {offense, defense}}."""
    return {ab: dict(t.get("coordinators") or {}) for ab, t in (doc.get("teams") or {}).items()}


# ------------------------------------------------------------------ son du stade
def _assets():
    with open(os.path.join(RACINE, "audio", "manifest.json"), encoding="utf-8") as fh:
        m = json.load(fh)
    par = {}
    for a in m["assets"]:
        if a["cat"] in ("crowd", "sfx"):
            par.setdefault(a["kind"], []).append(a)
    return par


def evenements_son(timeline):
    """Les sons à poser : [(instant en s, type de son, gain)] — le choix de la prise suit l'instant (déterministe)."""
    ev = [(0.15, "horn", 0.45)]
    for s in timeline["segments"]:
        if s["type"] == "card":
            if s is timeline["segments"][-1]:
                ev.append((s["from"] + 0.1, "cheer_medium", 0.5))
            elif s.get("kind") == "stats":                   # les chiffres du carton de statistiques (étape 8.6 a)
                ev.append((s["from"] + 0.2, "cheer_medium", 0.45))
            continue
        lent = s.get("speed", 1) < 1
        g = 0.55 if lent else 1.0
        snap, res, r, call = s["snap"], s["res"], s.get("result"), s.get("call")
        if not lent:
            ev.append((snap, "snap", 0.8))
            if call in ("kickoff", "punt", "field_goal", "extra_point"):
                ev.append((snap + 0.55, "kick", 0.8))
        if s.get("td"):
            ev += [(res, "react_td", g), (res + 0.2, "cheer_huge", 0.7 * g)]
        elif r == "field_goal_good":
            ev += [(res, "fg_good", 0.8 * g), (res + 0.1, "cheer_huge", 0.8 * g)]
        elif r in ("interception", "fumble_lost"):
            ev += [(res - 0.3, "turnover", 0.7 * g), (res, "react_int", g)]
        elif r in ("field_goal_missed",):
            ev.append((res, "disappointment", g))
        elif r == "incomplete":
            ev.append((res - 0.2, "incomplete", 0.7 * g))
        elif r == "sack":
            ev += [(res - 0.3, "hit", 0.8 * g), (res, "cheer_medium", 0.6 * g)]
        else:
            ev.append((res - 0.25, "tackle", 0.7 * g))
            ev.append((res, "cheer_medium" if s.get("highlight") else "cheer_small", 0.7 * g))
        if s.get("stamp") and r not in ("sack",):           # l'impact sous le mot du résultat (« TOUCHDOWN », « +34 »…)
            ev.append((res + 0.05, "hit", 0.5 * g))
        if not lent:
            ev.append((res + 0.9, "whistle", 0.6))
    return [(max(0.0, t), k, g) for t, k, g in ev]


def mixer_son(timeline, sortie):
    A = _assets()
    duree = timeline["end"]
    lit = A["bed_idle"][0]
    cmd = ["ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-i", os.path.join(RACINE, "audio", lit["file"])]
    filtres, n = [f"[0:a]atrim=0:{duree:.3f},volume={0.45 * lit.get('gain', 1):.3f}[b0]"], 1
    for t, kind, g in evenements_son(timeline):
        prises = A.get(kind)
        if not prises:
            continue
        a = prises[int(hashlib.md5(f"{kind}{t:.2f}".encode()).hexdigest(), 16) % len(prises)]
        cmd += ["-i", os.path.join(RACINE, "audio", a["file"])]
        ms = int(t * 1000)
        filtres.append(f"[{n}:a]adelay={ms}|{ms},volume={g * a.get('gain', 1):.3f}[e{n}]")
        n += 1
    entrees = "[b0]" + "".join(f"[e{i}]" for i in range(1, n))
    filtres.append(f"{entrees}amix=inputs={n}:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[a]")
    cmd += ["-filter_complex", ";".join(filtres), "-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", sortie]
    subprocess.run(cmd, check=True)


# ------------------------------------------------------------------ plans
def plan_action(doc, feeds, jour, a=None):
    """L'action du jour (ou, avec a, l'action donnée : « Best play so far ») : l'action à vitesse normale, l'enjeu en
    haut ; le ralenti, la bascule de probabilité en haut ; le carton snapline.live."""
    meilleure = a is not None
    a = a or C.action_du_jour(doc, feeds, jour)
    if not a:
        raise SystemExit(f"aucun match le {jour}")
    g = next(x for x in doc["schedule"] if x["id"] == a["game"])
    F, P = feeds[a["game"]], a["play"]
    d = datetime.fromisoformat(C.jour_du_match(g) if meilleure else jour)
    kicker = "AI vs AI · best play so far" if meilleure else f"AI vs AI · play of the day · {d.strftime('%-d %b')}"
    match = f"{g['away']} @ {g['home']} · every call made by an AI coach"
    hook = C.enjeu(F, a["index"], g)
    sw = C.bascule(F, a["index"], g)
    top_ralenti = ({"kicker": f"AI replay · {sw['team']} win probability", "title": f"{sw['avant']}% → {sw['apres']}%", "sub": match}
                   if sw else {"kicker": kicker, "title": hook, "sub": match})
    seg = [{"type": "play", "index": a["index"], "speed": 1, "label": horloge(P), "text": P.get("text"), "after": 1.8},
           {"type": "play", "index": a["index"], "speed": 0.5, "label": "0.5×", "text": P.get("text"),
            "after": 1.0, "top": top_ralenti},
           dict(FIN)]
    top = {"kicker": kicker, "title": hook, "sub": match}
    info = {"type": "meilleure" if meilleure else "action", "game": g["id"], "index": a["index"], "why": a["why"],
            "note": a["note"], "jour": d.date().isoformat(), "enjeu": hook, "bascule": sw}
    titre = titre_action(raison(a["why"]), P)
    quand = "Best play so far" if meilleure else f"Play of the day ({d.strftime('%-d %B')})"
    legende = legendes(f"{hook}… {titre} 🏈",
                       f"{quand}: {P.get('text')}. {g['away']} @ {g['home']}, {PHASE.get(g['phase'], '')}.",
                       question(a["why"]), "#bestplay" if meilleure else "#playoftheday",
                       f"{titre} · {hook} | AI football")
    return g, seg, top, info, legende


def plan_resume(doc, feeds, gid=None, long=False):
    """Résumé d'un match. Court (défaut, étape 8.3 : « Game in 60 seconds ») : il s'ouvre sur la 1re action, le score en
    haut, sans carton de quart-temps, puis le score final et snapline.live. Long (--long, à la demande) : 2 à 3 min,
    carton d'ouverture et de fin de quart-temps."""
    gid = gid or C.plus_beau_match(doc, feeds)["game"]
    g = next(x for x in doc["schedule"] if x["id"] == gid)
    F = feeds[gid]
    fs = F["game"].get("final_score") or F["plays"][-1]["after"]["score"]
    idx = C.resume(F) if long else C.resume_court(F)
    names = {s: (F["game"].get(s) or {}).get("name", g[s]) for s in ("home", "away")}
    jour = C.jour_du_match(g)
    d = datetime.fromisoformat(jour)
    kicker = f"AI vs AI · game of the week · {d.strftime('%-d %b')}" if long else "AI vs AI · game in 60 seconds"
    seg = [{"type": "card", "kicker": "Game of the week", "title": f"{g['away']} @ {g['home']}",
            "sub": f"{names['away']} at {names['home']} · {PHASE.get(g['phase'], '')} · {d.strftime('%A %-d %B')}", "dur": 3.0}] if long else []
    q_avant = None
    for i in idx:
        P = F["plays"][i]
        q = P.get("quarter") or 1
        if long and q_avant is not None and q != q_avant:   # carton de fin de quart-temps : le score à ce moment
            fin_q = next(x for x in reversed(F["plays"][:i]) if (x.get("quarter") or 1) == q_avant)["after"]["score"]
            seg.append({"type": "card", "kind": "quarter", "kicker": {1: "End of Q1", 2: "Halftime", 3: "End of Q3"}.get(q_avant, "End of regulation"),
                        "title": f"{g['away']} {fin_q['away']} – {fin_q['home']} {g['home']}", "sub": "", "dur": 2.2})
        q_avant = q
        sc = C.score_avant(F, i)
        seg.append({"type": "play", "index": i, "speed": 1, "label": horloge(P), "text": P.get("text"), "after": 1.6 if long else 0.8,
                    "top": {"kicker": kicker, "title": f"{g['away']} vs {g['home']}",
                            "sub": f"{names['away']} at {names['home']} · every call made by an AI coach"}})
    gagnant = "home" if fs["home"] > fs["away"] else "away"
    seg.append({"type": "card", "kicker": "Final" + (" · OT" if any((P.get("quarter") or 0) >= 5 for P in F["plays"]) else ""),
                "title": f"{g['away']} {fs['away']} – {fs['home']} {g['home']}",
                "sub": f"{names[gagnant]} win · no human called a single play · snapline.live", "dur": 3.5 if long else 3.0})
    top = (seg[0]["top"] if not long else
           {"kicker": kicker, "title": f"{g['away']} @ {g['home']}", "sub": PHASE.get(g["phase"], "")})
    info = {"type": "resume" if long else "resume_court", "game": gid, "plays": idx, "spectacle": C.spectacle(F, g)}
    quoi = "Game of the week" if long else "Game in 60 seconds"
    legende = legendes(f"{quoi}: {names['away']} at {names['home']}, {fs['away']}–{fs['home']} 🏈",
                       f"{PHASE.get(g['phase'], '')}, {d.strftime('%-d %B')}. Every score, every turnover, the final play.",
                       "Which team are you rooting for?", "#gamerecap",
                       f"{quoi}: {names['away']} at {names['home']}, {fs['away']}–{fs['home']} | AI football")
    return g, seg, top, info, legende


PRESENTATION = ["24 teams. 24 AI coaches.", "No human calls a single play", "A full season every week"]


def plan_presentation(choix, semaines):
    """« What is Snapline? » (≈ 20 s, post épinglé) : trois actions de trois matchs (choisir.trois_actions), une phrase
    en haut de chacune, puis le carton snapline.live."""
    seg = []
    for a, phrase in zip(choix, PRESENTATION):
        g = next(x for x in semaines[a["dossier"]]["schedule"] if x["id"] == a["game"])
        P = a["play"]
        seg.append({"type": "play", "index": a["index"], "speed": 1, "label": horloge(P), "text": P.get("text"),
                    "after": 0.8, "feed": os.path.join(a["dossier"], g["feed"]),
                    "top": {"kicker": "What is Snapline? · AI football", "title": phrase,
                            "sub": f"{g['away']} @ {g['home']} · {PHASE.get(g['phase'], '')}"}})
    seg.append({"type": "card", "kicker": "Free to watch", "title": "snapline.live",
                "sub": "Type it in your browser · free · a new AI-coached game every 30 min", "dur": 2.5})
    info = {"type": "presentation", "plays": [{"game": a["game"], "index": a["index"], "why": a["why"]} for a in choix]}
    legende = legendes("What is Snapline? 🏈 24 teams, 24 AI coaches, every game simulated and played live.",
                       "A full season every week, with replays, records and private leagues with friends.",
                       "Which team would you follow?", "#snapline",
                       "What is Snapline? 24 AI-coached football teams, every game live")
    return seg[0]["top"], seg, info, legende


# étape 8.6 a : carton de statistiques (choisir.joueur_de_la_semaine, choisir.champion)
CHIFFRES = {"QB": (("pyd", "Pass yards"), ("ptd", "Pass TD"), ("cmp%", "Completion %"), ("ryd", "Rush yards")),
            "RB": (("ryd", "Rush yards"), ("rtd", "Rush TD"), ("car", "Carries"), ("yd", "Receiving yards")),
            "WR": (("yd", "Receiving yards"), ("rec", "Receptions"), ("td", "Receiving TD"), ("tgt", "Targets")),
            "TE": (("yd", "Receiving yards"), ("rec", "Receptions"), ("td", "Receiving TD"), ("tgt", "Targets")),
            "K": (("fgm", "Field goals"), ("fga", "Attempts"), ("xpm", "Extra points"), ("fg_pct", "FG %"))}
DEFENSE = (("tk", "Tackles"), ("sk", "Sacks"), ("int", "Interceptions"), ("pd", "Passes defended"))
POSTE = {"QB": "Quarterback", "RB": "Running back", "WR": "Wide receiver", "TE": "Tight end", "K": "Kicker",
         "EDGE": "Edge rusher", "DT": "Defensive tackle", "LB": "Linebacker", "CB": "Cornerback", "S": "Safety"}


def chiffres_joueur(j):
    """Les 4 chiffres du carton (selon le poste), les nuls en dernier ; pourcentages calculés."""
    v = dict(j)
    v["cmp%"] = round(100 * j.get("cmp", 0) / j["att"]) if j.get("att") else 0
    v["fg_pct"] = round(100 * j.get("fgm", 0) / j["fga"]) if j.get("fga") else 0
    choix = [{"v": int(round(v.get(k, 0))), "l": l} for k, l in CHIFFRES.get(j["pos"], DEFENSE)]
    return sorted(choix, key=lambda x: x["v"] == 0)


def _nom_equipe(doc, abbr):
    return ((doc.get("teams") or {}).get(abbr) or {}).get("name", abbr)


def _segments_actions(actions, semaines, top):
    seg = []
    for a in actions:
        g = next(x for x in semaines[a["dossier"]]["schedule"] if x["id"] == a["game"])
        P = a["play"]
        seg.append({"type": "play", "index": a["index"], "speed": 1, "label": horloge(P), "text": P.get("text"),
                    "after": 0.8, "feed": os.path.join(a["dossier"], g["feed"]),
                    "top": dict(top, sub=f"{g['away']} @ {g['home']} · {PHASE.get(g['phase'], '')}")})
    return seg


def plan_joueur(res, doc):
    """Joueur de la semaine (≈ 25 s) : carton de statistiques, ses plus belles actions, carton snapline.live."""
    j = res["joueur"]
    equipe = _nom_equipe(doc, j["team"])
    stats = chiffres_joueur(j)
    seg = [{"type": "stats", "kicker": "Player of the week", "title": j["name"],
            "sub": f"{equipe} · {POSTE.get(j['pos'], j['pos'])} · {j['games']} games", "team": j["team"],
            "stats": stats, "dur": 3.4}]
    seg += _segments_actions(res["actions"], {a["dossier"]: doc for a in res["actions"]},
                             {"kicker": "AI vs AI · player of the week", "title": j["name"]})
    seg.append(dict(FIN))
    info = {"type": "joueur", "player": j["id"], "name": j["name"], "team": j["team"], "score": res["score"],
            "plays": [{"game": a["game"], "index": a["index"]} for a in res["actions"]]}
    ligne = " · ".join(f"{x['v']:,} {x['l']}" for x in stats[:3] if x["v"])
    legende = legendes(f"{j['name']} ({equipe}) is the player of the week 🏈",
                       f"{ligne} in {j['games']} games.",
                       "Who's your MVP this week?", "#playeroftheweek",
                       f"Player of the week: {j['name']}, {ligne} | AI football")
    return seg[1]["top"] if len(seg) > 2 else {"kicker": "", "title": "", "sub": ""}, seg, info, legende


def plan_champion(res, doc):
    """Champion de la Grand Final (≈ 30 s) : carton de statistiques, ses plus belles actions des demi-finales et de la
    finale, carton final."""
    t, o = res["team"], res["opp"]
    nom = _nom_equipe(doc, t)
    b = res["bilan"]
    bilan = f"{b['w']}-{b['l']}" + (f"-{b['t']}" if b.get("t") else "")
    stats = [{"v": f"{res['score'][0]}–{res['score'][1]}", "l": f"Grand Final vs {o}"}, {"v": bilan, "l": "Regular season"},
             {"v": res["titres"], "l": "Titles all-time"}]
    seg = [{"type": "stats", "kicker": "Grand Final champions", "title": nom, "sub": f"{t} beat {o} {res['score'][0]}–{res['score'][1]}",
            "team": t, "stats": stats, "dur": 3.4}]
    seg += _segments_actions(res["actions"], {a["dossier"]: doc for a in res["actions"]},
                             {"kicker": "AI vs AI · road to the title", "title": nom})
    seg.append({"type": "card", "kicker": "Champions", "title": f"{t} {res['score'][0]}–{res['score'][1]} {o}",
                "sub": "Coached by AI from the first snap · a new season starts Monday on snapline.live", "dur": 2.6})
    info = {"type": "champion", "team": t, "opp": o, "score": list(res["score"]), "titles": res["titres"],
            "plays": [{"game": a["game"], "index": a["index"]} for a in res["actions"]]}
    legende = legendes(f"{nom} win the Grand Final 🏆",
                       f"{res['score'][0]}–{res['score'][1]} against {_nom_equipe(doc, o)}, after a {bilan} regular season. "
                       f"Title number {res['titres']}.",
                       "Who takes the crown next week?", "#grandfinal",
                       f"{nom} win the Grand Final, {res['score'][0]}–{res['score'][1]} | AI football")
    return seg[1]["top"] if len(seg) > 2 else {"kicker": "", "title": "", "sub": ""}, seg, info, legende


# étape 8.6 b : match hors norme (choisir.match_hors_norme), franchise (choisir.franchise_de_la_semaine)
def plan_chiffres(res, doc, feeds):
    """Match hors norme (≈ 35 s) : carton du chiffre (et du record d'avant), les actions qui ont fait le score en
    rafale, le score final."""
    g = next(x for x in doc["schedule"] if x["id"] == res["game"])
    F = feeds[g["id"]]
    r = res["result"]
    jour = datetime.fromisoformat(C.jour_du_match(g)).strftime("%a %-d %b")
    chiffre = f"{res['value']} {res['label']}"
    score = f"{g['away']} {r['away']}–{r['home']} {g['home']}"
    n_td = sum(1 for P in F["plays"] if P.get("result") == "touchdown" or (P.get("kick_return") or {}).get("td")
               or (P.get("punt_return") or {}).get("td"))
    stats = [{"v": res["value"], "l": res["label"].capitalize()}]
    if res["previous"] is not None:
        stats.append({"v": res["previous"], "l": "Previous record"})
    stats += [{"v": n_td, "l": "Touchdowns"}, {"v": f"{r['away']}–{r['home']}", "l": "Final score"}][: 4 - len(stats)]
    seg = [{"type": "stats", "kicker": "All-time record" if res["previous"] is not None else "Wild game", "title": chiffre,
            "sub": f"{score} · {PHASE.get(g['phase'], '')} · {jour}", "team": None, "stats": stats, "dur": 3.4}]
    for i in C.actions_du_score(F):
        P = F["plays"][i]
        sc = C.score_avant(F, i)
        seg.append({"type": "play", "index": i, "speed": 1, "label": horloge(P), "text": P.get("text"), "after": 0.5,
                    "top": {"kicker": f"AI vs AI · {chiffre}", "title": f"{g['away']} vs {g['home']}",
                            "sub": f"{g['away']} @ {g['home']} · {PHASE.get(g['phase'], '')}"}})
    prol = " · OT" if r.get("overtime") or any((P.get("quarter") or 0) >= 5 for P in F["plays"]) else ""
    seg.append({"type": "card", "kicker": "Final" + prol, "title": score,
                "sub": "Two AI coaches, one wild game · watch the next one on snapline.live", "dur": 2.6})
    info = {"type": "chiffres", "game": g["id"], "kind": res["kind"], "value": res["value"], "previous": res["previous"],
            "plays": [x["index"] for x in seg if x["type"] == "play"]}
    detail = (f"New all-time record (previous: {res['previous']})." if res["previous"] is not None
              else "One of the wildest games of the season.")
    legende = legendes(f"{chiffre} in one game 🤯 {score}", f"{detail} {PHASE.get(g['phase'], '')}, {jour}.",
                       "Where was the defense?", "#record",
                       f"{chiffre} in one game: {score} | AI football")
    return seg[1]["top"] if len(seg) > 2 else {"kicker": "", "title": "", "sub": ""}, seg, info, legende


def plan_franchise(res, doc):
    """Histoire d'une franchise (≈ 22 s) : carton palmarès, carton du joueur légendaire, ses plus belles actions,
    carton snapline.live. (Le style et l'identité de la bible sont en français : la vidéo, en anglais, ne les montre pas.)"""
    t, f, b = res["team"], res["fiche"], res["bilan"]
    nom = f.get("name", t)
    co = f.get("coordinators") or {}
    bilan = f"{b['w']}-{b['l']}" + (f"-{b['t']}" if b.get("t") else "")
    lieu = " · ".join(x for x in (f"{f['conference']} conference" if f.get("conference") else "",
                                  f"{f['division']} division" if f.get("division") else "") if x)
    seg = [{"type": "stats", "kicker": "Franchise story", "title": nom,
            "sub": lieu + (f" · AI coordinators {co.get('offense')} & {co.get('defense')}" if co else ""), "team": t,
            "stats": [{"v": b["seasons"], "l": "Seasons"}, {"v": bilan, "l": "Regular season"},
                      {"v": b["titles"], "l": "Titles"}, {"v": b["finals"], "l": "Grand Finals"}], "dur": 3.6}]
    j = res["legende"]
    if j:
        seg.append({"type": "stats", "kicker": "Franchise legend", "title": j["name"],
                    "sub": f"{POSTE.get(j['pos'], j['pos'])} · {j['seasons']} season{'s' if j['seasons'] > 1 else ''} with {t}",
                    "team": t, "stats": chiffres_joueur(j), "dur": 3.2})
    seg += _segments_actions(res["actions"], {a["dossier"]: C.charger_semaine(a["dossier"])[0] for a in res["actions"]},
                             {"kicker": "AI vs AI · franchise story", "title": nom})
    seg.append(dict(FIN))
    info = {"type": "franchise", "team": t, "bilan": b, "legende": j and {"id": j["id"], "name": j["name"]},
            "plays": [{"game": a["game"], "index": a["index"]} for a in res["actions"]]}
    star = ""
    if j:
        x = chiffres_joueur(j)[0]
        star = f" Franchise legend: {j['name']} ({x['v']:,} {x['l']})."
    legende = legendes(f"The story of the {nom} 🏈",
                       f"{b['seasons']} seasons, {bilan}, {b['titles']} title{'s' if b['titles'] != 1 else ''}.{star}",
                       "Which franchise should we feature next?", "#franchise",
                       f"The story of the {nom} | AI football")
    top = next((x["top"] for x in seg if x["type"] == "play"), {"kicker": "", "title": "", "sub": ""})
    return top, seg, info, legende


# ------------------------------------------------------------------ tournage
def serveur(port):
    data = tempfile.mkdtemp(prefix="gc-video-")
    os.symlink(os.path.join(RACINE, "data", "weeks"), os.path.join(data, "weeks"))
    env = dict(os.environ, GC_DATA=data, GC_TEST_HOOK="1", GC_PUSH_LOOP="0")
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "serveur:app", "--port", str(port)], cwd=RACINE, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(240):
        try:
            urllib.request.urlopen(f"http://localhost:{port}/api/time", timeout=2)
            return p, data
        except Exception:
            time.sleep(0.5)
    p.kill()
    raise SystemExit("le serveur ne démarre pas")


def semaine_du(jour):
    """La semaine qui contient ce jour (la dernière qui commence avant lui : le samedi, la semaine suivante est déjà
    dans le dépôt, mais on filme celle qui se joue)."""
    base = os.path.join(RACINE, "data", "weeks")
    ws = sorted(d for d in os.listdir(base) if d.startswith("week_") and d[5:] <= jour)
    if not ws:
        raise SystemExit(f"aucune semaine ne contient le {jour}")
    return os.path.join(base, ws[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("type", choices=("action", "resume", "presentation", "joueur", "champion", "chiffres", "franchise"))
    ap.add_argument("--jour")
    ap.add_argument("--match")
    ap.add_argument("--meilleure", action="store_true", help="action : la plus belle de toutes les semaines (matchs terminés)")
    ap.add_argument("--long", action="store_true", help="resume : la version longue (2 à 3 min), à la demande")
    ap.add_argument("--semaine")
    ap.add_argument("--sortie", default="videos")
    ap.add_argument("--port", type=int, default=8150)
    a = ap.parse_args()
    jour = a.jour or (datetime.now(C.TZ) - timedelta(hours=3)).date().isoformat()   # la journée qui vient de finir
    toutes = glob.glob(os.path.join(RACINE, "data", "weeks", "week_*"))
    if a.type in ("chiffres", "franchise"):
        dossier = a.semaine or semaine_du(jour)
        res = (C.match_hors_norme(dossier, datetime.now(C.TZ), toutes) if a.type == "chiffres"
               else C.franchise_de_la_semaine(dossier, toutes, datetime.now(C.TZ)))
        if not res:
            print("aucun match hors norme cette semaine : pas de vidéo")      # pas une erreur : le workflow continue
            return
    elif a.type in ("joueur", "champion"):
        dossier = a.semaine or semaine_du(jour)
        res = (C.joueur_de_la_semaine(dossier, datetime.now(C.TZ)) if a.type == "joueur"
               else C.champion(dossier, datetime.now(C.TZ), toutes))
        if not res or not res["actions"]:
            raise SystemExit("pas encore de match terminé" if a.type == "joueur" else "la Grand Final n'est pas terminée")
    elif a.type == "presentation":
        choix = C.trois_actions(toutes, datetime.now(C.TZ))
        if len(choix) < 3:
            raise SystemExit("pas assez de matchs terminés")
        dossier = choix[0]["dossier"]
    elif a.type == "action" and a.meilleure:
        m = C.meilleure_action(toutes, datetime.now(C.TZ))
        if not m:
            raise SystemExit("aucun match terminé")
        dossier = m["dossier"]
    else:
        dossier = a.semaine or semaine_du(jour)
    doc, feeds = C.charger_semaine(dossier)
    if a.type == "chiffres":
        top, seg, info, legende = plan_chiffres(res, doc, feeds)
        g = next(x for x in doc["schedule"] if x["id"] == res["game"])
        nom = f"match-hors-norme-{g['id']}"
    elif a.type == "franchise":
        top, seg, info, legende = plan_franchise(res, doc)
        g = next((x for x in C.charger_semaine(res["actions"][0]["dossier"])[0]["schedule"] if x["id"] == res["actions"][0]["game"]),
                 None) if res["actions"] else None
        if g is None:
            raise SystemExit("aucune action de cette franchise")
        nom = f"franchise-{res['team']}-{os.path.basename(dossier)[5:]}"
    elif a.type in ("joueur", "champion"):
        top, seg, info, legende = (plan_joueur if a.type == "joueur" else plan_champion)(res, doc)
        g = next(x for x in doc["schedule"] if x["id"] == res["actions"][0]["game"])
        nom = f"{'joueur-de-la-semaine' if a.type == 'joueur' else 'champion'}-{os.path.basename(dossier)[5:]}"
    elif a.type == "presentation":
        semaines = {c["dossier"]: C.charger_semaine(c["dossier"])[0] for c in choix}
        top, seg, info, legende = plan_presentation(choix, semaines)
        g = next(x for x in doc["schedule"] if x["id"] == choix[0]["game"])
        nom = f"presentation-{jour}"
    elif a.type == "action" and a.meilleure:
        g, seg, top, info, legende = plan_action(doc, feeds, jour, m)
        nom = f"meilleure-action-{jour}"
    elif a.type == "action":
        g, seg, top, info, legende = plan_action(doc, feeds, jour)
        nom = f"action-du-jour-{jour}"
    else:
        g, seg, top, info, legende = plan_resume(doc, feeds, a.match, a.long)
        nom = f"resume-{'long-' if a.long else ''}{g['id']}"
    sortie = os.path.abspath(a.sortie)
    os.makedirs(sortie, exist_ok=True)
    travail = tempfile.mkdtemp(prefix="gc-film-")
    premier = next((x["feed"] for x in seg if x.get("feed")), os.path.join(dossier, g["feed"]))   # match ouvert d'abord
    plan = {"url": f"http://localhost:{a.port}/", "feed": premier, "out": travail,
            "top": top, "segments": seg, "coaches": coordinateurs(doc)}
    with open(os.path.join(travail, "plan.json"), "w", encoding="utf-8") as fh:
        json.dump(plan, fh)
    p, data = serveur(a.port)
    try:
        subprocess.run(["node", os.path.join(ICI, "filmer.js"), os.path.join(travail, "plan.json")], check=True)
    finally:
        p.kill()
        shutil.rmtree(data, ignore_errors=True)
    with open(os.path.join(travail, "timeline.json"), encoding="utf-8") as fh:
        tl = json.load(fh)
    son = os.path.join(travail, "son.m4a")
    mixer_son(tl, son)
    mp4 = os.path.join(sortie, nom + ".mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(travail, "images", "images.txt"),
                    "-i", son, "-vf", "fps=60,scale=1080:1920:flags=lanczos,format=yuv420p", "-c:v", "libx264",
                    "-profile:v", "high", "-level", "4.2", "-crf", "14", "-maxrate", "24M", "-bufsize", "48M",
                    "-preset", "slow", "-tune", "animation", "-g", "60", "-c:a", "copy", "-shortest",
                    "-movflags", "+faststart", mp4], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1.2", "-i", mp4, "-frames:v", "1", "-q:v", "2",
                    os.path.join(sortie, nom + "-cover.jpg")], check=True)        # la couverture à choisir sur TikTok
    with open(os.path.join(sortie, nom + ".txt"), "w", encoding="utf-8") as fh:
        fh.write(legende + "\n")
    with open(os.path.join(sortie, nom + ".json"), "w", encoding="utf-8") as fh:
        json.dump(dict(info, duree=round(tl["end"], 1), video=os.path.basename(mp4), cover=nom + "-cover.jpg"), fh, ensure_ascii=False, indent=1)
    shutil.rmtree(travail, ignore_errors=True)
    print(f"{mp4} · {tl['end']:.1f} s · {json.dumps(info, ensure_ascii=False)[:200]}")


if __name__ == "__main__":
    main()
