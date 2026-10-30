#!/usr/bin/env python3
"""Semaine de test des actions longues (README section 85) : joue une semaine complète de la ligue (chaque affiche
une fois, 276 matchs à 24) avec le moteur du notebook, sans cotes ni écriture dans data/, puis mesure les longues
actions, les retours d'interception et le calibrage (points, domicile, yards moyens par action).

    python3 outils/moteur/semaine_longues.py                           # moteur tel quel (cellule du notebook)
    python3 outils/moteur/semaine_longues.py --longues off             # moteur d'avant le chantier
    python3 outils/moteur/semaine_longues.py --boucle /tmp/b           # charge, puis une semaine par demande :
    echo '{"json": "/tmp/r.json", "longues": "on", "cellule": "/tmp/cellule.py"}' > /tmp/b/demande.json

Le moteur est chargé une fois (cellules jusqu'à 12.2 vicies octies, ≈ 8 min), puis la cellule des actions longues
(12.2 vicies novies, ou le fichier --cellule) est exécutée pour chaque semaine dans un processus fils (module relu).
Mêmes graines → mêmes matchs.
"""
import argparse, contextlib, importlib, io, json, multiprocessing, os, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rapport_calibration as rc     # noqa: E402

JUSQUA = "12.2 vicies octies"
CELLULE = "12.2 vicies novies"
_NS = {}


def _cellule(chemin=None):
    if chemin:
        return open(chemin, encoding="utf-8").read()
    nb = json.load(open(rc.NOTEBOOK, encoding="utf-8"))
    return next("".join(c["source"]) for c in nb["cells"]
                if c["cell_type"] == "code" and CELLULE in "".join(c["source"])[:300])


def brancher(ns, longues="on", chemin=None):
    os.environ["GC_ACTIONS_LONGUES"] = "1" if longues == "on" else "0"
    importlib.reload(importlib.import_module("moteur.actions_longues"))
    here = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                exec(compile(_cellule(chemin), "<cellule actions longues>", "exec"), ns)
        finally:
            os.chdir(here)
    print(out.getvalue().strip(), file=sys.stderr)


def _jouer(tache):
    i, h, a, graine = tache
    ns = _NS["ns"]
    g = ns["franchise_game"](h, a, seed=graine)
    f = ns["export_gamefeed"](g, game_id=f"t{i:03d}")
    m = {"home": h, "away": a, "hs": g["home_score"], "as": g["away_score"], "runs": [], "comp": [], "ints": [],
         "td_long": [], "plays": len(f["plays"])}
    for P in f["plays"]:
        r, y, t = P["result"], P.get("gain") or 0, P["call"]["type"]
        if r == "run" or (r == "touchdown" and t == "run" and not P.get("kick_return")):
            m["runs"].append(y)
        elif r == "complete" or (r == "touchdown" and t == "pass"):
            m["comp"].append(y)
        elif r == "interception":
            m["ints"].append(P.get("int_return") or {})
        if r == "touchdown" and t in ("run", "pass"):
            m["td_long"].append(y)
    return m


def mesurer(M):
    n = len(M)
    runs = [y for m in M for y in m["runs"]]
    comp = [y for m in M for y in m["comp"]]
    ints = [x for m in M for x in m["ints"]]
    tds = [y for m in M for y in m["td_long"]]
    q = lambda v, p: sorted(v)[int(len(v) * p)] if v else None
    return {"matchs": n, "points_par_match": round(sum(m["hs"] + m["as"] for m in M) / n, 2),
            "domicile": round(sum((m["hs"] > m["as"]) + 0.5 * (m["hs"] == m["as"]) for m in M) / n, 3),
            "courses": {"n_par_match": round(len(runs) / n, 1), "moyenne": round(sum(runs) / len(runs), 3),
                        "20+": round(sum(y >= 20 for y in runs) / n, 2), "40+": round(sum(y >= 40 for y in runs) / n, 2),
                        "max": max(runs), "p99": q(runs, .99)},
            "passes": {"n_par_match": round(len(comp) / n, 1), "moyenne": round(sum(comp) / len(comp), 3),
                       "20+": round(sum(y >= 20 for y in comp) / n, 2), "40+": round(sum(y >= 40 for y in comp) / n, 2),
                       "max": max(comp), "p99": q(comp, .99)},
            "interceptions": {"par_match": round(len(ints) / n, 2),
                              "retour_moyen": round(sum(x.get("return", 0) for x in ints) / max(1, len(ints)), 1),
                              "retour_median": q([x.get("return", 0) for x in ints], .5),
                              "20+": sum(x.get("return", 0) >= 20 for x in ints),
                              "pick_six": sum(bool(x.get("td")) for x in ints),
                              "pick_six_pct": round(sum(bool(x.get("td")) for x in ints) / max(1, len(ints)), 3),
                              "touchback": sum(bool(x.get("touchback")) for x in ints)},
            "td_scrimmage_40+": round(sum(y >= 40 for y in tds) / n, 2)}


def semaine(ns, graine, travailleurs, js=None):
    equipes = list(ns["AI_FRANCHISES"])
    affiches = [m for rnd in ns["league_rounds"](equipes) for m in rnd]
    taches = [(i, h, aw, graine + i) for i, (h, aw) in enumerate(affiches)]
    t1 = time.time()
    with multiprocessing.get_context("fork").Pool(max(1, travailleurs)) as pool:
        M = pool.map(_jouer, taches, chunksize=4)
    R = mesurer(M)
    R["secondes"] = round(time.time() - t1)
    print(json.dumps(R, ensure_ascii=False), file=sys.stderr)
    if js:
        json.dump(R, open(js, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return R


def boucle(ns, dossier, travailleurs):
    os.makedirs(dossier, exist_ok=True)
    dem, fait = os.path.join(dossier, "demande.json"), os.path.join(dossier, "fait.json")
    print(f"prêt : {dem}", file=sys.stderr)
    while True:
        if not os.path.exists(dem):
            time.sleep(1)
            continue
        d = json.load(open(dem, encoding="utf-8"))
        os.remove(dem)
        if d.get("fin"):
            return
        pid = os.fork()
        if pid == 0:
            code = 0
            try:
                brancher(ns, d.get("longues", "on"), d.get("cellule"))
                semaine(ns, d.get("graine", 500_000), travailleurs, d.get("json"))
                json.dump({"ok": True}, open(fait, "w"))
            except Exception:                           # noqa: BLE001 — l'erreur va dans fait.json
                import traceback
                json.dump({"ok": False, "erreur": traceback.format_exc()}, open(fait, "w"))
                code = 1
            os._exit(code)
        os.waitpid(pid, 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--longues", choices=("on", "off"), default="on")
    ap.add_argument("--cellule", help="fichier de la cellule à essayer (défaut : celle du notebook)")
    ap.add_argument("--graine", type=int, default=500_000)
    ap.add_argument("--travailleurs", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--json")
    ap.add_argument("--boucle")
    a = ap.parse_args()
    t0 = time.time()
    ns, _ = rc.charger(jusqua=JUSQUA, decisions=True)
    _NS["ns"] = ns
    print(f"moteur chargé en {time.time() - t0:.0f} s", file=sys.stderr)
    if a.boucle:
        boucle(ns, a.boucle, a.travailleurs)
        return
    brancher(ns, a.longues, a.cellule)
    semaine(ns, a.graine, a.travailleurs, a.json)


if __name__ == "__main__":
    main()
