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

Bloc B — intelligence du QB, poche et pression :
    intelligence_qb     8 attributs (awareness, processing, coverage reading, decision making, pocket awareness,
                        pressure response, anticipation, aggressiveness), dérivés des notes et de l'identité
    decision_qb         QB avec qb["iq"] : chrono de poche, statut perçu (erreurs de lecture), style

Bloc C — intelligence des joueurs (receveurs et défenseurs) :
    intelligence_joueurs  6 attributs de receveur (route IQ, release, separation, zone / man recognition, catch in
                          traffic, contested catch) et 7 de défenseur (play recognition, zone IQ, man IQ, awareness,
                          reaction, discipline, pursuit) ; séparation post-snap, coverage bust, réception, yards après

Bloc D — adaptation en match et plan de jeu :
    plan_de_jeu         plan par adversaire (scouting : blitz, couvertures, mismatchs, fond, course / passe),
                        mémoire de tendances, AdaptiveGameplanEngine (quick game contre le blitz, protection,
                        bascule hors du double ; bracket, rotation du bracket, pression déguisée) ; plan d'une passe

Bloc E — progression des joueurs :
    developpement       notes de base / actuelle / forme, potentiel, rythme de développement, âge (une année = 4
                        semaines), expérience (bonus d'intelligence des blocs B et C) ; évolution par attribut ;
                        anti-inflation (moyenne par unité, plafonds, écart d'équipe borné) ; état persistant (JSON)
"""
from .aleatoire import flux
from .progressions import progression
from .reaction_defensive import DefensiveReactionEngine, PostSnapState
from .decision_qb import QBDecisionEngine, QBDecision
from . import resolution, stats, intelligence_qb, intelligence_joueurs, plan_de_jeu, developpement
from .intelligence_qb import attributs_qb
from .intelligence_joueurs import attributs_joueur
from .plan_de_jeu import plan_de_jeu as plan_de_jeu_adverse, AdaptiveGameplanEngine, MemoireTendances

VERSION = "bloc-E-1"
FLUX_DECISION = "decision-passe"
FLUX_JOUEURS = "joueurs-passe"           # bloc C : son propre flux (garde-fou 2)
FLUX_PLAN = "plan-de-jeu"                # bloc D : son propre flux (cible favorite lue en premier)

_REACTION = DefensiveReactionEngine()
_QB = QBDecisionEngine()


def decider_passe(concept, formation, concept_defensif, receveurs, defenseurs, qb, niveau_pression,
                  graine_match, numero_action, plan=None):
    """Toute la chaîne d'une passe, dans le flux dédié de cette action.

    qb avec "iq" (moteur.intelligence_qb.attributs_qb) -> décision du bloc B ; sans -> bloc A à l'identique.
    Receveurs avec "iq" (moteur.intelligence_joueurs.attributs_joueur, défenseurs aussi) -> bloc C : séparation selon
    l'intelligence des joueurs (flux à part : « joueurs-passe »), puis réception et yards après la réception.
    plan (moteur.plan_de_jeu.plan_passe) -> bloc D : progression ajustée (protection, receveur doublé évité, cible
    favorite ; flux à part « plan-de-jeu »), bracket et protection dans l'état post-snap ; None -> bloc C à l'identique.
    Renvoie (lectures, etat_post_snap, decision) ; avec un plan, decision.plan note ce qui a joué.
    """
    rng = flux(FLUX_DECISION, graine_match, numero_action)
    bloc_c = any((r or {}).get("iq") for r in receveurs.values())
    lectures = progression(concept, formation, tuple(r for r in receveurs if receveurs[r]),
                           bloc="B" if (qb or {}).get("iq") else "A")
    notes = {}
    if plan:
        lectures, notes = plan_de_jeu.appliquer_progression(lectures, plan, flux(FLUX_PLAN, graine_match, numero_action))
    etat = _REACTION.react(concept_defensif, lectures, receveurs, defenseurs, niveau_pression, rng,
                           **({"bruit": intelligence_joueurs.BRUIT_C, "echelle": intelligence_joueurs.ECHELLE_C} if bloc_c else {}),
                           **plan_de_jeu.options_reaction(plan))
    qui = None
    if bloc_c:
        qui = intelligence_joueurs.ajuster_post_snap(etat, lectures, receveurs, defenseurs, concept,
                                                     flux(FLUX_JOUEURS, graine_match, numero_action))
    decision = _QB.decide(etat, lectures, qb, rng)
    if bloc_c:
        _completer_bloc_c(decision, etat, receveurs, qui)
    if plan:
        decision.plan = dict(notes, **({"bracket": plan["bracket"], "bracketed": etat.double_sur == plan["bracket"]}
                                       if plan.get("bracket") else {}))
    return lectures, etat, decision


def _completer_bloc_c(decision, etat, receveurs, qui):
    """Réception (receveur contre défenseur responsable) et yards après la réception d'un ballon lancé."""
    decision.bloc = "C"
    if decision.action != "LANCER" or not decision.cible:
        return
    rec, d = receveurs.get(decision.cible) or {}, qui.get(decision.cible) or {}
    m_int, m_inc, kind = intelligence_joueurs.modificateurs_reception(rec, d, decision.statut, etat.famille)
    decision.mod_int = round(decision.mod_int * m_int, 4)
    decision.mod_inc = round(decision.mod_inc * m_inc, 4)
    decision.reception = kind
    decision.couvreur_id, decision.couvreur_nom = d.get("id", ""), d.get("name", "")
    decision.bust = bool(etat.receveurs[decision.cible].bust)
    decision.yards_c = round(intelligence_joueurs.yards_apres_reception(rec, d), 3)
