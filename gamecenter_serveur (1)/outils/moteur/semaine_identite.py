#!/usr/bin/env python3
"""Semaine de test pour la refonte des playbooks (étape 2) : joue une semaine complète de la ligue (chaque affiche
une fois, 276 matchs à 24) avec le moteur du notebook, sans cotes ni écriture dans data/, puis mesure l'identité de
jeu des franchises avec identite_playbooks.py (même rapport que pour une vraie semaine).

    python3 outils/moteur/semaine_identite.py                          # moteur tel quel (GC_IDENTITE du notebook)
    python3 outils/moteur/semaine_identite.py --identite off           # moteur d'avant la refonte
    python3 outils/moteur/semaine_identite.py --md /tmp/r.md --json /tmp/r.json --graine 500000 --travailleurs 4

Le moteur est chargé une fois (cellules de code jusqu'à 12.2 vicies sexies, comme rapport_calibration.py, ≈ 8 min,
puis la cellule d'identité 12.2 vicies septies),
puis les matchs sont répartis entre des processus fils (fork : le moteur chargé est partagé, ≈ 30 s pour 276 matchs).
Mêmes graines → mêmes matchs.

Réglage des tables de moteur/identite_franchises.py sans recharger le notebook :

    python3 outils/moteur/semaine_identite.py --boucle /tmp/boucle      # charge, puis attend des demandes
    echo '{"md": "/tmp/r.md", "json": "/tmp/r.json"}' > /tmp/boucle/demande.json     # une semaine, module relu
"""
import argparse, json, multiprocessing, os, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import identite_playbooks as ip      # noqa: E402
import rapport_calibration as rc     # noqa: E402

JUSQUA = "12.2 vicies sexies"        # le moteur jusqu'à la cellule d'avant l'identité…
CELLULE_IDENTITE = "12.2 vicies septies"   # … puis la cellule d'identité, relue dans le notebook à chaque semaine
_NS = {}


def _jouer(tache):
    i, h, a, graine, dossier = tache
    ns = _NS["ns"]
    g = ns["franchise_game"](h, a, seed=graine)
    feed = ns["export_gamefeed"](g, game_id=f"t{i:03d}")
    nom = f"t{i:03d}.json"
    with open(os.path.join(dossier, "games", nom), "w", encoding="utf-8") as f:
        json.dump({"game": feed.get("game"), "plays": feed.get("plays")}, f)
    return {"id": f"t{i:03d}", "feed": f"games/{nom}", "home": h, "away": a,
            "score": (g["home_score"], g["away_score"])}


def _brancher_identite(ns):
    """Relit moteur/identite_franchises.py et exécute la cellule d'identité (12.2 vicies septies) telle qu'elle est
    dans le notebook : le moteur chargé une fois sert à chaque réglage (module ou cellule)."""
    import contextlib, importlib, io
    importlib.reload(importlib.import_module("moteur.identite_franchises"))
    nb = json.load(open(rc.NOTEBOOK, encoding="utf-8"))
    src = next("".join(c["source"]) for c in nb["cells"]
               if c["cell_type"] == "code" and CELLULE_IDENTITE in "".join(c["source"])[:400])
    here = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                exec(compile(src, "<cellule identité>", "exec"), ns)
        finally:
            os.chdir(here)
    print(out.getvalue().strip(), file=sys.stderr)


def semaine(ns, graine, travailleurs, md=None, js=None, garder=None, titre="semaine de test"):
    """Joue la semaine de test et écrit le rapport ; renvoie (R, L)."""
    equipes = list(ns["AI_FRANCHISES"])
    affiches = [m for rnd in ns["league_rounds"](equipes) for m in rnd]
    racine = garder or tempfile.mkdtemp(prefix="gc-semid-")
    dossier = os.path.join(racine, "week_test")
    os.makedirs(os.path.join(dossier, "games"), exist_ok=True)
    taches = [(i, h, aw, graine + i, dossier) for i, (h, aw) in enumerate(affiches)]
    t1 = time.time()
    with multiprocessing.get_context("fork").Pool(max(1, travailleurs)) as pool:
        sched = pool.map(_jouer, taches, chunksize=4)
    print(f"{len(sched)} matchs joués en {time.time() - t1:.0f} s", file=sys.stderr)
    with open(os.path.join(dossier, "week.json"), "w", encoding="utf-8") as f:
        json.dump({"schedule": [{"id": s["id"], "feed": s["feed"]} for s in sched]}, f)
    E = ip.mesurer([dossier])
    R, L = ip.analyser(E)
    texte = ip.markdown(R, L, titre)
    if md:
        open(md, "w", encoding="utf-8").write(texte)
    else:
        print(texte.split("\n## ")[0])
    if js:
        victoires = {t: [0, 0] for t in equipes}
        for s in sched:
            hs, as_ = s["score"]
            for t, pour, contre in ((s["home"], hs, as_), (s["away"], as_, hs)):
                victoires[t][0] += (pour > contre) + 0.5 * (pour == contre)
                victoires[t][1] += 1
        json.dump({"ligue": L, "franchises": R, "victoires": {t: v / n for t, (v, n) in victoires.items()},
                   "points_par_match": sum(sum(s["score"]) for s in sched) / len(sched)},
                  open(js, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=list)
    if not garder:
        import shutil
        shutil.rmtree(racine, ignore_errors=True)
    return R, L


def boucle(ns, dossier, travailleurs):
    """Attend dossier/demande.json ({md, json, graine, garder}) ; chaque demande est jouée dans un processus fils (moteur
    chargé intact) après relecture du module et de la cellule d'identité ; dossier/fait.json signale la fin (ou l'erreur)."""
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
                _brancher_identite(ns)
                semaine(ns, d.get("graine", 500_000), travailleurs, d.get("md"), d.get("json"), d.get("garder"))
                json.dump({"ok": True}, open(fait, "w"))
            except Exception as e:                      # noqa: BLE001 — l'erreur va dans fait.json
                import traceback
                json.dump({"ok": False, "erreur": traceback.format_exc()}, open(fait, "w"))
                code = 1
            os._exit(code)
        os.waitpid(pid, 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--identite", choices=("on", "off"), default=None, help="interrupteur GC_IDENTITE (défaut : celui du notebook)")
    ap.add_argument("--graine", type=int, default=500_000, help="graine du premier match (les suivants : +1)")
    ap.add_argument("--travailleurs", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--md", help="rapport Markdown")
    ap.add_argument("--json", help="mesures en JSON (+ scores des matchs)")
    ap.add_argument("--garder", help="dossier où garder les GameFeed de la semaine de test")
    ap.add_argument("--boucle", help="dossier de demandes : charge le moteur une fois, puis joue une semaine par demande")
    a = ap.parse_args()
    if a.identite:
        os.environ["GC_IDENTITE"] = "1" if a.identite == "on" else "0"
    t0 = time.time()
    ns, _ = rc.charger(jusqua=JUSQUA, decisions=True)
    _NS["ns"] = ns
    print(f"moteur chargé en {time.time() - t0:.0f} s", file=sys.stderr)
    if a.boucle:
        boucle(ns, a.boucle, a.travailleurs)
        return
    _brancher_identite(ns)
    semaine(ns, a.graine, a.travailleurs, a.md, a.json, a.garder,
            "semaine de test" + (f" (identité {a.identite})" if a.identite else ""))


if __name__ == "__main__":
    main()
