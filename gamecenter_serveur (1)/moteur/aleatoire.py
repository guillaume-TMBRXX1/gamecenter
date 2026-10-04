"""Flux aléatoires dédiés (garde-fou 2 du programme ENGINE INTELLIGENCE).

Chaque système tire dans SON propre flux, dérivé de la graine du match et du numéro d'action : le hasard
du moteur historique n'est jamais consommé par une décision (même principe que le placement latéral V18).
Même graine + même numéro d'action + même nom de système -> même suite de tirages, sur toute machine
(random.Random avec une graine str est déterministe d'une exécution à l'autre, quel que soit PYTHONHASHSEED).
"""
import random


def flux(systeme, graine_match, numero_action):
    """random.Random dédié à un système, pour une action d'un match.

    graine_match None (match sans graine) -> flux non reproductible, comme le reste du match.
    """
    if graine_match is None:
        return random.Random()
    return random.Random(f"{systeme}|{graine_match}|{numero_action}")


def gauss_borne(rng, sigma, borne):
    """Bruit gaussien centré, borné à ±borne (évite les queues extrêmes)."""
    return max(-borne, min(borne, rng.gauss(0.0, sigma)))
