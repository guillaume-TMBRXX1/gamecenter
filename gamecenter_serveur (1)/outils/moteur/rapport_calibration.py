#!/usr/bin/env python3
"""Rapport de calibration automatique du programme ENGINE INTELLIGENCE (garde-fou 3).

Charge le moteur du notebook (cellules de code jusqu'à 12.2 quinquies incluse, sans Jupyter), joue le test
d'équilibre de 12.3 (chaque franchise reçoit chacune des 3 autres, 84 graines -> 1 008 matchs, mêmes graines
que le notebook) et mesure : passes (complétion, sacks, INT, YPA, yards / tentative nette), courses, pertes de
balle, points, drives, premiers downs, actions, équilibre par équipe, temps par match. Avec les décisions
allumées, ajoute les stats des décisions (cible réelle, première lecture, pression, scramble, throwaway).

    python3 outils/moteur/rapport_calibration.py --decisions off --sortie /tmp/v21.json        # référence
    python3 outils/moteur/rapport_calibration.py --decisions on  --reference /tmp/v21.json     # comparaison
    python3 outils/moteur/rapport_calibration.py --decisions on --graines 20                   # rapide (240 matchs)

Code de sortie 1 si une mesure sort de sa tolérance (TOLERANCES, à valider par Guillaume).
"""
import argparse, contextlib, io, json, linecache, os, statistics, sys, tempfile, time, types
import __future__

HERE = os.path.dirname(os.path.abspath(__file__))
SERVEUR = os.path.abspath(os.path.join(HERE, "..", ".."))
NOTEBOOK = os.path.join(SERVEUR, "NFL_Sim_GameCenter.ipynb")
JUSQUA = "12.2 quinquies"

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


def charger(notebook=NOTEBOOK, jusqua=JUSQUA, decisions=False):
    """Exécute les cellules de code du notebook jusqu'à celle dont l'en-tête contient `jusqua` (incluse)."""
    os.environ["GC_DECISIONS"] = "1" if decisions else "0"
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


def mesurer(ns, graines=84, base=50_000):
    """Le test d'équilibre de 12.3 (mêmes graines), mesuré action par action."""
    teams = list(ns["AI_FRANCHISES"])
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
             fum_lost=0, plays=0, first_downs=0, drives=0, points=0, dropbacks=0)
    for g in games:
        c["points"] += g["home_score"] + g["away_score"]
        c["drives"] += len(g.get("drives") or [])
        log = [e for e in g["play_log"]]
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
    ap.add_argument("--graines", type=int, default=84, help="matchs par affiche et par terrain (84 -> 1 008 matchs)")
    ap.add_argument("--notebook", default=NOTEBOOK)
    ap.add_argument("--jusqua", default=JUSQUA, help="dernière cellule chargée (V21 : « 12.2 quater »)")
    ap.add_argument("--reference", help="rapport JSON de référence (V21, décisions coupées)")
    ap.add_argument("--sortie", help="écrit le rapport JSON ici")
    a = ap.parse_args()

    ns, t_charge = charger(a.notebook, a.jusqua, decisions=a.decisions == "on")
    assert ns.get("DECISIONS_ENABLED", False) == (a.decisions == "on")
    games, temps = mesurer(ns, a.graines)
    rep = _stats(games, temps, ns)
    rep["decisions"] = a.decisions
    rep["load_seconds"] = t_charge
    if a.decisions == "on":
        rep["decision_stats"] = {k: v for k, v in ns["decision_report"](games).items() if k != "par_joueur"}
    print(f"Rapport de calibration — décisions {a.decisions} — {rep['games']} matchs "
          f"({rep['seconds_per_game'] * 1000:.0f} ms / match, p95 {rep['seconds_per_game_p95'] * 1000:.0f} ms)")
    for k in ("completion_pct", "sack_rate", "int_rate", "ypa", "net_ypa", "ypc", "turnovers_pg", "int_pg",
              "fumbles_lost_pg", "points_pg", "drives_pg", "first_downs_pg", "plays_pg", "pass_rate", "attempts_pg",
              "sacks_pg", "scrambles_pg"):
        print(f"  {k:16s} {rep[k]:8.3f}")
    print("  victoires       ", " · ".join(f"{ab} {w:.1%}" for ab, w in rep["win_pct"].items()))
    if a.decisions == "on":
        s = rep["decision_stats"]
        print(f"  décisions : {s['dropbacks']} dropbacks · 1re lecture {s['taux_premiere_lecture']:.1%} · "
              f"sous pression {s['taux_pression']:.1%} · lancer à {s['temps_lancer_moyen']:.2f} s · "
              f"scrambles {s['scrambles']} · throwaways {s['throwaways']} · sans solution {s['sacks_decision']} · "
              f"forcées {s['forcees']}")
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
