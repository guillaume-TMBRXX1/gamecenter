#!/usr/bin/env python3
"""GameFeed.json de matchs joués par le moteur courant du notebook (V26 : blocs A-B-C-D-E), à charger dans le site
(bouton « Load GameFeed » du lecteur de replay, tuile Exhibition).

Rapide : charge le notebook sans Jupyter jusqu'à 12.2 nonies (comme outils/moteur/rapport_calibration.py), sans le
test d'équilibre ni les cotes (≈ 1-2 min). Les feeds n'ont donc pas les cotes du moteur (simuler_exhibition.py les a).
Comme la semaine suivante (15.1) et simuler_exhibition.py : staffs ajustés (staffs_next_week) et notes des joueurs
(bloc E : players_next_week, amorce depuis les stats sinon) de la dernière semaine de data/weeks.

    python3 outils/exhibition/gamefeeds.py --matchs "MNL@VEC,CTX@AEG" --par-affiche 2 --sortie /tmp/feeds
    python3 outils/exhibition/gamefeeds.py --matchs tous --par-affiche 1      # toutes les affiches (56 à 8 équipes)
    python3 outils/exhibition/gamefeeds.py --base                             # notes de base (sans semaine précédente)
"""
import argparse, ast, glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "moteur"))
import rapport_calibration as rc  # noqa: E402


def _staffs(ns):
    """apply_staff_snapshots (15.1) : seulement les définitions de la cellule (pas la semaine à la demande)."""
    nb = json.load(open(rc.NOTEBOOK, encoding="utf-8"))
    for c in nb["cells"]:
        src = "".join(c["source"])
        if c["cell_type"] == "code" and "def apply_staff_snapshots" in src:
            mod = ast.Module(body=[n for n in ast.parse(src).body if isinstance(n, (ast.FunctionDef, ast.Import))],
                             type_ignores=[])
            exec(compile(mod, "<cellule 15.1>", "exec"), ns)
            return
    raise SystemExit("apply_staff_snapshots introuvable")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--matchs", default="tous", help="« VIS@DOM,… » ou « tous » (toutes les affiches : 56 à 8 équipes)")
    ap.add_argument("--par-affiche", type=int, default=1)
    ap.add_argument("--graine", type=int, default=9_500_000, help="hors saison, hors cotes")
    ap.add_argument("--data", default=os.path.join(ROOT, "data"))
    ap.add_argument("--base", action="store_true", help="staffs et notes de départ (ignore data/weeks)")
    ap.add_argument("--sortie", default="gamefeeds")
    a = ap.parse_args()
    ns, t = rc.charger(decisions=True, bloc_b=True, bloc_c=True, bloc_d=True, bloc_e=True)
    print(f"notebook chargé en {t:.0f} s · blocs B {ns['QB_IQ_ENABLED']} C {ns['PLAYER_IQ_ENABLED']} "
          f"D {ns['GAMEPLAN_ENABLED']} E {ns['PROGRESSION_ENABLED']}")
    weeks = [] if a.base else sorted(glob.glob(os.path.join(a.data, "weeks", "week_*", "week.json")))
    prev = json.load(open(weeks[-1], encoding="utf-8")) if weeks else None
    if prev:
        _staffs(ns)
        ns["apply_staff_snapshots"](prev.get("staffs_next_week") or prev.get("staffs_at_start"))
    src = ns["progression_reprendre"](prev)
    print(f"semaine précédente : {os.path.basename(os.path.dirname(weeks[-1])) if weeks else 'aucune'} · notes : {src}")
    teams = list(ns["AI_FRANCHISES"])
    if a.matchs.strip().lower() == "tous":
        pairs = [(v, h) for h in teams for v in teams if v != h]
    else:
        pairs = [tuple(x.strip().upper().split("@")) for x in a.matchs.split(",") if x.strip()]
    os.makedirs(a.sortie, exist_ok=True)
    season = (prev or {}).get("week", {}).get("index", 0)
    for i, (away, home) in enumerate(pairs):
        assert home in teams and away in teams and home != away, (away, home)
        for k in range(a.par_affiche):
            seed = a.graine + 100 * i + k
            g = ns["franchise_game"](home, away, seed=seed)
            gid = f"v26-{away.lower()}-at-{home.lower()}-{seed}"
            feed = ns["export_gamefeed"](g, game_id=gid, featured=False, season=season, week="Exhibition")
            err = ns["validate_gamefeed"](feed, g)
            assert not err, err[:3]
            pl = feed["plays"]
            d = [p["decision"] for p in pl if p.get("decision")]
            n = lambda f: sum(1 for x in d if f(x))
            adj = [x for p in pl for x in (p.get("adjust") or [])]
            plan = sum(1 for x in adj if x.get("kind") in ("o_quick", "o_protect", "o_away", "d_bracket", "d_rotate", "d_disguise"))
            roster = feed["game"]["home"]["roster"] + feed["game"]["away"]["roster"]
            moved = sum(1 for r in roster if any((r.get("progression") or {}).get("delta", {}).values()))
            path = os.path.join(a.sortie, f"gamefeed_{gid}.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(feed, fh, ensure_ascii=False, separators=(",", ":"))
            print(f"{away} {g['away_score']} @ {home} {g['home_score']} · graine {seed} · {len(pl)} actions · "
                  f"1re lecture dépassée {n(lambda x: x.get('action') == 'LANCER' and (x.get('read') or 1) > 1)} · "
                  f"pressé {n(lambda x: x.get('hurried'))} · contested {n(lambda x: x.get('reception') == 'contested')} · "
                  f"busts {n(lambda x: x.get('bust'))} · ajustements {len(adj)} (plan de jeu {plan}) · "
                  f"joueurs aux notes développées {moved}/{len(roster)} -> {path}")


if __name__ == "__main__":
    main()
