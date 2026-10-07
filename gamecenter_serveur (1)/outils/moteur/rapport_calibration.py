#!/usr/bin/env python3
"""Rapport de calibration automatique du programme ENGINE INTELLIGENCE (garde-fou 3).

Charge le moteur du notebook (cellules de code jusqu'à 12.2 quinquies incluse, sans Jupyter), joue le test
d'équilibre de 12.3 (chaque franchise reçoit chacune des autres : 84 graines à 4 équipes, 18 à 8 -> 1 008 matchs,
mêmes graines que le notebook) et mesure : passes (complétion, sacks, INT, YPA, yards / tentative nette), courses, pertes de
balle, points, drives, premiers downs, actions, équilibre par équipe, temps par match. Avec les décisions
allumées, ajoute les stats des décisions (cible réelle, première lecture, pression, scramble, throwaway).

    python3 outils/moteur/rapport_calibration.py --decisions off --sortie /tmp/v21.json        # référence
    python3 outils/moteur/rapport_calibration.py --decisions on  --reference /tmp/v21.json     # comparaison
    python3 outils/moteur/rapport_calibration.py --decisions on --graines 20                   # rapide (240 matchs)
    python3 outils/moteur/rapport_calibration.py --decisions on --bloc-b off                   # décisions du bloc A
    python3 outils/moteur/rapport_calibration.py --decisions on --bloc-c off                   # blocs A + B (V23)
    python3 outils/moteur/rapport_calibration.py --decisions on --bloc-d off                   # blocs A + B + C (V24)
    python3 outils/moteur/rapport_calibration.py --decisions on --bloc-e off                   # blocs A-D (V25)
    python3 outils/moteur/rapport_calibration.py --decisions on --expansion off                # V26 (sans l'extension)
    python3 outils/moteur/rapport_calibration.py --decisions on --fin-periode off              # V27 (sans la fin de période)
    python3 outils/moteur/rapport_calibration.py --decisions on --semaines 12                  # bloc E : rosters après
                                                                                               # 12 semaines de progression

Code de sortie 1 si une mesure sort de sa tolérance (TOLERANCES, à valider par Guillaume).
"""
import argparse, contextlib, io, json, linecache, os, statistics, sys, tempfile, time, types
import __future__

HERE = os.path.dirname(os.path.abspath(__file__))
SERVEUR = os.path.abspath(os.path.join(HERE, "..", ".."))
NOTEBOOK = os.path.join(SERVEUR, "NFL_Sim_GameCenter.ipynb")
JUSQUA = "12.2 undecies"          # fin de période (V27 : « 12.2 decies », V26 : « 12.2 nonies »…)

# tolérances proposées (bloc A, 04/10/2026) : écart absolu toléré par rapport à la référence V21
TOLERANCES = {
    "completion_pct":   0.020,    # ± 2 points de %
    "sack_rate":        0.010,    # sacks / dropback, ± 1 point
    "int_rate":         0.005,    # INT / tentative, ± 0,5 point
    "ypa":              0.30,     # yards / tentative (passes complétées), ± 0,3
    "net_ypa":          0.30,     # yards nets / dropback (sacks et scrambles compris), ± 0,3
    "ypc":              0.20,     # yards / course, ± 0,2
    "turnovers_pg":     0.30,     # pertes de balle / match (les deux équipes), ± 0,3 (cible ≈ 3,5)
    "points_pg":        2.0,      # points / match (les deux équipes), ± 2
    "drives_pg":        1.0,      # drives / match, ± 1
    "first_downs_pg":   2.0,      # premiers downs / match, ± 2
    "plays_pg":         5.0,      # actions offensives / match, ± 5
    "pass_rate":        0.020,    # part des dropbacks dans les appels, ± 2 points
}
EQUILIBRE = (0.40, 0.60)          # % de victoires de chaque franchise (test 12.3, inchangé)


def charger(notebook=NOTEBOOK, jusqua=JUSQUA, decisions=False, bloc_b=True, bloc_c=True, bloc_d=True, bloc_e=True,
            expansion=True, fin_periode=True):
    """Exécute les cellules de code du notebook jusqu'à celle dont l'en-tête contient `jusqua` (incluse)."""
    os.environ["GC_DECISIONS"] = "1" if decisions else "0"
    os.environ["GC_BLOC_B"] = "1" if bloc_b else "0"
    os.environ["GC_BLOC_C"] = "1" if bloc_c else "0"
    os.environ["GC_BLOC_D"] = "1" if bloc_d else "0"
    os.environ["GC_BLOC_E"] = "1" if bloc_e else "0"
    os.environ["GC_EXPANSION"] = "1" if expansion else "0"
    os.environ["GC_FIN_PERIODE"] = "1" if fin_periode else "0"
    os.environ.setdefault("GC_MOTEUR_DIR", SERVEUR)
    nb = json.load(open(notebook, encoding="utf-8"))
    mod = types.ModuleType("__nb__")
    sys.modules["__nb__"] = mod
    ns, flags, t0 = mod.__dict__, 0, time.time()
    here = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)                       # les cellules d'export écrivent dans le dossier courant
        try:
            for i, c in enumerate(nb["cells"]):
                if c["cell_type"] != "code":
                    continue
                src = "".join(c["source"])
                fn = f"<cellule {i}>"
                linecache.cache[fn] = (len(src), None, src.splitlines(True), fn)
                code = compile(src, fn, "exec", flags=flags, dont_inherit=True)
                flags |= code.co_flags & __future__.annotations.compiler_flag      # comme IPython : __future__ persiste
                with contextlib.redirect_stdout(io.StringIO()):
                    exec(code, ns)
                if jusqua in src[:400]:
                    return ns, time.time() - t0
        finally:
            os.chdir(here)
    raise SystemExit(f"cellule « {jusqua} » introuvable")


def mesurer(ns, graines=None, base=50_000):
    """Le test d'équilibre de 12.3 (mêmes graines), mesuré action par action."""
    teams = list(ns["AI_FRANCHISES"])
    graines = graines or (84 if len(teams) == 4 else max(1, round(1008 / (len(teams) * (len(teams) - 1)))))
    games, temps = [], []
    for h in teams:
        for a in teams:
            if h == a:
                continue
            for s in range(graines):
                t = time.perf_counter()
                games.append(ns["franchise_game"](h, a, seed=base + s))
                temps.append(time.perf_counter() - t)
    return games, temps


def _stats(games, temps, ns):
    n = len(games)
    c = dict(att=0, comp=0, inc=0, ints=0, sacks=0, scr=0, pass_yds=0, comp_yds=0, runs=0, run_yds=0,
             fum_lost=0, plays=0, first_downs=0, drives=0, points=0, dropbacks=0, safeties=0, games_safety=0)
    for g in games:
        c["points"] += g["home_score"] + g["away_score"]
        c["drives"] += len(g.get("drives") or [])
        log = [e for e in g["play_log"]]
        saf = sum((e.get("run_summary") or {}).get("termination_cause") == "SAFETY" for e in log)
        c["safeties"] += saf
        c["games_safety"] += saf > 0
        for i, e in enumerate(log):
            if e.get("kind") != "OFF":
                continue
            c["plays"] += 1
            out, y = e["outcome"], int(e["yards_gained"] or 0)
            d = e.get("decision") or {}
            scramble = d.get("action") == "SCRAMBLE" and e["play_type"] == "RUN"
            if e["play_type"] == "PASS" or scramble:
                c["dropbacks"] += 1
                c["pass_yds"] += y
            if scramble:
                c["scr"] += 1
            elif e["play_type"] == "RUN":
                c["runs"] += 1
                c["run_yds"] += y
            if e["play_type"] == "PASS":
                if out in ("SACK", "FUMBLE"):            # une passe ne perd le ballon que sur un sack (01)
                    c["sacks"] += 1
                else:
                    c["att"] += 1
                    if out == "PASS_COMPLETE":
                        c["comp"] += 1
                        c["comp_yds"] += y
                    elif out == "INTERCEPTION":
                        c["ints"] += 1
                    elif out == "PASS_INCOMPLETE":
                        c["inc"] += 1
            if out == "FUMBLE":
                c["fum_lost"] += 1
            nxt = log[i + 1] if i + 1 < len(log) else None
            if nxt is not None and nxt.get("kind") == "OFF" and nxt["offense"] == e["offense"] and nxt["down"] == 1 \
                    and out not in ("INTERCEPTION", "FUMBLE"):
                c["first_downs"] += 1
    teams = list(ns["AI_FRANCHISES"])
    win = {ab: ns["franchise_style_metrics"](games, ab)["win_pct"] for ab in teams}
    att = max(1, c["att"])
    return {
        "games": n,
        "completion_pct": c["comp"] / att,
        "sack_rate": c["sacks"] / max(1, c["dropbacks"]),
        "int_rate": c["ints"] / att,
        "ypa": c["comp_yds"] / att,
        "net_ypa": c["pass_yds"] / max(1, c["dropbacks"]),
        "ypc": c["run_yds"] / max(1, c["runs"]),
        "turnovers_pg": (c["ints"] + c["fum_lost"]) / n,
        "int_pg": c["ints"] / n,
        "fumbles_lost_pg": c["fum_lost"] / n,
        "points_pg": c["points"] / n,
        "drives_pg": c["drives"] / n,
        "first_downs_pg": c["first_downs"] / n,
        "plays_pg": c["plays"] / n,
        "pass_rate": c["dropbacks"] / max(1, c["plays"]),
        "attempts_pg": c["att"] / n,
        "sacks_pg": c["sacks"] / n,
        "scrambles_pg": c["scr"] / n,
        "safeties_pg": c["safeties"] / n,
        "games_with_safety": c["games_safety"] / n,
        "win_pct": win,
        "seconds_per_game": statistics.mean(temps),
        "seconds_per_game_p95": sorted(temps)[int(0.95 * (len(temps) - 1))],
    }


def comparer(rep, ref):
    """Écarts et verdict par mesure."""
    lignes, ok = [], True
    for k, tol in TOLERANCES.items():
        a, b = ref.get(k), rep.get(k)
        if a is None or b is None:
            continue
        ecart = b - a
        bon = abs(ecart) <= tol + 1e-12
        ok &= bon
        lignes.append((k, a, b, ecart, tol, bon))
    for ab, w in rep["win_pct"].items():
        bon = EQUILIBRE[0] <= w <= EQUILIBRE[1]
        ok &= bon
        lignes.append((f"victoires {ab}", ref["win_pct"].get(ab), w, None, EQUILIBRE, bon))
    return lignes, ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--decisions", choices=("off", "on"), default="off")
    ap.add_argument("--graines", type=int, default=None,
                    help="matchs par affiche et par terrain (défaut : ≈ 1 008 matchs — 84 à 4 équipes, 18 à 8)")
    ap.add_argument("--franchises", choices=("4", "8", "12", "16"), default=None,
                    help="taille de la ligue (GC_FRANCHISES ; défaut : celle du notebook, 8 depuis l'étape 6)")
    ap.add_argument("--notebook", default=NOTEBOOK)
    ap.add_argument("--jusqua", default=JUSQUA, help="dernière cellule chargée (V21 : « 12.2 quater »)")
    ap.add_argument("--bloc-b", choices=("off", "on"), default="on", help="intelligence du QB (bloc B, V23)")
    ap.add_argument("--bloc-c", choices=("off", "on"), default="on", help="intelligence des joueurs (bloc C, V24)")
    ap.add_argument("--bloc-d", choices=("off", "on"), default="on", help="adaptation en match et plan de jeu (bloc D, V25)")
    ap.add_argument("--bloc-e", choices=("off", "on"), default="on", help="progression des joueurs (bloc E, V26)")
    ap.add_argument("--expansion", choices=("off", "on"), default="on", help="extension du playbook V0.1 (12.2 decies)")
    ap.add_argument("--fin-periode", choices=("off", "on"), default="on", help="field goal ou continuer en fin de Q2 / Q4 (12.2 undecies)")
    ap.add_argument("--semaines", type=int, default=0,
                    help="bloc E : semaines de progression jouées (une semaine de la ligue chacune) avant le test d'équilibre")
    ap.add_argument("--graine-trajectoire", type=int, default=990_000, help="bloc E : graines des semaines d'essai")
    ap.add_argument("--force-equipe", type=float, help="bloc E : écart maximal de la force d'une franchise (essai)")
    ap.add_argument("--ecart-equipe", type=float, help="bloc E : écart d'unité maximal d'une franchise (essai ; "
                                                          "défaut : moteur.developpement.ECART_EQUIPE_MAX)")
    ap.add_argument("--reference", help="rapport JSON de référence (V21, décisions coupées)")
    ap.add_argument("--sortie", help="écrit le rapport JSON ici")
    a = ap.parse_args()
    if a.franchises:
        os.environ["GC_FRANCHISES"] = a.franchises

    ns, t_charge = charger(a.notebook, a.jusqua, decisions=a.decisions == "on", bloc_b=a.bloc_b == "on",
                          bloc_c=a.bloc_c == "on", bloc_d=a.bloc_d == "on", bloc_e=a.bloc_e == "on",
                          expansion=a.expansion == "on", fin_periode=a.fin_periode == "on")
    assert ns.get("DECISIONS_ENABLED", False) == (a.decisions == "on")
    trajectoire = None
    if a.semaines:
        assert ns.get("PROGRESSION_ENABLED"), "--semaines demande le bloc E"
        if a.ecart_equipe is not None:
            ns["DEV"].ECART_EQUIPE_MAX = a.ecart_equipe
        if a.force_equipe is not None:
            ns["DEV"].FORCE_EQUIPE_MAX = a.force_equipe
        t0 = time.time()
        trajectoire = ns["progression_trajectoire"](a.semaines, seed_base=a.graine_trajectoire)
        print(f"Bloc E : {a.semaines} semaines de progression ({time.time() - t0:.0f} s) — notes d'unité après :")
        for ab, t in ns["AI_FRANCHISES"].items():
            d = trajectoire[-1]["team_units"][ab]
            print(f"  {ab} " + " · ".join(f"{u} {t.units[u]:.1f} ({d[u]:+.1f})" for u in d)
                  + f" · force {trajectoire[-1]['team_strength'][ab]:+.2f}")
    n_eq = len(ns["AI_FRANCHISES"])
    graines = a.graines or (84 if n_eq == 4 else max(1, round(1008 / (n_eq * (n_eq - 1)))))   # comme 12.3
    games, temps = mesurer(ns, graines)
    rep = _stats(games, temps, ns)
    rep["decisions"] = a.decisions
    rep["bloc_b"] = bool(ns.get("QB_IQ_ENABLED", False))
    rep["bloc_c"] = bool(ns.get("PLAYER_IQ_ENABLED", False))
    rep["bloc_d"] = bool(ns.get("GAMEPLAN_ENABLED", False))
    rep["load_seconds"] = t_charge
    rep["bloc_e"] = bool(ns.get("PROGRESSION_ENABLED", False))
    rep["expansion"] = bool(ns.get("EXPANSION_ENABLED", False))
    rep["fin_periode"] = bool(ns.get("FIN_PERIODE_ENABLED", False))
    if trajectoire:
        rep["progression"] = {"semaines": a.semaines, "graine": a.graine_trajectoire,
                              "ecart_equipe_max": ns["DEV"].ECART_EQUIPE_MAX,
                              "force_equipe_max": ns["DEV"].FORCE_EQUIPE_MAX,
                              "team_strength": trajectoire[-1].get("team_strength"),
                              "league_drift_max": max(r["league_drift_max"] for r in trajectoire),
                              "team_units": trajectoire[-1]["team_units"],
                              "team_guard_weeks": sum(bool(r["team_guard"]) for r in trajectoire),
                              "units": {ab: dict(t.units) for ab, t in ns["AI_FRANCHISES"].items()}}
    if a.decisions == "on":
        rep["decision_stats"] = {k: v for k, v in ns["decision_report"](games).items() if k not in ("par_joueur", "par_couvreur")}
    if "gameplan_report" in ns:
        rep["gameplan"] = ns["gameplan_report"](games)
    print(f"Rapport de calibration — décisions {a.decisions} — {rep['games']} matchs "
          f"({rep['seconds_per_game'] * 1000:.0f} ms / match, p95 {rep['seconds_per_game_p95'] * 1000:.0f} ms)")
    for k in ("completion_pct", "sack_rate", "int_rate", "ypa", "net_ypa", "ypc", "turnovers_pg", "int_pg",
              "fumbles_lost_pg", "points_pg", "drives_pg", "first_downs_pg", "plays_pg", "pass_rate", "attempts_pg",
              "sacks_pg", "scrambles_pg", "safeties_pg", "games_with_safety"):
        print(f"  {k:16s} {rep[k]:8.3f}")
    print("  victoires       ", " · ".join(f"{ab} {w:.1%}" for ab, w in rep["win_pct"].items()))
    if a.decisions == "on":
        s = rep["decision_stats"]
        print(f"  décisions : {s['dropbacks']} dropbacks · 1re lecture {s['taux_premiere_lecture']:.1%} · "
              f"sous pression {s['taux_pression']:.1%} · lancer à {s['temps_lancer_moyen']:.2f} s · "
              f"scrambles {s['scrambles']} · throwaways {s['throwaways']} · sans solution {s['sacks_decision']} · "
              f"forcées {s['forcees']}")
        if rep["bloc_b"]:
            print(f"  bloc B : erreurs de lecture {s['taux_erreur_lecture']:.1%} des lancers · poche {s['temps_poche_moyen']:.2f} s · "
                  f"INT sur décision fautive (forcée / mal lue) {s['part_int_decision']:.0%} · "
                  f"sacks « ballon gardé » {s['part_sacks_decision']:.0%}")
            for qid, q in sorted(s["par_qb"].items()):
                print(f"    {qid:8s} {q['name']:16s} lancer {q['temps_lancer_moyen']:.2f} s · 1re lecture "
                      f"{q['taux_premiere_lecture']:.0%} · erreurs {q['taux_erreur_lecture']:.1%} · pressé "
                      f"{q['presses'] / max(1, q['lancers']):.0%} · sacks {q['taux_sack']:.1%} · INT {q['taux_int']:.1%}")
        if rep["bloc_c"]:
            print("  bloc C : " + " · ".join(f"{k} {v['part']:.1%} des ballons (complétion {v['completion']:.1%}, INT "
                                            f"{v['int'] / max(1, v['cibles']):.1%})" for k, v in sorted(s["par_reception"].items()))
                  + f" · coverage busts sur la cible {s['taux_bust']:.1%} ({s['busts']} au total)")
        if rep.get("gameplan"):
            gpr, n = rep["gameplan"], rep["games"]
            print("  ajustements / match : " + " · ".join(f"{k} {v / n:.2f}" for k, v in sorted(gpr["adjust"].items())))
            if rep["bloc_d"]:
                print(f"  bloc D : passes avec un plan {gpr['plan_passes']} · bracket {gpr['bracket']} (double réel "
                      f"{gpr['bracketed']}, lancer dans le bracket {gpr['bracketed_thrown']}) · protection {gpr['protection']} · "
                      f"cible évitée {gpr['away']} · cible favorite lue en premier {gpr['focus']}")
        for role, d in sorted(s["par_role"].items(), key=lambda x: -x[1]["cibles"]):
            print(f"    {role:4s} {d['cibles'] / max(1, s['lancers']):6.1%} des cibles · complétion "
                  f"{d['completes'] / max(1, d['cibles']):6.1%} · INT {d['int'] / max(1, d['cibles']):5.1%} · "
                  f"{d['yards'] / max(1, d['completes']):5.1f} yds / réception")
    if a.sortie:
        with open(a.sortie, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, ensure_ascii=False, indent=1)
    if a.reference:
        ref = json.load(open(a.reference, encoding="utf-8"))
        lignes, ok = comparer(rep, ref)
        print(f"\nComparaison avec {a.reference} :")
        for k, x, y, e, tol, bon in lignes:
            if e is None:
                print(f"  {'✅' if bon else '❌'} {k:16s} {x if x is None else round(x, 3)} -> {y:.3f}  (plage {tol[0]:.0%}-{tol[1]:.0%})")
            else:
                print(f"  {'✅' if bon else '❌'} {k:16s} {x:8.3f} -> {y:8.3f}  écart {e:+.3f} (tolérance ±{tol})")
        tr = rep["seconds_per_game"] / max(1e-9, ref["seconds_per_game"])
        print(f"  {'✅' if tr <= 2 else '❌'} temps par match ×{tr:.2f} (budget ≤ ×2)")
        ok &= tr <= 2
        print("VERDICT :", "dans les tolérances" if ok else "HORS TOLÉRANCE")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
