#!/usr/bin/env python3
"""Refonte des playbooks, étape 3 : test d'équilibre de 12.3 avec l'identité de jeu coupée puis allumée.

Joue le test d'équilibre du notebook (chaque franchise reçoit chacune des autres, BALANCE_TEST_SEEDS = 4 à 24 équipes :
2 208 matchs, mêmes graines que 12.3) deux fois — GC_IDENTITE=0 (moteur d'avant) puis 1 — et compare :
  - les mesures de la ligue aux tolérances de la calibration (rapport_calibration.TOLERANCES), l'identité coupée
    servant de référence ;
  - le % de victoires de chaque franchise à l'équilibre 40-60 % (rapport_calibration.EQUILIBRE) ;
  - le temps par match (le calcul du samedi en dépend : cotes comprises, ≈ 15 simulations par affiche).

    python3 outils/moteur/equilibre_identite.py                      # ≈ 8 min de chargement + 2 × (2 208 matchs)
    python3 outils/moteur/equilibre_identite.py --graines 2 --sortie /tmp/eq.json

Le moteur est chargé une fois (jusqu'à 12.2 vicies sexies) ; chaque passage (coupé, allumé) est un processus fils qui
exécute la cellule d'identité puis répartit les matchs entre des travailleurs (fork). Code de sortie 1 si une mesure
sort de sa tolérance ou une franchise de 40-60 %.
"""
import argparse, collections, hashlib, json, multiprocessing, os, statistics, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rapport_calibration as rc     # noqa: E402
import semaine_identite as si        # noqa: E402

_NS = {}


def graine(h, a, s, base=50_000):
    """Même graine que _balance_seed (12.3)."""
    k = int(hashlib.md5(f"equilibre|{h}|{a}".encode()).hexdigest()[:6], 16)
    return base + k * 100 + s


def _compter(tache):
    """Un match : compteurs de rapport_calibration._stats, score et temps."""
    h, a, g = tache
    t = time.perf_counter()
    m = _NS["ns"]["franchise_game"](h, a, seed=g)
    dt = time.perf_counter() - t
    c = collections.Counter()
    c["points"] = m["home_score"] + m["away_score"]
    c["drives"] = len(m.get("drives") or [])
    log = m["play_log"]
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
            if out in ("SACK", "FUMBLE"):
                c["sacks"] += 1
            else:
                c["att"] += 1
                if out == "PASS_COMPLETE":
                    c["comp"] += 1
                    c["comp_yds"] += y
                elif out == "INTERCEPTION":
                    c["ints"] += 1
        if out == "FUMBLE":
            c["fum_lost"] += 1
        nxt = log[i + 1] if i + 1 < len(log) else None
        if nxt is not None and nxt.get("kind") == "OFF" and nxt["offense"] == e["offense"] and nxt["down"] == 1 \
                and out not in ("INTERCEPTION", "FUMBLE"):
            c["first_downs"] += 1
    return h, a, m["home_score"], m["away_score"], dict(c), dt


def mesures(res):
    n = len(res)
    c = collections.Counter()
    v = collections.defaultdict(lambda: [0.0, 0])
    for h, a, hs, as_, cc, _ in res:
        c.update(cc)
        for t, p, q in ((h, hs, as_), (a, as_, hs)):
            v[t][0] += (p > q) + 0.5 * (p == q)
            v[t][1] += 1
    att = max(1, c["att"])
    temps = [r[5] for r in res]
    return {"games": n, "completion_pct": c["comp"] / att, "sack_rate": c["sacks"] / max(1, c["dropbacks"]),
            "int_rate": c["ints"] / att, "ypa": c["comp_yds"] / att, "net_ypa": c["pass_yds"] / max(1, c["dropbacks"]),
            "ypc": c["run_yds"] / max(1, c["runs"]), "turnovers_pg": (c["ints"] + c["fum_lost"]) / n,
            "points_pg": c["points"] / n, "drives_pg": c["drives"] / n, "first_downs_pg": c["first_downs"] / n,
            "plays_pg": c["plays"] / n, "pass_rate": c["dropbacks"] / max(1, c["plays"]),
            "win_pct": {t: w / k for t, (w, k) in sorted(v.items())},
            "seconds_per_game": statistics.mean(temps), "seconds_per_game_p95": sorted(temps)[int(0.95 * (n - 1))]}


def passage(ns, identite, graines, travailleurs, sortie):
    """Processus fils : identité coupée / allumée, test d'équilibre, mesures écrites dans sortie (JSON)."""
    pid = os.fork()
    if pid:
        os.waitpid(pid, 0)
        return json.load(open(sortie, encoding="utf-8"))
    code = 0
    try:
        os.environ["GC_IDENTITE"] = "1" if identite else "0"
        si._brancher_identite(ns)
        _NS["ns"] = ns
        eq = list(ns["AI_FRANCHISES"])
        taches = [(h, a, graine(h, a, s)) for h in eq for a in eq if h != a for s in range(graines)]
        t0 = time.time()
        with multiprocessing.get_context("fork").Pool(travailleurs) as pool:
            res = pool.map(_compter, taches, chunksize=8)
        m = mesures(res)
        m["mur_s"] = time.time() - t0
        json.dump(m, open(sortie, "w", encoding="utf-8"), indent=1)
    except Exception:                                    # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--graines", type=int, default=4, help="matchs par affiche (12.3 : 4 à 24 équipes)")
    ap.add_argument("--travailleurs", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--sortie", help="rapport JSON (coupé, allumé, verdicts)")
    a = ap.parse_args()
    t0 = time.time()
    ns, _ = rc.charger(jusqua=si.JUSQUA, decisions=True)
    print(f"moteur chargé en {time.time() - t0:.0f} s", file=sys.stderr)
    import tempfile
    tmp = tempfile.mkdtemp(prefix="gc-eqid-")
    off = passage(ns, False, a.graines, a.travailleurs, os.path.join(tmp, "off.json"))
    on = passage(ns, True, a.graines, a.travailleurs, os.path.join(tmp, "on.json"))
    lignes, ok = rc.comparer(on, off)
    print(f"\n{on['games']} matchs par passage · {on['seconds_per_game'] * 1000:.0f} ms par match allumé "
          f"(coupé {off['seconds_per_game'] * 1000:.0f} ms ; p95 {on['seconds_per_game_p95'] * 1000:.0f} ms)")
    for k, ref, val, ecart, tol, bon in lignes:
        if ecart is None:
            print(f"  {'✓' if bon else '✗'} {k:24s} {ref:.3f} -> {val:.3f}   ({tol[0]:.0%}-{tol[1]:.0%})")
        else:
            print(f"  {'✓' if bon else '✗'} {k:24s} {ref:8.3f} -> {val:8.3f}   écart {ecart:+.3f} (± {tol})")
    print("VERDICT :", "dans les tolérances" if ok else "HORS TOLÉRANCE")
    if a.sortie:
        json.dump({"coupe": off, "allume": on, "ok": ok}, open(a.sortie, "w", encoding="utf-8"), indent=1)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
