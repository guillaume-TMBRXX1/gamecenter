"""Décision de fin de période : field goal maintenant ou continuer à jouer (fin du Q2 et du Q4).

Constat (V27, 240 matchs des franchises) : dans les dernières secondes du Q2 et du Q4, une équipe à portée de field goal
jouait presque toujours une course ou une passe (166 fois la dernière action du quart-temps, 4 field goals) : le moteur
ne regardait le field goal qu'au 4e essai, jamais l'horloge. Une course arrêtée à la ligne des 12 quand l'horloge tombe
à zéro ne rapporte rien.

Ce module ne pose pas de règle « s'il reste X secondes, tenter le field goal » : il COMPARE les options avec un petit
modèle du reste de la période, et choisit celle qui donne la meilleure valeur :
  - Q2 : points attendus (la mi-temps efface la possession) ;
  - Q4 : probabilité de victoire (écart final : gagné 1, égalité 0,5, perdu 0) — 3 points ne servent à rien à une équipe
    menée de 4, ils valent un match gagné à une équipe menée de 2.

État : quart-temps, secondes restantes, essai, distance à gagner, distance de l'en-but, écart au score, probabilité de
réussite du kicker (distance + notes des équipes spéciales : même fonction que le moteur), écart des unités (attaque
contre défense : chances de touchdown), temps morts (voir TEMPS_ENTRE_ACTIONS). Options :
  FG     : 3 points avec la probabilité du kicker ; l'action dure 3 à 6 s (la période s'arrête si l'horloge tombe à 0).
  JOUER  : une action (course ou passe du coordinateur) : touchdown, perte de balle, ou gain moyen de la zone ; elle
           dure TEMPS (distribution mesurée) ; ensuite la même décision se repose avec le temps qui reste — ou la
           période est finie. Au 4e essai sans touchdown ni premier essai : ballon rendu.
Une action commencée avant 0:00 va au bout (comme dans le moteur) : tant qu'il reste une seconde, on peut tirer.

Paramètres mesurés sur 160 matchs des franchises (V27) : temps par action, touchdown / perte de balle / gain moyen par
zone (5 yards) et par type d'action. Tout est déterministe (aucun tirage) : même état -> même décision.
"""
from functools import lru_cache

VERSION = "fin-de-periode-1"

FENETRE = 45                 # secondes : au-delà, la décision reste celle du coordinateur (temps pour plusieurs drives)
P_MIN = 0.30                 # en dessous, le kicker n'est pas « raisonnablement » à portée
DISTANCE_MAX = 64            # yards (le moteur : 45 % à 61-70 yards avant les notes)
MARGE = 0.01                 # le field goal doit être meilleur d'au moins ça (sinon : le coordinateur décide)
TEMPS_FG = (3, 6)            # durée d'un field goal (moteur : randint(3, 6))
TEMPS_ENTRE_ACTIONS = 0      # le moteur n'écoule pas l'horloge entre deux actions : les temps morts ne changent rien
                             # pour l'instant (paramètre gardé pour un futur modèle d'horloge, avec `temps_morts`)
PART_PASSE = 0.6             # mélange course / passe du coordinateur dans ces situations (mesuré : 0,55-0,65)
ARRET = 0.32                 # action sans gain (passe incomplète, sack, course bloquée) hors touchdown / perte de balle

# temps d'une action (secondes -> probabilité), mesuré
TEMPS = {1: .005, 2: .066, 3: .106, 4: .173, 5: .195, 6: .173, 7: .135, 8: .09, 9: .047, 10: .006, 11: .005}
# par zone de 5 yards (distance à l'en-but // 5, 8 = 40 yards et plus) : (touchdown, perte de balle, gain moyen)
ZONES = {
    "PASS": [(.549, .031, 1.0), (.458, .030, 2.9), (.308, .029, 5.3), (.169, .022, 6.3), (.079, .017, 6.5),
             (.035, .023, 7.2), (.016, .019, 6.1), (.010, .028, 7.0), (.0, .023, 6.7)],
    "RUN":  [(.628, .031, 1.3), (.437, .029, 4.2), (.169, .028, 5.8), (.034, .020, 6.3), (.010, .041, 6.3),
             (.004, .032, 6.2), (.0, .036, 6.1), (.0, .038, 6.0), (.0, .035, 6.3)],
}


def probabilite_fg(distance, special_teams_rating=75.0):
    """Même barème que calculate_field_goal_probability (notebook, 07) : distance + notes des équipes spéciales."""
    base = (0.98 if distance <= 30 else 0.92 if distance <= 40 else 0.80 if distance <= 50 else 0.65 if distance <= 60
            else 0.45 if distance <= 70 else 0.15)
    return round(max(0.01, min(0.99, base + (special_teams_rating - 75) / 100)), 4)


def _action(en_but, ecart_unites):
    """(touchdown, perte de balle, gain) d'une action du coordinateur à cette distance de l'en-but."""
    z = min(int(en_but) // 5, 8)
    k = max(0.7, min(1.3, 1 + 0.02 * ecart_unites))          # attaque contre défense : chances de touchdown
    td = to = g = 0.0
    for typ, part in (("PASS", PART_PASSE), ("RUN", 1 - PART_PASSE)):
        a, b, c = ZONES[typ][z]
        td += part * min(0.95, a * k)
        to += part * b
        g += part * c
    return td, to, g


def _utilite(quart, ecart, points):
    if quart == 2:
        return float(points)
    d = ecart + points
    return 1.0 if d > 0 else 0.5 if d == 0 else 0.0


@lru_cache(maxsize=200_000)
def _valeurs(quart, secondes, essai, a_gagner, en_but, ecart, st, ecart_unites):
    """(valeur du field goal ou None, valeur de jouer) — récursion sur le temps qui reste."""
    dist = en_but + 17
    p = probabilite_fg(dist, st)
    v_fg = None
    if dist <= DISTANCE_MAX and p >= P_MIN:
        v_fg = p * _utilite(quart, ecart, 3) + (1 - p) * _utilite(quart, ecart, 0)
    td, to, gain = _action(en_but, ecart_unites)
    reste = 1.0 - td - to
    v_td, v_rien = _utilite(quart, ecart, 7), _utilite(quart, ecart, 0)
    v = td * v_td + to * v_rien
    # sans touchdown ni perte de balle : action arrêtée (incomplète, sack, course bloquée : aucun gain) ou gain
    branches = ((ARRET, 0.0), (1 - ARRET, gain / (1 - ARRET)))
    for t, pt in TEMPS.items():
        s = secondes - t - TEMPS_ENTRE_ACTIONS
        for pb, g in branches:
            w = pt * reste * pb
            nouvel_en_but = max(1, int(round(en_but - g)))
            premier = g >= a_gagner
            if s <= 0 or (essai == 4 and not premier):
                v += w * v_rien            # la période se termine sur cette action, ou ballon rendu au 4e essai
            else:
                e2, ag2 = (1, min(10, nouvel_en_but)) if premier else (essai + 1, max(1, int(round(a_gagner - g))))
                v += w * meilleure(quart, s, e2, ag2, nouvel_en_but, ecart, st, ecart_unites)
    return v_fg, min(v, _utilite(quart, ecart, 7))


def meilleure(quart, secondes, essai, a_gagner, en_but, ecart, st, ecart_unites):
    v_fg, v_jouer = _valeurs(quart, secondes, essai, a_gagner, en_but, ecart, st, ecart_unites)
    return max(v_jouer, v_fg) if v_fg is not None else v_jouer


def decider(quart, secondes, essai, a_gagner, en_but, ecart, special_teams_rating=75.0, ecart_unites=0.0,
            temps_morts=3):
    """Décision de fin de période, ou None hors de la fenêtre (le coordinateur décide comme avant).

    quart      : 1-4 (5+ : prolongation, hors fenêtre)
    secondes   : secondes restantes dans le quart-temps
    essai      : 1-4 ; a_gagner : yards pour le premier essai ; en_but : yards jusqu'à l'en-but adverse
    ecart      : points de l'attaque − points de la défense
    special_teams_rating : notes des équipes spéciales de l'attaque (kicker) ; ecart_unites : attaque − défense
    temps_morts : temps morts de l'attaque (sans effet tant que TEMPS_ENTRE_ACTIONS = 0)
    Renvoie {"choix": "FG" | "JOUER", "fg": valeur, "jouer": valeur, "p_fg": …, "distance": …, "objectif", "raison"}.
    """
    if quart not in (2, 4) or secondes > FENETRE or secondes <= 0:
        return None
    en_but = max(1, int(round(en_but)))
    st = round(float(special_teams_rating), 1)
    eu = round(max(-15.0, min(15.0, float(ecart_unites))), 1)
    v_fg, v_jouer = _valeurs(quart, int(secondes), int(essai), max(1, int(round(a_gagner))), en_but, int(ecart), st, eu)
    dist = en_but + 17
    p = probabilite_fg(dist, st)
    objectif = "points attendus" if quart == 2 else "probabilité de victoire"
    if v_fg is None:
        choix, raison = "JOUER", f"field goal de {dist} yards hors de portée ({p:.0%})"
    elif v_fg > v_jouer + MARGE:
        choix = "FG"
        if quart == 4 and -3 <= ecart <= 0:
            raison = "3 points " + ("égalisent" if ecart == -3 else "donnent l'avantage")
        elif quart == 4 and ecart > 0:
            raison = "3 points mettent le match hors de portée" if ecart <= 5 else "prendre les points"
        else:
            raison = f"{secondes} s : pas le temps d'aller plus loin sans risque"
    else:
        choix = "JOUER"
        if quart == 4 and ecart <= -4:
            raison = "3 points ne suffisent pas : il faut un touchdown"
        elif quart == 4 and ecart > 0 and v_fg >= 0.999 and v_jouer >= 0.999:
            raison = "match déjà gagné : le coordinateur garde son appel"
        elif secondes <= max(TEMPS) and v_fg is not None:
            raison = f"à {en_but} yards de l'en-but, tenter le touchdown vaut plus que 3 points"
        else:
            raison = "il reste le temps de s'approcher"
    return {"version": VERSION, "choix": choix, "fg": None if v_fg is None else round(v_fg, 4),
            "jouer": round(v_jouer, 4), "p_fg": p, "distance": dist, "objectif": objectif, "raison": raison,
            "temps_morts": temps_morts}
