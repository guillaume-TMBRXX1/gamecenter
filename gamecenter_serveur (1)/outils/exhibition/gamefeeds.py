#!/usr/bin/env python3
"""GameFeed.json de matchs joués par le moteur courant du notebook (V24 : blocs A-B-C), à charger dans le site
(bouton « Load GameFeed » du lecteur de replay, tuile Exhibition).

Rapide : charge le notebook sans Jupyter jusqu'à 12.2 septies (comme outils/moteur/rapport_calibration.py), sans le
test d'équilibre ni les cotes (≈ 1-2 min). Les feeds n'ont donc pas les cotes du moteur (simulate_exhibition.py les a).

    python3 outils/exhibition/gamefeeds.py --matchs "MNL@VEC,CTX@AEG" --par-affiche 2 --sortie /tmp/feeds
    python3 outils/exhibition/gamefeeds.py --matchs tous --par-affiche 1      # les 12 affiches
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "moteur"))
import rapport_calibration as rc  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--matchs", default="tous", help="« VIS@DOM,… » ou « tous » (12 affiches)")
    ap.add_argument("--par-affiche", type=int, default=1)
    ap.add_argument("--graine", type=int, default=9_500_000, help="hors saison, hors cotes")
    ap.add_argument("--sortie", default="gamefeeds")
    a = ap.parse_args()
    ns, t = rc.charger(decisions=True, bloc_b=True, bloc_c=True)
    print(f"notebook chargé en {t:.0f} s · moteur {ns['moteur'].VERSION} · blocs B {ns['QB_IQ_ENABLED']} C {ns['PLAYER_IQ_ENABLED']}")
    teams = list(ns["AI_FRANCHISES"])
    if a.matchs.strip().lower() == "tous":
        pairs = [(v, h) for h in teams for v in teams if v != h]
    else:
        pairs = [tuple(x.strip().upper().split("@")) for x in a.matchs.split(",") if x.strip()]
    os.makedirs(a.sortie, exist_ok=True)
    for i, (away, home) in enumerate(pairs):
        assert home in teams and away in teams and home != away, (away, home)
        for k in range(a.par_affiche):
            seed = a.graine + 100 * i + k
            g = ns["franchise_game"](home, away, seed=seed)
            gid = f"v24-{away.lower()}-at-{home.lower()}-{seed}"
            feed = ns["export_gamefeed"](g, game_id=gid, featured=False, week="Exhibition")
            err = ns["validate_gamefeed"](feed, g)
            assert not err, err[:3]
            d = [p["decision"] for p in feed["plays"] if p.get("decision")]
            n = lambda f: sum(1 for x in d if f(x))
            path = os.path.join(a.sortie, f"gamefeed_{gid}.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(feed, fh, ensure_ascii=False, separators=(",", ":"))
            print(f"{away} {g['away_score']} @ {home} {g['home_score']} · graine {seed} · {len(feed['plays'])} actions · "
                  f"contested {n(lambda x: x.get('reception') == 'contested')} · busts {n(lambda x: x.get('bust'))} -> {path}")


if __name__ == "__main__":
    main()
