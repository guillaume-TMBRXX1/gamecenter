#!/usr/bin/env python3
"""GameCenter — match d'exhibition joué par le moteur du notebook (hors calendrier, « en annexe »).

Exécute NFL_Sim_GameCenter.ipynb sans l'ouvrir (comme le calcul du samedi, mais SANS produire de semaine), puis
une cellule ajoutée à la volée qui :
  1. reprend les staffs ajustés de la dernière semaine (staffs_next_week), comme le ferait la semaine suivante ;
  2. joue N matchs candidats entre deux franchises avec le moteur courant (V22.1 : lectures du QB, coordinateurs adaptatifs en
     direct, playbooks V19 + « Roman 2014 » V20) — graines hors saison et hors cotes ;
  3. garde le plus représentatif : beaucoup d'ajustements en direct, score serré, beaucoup de concepts différents ;
  4. calcule les cotes d'avant-match du moteur (300 matchs), les attache, exporte le GameFeed.
Écrit data/exhibitions/<id>.json et data/exhibitions/index.json ; le site les montre dans « Exhibition ».

    python3 outils/exhibition/simuler_exhibition.py --home CTX --away MNL [--candidats 16] [--id exh-v21-ctx-mnl]
Durée : l'exécution complète du notebook (≈ 15-20 min, tests compris) + quelques secondes.
"""
import argparse, json, os, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

CELL = r'''
# ==== EXHIBITION (ajoutée par outils/exhibition/simuler_exhibition.py, pas dans le notebook) ====
import json as _xj, os as _xo, glob as _xg
_P = _xj.loads(_xo.environ["GC_EXH"])
_weeks = sorted(_xg.glob(_xo.path.join(_P["weeks"], "week_*", "week.json")))
_prev = _xj.load(open(_weeks[-1], encoding="utf-8")) if _weeks else None
apply_staff_snapshots(INITIAL_STAFFS)
if _prev and _prev.get("staffs_next_week"):
    apply_staff_snapshots(_prev["staffs_next_week"])
_H, _A = _P["home"], _P["away"]
_cands = []
for _k in range(_P["candidates"]):
    _seed = _P["seed_base"] + _k
    _m = franchise_game(_H, _A, seed=_seed)
    _f = export_gamefeed(_m, game_id=_P["id"], featured=False, season=(_prev or {}).get("week", {}).get("index", 0), week="Exhibition")
    _pl = _f["plays"]
    _adj = sum(len(p.get("adjust") or []) for p in _pl)
    _kinds = sorted({a.get("kind") for p in _pl for a in (p.get("adjust") or [])})
    _conc = len({(p.get("call") or {}).get("concept") for p in _pl if (p.get("call") or {}).get("type") in ("run", "pass")})
    _margin = abs(_m["home_score"] - _m["away_score"])
    _score = _adj * 3 + len(_kinds) * 4 + _conc - max(0, _margin - 7) * 2
    _cands.append((_score, _seed, _m, _adj, _kinds, _conc, _margin))
    print(f"candidat {_seed}: {_A} {_m['away_score']} - {_H} {_m['home_score']} · ajustements {_adj} {_kinds} · concepts {_conc}")
_cands.sort(key=lambda c: -c[0])
_score, _seed, _m, _adj, _kinds, _conc, _margin = _cands[0]
_odds = engine_pregame_odds(AI_FRANCHISES[_H], AI_FRANCHISES[_A], n_sims=_P["odds_sims"])
attach_engine_odds(_m, _odds)
_feed = export_gamefeed(_m, game_id=_P["id"], featured=False, season=(_prev or {}).get("week", {}).get("index", 0), week="Exhibition")
_feed["game"].update(phase="exhibition", slot=None, kickoff=None, week_start=None,
    exhibition={"engine": _P["engine"], "seed": _seed, "staffs_from": _xo.path.basename(_xo.path.dirname(_weeks[-1])) if _weeks else "départ",
                "adjustments": _adj, "adjust_kinds": _kinds, "concepts": _conc, "candidates": _P["candidates"]})
_xo.makedirs(_P["out"], exist_ok=True)
with open(_xo.path.join(_P["out"], _P["id"] + ".json"), "w", encoding="utf-8") as _fh:
    _xj.dump(_feed, _fh, ensure_ascii=False, separators=(",", ":"))
print("EXHIBITION_OK", _xj.dumps({"seed": _seed, "home": _m["home_score"], "away": _m["away_score"], "plays": len(_feed["plays"]), "adjust": _adj, "kinds": _kinds, "concepts": _conc}))
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--home", default="CTX"); ap.add_argument("--away", default="MNL")
    ap.add_argument("--candidats", type=int, default=16); ap.add_argument("--id", default=None)
    ap.add_argument("--notebook", default=os.path.join(ROOT, "NFL_Sim_GameCenter.ipynb"))
    ap.add_argument("--data", default=os.path.join(ROOT, "data"))
    ap.add_argument("--titre", default="Notebook V22.1 · QB reads & post-snap coverage · adaptive coordinators")
    ap.add_argument("--sans-decisions", action="store_true",
                    help="moteur V21 : décisions de passe du bloc A coupées (ENGINE INTELLIGENCE, allumées par défaut)")
    a = ap.parse_args()
    import nbformat
    from nbclient import NotebookClient
    gid = a.id or f"exh-{a.home.lower()}-{a.away.lower()}"
    out = os.path.join(a.data, "exhibitions")
    params = {"home": a.home, "away": a.away, "candidates": a.candidats, "id": gid, "out": os.path.abspath(out),
              "weeks": os.path.abspath(os.path.join(a.data, "weeks")), "odds_sims": 300,
              "seed_base": 9_400_000,          # hors saison (≈ 1 001 001…) et hors cotes (≥ 10 000 000)
              "engine": a.titre}
    for k in ("GC_WEEK_START", "GC_PREV_WEEK", "GC_OUT"):
        os.environ.pop(k, None)               # surtout pas de semaine produite
    os.environ["GC_EXH"] = json.dumps(params)
    os.environ.setdefault("GC_MOTEUR_DIR", ROOT)        # modules moteur/ (V22)
    os.environ["GC_DECISIONS"] = "0" if a.sans_decisions else "1"
    nb = nbformat.read(a.notebook, as_version=4)
    nb.cells.append(nbformat.v4.new_code_cell(CELL))
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        NotebookClient(nb, timeout=3600, kernel_name="python3", resources={"metadata": {"path": tmp}}).execute()
    res = None
    for o in nb.cells[-1].get("outputs", []):
        txt = o.get("text", "")
        for line in txt.splitlines():
            print("  ", line)
            if line.startswith("EXHIBITION_OK "):
                res = json.loads(line[len("EXHIBITION_OK "):])
    if not res:
        sys.exit("la cellule d'exhibition n'a rien écrit")
    # index des exhibitions (lu par le serveur)
    idx_path = os.path.join(out, "index.json")
    idx = json.load(open(idx_path, encoding="utf-8")) if os.path.exists(idx_path) else {"exhibitions": []}
    idx["exhibitions"] = [x for x in idx["exhibitions"] if x["id"] != gid] + [{
        "id": gid, "home": a.home, "away": a.away, "title": a.titre, "created": time.strftime("%Y-%m-%d"),
        "plays": res["plays"], "adjustments": res["adjust"], "adjust_kinds": res["kinds"], "concepts": res["concepts"]}]
    with open(idx_path, "w", encoding="utf-8") as fh:
        json.dump(idx, fh, ensure_ascii=False, indent=1)
    print(f"Exhibition {gid} écrite en {int(time.time() - t0)} s : {res}")


if __name__ == "__main__":
    main()
