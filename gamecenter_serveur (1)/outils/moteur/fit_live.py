#!/usr/bin/env python3
"""Réajuste le modèle des cotes en direct (13.1 : paramètres LIVE_*) sur le moteur courant, puis le vérifie comme 13.4.

Quand un changement du moteur modifie le déroulé des matchs (adaptation, horloge, bloc F, punts, mémoire…), 13.4 peut
trouver les cotes en direct mal calibrées (extrêmes, écart moyen, rendement des outsiders). Les étapes précédentes
réajustaient alors les mêmes paramètres par maximum de vraisemblance ; cet outil le refait de façon reproductible :

  1. charge le notebook sans Jupyter jusqu'à 13.4 (contrôles lourds sautés : GC_LEGER=1) ;
  2. joue N matchs de franchises sur les graines 3 100 000 + (jamais utilisées par 13.4), cotes d'avant-match du moteur
     (SEASON_ODDS_SIMS simulations par affiche, comme la saison), et relève chaque action : écart, temps restant,
     possession, position, loi d'avant-match, issue (nuls exclus) ;
  3. ajuste LIVE_VAR_EXTRA, LIVE_VAR_FLOOR, LIVE_EP0, LIVE_EP1, LIVE_REVERT, LIVE_REVERT_POW, LIVE_HOME (Nelder-Mead sur
     la log-vraisemblance de l'issue, départ = paramètres actuels) ;
  4. rejoue la vérification de 13.4 (graines 4 000 000 +) avec les anciens puis les nouveaux paramètres.

    python3 outils/moteur/fit_live.py [--matchs 1500] [--procs 4] [--sortie fit.json]

Aucun fichier du dépôt n'est modifié : les valeurs sont à reporter dans 13.1 (bloc des paramètres LIVE_*).
Durée : ≈ 8 min de chargement, ≈ 30 min de cotes d'avant-match (552 affiches), quelques minutes de matchs et d'ajustement.
"""
import argparse, json, math, multiprocessing as mp, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rapport_calibration as rc  # noqa: E402

PARAMS = ("LIVE_VAR_EXTRA", "LIVE_VAR_FLOOR", "LIVE_EP0", "LIVE_EP1", "LIVE_REVERT", "LIVE_REVERT_POW", "LIVE_HOME")
NS = {}


def _lignes(args):
    """Actions d'un match : (issue, écart, f, signe de la possession, position, moyenne, écart-type d'avant-match)."""
    h, a, seed, sims = args
    F = NS["AI_FRANCHISES"]
    odds = NS["engine_pregame_odds"](F[h], F[a], n_sims=sims)
    m = NS["franchise_game"](h, a, seed=seed)
    if m["home_score"] == m["away_score"]:
        return []
    y = 1 if m["home_score"] > m["away_score"] else 0
    NS["attach_engine_odds"](m, odds)
    f = NS["export_gamefeed"](m, game_id=f"fit{seed}")
    qs = m["quarter_seconds"]
    out = []
    for pl in f["plays"]:
        A = pl["after"]
        if A["status"] == "final":
            continue
        left = pl["clock_end"] if pl["quarter"] > 4 else (4 - pl["quarter"]) * qs + pl["clock_end"]
        sc, pos, x = A["score"], A["offense"], A["los_x"]
        yl = (x - 10) if pos == "home" else (110 - x)
        out.append((y, sc["home"] - sc["away"], max(0.0, min(1.0, left / (4 * qs))),
                    1 if pos == "home" else -1 if pos == "away" else 0, max(0.0, min(100.0, yl)),
                    odds["dist"]["margin_mean"], odds["dist"]["margin_sd"]))
    return out


def _phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def prob(p, r):
    """engine_live_odds (13.1, modèle V21) sur une ligne, paramètres p (ordre de PARAMS)."""
    ve, vf, e0, e1, rv, rp, hm = p
    _, d, f, s, yl, mm, msd = r
    mu = d + (mm + hm) * f
    if f > 0:
        if s:
            mu += s * (e0 + e1 * yl)
        if rv:
            mu -= rv * d * f ** rp
    v = msd * msd * f * (1 + ve * (1 - f)) + vf
    sd = max(0.5, math.sqrt(v) if v > 0 else 0.0)
    return min(max(_phi(mu / sd), 0.005), 0.995)


def nll(p, rows):
    return -sum(math.log(q) if r[0] else math.log(1 - q) for r in rows for q in (prob(p, r),)) / len(rows)


def nelder_mead(f, x0, pas, iters=900, tol=1e-7):
    n = len(x0)
    pts = [list(x0)] + [[x0[j] + (pas[j] if j == i else 0.0) for j in range(n)] for i in range(n)]
    val = [f(x) for x in pts]
    for _ in range(iters):
        o = sorted(range(n + 1), key=lambda i: val[i])
        pts, val = [pts[i] for i in o], [val[i] for i in o]
        if abs(val[-1] - val[0]) < tol:
            break
        c = [sum(pts[i][j] for i in range(n)) / n for j in range(n)]
        xr = [c[j] + (c[j] - pts[-1][j]) for j in range(n)]
        fr = f(xr)
        if fr < val[0]:
            xe = [c[j] + 2 * (c[j] - pts[-1][j]) for j in range(n)]
            fe = f(xe)
            pts[-1], val[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < val[-2]:
            pts[-1], val[-1] = xr, fr
        else:
            xc = [c[j] + 0.5 * (pts[-1][j] - c[j]) for j in range(n)]
            fc = f(xc)
            if fc < val[-1]:
                pts[-1], val[-1] = xc, fc
            else:
                for i in range(1, n + 1):
                    pts[i] = [pts[0][j] + 0.5 * (pts[i][j] - pts[0][j]) for j in range(n)]
                    val[i] = f(pts[i])
    i = min(range(n + 1), key=lambda k: val[k])
    return pts[i], val[i]


def verifier(ns, params, label):
    """La vérification de 13.4 (graines 4 000 000 +, 1 008 matchs) avec ces paramètres."""
    for k, v in zip(PARAMS, params):
        ns[k] = v
    rows = ns["_live_cal_rows"]()
    r = ns["_live_cal_report"](rows, 3, label)
    tails = [b for b in r["bins"] if b[1] <= 0.1 or b[0] >= 0.9]
    gap = max(abs(b[5] - b[4]) for b in tails)
    ok = gap < 0.03 and r["ece"] < 0.03 and r["roi_ci"][0] < 0
    print(f"   {label} : extrêmes ± {gap:.3f} · écart moyen {r['ece']:.3f} · outsiders {r['roi']:+.1%} "
          f"(90 % : {r['roi_ci'][0]:+.1%} à {r['roi_ci'][1]:+.1%}) -> {'✅' if ok else '❌'}")
    return {"gap": gap, "ece": r["ece"], "roi": r["roi"], "roi_ci": r["roi_ci"], "ll": r["ll"], "ok": ok}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--matchs", type=int, default=1500)
    ap.add_argument("--graine", type=int, default=3_100_000)
    ap.add_argument("--procs", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--sortie")
    a = ap.parse_args()
    os.environ["GC_LEGER"] = "1"                    # contrôles lourds sautés (12.3, 13.2, 13.4) : on les rejoue ici
    ns, t = rc.charger(jusqua="— 13.4 —", decisions=True)
    NS.update(ns)
    print(f"notebook chargé jusqu'à 13.4 en {t:.0f} s · mémoire {ns.get('MEMOIRE_ENABLED')} "
          f"(film {ns.get('_MEM', {}).get('source')})")
    T = list(ns["AI_FRANCHISES"])
    pairs = [(h, x) for h in T for x in T if h != x]
    sims = ns["SEASON_ODDS_SIMS"]
    ns["ODDS_CALIBRATION_SIMS"] = sims
    t0 = time.time()
    ns["engine_pregame_odds_many"](pairs, n_sims=sims)
    print(f"cotes d'avant-match : {len(pairs)} affiches × {sims} simulations en {time.time() - t0:.0f} s")
    t0 = time.time()
    todo = [(*pairs[k % len(pairs)], a.graine + k, sims) for k in range(a.matchs)]
    with mp.get_context("fork").Pool(a.procs) as pool:
        rows = [r for part in pool.map(_lignes, todo, chunksize=4) for r in part]
    print(f"{len(rows)} actions de {len({(x[0], x[1]) for x in todo})} matchs en {time.time() - t0:.0f} s")
    x0 = [float(ns[k]) for k in PARAMS]
    n0 = nll(x0, rows)
    t0 = time.time()
    x, n1 = nelder_mead(lambda p: nll(p, rows), x0, [0.3, 0.5, 0.2, 0.01, 0.1, 0.3, 0.3])
    print(f"log-vraisemblance (par action) : {n0:.5f} -> {n1:.5f} en {time.time() - t0:.0f} s")
    print("nouveaux paramètres : " + " · ".join(f"{k} {v:.3f}" for k, v in zip(PARAMS, x)))
    avant = verifier(ns, x0, "actuels  ")
    apres = verifier(ns, x, "réajustés")
    if a.sortie:
        json.dump({"params": dict(zip(PARAMS, [round(v, 4) for v in x])), "avant": dict(zip(PARAMS, x0)),
                   "nll": [n0, n1], "matchs": a.matchs, "graine": a.graine, "verif_avant": avant, "verif_apres": apres},
                  open(a.sortie, "w"), indent=1, default=str)
    sys.exit(0 if apres["ok"] else 1)


if __name__ == "__main__":
    main()
