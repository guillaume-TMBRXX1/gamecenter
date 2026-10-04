#!/usr/bin/env python3
"""Calcule les facteurs de normalisation du bloc A (moteur/resolution.py, CALIBRATION).

Les décisions changent la RÉPARTITION des résultats (libre -> plus de complétions, sans solution -> sack…) ;
ces facteurs ramènent les taux moyens de la ligue sur la référence V21 (garde-fou 3) : sacks / dropback,
INT / tentative, complétion, yards par réception. Itération à point fixe sur le test d'équilibre (mêmes graines
que 12.3), le notebook chargé une seule fois.

    python3 outils/moteur/calibrer_bloc_a.py --reference /tmp/v21.json [--graines 30] [--tours 6]
    python3 outils/moteur/calibrer_bloc_a.py --reference /tmp/v21.json --bloc B         # CALIBRATION_B (V23)

Affiche la ligne CALIBRATION (ou CALIBRATION_B) à recopier dans moteur/resolution.py (puis relancer
rapport_calibration.py).
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rapport_calibration as rc  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reference", required=True, help="rapport JSON V21 (rapport_calibration.py --decisions off)")
    ap.add_argument("--graines", type=int, default=30)
    ap.add_argument("--tours", type=int, default=6)
    ap.add_argument("--bloc", choices=("A", "B"), default="A")
    a = ap.parse_args()
    ref = json.load(open(a.reference, encoding="utf-8"))
    ns, _ = rc.charger(decisions=True, bloc_b=a.bloc == "B")
    k = ns["DECISION_CALIBRATION_B" if a.bloc == "B" else "DECISION_CALIBRATION"]   # dict du moteur (modifié en place)
    k.update({"int": 1.0, "sack": 1.0, "inc": 1.0, "yards": 0.0})
    for t in range(a.tours):
        games, temps = rc.mesurer(ns, a.graines)
        m = rc._stats(games, temps, ns)
        ypr_ref = ref["ypa"] / ref["completion_pct"]
        ypr = m["ypa"] / m["completion_pct"]
        print(f"tour {t}: K={ {x: round(v, 3) for x, v in k.items()} } · comp {m['completion_pct']:.3f} "
              f"sack {m['sack_rate']:.3f} int {m['int_rate']:.4f} yds/réc {ypr:.2f} · pts {m['points_pg']:.1f} "
              f"· victoires {', '.join(f'{x} {w:.0%}' for x, w in m['win_pct'].items())}")
        k["sack"] *= ref["sack_rate"] / m["sack_rate"]
        k["int"] *= ref["int_rate"] / m["int_rate"]
        k["inc"] *= (1 - ref["completion_pct"]) / (1 - m["completion_pct"])
        k["yards"] += ypr_ref - ypr
    print(f"\nCALIBRATION{'_B' if a.bloc == 'B' else ''} = " + json.dumps({x: round(v, 3) for x, v in k.items()}))


if __name__ == "__main__":
    main()
