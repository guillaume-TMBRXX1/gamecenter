"""Vidéos verticales pour les réseaux (bloc 2, étape 8) : MP4 1080×1920 + légende, à publier à la main.

    python outils/video/faire_video.py action [--jour AAAA-MM-JJ]   l'action du jour (≈ 20 s) ; jour par défaut : la
                                                                      veille au soir (heure de Bruxelles, 3 h de marge)
    python outils/video/faire_video.py resume [--match ID]          résumé d'un match (2 à 3 min) ; par défaut : le plus
                                                                      beau match de la semaine
    options : --semaine data/weeks/week_AAAA-MM-JJ (défaut : la dernière), --sortie videos/ (défaut), --port 8150

Le site rejoue l'action sur son terrain (serveur local avec le crochet de test ; outils/video/filmer.js filme le
navigateur), ffmpeg assemble les images et le son du stade (foule et effets du dépôt, audio/crowd et audio/sfx, calés
sur le snap et le résultat de chaque action). Depuis « gamecenter_serveur (1) » ; il faut Python avec fastapi/uvicorn,
Node avec Playwright (Chromium) et ffmpeg. Pas de commentaire ni de musique (choix du 12/10 : la musique se met au
moment de publier).
"""
import argparse
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


def horloge(P):
    q = P.get("quarter") or 1
    s = int(P.get("clock_start") or 0)
    qn = f"Q{q}" if q <= 4 else "OT"
    jeu = (P.get("call") or {}).get("type") in ("run", "pass")          # l'essai n'a de sens que sur une course ou une passe
    d = f" · {ORD.get(P.get('down'), '')} & {P.get('to_go')}" if jeu and P.get("down") and P.get("to_go") is not None else ""
    return f"{qn} {s // 60}:{s % 60:02d}{d}"


def titre_action(why, P):
    """Le grand titre du carton d'ouverture (court, en majuscules à l'écran)."""
    w = why.split(" · ")
    if w[0].startswith("game-winning") and len(w) > 1:
        return f"Game-winner: {w[1]}"
    if w[0].startswith("game-winning"):
        return "Game-winner"
    return w[0][:1].upper() + w[0][1:]


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
def plan_action(doc, feeds, jour):
    a = C.action_du_jour(doc, feeds, jour)
    if not a:
        raise SystemExit(f"aucun match le {jour}")
    g = next(x for x in doc["schedule"] if x["id"] == a["game"])
    P = a["play"]
    d = datetime.fromisoformat(jour)
    jour_txt = d.strftime("%A %-d %B")
    seg = [{"type": "card", "kicker": "Play of the day", "title": titre_action(a["why"], P),
            "sub": f"{jour_txt} · {g['away']} @ {g['home']} · {PHASE.get(g['phase'], '')}", "dur": 2.6},
           {"type": "play", "index": a["index"], "speed": 1, "label": horloge(P), "text": P.get("text"), "after": 2.4},
           {"type": "play", "index": a["index"], "speed": 0.5, "label": "Replay · slow motion", "text": P.get("text"), "after": 1.4},
           {"type": "card", "kicker": "Every game, played live by the engine", "title": "snapline.live",
            "sub": "Simulated football · new games every day · free to watch", "dur": 2.8}]
    top = {"kicker": f"Play of the day · {d.strftime('%a %-d %b')}", "title": f"{g['away']} @ {g['home']}",
           "sub": a["why"][:1].upper() + a["why"][1:]}
    info = {"type": "action", "game": g["id"], "index": a["index"], "why": a["why"], "note": a["note"], "jour": jour}
    legende = (f"Play of the day ({d.strftime('%-d %B')}): {a['why']} — {P.get('text')}. "
               f"{g['away']} @ {g['home']}, {PHASE.get(g['phase'], '')}.\n"
               "Every game simulated and played live on snapline.live\n\n"
               "#Snapline #AmericanFootball #Football #SportsSimulation #PlayOfTheDay")
    return g, seg, top, info, legende


def plan_resume(doc, feeds, gid=None):
    gid = gid or C.plus_beau_match(doc, feeds)["game"]
    g = next(x for x in doc["schedule"] if x["id"] == gid)
    F = feeds[gid]
    fs = F["game"].get("final_score") or F["plays"][-1]["after"]["score"]
    idx = C.resume(F)
    names = {s: (F["game"].get(s) or {}).get("name", g[s]) for s in ("home", "away")}
    jour = C.jour_du_match(g)
    d = datetime.fromisoformat(jour)
    seg = [{"type": "card", "kicker": "Game of the week" if gid else "Game recap", "title": f"{g['away']} @ {g['home']}",
            "sub": f"{names['away']} at {names['home']} · {PHASE.get(g['phase'], '')} · {d.strftime('%A %-d %B')}", "dur": 3.0}]
    q_avant = None
    for i in idx:
        P = F["plays"][i]
        q = P.get("quarter") or 1
        if q_avant is not None and q != q_avant:          # carton de fin de quart-temps : le score à ce moment
            fin_q = next(x for x in reversed(F["plays"][:i]) if (x.get("quarter") or 1) == q_avant)["after"]["score"]
            seg.append({"type": "card", "kind": "quarter", "kicker": {1: "End of Q1", 2: "Halftime", 3: "End of Q3"}.get(q_avant, "End of regulation"),
                        "title": f"{g['away']} {fin_q['away']} – {fin_q['home']} {g['home']}", "sub": "", "dur": 2.2})
        q_avant = q
        seg.append({"type": "play", "index": i, "speed": 1, "label": horloge(P), "text": P.get("text"), "after": 1.6})
    gagnant = "home" if fs["home"] > fs["away"] else "away"
    seg.append({"type": "card", "kicker": "Final" + (" · OT" if any((P.get("quarter") or 0) >= 5 for P in F["plays"]) else ""),
                "title": f"{g['away']} {fs['away']} – {fs['home']} {g['home']}",
                "sub": f"{names[gagnant]} win · watch every game live on snapline.live", "dur": 3.5})
    top = {"kicker": f"Game of the week · {d.strftime('%a %-d %b')}", "title": f"{g['away']} @ {g['home']}",
           "sub": PHASE.get(g["phase"], "")}
    info = {"type": "resume", "game": gid, "plays": idx, "spectacle": C.spectacle(F, g)}
    legende = (f"Game of the week: {names['away']} at {names['home']}, {fs['away']}–{fs['home']} "
               f"({PHASE.get(g['phase'], '')}, {d.strftime('%-d %B')}). Every score, every turnover, the final drive.\n"
               "Every game simulated and played live on snapline.live\n\n"
               "#Snapline #AmericanFootball #Football #SportsSimulation #GameRecap")
    return g, seg, top, info, legende


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
    ap.add_argument("type", choices=("action", "resume"))
    ap.add_argument("--jour")
    ap.add_argument("--match")
    ap.add_argument("--semaine")
    ap.add_argument("--sortie", default="videos")
    ap.add_argument("--port", type=int, default=8150)
    a = ap.parse_args()
    jour = a.jour or (datetime.now(C.TZ) - timedelta(hours=3)).date().isoformat()   # la journée qui vient de finir
    dossier = a.semaine or semaine_du(jour)
    doc, feeds = C.charger_semaine(dossier)
    if a.type == "action":
        g, seg, top, info, legende = plan_action(doc, feeds, jour)
        nom = f"action-du-jour-{jour}"
    else:
        g, seg, top, info, legende = plan_resume(doc, feeds, a.match)
        nom = f"resume-{g['id']}"
    sortie = os.path.abspath(a.sortie)
    os.makedirs(sortie, exist_ok=True)
    travail = tempfile.mkdtemp(prefix="gc-film-")
    plan = {"url": f"http://localhost:{a.port}/", "feed": os.path.join(dossier, g["feed"]), "out": travail,
            "top": top, "segments": seg}
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
                    "-i", son, "-vf", "fps=30,scale=1080:1920:flags=lanczos,format=yuv420p", "-c:v", "libx264",
                    "-profile:v", "high", "-crf", "19", "-preset", "medium", "-c:a", "copy", "-shortest",
                    "-movflags", "+faststart", mp4], check=True)
    with open(os.path.join(sortie, nom + ".txt"), "w", encoding="utf-8") as fh:
        fh.write(legende + "\n")
    with open(os.path.join(sortie, nom + ".json"), "w", encoding="utf-8") as fh:
        json.dump(dict(info, duree=round(tl["end"], 1), video=os.path.basename(mp4)), fh, ensure_ascii=False, indent=1)
    shutil.rmtree(travail, ignore_errors=True)
    print(f"{mp4} · {tl['end']:.1f} s · {json.dumps(info, ensure_ascii=False)[:200]}")


if __name__ == "__main__":
    main()
