"""Statistiques des décisions de passe (bloc A), calculées depuis le play_log des matchs.

Chaque action de passe décidée porte entry["decision"] (écrit par le notebook, 12.2 quinquies) :
    {"action", "intended": {"role", "id", "name"}, "target": {...} | None, "read", "reads", "status",
     "pressure", "forced", "throw_time", "time_to_pressure", "coverage", "family", "rushers", "blitz", "double"}
Bloc B (V23) ajoute : "qb": {"id", "name"}, "perceived", "misread", "hurried", "pocket_time" — d'où les stats par QB,
les erreurs de lecture et la part des interceptions / sacks qui viennent d'une décision (passe forcée ou mal lue,
ballon gardé trop longtemps).
Bloc C (V24) ajoute : "reception" (open / traffic / contested), "coverer": {"id", "name"} (défenseur responsable de la
cible), "bust" (cible oubliée par son défenseur), "busts" (rôles oubliés sur l'action) — d'où les réceptions par type,
les coverage busts et les stats par défenseur responsable (cibles, réceptions concédées, interceptions).
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
         "par_role": {}, "par_statut": {}, "par_couverture": {}, "par_lecture": {}, "par_joueur": {},
         "erreurs_lecture": 0, "presses": 0, "temps_poche": 0.0, "int": 0, "int_decision": 0, "par_qb": {},
         "par_reception": {}, "busts": 0, "busts_cible": 0, "par_couvreur": {}, "bloc_c": 0}
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
            s["busts"] += len(d.get("busts") or ())
            s["temps_poche"] += d.get("pocket_time") or d.get("time_to_pressure") or 0.0
            qid = (d.get("qb") or {}).get("id")
            if qid:
                q = s["par_qb"].setdefault(qid, {"name": d["qb"].get("name"), "dropbacks": 0, "lancers": 0,
                                                 "premiere_lecture": 0, "erreurs_lecture": 0, "presses": 0,
                                                 "sacks": 0, "sacks_decision": 0, "int": 0, "throwaways": 0,
                                                 "scrambles": 0, "temps_lancer": 0.0})
                q["dropbacks"] += 1
                q["sacks"] += out in SACKS and e.get("play_type") == "PASS"
                q["sacks_decision"] += a == "SACK"
                q["throwaways"] += a == "THROWAWAY"
                q["scrambles"] += a == "SCRAMBLE"
                if a == "LANCER":
                    q["lancers"] += 1
                    q["premiere_lecture"] += d.get("read") == 1
                    q["erreurs_lecture"] += bool(d.get("misread"))
                    q["presses"] += bool(d.get("hurried"))
                    q["int"] += out == INT
                    q["temps_lancer"] += d.get("throw_time") or 0.0
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
            s["erreurs_lecture"] += bool(d.get("misread"))
            s["presses"] += bool(d.get("hurried"))
            if out == INT:
                s["int"] += 1
                s["int_decision"] += bool(d.get("forced") or d.get("misread"))
            t = d.get("target") or {}
            y = int(e.get("yards_gained") or 0)
            if out in SACKS:
                continue                                  # lancer prévu, mais rattrapé (blitz)
            if d.get("reception"):
                s["bloc_c"] += 1
                s["busts_cible"] += bool(d.get("bust"))
                _compte(s["par_reception"].setdefault(d["reception"], _ligne()), out, y)
                cv = d.get("coverer") or {}
                if cv.get("id"):
                    _compte(s["par_couvreur"].setdefault(cv["id"], dict(_ligne(), name=cv.get("name"))), out, y)
            for cle, val in (("par_role", t.get("role")), ("par_statut", d.get("status")),
                             ("par_couverture", d.get("coverage")), ("par_lecture", d.get("read")),
                             ("par_joueur", t.get("id"))):
                _compte(s[cle].setdefault(str(val), _ligne()), out, y)
    n = max(1, s["lancers"])
    s["taux_premiere_lecture"] = s["premiere_lecture"] / n
    s["taux_pression"] = s["sous_pression"] / n
    s["temps_lancer_moyen"] = s["temps_lancer"] / n
    s["taux_erreur_lecture"] = s["erreurs_lecture"] / n
    s["temps_poche_moyen"] = s["temps_poche"] / max(1, s["dropbacks"])
    s["part_int_decision"] = s["int_decision"] / max(1, s["int"])
    s["part_sacks_decision"] = s["sacks_decision"] / max(1, s["sacks"])
    s["taux_bust"] = s["busts_cible"] / max(1, s["bloc_c"])
    for r in s["par_reception"].values():
        r["completion"] = r["completes"] / max(1, r["cibles"])
        r["part"] = r["cibles"] / max(1, s["bloc_c"])
    for q in s["par_qb"].values():
        k = max(1, q["lancers"])
        q["taux_premiere_lecture"] = q["premiere_lecture"] / k
        q["taux_erreur_lecture"] = q["erreurs_lecture"] / k
        q["temps_lancer_moyen"] = q["temps_lancer"] / k
        q["taux_sack"] = q["sacks"] / max(1, q["dropbacks"])
        q["taux_int"] = q["int"] / k
    return s
