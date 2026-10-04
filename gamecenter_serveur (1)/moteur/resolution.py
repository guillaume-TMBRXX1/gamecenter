"""Résolution « ajustée » (décision n° 2 du 04/10/2026).

La décision ne remplace pas la résolution historique : elle AJUSTE les probabilités que le notebook
transmet à son tirage (calculate_pass_outcome : interception / sack / incomplète / complète).
  - passe vers un receveur libre : moins d'incomplètes et d'interceptions ; serré / couvert / double : plus ;
  - passe lancée sous pression : un peu plus d'erreurs ; lancer tôt : presque plus de sack ;
  - throwaway : incomplète (sauf sack au moment du geste) ; fin de poche sans solution : sack le plus souvent ;
  - scramble : course du QB (yards tirés ici, avec le hasard du moteur).
Les facteurs CALIBRATION ramènent les taux moyens de la ligue sur ceux du moteur V21 (garde-fou 3) :
seule la RÉPARTITION des résultats entre les actions change, pas leur fréquence globale.
"""
from .decision_qb import LANCER, THROWAWAY, SCRAMBLE, SACK
from .reaction_defensive import LIBRE, SERRE, COUVERT, DOUBLE

M_INT = {LIBRE: 0.35, SERRE: 1.25, COUVERT: 3.2, DOUBLE: 3.8}
M_INC = {LIBRE: 0.62, SERRE: 1.40, COUVERT: 1.85, DOUBLE: 1.95}
PRESSION = {"int": 1.35, "inc": 1.15, "sack": 0.9}
SACK_LANCER_TOT = 0.25          # lancer avant la pression : il reste un petit risque de sack (rusher libre)
SACK_THROWAWAY = 0.5
SACK_FIN = 0.82                 # personne, pas de scramble ni de throwaway : sack (sinon passe jetée au sol)
INT_FIN = 0.5
SACK_SCRAMBLE = 0.12            # rattrapé en sortant de la poche

# normalisation (mesurée par outils/moteur/calibrer_bloc_a.py sur les passes de V21) : facteurs appliqués aux
# probabilités ajustées pour que la moyenne de la ligue reste celle du moteur historique
CALIBRATION = {"int": 1.42, "sack": 1.10, "inc": 0.96, "yards": 0.45}

# yards : profondeur de la cible réelle par rapport à la cible primaire (le concept a déjà son effet moyen)
PROFONDEUR = {"court": 0.0, "moyen": 3.0, "profond": 8.0}
PART_PROFONDEUR = 0.5
YARDS_STATUT = {LIBRE: 1.0, SERRE: -0.5, COUVERT: -1.0, DOUBLE: -1.5}


def probabilites_base(seuil_int, seuil_sack, seuil_inc):
    """Seuils cumulés du moteur historique -> probabilités {int, sack, inc, comp}."""
    p_int = max(0.0, seuil_int)
    p_sack = max(0.0, seuil_sack - max(0.0, seuil_int))
    p_inc = max(0.0, seuil_inc - max(seuil_sack, seuil_int, 0.0))
    return {"int": p_int, "sack": p_sack, "inc": p_inc, "comp": max(0.0, 1.0 - p_int - p_sack - p_inc)}


def _ferme(p_int, p_sack, p_inc):
    tot = p_int + p_sack + p_inc
    if tot > 0.97:                                      # jamais de résultat certain
        k = 0.97 / tot
        p_int, p_sack, p_inc = p_int * k, p_sack * k, p_inc * k
    return {"int": p_int, "sack": p_sack, "inc": p_inc, "comp": 1.0 - p_int - p_sack - p_inc}


def probabilites_ajustees(base, decision, calibration=CALIBRATION):
    """Probabilités transmises au tirage du moteur, selon la décision du QB (SCRAMBLE : voir yards_scramble)."""
    k = calibration
    if decision.action == LANCER:
        st = decision.statut or SERRE
        pr = decision.sous_pression
        p_int = base["int"] * M_INT[st] * (PRESSION["int"] if pr else 1.0) * k["int"]
        p_sack = base["sack"] * (PRESSION["sack"] if pr else SACK_LANCER_TOT) * k["sack"]
        p_inc = base["inc"] * M_INC[st] * (PRESSION["inc"] if pr else 1.0) * k["inc"]
        return _ferme(p_int, p_sack, p_inc)
    if decision.action == THROWAWAY:
        p_sack = min(0.9, base["sack"] * SACK_THROWAWAY * k["sack"])
        return {"int": 0.0, "sack": p_sack, "inc": 1.0 - p_sack, "comp": 0.0}
    if decision.action == SACK:
        p_sack = min(0.95, SACK_FIN * k["sack"])
        p_int = base["int"] * INT_FIN
        return {"int": p_int, "sack": p_sack, "inc": max(0.0, 1.0 - p_sack - p_int), "comp": 0.0}
    # SCRAMBLE : seul le sack en sortant de la poche passe par le tirage
    p_sack = SACK_SCRAMBLE * k["sack"]
    return {"int": 0.0, "sack": p_sack, "inc": 0.0, "comp": 0.0, "scramble": 1.0 - p_sack}


def seuils(probas):
    """Probabilités -> seuils cumulés (int, sack, inc) dans l'ordre du tirage historique."""
    a = probas["int"]
    b = a + probas["sack"]
    c = b + probas["inc"]
    return a, b, c


def ajustement_yards(decision, lectures, calibration=CALIBRATION):
    """Yards ajoutés à une passe complétée : profondeur de la cible réelle vs primaire, séparation."""
    if decision.action != LANCER or not lectures:
        return 0
    classe = {l["role"]: l["classe"] for l in lectures}
    d = (PROFONDEUR[classe.get(decision.cible, "court")] - PROFONDEUR[lectures[0]["classe"]]) * PART_PROFONDEUR
    d += YARDS_STATUT.get(decision.statut, 0.0) + calibration.get("yards", 0.0)
    return int(round(d))


def yards_scramble(rng, qb):
    """Course du QB qui sort de la poche (hasard du moteur : c'est la résolution)."""
    mob = float(((qb or {}).get("ratings") or {}).get("mobility", 70))
    r = rng.random()
    if r < 0.18:
        y = rng.randint(-1, 2)
    elif r < 0.62:
        y = rng.randint(3, 7)
    elif r < 0.90:
        y = rng.randint(8, 12)
    else:
        y = rng.randint(13, 24)
    return max(-2, y + int(round((mob - 75) / 10)))
