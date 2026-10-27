"""Identité de jeu des franchises — refonte des playbooks, étape 2 (programme/Refonte_playbooks_fiches.md, validée par
Guillaume le 27/10/2026).

L'étape 1 a mesuré (outils/moteur/identite_playbooks.py) que les 24 franchises jouaient presque le même menu : 248 plays
dont 3 exclusifs, écart moyen à la ligue 0,062, 14 paires presque identiques. Ce module est la couche « identité »
posée sur les playbooks existants (12.2 bis → 12.2 decies) ; il ne crée aucune mécanique de jeu :

  - SYSTEMES : le système réel qui sert de repère à chaque franchise (Walsh, Leach, Shanahan…) ;
  - ATTAQUE : multiplicateurs de concepts et de formations sur le playbook de base. Le budget de chaque famille
    (course, passe) reste celui du coordinateur : on change CE QU'IL APPELLE, pas combien il passe ;
  - EXCLUSIFS : 4 à 6 plays par franchise (formation × concept existants) que personne d'autre n'appelle ;
  - SITUATIONS : la feuille d'appel propre à une franchise (zone rouge d'APX, 3e / 4e et court de GMB…) ;
  - MENU : franchise au menu resserré (PLS : tempo, peu de jeux répétés vite) ;
  - MOTION : part des snaps avec motion pour les franchises « motion » (AXM, CPH, MRG, PRM, TDL, APX…) ;
  - PERSONNEL_EQUIPE : ZPH joue ses formations spread en 10 personnel (4 WR : le WR4 du banc entre à la place du TE) ;
  - DEFENSE : poids des couvertures du coordinateur, blitz, paquets, jeux de rush et fronts propres à la franchise.

Pas d'effet de jeu nouveau (décision du 27/10) : ni bonus d'interception, ni adaptation renforcée, ni équipes
spéciales. Python pur, déterministe ; les tirages (motion) passent par moteur.aleatoire.flux dans leur propre flux.
Le notebook (cellule 12.2 vicies septies) branche ce module derrière l'interrupteur GC_IDENTITE (0 : moteur d'avant).
"""
from .aleatoire import flux

VERSION = "identite-1"
FLUX_MOTION = "id-motion"

# =====================================================================================================================
# 1. SYSTÈMES RÉELS (repères ; à terme, les coordinateurs imagineront les leurs)
# =====================================================================================================================
SYSTEMES = {
    "CTX": "Patriots de Bill Belichick : un plan de jeu par adversaire, aucune dominante fixe",
    "VEC": "Run and Shoot (Mouse Davis, June Jones) et « Greatest Show on Turf » de Mike Martz : spread vertical",
    "AEG": "Contrôle du ballon de Bill Parcells ; défense en match quarters de Nick Saban",
    "MNL": "Power-I de Nebraska et gap scheme de Greg Roman : sous le centre, 21 / 22 personnel",
    "AXM": "West Coast de Bill Walsh : timing, passes courtes, motion",
    "GLT": "Défense « 46 » de Buddy Ryan et blitz de Jim Johnson ; attaque d'écrans et de play-action",
    "CPH": "Pistol de Chris Ault et spread option d'Urban Meyer",
    "NVA": "Air Coryell (Don Coryell) et Bruce Arians : shots en play-action, max protect",
    "PLS": "Tempo de Chip Kelly (Oregon) : sans regroupement, petit menu répété vite",
    "ONX": "Tampa 2 de Tony Dungy et Monte Kiffin, Bears de Lovie Smith : défense qui chasse le ballon",
    "FRG": "Wisconsin : zone intérieure, duo, play-action depuis 12 personnel, pression intérieure",
    "MRD": "« Tresselball » de Jim Tressel : terrain, horloge, jeu sûr, Cover 2 / 3 qui plie",
    "APX": "Erhardt-Perkins en zone rouge (Patriots) : picks en bunch / stack, RPO, motion",
    "LTC": "RPO des Eagles 2017 (Doug Pederson, Frank Reich) : zone + lecture, bubble / tunnel",
    "ZPH": "Air Raid de Hal Mumme et Mike Leach : 4 receveurs, mesh, Y-cross, four verts",
    "BST": "Press man des Jets de Rex Ryan (Darrelle Revis) : homme, Cover 1 / 6, peu de blitz",
    "GRZ": "Défense des Ravens 2000 contre la course ; attaque à deux TE des Patriots 2011 (play-action, coutures)",
    "MRG": "Kyle Shanahan et Sean McVay : boot, jet, reverse, feintes",
    "GMB": "Eagles 2017 et Lions de Dan Campbell : le 4e essai joué",
    "PRM": "Chiefs d'Andy Reid : motions, shifts, formations hybrides",
    "SPK": "Oklahoma de Lincoln Riley : Air Raid jeune, verticales et jet sweeps",
    "CTD": "Colts de Peyton Manning et Tom Moore : peu de formations, timing, play-action classique",
    "TDL": "Broncos de Mike Shanahan : zone large et bootleg sur la même allure",
    "CMT": "« Beamer Ball » de Frank Beamer (Virginia Tech) : vitesse, trucs, équipes spéciales",
}

# =====================================================================================================================
# 2. ATTAQUE — multiplicateurs (concepts et formations) sur le playbook de base
# =====================================================================================================================
# concepts : clé = concept appelé (pb_concept) ; formations : clé = formation_id. Absent = 1.
# Les familles restent celles du coordinateur : les poids sont renormalisés à son budget course / passe.
_SPREAD = ("SHOTGUN", "TRIPS", "EMPTY", "GUN_QUADS", "GUN_TRIPS_OPEN", "GUN_STACK", "GUN_FLEX", "GUN_TRIPS_TIGHT")
_SOUS_CENTRE = ("I_FORM", "I_FORM_WING", "I_FORM_SLOT", "STRONG", "WEAK", "JUMBO", "HEAVY", "PISTOL_FULL_HOUSE")
_DEUX_TE = ("ACE", "SINGLEBACK_TIGHT", "SINGLEBACK_DEUCE", "SINGLEBACK_WING_PAIR", "SINGLEBACK_NASTY")


def _f(noms, k):
    return {n: k for n in noms}


ATTAQUE = {
    "CTX": {"concepts": {"READ_OPTION": 1.2, "Y_CROSS": 1.2, "LEVELS": 1.2},
            "formations": {"SHOTGUN": 0.8}},
    "VEC": {"concepts": {"DEEP_POST": 0.9, "FOUR_VERTS": 0.7, "CORNER": 0.85, "IN": 1.5, "DAGGER": 1.6, "SAIL": 1.4,
                         "CROSS": 1.3, "SWITCH_VERTICALS": 1.6, "DIVIDE": 1.4, "DEEP_CROSS": 1.4,
                         "DOUBLE_POST": 1.5, "PLAY_ACTION": 0.6, "BOOT": 0.5, "PA_FLOOD": 0.5, "PA_SLIDE": 0.5},
            "formations": {**_f(("TRIPS", "EMPTY", "GUN_QUADS", "GUN_TRIPS_OPEN", "GUN_STACK"), 1.6),
                           **_f(_DEUX_TE + _SOUS_CENTRE, 0.3)}},
    "AEG": {"concepts": {"INSIDE_RUN": 1.4, "TRAP": 1.8, "PA_SLIDE": 1.6, "CURL": 1.4, "LEVELS": 1.6, "DEEP_POST": 0.5,
                         "CORNER": 0.5, "FOUR_VERTS": 0.4, "DOUBLE_POST": 0.4, "DIVIDE": 0.4, "COUNTER": 0.8},
            "formations": {**_f(_DEUX_TE, 2.2), "SHOTGUN": 0.6, "EMPTY": 0.4, "TRIPS": 0.6}},
    "MNL": {"concepts": {"POWER": 1.3, "COUNTER": 1.2, "PIN_PULL": 1.6, "BUCK_SWEEP": 1.6, "POWER_TOSS": 1.4,
                         "INSIDE_RUN": 0.6, "TRAP": 0.6, "DRAW": 0.5, "PLAY_ACTION": 1.4, "BOOT": 1.3, "POP": 1.3},
            "formations": {**_f(_SOUS_CENTRE, 2.4), "SHOTGUN": 0.25, "TRIPS": 0.3, "EMPTY": 0.2, "PISTOL": 0.6,
                           "BUNCH": 0.4}},
    "AXM": {"concepts": {"STICK": 1.2, "SPOT_SNAG": 1.6, "PIVOT": 1.6, "CHOICE": 1.6, "CURL": 1.2, "DRAG": 1.2,
                         "Y_CROSS": 1.3, "DEEP_POST": 0.9, "CORNER": 0.9, "FOUR_VERTS": 0.8},
            "formations": {"BUNCH": 1.8, "SINGLEBACK_BUNCH": 2.0, "GUN_Y_OFF": 1.4, "SINGLEBACK_WING_PAIR": 1.3,
                           "SHOTGUN": 0.6}},
    "GLT": {"concepts": {"SCREEN": 2.0, "FL_SE_SCREEN": 4.0, "WR_TUNNEL_SCREEN": 3.0, "PLAY_ACTION": 1.8, "BOOT": 1.6,
                         "PA_FLOOD": 3.5, "PA_SLIDE": 2.0, "DRAW": 0.8, "QB_DRAW": 2.5, "STICK": 0.7, "QUICK_SLANT": 0.7},
            "formations": {"GUN_TIGHT": 2.0, "PISTOL": 1.5, "GUN_WING": 1.8}},
    "CPH": {"concepts": {"READ_OPTION": 1.3, "POWER_READ": 3.0, "INVERTED_VEER": 4.0, "MIDLINE_OPTION": 2.5,
                         "SPEED_OPTION": 3.0, "COUNTER": 0.6, "DRAW": 0.6, "SHOVEL_OPTION": 1.3, "TRIPLE_OPTION": 2.0, "RPO_INSIDE_ZONE": 1.8,
                         "RPO_READ": 1.8, "RPO_POWER": 1.6, "JET_ACTION": 2.0, "JET_SWEEP": 1.6, "QB_DRAW": 1.2},
            "formations": {"PISTOL": 2.2, "PISTOL_STRONG": 2.2, "PISTOL_WING": 2.2, "PISTOL_FULL_HOUSE": 1.5,
                           "SHOTGUN": 0.6, "TRIPS": 0.6}},
    "NVA": {"concepts": {"PLAY_ACTION": 1.6, "PA_FLOOD": 1.6, "PA_SLIDE": 1.4, "BOOT": 1.2, "DEEP_POST": 1.1,
                         "CORNER": 1.1, "DOUBLE_POST": 1.3, "FOUR_VERTS": 0.7, "SWITCH_VERTICALS": 0.5},
            "formations": {**_f(("ACE", "SINGLEBACK", "I_FORM", "I_FORM_WING", "SINGLEBACK_TIGHT", "SINGLEBACK_DEUCE",
                                 "STRONG", "I_FORM_SLOT"), 2.0),
                           "SHOTGUN": 0.6, "TRIPS": 0.5, "EMPTY": 0.5, "GUN_QUADS": 0.4}},
    "PLS": {"concepts": {"STICK": 1.3, "SHORT_OUT": 1.2, "HITCH": 1.5, "SCREEN": 1.3, "FL_SE_SCREEN": 1.5,
                         "RPO_ALERT": 2.0, "RPO_INSIDE_ZONE": 1.6, "RPO_READ": 1.5, "DEEP_POST": 0.7, "CORNER": 0.7},
            "formations": {**_f(("SHOTGUN", "TRIPS", "EMPTY", "GUN_TRIPS_OPEN", "GUN_TRIPS_TIGHT"), 1.5),
                           **_f(_DEUX_TE + _SOUS_CENTRE, 0.3)}},
    "ONX": {"concepts": {"SHORT_OUT": 1.8, "HITCH": 4.0, "STICK": 1.3, "SCREEN": 0.9, "WR_TUNNEL_SCREEN": 1.5,
                         "DRAW": 0.6, "CURL": 0.8, "POWER": 0.8, "COUNTER": 0.8,
                         "DART_QUICK_DIG": 5.0, "PIVOT": 4.0, "INSIDE_RUN": 0.6, "TRAP": 0.7, "DEEP_POST": 0.5, "CORNER": 0.5, "FOUR_VERTS": 0.4, "DOUBLE_POST": 0.4,
                         "SWITCH_VERTICALS": 0.4, "DIVIDE": 0.4, "CHAMP": 0.6},
            "formations": {"GUN_Y_OFF": 1.6, "GUN_FLEX": 1.4, "SINGLEBACK": 1.2, "PISTOL": 1.2}},
    "FRG": {"concepts": {"INSIDE_RUN": 1.5, "TRAP": 1.3, "WHAM": 2.0, "POWER": 0.6, "COUNTER": 0.9, "PA_SLIDE": 1.6,
                         "BOOT": 1.2, "PLAY_ACTION": 1.2},
            "formations": {**_f(_DEUX_TE, 2.2), "SINGLEBACK": 1.4, "SHOTGUN": 0.4, "TRIPS": 0.4, "EMPTY": 0.3,
                           "I_FORM": 0.6, "HEAVY": 0.7, "JUMBO": 0.6}},
    "MRD": {"concepts": {"SCREEN": 1.7, "FL_SE_SCREEN": 1.8, "CURL": 1.4, "HITCH": 1.0, "SHORT_OUT": 0.8, "DRAW": 1.5,
                         "INSIDE_RUN": 1.3, "OUTSIDE_RUN": 1.2, "STICK": 0.8,
                         "DEEP_POST": 0.5, "CORNER": 0.5, "FOUR_VERTS": 0.4, "DOUBLE_POST": 0.4, "DIVIDE": 0.4,
                         "SWITCH_VERTICALS": 0.4},
            "formations": {"PONY": 2.4, "PISTOL": 1.5, "SINGLEBACK_WING": 1.4, "SHOTGUN": 0.7}},
    "APX": {"concepts": {"MESH_WHEEL": 2.5, "SPOT_SNAG": 1.8, "RPO_POWER": 3.0, "RPO_READ": 2.0, "RPO_INSIDE_ZONE": 1.6,
                         "BOOT": 1.5, "PA_FLOOD": 1.8, "QB_DRAW": 1.8, "DRAW": 0.6},
            "formations": {"BUNCH": 1.5, "GUN_STACK": 1.8, "GUN_TRIPS_TIGHT": 1.4, "SINGLEBACK_BUNCH": 1.3}},
    "LTC": {"concepts": {"RPO_INSIDE_ZONE": 3.5, "RPO_OUTSIDE_ZONE": 3.5, "RPO_PEEK": 3.5, "RPO_READ": 3.5,
                         "RPO_ALERT": 2.5, "FL_SE_SCREEN": 1.8, "WR_TUNNEL_SCREEN": 1.8, "INSIDE_RUN": 0.6,
                         "OUTSIDE_RUN": 0.7, "DRAW": 0.6},
            "formations": {"GUN_TRIPS_OPEN": 2.0, "GUN_FLEX": 1.8, "EMPTY": 1.2, **_f(_DEUX_TE + _SOUS_CENTRE, 0.3)}},
    "ZPH": {"concepts": {"MESH": 1.6, "Y_CROSS": 2.0, "FOUR_VERTS": 1.3, "STICK": 1.2, "DAGGER": 1.4, "DRAG": 1.2,
                         "SAIL": 1.2, "PLAY_ACTION": 0.5, "BOOT": 0.4},
            "formations": {"EMPTY": 1.6, "GUN_QUADS": 2.4, "GUN_TRIPS_OPEN": 1.6, **_f(_DEUX_TE + _SOUS_CENTRE, 0.2)}},
    "BST": {"concepts": {"INSIDE_RUN": 1.3, "OUTSIDE_RUN": 1.8, "COUNTER": 1.2, "STICK": 1.4, "SHORT_OUT": 0.8,
                         "HITCH": 0.8, "CURL": 1.4, "SCREEN": 0.6,
                         "DEEP_POST": 0.6, "CORNER": 0.6, "FOUR_VERTS": 0.5, "DOUBLE_POST": 0.5, "DIVIDE": 0.5,
                         "SWITCH_VERTICALS": 0.5},
            "formations": {"ACE": 1.5, "SINGLEBACK_WING_PAIR": 1.6, "SINGLEBACK": 1.2, "GUN_Y_OFF": 1.3,
                           "SHOTGUN": 0.7}},
    "GRZ": {"concepts": {"BOOT": 1.4, "PLAY_ACTION": 1.8, "PA_SLIDE": 3.0, "PA_FLOOD": 2.0, "SAIL": 1.4,
                         "DEEP_CROSS": 3.0, "Y_CROSS": 3.0, "SALEM": 2.0, "DOUBLE_DIG": 2.0, "SCREEN": 0.6, "DRAW": 0.7},
            "formations": {**_f(_DEUX_TE, 1.8), "HEAVY": 1.4, "JUMBO": 1.3, "SHOTGUN": 0.6, "TRIPS": 0.6,
                           "EMPTY": 0.4}},
    "MRG": {"concepts": {"BOOT": 1.5, "PLAY_ACTION": 1.3, "PA_SLIDE": 1.4, "POP": 1.5, "REVERSE": 2.5,
                         "END_AROUND": 2.5, "DOUBLE_REVERSE": 2.5, "COUNTER_SWEEP": 2.0, "JET_ACTION": 2.0,
                         "JET_SWEEP": 1.5, "COUNTER": 1.1},
            "formations": {"SINGLEBACK_WING": 1.6, "PISTOL_WING": 1.6, "I_FORM_WING": 1.5, "WEAK": 1.4,
                           "SHOTGUN": 0.6}},
    "GMB": {"concepts": {"QUICK_SLANT": 1.5, "MESH": 2.0, "RPO_POWER": 3.0, "RPO_INSIDE_ZONE": 2.0, "WHAM": 2.0,
                         "DEEP_POST": 1.3, "CORNER": 1.3, "DOUBLE_POST": 2.0, "CHAMP": 1.4, "SPOT_SNAG": 1.6,
                         "DRAW": 0.6, "SCREEN": 0.6},
            "formations": {"BUNCH": 2.2, "GUN_TIGHT": 2.0, "GUN_TRIPS_TIGHT": 2.0, "SHOTGUN": 0.7}},
    "PRM": {"concepts": {"CHAMP": 1.8, "LEVELS": 2.0, "FLOOD": 2.0, "CHOICE": 2.0, "CROSS": 1.4, "JET_ACTION": 2.5,
                         "Y_CROSS": 1.6, "DRAW": 0.6, "COUNTER": 0.8},
            "formations": {"GUN_FLEX": 3.5, "GUN_Y_OFF": 3.5, "SINGLEBACK_BUNCH": 3.0, "GUN_WING": 3.0,
                           "I_FORM_SLOT": 2.5, "GUN_TRIPS_TIGHT": 2.0, "SHOTGUN": 0.3, "TRIPS": 0.4, "SINGLEBACK": 0.6}},
    "SPK": {"concepts": {"FOUR_VERTS": 1.8, "DAGGER": 1.6, "SWITCH_VERTICALS": 2.0, "DOUBLE_POST": 1.8, "DIVIDE": 1.8,
                         "JET_SWEEP": 2.0, "JET_ACTION": 1.8, "PLAY_ACTION": 0.7, "BOOT": 0.7, "SCREEN": 0.5,
                         "FL_SE_SCREEN": 0.5, "WR_TUNNEL_SCREEN": 0.5, "DRAW": 0.7},
            "formations": {"GUN_TRIPS_OPEN": 1.8, "GUN_WING": 1.5, "TRIPS": 1.2}},
    "CTD": {"concepts": {"PLAY_ACTION": 1.6, "PA_SLIDE": 1.3, "PA_FLOOD": 1.3, "CURL": 1.3, "LEVELS": 1.5,
                         "DOUBLE_DIG": 1.6, "SALEM": 1.0, "SCREEN": 0.7},
            "formations": {"SINGLEBACK": 1.6, "ACE": 1.6, "I_FORM": 1.5, "STRONG": 1.4, "SHOTGUN": 0.6,
                           "TRIPS": 0.6, "EMPTY": 0.5}},
    "TDL": {"concepts": {"OUTSIDE_RUN": 1.8, "PIN_PULL": 1.4, "BOOT": 1.5, "PA_FLOOD": 1.3, "PA_SLIDE": 1.3,
                         "JET_ACTION": 1.6, "DEEP_CROSS": 1.3, "DRAG": 1.2, "INSIDE_RUN": 0.7, "DRAW": 0.6,
                         "POWER": 0.7},
            "formations": {"SINGLEBACK_WING": 2.0, "PISTOL_WING": 1.8, "SINGLEBACK": 1.4, "I_FORM_WING": 1.6,
                           "WEAK": 1.3, "SHOTGUN": 0.4, "TRIPS": 0.5, "EMPTY": 0.4}},
    "CMT": {"concepts": {"SCREEN": 1.6, "FL_SE_SCREEN": 2.5, "WR_TUNNEL_SCREEN": 2.5, "JET_SWEEP": 2.5,
                         "REVERSE": 3.0, "END_AROUND": 3.0, "DOUBLE_REVERSE": 2.0, "COUNTER_SWEEP": 2.0,
                         "DEEP_POST": 0.6, "FOUR_VERTS": 0.6, "CORNER": 0.7, "DOUBLE_POST": 0.6},
            "formations": {"GUN_WING": 1.4, "BUNCH": 1.3}},
}

# =====================================================================================================================
# 3. PLAYS EXCLUSIFS — formation × concept, joués par une seule franchise
# =====================================================================================================================
# Un play qui n'existe pas encore est créé pour cette franchise ; un play de l'extension (moteur.playbook_expansion.PLAYS)
# qui existe déjà lui est RÉSERVÉ (les autres franchises le perdent ; sa part revient aux autres variantes du concept).
# Les plays de base, 12.2 bis et Roman (12.2 ter) restent à tout le monde.
EXCLUSIFS = {
    "CTX": {"CTX_GUN_FLEX_Y_CROSS": ("GUN_FLEX", "Y_CROSS"), "CTX_PISTOL_WING_RPO_PEEK": ("PISTOL_WING", "RPO_PEEK"),
            "CTX_SINGLEBACK_BUNCH_LEVELS": ("SINGLEBACK_BUNCH", "LEVELS"),
            "CTX_GUN_TRIPS_OPEN_SPOT": ("GUN_TRIPS_OPEN", "SPOT_SNAG")},
    "VEC": {"VEC_GUN_QUADS_SWITCH": ("GUN_QUADS", "SWITCH_VERTICALS"), "VEC_EMPTY_DIVIDE": ("EMPTY", "DIVIDE"),
            "VEC_TRIPS_DOUBLE_POST": ("TRIPS", "DOUBLE_POST"),
            "VEC_GUN_TRIPS_OPEN_DEEP_CROSS": ("GUN_TRIPS_OPEN", "DEEP_CROSS"),
            "VEC_GUN_STACK_FOUR_VERTS": ("GUN_STACK", "FOUR_VERTS")},
    "AEG": {"ACE_PA_SLIDE": ("ACE", "PA_SLIDE"), "AEG_SINGLEBACK_TIGHT_TRAP": ("SINGLEBACK_TIGHT", "TRAP"),
            "AEG_ACE_LEVELS": ("ACE", "LEVELS"), "AEG_SINGLEBACK_DEUCE_INSIDE_ZONE": ("SINGLEBACK_DEUCE", "INSIDE_RUN")},
    "MNL": {"MNL_JUMBO_POWER_TOSS": ("JUMBO", "POWER_TOSS"), "MNL_I_FORM_BUCK_SWEEP": ("I_FORM", "BUCK_SWEEP"),
            "MNL_PISTOL_FULL_HOUSE_PIN_PULL": ("PISTOL_FULL_HOUSE", "PIN_PULL"), "MNL_HEAVY_WHAM": ("HEAVY", "WHAM"),
            "MNL_I_FORM_WING_PLAY_ACTION": ("I_FORM_WING", "PLAY_ACTION")},
    "AXM": {"BUNCH_SPOT": ("BUNCH", "SPOT_SNAG"), "AXM_SINGLEBACK_BUNCH_DRAG": ("SINGLEBACK_BUNCH", "DRAG"),
            "AXM_GUN_Y_OFF_PIVOT": ("GUN_Y_OFF", "PIVOT"), "AXM_BUNCH_CHOICE": ("BUNCH", "CHOICE"),
            "AXM_SINGLEBACK_WING_PAIR_Y_CROSS": ("SINGLEBACK_WING_PAIR", "Y_CROSS")},
    "GLT": {"GLT_GUN_TIGHT_TUNNEL": ("GUN_TIGHT", "WR_TUNNEL_SCREEN"), "GLT_PISTOL_QB_DRAW": ("PISTOL", "QB_DRAW"),
            "GLT_SINGLEBACK_WR_SCREEN": ("SINGLEBACK", "FL_SE_SCREEN"), "GUN_WING_PA_FLOOD": ("GUN_WING", "PA_FLOOD")},
    "CPH": {"PISTOL_INVERTED_VEER": ("PISTOL", "INVERTED_VEER"), "PISTOL_WING_SPEED_OPTION": ("PISTOL_WING", "SPEED_OPTION"),
            "CPH_GUN_WING_MIDLINE": ("GUN_WING", "MIDLINE_OPTION"), "PISTOL_STRONG_POWER_READ": ("PISTOL_STRONG", "POWER_READ"),
            "CPH_PISTOL_TRIPLE": ("PISTOL", "TRIPLE_OPTION"),
            "CPH_PISTOL_FULL_HOUSE_SPEED_OPTION": ("PISTOL_FULL_HOUSE", "SPEED_OPTION")},
    "NVA": {"NVA_ACE_PA_FLOOD": ("ACE", "PA_FLOOD"), "NVA_I_FORM_DOUBLE_POST": ("I_FORM", "DOUBLE_POST"),
            "NVA_SINGLEBACK_PA_FLOOD": ("SINGLEBACK", "PA_FLOOD"), "NVA_ACE_DEEP_POST": ("ACE", "DEEP_POST"),
            "NVA_I_FORM_WING_CORNER": ("I_FORM_WING", "CORNER")},
    "PLS": {"PLS_GUN_TRIPS_OPEN_HITCH": ("GUN_TRIPS_OPEN", "HITCH"), "PLS_EMPTY_HITCH": ("EMPTY", "HITCH"),
            "PLS_GUN_TRIPS_TIGHT_WR_SCREEN": ("GUN_TRIPS_TIGHT", "FL_SE_SCREEN"),
            "PLS_SHOTGUN_RPO_ALERT": ("SHOTGUN", "RPO_ALERT")},
    "ONX": {"ONX_GUN_Y_OFF_SHORT_OUT": ("GUN_Y_OFF", "SHORT_OUT"), "ONX_SINGLEBACK_HITCH": ("SINGLEBACK", "HITCH"),
            "ONX_GUN_FLEX_TUNNEL": ("GUN_FLEX", "WR_TUNNEL_SCREEN"), "ONX_PISTOL_DART": ("PISTOL", "DART_QUICK_DIG")},
    "FRG": {"SINGLEBACK_NASTY_INSIDE_ZONE": ("SINGLEBACK_NASTY", "INSIDE_RUN"), "ACE_WHAM": ("ACE", "WHAM"),
            "FRG_SINGLEBACK_TIGHT_PA_SLIDE": ("SINGLEBACK_TIGHT", "PA_SLIDE"), "FRG_STRONG_TRAP": ("STRONG", "TRAP")},
    "MRD": {"MRD_PONY_WR_SCREEN": ("PONY", "FL_SE_SCREEN"), "MRD_PISTOL_CURL": ("PISTOL", "CURL"),
            "MRD_SINGLEBACK_WING_DRAW": ("SINGLEBACK_WING", "DRAW"), "MRD_SINGLEBACK_WING_HITCH": ("SINGLEBACK_WING", "HITCH")},
    "APX": {"APX_GUN_STACK_MESH_WHEEL": ("GUN_STACK", "MESH_WHEEL"), "APX_GUN_STACK_SPOT": ("GUN_STACK", "SPOT_SNAG"),
            "APX_GUN_STACK_RPO_POWER": ("GUN_STACK", "RPO_POWER"), "APX_PISTOL_STRONG_QB_DRAW": ("PISTOL_STRONG", "QB_DRAW"),
            "APX_BUNCH_PA_FLOOD": ("BUNCH", "PA_FLOOD")},
    "LTC": {"LTC_GUN_TRIPS_OPEN_RPO_INSIDE_ZONE": ("GUN_TRIPS_OPEN", "RPO_INSIDE_ZONE"),
            "LTC_GUN_FLEX_RPO_PEEK": ("GUN_FLEX", "RPO_PEEK"), "LTC_EMPTY_MESH": ("EMPTY", "MESH"),
            "LTC_SHOTGUN_RPO_OUTSIDE_ZONE": ("SHOTGUN", "RPO_OUTSIDE_ZONE"),
            "GUN_TRIPS_OPEN_TUNNEL": ("GUN_TRIPS_OPEN", "WR_TUNNEL_SCREEN")},
    "ZPH": {"ZPH_GUN_QUADS_MESH": ("GUN_QUADS", "MESH"), "ZPH_EMPTY_Y_CROSS": ("EMPTY", "Y_CROSS"),
            "ZPH_GUN_QUADS_FOUR_VERTS": ("GUN_QUADS", "FOUR_VERTS"), "ZPH_EMPTY_DAGGER": ("EMPTY", "DAGGER"),
            "ZPH_GUN_TRIPS_OPEN_DRAG": ("GUN_TRIPS_OPEN", "DRAG")},
    "BST": {"BST_SINGLEBACK_WING_PAIR_OUTSIDE_ZONE": ("SINGLEBACK_WING_PAIR", "OUTSIDE_RUN"),
            "BST_ACE_INSIDE_ZONE": ("ACE", "INSIDE_RUN"), "BST_GUN_Y_OFF_HITCH": ("GUN_Y_OFF", "HITCH"),
            "BST_SINGLEBACK_WING_PAIR_STICK": ("SINGLEBACK_WING_PAIR", "STICK")},
    "GRZ": {"GRZ_ACE_SAIL": ("ACE", "SAIL"), "GRZ_SINGLEBACK_DEUCE_BOOT": ("SINGLEBACK_DEUCE", "BOOT"),
            "GRZ_SINGLEBACK_DEUCE_Y_CROSS": ("SINGLEBACK_DEUCE", "Y_CROSS"),
            "GRZ_I_FORM_SLOT_PA_SLIDE": ("I_FORM_SLOT", "PA_SLIDE"), "GRZ_ACE_SALEM": ("ACE", "SALEM")},
    "MRG": {"MRG_I_FORM_DOUBLE_REVERSE": ("I_FORM", "DOUBLE_REVERSE"),
            "MRG_SINGLEBACK_WING_COUNTER_SWEEP": ("SINGLEBACK_WING", "COUNTER_SWEEP"), "MRG_ACE_POP": ("ACE", "POP"),
            "MRG_PISTOL_WING_END_AROUND": ("PISTOL_WING", "END_AROUND"), "MRG_WEAK_BOOT": ("WEAK", "BOOT")},
    "GMB": {"GMB_BUNCH_QUICK_SLANT": ("BUNCH", "QUICK_SLANT"), "GMB_GUN_TIGHT_RPO_POWER": ("GUN_TIGHT", "RPO_POWER"),
            "JUMBO_WHAM": ("JUMBO", "WHAM"), "GMB_GUN_TRIPS_TIGHT_MESH": ("GUN_TRIPS_TIGHT", "MESH")},
    "PRM": {"PRM_GUN_FLEX_CHAMP": ("GUN_FLEX", "CHAMP"), "GUN_Y_OFF_LEVELS": ("GUN_Y_OFF", "LEVELS"),
            "PRM_SINGLEBACK_BUNCH_FLOOD": ("SINGLEBACK_BUNCH", "FLOOD"), "PRM_GUN_WING_CROSS": ("GUN_WING", "CROSS"),
            "PRM_I_FORM_SLOT_CHOICE": ("I_FORM_SLOT", "CHOICE")},
    "SPK": {"SPK_GUN_TRIPS_OPEN_FOUR_VERTS": ("GUN_TRIPS_OPEN", "FOUR_VERTS"), "SPK_SHOTGUN_JET_SWEEP": ("SHOTGUN", "JET_SWEEP"),
            "SPK_GUN_TRIPS_OPEN_DAGGER": ("GUN_TRIPS_OPEN", "DAGGER"),
            "SPK_GUN_WING_SWITCH": ("GUN_WING", "SWITCH_VERTICALS")},
    "CTD": {"CTD_I_FORM_PA_SLIDE": ("I_FORM", "PA_SLIDE"), "CTD_ACE_DOUBLE_DIG": ("ACE", "DOUBLE_DIG"),
            "CTD_SINGLEBACK_LEVELS": ("SINGLEBACK", "LEVELS"), "STRONG_PA_FLOOD": ("STRONG", "PA_FLOOD"),
            "CTD_SINGLEBACK_SALEM": ("SINGLEBACK", "SALEM")},
    "TDL": {"TDL_SINGLEBACK_WING_OUTSIDE_ZONE": ("SINGLEBACK_WING", "OUTSIDE_RUN"), "TDL_PISTOL_WING_BOOT": ("PISTOL_WING", "BOOT"),
            "TDL_I_FORM_WING_JET_ACTION": ("I_FORM_WING", "JET_ACTION"),
            "TDL_SINGLEBACK_DEEP_CROSS": ("SINGLEBACK", "DEEP_CROSS"), "TDL_WEAK_OUTSIDE_ZONE": ("WEAK", "OUTSIDE_RUN")},
    "CMT": {"CMT_GUN_WING_REVERSE": ("GUN_WING", "REVERSE"), "TRIPS_WR_SCREEN": ("TRIPS", "FL_SE_SCREEN"),
            "CMT_SHOTGUN_END_AROUND": ("SHOTGUN", "END_AROUND"), "CMT_BUNCH_TUNNEL": ("BUNCH", "WR_TUNNEL_SCREEN")},
}
# parts à ajouter à moteur.playbook_expansion.PARTS (concepts qui n'avaient aucun budget chez leur franchise) :
# SALEM prend sur SAIL (12.2 ter), le double reverse de MRG sur OUTSIDE_RUN
PARTS_EN_PLUS = {"GRZ": {"SALEM": .40}, "CTD": {"SALEM": .40}, "MRG": {"DOUBLE_REVERSE": .06}}
EXCLUSIF_BONUS = 2.5         # poids d'un exclusif dans son concept (× la préférence de sa formation) : il se voit
PROPRIETAIRE = {pid: a for a, d in EXCLUSIFS.items() for pid in d}

# =====================================================================================================================
# 4. FEUILLE D'APPEL PROPRE À LA FRANCHISE — situations de 12.2 bis (short, long, red_zone, goal_line, backed_up,
#    first_down) : multiplicateurs en plus de ceux de la ligue (clé « @FORMATION » pour une formation)
# =====================================================================================================================
SITUATIONS = {
    "APX": {"red_zone": {"@GUN_STACK": 2.5, "@BUNCH": 2.2, "@GUN_TRIPS_TIGHT": 1.8, "@SINGLEBACK_BUNCH": 1.8,
                         "MESH_WHEEL": 2.0, "SPOT_SNAG": 2.0, "DRAG": 1.5, "RPO_POWER": 2.0, "RPO_READ": 1.6,
                         "QB_DRAW": 1.6, "PA_FLOOD": 1.5, "BOOT": 1.4},
            "goal_line": {"@GUN_STACK": 2.0, "@BUNCH": 2.0, "SPOT_SNAG": 1.8, "RPO_POWER": 2.0, "QB_DRAW": 1.5}},
    "GMB": {"short": {"@BUNCH": 2.2, "@GUN_TIGHT": 1.6, "QUICK_SLANT": 1.8, "MESH": 1.8, "RPO_POWER": 2.2, "POWER": 1.3,
                      "WHAM": 1.8},
            "long": {"DEEP_POST": 1.3, "CORNER": 1.3, "DOUBLE_POST": 1.4}},
    "MRD": {"first_down": {"INSIDE_RUN": 1.3, "DRAW": 1.2, "SCREEN": 1.3},
            "long": {"SCREEN": 1.6, "FL_SE_SCREEN": 1.6, "DRAW": 1.5, "DEEP_POST": 0.6, "FOUR_VERTS": 0.6}},
    "GLT": {"first_down": {"PLAY_ACTION": 1.4, "PA_FLOOD": 1.4, "DEEP_POST": 1.3, "CORNER": 1.3}},
    "NVA": {"first_down": {"PLAY_ACTION": 1.5, "PA_FLOOD": 1.5, "PA_SLIDE": 1.4, "DOUBLE_POST": 1.4}},
    "MNL": {"short": {"@JUMBO": 1.6, "@HEAVY": 1.6, "POWER": 1.4}, "goal_line": {"@JUMBO": 1.6, "POWER": 1.4}},
    "CTD": {"long": {"CURL": 1.4, "DOUBLE_DIG": 1.5, "LEVELS": 1.4, "SALEM": 1.4}},
    "ZPH": {"short": {"STICK": 1.6, "MESH": 1.5, "QUICK_SLANT": 1.4}},
}

# franchises au menu resserré : nombre de plays gardés par famille (les plus lourds du playbook de base)
MENU = {"PLS": {"RUN": 24, "PASS": 60}}

# =====================================================================================================================
# 5. MOTION — part des snaps avec motion (sur les plays de l'extension, où la motion existe), et type de motion
# =====================================================================================================================
MOTION = {
    "AXM": (0.45, {"ACROSS": .5, "RETURN": .3, "TRADE": .2}),
    "CPH": (0.45, {"JET": .5, "ORBIT": .5}),
    "MRG": (0.50, {"JET": .6, "ORBIT": .2, "TRADE": .2}),
    "PRM": (0.45, {"ACROSS": .3, "TRADE": .3, "JET": .2, "RETURN": .2}),
    "TDL": (0.35, {"JET": .7, "ORBIT": .3}),
    "APX": (0.35, {"ACROSS": .4, "JET": .3, "TRADE": .3}),
    "SPK": (0.20, {"JET": .7, "ACROSS": .3}),
    "CMT": (0.30, {"JET": .8, "ORBIT": .2}),
}

# =====================================================================================================================
# 6. PERSONNEL — ZPH en 10 personnel (4 WR) sur ses formations spread : le WR4 du banc prend la place du TE
# =====================================================================================================================
PERSONNEL_EQUIPE = {"ZPH": {f: "10" for f in ("SHOTGUN", "TRIPS", "GUN_QUADS", "GUN_TRIPS_OPEN", "GUN_STACK")}}

# =====================================================================================================================
# 7. DÉFENSE — couvertures du coordinateur (multiplicateurs), blitz, paquets, jeux de rush, fronts
# =====================================================================================================================
# couvertures : clés de coverage_weights (MAN, ZONE, COVER_2, COVER_4) et COVER_3 ; blitz : × blitz_rate
# paquets : {concept de base : {paquet : part}} remplace la ligne de PAQUETS_STYLE de la franchise
# rush : {jeu de rush : part} remplace RUSH_STYLE ; fronts : {front : part} met à jour FRONTS_STYLE
DEFENSE = {
    "AEG": {"couvertures": {"COVER_4": 1.6, "COVER_3": 1.3, "MAN": 0.4, "ZONE": 0.8}, "blitz": 0.8,
            "paquets": {"COVER_4": {"MATCH_QUARTERS": .45, "PALMS": .20, "COVER_6": .15},
                        "COVER_3": {"COVER_3_MATCH": .45, "COVER_3_SKY": .15}}},
    "NVA": {"couvertures": {"COVER_2": 1.6, "COVER_4": 1.4, "MAN": 0.4}, "blitz": 0.8,
            "paquets": {"COVER_2": {"TAMPA_2": .45, "COVER_2_SINK": .20},
                        "COVER_4": {"COVER_6": .30, "MATCH_QUARTERS": .20, "COVER_8": .15}}},
    "BST": {"couvertures": {"MAN": 3.5, "COVER_4": 0.8, "ZONE": 0.6}, "blitz": 0.7,
            "paquets": {"MAN": {"PRESS_MAN": .50, "COVER_2_MAN": .20, "COVER_1_ROBBER": .10},
                        "COVER_4": {"COVER_6": .40, "MATCH_QUARTERS": .20}}},
    "ONX": {"couvertures": {"MAN": 1.4, "COVER_2": 1.3},
            "paquets": {"MAN": {"COVER_1_ROBBER": .55, "PRESS_MAN": .10},
                        "COVER_3": {"COVER_3_BUZZ": .40, "COVER_3_SKY": .25, "SIM_PRESSURE": .10},
                        "ZONE": {"SIM_PRESSURE": .25, "CREEPER": .15, "MUG_DROP": .15, "COVER_3_BUZZ": .20},
                        "COVER_2": {"TAMPA_2": .50},
                        "BOX_STACK": {"BOX_ROBBER": .60}}},
    "MRD": {"couvertures": {"COVER_2": 1.6, "COVER_3": 1.4, "MAN": 0.4}, "blitz": 0.8,
            "paquets": {"COVER_2": {"COVER_2_SINK": .40, "TAMPA_2": .30}}},
    "GRZ": {"paquets": {"BOX_STACK": {"BOX_SKY": .30, "SPILL_PROTECTION": .35, "BOX_ROBBER": .15},
                        "BLITZ": {"SPILL_PROTECTION": .30, "FIRE_ZONE": .20, "A_GAP_BLITZ": .10, "EDGE_BLITZ": .10}},
            "fronts": {"BEAR": .45, "TITE": .45, "4_3_UNDER": .35, "SHORT_YARDAGE": .70}},
    "FRG": {"paquets": {"BOX_STACK": {"SPILL_PROTECTION": .30, "BOX_SKY": .25, "BOX_ROBBER": .20},
                        "BLITZ": {"SPILL_PROTECTION": .20, "A_GAP_BLITZ": .20, "B_GAP_BLITZ": .15, "MUG_BLITZ": .15,
                                  "FIRE_ZONE": .10}},
            "rush": {"INTERIOR_STUNT": .12, "INTERIOR_COLLAPSE": .18, "ET_STUNT": .08, "TEX_STUNT": .08,
                     "EDGE_RUSH": .06, "CONTAIN_RUSH": .02, "LONG_STUNT": .03}},
    "GLT": {"rush": {"ET_STUNT": .12, "TEX_STUNT": .12, "INTERIOR_STUNT": .08, "LONG_STUNT": .08, "CONTAIN_RUSH": .02,
                     "INTERIOR_COLLAPSE": .05, "EDGE_RUSH": .06}},
}

# =====================================================================================================================
# 8. FONCTIONS PURES (le notebook les appelle ; tests : moteur/tests/test_identite_franchises.py)
# =====================================================================================================================
def proprietaire(play_id):
    return PROPRIETAIRE.get(play_id)


def playbook(abbr, famille, plays):
    """Playbook d'identité. plays : [(play_id, concept, formation, poids de base)] d'une famille (RUN / PASS) tel que
    le moteur le construit (exclusifs de toutes les franchises compris). Renvoie [(play_id, poids)] :
      1. les exclusifs des autres franchises sont retirés ; la part de leur concept revient aux autres variantes du
         concept (rien ne se perd : un concept garde son poids) ;
      2. un exclusif de la franchise reçoit EXCLUSIF_BONUS fois le poids d'une variante ordinaire de son concept ;
      3. multiplicateurs de concepts et de formations de la franchise ;
      4. menu resserré (MENU) ;
      5. le total de la famille est ramené à celui d'entrée (budget du coordinateur)."""
    total = sum(w for *_, w in plays)
    if total <= 0:
        return [(p, w) for p, _, _, w in plays]
    par_concept = {}
    for p, c, f, w in plays:
        par_concept.setdefault(c, []).append((p, f, w))
    a = ATTAQUE.get(abbr, {})
    mc, mf = a.get("concepts", {}), a.get("formations", {})
    out = []
    for c in sorted(par_concept):
        vs = par_concept[c]
        tc = sum(w for _, _, w in vs)
        garde = [(p, f, w) for p, f, w in vs if PROPRIETAIRE.get(p, abbr) == abbr]
        if not garde:
            continue                                        # concept porté seulement par des exclusifs d'autres équipes
        ordinaires = [w for p, _, w in garde if p not in PROPRIETAIRE and w > 0]
        ref = (sum(ordinaires) / len(ordinaires)) if ordinaires else None
        poids = []
        for p, f, w in garde:
            if p in PROPRIETAIRE:
                w = (ref if ref is not None else max(w, 1e-9)) * EXCLUSIF_BONUS
            poids.append((p, f, w))
        tg = sum(w for _, _, w in poids)
        if tg <= 0:
            continue
        for p, f, w in poids:
            out.append((p, w * tc / tg * mc.get(c, 1.0) * mf.get(f, 1.0)))
    menu = MENU.get(abbr, {}).get(famille)
    if menu and len(out) > menu:
        garde = {p for p, _ in sorted(out, key=lambda x: (-x[1], x[0]))[:menu]}
        garde |= {p for p, _ in out if PROPRIETAIRE.get(p) == abbr}
        out = [(p, w) for p, w in out if p in garde]
    t = sum(w for _, w in out)
    if t <= 0:
        return [(p, w) for p, _, _, w in plays if PROPRIETAIRE.get(p, abbr) == abbr]
    return [(p, w * total / t) for p, w in out if w > 0]


def multiplicateur_situation(abbr, situations, concept, formation):
    """Multiplicateur de la feuille d'appel de la franchise pour un play, dans les situations du snap."""
    s = SITUATIONS.get(abbr)
    if not s:
        return 1.0
    k = 1.0
    for sit in situations:
        m = s.get(sit)
        if m:
            k *= m.get(concept, 1.0) * m.get("@" + formation, 1.0)
    return k


def motion(abbr, graine, n):
    """Motion de la franchise sur un play de l'extension qui n'en a pas (ou None), dans le flux « id-motion »."""
    d = MOTION.get(abbr)
    if not d:
        return None
    p, types = d
    rng = flux(FLUX_MOTION, graine, n)
    if rng.random() >= p:
        return None
    r = rng.random()
    for m, q in sorted(types.items()):
        r -= q
        if r < 0:
            return m
    return sorted(types)[-1]


def personnel(abbr, formation, defaut):
    return PERSONNEL_EQUIPE.get(abbr, {}).get(formation, defaut)


def couvertures(abbr, poids, blitz_rate):
    """(poids des couvertures, taux de blitz) du coordinateur défensif avec l'identité de la franchise."""
    d = DEFENSE.get(abbr)
    if not d:
        return poids, blitz_rate
    m = d.get("couvertures", {})
    out = dict(poids)
    moy = sum(out.values()) / max(1, len(out)) if out else 1.0
    for k, v in m.items():
        out[k] = out.get(k, moy) * v
    return out, blitz_rate * d.get("blitz", 1.0)


def appliquer_styles(paquets_style, rush_style, fronts_style):
    """Met à jour les styles défensifs de l'extension (dictionnaires de moteur.playbook_expansion), en place."""
    for a, d in DEFENSE.items():
        for concept, parts in d.get("paquets", {}).items():
            paquets_style.setdefault(a, {})[concept] = dict(parts)
        if d.get("rush"):
            rush_style[a] = dict(d["rush"])
        if d.get("fronts"):
            fronts_style.setdefault(a, {}).update(d["fronts"])


def controle(formations, concepts_connus, paquets, rush, fronts, franchises):
    """Erreurs de cohérence des tables (liste vide = tout est connu du moteur)."""
    err = []
    for a in list(ATTAQUE) + list(EXCLUSIFS) + list(SITUATIONS) + list(MOTION) + list(DEFENSE) + list(SYSTEMES):
        if a not in franchises:
            err.append(f"franchise inconnue : {a}")
    for a, d in ATTAQUE.items():
        err += [f"{a} : concept inconnu {c}" for c in d.get("concepts", {}) if c not in concepts_connus]
        err += [f"{a} : formation inconnue {f}" for f in d.get("formations", {}) if f not in formations]
    vus = {}
    for a, d in EXCLUSIFS.items():
        if not 4 <= len(d) <= 6:
            err.append(f"{a} : {len(d)} exclusifs (4 à 6)")
        for pid, (f, c) in d.items():
            if f not in formations:
                err.append(f"{a} : {pid} formation inconnue {f}")
            if c not in concepts_connus:
                err.append(f"{a} : {pid} concept inconnu {c}")
            if (f, c) in vus:
                err.append(f"{pid} : même combinaison que {vus[(f, c)]}")
            vus[(f, c)] = pid
    for a, s in SITUATIONS.items():
        for sit, m in s.items():
            if sit not in ("short", "long", "red_zone", "goal_line", "backed_up", "first_down"):
                err.append(f"{a} : situation inconnue {sit}")
            for k in m:
                if (k[1:] not in formations) if k.startswith("@") else (k not in concepts_connus):
                    err.append(f"{a} : {sit} clé inconnue {k}")
    for a, d in DEFENSE.items():
        for concept, parts in d.get("paquets", {}).items():
            err += [f"{a} : paquet inconnu {p}" for p in parts if p not in paquets]
            if sum(parts.values()) > 1 + 1e-9:
                err.append(f"{a} : parts de paquets {concept} > 1")
        err += [f"{a} : rush inconnu {r}" for r in d.get("rush", {}) if r not in rush]
        err += [f"{a} : front inconnu {f}" for f in d.get("fronts", {}) if f not in fronts]
    for a, d in PERSONNEL_EQUIPE.items():
        err += [f"{a} : formation inconnue {f}" for f in d if f not in formations]
    return err
