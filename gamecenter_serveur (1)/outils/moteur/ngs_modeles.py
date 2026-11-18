"""Modèles « attendus » des statistiques de suivi (moteur/ngs.py, programme/Next_Gen_Stats_plan.md, NGS-2).

Apprend xComp (complétion attendue), xYAC (yards après la réception attendus) et xRush (yards attendus d'une course,
d'après ce qui est connu avant le snap) sur des semaines PASSÉES, et les écrit dans moteur/ngs_modeles.json (versé au
dépôt). Le serveur les applique à la semaine en cours ; l'écart moyen de la ligue est retiré à l'affichage.

    python outils/moteur/ngs_modeles.py --semaines data/weeks/week_2026-11-09            (écrit moteur/ngs_modeles.json)
    python outils/moteur/ngs_modeles.py --controle data/weeks/week_2026-11-16            (rapport, n'écrit rien)

Le contrôle donne, sur une semaine : l'écart de la ligue aux modèles (CPOE, RYOE, YAC), la stabilité de chaque
statistique d'une moitié des matchs à l'autre (corrélation entre les matchs pairs et impairs, joueurs qualifiés dans les
deux), le nombre de joueurs qualifiés et les trois premiers de chaque classement. Depuis « gamecenter_serveur (1) ».
"""
import argparse
import glob
import json
import os
import statistics
import sys
import time

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(os.path.dirname(ICI))
sys.path.insert(0, RACINE)
from moteur import ngs  # noqa: E402

SORTIE = os.path.join(RACINE, "moteur", "ngs_modeles.json")


def feeds(dossier):
    for f in sorted(glob.glob(os.path.join(dossier, "games", "*.json"))):
        with open(f, encoding="utf-8") as fh:
            yield json.load(fh)


def _corr(x, y):
    mx, my = statistics.mean(x), statistics.mean(y)
    sx = sum((i - mx) ** 2 for i in x) ** 0.5
    sy = sum((j - my) ** 2 for j in y) ** 0.5
    return sum((i - mx) * (j - my) for i, j in zip(x, y)) / (sx * sy) if sx and sy else None


def controle(dossier, modeles):
    t = time.time()
    C = [ngs.compter(F, modeles) for F in feeds(dossier)]
    print(f"{len(C)} matchs comptés en {time.time() - t:.1f} s")
    A = ngs.agreger(C)
    L = ngs._ligue(A)
    print(f"Écart de la ligue aux modèles : CPOE {L['off_c']:+.2f} pt · RYOE {L['off_r']:+.3f} yd/course · "
          f"YAC {L['off_y']:+.3f} yd/réception (retirés à l'affichage)")
    T = ngs.tableaux(A, modeles)
    a, b = ngs.tableaux(ngs.agreger(C[0::2]), modeles), ngs.tableaux(ngs.agreger(C[1::2]), modeles)
    for g, ga, gb in zip(T["groups"], a["groups"], b["groups"]):
        A1 = {r["id"]: r["v"] for r in ga["rows"]}
        B1 = {r["id"]: r["v"] for r in gb["rows"]}
        ids = [i for i in A1 if i in B1]
        st = []
        for c in g["cols"]:
            xs = [(A1[i][c["k"]], B1[i][c["k"]]) for i in ids
                  if A1[i][c["k"]] is not None and B1[i][c["k"]] is not None]
            r = _corr(*zip(*xs)) if len(xs) > 5 else None
            st.append(f"{c['k']} {r:.2f}" if r is not None else f"{c['k']} —")
        print(f"\n{g['label']} : {len(g['rows'])} qualifiés · stabilité (moitiés) : {' · '.join(st)}")
        for r in g["rows"][:3]:
            print(f"   {r['name']} ({r['team']}, {r['pos']}) {g['sort']} = {r['v'].get(g['sort'])}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--semaines", nargs="*", default=[], help="dossiers des semaines d'apprentissage (passées)")
    ap.add_argument("--controle", help="dossier d'une semaine à contrôler (rien n'est écrit)")
    ap.add_argument("--sortie", default=SORTIE)
    a = ap.parse_args()
    if a.semaines:
        t = time.time()
        noms = [os.path.basename(os.path.normpath(d)).replace("week_", "") for d in a.semaines]
        M = ngs.entrainer((F for d in a.semaines for F in feeds(d)), noms)
        with open(a.sortie, "w", encoding="utf-8") as fh:
            json.dump(M, fh, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            fh.write("\n")
        print(f"{a.sortie} écrit en {time.time() - t:.1f} s : " +
              " · ".join(f"{k} {len(M[k])} cases" for k in ("comp", "yac", "rush")))
    if a.controle:
        with open(a.sortie, encoding="utf-8") as fh:
            controle(a.controle, json.load(fh))
    if not a.semaines and not a.controle:
        ap.print_help()


if __name__ == "__main__":
    main()
