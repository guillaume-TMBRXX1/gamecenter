#!/usr/bin/env python3
"""Identité de jeu des franchises, mesurée sur les matchs joués (refonte des playbooks, étape 1 — 27/10/2026).

Lit les GameFeed d'une ou plusieurs semaines (data/weeks/week_*/games/*.json) et mesure, pour chaque franchise, ce
qu'elle JOUE vraiment — pas ce que son playbook permet :
  attaque  : part de passes (en général, 1er & 10, 3e et long), familles de concepts (passes courtes, intermédiaires,
             profondes, écrans, play-action / bootleg, RPO, courses intérieures, en force, extérieures, option / QB),
             concepts et formations favoris, personnel, motions, plays joués, plays que personne d'autre ne joue,
             concepts « signature » (≥ 3 % de ses appels et ≥ 1,5 fois la moyenne de la ligue), 4e essais tentés,
             gros gains (20 yards ou plus), zone rouge et courte distance ;
  défense  : couvertures (concept et paquet), blitz, fronts, formations, stunts, ballons récupérés par match ;
  distance : divergence de Jensen-Shannon (0 = même jeu que la ligue, 1 = rien en commun) entre le mélange de concepts
             d'une franchise et celui de la ligue, et franchise la plus proche.
Ne charge pas le moteur et ne modifie rien : lecture des GameFeed seulement. Une action est classée par le concept
APPELÉ (un scramble sur une passe reste une passe ; genou et spike sont exclus).

    python3 outils/moteur/identite_playbooks.py                          # dernière semaine, résumé à l'écran
    python3 outils/moteur/identite_playbooks.py --semaines 3             # 3 dernières semaines ensemble
    python3 outils/moteur/identite_playbooks.py --md rapport.md --json rapport.json

Depuis « gamecenter_serveur (1) ».
"""
import argparse, collections, glob, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVEUR = os.path.abspath(os.path.join(HERE, "..", ".."))
WEEKS = os.path.join(SERVEUR, "data", "weeks")

# familles de concepts offensifs (concept appelé -> famille) ; tout concept inconnu tombe dans « autre »
FAMILLES = {
    "courte": ("QUICK_SLANT", "STICK", "SHORT_OUT", "HITCH", "SPOT_SNAG", "PIVOT", "CHOICE", "CURL", "DRAG", "MESH",
               "MESH_WHEEL", "DART_QUICK_DIG"),
    "intermediaire": ("IN", "CROSS", "Y_CROSS", "LEVELS", "DOUBLE_DIG", "FLOOD", "SAIL", "DAGGER", "DEEP_CROSS", "CHAMP"),
    "profonde": ("DEEP_POST", "CORNER", "DOUBLE_POST", "FOUR_VERTS", "SWITCH_VERTICALS", "DIVIDE"),
    "ecran": ("SCREEN", "FL_SE_SCREEN", "WR_TUNNEL_SCREEN"),
    "play_action": ("PLAY_ACTION", "BOOT", "PA_FLOOD", "PA_SLIDE", "POP"),
    "rpo": ("RPO_ALERT", "RPO_INSIDE_ZONE", "RPO_OUTSIDE_ZONE", "RPO_PEEK", "RPO_POWER", "RPO_READ", "RPO_ALERT_THROW",
            "RPO_INSIDE_ZONE_THROW", "RPO_OUTSIDE_ZONE_THROW", "RPO_PEEK_THROW", "RPO_POWER_THROW", "RPO_READ_THROW"),
    "course_interieure": ("INSIDE_RUN", "TRAP", "DRAW", "WHAM", "QB_DRAW"),
    "course_force": ("POWER", "COUNTER", "PIN_PULL"),
    "course_exterieure": ("OUTSIDE_RUN", "BUCK_SWEEP", "COUNTER_SWEEP", "POWER_TOSS", "JET_SWEEP", "JET_ACTION",
                          "END_AROUND", "REVERSE", "DOUBLE_REVERSE"),
    "option_qb": ("READ_OPTION", "POWER_READ", "INVERTED_VEER", "MIDLINE_OPTION", "SHOVEL_OPTION", "SPEED_OPTION",
                  "TRIPLE_OPTION", "QB_SWEEP"),
}
FAMILLE_DE = {c: f for f, cs in FAMILLES.items() for c in cs}
COURSES = set(FAMILLES["course_interieure"] + FAMILLES["course_force"] + FAMILLES["course_exterieure"]
              + FAMILLES["option_qb"]) | {c for c in FAMILLES["rpo"] if not c.endswith("_THROW")}
EXCLUS = {"KNEEL", "SPIKE"}
LIBELLES = {"courte": "passes courtes", "intermediaire": "passes intermédiaires", "profonde": "passes profondes",
            "ecran": "écrans", "play_action": "play-action / bootleg", "rpo": "RPO", "course_interieure":
            "courses intérieures", "course_force": "courses en force", "course_exterieure": "courses extérieures",
            "option_qb": "option / QB", "autre": "autre"}
SIGNATURE_PART, SIGNATURE_LIFT = 0.03, 1.5


def famille(concept):
    return FAMILLE_DE.get(concept, "autre")


def est_passe(concept):
    return concept not in COURSES


def yards_a_marquer(play):
    """Yards jusqu'à l'en-but adverse : le terrain va de 0 à 120, l'équipe à domicile attaque vers 110."""
    x = play.get("los_x")
    if x is None:
        return None
    return 110 - x if play.get("offense") == "home" else x - 10


def js(a, b):
    """Divergence de Jensen-Shannon (base 2, entre 0 et 1) entre deux compteurs."""
    sa, sb = sum(a.values()), sum(b.values())
    if not sa or not sb:
        return None
    r = 0.0
    for k in set(a) | set(b):
        p, q = a.get(k, 0) / sa, b.get(k, 0) / sb
        m = (p + q) / 2
        if p:
            r += p * math.log2(p / m) / 2
        if q:
            r += q * math.log2(q / m) / 2
    return r


def semaines(n=1, weeks_dir=WEEKS):
    ds = sorted(d for d in glob.glob(os.path.join(weeks_dir, "week_*")) if os.path.exists(os.path.join(d, "week.json")))
    return ds[-n:] if n else ds


def _equipe():
    return {"snaps": 0, "passes": 0, "concepts": collections.Counter(), "familles": collections.Counter(),
            "formations": collections.Counter(), "personnel": collections.Counter(), "plays": collections.Counter(),
            "motions": 0, "pa": 0, "rpo": 0, "gros_gains": 0,
            "neutre": [0, 0], "troisieme_long": [0, 0], "courte_distance": [0, 0],
            "zone_rouge": collections.Counter(), "quatrieme": [0, 0],
            "def_snaps": 0, "def_concepts": collections.Counter(), "def_paquets": collections.Counter(),
            "def_fronts": collections.Counter(), "def_formations": collections.Counter(), "stunts": 0,
            "ballons": 0, "matchs": 0}


def mesurer(dossiers):
    """{équipe: mesures brutes} sur les GameFeed des semaines données."""
    E = collections.defaultdict(_equipe)
    for d in dossiers:
        doc = json.load(open(os.path.join(d, "week.json"), encoding="utf-8"))
        for g in doc["schedule"]:
            p = os.path.join(d, g["feed"])
            if not os.path.exists(p):
                continue
            f = json.load(open(p, encoding="utf-8"))
            abbr = {s: (f["game"].get(s) or {}).get("abbr") for s in ("home", "away")}
            if not all(abbr.values()):
                continue
            for a in abbr.values():
                E[a]["matchs"] += 1
            for play in f.get("plays", []):
                c = play.get("call") or {}
                att, dfn = abbr.get(play.get("offense")), abbr.get("away" if play.get("offense") == "home" else "home")
                if not att:
                    continue
                if play.get("down") == 4 and c.get("type") in ("run", "pass", "punt", "field_goal"):
                    E[att]["quatrieme"][1] += 1
                    if c.get("type") in ("run", "pass") and c.get("concept") not in EXCLUS:
                        E[att]["quatrieme"][0] += 1
                if c.get("type") not in ("run", "pass") or c.get("concept") in EXCLUS or not c.get("concept"):
                    continue
                o, k = E[att], c["concept"]
                passe = est_passe(k)
                o["snaps"] += 1
                o["passes"] += passe
                o["concepts"][k] += 1
                o["familles"][famille(k)] += 1
                o["formations"][c.get("formation")] += 1
                o["personnel"][c.get("personnel") or "?"] += 1
                o["plays"][c.get("play_id")] += 1
                o["motions"] += bool(c.get("motion"))
                o["pa"] += famille(k) == "play_action"
                o["rpo"] += famille(k) == "rpo"
                o["gros_gains"] += (play.get("gain") or 0) >= 20
                down, togo, ytg = play.get("down"), play.get("to_go") or 0, yards_a_marquer(play)
                if down == 1 and togo == 10:
                    o["neutre"][0] += passe; o["neutre"][1] += 1
                if down == 3 and togo >= 7:
                    o["troisieme_long"][0] += passe; o["troisieme_long"][1] += 1
                if down in (3, 4) and togo <= 2:
                    o["courte_distance"][0] += not passe; o["courte_distance"][1] += 1
                if ytg is not None and ytg <= 20:
                    o["zone_rouge"][famille(k)] += 1
                if dfn:
                    dd, x = c.get("defense") or {}, E[dfn]
                    x["def_snaps"] += 1
                    x["def_concepts"][dd.get("concept")] += 1
                    if dd.get("package"):
                        x["def_paquets"][dd["package"]] += 1
                    if dd.get("front"):
                        x["def_fronts"][dd["front"]] += 1
                    x["def_formations"][dd.get("formation")] += 1
                    x["stunts"] += bool(dd.get("rush"))
                    if play.get("result") in ("interception", "fumble_lost"):
                        x["ballons"] += 1
    return dict(E)


def _part(n, d):
    return n / d if d else None


def analyser(E):
    """Indicateurs par équipe (parts entre 0 et 1) et indicateurs de la ligue."""
    eq = sorted(t for t in E if E[t]["snaps"])
    ligue_c, ligue_f = collections.Counter(), collections.Counter()
    for t in eq:
        ligue_c.update(E[t]["concepts"]); ligue_f.update(E[t]["familles"])
    tot = sum(ligue_c.values())
    joueurs = collections.Counter()
    for t in eq:
        joueurs.update(set(E[t]["plays"]))
    R = {}
    for t in eq:
        o = E[t]; n = o["snaps"]
        sig = [(k, v / n, (v / n) / (ligue_c[k] / tot)) for k, v in o["concepts"].items()
               if v / n >= SIGNATURE_PART and (v / n) / (ligue_c[k] / tot) >= SIGNATURE_LIFT]
        proches = sorted((js(o["concepts"], E[u]["concepts"]), u) for u in eq if u != t)
        R[t] = {
            "matchs": o["matchs"], "snaps": n, "passe": o["passes"] / n,
            "passe_1er_10": _part(*o["neutre"]), "passe_3e_long": _part(*o["troisieme_long"]),
            "course_courte_distance": _part(*o["courte_distance"]),
            "familles": {f: v / n for f, v in o["familles"].most_common()},
            "concepts": [(k, v / n) for k, v in o["concepts"].most_common(8)],
            "formations": [(k, v / n) for k, v in o["formations"].most_common(5)],
            "personnel": [(k, v / n) for k, v in o["personnel"].most_common(4)],
            "motion": o["motions"] / n, "play_action": o["pa"] / n, "rpo": o["rpo"] / n, "gros_gains": o["gros_gains"] / n,
            "plays_distincts": len(o["plays"]), "plays_exclusifs": sorted(p for p in o["plays"] if joueurs[p] == 1),
            "signatures": sorted(sig, key=lambda s: -s[1]),
            "zone_rouge": {f: v / sum(o["zone_rouge"].values()) for f, v in o["zone_rouge"].most_common(3)} if o["zone_rouge"] else {},
            "quatrieme_tente": _part(*o["quatrieme"]),
            "ecart_ligue": js(o["concepts"], ligue_c), "ecart_familles": js(o["familles"], ligue_f),
            "plus_proche": (proches[0][1], proches[0][0]) if proches else None,
            "def": {
                "snaps": o["def_snaps"],
                "concepts": [(k, v / o["def_snaps"]) for k, v in o["def_concepts"].most_common(4)] if o["def_snaps"] else [],
                "blitz": _part(o["def_concepts"].get("BLITZ", 0), o["def_snaps"]),
                "homme": _part(o["def_concepts"].get("MAN", 0), o["def_snaps"]),
                "paquets": [(k, v / o["def_snaps"]) for k, v in o["def_paquets"].most_common(3)] if o["def_snaps"] else [],
                "fronts": [(k, v / o["def_snaps"]) for k, v in o["def_fronts"].most_common(2)] if o["def_snaps"] else [],
                "formations": [(k, v / o["def_snaps"]) for k, v in o["def_formations"].most_common(3)] if o["def_snaps"] else [],
                "stunts": _part(o["stunts"], o["def_snaps"]),
                "ballons_par_match": o["ballons"] / o["matchs"] if o["matchs"] else None,
            },
        }
    ecarts = [R[t]["ecart_ligue"] for t in eq]
    paires = sorted((js(E[a]["concepts"], E[b]["concepts"]), a, b) for i, a in enumerate(eq) for b in eq[i + 1:])
    ligue = {"equipes": len(eq), "snaps": tot, "plays_distincts": len(joueurs),
             "plays_exclusifs": sum(1 for p in joueurs if joueurs[p] == 1), "concepts": len(ligue_c),
             "passe": sum(E[t]["passes"] for t in eq) / tot if tot else None,
             "familles": {f: v / tot for f, v in ligue_f.most_common()},
             "ecart_moyen": sum(ecarts) / len(ecarts) if ecarts else None,
             "paires_proches": paires[:5], "paires_eloignees": paires[-3:]}
    return R, ligue


def _pc(x, d=0):
    return "—" if x is None else f"{100 * x:.{d}f} %"


def markdown(R, ligue, titre):
    L = [f"# Identité de jeu des franchises — {titre}", "",
         f"{ligue['equipes']} franchises, {ligue['snaps']} appels de course ou de passe (genou et spike exclus). "
         f"{ligue['plays_distincts']} plays différents joués, dont {ligue['plays_exclusifs']} par une seule franchise ; "
         f"{ligue['concepts']} concepts. Passes : {_pc(ligue['passe'])}. Écart moyen à la ligue (Jensen-Shannon, concepts) : "
         f"{ligue['ecart_moyen']:.3f}.", "",
         "Paires les plus proches : " + ", ".join(f"{a}–{b} ({x:.3f})" for x, a, b in ligue["paires_proches"]) + ".",
         "Paires les plus éloignées : " + ", ".join(f"{a}–{b} ({x:.3f})" for x, a, b in ligue["paires_eloignees"]) + ".", "",
         "| Franchise | Passes | 1er & 10 | 3e et long | Courte dist. (course) | Motion | PA | RPO | Gros gains | 4e tentés | "
         "Plays | Exclusifs | Écart ligue | Plus proche |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for t, r in R.items():
        pp = r["plus_proche"]
        L.append(f"| {t} | {_pc(r['passe'])} | {_pc(r['passe_1er_10'])} | {_pc(r['passe_3e_long'])} | "
                 f"{_pc(r['course_courte_distance'])} | {_pc(r['motion'])} | {_pc(r['play_action'])} | {_pc(r['rpo'])} | "
                 f"{_pc(r['gros_gains'], 1)} | {_pc(r['quatrieme_tente'])} | {r['plays_distincts']} | "
                 f"{len(r['plays_exclusifs'])} | {r['ecart_ligue']:.3f} | {pp[0]} ({pp[1]:.3f}) |")
    L += ["", "Familles de la ligue : " + ", ".join(f"{LIBELLES[f]} {_pc(v)}" for f, v in ligue["familles"].items()) + ".", ""]
    for t, r in R.items():
        d = r["def"]
        L += [f"## {t}", "",
              "- **Familles** : " + ", ".join(f"{LIBELLES[f]} {_pc(v)}" for f, v in r["familles"].items()),
              "- **Concepts** : " + ", ".join(f"{k} {_pc(v)}" for k, v in r["concepts"]),
              "- **Signatures** (≥ 3 % et ≥ ×1,5 la ligue) : " + (", ".join(f"{k} {_pc(v)} (×{x:.1f})" for k, v, x in r["signatures"]) or "aucune"),
              "- **Formations** : " + ", ".join(f"{k} {_pc(v)}" for k, v in r["formations"]) +
              " · **personnel** : " + ", ".join(f"{k} {_pc(v)}" for k, v in r["personnel"]),
              "- **Zone rouge** : " + (", ".join(f"{LIBELLES[f]} {_pc(v)}" for f, v in r["zone_rouge"].items()) or "—"),
              f"- **Défense** : " + ", ".join(f"{k} {_pc(v)}" for k, v in d["concepts"]) +
              f" · blitz {_pc(d['blitz'])} · homme {_pc(d['homme'])} · stunts {_pc(d['stunts'])} · paquets : " +
              ", ".join(f"{k} {_pc(v)}" for k, v in d["paquets"]) + " · formations : " +
              ", ".join(f"{k} {_pc(v)}" for k, v in d["formations"]) +
              (f" · ballons récupérés {d['ballons_par_match']:.2f} / match" if d["ballons_par_match"] is not None else ""),
              ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--semaines", type=int, default=1, help="nombre de dernières semaines (0 = toutes)")
    ap.add_argument("--weeks", default=WEEKS, help="dossier des semaines")
    ap.add_argument("--md", help="écrire le rapport Markdown ici")
    ap.add_argument("--json", help="écrire les mesures JSON ici")
    a = ap.parse_args()
    ds = semaines(a.semaines, a.weeks)
    if not ds:
        sys.exit("aucune semaine trouvée")
    R, ligue = analyser(mesurer(ds))
    titre = ", ".join(os.path.basename(d)[5:] for d in ds)
    md = markdown(R, ligue, "semaine" + ("s " if len(ds) > 1 else " ") + titre)
    if a.md:
        open(a.md, "w", encoding="utf-8").write(md + "\n")
    if a.json:
        json.dump({"semaines": titre, "ligue": ligue, "franchises": R}, open(a.json, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    if not a.md:
        print("\n".join(md.split("\n")[:8 + len(R)]))
    else:
        print(f"{len(R)} franchises, {ligue['snaps']} appels · écart moyen {ligue['ecart_moyen']:.3f} -> {a.md}")


if __name__ == "__main__":
    main()
