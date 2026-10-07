#!/usr/bin/env python3
"""Validation complète du programme ENGINE INTELLIGENCE (fin de programme, phases 13 et 14).

Un seul outil pour tout ce que la feuille de route demande avant l'étape 6 :

1. **tests unitaires** de tous les modules (`moteur/tests`, blocs A → E) ;
2. **tests d'intégration**, pour chaque étage du moteur (V21 historique, A, A+B, A-C, A-D, A-E) et sur les
   1 008 matchs du test d'équilibre (12.3) : GameFeed exporté et validé (`validate_gamefeed` du notebook), contrôle
   de chaque action par `audit_moteur.check_game` (score, horloge, downs, possession, ajustements, notes du bloc E),
   identités stats joueurs = stats d'équipe (`season_stats` de 14.1 : passes, réceptions, courses, INT, sacks),
   champs de chaque bloc présents dans le GameFeed ;
3. **déterminisme** : chaque match rejoué (dans l'ordre et à l'envers) redonne exactement le même match ; deux
   processus Python différents (graine de hachage différente) donnent les mêmes matchs ; une trajectoire de
   progression (bloc E) rejouée redonne le même état ;
4. **non-régression** : chaque étage redonne EXACTEMENT les chiffres de son rapport de calibration publié
   (V23 bloc A + safety, V23, V24, V25, V26) ; bloc E au départ = V25 match par match ; calibration (garde-fou 3)
   de chaque étage contre la référence V21 (tolérances de `rapport_calibration.TOLERANCES`, équilibre 40-60 %) ;
5. **stats joueurs / équipes et Next Gen Stats** (repères, non bloquants) : par équipe et par match, leaders,
   répartition des réceptions par poste, défense créditée, temps avant le lancer, pression, 1re lecture, types de
   réception, jeux explosifs, 3e essais — comparés au moteur V21 ;
6. **plusieurs semaines enchaînées** (bloc E) : test d'équilibre après N semaines de progression (`--semaines`),
   sur une trajectoire neuve, plus la trajectoire du rapport V26 (8 semaines) pour la non-régression.

    python3 outils/moteur/validation_complete.py                                   # tout (≈ 30 min sur 3 cœurs)
    python3 outils/moteur/validation_complete.py --rapide                          # 8 graines, 2 et 4 semaines
    python3 outils/moteur/validation_complete.py --sortie outils/moteur/rapport_validation_complete.json
    python3 outils/moteur/validation_complete.py --travailleur ABCDE --graines 4   # un seul étage (débogage)

Code de sortie 1 si un contrôle BLOQUANT échoue (tests, intégration, déterminisme, non-régression, tolérances).
La simulation d'une vraie semaine (notebook complet, cotes comprises) reste `generer_semaine.py` + `audit_moteur.py`.
"""
import argparse, collections, hashlib, json, os, re, statistics, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
SERVEUR = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, SERVEUR)
import rapport_calibration as rc            # noqa: E402  (charger, mesurer, _stats, comparer, TOLERANCES)

# étages du moteur : interrupteurs (décisions, B, C, D, E) et rapport publié qu'ils doivent redonner à l'identique
ETAGES = {
    "V21":   dict(flags=(False, False, False, False, False), titre="moteur historique (décisions coupées, safety V23)"),
    "A":     dict(flags=(True, False, False, False, False), titre="bloc A (+ safety)",
                  historique=("rapport_v23_safety_bloc_a.json", None)),
    "AB":    dict(flags=(True, True, False, False, False), titre="blocs A-B (V23)",
                  historique=("rapport_v23_bloc_b.json", None)),
    "ABC":   dict(flags=(True, True, True, False, False), titre="blocs A-C (V24)",
                  historique=("rapport_v24_bloc_c.json", None)),
    "ABCD":  dict(flags=(True, True, True, True, False), titre="blocs A-D (V25)",
                  historique=("rapport_v25_bloc_d.json", None)),
    "ABCDE": dict(flags=(True, True, True, True, True), titre="blocs A-E (V26), au départ",
                  historique=("rapport_v26_bloc_e.json", "depart")),
}
GRAINE_TRAJECTOIRE_V26 = 990_000         # graine par défaut de rapport_calibration (--graine-trajectoire)
GRAINE_TRAJECTOIRE_NEUVE = 660_000       # trajectoire jamais mesurée (le rapport V26 a utilisé 770 000, 550 000,
                                         # 330 000 et 990 000 pour 8, 16, 24 et 32 semaines)


def trajectoires_v26():
    """{nom du rapport: (semaines, graine)} des rapports publiés du bloc E (non-régression)."""
    doc = json.load(open(os.path.join(HERE, "rapport_v26_bloc_e.json"), encoding="utf-8"))["rapports"]
    return {k: (r["progression"]["semaines"], r["progression"]["graine"]) for k, r in doc.items() if r.get("progression")}
# mesures comparées à l'identique avec un rapport publié (pas les temps : ils dépendent de la machine)
MESURES_EXACTES = ("games", "completion_pct", "sack_rate", "int_rate", "ypa", "net_ypa", "ypc", "turnovers_pg",
                   "int_pg", "fumbles_lost_pg", "points_pg", "drives_pg", "first_downs_pg", "plays_pg", "pass_rate",
                   "attempts_pg", "sacks_pg", "scrambles_pg", "safeties_pg", "games_with_safety", "win_pct")
# artefacts d'un match joué hors d'une semaine (pas de cotes calculées, pas de semaine dans la courbe du bloc E)
AUDIT_HORS_SEMAINE = ("pas de cotes d'avant-match", "courbe de progression vide")
# identités exactes stats joueurs = stats d'équipe (season_stats, 14.1) ; « adverse » : défense de l'adversaire
IDENTITES = (("pass_att", "pass_att"), ("comp", "comp"), ("pass_yds", "pass_yds"), ("pass_td", "pass_td"),
             ("ints", "ints"), ("rush_att", "rush_att"), ("rush_yds", "rush_yds"), ("rush_td", "rush_td"),
             ("rec", "comp"), ("rec_yds", "pass_yds"), ("rec_td", "pass_td"))
IDENTITES_ADVERSE = (("def_int", "ints"), ("sacks", "sacks_taken"))
REPLAY_GRAINES = 2                       # matchs rejoués par affiche pour le déterminisme (12 affiches)


# ---------------------------------------------------------------------------------------------------------------
# travailleur : un étage du moteur, dans son propre processus (les interrupteurs sont lus au chargement)
# ---------------------------------------------------------------------------------------------------------------
def _charger_saison(ns):
    """Cellule 14.1 (définitions seulement : season_stats, calendrier…) dans l'espace du notebook chargé."""
    nb = json.load(open(rc.NOTEBOOK, encoding="utf-8"))
    for c in nb["cells"]:
        src = "".join(c["source"])
        if c["cell_type"] == "code" and "14.1 — SAISON" in src[:400]:
            exec(compile(src, "<cellule 14.1>", "exec"), ns)
            return
    raise SystemExit("cellule 14.1 introuvable")


_RE_ADR = re.compile(r" at 0x[0-9a-f]+")
_RE_PLAY = re.compile(r"PLAY_\d+")      # compteur global d'identifiants d'événements (pas une donnée du match)


def signature(m):
    """Empreinte d'un match complet (journal, drives, stats, ledgers) — mêmes données = même empreinte."""
    s = json.dumps(m, default=str, sort_keys=True, ensure_ascii=False)
    s = _RE_PLAY.sub("PLAY", _RE_ADR.sub("", s))
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def alleger(m):
    """Garde ce qu'utilisent les rapports (rc._stats, decision_report, gameplan_report, franchise_style_metrics)."""
    log = [{k: v for k, v in e.items() if k not in ("event_ledger", "route_profile")} for e in m["play_log"]]
    return dict(m, play_log=log, event_ledgers=None)


def _champs_blocs(feed):
    """Présence des champs additifs de chaque bloc dans un GameFeed."""
    d = [p.get("decision") for p in feed["plays"] if p.get("decision")]
    roster = (feed["game"]["home"].get("roster") or []) + (feed["game"]["away"].get("roster") or [])
    return {"A": bool(d),
            "B": any("pocket_time" in x for x in d) and any(r.get("qb_iq") for r in roster),
            "C": any("reception" in x for x in d) and any(r.get("player_iq") for r in roster),
            "D": bool(feed["game"].get("gameplan")) and any("plan" in x for x in d),
            "E": all(r.get("progression") for r in roster)}


def _controler_match(ns, am, i, m, res):
    """Intégration : GameFeed, validate_gamefeed, audit action par action, identités de stats."""
    feed = ns["export_gamefeed"](m, game_id=f"v{i}", featured=False, season=1, week="R1")
    for pb in ns["validate_gamefeed"](feed, m):
        res["validate_gamefeed"].append(f"match {i} : {pb}")
    A = am.Audit()
    am.check_game(A, "validation", {"id": f"v{i}", "phase": "regular",
                                    "result": {"home": m["home_score"], "away": m["away_score"]}}, feed)
    for lvl, _w, _g, seq, msg in A.items:
        if any(msg.startswith(x) or x in msg for x in AUDIT_HORS_SEMAINE):
            res["audit_hors_semaine"] += 1
            continue
        res["audit"][lvl].append(f"match {i} action {seq} : {msg}")
    for k, v in _champs_blocs(feed).items():
        res["champs"][k] += v
    st = ns["season_stats"]([({"id": f"v{i}"}, m)])                  # {"teams", "players", "leaders"}
    T, P = st["teams"], st["players"]
    sides = (m["home_team"].abbreviation, m["away_team"].abbreviation)
    for ab in sides:
        opp = sides[1] if ab == sides[0] else sides[0]
        mine = [p for p in P if p["team"] == ab]
        theirs = [p for p in P if p["team"] == opp]
        for kp, kt in IDENTITES:
            res["identites"][kp][0] += 1
            if sum(p[kp] for p in mine) != T[ab][kt]:
                res["identites"][kp][1] += 1
                res["identites_ex"].append(f"match {i} {ab} {kp} : joueurs {sum(p[kp] for p in mine)} ≠ équipe {T[ab][kt]}")
        for kp, kt in IDENTITES_ADVERSE:
            res["identites"][kp][0] += 1
            if sum(p[kp] for p in theirs) != T[ab][kt]:
                res["identites"][kp][1] += 1
                res["identites_ex"].append(f"match {i} {ab} {kp} (défense adverse) : {sum(p[kp] for p in theirs)} ≠ {T[ab][kt]}")
        tg = sum(p["targets"] for p in mine)
        res["identites"]["targets<=pass_att"][0] += 1
        if tg > T[ab]["pass_att"]:
            res["identites"]["targets<=pass_att"][1] += 1
    return st


def _box(stats_matchs, n_matchs):
    """Stats d'équipe / de joueurs (repères) à partir des season_stats de chaque match."""
    eq = collections.defaultdict(lambda: collections.Counter())
    joueurs = collections.defaultdict(lambda: collections.Counter())
    pos = {}
    for st in stats_matchs:
        for ab, t in st["teams"].items():
            if t["games"]:
                eq[ab].update({k: v for k, v in t.items() if isinstance(v, (int, float))})
        for p in st["players"]:
            joueurs[p["id"]].update({k: v for k, v in p.items() if isinstance(v, (int, float)) and k != "games"})
            pos[p["id"]] = (p["team"], p["pos"])
    ligue = collections.Counter()
    for t in eq.values():
        ligue.update(t)
    tg = max(1, ligue["games"])                                          # matchs-équipe
    out = {"par_equipe_match": {k: ligue[k] / tg for k in ("pts", "yards", "pass_att", "comp", "pass_yds", "pass_td",
                                                          "ints", "sacks_taken", "rush_att", "rush_yds", "rush_td",
                                                          "fumbles_lost", "fg_att", "fg_made", "fourth_att")},
           "fg_pct": ligue["fg_made"] / max(1, ligue["fg_att"]),
           "fourth_conv": ligue["fourth_conv"] / max(1, ligue["fourth_att"]),
           "blitz_rate": ligue["blitz"] / max(1, ligue["def_snaps"]),
           "franchises": {ab: {"ppg": t["pts"] / max(1, t["games"]), "papg": t["pts_against"] / max(1, t["games"]),
                               "ypg": t["yards"] / max(1, t["games"]),
                               "pass_rate": (t["pass_att"] + t["sacks_taken"]) / max(1, t["plays"]),
                               "turnovers_pg": (t["ints"] + t["fumbles_lost"]) / max(1, t["games"])}
                          for ab, t in sorted(eq.items())}}
    # réceptions par poste (WR1, WR2, WR3, TE, RB) et défense créditée
    rec = collections.Counter()
    tot_rec = 0
    defense = collections.Counter()
    for pid, c in joueurs.items():
        role = pid.split("_", 1)[1]                                      # WR1, WR2, WR3 ; TE ; RB (RB1 + RB2) ; QB
        role = role.rstrip("0123456789") if role.startswith(("RB", "TE", "QB")) else role
        rec[role] += c["rec_yds"]
        tot_rec += c["rec_yds"]
        for k in ("tackles", "sacks", "def_int", "passes_defended", "forced_fumbles"):
            defense[k] += c[k]
    out["part_yards_reception"] = {r: v / max(1, tot_rec) for r, v in sorted(rec.items()) if v}
    out["defense_par_equipe_match"] = {k: v / tg for k, v in defense.items()}
    # leaders (par match joué par la franchise, chaque franchise joue n_matchs / 2 matchs)
    par_franchise = n_matchs / 2
    lead = {}
    for k in ("pass_yds", "rush_yds", "rec_yds", "tackles", "sacks", "def_int"):
        best = max(joueurs.items(), key=lambda kv: kv[1][k])
        lead[k] = {"id": best[0], "par_match": best[1][k] / par_franchise}
    out["leaders"] = lead
    return out


def _ngs(games):
    """Next Gen Stats / indicateurs fins tirés du journal (fonctionne aussi pour V21, sans décisions)."""
    c = collections.Counter()
    for g in games:
        log = g["play_log"]
        for i, e in enumerate(log):
            if e.get("kind") != "OFF":
                continue
            y, out = int(e["yards_gained"] or 0), e["outcome"]
            if e["play_type"] == "PASS" and out not in ("SACK",):
                c["att"] += 1
                c["expl_pass"] += out == "PASS_COMPLETE" and y >= 20
            elif e["play_type"] == "RUN":
                c["runs"] += 1
                c["expl_run"] += y >= 10
                c["stuff"] += y <= 0
            if e["down"] == 3:
                c["third"] += 1
                nxt = log[i + 1] if i + 1 < len(log) else None
                td = (e.get("run_summary") or {}).get("termination_cause") == "TOUCHDOWN"
                c["third_conv"] += td or (y >= e["distance"] and out not in ("INTERCEPTION", "FUMBLE")) or bool(
                    nxt and nxt.get("kind") == "OFF" and nxt["offense"] == e["offense"] and nxt["down"] == 1)
            if e["yard_line"] >= 80:
                c["rz_plays"] += 1
                c["rz_td"] += (e.get("run_summary") or {}).get("termination_cause") == "TOUCHDOWN"
    return {"explosive_pass_rate": c["expl_pass"] / max(1, c["att"]),       # passe complète de 20 yards et plus
            "explosive_run_rate": c["expl_run"] / max(1, c["runs"]),        # course de 10 yards et plus
            "stuffed_run_rate": c["stuff"] / max(1, c["runs"]),             # course arrêtée sans gain
            "third_down_conv": c["third_conv"] / max(1, c["third"]),
            "red_zone_td_per_play": c["rz_td"] / max(1, c["rz_plays"])}


def travailleur(nom, graines, semaines=0, graine_traj=GRAINE_TRAJECTOIRE_V26, traj_det=False, sortie=None,
                controles=True):
    import audit_moteur as am
    flags = ETAGES[nom.split("@")[0]]["flags"]
    t0 = time.time()
    ns, t_charge = rc.charger(decisions=flags[0], bloc_b=flags[1], bloc_c=flags[2], bloc_d=flags[3], bloc_e=flags[4])
    assert (ns.get("DECISIONS_ENABLED", False), bool(ns.get("QB_IQ_ENABLED")), bool(ns.get("PLAYER_IQ_ENABLED")),
            bool(ns.get("GAMEPLAN_ENABLED")), bool(ns.get("PROGRESSION_ENABLED"))) == flags, "interrupteurs inattendus"
    _charger_saison(ns)
    res = {"etage": nom, "flags": flags, "graines": graines, "semaines": semaines, "load_seconds": t_charge,
           "validate_gamefeed": [], "audit": {"BLOQUANT": [], "ALERTE": []}, "audit_hors_semaine": 0,
           "champs": collections.Counter(), "identites": collections.defaultdict(lambda: [0, 0]), "identites_ex": [],
           "determinisme": {}}
    # --- bloc E : trajectoire rejouée = même état (déterminisme), puis la trajectoire mesurée ---
    if semaines:
        if traj_det:
            etats = []
            for _ in range(2):
                ns["reset_franchises"]()
                ns["progression_trajectoire"](2, seed_base=graine_traj + 500_000)
                etats.append(json.dumps(ns["PROGRESSION"]["etat"], sort_keys=True, default=str))
            res["determinisme"]["trajectoire"] = etats[0] == etats[1]
            ns["reset_franchises"]()
        t = time.time()
        traj = ns["progression_trajectoire"](semaines, seed_base=graine_traj)
        res["progression"] = {"semaines": semaines, "graine": graine_traj, "secondes": time.time() - t,
                              "team_strength": traj[-1].get("team_strength"), "team_units": traj[-1]["team_units"],
                              "league_drift_max": max(r["league_drift_max"] for r in traj),
                              "team_guard_weeks": sum(bool(r["team_guard"]) for r in traj),
                              "units": {ab: dict(t.units) for ab, t in ns["AI_FRANCHISES"].items()}}
        etat = ns["PROGRESSION"]["etat"]
        J = etat["joueurs"]
        res["progression"]["controler"] = ns["DEV"].controler(etat)
        D = ns["DEV"]
        ovr = [D.ovr(D.notes_effectives(j)) - D.ovr(j["base"]) for j in J.values()]
        if ovr:
            res["progression"]["ovr_ecart"] = {"moyen": statistics.mean(ovr), "min": min(ovr), "max": max(ovr)}
    # --- les 1 008 matchs du test d'équilibre, contrôlés un par un ---
    teams = list(ns["AI_FRANCHISES"])
    games, temps, sigs, stats_matchs = [], [], [], []
    affiches = [(h, a) for h in teams for a in teams if h != a]
    for h, a in affiches:
        for s in range(graines):
            t = time.perf_counter()
            m = ns["franchise_game"](h, a, seed=50_000 + s)
            temps.append(time.perf_counter() - t)
            sigs.append(signature(m))
            if controles:
                stats_matchs.append(_controler_match(ns, am, len(games), m, res))
            games.append(alleger(m))
    # --- déterminisme : rejouer (dans l'ordre, puis à l'envers) ---
    rejeu = [(k, h, a, s) for k, (h, a) in enumerate(affiches) for s in range(min(REPLAY_GRAINES, graines))]
    diff = []
    for ordre in ("ordre", "envers"):
        for k, h, a, s in (rejeu if ordre == "ordre" else rejeu[::-1]):
            if signature(ns["franchise_game"](h, a, seed=50_000 + s)) != sigs[k * graines + s]:
                diff.append(f"{ordre} : {h}-{a} graine {50_000 + s}")
    res["determinisme"]["rejeu"] = {"matchs": 2 * len(rejeu), "differents": diff}
    # --- mesures ---
    rep = rc._stats(games, temps, ns)
    if flags[0]:
        rep["decision_stats"] = {k: v for k, v in ns["decision_report"](games).items() if k not in ("par_joueur", "par_couvreur")}
    if "gameplan_report" in ns:
        rep["gameplan"] = ns["gameplan_report"](games)
    res["mesures"] = rep
    res["ngs"] = _ngs(games)
    if flags[0]:
        s = rep["decision_stats"]
        res["ngs"].update({k: s.get(k) for k in ("taux_premiere_lecture", "taux_pression", "temps_lancer_moyen",
                                                 "temps_poche_moyen", "taux_erreur_lecture", "taux_bust")})
        n = rep["games"]
        res["ngs"]["scrambles_pg"] = s.get("scrambles", 0) / n
        res["ngs"]["throwaways_pg"] = s.get("throwaways", 0) / n
        res["ngs"]["cibles"] = {r: d["cibles"] / max(1, s["lancers"]) for r, d in s.get("par_role", {}).items()}
        if s.get("par_reception"):
            res["ngs"]["receptions"] = {k: {"part": v["part"], "completion": v["completion"]}
                                        for k, v in s["par_reception"].items()}
    if controles:
        res["box"] = _box(stats_matchs, len(games))
    res["signatures"] = sigs
    res["secondes"] = time.time() - t0
    res["champs"] = dict(res["champs"])
    res["identites"] = {k: v for k, v in res["identites"].items()}
    res["identites_ex"] = res["identites_ex"][:20]
    if sortie:
        with open(sortie, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, default=str)
    return res


# ---------------------------------------------------------------------------------------------------------------
# orchestrateur
# ---------------------------------------------------------------------------------------------------------------
def _lancer(taches, jobs, dossier):
    """Lance les travailleurs (sous-processus, au plus `jobs` à la fois) ; renvoie {nom: résultat}."""
    attente, actifs, fini = list(taches), {}, {}
    while attente or actifs:
        while attente and len(actifs) < jobs:
            nom, args, env_extra = attente.pop(0)
            out = os.path.join(dossier, f"{nom}.json")
            log = open(os.path.join(dossier, f"{nom}.log"), "w")
            env = {**os.environ, "PYTHONHASHSEED": "0", **env_extra}
            p = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--travailleur", *args, "--sortie-travailleur", out],
                                 stdout=log, stderr=subprocess.STDOUT, env=env, cwd=SERVEUR)
            actifs[nom] = (p, out, log, time.time())
            print(f"  … {nom} lancé", flush=True)
        time.sleep(2)
        for nom, (p, out, log, t) in list(actifs.items()):
            if p.poll() is not None:
                log.close()
                del actifs[nom]
                if p.returncode == 0 and os.path.exists(out):
                    fini[nom] = json.load(open(out, encoding="utf-8"))
                    print(f"  ✓ {nom} ({time.time() - t:.0f} s)", flush=True)
                else:
                    fini[nom] = {"erreur": open(log.name, encoding="utf-8").read()[-3000:]}
                    print(f"  ✗ {nom} : échec (code {p.returncode})", flush=True)
    return fini


def _egal(a, b, tol=1e-12):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_egal(a[k], b[k], tol) for k in a)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol
    return a == b


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--graines", type=int, default=None,
                    help="matchs par affiche et par terrain (défaut : 1 008 matchs — 84 à 4 équipes, 18 à 8)")
    ap.add_argument("--franchises", choices=("4", "8", "12", "16"), default="4",
                    help="taille de la ligue (GC_FRANCHISES). 4 : ligue de départ, non-régression exacte contre les "
                         "rapports publiés (V23 → V26) ; 8 : ligue de l'étape 6 (tolérances contre V21, équilibre)")
    ap.add_argument("--semaines", default="8,16,32,52", help="bloc E : semaines de progression enchaînées (trajectoire neuve)")
    ap.add_argument("--rapide", action="store_true", help="8 graines, 2 et 4 semaines (≈ 6 min) : vérifie l'outil")
    ap.add_argument("--jobs", type=int, default=max(1, min(3, (os.cpu_count() or 2) - 1)))
    ap.add_argument("--etages", default=",".join(ETAGES))
    ap.add_argument("--sortie", help="rapport JSON (sans les empreintes des matchs)")
    ap.add_argument("--travailleur", help=argparse.SUPPRESS)
    ap.add_argument("--graine-trajectoire", type=int, default=GRAINE_TRAJECTOIRE_V26, help=argparse.SUPPRESS)
    ap.add_argument("--traj-det", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--sans-controles", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--n-semaines", type=int, default=0, help=argparse.SUPPRESS)
    ap.add_argument("--sortie-travailleur", help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.travailleur:
        travailleur(a.travailleur, a.graines, a.n_semaines, a.graine_trajectoire, a.traj_det, a.sortie_travailleur,
                    controles=not a.sans_controles)
        return
    os.environ["GC_FRANCHISES"] = a.franchises          # hérité par les travailleurs
    n_aff = int(a.franchises) * (int(a.franchises) - 1)  # affiches (12 à 4 équipes, 56 à 8)
    defaut = 84 if a.franchises == "4" else 18
    if a.rapide:
        a.graines, a.semaines = (8 if a.franchises == "4" else 2), "2,4"
    a.graines = a.graines or defaut
    complet = a.graines == defaut
    publies = complet and a.franchises == "4"           # rapports publiés : ligue de départ seulement
    bloquants, rapport = [], {"programme": "ENGINE INTELLIGENCE — validation complète (fin de programme)",
                              "date": time.strftime("%Y-%m-%d"), "graines": a.graines, "franchises": int(a.franchises)}
    t0 = time.time()

    # 1. tests unitaires
    print("1. Tests unitaires des modules (moteur/tests)", flush=True)
    p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "moteur/tests", "-t", "."], cwd=SERVEUR,
                       capture_output=True, text=True)
    m = re.search(r"Ran (\d+) tests in ([\d.]+)s", p.stderr)
    par_bloc = {}
    for f in sorted(os.listdir(os.path.join(SERVEUR, "moteur", "tests"))):
        if f.startswith("test_") and f.endswith(".py"):
            par_bloc[f[:-3]] = len(re.findall(r"^\s+def test_", open(os.path.join(SERVEUR, "moteur", "tests", f),
                                                                     encoding="utf-8").read(), re.M))
    rapport["tests_unitaires"] = {"ok": p.returncode == 0, "tests": int(m.group(1)) if m else None,
                                  "secondes": float(m.group(2)) if m else None, "par_fichier": par_bloc}
    print(f"   {'✅' if p.returncode == 0 else '❌'} {rapport['tests_unitaires']['tests']} tests en "
          f"{rapport['tests_unitaires']['secondes']} s · " + " · ".join(f"{k[5:]} {v}" for k, v in par_bloc.items()))
    if p.returncode:
        bloquants.append("tests unitaires : " + p.stderr[-800:])

    # 2-6. étages, déterminisme inter-processus, semaines enchaînées
    etages = [e for e in a.etages.split(",") if e]
    semaines = [int(x) for x in a.semaines.split(",") if x]
    taches = [(e, [e, "--graines", str(a.graines)], {}) for e in etages]
    taches.append(("ABCDE_hash", ["ABCDE", "--graines", str(min(a.graines, 8)), "--sans-controles"],
                   {"PYTHONHASHSEED": "12345"}))
    if "ABCDE" in etages and publies:
        for cle, (n, g) in trajectoires_v26().items():
            taches.append((f"v26_{cle}", ["ABCDE", "--graines", str(a.graines), "--n-semaines", str(n), "--sans-controles",
                                         "--graine-trajectoire", str(g)], {}))
    for k, n in enumerate(semaines):
        taches.append((f"E{n}", ["ABCDE", "--graines", str(a.graines), "--n-semaines", str(n),
                                 "--graine-trajectoire", str(GRAINE_TRAJECTOIRE_NEUVE)] + (["--traj-det"] if k == 0 else []), {}))
    print(f"2. {len(taches)} simulations ({a.graines * n_aff} matchs chacune, {a.jobs} en parallèle)", flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        R = _lancer(taches, a.jobs, tmp)
    for nom, r in R.items():
        if "erreur" in r:
            bloquants.append(f"{nom} : le travailleur a échoué\n{r['erreur']}")
    ref_v21 = json.load(open(os.path.join(HERE, "reference_v21.json"), encoding="utf-8"))

    # 2. intégration
    print("3. Intégration (GameFeed, audit action par action, stats joueurs = stats d'équipe, champs des blocs)")
    integ = {}
    for nom in etages + [f"E{n}" for n in semaines]:
        r = R.get(nom)
        if not r or "erreur" in r:
            continue
        n = r["mesures"]["games"]
        ident = {k: v[1] for k, v in r["identites"].items()}
        integ[nom] = {"matchs": n, "validate_gamefeed": len(r["validate_gamefeed"]),
                      "audit_bloquant": len(r["audit"]["BLOQUANT"]), "audit_alertes": len(r["audit"]["ALERTE"]),
                      "audit_hors_semaine_ignores": r["audit_hors_semaine"], "identites_fausses": ident,
                      "champs_blocs": r["champs"], "exemples": (r["validate_gamefeed"] + r["audit"]["BLOQUANT"]
                                                                + r["audit"]["ALERTE"] + r["identites_ex"])[:10]}
        attendus = dict(zip("ABCDE", r["flags"]))
        manque = [b for b, on in attendus.items() if on and r["champs"].get(b, 0) != n]
        en_trop = [b for b, on in attendus.items() if not on and r["champs"].get(b, 0)]
        ok = not (integ[nom]["validate_gamefeed"] or integ[nom]["audit_bloquant"] or any(ident.values()) or manque or en_trop)
        integ[nom]["ok"] = ok
        print(f"   {'✅' if ok else '❌'} {nom:6s} {n} matchs · validate_gamefeed {integ[nom]['validate_gamefeed']} · audit "
              f"{integ[nom]['audit_bloquant']} bloquant / {integ[nom]['audit_alertes']} alerte(s) · identités fausses "
              f"{sum(ident.values())} sur {sum(v[0] for v in r['identites'].values())} · champs "
              + " ".join(f"{b}{'✓' if r['champs'].get(b, 0) == n else ('·' if not r['champs'].get(b) else '½')}" for b in "ABCDE"))
        if not ok:
            bloquants.append(f"intégration {nom} : {integ[nom]}")
    rapport["integration"] = integ

    # 3. déterminisme
    print("4. Déterminisme")
    det = {}
    for nom, r in R.items():
        if "erreur" in r:
            continue
        d = r["determinisme"]["rejeu"]
        det[nom] = {"rejoues": d["matchs"], "differents": len(d["differents"])}
        if d["differents"]:
            bloquants.append(f"déterminisme {nom} : {d['differents'][:5]}")
        if "trajectoire" in r["determinisme"]:
            det[nom]["trajectoire_identique"] = r["determinisme"]["trajectoire"]
            if not r["determinisme"]["trajectoire"]:
                bloquants.append(f"déterminisme {nom} : trajectoire de progression rejouée différente")
    tot_rejeu = sum(v["rejoues"] for v in det.values())
    print(f"   {'✅' if not any(v['differents'] for v in det.values()) else '❌'} {tot_rejeu} matchs rejoués "
          f"(dans l'ordre et à l'envers, {len(det)} simulations) : "
          f"{sum(v['differents'] for v in det.values())} différent(s)")
    tr = [v.get("trajectoire_identique") for v in det.values() if "trajectoire_identique" in v]
    if tr:
        print(f"   {'✅' if all(tr) else '❌'} trajectoire de progression (2 semaines) rejouée : état identique")
    h0, h1 = R.get("ABCDE"), R.get("ABCDE_hash")
    if h0 and h1 and "erreur" not in h0 and "erreur" not in h1:
        k = len(h1["signatures"]) // n_aff
        idx = [i * a.graines + s for i in range(n_aff) for s in range(k)]
        same = all(h0["signatures"][j] == h1["signatures"][n] for n, j in enumerate(idx))
        det["inter_processus"] = {"matchs": len(idx), "identiques": same}
        print(f"   {'✅' if same else '❌'} autre processus (PYTHONHASHSEED différent) : {len(idx)} matchs identiques")
        if not same:
            bloquants.append("déterminisme : matchs différents d'un processus à l'autre")
    rapport["determinisme"] = det

    # 4. non-régression
    print("5. Non-régression")
    nonreg = {}
    for nom in etages:
        r, h = R.get(nom), ETAGES[nom].get("historique")
        if not r or "erreur" in r or not h or not publies:
            continue
        doc = json.load(open(os.path.join(HERE, h[0]), encoding="utf-8"))
        doc = doc["rapports"][h[1]] if h[1] else doc
        diff = {k: (doc.get(k), r["mesures"].get(k)) for k in MESURES_EXACTES
                if k in doc and not _egal(doc.get(k), r["mesures"].get(k))}
        nonreg[nom] = {"rapport": h[0] + (f" [{h[1]}]" if h[1] else ""), "identique": not diff, "differences": diff}
        print(f"   {'✅' if not diff else '❌'} {nom:6s} = {nonreg[nom]['rapport']} "
              + ("(toutes les mesures à l'identique)" if not diff else f"différences : {diff}"))
        if diff:
            bloquants.append(f"non-régression {nom} : {diff}")
    docs = json.load(open(os.path.join(HERE, "rapport_v26_bloc_e.json"), encoding="utf-8"))["rapports"]
    for cle, (n, g) in (trajectoires_v26().items() if publies else ()):
        r = R.get(f"v26_{cle}")
        if not r or "erreur" in r:
            continue
        doc = docs[cle]
        diff = {k: (doc.get(k), r["mesures"].get(k)) for k in MESURES_EXACTES if k in doc and not _egal(doc.get(k), r["mesures"].get(k))}
        nonreg[f"v26_{cle}"] = {"rapport": f"rapport_v26_bloc_e.json [{cle}]", "graine": g, "identique": not diff,
                                "differences": diff}
        print(f"   {'✅' if not diff else '❌'} {n} semaines de progression (trajectoire {g}) = rapport V26 [{cle}] "
              + ("(à l'identique)" if not diff else f"différences : {diff}"))
        if diff:
            bloquants.append(f"non-régression {cle} : {diff}")
    if R.get("ABCD") and R.get("ABCDE") and "erreur" not in R["ABCD"] and "erreur" not in R["ABCDE"]:
        same = R["ABCD"]["signatures"] == R["ABCDE"]["signatures"]
        nonreg["E_depart_egal_V25"] = same
        print(f"   {'✅' if same else '❌'} bloc E au départ = V25, match par match ({len(R['ABCD']['signatures'])} matchs)")
        if not same:
            bloquants.append("bloc E au départ ≠ V25")
    # calibration contre V21
    calib = {}
    print(f"   Calibration contre la référence V21 ({', '.join(f'{k} ±{v}' for k, v in list(rc.TOLERANCES.items())[:3])}…, équilibre 40-60 %) :")
    for nom in etages + [f"E{n}" for n in semaines]:
        r = R.get(nom)
        if not r or "erreur" in r:
            continue
        lignes, ok = rc.comparer(r["mesures"], ref_v21)
        tps = r["mesures"]["seconds_per_game"] / ref_v21["seconds_per_game"]
        hors = [l[0] for l in lignes if not l[5]]
        calib[nom] = {"ok": ok, "hors_tolerance": hors, "temps_x": tps,
                      **{k: r["mesures"][k] for k in rc.TOLERANCES}, "win_pct": r["mesures"]["win_pct"]}
        print(f"   {'✅' if ok else '❌'} {nom:6s} " + " · ".join(f"{k} {r['mesures'][k]:.3f}" for k in
                                                               ("completion_pct", "sack_rate", "int_rate", "ypa", "ypc",
                                                                "turnovers_pg", "points_pg"))
              + " · victoires " + " ".join(f"{ab} {w:.1%}" for ab, w in r["mesures"]["win_pct"].items())
              + f" · temps ×{tps:.2f}" + (f" · HORS : {hors}" if hors else ""))
        if not ok and complet:
            bloquants.append(f"calibration {nom} hors tolérance : {hors}")
    rapport["non_regression"] = nonreg
    rapport["calibration"] = calib

    # 5. stats joueurs / équipes, Next Gen Stats (repères)
    print("6. Stats joueurs / équipes et Next Gen Stats (repères, contre V21)")
    box = {}
    base = R.get("V21")
    for nom in etages + [f"E{n}" for n in semaines]:
        r = R.get(nom)
        if r and "erreur" not in r and r.get("box"):
            box[nom] = {"box": r["box"], "ngs": r["ngs"]}
    rapport["stats_et_ngs"] = box
    if base and "box" in base:
        b0 = base["box"]["par_equipe_match"]
        cle = ("pts", "yards", "pass_yds", "rush_yds", "ints", "sacks_taken", "fumbles_lost")
        print("   par équipe et par match : " + " | ".join(cle))
        for nom, d in box.items():
            print(f"   {nom:6s} " + " | ".join(f"{d['box']['par_equipe_match'][k]:.1f}" for k in cle)
                  + f" | 3e essais {d['ngs']['third_down_conv']:.1%} · passes 20+ {d['ngs']['explosive_pass_rate']:.1%}"
                  + f" · courses 10+ {d['ngs']['explosive_run_rate']:.1%}"
                  + (f" · lancer {d['ngs']['temps_lancer_moyen']:.2f} s · pression {d['ngs']['taux_pression']:.1%}"
                     f" · 1re lecture {d['ngs']['taux_premiere_lecture']:.1%}" if d["ngs"].get("temps_lancer_moyen") else ""))
        print("   yards à la réception par poste : " + " | ".join(
            f"{nom} " + " ".join(f"{p} {v:.0%}" for p, v in d["box"]["part_yards_reception"].items()) for nom, d in box.items()
            if nom in ("V21", "ABCDE", f"E{semaines[-1]}" if semaines else "")))
    # 6. semaines enchaînées
    print("7. Semaines enchaînées (bloc E, trajectoire neuve)")
    chaine = {}
    for n in semaines:
        r = R.get(f"E{n}")
        if not r or "erreur" in r:
            continue
        pg = r["progression"]
        chaine[n] = {"force": pg["team_strength"], "derive_ligue_max": pg["league_drift_max"],
                     "semaines_garde_fou": pg["team_guard_weeks"], "controler": pg["controler"],
                     "ovr_ecart": pg.get("ovr_ecart"), "secondes_trajectoire": pg["secondes"]}
        ok = not pg["controler"] and pg["league_drift_max"] <= 0.5 and all(
            abs(f) <= 0.2 + 0.005 for f in (pg["team_strength"] or {}).values())
        chaine[n]["ok"] = ok
        print(f"   {'✅' if ok else '❌'} {n:3d} semaines : force " + " ".join(f"{ab} {f:+.2f}" for ab, f in pg["team_strength"].items())
              + f" · dérive max {pg['league_drift_max']:.2f} · garde-fou d'équipe {pg['team_guard_weeks']} sem."
              + (f" · OVR (écart à la base) {pg['ovr_ecart']['min']:+.1f} à {pg['ovr_ecart']['max']:+.1f}" if pg.get("ovr_ecart") else "")
              + f" · victoires " + " ".join(f"{ab} {w:.1%}" for ab, w in r["mesures"]["win_pct"].items()))
        if not ok:
            bloquants.append(f"semaines enchaînées {n} : {chaine[n]}")
    rapport["semaines_enchainees"] = chaine
    rapport["bloquants"] = bloquants
    rapport["secondes"] = time.time() - t0
    if a.sortie:
        with open(a.sortie, "w", encoding="utf-8") as fh:
            json.dump(rapport, fh, ensure_ascii=False, indent=1, default=str)
    print(f"\nVERDICT : {'✅ validation complète réussie' if not bloquants else '❌ ' + str(len(bloquants)) + ' contrôle(s) bloquant(s)'}"
          f" ({time.time() - t0:.0f} s)")
    for b in bloquants:
        print("  -", b[:600])
    sys.exit(1 if bloquants else 0)


if __name__ == "__main__":
    main()
