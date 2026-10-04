"""Statistiques des décisions de passe (bloc A), calculées depuis le play_log des matchs.

Chaque action de passe décidée porte entry["decision"] (écrit par le notebook, 12.2 quinquies) :
    {"action", "intended": {"role", "id", "name"}, "target": {...} | None, "read", "reads", "status",
     "pressure", "forced", "throw_time", "time_to_pressure", "coverage", "family", "rushers", "blitz", "double"}
"""

COMPLETE, INCOMPLETE, INT, SACKS = "PASS_COMPLETE", "PASS_INCOMPLETE", "INTERCEPTION", ("SACK", "FUMBLE")


def _ligne():
    return {"cibles": 0, "completes": 0, "incompletes": 0, "int": 0, "yards": 0}


def _compte(d, outcome, yards):
    d["cibles"] += 1
    if outcome == COMPLETE:
        d["completes"] += 1
        d["yards"] += yards
    elif outcome == INCOMPLETE:
        d["incompletes"] += 1
    elif outcome == INT:
        d["int"] += 1


def stats_decisions(play_logs):
    """Agrège les décisions d'une liste de play_log (un par match). Renvoie un dict sérialisable."""
    s = {"dropbacks": 0, "lancers": 0, "premiere_lecture": 0, "sous_pression": 0, "forcees": 0,
         "scrambles": 0, "throwaways": 0, "sacks_decision": 0, "sacks": 0, "temps_lancer": 0.0,
         "par_role": {}, "par_statut": {}, "par_couverture": {}, "par_lecture": {}, "par_joueur": {}}
    for log in play_logs:
        for e in log:
            d = e.get("decision")
            if not d:
                continue
            s["dropbacks"] += 1
            out = e.get("outcome")
            if out in SACKS and e.get("play_type") == "PASS":
                s["sacks"] += 1
            a = d["action"]
            if a == "SCRAMBLE":
                s["scrambles"] += 1
                continue
            if a == "THROWAWAY":
                s["throwaways"] += 1
                continue
            if a == "SACK":
                s["sacks_decision"] += 1
                continue
            s["lancers"] += 1
            s["temps_lancer"] += d.get("throw_time") or 0.0
            s["premiere_lecture"] += d.get("read") == 1
            s["sous_pression"] += bool(d.get("pressure"))
            s["forcees"] += bool(d.get("forced"))
            t = d.get("target") or {}
            y = int(e.get("yards_gained") or 0)
            if out in SACKS:
                continue                                  # lancer prévu, mais rattrapé (blitz)
            for cle, val in (("par_role", t.get("role")), ("par_statut", d.get("status")),
                             ("par_couverture", d.get("coverage")), ("par_lecture", d.get("read")),
                             ("par_joueur", t.get("id"))):
                _compte(s[cle].setdefault(str(val), _ligne()), out, y)
    n = max(1, s["lancers"])
    s["taux_premiere_lecture"] = s["premiere_lecture"] / n
    s["taux_pression"] = s["sous_pression"] / n
    s["temps_lancer_moyen"] = s["temps_lancer"] / n
    return s
