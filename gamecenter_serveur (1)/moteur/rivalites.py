"""Rivalités, bilans des confrontations et mémoire (README section 88, 02/11/2026).

Douze rivalités officielles, une par franchise, dans sa division (décision de Guillaume) ; chacune a son trophée, détenu
par le vainqueur de la dernière confrontation décidée (un nul ne le fait pas changer de main). Pour n'importe quelle
affiche : bilan de toutes les confrontations terminées, série en cours, plus large victoire, cinq derniers résultats,
dernière confrontation et match « classique » (le plus serré, prolongation et playoffs d'abord, puis le plus de points).

Ne lit que les résultats des calendriers (week.json) : jamais un match pas encore terminé. Les matchs arrivent comme
moteur/insights.confrontations les donne : {id, week, kickoff, phase, home, away, hs, as, ot}.
"""
VERSION = "rivalites-1"

# (franchise, franchise, trophée) — noms en anglais, comme le site
RIVALITES = (
    ("MNL", "ZPH", "The Ground & Air Trophy"),
    ("AXM", "ONX", "The Talon"),
    ("MRG", "CTD", "The Mirage Cup"),
    ("VEC", "APX", "The Fang"),
    ("GRZ", "LTC", "The Den"),
    ("CPH", "MRD", "The Riddle"),
    ("CTX", "PRM", "The Masks"),
    ("FRG", "BST", "The Anvil"),
    ("PLS", "CMT", "Lightspeed"),
    ("AEG", "GLT", "The Firewall"),
    ("NVA", "SPK", "Starfall"),
    ("GMB", "TDL", "The Wager"),
)
_PAR_PAIRE = {frozenset((a, b)): t for a, b, t in RIVALITES}
_RIVAL = {**{a: b for a, b, _ in RIVALITES}, **{b: a for a, b, _ in RIVALITES}}
SERRE = 3          # un « classique » : 3 points d'écart au plus (ou une prolongation)
DERNIERS = 5


def rival(abbr):
    """Le rival attitré d'une franchise (ou None)."""
    return _RIVAL.get(abbr)


def trophee(a, b):
    """Le trophée de la rivalité a–b (ou None si ce n'est pas une rivalité)."""
    return _PAR_PAIRE.get(frozenset((a, b)))


def _vainqueur(m):
    return m["home"] if m["hs"] > m["as"] else m["away"] if m["as"] > m["hs"] else None


def _resume(m):
    return {"id": m["id"], "week": m["week"], "phase": m.get("phase"), "home": m["home"], "away": m["away"],
            "hs": m["hs"], "as": m["as"], "ot": bool(m.get("ot")), "winner": _vainqueur(m)}


def serie(matchs, a, b):
    """Bilan des confrontations a–b. matchs : les confrontations terminées (dans n'importe quel ordre)."""
    M = sorted((m for m in matchs if {m["home"], m["away"]} == {a, b}), key=lambda m: m["kickoff"], reverse=True)
    rec = {a: 0, b: 0, "ties": 0}
    for m in M:
        w = _vainqueur(m)
        rec[w if w else "ties"] += 1
    streak = None
    for m in M:                                     # du plus récent : victoires de suite de la même franchise
        w = _vainqueur(m)
        if w is None or (streak and w != streak["team"]):
            break
        streak = {"team": w, "n": streak["n"] + 1 if streak else 1}
    decide = [m for m in M if _vainqueur(m)]
    big = max(decide, key=lambda m: (abs(m["hs"] - m["as"]), m["kickoff"]), default=None)
    serres = [m for m in M if abs(m["hs"] - m["as"]) <= SERRE or m.get("ot")]
    classic = max(serres, key=lambda m: (bool(m.get("ot")), m.get("phase") not in (None, "regular"),
                                         -abs(m["hs"] - m["as"]), m["hs"] + m["as"], m["kickoff"]), default=None)
    t = trophee(a, b)
    out = {"a": a, "b": b, "games": len(M), "record": rec, "streak": streak if streak and streak["n"] >= 2 else None,
           "last": _resume(M[0]) if M else None, "recent": [_resume(m) for m in M[:DERNIERS]],
           "biggest": dict(_resume(big), margin=abs(big["hs"] - big["as"])) if big else None,
           "classic": _resume(classic) if classic else None,
           "rivalry": {"trophy": t, "holder": _vainqueur(decide[0]) if decide else None} if t else None}
    return out


def table():
    """Les 12 rivalités pour la page : [{a, b, trophy}]."""
    return [{"a": a, "b": b, "trophy": t} for a, b, t in RIVALITES]
