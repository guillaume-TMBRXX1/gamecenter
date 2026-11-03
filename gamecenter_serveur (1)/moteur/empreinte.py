"""Empreinte de jeu d'une franchise (README section 89, 03/11/2026).

Ce qu'une franchise JOUE vraiment, sur ses derniers matchs terminés, en 8 axes (parts entre 0 et 1) :
  pass    part de passes parmi ses appels de course ou de passe (concept appelé ; un RPO donné est une course)
  power   courses en force (POWER, COUNTER, TRAP, WHAM, POWER_TOSS, BUCK_SWEEP) parmi ses courses
  motion  appels avec un homme en mouvement avant le snap
  pa      play-action et bootleg ;  rpo  RPO (donné ou lancé)
  go4     4es essais tentés (course ou passe) parmi ses 4es essais (punt et field goal compris)
  blitz   défense : appels BLITZ de ses défenses ;  man  défense : couverture homme à homme (MAN)
Genou et spike exclus. Mêmes familles que la mesure de l'identité (outils/moteur/identite_playbooks.py).

Fenêtre : les FENETRE derniers matchs terminés de la franchise depuis la semaine où les identités de jeu ont commencé ;
pas d'empreinte sous MIN_MATCHS matchs. La ligue (minimum, maximum, moyenne de chaque axe) se calcule sur les
franchises qui en ont une. Le serveur ne passe que des matchs terminés : jamais une action pas encore jouée.

Accès (décision de Guillaume) : la FORME du radar est publique, arrondie à PAS_FORME pour qu'on ne puisse pas en
retrouver les pourcentages ; les chiffres, la moyenne de la ligue, la comparaison de deux franchises et ce qui a changé
depuis la semaine dernière sont réservés aux comptes Insights.
"""
import collections

VERSION = "empreinte-1"
AXES = (("pass", "Pass / run"), ("power", "Power runs"), ("motion", "Motion"), ("pa", "Play-action"),
        ("rpo", "RPO"), ("go4", "4th-down tries"), ("blitz", "Blitz"), ("man", "Man coverage"))
CLES = tuple(k for k, _ in AXES)
FENETRE = 20                    # derniers matchs terminés d'une franchise (≈ une semaine)
MIN_MATCHS = 6                  # en dessous : pas encore d'empreinte
PAS_FORME = 0.1                 # forme publique : position sur chaque axe arrondie au dixième
SEUIL_CHANGE = 0.05             # « ce qui a changé » : 5 points de pourcentage au moins
MAX_CHANGES = 2

PLAY_ACTION = {"PLAY_ACTION", "BOOT", "PA_FLOOD", "PA_SLIDE", "POP"}
RPO_COURSE = {"RPO_ALERT", "RPO_INSIDE_ZONE", "RPO_OUTSIDE_ZONE", "RPO_PEEK", "RPO_POWER", "RPO_READ"}
RPO = RPO_COURSE | {c + "_THROW" for c in RPO_COURSE}
COURSES = {"INSIDE_RUN", "TRAP", "DRAW", "WHAM", "QB_DRAW", "POWER", "COUNTER", "PIN_PULL", "OUTSIDE_RUN", "BUCK_SWEEP",
           "COUNTER_SWEEP", "POWER_TOSS", "JET_SWEEP", "JET_ACTION", "END_AROUND", "REVERSE", "DOUBLE_REVERSE",
           "READ_OPTION", "POWER_READ", "INVERTED_VEER", "MIDLINE_OPTION", "SHOVEL_OPTION", "SPEED_OPTION",
           "TRIPLE_OPTION", "QB_SWEEP"} | RPO_COURSE
FORCE = {"POWER", "COUNTER", "TRAP", "WHAM", "POWER_TOSS", "BUCK_SWEEP"}       # courses « gap » : on tire, on cogne
EXCLUS = {"KNEEL", "SPIKE"}


def _vide():
    return {"snaps": 0, "pass": 0, "runs": 0, "power": 0, "motion": 0, "pa": 0, "rpo": 0, "q4": 0, "go4": 0,
            "dsnaps": 0, "blitz": 0, "man": 0}


def mesurer_match(feed, home, away):
    """Comptes bruts d'un match terminé, pour chaque franchise : {abbr: {snaps, pass, runs, power, …}}."""
    abbr = {"home": home, "away": away}
    M = {home: _vide(), away: _vide()}
    for p in feed.get("plays") or []:
        att = abbr.get(p.get("offense"))
        if not att:
            continue
        dfn = away if att == home else home
        c = p.get("call") or {}
        typ, k = c.get("type"), c.get("concept")
        if p.get("down") == 4 and typ in ("run", "pass", "punt", "field_goal"):
            M[att]["q4"] += 1
            M[att]["go4"] += typ in ("run", "pass") and k not in EXCLUS
        if typ not in ("run", "pass") or not k or k in EXCLUS:
            continue
        o = M[att]
        course = k in COURSES
        o["snaps"] += 1
        o["pass"] += not course
        o["runs"] += course
        o["power"] += k in FORCE
        o["motion"] += bool(c.get("motion"))
        o["pa"] += k in PLAY_ACTION
        o["rpo"] += k in RPO
        dd = (c.get("defense") or {}).get("concept")
        d = M[dfn]
        d["dsnaps"] += 1
        d["blitz"] += dd == "BLITZ"
        d["man"] += dd == "MAN"
    return M


def _part(a, b):
    return a / b if b else 0.0


def valeurs(matchs):
    """Les 8 axes sur une liste de comptes de matchs (ceux d'une franchise)."""
    s = collections.Counter()
    for m in matchs:
        s.update(m)
    return {"pass": _part(s["pass"], s["snaps"]), "power": _part(s["power"], s["runs"]),
            "motion": _part(s["motion"], s["snaps"]), "pa": _part(s["pa"], s["snaps"]),
            "rpo": _part(s["rpo"], s["snaps"]), "go4": _part(s["go4"], s["q4"]),
            "blitz": _part(s["blitz"], s["dsnaps"]), "man": _part(s["man"], s["dsnaps"])}


def calculer(par_equipe, fenetre=FENETRE, min_matchs=MIN_MATCHS):
    """par_equipe = {abbr: [comptes de ses matchs terminés, du plus récent au plus ancien]}.
    -> {"teams": {abbr: {"games", "values"|None}}, "league": {"min", "max", "avg"}|None}"""
    T = {}
    for t, ms in par_equipe.items():
        ms = ms[:fenetre]
        T[t] = {"games": len(ms), "values": valeurs(ms) if len(ms) >= min_matchs else None}
    ok = [v["values"] for v in T.values() if v["values"]]
    ligue = None
    if len(ok) >= 2:
        ligue = {f: {k: g([v[k] for v in ok]) for k in CLES}
                 for f, g in (("min", min), ("max", max), ("avg", lambda x: sum(x) / len(x)))}
    return {"teams": T, "league": ligue}


def position(ligue, k, v):
    """Place de v sur l'axe k : 0 = la franchise la plus basse de la ligue, 1 = la plus haute."""
    lo, hi = ligue["min"][k], ligue["max"][k]
    return 0.5 if hi <= lo else min(1.0, max(0.0, (v - lo) / (hi - lo)))


def forme(ligue, vals):
    """La forme publique du radar : 8 positions arrondies au dixième (aucun pourcentage)."""
    if not ligue or not vals:
        return None
    return [round(round(position(ligue, k, vals[k]) / PAS_FORME) * PAS_FORME, 1) for k in CLES]


def changements(avant, apres, seuil=SEUIL_CHANGE, n=MAX_CHANGES):
    """Ce qui a le plus changé entre deux empreintes (points de pourcentage) : [{axis, label, delta}]."""
    if not avant or not apres:
        return []
    lib = dict(AXES)
    d = [(apres[k] - avant[k], k) for k in CLES if abs(apres[k] - avant[k]) >= seuil]
    d.sort(key=lambda x: (-abs(x[0]), x[1]))
    return [{"axis": k, "label": lib[k], "delta": round(x, 3)} for x, k in d[:n]]


def publique(res, t):
    """Ce que tout le monde reçoit pour la franchise t : sa forme seulement."""
    e = res["teams"].get(t) or {"games": 0, "values": None}
    return {"team": t, "games": e["games"], "shape": forme(res["league"], e["values"])}


def complete(res, t, avant=None):
    """Ce que reçoit un compte Insights : forme, chiffres, ligue, changements depuis la semaine dernière."""
    e = res["teams"].get(t) or {"games": 0, "values": None}
    out = publique(res, t)
    v = e["values"]
    out["values"] = {k: round(v[k], 4) for k in CLES} if v else None
    out["pos"] = [round(position(res["league"], k, v[k]), 4) for k in CLES] if v and res["league"] else None
    out["changes"] = changements((avant or {}).get("values"), v)
    return out


def ligue_publique(res):
    """La ligue pour un compte Insights : min, max, moyenne (arrondis) et position de la moyenne sur chaque axe."""
    L = res["league"]
    if not L:
        return None
    return {"min": {k: round(L["min"][k], 4) for k in CLES}, "max": {k: round(L["max"][k], 4) for k in CLES},
            "avg": {k: round(L["avg"][k], 4) for k in CLES},
            "avg_pos": [round(position(L, k, L["avg"][k]), 4) for k in CLES]}
