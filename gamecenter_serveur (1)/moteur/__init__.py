"""ENGINE INTELLIGENCE — modules de décision du moteur GridironSim (programme/Feuille_de_route.md, étape 5).

Modules indépendants du notebook (aucun import de ses classes : on échange des dict simples), importés par
NFL_Sim_GameCenter.ipynb et appelés par ses fonctions historiques derrière l'interrupteur DECISIONS_ENABLED.

Bloc A — état post-snap, progression du QB, cible réelle :
    progressions        cible primaire / secondaire / tertiaire / checkdown de chaque concept de passe
    reaction_defensive  DefensiveReactionEngine -> PostSnapState (couverture, statut de chaque receveur, pression)
    decision_qb         QBDecisionEngine -> QBDecision (lancer, throwaway, scramble, sack ; cible réelle)
    resolution          probabilités ajustées transmises au tirage historique, yards selon la cible
    stats               statistiques des décisions (par cible réelle, première lecture, pression…)
    aleatoire           flux aléatoires dédiés (graine du match + n° d'action)
"""
from .aleatoire import flux
from .progressions import progression
from .reaction_defensive import DefensiveReactionEngine, PostSnapState
from .decision_qb import QBDecisionEngine, QBDecision
from . import resolution, stats

VERSION = "bloc-A-1"
FLUX_DECISION = "decision-passe"

_REACTION = DefensiveReactionEngine()
_QB = QBDecisionEngine()


def decider_passe(concept, formation, concept_defensif, receveurs, defenseurs, qb, niveau_pression,
                  graine_match, numero_action):
    """Toute la chaîne du bloc A pour une passe, dans le flux dédié de cette action.

    Renvoie (lectures, etat_post_snap, decision).
    """
    rng = flux(FLUX_DECISION, graine_match, numero_action)
    lectures = progression(concept, formation, tuple(r for r in receveurs if receveurs[r]))
    etat = _REACTION.react(concept_defensif, lectures, receveurs, defenseurs, niveau_pression, rng)
    decision = _QB.decide(etat, lectures, qb, rng)
    return lectures, etat, decision
