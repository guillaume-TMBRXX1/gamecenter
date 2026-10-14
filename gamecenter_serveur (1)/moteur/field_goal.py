"""Barème des field goals des franchises (partagé : moteur 12.2, fin de période, valeur des décisions — 14/10/2026).

Jusqu'à 60 yards : le barème du moteur (calculate_field_goal_probability, notebook 07), inchangé — 98 % jusqu'à 30,
92 % jusqu'à 40, 80 % jusqu'à 50, 65 % jusqu'à 60, ± 1 point par point d'équipes spéciales au-dessus / au-dessous de 75.
Au-delà, l'ancien barème donnait 45 % de 61 à 70 yards (≈ 50 % avec de bonnes équipes spéciales) et 15 % plus loin :
en fin de match, deux équipes à égalité tentaient des field goals de 63-64 yards l'une après l'autre (exhibition du
14/10). Désormais (repères NFL : les tentatives de 60 yards et plus réussissent à 35-45 %, presque toujours par les
meilleurs kickers ; le record est de 66 yards) : 40 % à 61 yards, puis − 6 points par yard, 2 % au-delà de 67 yards ; les
équipes spéciales comptent pour moitié à cette distance.
"""

VERSION = "fg-2"

LONG = {61: 0.40, 62: 0.34, 63: 0.28, 64: 0.22, 65: 0.16, 66: 0.10, 67: 0.05}
TRES_LONG = 0.02


def base(distance):
    if distance <= 30:
        return 0.98
    if distance <= 40:
        return 0.92
    if distance <= 50:
        return 0.80
    if distance <= 60:
        return 0.65
    return LONG.get(int(distance), TRES_LONG)


def probabilite(distance, special_teams_rating=75.0):
    """Probabilité de réussite d'un field goal de `distance` yards (équipes spéciales : 75 = neutre)."""
    mod = (special_teams_rating - 75) / 100
    if distance > 60:
        mod *= 0.5
    return round(max(0.01, min(0.99, base(distance) + mod)), 4)
