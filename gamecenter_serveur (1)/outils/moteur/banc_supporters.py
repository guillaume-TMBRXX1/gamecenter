#!/usr/bin/env python3
"""Front office, étape FO-1 : mesure des leviers des supporters sur le test d'équilibre de 12.3 (mêmes graines).

Le moteur est chargé une fois (cellules jusqu'à 12.3, contrôles lourds sautés) ; chaque passage est un processus fils
(fork) qui relit moteur/supporters.py, exécute la cellule des supporters (12.2 quinquatricies) telle qu'elle est dans le
notebook, applique une configuration aux 24 franchises, puis répartit les matchs entre des travailleurs :

  base              GC_SUPPORTERS coupé (moteur d'aujourd'hui)
  coord             toutes les franchises sur « coordinateur » (doit redonner base, match par match)
  <levier>:<option> toutes les franchises sur cette option (effet visible de l'option)
  hasard:<levier>   une option tirée au hasard par franchise (graine fixe) : équilibre, effet sur les victoires

Par passage : mesures de la ligue (rapport_calibration), % de victoires par franchise, et par franchise en attaque /
défense : 4es essais tentés par match, part des courses, taux de blitz, part d'homme à homme, profondeur moyenne des
passes (yards dans l'air de la cible lancée) ; une signature des matchs (déterminisme, identité avec base).

    python3 outils/moteur/banc_supporters.py --sortie /tmp/fo1.json                  # tout (≈ 8 min + 18 passages)
    python3 outils/moteur/banc_supporters.py --passages base,coord,quatrieme:agressif --graines 1
"""
import argparse, collections, hashlib, json, multiprocessing, os, random, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rapport_calibration as rc     # noqa: E402
import equilibre_identite as ei      # noqa: E402
sys.path.insert(0, rc.SERVEUR)
from moteur import supporters as _FO   # noqa: E402

JUSQUA = "TEST D'ÉQUILIBRE + AJUSTEMENT HEBDOMADAIRE"        # 12.3
CELLULE = "12.2 quinquatricies"
_NS = {}


def _cellule(ns):
    """Relit moteur/supporters.py et exécute la cellule des supporters du notebook dans ns."""
    import contextlib, importlib, io
    importlib.reload(importlib.import_module("moteur.supporters"))
    nb = json.load(open(rc.NOTEBOOK, encoding="utf-8"))
    src = next("".join(c["source"]) for c in nb["cells"]
               if c["cell_type"] == "code" and CELLULE in "".join(c["source"])[:400])
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(src, "<cellule supporters>", "exec"), ns)


def _profondeur(e):
    """Yards dans l'air d'une passe complétée (decision.yac.air ; None sinon)."""
    v = ((e.get("decision") or {}).get("yac") or {}).get("air")
    return float(v) if isinstance(v, (int, float)) else None


def _match(tache):
    h, a, g = tache
    ns = _NS["ns"]
    t = time.perf_counter()
    m = ns["franchise_game"](h, a, seed=g)
    dt = time.perf_counter() - t
    sig = hashlib.md5(json.dumps([(e.get("play_id"), e.get("yards_gained"), e.get("def_concept"))
                                  for e in m["play_log"]]).encode()).hexdigest()[:12]
    eq = collections.defaultdict(collections.Counter)
    for e in m["play_log"]:
        if e.get("kind") != "OFF":
            continue
        o, d = e["offense"], e["defense"]
        co = e.get("coordinator") or {}
        if co.get("go_for_it"):
            eq[o]["go4"] += 1
        eq[o]["snaps"] += 1
        eq[o]["runs"] += e["play_type"] == "RUN"
        eq[d]["def_snaps"] += 1
        eq[d]["blitz"] += e.get("def_concept") == "BLITZ"
        eq[d]["man"] += e.get("def_concept") == "MAN"
        dec = e.get("decision") or {}
        if e["play_type"] == "PASS" and dec.get("family"):
            eq[d]["cov_snaps"] += 1
            eq[d]["cov_man"] += dec["family"] == "homme"
        if e["play_type"] == "PASS":
            cc = e.get("play_concept")
            eq[o]["pass_calls"] += 1
            eq[o]["long_calls"] += cc in _FO.LONGS
            eq[o]["short_calls"] += cc in _FO.COURTS
        p = _profondeur(e) if e["play_type"] == "PASS" else None
        if p is not None:
            eq[o]["passes"] += 1
            eq[o]["air"] += p
            eq[o]["deep"] += p >= 15
    c = _compter_match(m)
    return h, a, m["home_score"], m["away_score"], c, dt, sig, {k: dict(v) for k, v in eq.items()}


def _compter_match(m):
    """Compteurs de la ligue (mêmes définitions que equilibre_identite._compter), sur un match déjà joué."""
    ei._NS["ns"] = {"franchise_game": lambda h, a, seed=None: m}
    return ei._compter(("H", "A", 0))[4]


def _configurer(ns, nom):
    """Applique la configuration `nom` aux franchises (dans le fils). Renvoie le dict des choix."""
    if nom == "base":
        return {}
    FO = ns["FO"]
    equipes = list(ns["LEAGUE_TEAMS"])
    if nom == "coord":
        lv, choix = "quatrieme", {a: FO.COORD for a in equipes}
    elif nom.startswith("hasard:"):
        lv = nom.split(":", 1)[1]
        rng = random.Random(f"fo1|{lv}")
        choix = {a: rng.choice(FO.options(lv)) for a in equipes}
    else:
        lv, op = nom.split(":", 1)
        choix = {a: op for a in equipes}
    for a in equipes:
        FO.appliquer(ns["AI_FRANCHISES"][a].coordinator, a, lv, choix[a], ns["FANS_SEMAINE"])
    return {"lever": lv, "choices": choix}


def passage(ns, nom, graines, travailleurs, sortie):
    pid = os.fork()
    if pid:
        os.waitpid(pid, 0)
        return json.load(open(sortie, encoding="utf-8"))
    code = 0
    try:
        if nom != "base":                                # base : le notebook sans la cellule des supporters
            _cellule(ns)
        cfg = _configurer(ns, nom)
        _NS["ns"] = ns
        eq = list(ns["AI_FRANCHISES"])
        taches = [(h, a, ei.graine(h, a, s)) for h in eq for a in eq if h != a for s in range(graines)]
        t0 = time.time()
        with multiprocessing.get_context("fork").Pool(travailleurs) as pool:
            res = pool.map(_match, taches, chunksize=8)
        m = ei.mesures([r[:6] for r in res])
        m["mur_s"] = time.time() - t0
        m["config"] = cfg
        m["signatures"] = [r[6] for r in res]
        tot = collections.defaultdict(collections.Counter)
        for r in res:
            for t, c in r[7].items():
                tot[t].update(c)
            tot[r[0]]["games"] += 1
            tot[r[1]]["games"] += 1
        m["equipes"] = {t: dict(c) for t, c in sorted(tot.items())}
        json.dump(m, open(sortie, "w", encoding="utf-8"))
    except Exception:                                    # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.stderr.flush()
        code = 1
    os._exit(code)


def resume(m):
    """Indicateurs de la ligue pour un passage : par match / par snap."""
    T = m["equipes"]
    s = lambda k: sum(t.get(k, 0) for t in T.values())
    g = s("games") / 2
    return {"go4_pg": s("go4") / g, "run_share": s("runs") / max(1, s("snaps")),
            "blitz_rate": s("blitz") / max(1, s("def_snaps")), "man_share": s("man") / max(1, s("def_snaps")),
            "man_cov": s("cov_man") / max(1, s("cov_snaps")), "long_calls": s("long_calls") / max(1, s("pass_calls")),
            "air_yards": s("air") / max(1, s("passes")), "deep_share": s("deep") / max(1, s("passes")),
            "points_pg": m["points_pg"], "win_min": min(m["win_pct"].values()), "win_max": max(m["win_pct"].values())}


DEFAUT = (["base", "coord"] + [f"{lv}:{op}" for lv, ops in (
    ("quatrieme", ("prudent", "agressif")), ("course_passe", ("plus_course", "plus_passe")),
    ("blitz", ("moins", "plus")), ("couverture", ("zone", "homme")), ("profondeur", ("courtes", "longues")))
    for op in ops] + [f"hasard:{lv}" for lv in ("quatrieme", "course_passe", "blitz", "couverture", "profondeur")])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--graines", type=int, default=4, help="matchs par affiche (12.3 : 4 à 24 équipes)")
    ap.add_argument("--travailleurs", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--passages", default=",".join(DEFAUT))
    ap.add_argument("--sortie", help="rapport JSON (un objet par passage)")
    a = ap.parse_args()
    os.environ["GC_LEGER"] = "1"
    t0 = time.time()
    ns, _ = rc.charger(jusqua=JUSQUA, decisions=True)
    print(f"moteur chargé en {time.time() - t0:.0f} s", file=sys.stderr)
    import tempfile
    tmp = tempfile.mkdtemp(prefix="gc-fo1-")
    out = {}
    for nom in a.passages.split(","):
        out[nom] = passage(ns, nom, a.graines, a.travailleurs, os.path.join(tmp, nom.replace(":", "_") + ".json"))
        r = resume(out[nom])
        print(f"{nom:24s} 4e/m {r['go4_pg']:.2f} · courses {r['run_share']:.1%} · blitz {r['blitz_rate']:.1%} · "
              f"homme {r['man_share']:.1%} (couv. {r['man_cov']:.1%}) · longues {r['long_calls']:.1%} · air {r['air_yards']:.2f} yd · pts {r['points_pg']:.1f} · "
              f"vict. {r['win_min']:.3f}-{r['win_max']:.3f} · {out[nom]['mur_s']:.0f} s", file=sys.stderr, flush=True)
        if a.sortie:
            json.dump(out, open(a.sortie, "w", encoding="utf-8"))


if __name__ == "__main__":
    main()
