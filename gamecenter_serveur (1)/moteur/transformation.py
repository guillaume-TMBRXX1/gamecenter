"""Transformation après un touchdown : point après touchdown (1 point) ou transformation à 2 points (bloc 2, étape 3).

Avant (moteur V28) : un touchdown valait 7 points d'un coup, sans action. Désormais il vaut 6 points, puis l'attaque
tente une transformation, action à part (sans temps de jeu) :
  PAT  : coup de pied depuis la ligne des 15 (33 yards) ; ≈ 94 % de réussite, ± selon la précision du kicker.
  2PT  : une course ou une passe depuis la ligne des 2 ; ≈ 47 % de réussite, ± selon l'attaque contre la défense.

Le choix suit la règle classique des entraîneurs (tableau de l'écart au score APRÈS le touchdown) :
  - 4e quart-temps et prolongation : 2 points si mené de 2 (égaliser), de 5 (revenir à 3), de 9 (revenir à 7), de 12
    (revenir à 10) ; si l'avance est de 1 (passer à 3), de 4 ou 5 (passer à 6-7), de 12 (passer à 14) — tableau de
    Dick Vermeil, le plus utilisé ;
  - 3e quart-temps : le même tableau, seulement pour un coordinateur agressif (AGRESSIF_Q3) ;
  - en dehors du tableau, le point après touchdown ; un coordinateur agressif tente parfois les 2 points quand même
    (BASE_2PT × agressivité : les 2 points valent presque autant en moyenne).
  - Touchdown sur la dernière action du match (horloge à 0 au 4e quart-temps ou en prolongation) avec l'avance :
    pas de transformation, le match est joué (règle de la NFL).
L'agressivité du coordinateur vient de ses réglages du 4e essai (go_max_to_go, go_min_yard_line), de 0 à 1.

Cas rares non modélisés (choix du 11/10/2026) : coup de pied contré, transformation ratée ramenée par la défense dans
l'autre en-but (2 points pour la défense). Tirages dans un flux dédié (moteur/aleatoire.py, « transformation ») : le
hasard du moteur historique n'est pas consommé.
"""
from moteur import aleatoire

VERSION = "transformation-1"

P_PAT = 0.94                  # réussite du point après touchdown, kicker moyen (NFL : 94-95 %)
PRECISION_MOYENNE = 82        # précision moyenne des kickers des franchises
PAT_PAR_POINT = 0.004         # + 0,4 point de % par point de précision au-dessus de la moyenne
PAT_BORNES = (0.85, 0.99)
P_2PT = 0.47                  # réussite de la transformation à 2 points, attaque = défense (NFL : 45-50 %)
DEUX_PAR_POINT = 0.01         # + 1 point de % par point d'écart des unités (attaque − défense)
DEUX_BORNES = (0.30, 0.65)
PART_PASSE = 0.55             # transformation à 2 points : passe 55 %, course 45 %
BASE_2PT = 0.05               # hors tableau : 2 points tentés avec la probabilité BASE_2PT × agressivité
AGRESSIF_Q3 = 0.5             # à partir de cette agressivité, le tableau s'applique dès le 3e quart-temps
LIGNE_PAT = 15                # le coup de pied se tire de la ligne des 15 (ballon à 85 dans le repère de l'attaque)
LIGNE_2PT = 2                 # la transformation à 2 points se joue de la ligne des 2 (ballon à 98)

# écart au score APRÈS le touchdown (attaque − défense) -> 2 points, et ce que la tentative cherche
TABLEAU = {-2: "égaliser", -5: "revenir à 3 points", -9: "revenir à 7 points (un touchdown pour égaliser)",
           -12: "revenir à 10 points (touchdown + field goal)",
           1: "passer à 3 points d'avance", 4: "passer à 6 points d'avance", 5: "passer à 7 points d'avance",
           12: "passer à 14 points d'avance (deux touchdowns)"}


def agressivite(go_max_to_go, go_min_yard_line):
    """0 (prudent) à 1 (agressif) depuis les réglages du 4e essai du coordinateur offensif (franchises : 1-5, 30-62)."""
    a = ((go_max_to_go - 1) / 4 + (62 - go_min_yard_line) / 32) / 2
    return round(max(0.0, min(1.0, a)), 3)


def probabilite_pat(precision_kicker=PRECISION_MOYENNE):
    p = P_PAT + (precision_kicker - PRECISION_MOYENNE) * PAT_PAR_POINT
    return round(max(PAT_BORNES[0], min(PAT_BORNES[1], p)), 4)


def probabilite_2pt(ecart_unites=0.0):
    p = P_2PT + float(ecart_unites) * DEUX_PAR_POINT
    return round(max(DEUX_BORNES[0], min(DEUX_BORNES[1], p)), 4)


def decider(ecart_apres_td, quart, secondes, agressivite_oc=0.0, rng=None):
    """Choix de la transformation.

    ecart_apres_td : points de l'attaque − points de la défense, touchdown (6 points) compté
    quart          : 1-4 (5 et plus : prolongation) ; secondes : secondes restantes dans le quart-temps
    agressivite_oc : 0-1 (agressivite) ; rng : flux dédié (tirage « hors tableau »), None = jamais hors tableau
    Renvoie {"choix": "PAT" | "2PT" | None, "raison": …} — None : pas de transformation (match terminé et gagné).
    """
    fin = quart >= 4 and secondes <= 0
    if fin and ecart_apres_td > 0:
        return {"version": VERSION, "choix": None, "raison": "match terminé : la transformation ne change rien"}
    cible = TABLEAU.get(ecart_apres_td)
    if cible and (quart >= 4 or (quart == 3 and agressivite_oc >= AGRESSIF_Q3)):
        return {"version": VERSION, "choix": "2PT", "raison": cible}
    if rng is not None and rng.random() < BASE_2PT * agressivite_oc:
        return {"version": VERSION, "choix": "2PT", "raison": "coordinateur agressif"}
    return {"version": VERSION, "choix": "PAT", "raison": "point après touchdown"}


def resoudre(choix, rng, precision_kicker=PRECISION_MOYENNE, ecart_unites=0.0):
    """Résultat de la transformation choisie : {"reussie", "points", "p", "jeu": "KICK" | "RUN" | "PASS"}."""
    if choix == "PAT":
        p = probabilite_pat(precision_kicker)
        ok = rng.random() < p
        return {"reussie": ok, "points": 1 if ok else 0, "p": p, "jeu": "KICK"}
    if choix == "2PT":
        p = probabilite_2pt(ecart_unites)
        jeu = "PASS" if rng.random() < PART_PASSE else "RUN"
        ok = rng.random() < p
        return {"reussie": ok, "points": 2 if ok else 0, "p": p, "jeu": jeu}
    raise ValueError(f"choix inconnu : {choix!r}")


def transformation(ecart_apres_td, quart, secondes, graine_match, numero_action, agressivite_oc=0.0,
                   precision_kicker=PRECISION_MOYENNE, ecart_unites=0.0):
    """Décision + résultat, dans le flux dédié « transformation|graine|n° d'action » (déterministe).

    Renvoie None (pas de transformation) ou {"choix", "raison", "reussie", "points", "p", "jeu", "version"}.
    """
    rng = aleatoire.flux("transformation", graine_match, numero_action)
    d = decider(ecart_apres_td, quart, secondes, agressivite_oc, rng)
    if d["choix"] is None:
        return None
    return dict(d, **resoudre(d["choix"], rng, precision_kicker, ecart_unites))
