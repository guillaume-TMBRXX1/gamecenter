"""Coup d'envoi avec retour (bloc 2, étape 4) : longueur du coup de pied, touchback ou retour, yards du retour.

Avant (moteur V28) : coup d'envoi de la ligne des 25, 55 à 70 yards, sans retour (« return_yards = 0 ») ; après un
touchdown ou un field goal, pas de coup d'envoi du tout (l'adversaire repartait de ses 25).

Désormais (repères : NFL, mesuré sur ce moteur pour la position de départ) :
  coup de pied   : de la ligne des 35 de l'équipe qui botte ; LONGUEUR_MOYENNE yards (± puissance du kicker), bruit
                   gaussien ; point de chute repéré chez l'équipe qui botte (100 = ligne de but adverse, > 100 : dans
                   l'en-but) ;
  touchback      : ballon au-delà du fond de l'en-but, ou réception dans l'en-but et genou à terre (d'autant plus
                   souvent que le ballon tombe profond) ; départ à la ligne des 25 (TOUCHBACK) ;
  retour         : le receveur (le plus rapide des WR2, WR3, RB2 : vitesse et agilité) remonte en moyenne une
                   vingtaine de yards (± receveur, ± équipes spéciales de l'équipe qui botte) ; parfois une grande
                   chevauchée (P_ECHAPPEE) ; au bout du terrain : touchdown sur retour (si permis : pas sur les coups
                   d'envoi du début de match, de la mi-temps et de la prolongation).
Mesuré (200 000 coups d'envoi, kicker / receveur / couverture moyens) : 42 % de touchbacks, retour moyen 25 yards,
retours de 40 yards et plus 2,6 %, touchdowns 0,38 %, départ moyen 25,7 (avant : 25) — le calibrage du moteur ne bouge pas.
Non modélisés (choix du 12/10/2026) : onside kick, fumble sur retour. Tirages dans un flux dédié (moteur/aleatoire.py).
"""
from moteur import aleatoire

VERSION = "coup-envoi-1"

LIGNE_TIR = 35                # coup d'envoi de la ligne des 35 de l'équipe qui botte
TOUCHBACK = 25                # départ du receveur après un touchback
LONGUEUR_MOYENNE = 66.0       # yards, kicker moyen (point de chute moyen : 1 yard dans l'en-but)
LONGUEUR_PAR_POINT = 0.25     # + 0,25 yard par point de puissance au-dessus de PUISSANCE_MOYENNE
PUISSANCE_MOYENNE = 82
LONGUEUR_SIGMA = 4.5
LONGUEUR_BORNES = (45, 80)
FOND_EN_BUT = 10              # au-delà de 10 yards dans l'en-but : hors de l'en-but, touchback
GENOU = (0.40, 0.08)          # réception dans l'en-but : genou à terre avec 40 % + 8 % par yard de profondeur
RETOUR_MOYEN = 23.0           # yards, receveur et couverture moyens
RETOUR_PAR_POINT = 0.15       # + 0,15 yard par point d'avantage du receveur (receveur − couverture)
RETOUR_SIGMA = 6.5
P_ECHAPPEE = 0.04             # une grande chevauchée : + 20 à 85 yards
ECHAPPEE = (20, 85)
DEPART_MIN = 2                # un retour finit au plus près à la ligne des 2 (pas de safety sur coup d'envoi)


def note_receveur(vitesse, agilite):
    return round((vitesse + agilite) / 2, 1)


def coup_envoi(rng, puissance_kicker=PUISSANCE_MOYENNE, receveur=75.0, couverture=75.0, td_possible=True):
    """Un coup d'envoi. rng : flux dédié. Renvoie un dict :

    longueur  : yards du coup de pied ; chute : point de chute (repère de l'équipe qui botte, > 100 : en-but)
    touchback : True / False ; retour : yards remontés (0 sur touchback) ; td : touchdown sur retour
    depart    : ligne de départ du receveur (son repère, 1-99) ; 100 sur un touchdown
    reception : point de réception chez le receveur (≤ 0 : dans l'en-but)
    """
    longueur = rng.gauss(LONGUEUR_MOYENNE + (puissance_kicker - PUISSANCE_MOYENNE) * LONGUEUR_PAR_POINT, LONGUEUR_SIGMA)
    longueur = int(round(max(LONGUEUR_BORNES[0], min(LONGUEUR_BORNES[1], longueur))))
    chute = LIGNE_TIR + longueur
    reception = 100 - chute                                  # repère du receveur (négatif : dans l'en-but)
    profond = chute - 100
    if profond > FOND_EN_BUT or (profond >= 0 and rng.random() < min(0.95, GENOU[0] + GENOU[1] * profond)):
        return {"version": VERSION, "longueur": longueur, "chute": chute, "reception": reception, "touchback": True,
                "retour": 0, "td": False, "depart": TOUCHBACK}
    moyen = RETOUR_MOYEN + (receveur - couverture) * RETOUR_PAR_POINT
    retour = max(0.0, rng.gauss(moyen, RETOUR_SIGMA))
    if rng.random() < P_ECHAPPEE:
        retour += rng.uniform(*ECHAPPEE)
    retour = int(round(retour))
    depart = reception + retour
    td = depart >= 100
    if td and not td_possible:
        depart = 95                                          # stoppé sur la fin (coups d'envoi hors drive)
    if not td or not td_possible:
        depart = max(DEPART_MIN, min(99, depart))
        td = False
    else:
        depart = 100
    return {"version": VERSION, "longueur": longueur, "chute": chute, "reception": reception, "touchback": False,
            "retour": depart - reception, "td": td, "depart": depart}


def tirer(graine_match, numero_action, **kw):
    """coup_envoi() dans le flux dédié « coup-envoi|graine|n° d'action » (déterministe)."""
    return coup_envoi(aleatoire.flux("coup-envoi", graine_match, numero_action), **kw)
