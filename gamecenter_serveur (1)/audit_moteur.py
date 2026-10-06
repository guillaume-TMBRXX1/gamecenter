"""Audit du moteur : contrôle chaque action de chaque match d'une ou plusieurs semaines exportées.

    python3 audit_moteur.py data/weeks                  # toutes les semaines du dossier
    python3 audit_moteur.py data/weeks/week_2026-10-12  # une semaine
    python3 audit_moteur.py data/weeks --json rapport.json

Code de sortie 1 si une anomalie BLOQUANTE est trouvée (score faux, horloge qui recule, match sans fin…) :
le calcul du samedi (GitHub) s'arrête alors AVANT de publier la semaine.
Les ALERTES (statistiques inhabituelles) sont signalées sans bloquer.
"""
import json, os, sys, glob, statistics
from collections import Counter, defaultdict

try:                                    # bloc E (V26) : notes effectives et contrôles de l'état des joueurs
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from moteur import developpement as _dev
except Exception:                       # audit sans le dossier moteur/ : contrôles du bloc E réduits
    _dev = None

BLOQUANT, ALERTE = "BLOQUANT", "ALERTE"


class Audit:
    def __init__(self):
        self.items = []            # (niveau, semaine, match, seq, message)
        self.counts = Counter()

    def add(self, lvl, week, gid, seq, msg):
        self.items.append((lvl, week, gid, seq, msg))
        self.counts[lvl] += 1


def other(side):
    return "away" if side == "home" else "home"


def check_game(A, week, g_sched, feed):
    gid = g_sched["id"]
    game, plays = feed["game"], feed["plays"]
    qs = game.get("quarter_seconds", 180)
    bad = lambda seq, m: A.add(BLOQUANT, week, gid, seq, m)
    warn = lambda seq, m: A.add(ALERTE, week, gid, seq, m)
    if not plays:
        bad(None, "match sans aucune action"); return None
    prev = None
    halves = 0
    score = {"home": 0, "away": 0}
    for i, p in enumerate(plays):
        s, a = p["seq"], p["after"]
        if s != i + 1:
            bad(s, f"numérotation : action {s} à la position {i + 1}")
        q = p["quarter"]
        if q < 1 or q > 5:
            bad(s, f"quart-temps impossible : {q}")
        if not (0 <= p["clock_end"] <= p["clock_start"] <= qs):
            bad(s, f"horloge incohérente : {p['clock_start']} → {p['clock_end']} (quart de {qs} s)")
        if p["result"] != "kickoff" and p["down"] is not None:
            if p["down"] not in (1, 2, 3, 4):
                bad(s, f"down impossible : {p['down']}")
            if p["to_go"] is None or p["to_go"] <= 0:
                bad(s, f"distance à franchir impossible : {p['to_go']}")
        for k in ("los_x",):
            if p[k] is None or not (0 <= p[k] <= 120):
                bad(s, f"{k} hors du terrain : {p[k]}")
        if p.get("win_prob_home") is not None and not (0 <= p["win_prob_home"] <= 1):
            bad(s, f"probabilité de victoire hors [0,1] : {p['win_prob_home']}")
        # --- score : jamais en baisse, sauts possibles 0/2/3/6/7/8 ---
        ns = a["score"]
        dh, da = ns["home"] - score["home"], ns["away"] - score["away"]
        if dh < 0 or da < 0:
            bad(s, f"le score recule : {score} → {ns}")
        for side, d in (("home", dh), ("away", da)):
            if d not in (0, 2, 3, 6, 7, 8):
                bad(s, f"saut de score impossible pour {side} : +{d}")
        if dh and da:
            bad(s, "les deux équipes marquent sur la même action")
        scorer = "home" if dh else "away" if da else None
        r = p["result"]
        if r == "touchdown" and not scorer:
            bad(s, "touchdown sans points")
        if r == "field_goal_good" and (scorer != p["offense"] or (dh or da) != 3):
            bad(s, f"field goal réussi mal compté ({dh}/{da})")
        if r == "safety" and (scorer is None or scorer == p["offense"] or (dh or da) != 2):
            bad(s, f"safety mal compté ({dh}/{da}) : 2 points pour la défense")
        if r in ("incomplete", "punt", "field_goal_missed", "kickoff") and scorer:
            bad(s, f"des points sur une action « {r} »")
        if r in ("run", "complete") and scorer:
            warn(s, f"points sur « {r} » sans touchdown (+{dh or da})")
        score = dict(ns)
        # --- continuité avec l'action précédente ---
        if prev is not None:
            pa = prev["after"]
            if pa["status"] == "final":
                bad(s, "action après la fin du match")
            same_q = prev["quarter"] == q
            if same_q and p["clock_start"] != prev["clock_end"]:
                bad(s, f"l'horloge saute : fin {prev['clock_end']} s → début {p['clock_start']} s")
            if not same_q:
                if q != prev["quarter"] + 1:
                    bad(s, f"quart-temps sauté : {prev['quarter']} → {q}")
                if prev["clock_end"] != 0:
                    warn(s, f"quart-temps {prev['quarter']} terminé à {prev['clock_end']} s")
                if p["clock_start"] != qs and q <= 4:
                    warn(s, f"quart-temps {q} commence à {p['clock_start']} s")
            if pa["status"] == "live":
                if p["offense"] != pa["offense"]:
                    bad(s, f"le ballon change d'équipe entre deux actions ({pa['offense']} → {p['offense']})")
                if p["los_x"] != pa["los_x"]:
                    bad(s, f"le ballon se déplace entre deux actions ({pa['los_x']} → {p['los_x']})")
                if p["result"] != "kickoff" and pa["down"] is not None and (p["down"], p["to_go"]) != (pa["down"], pa["to_go"]):
                    bad(s, f"down / distance changent entre deux actions ({pa['down']}&{pa['to_go']} → {p['down']}&{p['to_go']})")
        # --- changements de possession ---
        pc = p["possession_change"]
        if a["status"] == "live":
            if pc in ("punt", "turnover", "downs", "missed_fg") and a["offense"] == p["offense"]:
                bad(s, f"« {pc} » mais la même équipe garde le ballon")
            if pc is None and r != "kickoff" and a["offense"] != p["offense"]:
                bad(s, "changement d'équipe sans raison")
            if r in ("interception", "fumble_lost") and pc not in ("turnover", "score"):
                bad(s, f"« {r} » sans changement de possession ({pc})")
            if p["down"] == 4 and pc is None and a["down"] != 1 and r not in ("kickoff",):
                bad(s, f"4e tentative ratée sans perte du ballon ({r}, gain {p['gain']} sur {p['to_go']})")
            # progression des tentatives
            if pc is None and r in ("run", "complete", "incomplete", "sack") and p["down"]:
                gained = (p["gain"] or 0) >= p["to_go"]
                if gained and a["down"] != 1:
                    bad(s, f"premier essai obtenu (+{p['gain']} sur {p['to_go']}) mais down {a['down']}")
                if not gained and a["down"] != p["down"] + 1:
                    bad(s, f"tentative {p['down']} → {a['down']} sans premier essai (+{p['gain']} sur {p['to_go']})")
        if a["status"] == "half":
            halves += 1
            if q != 2:
                bad(s, f"mi-temps au quart-temps {q}")
        # --- joueurs ---
        pl = p.get("players") or {}
        if r in ("run", "complete", "touchdown") and p["call"]["type"] in ("run", "pass") and not (pl.get("carrier") or {}).get("name"):
            warn(s, f"« {r} » sans porteur du ballon")
        if p["call"]["type"] == "pass" and r in ("complete", "incomplete", "interception") and not pl.get("passer"):
            warn(s, "passe sans passeur")
        # --- ajustements des coordinateurs (V21) et du plan de jeu (bloc D, V25) ---
        for x in p.get("adjust") or []:
            if x.get("team") not in ("home", "away") or not x.get("text"):
                bad(s, f"ajustement mal formé : {x}")
            elif x.get("kind") in ("o_quick", "o_protect", "o_away", "d_bracket", "d_rotate", "d_disguise") and not x.get("reason"):
                warn(s, f"ajustement « {x['kind']} » sans raison")
        # --- cotes en direct ---
        o = p.get("odds") or {}
        if a["status"] == "live" and o.get("ml"):
            for side, v in o["ml"].items():
                if v is None or abs(v) < 100:
                    bad(s, f"cote américaine impossible pour {side} : {v}")
            if o.get("total") is not None and o["total"] < ns["home"] + ns["away"]:
                bad(s, f"total en direct ({o['total']}) sous les points déjà marqués ({ns['home'] + ns['away']})")
        prev = p
    last = plays[-1]
    if last["after"]["status"] != "final":
        bad(last["seq"], "le match ne se termine pas (dernière action non finale)")
    if halves != 1:
        bad(None, f"{halves} mi-temps au lieu d'une")
    fs = game.get("final_score")
    if fs != last["after"]["score"]:
        bad(None, f"score final {fs} ≠ score de la dernière action {last['after']['score']}")
    res = g_sched.get("result") or {}
    if fs and (res.get("home"), res.get("away")) != (fs["home"], fs["away"]):
        bad(None, f"résultat du calendrier {res} ≠ score final {fs}")
    if g_sched["phase"] != "regular" and fs and fs["home"] == fs["away"]:
        bad(None, "match de playoffs terminé à égalité")
    if last["clock_end"] != 0 and not game.get("overtime"):
        warn(last["seq"], f"match fini avec {last['clock_end']} s au chrono sans prolongation")
    gp = game.get("gameplan")
    if gp is not None and not (set(gp) <= {"home", "away"} and all(isinstance(v, dict) for v in gp.values())):
        bad(None, f"plan de jeu mal formé : {gp}")
    po = game.get("pregame_odds") or {}
    if not po.get("ml"):
        bad(None, "pas de cotes d'avant-match")
    ratings = {}
    for side in ("home", "away"):                       # bloc E (V26) : roster[].progression
        for r in (game.get(side) or {}).get("roster") or []:
            ratings[r["id"]] = r.get("ratings") or {}
            pg = r.get("progression")
            if pg is None:
                continue
            if any(not 40 <= v <= 99 for v in (r.get("ratings") or {}).values()):
                bad(None, f"{r['id']} : note hors 40-99 {r['ratings']}")
            if {k: pg["base"][k] + d for k, d in (pg.get("delta") or {}).items()} != (r.get("ratings") or {}):
                bad(None, f"{r['id']} : notes ≠ base + écart ({r.get('ratings')} / {pg.get('base')} / {pg.get('delta')})")
            if abs(pg.get("form", 0)) > 3.0 + 1e-9:
                bad(None, f"{r['id']} : forme {pg.get('form')} hors ± 3")
            if not pg.get("history"):
                warn(None, f"{r['id']} : courbe de progression vide")
    return {"plays": len(plays), "pts": (fs or {}).get("home", 0) + (fs or {}).get("away", 0),
            "home": fs["home"] if fs else 0, "away": fs["away"] if fs else 0,
            "tie": bool(fs and fs["home"] == fs["away"]), "ot": bool(game.get("overtime")),
            "res": Counter(p["result"] for p in plays),
            "td_len": [p["gain"] for p in plays if p["result"] == "touchdown" and p["gain"] is not None],
            "ratings": ratings}


def check_week(A, folder):
    name = os.path.basename(os.path.normpath(folder))
    w = json.load(open(os.path.join(folder, "week.json"), encoding="utf-8"))
    sched = w["schedule"]
    stats = []
    for g in sched:
        try:
            feed = json.load(open(os.path.join(folder, g["feed"]), encoding="utf-8"))
        except Exception as e:
            A.add(BLOQUANT, name, g["id"], None, f"fichier du match illisible : {e}"); continue
        st = check_game(A, name, g, feed)
        if st:
            st["phase"] = g["phase"]; st["id"] = g["id"]; stats.append(st)
    # --- semaine ---
    vues = {}                                           # bloc E : notes figées pendant toute la semaine
    for st in stats:
        for pid, r in st.pop("ratings", {}).items():
            if vues.setdefault(pid, r) != r:
                A.add(BLOQUANT, name, st["id"], None, f"{pid} : notes qui changent pendant la semaine ({vues[pid]} / {r})")
    check_progression(A, name, w)
    reg = [g for g in sched if g["phase"] == "regular"]
    teams = list(w["teams"]) if isinstance(w["teams"], dict) else [t["abbr"] for t in w["teams"]]
    per = Counter()
    pairs = Counter()
    for g in reg:
        per[g["home"]] += 1; per[g["away"]] += 1
        pairs[tuple(sorted((g["home"], g["away"])))] += 1
    # 4 équipes : 36 matchs, 18 par équipe, chaque affiche 6 fois ; étape 6, 8 équipes : 56, 14, 2 (aller-retour)
    nslots = max((g["slot"] for g in reg), default=0)
    if len(reg) != len(teams) // 2 * nslots or any(per[t] != nslots for t in teams):
        A.add(BLOQUANT, name, None, None, f"calendrier : {len(reg)} matchs, par équipe {dict(per)}")
    if len(pairs) != len(teams) * (len(teams) - 1) // 2 or len(set(pairs.values())) != 1:
        A.add(BLOQUANT, name, None, None, f"affiches : {dict(pairs)}")
    # classement recalculé à partir des résultats
    wins = Counter(); ties = Counter()
    for g in reg:
        r = g["result"]
        if r["home"] > r["away"]: wins[g["home"]] += 1
        elif r["away"] > r["home"]: wins[g["away"]] += 1
        else: ties[g["home"]] += 1; ties[g["away"]] += 1
    for row in w.get("standings") or []:
        t = row.get("team")
        if t and ("wins" in row or "w" in row):
            ww = row.get("wins", row.get("w"))
            if ww != wins[t]:
                A.add(BLOQUANT, name, None, None, f"classement : {t} a {ww} victoires, les résultats en donnent {wins[t]}")
    final = next((g for g in sched if g["phase"] == "ai_bowl"), None)
    if final and final.get("result"):
        r = final["result"]; champ = final["home"] if r["home"] > r["away"] else final["away"]
        if w.get("champion") != champ:
            A.add(BLOQUANT, name, None, None, f"champion {w.get('champion')} ≠ vainqueur de l'AI Bowl {champ}")
    semis = [g for g in sched if g["phase"] == "semifinal"]
    if final and semis and all(g.get("result") for g in semis):
        winners = {g["home"] if g["result"]["home"] > g["result"]["away"] else g["away"] for g in semis}
        if {final["home"], final["away"]} != winners:
            A.add(BLOQUANT, name, None, None, f"AI Bowl {final['home']}–{final['away']} ≠ vainqueurs des demi-finales {winners}")
    return stats


def check_progression(A, name, w):
    """Bloc E (V26) : état des joueurs pour la semaine suivante (players_next_week) et rapport (progression)."""
    etat, rap = w.get("players_next_week"), w.get("progression")
    if etat is None:
        return
    J = etat.get("joueurs") or {}
    roster = {r["id"] for t in (w["teams"].values() if isinstance(w["teams"], dict) else w["teams"]) for r in t.get("roster") or []}
    if roster and set(J) != roster:
        A.add(BLOQUANT, name, None, None, f"players_next_week : {len(J)} joueurs pour {len(roster)} au roster")
    if _dev is not None:
        for pb in _dev.controler(etat):
            A.add(BLOQUANT, name, None, None, f"players_next_week : {pb}")
    if etat.get("semaines", 0) < 1:
        A.add(BLOQUANT, name, None, None, "players_next_week : aucune semaine de progression comptée")
    e_max = _dev.ECART_EQUIPE_MAX if _dev is not None else 3.0
    f_max = _dev.FORCE_EQUIPE_MAX if _dev is not None else None
    for t, us in ((rap or {}).get("team_units") or {}).items():
        for u, d in us.items():
            if abs(d) > e_max + 1e-6:
                A.add(BLOQUANT, name, None, None, f"progression : {t} {u} à {d:+.2f} de sa base (± {e_max} au plus)")
    for t, f in ((rap or {}).get("team_strength") or {}).items():
        if f_max is not None and abs(f) > f_max + 0.005:
            A.add(BLOQUANT, name, None, None, f"progression : force de {t} à {f:+.2f} de sa base (± {f_max} au plus)")
    if rap and rap.get("league_drift_max", 0) > 0.5:
        A.add(ALERTE, name, None, None, f"progression : dérive de la ligue {rap['league_drift']}")


def stat_alerts(A, stats, label):
    """Alertes statistiques sur l'ensemble des matchs (repères mesurés sur 1 008 matchs, fiche technique)."""
    if not stats:
        return {}
    pts = [s["pts"] for s in stats]; npl = [s["plays"] for s in stats]
    hw = sum(1 for s in stats if s["home"] > s["away"]) / len(stats)
    ties = sum(s["tie"] for s in stats)
    tot = Counter(); [tot.update(s["res"]) for s in stats]
    tdl = [x for s in stats for x in s["td_len"]]
    summ = {"matchs": len(stats), "points_moyens": round(statistics.mean(pts), 1), "points_min": min(pts), "points_max": max(pts),
            "actions_moyennes": round(statistics.mean(npl), 1), "actions_min": min(npl), "actions_max": max(npl),
            "victoires_domicile": round(hw, 3), "nuls": ties, "prolongations": sum(s["ot"] for s in stats),
            "par_match": {k: round(v / len(stats), 2) for k, v in tot.most_common()},
            "td_longueur_moyenne": round(statistics.mean(tdl), 1) if tdl else None}
    for s in stats:
        if s["pts"] > 120: A.add(ALERTE, label, s["id"], None, f"score très élevé : {s['home']}-{s['away']}")
        if s["pts"] < 6: A.add(ALERTE, label, s["id"], None, f"score très bas : {s['home']}-{s['away']}")
        if not 90 <= s["plays"] <= 220: A.add(ALERTE, label, s["id"], None, f"nombre d'actions inhabituel : {s['plays']}")
    return summ


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_json = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    if out_json in args: args.remove(out_json)
    root = args[0] if args else "data/weeks"
    folders = [root] if os.path.exists(os.path.join(root, "week.json")) else sorted(
        d for d in glob.glob(os.path.join(root, "week_*")) if os.path.exists(os.path.join(d, "week.json")))
    A = Audit(); allstats = []; per_week = {}
    # deux semaines ne doivent jamais rejouer les mêmes matchs (même numéro de semaine = mêmes graines)
    sig = {}
    for f in folders:
        w = json.load(open(os.path.join(f, "week.json"), encoding="utf-8"))
        key = json.dumps([(g["home"], g["away"], g.get("result")) for g in w["schedule"] if g["phase"] == "regular"])
        idx = w["week"].get("index")
        for other_name, (okey, oidx) in sig.items():
            if okey == key:
                A.add(BLOQUANT, os.path.basename(f), None, None, f"semaine identique à {other_name} (mêmes résultats : mêmes graines)")
            elif idx is not None and idx == oidx:
                A.add(BLOQUANT, os.path.basename(f), None, None, f"même numéro de semaine ({idx}) que {other_name} : graines identiques")
        sig[os.path.basename(f)] = (key, idx)
    for f in folders:
        st = check_week(A, f)
        per_week[os.path.basename(f)] = stat_alerts(A, st, os.path.basename(f))
        allstats += st
    total = stat_alerts(Audit(), allstats, "total")
    print(f"Audit du moteur — {len(folders)} semaine(s), {total.get('matchs', 0)} matchs, "
          f"{sum(s['plays'] for s in allstats)} actions")
    print(f"  {A.counts[BLOQUANT]} anomalie(s) bloquante(s), {A.counts[ALERTE]} alerte(s)")
    for lvl in (BLOQUANT, ALERTE):
        byk = defaultdict(list)
        for it in A.items:
            if it[0] == lvl:
                byk[it[4].split(" :")[0].split(" (")[0]].append(it)
        for k, its in sorted(byk.items(), key=lambda kv: -len(kv[1])):
            ex = its[0]
            print(f"  [{lvl}] {k} — {len(its)} fois · ex. {ex[1]} {ex[2]} action {ex[3]} : {ex[4]}")
    print("  Repères :", json.dumps(total, ensure_ascii=False))
    if out_json:
        json.dump({"bloquant": A.counts[BLOQUANT], "alertes": A.counts[ALERTE], "total": total, "semaines": per_week,
                   "anomalies": [dict(zip(("niveau", "semaine", "match", "action", "message"), it)) for it in A.items]},
                  open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sys.exit(1 if A.counts[BLOQUANT] else 0)


if __name__ == "__main__":
    main()
