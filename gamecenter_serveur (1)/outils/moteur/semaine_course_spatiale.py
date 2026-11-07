#!/usr/bin/env python3
"""Semaine de test du causal léger, blocs 1 (la course après le contact) et 2 (la course après la réception) : joue une
semaine complète de la ligue (chaque affiche une fois, 276 matchs à 24) avec le moteur du notebook, sans cotes ni écriture
dans data/, et mesure la distribution des yards de course et de passe complétée (cible : celle d'avant le bloc), les
points, l'avantage du terrain et le temps.

    python3 outils/moteur/semaine_course_spatiale.py --spatiale off --json /tmp/ref.json     # référence (moteur d'avant)
    python3 outils/moteur/semaine_course_spatiale.py --json /tmp/b1.json                      # cellule du dépôt
    python3 outils/moteur/semaine_course_spatiale.py --boucle /tmp/b                          # charge, puis une semaine par demande :
    echo '{"json": "/tmp/r.json", "spatiale": "on", "params": {"p_plaquage": 0.6}}' > /tmp/b/demande.json
    python3 outils/moteur/semaine_course_spatiale.py --bloc 2 --json /tmp/b2.json             # bloc 2 (réception)

Le moteur est chargé une fois (cellules jusqu'à 12.2 tricies, ≈ 8 min), puis la cellule du bloc (le fichier
outils/moteur/cellule_course_spatiale.py, ou 12.2 untricies du notebook une fois branchée) est exécutée pour chaque
semaine dans un processus fils. Mêmes graines → mêmes matchs.
"""
import argparse, contextlib, importlib, io, json, multiprocessing, os, statistics, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rapport_calibration as rc     # noqa: E402

BLOCS = {1: ("12.2 tricies", "12.2 untricies", "cellule_course_spatiale.py", "GC_COURSE_SPATIALE", "GC_CS_PARAMS"),
         2: ("12.2 untricies", "12.2 duotricies", "cellule_reception_spatiale.py", "GC_RECEPTION_SPATIALE", "GC_RS_PARAMS"),
         3: ("12.2 duotricies", "12.2 tritricies", "cellule_couverture_spatiale.py", "GC_COUVERTURE_SPATIALE", "GC_CV_PARAMS"),
         4: ("12.2 tritricies", "12.2 quattuortricies", "cellule_poche_spatiale.py", "GC_POCHE_SPATIALE", "GC_PS_PARAMS")}
BLOC = [1]
_NS = {}


def _cellule(chemin=None):
    if chemin:
        return open(chemin, encoding="utf-8").read()
    _, cellule, fichier, _, _ = BLOCS[BLOC[0]]
    nb = json.load(open(rc.NOTEBOOK, encoding="utf-8"))
    src = next(("".join(c["source"]) for c in nb["cells"]
                if c["cell_type"] == "code" and cellule in "".join(c["source"])[:300]), None)
    return src or open(os.path.join(HERE, fichier), encoding="utf-8").read()


def brancher(ns, spatiale="on", params=None, chemin=None):
    _, _, _, interrupteur, reglages = BLOCS[BLOC[0]]
    os.environ[interrupteur] = "1" if spatiale == "on" else "0"
    os.environ[reglages] = json.dumps(params or {})
    importlib.reload(importlib.import_module("moteur.course_spatiale"))
    here = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                exec(compile(_cellule(chemin), "<cellule course spatiale>", "exec"), ns)
        finally:
            os.chdir(here)
    print(out.getvalue().strip(), file=sys.stderr)


def _jouer(tache):
    i, h, a, graine = tache
    ns = _NS["ns"]
    t = time.perf_counter()
    g = ns["franchise_game"](h, a, seed=graine)
    sec = time.perf_counter() - t
    m = {"hs": g["home_score"], "as": g["away_score"], "sec": sec, "runs": [], "niv": [], "manques": 0, "sim": 0,
         "passes": [], "psim": 0, "pmanques": 0, "issues": {}, "statuts": {}}
    for e in g["play_log"]:
        dec = e.get("decision") or {}
        if dec.get("action"):
            o = e.get("outcome")
            m["issues"][o] = m["issues"].get(o, 0) + 1
            if dec.get("status"):
                m["statuts"][dec["status"]] = m["statuts"].get(dec["status"], 0) + 1
        if e.get("outcome") == "PASS_COMPLETE":
            m["passes"].append(e.get("yards_gained") or 0)
            y = (e.get("decision") or {}).get("yac")
            if y:
                m["psim"] += 1
                m["pmanques"] += y.get("manques", 0)
        r = e.get("run")
        if r and e.get("outcome") == "RUN":
            m["runs"].append(e.get("yards_gained") or 0)
            m["niv"].append(r.get("contact"))
            s = r.get("spatial")
            if s:
                m["sim"] += 1
                m["manques"] += s.get("manques", 0)
    return m


def mesurer(M):
    n = len(M)
    runs = [y for m in M for y in m["runs"]]
    par = lambda k: round(sum(y >= k for y in runs) / len(runs), 4)
    niv = {}
    for m in M:
        for y, l in zip(m["runs"], m["niv"]):
            niv.setdefault(l, []).append(y)
    return {"matchs": n, "points_par_match": round(sum(m["hs"] + m["as"] for m in M) / n, 2),
            "domicile": round(sum((m["hs"] > m["as"]) + 0.5 * (m["hs"] == m["as"]) for m in M) / n, 3),
            "secondes_par_match": round(statistics.mean(m["sec"] for m in M), 4),
            "courses": {"n_par_match": round(len(runs) / n, 1), "moyenne": round(statistics.mean(runs), 3),
                        "mediane": statistics.median(runs), "<=0": round(sum(y <= 0 for y in runs) / len(runs), 4),
                        "3+": par(3), "10+": par(10), "20+": par(20), "40+": par(40),
                        "20+_par_match": round(sum(y >= 20 for y in runs) / n, 2), "max": max(runs),
                        "simulees": sum(m["sim"] for m in M),
                        "plaquages_manques_par_course": round(sum(m["manques"] for m in M) / max(1, sum(m["sim"] for m in M)), 2)},
            "passes": _passes(M), "decisions": _decisions(M),
            "par_niveau": {k: {"n": len(v), "moyenne": round(statistics.mean(v), 2), "20+": round(sum(y >= 20 for y in v) / len(v), 4)}
                           for k, v in niv.items() if k}}


def _decisions(M):
    """Passes décidées : issues (complète, incomplète, interception, sack, course du QB) et statut de la cible au lancer."""
    iss, st = {}, {}
    for m in M:
        for k, v in m.get("issues", {}).items():
            iss[k] = iss.get(k, 0) + v
        for k, v in m.get("statuts", {}).items():
            st[k] = st.get(k, 0) + v
    n, ns = max(1, sum(iss.values())), max(1, sum(st.values()))
    lancers = sum(iss.get(k, 0) for k in ("PASS_COMPLETE", "PASS_INCOMPLETE", "INTERCEPTION"))
    yards = sum(sum(m["passes"]) for m in M)
    return {"n_par_match": round(n / len(M), 1), "issues": {k: round(v / n, 4) for k, v in sorted(iss.items())},
            "completion": round(iss.get("PASS_COMPLETE", 0) / max(1, lancers), 4),
            "yards_par_tentative": round(yards / max(1, lancers), 3),
            "statuts": {k: round(v / ns, 4) for k, v in sorted(st.items())}}


def _passes(M):
    p = [y for m in M for y in m.get("passes", [])]
    if not p:
        return {}
    par = lambda k: round(sum(y >= k for y in p) / len(p), 4)
    return {"n_par_match": round(len(p) / len(M), 1), "moyenne": round(statistics.mean(p), 3),
            "mediane": statistics.median(p), "<=0": round(sum(y <= 0 for y in p) / len(p), 4), "5+": par(5),
            "10+": par(10), "20+": par(20), "30+": par(30), "40+": par(40), "max": max(p),
            "simulees": sum(m["psim"] for m in M),
            "plaquages_manques_par_reception": round(sum(m["pmanques"] for m in M) / max(1, sum(m["psim"] for m in M)), 2)}


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
                brancher(ns, d.get("spatiale", "on"), d.get("params"), d.get("cellule"))
                semaine(ns, d.get("graine", 600_000), travailleurs, d.get("json"))
                json.dump({"ok": True}, open(fait, "w"))
            except Exception:                           # noqa: BLE001 — l'erreur va dans fait.json
                import traceback
                json.dump({"ok": False, "erreur": traceback.format_exc()}, open(fait, "w"))
                code = 1
            os._exit(code)
        os.waitpid(pid, 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--spatiale", choices=("on", "off"), default="on")
    ap.add_argument("--params", help="réglages (JSON) qui remplacent ceux de moteur/course_spatiale.PARAMS")
    ap.add_argument("--cellule", help="fichier de la cellule à essayer")
    ap.add_argument("--graine", type=int, default=600_000)
    ap.add_argument("--travailleurs", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--json")
    ap.add_argument("--boucle")
    ap.add_argument("--bloc", type=int, choices=sorted(BLOCS), default=1)
    a = ap.parse_args()
    BLOC[0] = a.bloc
    t0 = time.time()
    ns, _ = rc.charger(jusqua=BLOCS[a.bloc][0], decisions=True)
    _NS["ns"] = ns
    print(f"moteur chargé en {time.time() - t0:.0f} s", file=sys.stderr)
    if a.boucle:
        boucle(ns, a.boucle, a.travailleurs)
        return
    brancher(ns, a.spatiale, json.loads(a.params) if a.params else None, a.cellule)
    semaine(ns, a.graine, a.travailleurs, a.json)


if __name__ == "__main__":
    main()
