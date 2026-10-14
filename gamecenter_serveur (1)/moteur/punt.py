"""Punt avec retour (14/10/2026) : longueur du coup de pied, punt de précision, réception, retour.

Avant : punt de 35 à 55 yards (tirage uniforme), sans retour (« return_yards » tiré mais jamais utilisé) ; ballon au-delà
de la ligne de but : touchback aux 20.

Désormais (repères NFL 2019-2024 : ≈ 46-47 yards bruts, ≈ 41-42 nets, ≈ 40 % de punts retournés pour ≈ 9-10 yards,
≈ 30 % de fair catches, 7 % de touchbacks, ≈ 1 touchdown sur retour pour 200 à 250 punts) :
  coup de pied   : depuis la ligne de scrimmage ; LONGUEUR_MOYENNE yards (± puissance du punter), bruit gaussien ;
  précision      : près du terrain adverse (le punt normal irait dans l'en-but), le punter vise le coin et la ligne des
                   10 (CIBLE) : plus court, plus de ballons arrêtés par la couverture, de sorties et de fair catches, peu de
                   retours ; un rebond peut finir dans l'en-but (touchback) ;
  réception      : touchback (ballon dans l'en-but), fair catch, ballon arrêté par la couverture après rebond (« downed »),
                   sortie du terrain, ou retour ; le receveur évite d'attraper près de sa ligne de but (rebond) ;
  retour         : le retourneur (le plus rapide des WR2, WR3, RB2 : le même que sur les coups d'envoi) remonte en moyenne
                   RETOUR_MOYEN yards (± retourneur, ± équipes spéciales de l'équipe qui botte) ; parfois une grande
                   chevauchée (P_ECHAPPEE) ; au bout : touchdown sur retour (si permis : pas en prolongation).
Mesuré (200 000 punts depuis la ligne des 30, punter / retourneur / couverture moyens) : voir tests/test_punt.py.
Non modélisés (choix du 14/10/2026, comme pour les coups d'envoi) : punt contré, ballon échappé par le retourneur, fausse
formation de punt. Tirages dans un flux dédié (moteur/aleatoire.py).
"""
from moteur import aleatoire

VERSION = "punt-1"

TOUCHBACK = 20                # départ du receveur après un touchback
LONGUEUR_MOYENNE = 46.5       # yards bruts, punter moyen
LONGUEUR_PAR_POINT = 0.22     # + 0,22 yard par point de puissance au-dessus de PUISSANCE_MOYENNE
PUISSANCE_MOYENNE = 80
LONGUEUR_SIGMA = 5.0
LONGUEUR_BORNES = (25, 70)
CIBLE = 9                     # punt de précision : point de chute visé, chez le receveur (sa ligne des 9)
PRECISION_SIGMA = 4.5
MARGE_PRECISION = 6           # le punt normal tomberait à moins de 6 yards de la ligne de but : punt de précision
# punt normal : fair catch, sortie, ballon arrêté (le reste : retour) ; près de sa ligne, le receveur laisse rebondir
P_FAIR_CATCH = 0.37
P_SORTIE = 0.08
P_ARRETE = 0.05
PRES_LIGNE = 15               # réception à moins de 15 yards de sa ligne : on laisse rebondir plus souvent
P_ARRETE_PRES = 0.30
# punt de précision : ballon arrêté, sortie, fair catch, rebond dans l'en-but (le reste : retour)
PRECISION = {"downed": 0.36, "sortie": 0.18, "fair_catch": 0.26, "touchback": 0.10}
ROULE = (2, 9)                # un ballon qui rebondit roule encore de 2 à 9 yards
RETOUR_MOYEN = 8.4           # yards, retourneur et couverture moyens
RETOUR_PAR_POINT = 0.12       # + 0,12 yard par point d'avantage du retourneur (retourneur − couverture)
RETOUR_SIGMA = 6.0
RETOUR_MIN = -3
P_ECHAPPEE = 0.025            # une grande chevauchée : + 15 à 85 yards
ECHAPPEE = (15, 85)


def note_retourneur(vitesse, agilite):
    return round((vitesse + agilite) / 2, 1)


def punt(rng, ligne, puissance_punter=PUISSANCE_MOYENNE, retourneur=75.0, couverture=75.0, td_possible=True):
    """Un punt depuis `ligne` (repère de l'équipe qui botte, 1-99). rng : flux dédié. Renvoie un dict :

    longueur  : yards bruts ; chute : point de chute (repère de l'équipe qui botte, ≥ 100 : en-but)
    precision : punt de précision (terrain adverse) ; issue : "touchback" | "fair_catch" | "downed" | "sortie" | "retour"
    reception : où le receveur prend le ballon (son repère) ; retour : yards remontés (0 sans retour) ; td
    depart    : ligne de départ du receveur (son repère, 1-99) ; 100 sur un touchdown
    """
    normal = LONGUEUR_MOYENNE + (puissance_punter - PUISSANCE_MOYENNE) * LONGUEUR_PAR_POINT
    espace = 100 - ligne                                     # yards jusqu'à la ligne de but adverse
    precision = normal > espace - MARGE_PRECISION
    if precision:
        longueur = rng.gauss(espace - CIBLE, PRECISION_SIGMA)
    else:
        longueur = rng.gauss(normal, LONGUEUR_SIGMA)
    longueur = int(round(max(LONGUEUR_BORNES[0], min(LONGUEUR_BORNES[1], longueur))))
    chute = ligne + longueur
    base = {"version": VERSION, "longueur": longueur, "chute": chute, "precision": precision}

    def fin(issue, reception, retour=0, td=False):
        if issue == "touchback":
            return dict(base, issue=issue, reception=reception, retour=0, td=False, depart=TOUCHBACK)
        depart = 100 if td else max(1, min(99, reception + retour))
        return dict(base, issue=issue, reception=reception, retour=depart - reception if not td else 100 - reception,
                    td=td, depart=depart)

    reception = 100 - chute                                  # repère du receveur (≤ 0 : dans l'en-but)
    if reception <= 0:
        return fin("touchback", reception)
    u = rng.random()
    if precision:
        p = PRECISION
        if u < p["touchback"] * (1.0 if reception <= 6 else 0.4):
            return fin("touchback", reception)
        u = rng.random()
        if u < p["downed"]:
            roule = rng.randint(*ROULE)
            if reception - roule <= 0:
                return fin("touchback", reception)
            return fin("downed", reception - roule)
        if u < p["downed"] + p["sortie"]:
            return fin("sortie", max(1, reception - rng.randint(0, 3)))
        if u < p["downed"] + p["sortie"] + p["fair_catch"]:
            return fin("fair_catch", reception)
    else:
        arrete = P_ARRETE_PRES if reception < PRES_LIGNE else P_ARRETE
        if u < arrete:
            roule = rng.randint(*ROULE)
            if reception - roule <= 0:
                return fin("touchback", reception)
            return fin("downed", reception - roule)
        if u < arrete + P_SORTIE:
            return fin("sortie", max(1, reception - rng.randint(0, 4)))
        if u < arrete + P_SORTIE + P_FAIR_CATCH:
            return fin("fair_catch", reception)
    moyen = RETOUR_MOYEN + (retourneur - couverture) * RETOUR_PAR_POINT
    retour = max(RETOUR_MIN, rng.gauss(moyen, RETOUR_SIGMA))
    if rng.random() < P_ECHAPPEE:
        retour += rng.uniform(*ECHAPPEE)
    retour = int(round(retour))
    if reception + retour >= 100:
        if td_possible:
            return fin("retour", reception, 100 - reception, td=True)
        retour = 95 - reception                              # stoppé sur la fin (prolongation)
    return fin("retour", reception, retour)


def tirer(graine_match, numero_action, ligne, **kw):
    """punt() dans le flux dédié « punt|graine|n° d'action » (déterministe)."""
    return punt(aleatoire.flux("punt", graine_match, numero_action), ligne, **kw)
