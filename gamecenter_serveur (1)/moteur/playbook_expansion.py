"""Extension du playbook V0.1 (programme/GRIDIRON_SIM_PLAYBOOK_EXPANSION_DATABASE_V0.1.md), branchée au moteur.

Ce module est le CATALOGUE de tout ce que la base de connaissances apporte et que le notebook n'avait pas encore :
formations (avec leur personnel et leurs modificateurs de structure), concepts de course, de passe, d'option et de
RPO, routes, motions et shifts, protections, paquets défensifs (couvertures, pressions, présentations), fronts et
mouvements de front, jeux de rush, relations entre concepts (enchaînements). Rien de ce qui existait déjà n'est
recréé : chaque nom de la base déjà présent dans le moteur (même sous un autre nom) est rangé dans ALIAS, avec ce
qui le porte aujourd'hui. Python pur (bibliothèque standard), comme le reste de moteur/.

Principes de la base respectés (§00, §38, §39) :
  - formation = contenant, concept = action ; PLAY CALL ≠ EXÉCUTION ≠ RÉSULTAT ;
  - la compatibilité est un FILTRE d'intégrité (compatibilite), pas une fréquence ;
  - les fréquences viennent du budget de chaque coordinateur : un nouveau concept prend une PART d'un concept existant
    de même nature (son « ancre », méthode du playbook Roman 2014, cellule 12.2 ter) ; l'identité des franchises et
    le mélange course / passe ne changent pas ;
  - rien n'est garanti : lectures d'option et de RPO, paquets défensifs, motion, front ne font que DÉPLACER des
    probabilités, chacun dans son flux aléatoire (moteur.aleatoire.flux) ; le hasard du moteur n'est pas consommé ;
  - présenté ≠ réel : la défense montre une coquille ou une pression (presented) et joue autre chose (paquet).

Le notebook (cellule 12.2 decies) enregistre plays et formations dans ses tables, puis appelle brancher() qui
inscrit routes, progressions, couvertures et familles de concepts dans les autres modules de moteur/. Sans brancher(),
les autres modules sont exactement ceux du bloc E (tests : moteur/tests/test_expansion.py).
"""
from .aleatoire import flux, gauss_borne

VERSION = "expansion-0.1"
FRANCHISES = ("CTX", "VEC", "AEG", "MNL", "AXM", "GLT", "CPH", "NVA",     # étape 6 : + franchises 05-08
              "PLS", "ONX", "FRG", "MRD")                               # palier 2 : + 09-12

# flux aléatoires dédiés (garde-fou 2) : un par système
FLUX = {"motion": "xp-motion", "shift": "xp-shift", "rpo": "xp-rpo", "option": "xp-option", "paquet": "xp-paquet",
        "front": "xp-front", "rush": "xp-rush", "mouvement": "xp-mouvement"}


# =====================================================================================================================
# 0. ALIAS — ce que la base nomme et que le moteur avait déjà (pas de doublon)
# =====================================================================================================================
ALIAS = {
    "formations": {
        "GUN": "SHOTGUN", "GUN_DOUBLES": "SHOTGUN (2x2 + TE, formation de base)", "DOUBLES": "SHOTGUN",
        "GUN_TRIPS": "TRIPS", "TRIPS": "TRIPS", "GUN_BUNCH": "BUNCH", "BUNCH": "BUNCH", "GUN_EMPTY": "EMPTY",
        "GUN_SPLIT": "PONY (deux halfbacks de part et d'autre du QB)", "SPLIT_BACK": "PONY", "SPLIT": "PONY",
        "SINGLEBACK_ACE": "ACE", "HEAVY": "HEAVY (tackle-over, V20) et JUMBO (2 TE + FB)",
        "CLOSE": "SINGLEBACK_NASTY (receveur resserré contre le TE)", "HIP": "GUN_Y_OFF (H-back sur la hanche du tackle)",
        "OFFSET": "STRONG / WEAK / PISTOL_STRONG (fullback décalé)", "FULL_HOUSE": "PISTOL_FULL_HOUSE",
        "SLOT": "I_FORM_SLOT (et le slot des formations shotgun)",
        # défense
        "4_2_5": "NICKEL", "ODD": "3_4", "3_4_ODD": "3_4", "OKIE": "3_4", "GOAL_LINE": "GOAL_LINE",
        "EVEN": "4_3_EVEN", "4_3": "4_3", "3_4": "3_4", "NICKEL": "NICKEL", "DIME": "DIME",
    },
    "concepts": {
        # courses
        "INSIDE_ZONE": "INSIDE_RUN (PISTOL_INSIDE_ZONE…)", "OUTSIDE_ZONE": "OUTSIDE_RUN", "WIDE_ZONE": "OUTSIDE_RUN",
        "STRETCH": "OUTSIDE_RUN", "SWEEP": "OUTSIDE_RUN", "SPLIT_ZONE": "PONY_92_SPLIT_ZONE (INSIDE_RUN)",
        "DUO": "I_FORM_91_DRILL (INSIDE_RUN)", "ISO": "I_FORM_ISO", "LEAD": "I_FORM_ISO", "BLAST": "I_FORM_90_BIG_BLAST",
        "GOAL_LINE_ISO": "I_FORM_ISO (feuille d'appel « goal_line »)", "GOAL_LINE_POWER": "POWER (« goal_line »)",
        "POWER": "POWER", "COUNTER": "COUNTER", "COUNTER_GT": "COUNTER", "COUNTER_GH": "COUNTER (HEAVY_95_WRAP)",
        "TRAP": "TRAP", "QB_POWER": "PISTOL_QB_POWER", "QB_SNEAK": "QB_SNEAK (OffensivePlayType)",
        "TOSS": "I_FORM_TOSS", "TOSS_LEAD": "I_FORM_TOSS", "TOSS_CRACK": "HEAVY_98_TRUCK", "JET_SWEEP": "JET_SWEEP",
        "DIVE": "JUMBO_DIVE", "HB_SLAM": "JUMBO_DIVE / I_FORM_90_BIG_BLAST", "HB_OFF_TACKLE": "POWER",
        "HB_DRAW": "DRAW", "SET_DRAW": "DRAW (SHOTGUN_HOUND_DRAW…)", "READ_OPTION": "READ_OPTION",
        # passes
        "SLANT": "QUICK_SLANT", "STICK": "STICK", "SPACING": "EMPTY_SPACING (STICK)", "BUBBLE_SCREEN": "SCREEN (bubble)",
        "HB_SLIP_SCREEN": "SCREEN (RB)", "SHALLOW_CROSS": "DRAG (drag + dig)", "DRIVE": "DRAG (drag + dig)",
        "MESH": "MESH", "SMASH": "CHAMP (hitch + corner)", "CURL_FLAT": "CURL", "SAIL": "SAIL", "DAGGER": "DAGGER",
        "MILLS": "DEEP_POST (post + dig)", "VERTICALS": "FOUR_VERTS", "FOUR_VERTICALS": "FOUR_VERTS",
        "COMEBACK": "COMEBACK (OffensivePlayType)", "PA_BOOT": "BOOT", "PA_BOOT_FLOOD": "BOOT (flag + cross + flat)",
        # défense
        "COVER_0": "BLITZ (Cover 0)", "COVER_0_BLITZ": "BLITZ (Cover 0)", "COVER_0_PRESSURE": "BLITZ (Cover 0)",
        "COVER_1": "MAN (Cover 1)", "COVER_1_PRESSURE": "BLITZ (Cover 1)", "FIVE_MAN_PRESSURE": "BLITZ (5 rushers)",
        "SIX_MAN_PRESSURE": "BLITZ (Cover 0, 6 rushers)", "COVER_2": "COVER_2", "COVER_3": "COVER_3",
        "QUARTERS": "COVER_4", "COVER_4": "COVER_4", "BRACKET": "bloc D (bracket)", "DOUBLE": "bloc D (double)",
        "ROBBER": "COVER_1_ROBBER", "SPLIT_FIELD": "COVER_6 / COVER_8", "COVER_2_BUZZ": "TAMPA_2 (défenseur dans le trou)",
        "FOUR_MAN_RUSH": "défaut (4 rushers)", "FOUR_MAN_STUNT": "ET_STUNT / TEX_STUNT / INTERIOR_STUNT / LONG_STUNT",
        "ZONE_BLITZ": "FIRE_ZONE", "FIRE_3": "FIRE_ZONE", "MUG_PRESSURE": "MUG_BLITZ", "DOUBLE_A_GAP_MUG": "MUG_BLITZ",
        "INTERIOR_BLITZ": "A_GAP_BLITZ / B_GAP_BLITZ", "INTERIOR_PRESSURE": "A_GAP_BLITZ / B_GAP_BLITZ",
        "EDGE_PRESSURE": "EDGE_BLITZ", "OVERLOAD": "OVERLOAD_BLITZ", "FIELD_OVERLOAD": "OVERLOAD_BLITZ (côté champ)",
        "BOUNDARY_PRESSURE": "OVERLOAD_BLITZ (côté court)", "CROSS_BLITZ": "CROSS_DOG", "BLITZ": "BLITZ",
        "SIMULATED_PRESSURE": "SIM_PRESSURE", "TE_GREEN_DOG": "GREEN_DOG", "RB_GREEN_DOG": "GREEN_DOG",
        "MATCH_MAN": "MATCH_QUARTERS / COVER_3_MATCH (règles de match)", "MATCH": "COVER_3_MATCH / MATCH_QUARTERS",
        "2_READ": "PALMS", "COVER_2_CORNER": "COVER_2_SINK (le corner s'enfonce sous le corner route)",
        "WALL": "technique de COVER_3_MATCH / MATCH_QUARTERS", "COLLISION": "technique de PRESS_MAN",
        "MEG": "technique de MATCH_QUARTERS", "MOD": "technique de MATCH_QUARTERS",
    },
    "routes": {"SHALLOW_CROSS": "DRAG", "SAIL": "FLAG", "TEXAS": "ANGLE", "SLANT": "SLANT", "GO": "GO", "SEAM": "SEAM",
               "DIG": "DIG", "POST": "POST", "OUT": "OUT", "DRAG": "DRAG", "CURL": "CURL", "CORNER": "CORNER",
               "FLAT": "FLAT"},
}

# éléments de la base laissés en réserve, avec la raison (rien n'est inventé)
RESERVE = {
    "SALEM": "concept de passe sans structure de routes dans la base (aucune définition sûre) : en attente d'une définition",
    "SPILL_PROTECTION": "terme de la liste « pressure » sans définition dans la base : en attente",
    "10_PERSONNEL": "4 WR exigés, les rosters actuels en ont 3 : formations 10 bloquées par compatibilite() (étape 6)",
    "SPECIAL_TEAMS": "équipes spéciales (§21) : hors playbook offensif / défensif, à traiter avec les règles de jeu",
    "RUN_FITS / BLOCKING / ARCHETYPES": "vocabulaire d'exécution (§10, §13, §22-23) : déjà porté par les blocs A-E",
}


# =====================================================================================================================
# 1. PERSONNEL et FORMATIONS
# =====================================================================================================================
PERSONNEL = {"10": {"RB": 1, "TE": 0, "WR": 4}, "11": {"RB": 1, "TE": 1, "WR": 3}, "12": {"RB": 1, "TE": 2, "WR": 2},
             "21": {"RB": 2, "TE": 1, "WR": 2}, "22": {"RB": 2, "TE": 2, "WR": 1}}

# personnel des formations qui existaient déjà (métadonnée affichée, formations inchangées)
PERSONNEL_EXISTANT = {"SHOTGUN": "11", "SINGLEBACK": "11", "I_FORM": "21", "PISTOL": "11", "EMPTY": "11",
                      "TRIPS": "11", "ACE": "12", "JUMBO": "22", "BUNCH": "11", "HEAVY": "22", "PONY": "21"}

# alignement (site) : [profondeur derrière la ligne, latéral] — mêmes conventions que OFF_FORM du site ; un QB décalé
# latéralement (WILDCAT) porte un 2e nombre. Rôles : WR3 sert de fullback / H quand la formation l'exige (I_FORM).
# libelles : nom affiché pour un emplacement (site : fiche des rôles)
FORMATIONS = {
    # ---- shotgun ----
    "GUN_TIGHT":       {"nom": "Gun Tight", "type": "SHOTGUN", "personnel": "11", "mods": ["TIGHT"],
                        "align": {"TE": [1.0, 5.6], "QB": [5, 0], "RB": [5.2, -1.9], "WR1": [1, -9.5], "WR2": [1, 10.5], "WR3": [1.3, -6.5]}},
    "GUN_Y_OFF":       {"nom": "Gun Y-Off", "type": "SHOTGUN", "personnel": "11", "mods": ["Y_OFF", "HIP"],
                        "align": {"TE": [1.9, 3.6], "QB": [5, 0], "RB": [5.2, -1.9], "WR1": [1, -20], "WR2": [1, 21], "WR3": [1.3, -13]},
                        "libelles": {"TE": "H-back"}},
    "GUN_WING":        {"nom": "Gun Wing", "type": "SHOTGUN", "personnel": "11", "mods": ["WING"],
                        "align": {"TE": [1.7, 6.6], "QB": [5, 0], "RB": [5.2, -1.9], "WR1": [1, -20], "WR2": [1, 21], "WR3": [1.3, -13]},
                        "libelles": {"TE": "Wing"}},
    "GUN_STACK":       {"nom": "Gun Stack", "type": "SHOTGUN", "personnel": "11", "mods": ["STACK"],
                        "align": {"TE": [1.0, 5.6], "QB": [5, 0], "RB": [5.2, -1.9], "WR1": [1, -20], "WR2": [1, 17], "WR3": [3.4, 17.6]}},
    "GUN_QUADS":       {"nom": "Gun Quads", "type": "SHOTGUN", "personnel": "11", "mods": ["QUADS"],
                        "align": {"TE": [1.2, 6.5], "QB": [5, 0], "RB": [5.2, -1.9], "WR1": [1, 22], "WR2": [1.3, 16.5], "WR3": [1.3, 11.5]}},
    "GUN_TRIPS_OPEN":  {"nom": "Gun Trips Open", "type": "SHOTGUN", "personnel": "11", "mods": ["TRIPS", "TRIPS_OPEN"],
                        "align": {"TE": [1.0, 5.6], "QB": [5, 0], "RB": [5.2, 1.9], "WR1": [1, -21], "WR2": [1.3, -9], "WR3": [1.3, -14.5]}},
    "GUN_TRIPS_TIGHT": {"nom": "Gun Trips Tight", "type": "SHOTGUN", "personnel": "11", "mods": ["TRIPS", "TRIPS_TIGHT"],
                        "align": {"TE": [1.0, 5.6], "QB": [5, 0], "RB": [5.2, -1.9], "WR1": [1, -20], "WR2": [1, 13], "WR3": [1.4, 9.4]}},
    "GUN_FLEX":        {"nom": "Gun Flex", "type": "SHOTGUN", "personnel": "11", "mods": ["FLEX"],
                        "align": {"TE": [1.3, 9.5], "QB": [5, 0], "RB": [5.2, -1.9], "WR1": [1, -20], "WR2": [1, 21], "WR3": [1.3, -13]},
                        "libelles": {"TE": "Flex TE"}},
    # ---- singleback ----
    "SINGLEBACK_BUNCH":     {"nom": "Singleback Bunch", "type": "SINGLEBACK", "personnel": "11", "mods": ["BUNCH"],
                             "align": {"TE": [1.2, 8.5], "QB": [1.1, 0], "RB": [7, 0], "WR1": [1, -20], "WR2": [2.6, 10.5], "WR3": [2.6, 6.8]}},
    "SINGLEBACK_WING":      {"nom": "Singleback Wing", "type": "SINGLEBACK", "personnel": "12", "mods": ["WING"],
                             "align": {"TE": [1.0, 5.6], "QB": [1.1, 0], "RB": [7, 0], "WR1": [1, -20], "WR2": [1, 21], "WR3": [1.7, 7.6]},
                             "libelles": {"WR3": "Wing"}},
    "SINGLEBACK_TIGHT":     {"nom": "Singleback Tight", "type": "SINGLEBACK", "personnel": "12", "mods": ["TIGHT"],
                             "align": {"TE": [1.0, 5.6], "QB": [1.1, 0], "RB": [7, 0], "WR1": [1, -9.5], "WR2": [1, 10.5], "WR3": [1.0, -5.6]},
                             "libelles": {"WR3": "Y (2nd TE)"}},
    "SINGLEBACK_DEUCE":     {"nom": "Singleback Deuce", "type": "SINGLEBACK", "personnel": "12", "mods": ["DEUCE"],
                             "align": {"TE": [1.0, 5.6], "QB": [1.1, 0], "RB": [7, 0], "WR1": [1, -20], "WR2": [1, 21], "WR3": [1.0, 7.6]},
                             "libelles": {"WR3": "Y (2nd TE)"}},
    "SINGLEBACK_WING_PAIR": {"nom": "Singleback Wing Pair", "type": "SINGLEBACK", "personnel": "12", "mods": ["WING_PAIR"],
                             "align": {"TE": [1.7, 6.8], "QB": [1.1, 0], "RB": [7, 0], "WR1": [1, -20], "WR2": [1, 21], "WR3": [1.7, -6.8]},
                             "libelles": {"TE": "Wing", "WR3": "Wing"}},
    "SINGLEBACK_NASTY":     {"nom": "Singleback Nasty", "type": "SINGLEBACK", "personnel": "11", "mods": ["NASTY", "CLOSE"],
                             "align": {"TE": [1.0, 5.6], "QB": [1.1, 0], "RB": [7, 0], "WR1": [1, -20], "WR2": [1, 9.6], "WR3": [1.3, -13]}},
    # ---- pistol ----
    "PISTOL_STRONG":     {"nom": "Pistol Strong", "type": "PISTOL", "personnel": "21", "mods": ["STRONG", "OFFSET"],
                          "align": {"TE": [1.0, 5.6], "QB": [4, 0], "RB": [7, 0], "WR1": [1, -20], "WR2": [1, 21], "WR3": [4.6, 2.3]},
                          "libelles": {"WR3": "Fullback"}},
    "PISTOL_WING":       {"nom": "Pistol Wing", "type": "PISTOL", "personnel": "12", "mods": ["WING"],
                          "align": {"TE": [1.0, 5.6], "QB": [4, 0], "RB": [7, 0], "WR1": [1, -20], "WR2": [1, 21], "WR3": [1.7, 7.6]},
                          "libelles": {"WR3": "Wing"}},
    "PISTOL_FULL_HOUSE": {"nom": "Pistol Full House", "type": "PISTOL", "personnel": "21", "mods": ["FULL_HOUSE"],
                          "align": {"TE": [4.6, -2.3], "QB": [4, 0], "RB": [7, 0], "WR1": [1, -20], "WR2": [1, 21], "WR3": [4.6, 2.3]},
                          "libelles": {"TE": "H-back", "WR3": "Fullback"}},
    # ---- I-form et familles STRONG / WEAK ----
    "I_FORM_SLOT": {"nom": "I-Form Slot", "type": "I_FORM", "personnel": "11", "mods": ["SLOT"],
                    "align": {"TE": [4.4, 0], "QB": [1.1, 0], "RB": [7.4, 0], "WR1": [1, -20], "WR2": [1, 19.5], "WR3": [1.3, -13]},
                    "libelles": {"TE": "Fullback (H)"}},
    "I_FORM_WING": {"nom": "I-Form Wing", "type": "I_FORM", "personnel": "21", "mods": ["WING"],
                    "align": {"TE": [1.7, 7.0], "QB": [1.1, 0], "RB": [7.4, 0], "WR1": [1, -20], "WR2": [1, 19.5], "WR3": [4.4, 0]},
                    "libelles": {"TE": "Wing", "WR3": "Fullback"}},
    "STRONG":      {"nom": "Strong I", "type": "I_FORM", "personnel": "21", "mods": ["STRONG", "OFFSET"],
                    "align": {"TE": [1.0, 5.6], "QB": [1.1, 0], "RB": [7.4, 0], "WR1": [1, -20], "WR2": [1, 19.5], "WR3": [4.4, 2.3]},
                    "libelles": {"WR3": "Fullback"}},
    "WEAK":        {"nom": "Weak I", "type": "I_FORM", "personnel": "21", "mods": ["WEAK", "OFFSET"],
                    "align": {"TE": [1.0, 5.6], "QB": [1.1, 0], "RB": [7.4, 0], "WR1": [1, -20], "WR2": [1, 19.5], "WR3": [4.4, -2.3]},
                    "libelles": {"WR3": "Fullback"}},
    # ---- wildcat : snap direct au RB, le QB s'aligne au large ----
    "WILDCAT":     {"nom": "Wildcat", "type": "SHOTGUN", "personnel": "21", "mods": ["WILDCAT"],
                    "align": {"TE": [1.0, 5.6], "QB": [1, -20], "RB": [5, 0], "WR1": [1.3, -13], "WR2": [1, 21], "WR3": [5.2, 2.0]},
                    "libelles": {"QB": "QB (wide)", "RB": "Wildcat (direct snap)", "WR3": "Jet / sweep"},
                    "passes": False},
}
# formation de départ d'un SHIFT (la structure change avant le snap : §05.2) — une sur quatre environ
SHIFT_DEPUIS = {"GUN_TRIPS_OPEN": "SHOTGUN", "GUN_QUADS": "TRIPS", "SINGLEBACK_DEUCE": "ACE", "STRONG": "I_FORM",
                "WEAK": "I_FORM", "PISTOL_WING": "PISTOL", "SINGLEBACK_WING_PAIR": "ACE", "GUN_TRIPS_TIGHT": "GUN_TIGHT",
                "I_FORM_WING": "I_FORM"}
P_SHIFT = 0.25

# rôles de personnel tenus par un autre poste (convention du moteur : JUMBO / ACE placent un WR en 2e TE)
_SUBST = {"TE": ("WR",), "RB": ("TE", "WR"), "WR": ("TE", "RB")}


def compatibilite(personnel, roster):
    """Filtre d'intégrité (§28-29) : (niveau, raison) pour un personnel face à un roster {"RB": n, "TE": n, "WR": n}.

    PRIMARY : chaque rôle tenu par son poste · SUPPORTED : un rôle tenu par un autre poste (WR en 2e TE…) ·
    UNNATURAL : deux rôles ou plus · INVALID : rôle impossible à tenir (raison structurelle).
    """
    besoin = PERSONNEL.get(str(personnel))
    if besoin is None:
        return "INVALID", f"personnel {personnel} inconnu"
    dispo = {k: int(roster.get(k, 0)) for k in ("RB", "TE", "WR")}
    manque = {k: max(0, besoin[k] - dispo[k]) for k in besoin}
    reste = {k: max(0, dispo[k] - besoin[k]) for k in dispo}
    subs = 0
    for k, n in manque.items():
        for _ in range(n):
            src = next((s for s in _SUBST[k] if reste.get(s, 0) > 0), None)
            if src is None or (k == "WR" and besoin["WR"] >= 4):
                return "INVALID", f"{besoin[k]} {k} exigés, le roster en a {dispo[k]} sans remplaçant possible"
            reste[src] -= 1
            subs += 1
    if subs == 0:
        return "PRIMARY", "chaque rôle tenu par son poste"
    if subs == 1:
        return "SUPPORTED", "un rôle tenu par un autre poste"
    return "UNNATURAL", f"{subs} rôles tenus par un autre poste"


# =====================================================================================================================
# 2. ROUTES (nouvelles primitives §08) — même format que moteur.progressions.ROUTES et ROUTE_LIBRARY (notebook / site)
# =====================================================================================================================
ROUTES = {
    "HITCH":      {"classe": "court",   "ouverture": 0.9, "lib": {"depth": 5.0,  "break_depth": 5.0,  "break_angle": 160, "break_run": 1.0,  "direction": "INSIDE"}},
    "ARROW":      {"classe": "court",   "ouverture": 0.8, "lib": {"depth": 3.0,  "break_depth": 1.0,  "break_angle": 60,  "break_run": 8.0,  "direction": "OUTSIDE"}},
    "ANGLE":      {"classe": "court",   "ouverture": 1.2, "lib": {"depth": 5.0,  "break_depth": 3.0,  "break_angle": 120, "break_run": 6.0,  "direction": "INSIDE"}},
    "PIVOT":      {"classe": "court",   "ouverture": 1.2, "lib": {"depth": 5.0,  "break_depth": 5.0,  "break_angle": 90,  "break_run": 6.0,  "direction": "OUTSIDE"}},
    "CHOICE":     {"classe": "court",   "ouverture": 1.3, "lib": {"depth": 6.0,  "break_depth": 6.0,  "break_angle": 90,  "break_run": 5.0,  "direction": "INSIDE"}},
    "COMEBACK":   {"classe": "moyen",   "ouverture": 1.7, "lib": {"depth": 15.0, "break_depth": 14.0, "break_angle": 135, "break_run": 3.0,  "direction": "OUTSIDE"}},
    "DEEP_CROSS": {"classe": "moyen",   "ouverture": 2.0, "lib": {"depth": 18.0, "break_depth": 6.0,  "break_angle": 70,  "break_run": 22.0, "direction": "HORIZONTAL"}},
    "FADE":       {"classe": "profond", "ouverture": 2.0, "lib": {"depth": 28.0, "break_depth": None, "break_angle": 0,   "break_run": None, "direction": "VERTICAL"}},
    "WHEEL":      {"classe": "profond", "ouverture": 2.2, "lib": {"depth": 24.0, "break_depth": 4.0,  "break_angle": 80,  "break_run": 9.0,  "direction": "OUTSIDE"}},
}


# =====================================================================================================================
# 3. CONCEPTS (course, passe, option, RPO)
# =====================================================================================================================
# porteur : membre d'OffensivePlayType qui porte le play (mécanisme de 10.5 / 12.2 bis : le vrai concept est dans
# PLAY_ID_TO_CONCEPT) ; ancre : concept existant dont le nouveau prend une part du budget ; modif : (décalage moyen,
# facteur de variance) des yards, proche de l'ancre (garde l'équilibre) ; classe (courses) : où le front et la motion
# pèsent ; porteur_course : qui porte le ballon ; plan : familles du bloc D (moteur.plan_de_jeu).
R, P = "RUN", "PASS"
CONCEPTS = {
    # ---- courses gap / downhill, périmètre, misdirection (§06.2-06.3) ----
    "WHAM":           {"famille": R, "porteur": "INSIDE_RUN",  "ancre": "INSIDE_RUN",  "modif": (0, 0.9), "classe": "inside",
                       "nom": "Wham", "dessin": "TRAP"},
    "POWER_TOSS":     {"famille": R, "porteur": "POWER",       "ancre": "POWER",       "modif": (1, 1.2), "classe": "gap",
                       "nom": "Power Toss", "dessin": "OUTSIDE_RUN"},
    "PIN_PULL":       {"famille": R, "porteur": "OUTSIDE_RUN", "ancre": "OUTSIDE_RUN", "modif": (1, 1.3), "classe": "outside",
                       "nom": "Pin & Pull", "dessin": "OUTSIDE_RUN"},
    "BUCK_SWEEP":     {"famille": R, "porteur": "OUTSIDE_RUN", "ancre": "OUTSIDE_RUN", "modif": (1, 1.3), "classe": "outside",
                       "nom": "Buck Sweep", "dessin": "OUTSIDE_RUN"},
    "COUNTER_SWEEP":  {"famille": R, "porteur": "COUNTER",     "ancre": "COUNTER",     "modif": (2, 1.5), "classe": "perimeter",
                       "nom": "Counter Sweep", "dessin": "COUNTER"},
    "JET_ACTION":     {"famille": R, "porteur": "INSIDE_RUN",  "ancre": "INSIDE_RUN",  "modif": (0, 1.1), "classe": "inside",
                       "nom": "Jet Action (zone)", "dessin": "INSIDE_RUN", "motion": "JET"},
    "END_AROUND":     {"famille": R, "porteur": "OUTSIDE_RUN", "ancre": "OUTSIDE_RUN", "modif": (1, 1.8), "classe": "perimeter",
                       "nom": "End Around", "dessin": "JET_SWEEP", "porteur_course": ("WR1", "WR2")},
    "REVERSE":        {"famille": R, "porteur": "OUTSIDE_RUN", "ancre": "OUTSIDE_RUN", "modif": (1, 2.0), "classe": "perimeter",
                       "nom": "Reverse", "dessin": "JET_SWEEP", "porteur_course": ("WR2",)},
    "DOUBLE_REVERSE": {"famille": R, "porteur": "OUTSIDE_RUN", "ancre": "OUTSIDE_RUN", "modif": (1, 2.3), "classe": "perimeter",
                       "nom": "Double Reverse", "dessin": "JET_SWEEP", "porteur_course": ("WR1",)},
    # ---- draws / courses du QB (§06.4) ----
    "QB_DRAW":        {"famille": R, "porteur": "DRAW",        "ancre": "DRAW",        "modif": (2, 1.4), "classe": "qb",
                       "nom": "QB Draw", "dessin": "DRAW", "porteur_course": ("QB",)},
    "QB_SWEEP":       {"famille": R, "porteur": "OUTSIDE_RUN", "ancre": "OUTSIDE_RUN", "modif": (1, 1.5), "classe": "qb",
                       "nom": "QB Sweep", "dessin": "OUTSIDE_RUN", "porteur_course": ("QB",)},
    # ---- option (§06.5, §09.1) : la lecture décide du porteur ----
    "POWER_READ":     {"famille": R, "porteur": "POWER",       "ancre": "POWER",       "modif": (1, 1.2), "classe": "option",
                       "nom": "Power Read", "dessin": "POWER", "option": {"QB": 0.45, "RB": 0.55}},
    "INVERTED_VEER":  {"famille": R, "porteur": "POWER",       "ancre": "POWER",       "modif": (1, 1.2), "classe": "option",
                       "nom": "Inverted Veer", "dessin": "POWER", "option": {"QB": 0.55, "RB": 0.45}},
    "SPEED_OPTION":   {"famille": R, "porteur": "OUTSIDE_RUN", "ancre": "OUTSIDE_RUN", "modif": (1, 1.5), "classe": "option",
                       "nom": "Speed Option", "dessin": "OUTSIDE_RUN", "option": {"QB": 0.40, "RB": 0.60}},
    "MIDLINE_OPTION": {"famille": R, "porteur": "INSIDE_RUN",  "ancre": "INSIDE_RUN",  "modif": (0, 1.1), "classe": "option",
                       "nom": "Midline Option", "dessin": "INSIDE_RUN", "option": {"QB": 0.50, "RB": 0.50}},
    "TRIPLE_OPTION":  {"famille": R, "porteur": "INSIDE_RUN",  "ancre": "INSIDE_RUN",  "modif": (1, 1.4), "classe": "option",
                       "nom": "Triple Option", "dessin": "READ_OPTION", "option": {"RB": 0.40, "QB": 0.35, "WR3": 0.25}},
    "SHOVEL_OPTION":  {"famille": R, "porteur": "COUNTER",     "ancre": "COUNTER",     "modif": (1, 1.2), "classe": "option",
                       "nom": "Shovel Option", "dessin": "COUNTER", "option": {"QB": 0.30, "TE": 0.50, "RB": 0.20}},
    # ---- RPO (§09.2) : course appelée, le QB lit un défenseur et donne ou lance ----
    "RPO_INSIDE_ZONE":  {"famille": R, "porteur": "INSIDE_RUN",  "ancre": "INSIDE_RUN",  "modif": (0, 1.0), "classe": "inside",
                         "nom": "RPO Inside Zone", "dessin": "INSIDE_RUN", "rpo": "post"},
    "RPO_READ":         {"famille": R, "porteur": "INSIDE_RUN",  "ancre": "INSIDE_RUN",  "modif": (0, 1.0), "classe": "inside",
                         "nom": "RPO Read", "dessin": "INSIDE_RUN", "rpo": "post"},
    "RPO_ALERT":        {"famille": R, "porteur": "INSIDE_RUN",  "ancre": "INSIDE_RUN",  "modif": (0, 1.0), "classe": "inside",
                         "nom": "RPO Alert", "dessin": "INSIDE_RUN", "rpo": "alert"},
    "RPO_PEEK":         {"famille": R, "porteur": "INSIDE_RUN",  "ancre": "INSIDE_RUN",  "modif": (0, 1.0), "classe": "inside",
                         "nom": "RPO Peek", "dessin": "INSIDE_RUN", "rpo": "peek"},
    "RPO_POWER":        {"famille": R, "porteur": "POWER",       "ancre": "POWER",       "modif": (1, 0.8), "classe": "gap",
                         "nom": "RPO Power", "dessin": "POWER", "rpo": "post"},
    "RPO_OUTSIDE_ZONE": {"famille": R, "porteur": "OUTSIDE_RUN", "ancre": "OUTSIDE_RUN", "modif": (1, 1.3), "classe": "outside",
                         "nom": "RPO Outside Zone", "dessin": "OUTSIDE_RUN", "rpo": "post"},
    # ---- passes rapides et écrans (§07.1-07.2) ----
    "HITCH":            {"famille": P, "porteur": "QUICK_SLANT", "ancre": "QUICK_SLANT", "modif": (0, 0.8), "nom": "Hitch",
                         "plan": {"QUICK", "BATTRE_ZONE"}},
    "CHOICE":           {"famille": P, "porteur": "SHORT_OUT",   "ancre": "SHORT_OUT",   "modif": (1, 0.9), "nom": "Choice",
                         "plan": {"QUICK", "BATTRE_HOMME"}},
    "FL_SE_SCREEN":     {"famille": P, "porteur": "SCREEN",      "ancre": "SCREEN",      "modif": (-1, 1.9), "nom": "WR Screen",
                         "plan": {"QUICK"}},
    "WR_TUNNEL_SCREEN": {"famille": P, "porteur": "SCREEN",      "ancre": "SCREEN",      "modif": (0, 1.9), "nom": "Tunnel Screen",
                         "plan": {"QUICK"}},
    "MESH_WHEEL":       {"famille": P, "porteur": "CROSS",       "ancre": "DRAG",        "modif": (1, 1.2), "nom": "Mesh Wheel",
                         "plan": {"BATTRE_HOMME"}},
    "PIVOT":            {"famille": P, "porteur": "SHORT_OUT",   "ancre": "SHORT_OUT",   "modif": (0, 0.8), "nom": "Pivot",
                         "plan": {"QUICK", "BATTRE_HOMME"}},
    "SPOT_SNAG":        {"famille": P, "porteur": "QUICK_SLANT", "ancre": "QUICK_SLANT", "modif": (0, 0.8), "nom": "Spot (Snag)",
                         "plan": {"QUICK", "BATTRE_ZONE"}},
    # ---- passes intermédiaires (§07.3) ----
    "LEVELS":           {"famille": P, "porteur": "CROSS",       "ancre": "CROSS",       "modif": (2, 1.0), "nom": "Levels",
                         "plan": {"BATTRE_ZONE"}},
    "Y_CROSS":          {"famille": P, "porteur": "CROSS",       "ancre": "CROSS",       "modif": (3, 1.2), "nom": "Y-Cross",
                         "plan": {"BATTRE_HOMME"}},
    "DART_QUICK_DIG":   {"famille": P, "porteur": "CROSS",       "ancre": "IN",          "modif": (1, 0.9), "nom": "Dart / Quick Dig",
                         "plan": {"BATTRE_ZONE"}},
    "DOUBLE_DIG":       {"famille": P, "porteur": "CROSS",       "ancre": "IN",          "modif": (2, 1.1), "nom": "Double Dig",
                         "plan": {"BATTRE_ZONE"}},
    "FLOOD":            {"famille": P, "porteur": "CROSS",       "ancre": "CROSS",       "modif": (2, 1.1), "nom": "Flood",
                         "plan": {"BATTRE_ZONE"}},
    # ---- passes profondes (§07.4) ----
    "DEEP_CROSS":       {"famille": P, "porteur": "DEEP_POST",   "ancre": "DEEP_POST",   "modif": (5, 1.4), "nom": "Deep Cross",
                         "plan": {"PROFONDS", "BATTRE_HOMME"}},
    "DOUBLE_POST":      {"famille": P, "porteur": "DEEP_POST",   "ancre": "DEEP_POST",   "modif": (5, 1.5), "nom": "Double Post",
                         "plan": {"PROFONDS", "BATTRE_ZONE"}},
    "DIVIDE":           {"famille": P, "porteur": "FOUR_VERTS",  "ancre": "FOUR_VERTS",  "modif": (5, 1.5), "nom": "Divide",
                         "plan": {"PROFONDS", "BATTRE_ZONE"}},
    "SWITCH_VERTICALS": {"famille": P, "porteur": "FOUR_VERTS",  "ancre": "FOUR_VERTS",  "modif": (5, 1.6), "nom": "Switch Verticals",
                         "plan": {"PROFONDS", "BATTRE_HOMME"}},
    # ---- play action (§07.5) ----
    "PA_SLIDE":         {"famille": P, "porteur": "PLAY_ACTION", "ancre": "PLAY_ACTION", "modif": (3, 1.2), "nom": "PA Slide",
                         "plan": {"PROFONDS"}, "pa": True},
    "PA_FLOOD":         {"famille": P, "porteur": "PLAY_ACTION", "ancre": "PLAY_ACTION", "modif": (3, 1.3), "nom": "PA Flood",
                         "plan": {"PROFONDS"}, "pa": True},
}
for _c, _d in list(CONCEPTS.items()):
    if _d.get("rpo"):
        # le côté « lancer » d'un RPO : un concept de passe à part (sa progression, ses yards : jeu rapide)
        CONCEPTS[_c + "_THROW"] = {"famille": P, "porteur": "QUICK_SLANT", "ancre": None, "modif": (0, 0.9),
                                   "nom": _d["nom"] + " (throw)", "plan": {"QUICK"}, "rpo_de": _c}

# progression de lecture (rôle, route) : primaire, secondaire, tertiaire, checkdown (moteur.progressions)
PROGRESSIONS = {
    "HITCH":            [("WR1", "HITCH"), ("WR2", "HITCH"), ("WR3", "SEAM"), ("RB", "FLAT")],
    "CHOICE":           [("WR3", "CHOICE"), ("WR1", "GO"), ("TE", "DRAG"), ("RB", "FLAT")],
    "FL_SE_SCREEN":     [("WR1", "SCREEN"), ("WR3", "QUICK_SLANT"), ("TE", "DRAG"), ("RB", "FLAT")],
    "WR_TUNNEL_SCREEN": [("WR2", "SCREEN"), ("WR3", "SLANT"), ("TE", "DRAG"), ("RB", "FLAT")],
    "MESH_WHEEL":       [("WR3", "DRAG"), ("RB", "WHEEL"), ("WR1", "CORNER"), ("TE", "DRAG")],
    "PIVOT":            [("WR3", "PIVOT"), ("WR1", "GO"), ("TE", "STICK"), ("RB", "FLAT")],
    "SPOT_SNAG":        [("WR2", "CORNER"), ("WR3", "STICK"), ("TE", "FLAT"), ("RB", "DRAG")],
    "LEVELS":           [("WR2", "IN"), ("WR3", "DRAG"), ("WR1", "POST"), ("RB", "FLAT")],
    "Y_CROSS":          [("TE", "DEEP_CROSS"), ("WR1", "POST"), ("WR2", "CURL"), ("RB", "FLAT")],
    "DART_QUICK_DIG":   [("WR3", "IN"), ("WR1", "SLANT"), ("TE", "DRAG"), ("RB", "FLAT")],
    "DOUBLE_DIG":       [("WR1", "DIG"), ("WR2", "DIG"), ("TE", "SEAM"), ("RB", "FLAT")],
    "FLOOD":            [("WR3", "OUT"), ("WR2", "GO"), ("TE", "FLAT"), ("RB", "DRAG")],
    "DEEP_CROSS":       [("WR2", "DEEP_CROSS"), ("WR1", "POST"), ("TE", "FLAT"), ("RB", "DRAG")],
    "DOUBLE_POST":      [("WR3", "POST"), ("WR1", "POST"), ("TE", "DRAG"), ("RB", "FLAT")],
    "DIVIDE":           [("TE", "SEAM"), ("WR3", "SEAM"), ("WR1", "GO"), ("RB", "FLAT")],
    "SWITCH_VERTICALS": [("WR3", "WHEEL"), ("WR1", "SEAM"), ("WR2", "GO"), ("RB", "FLAT")],
    "PA_SLIDE":         [("WR2", "DEEP_CROSS"), ("WR1", "POST"), ("TE", "FLAT"), ("RB", "FLAT")],
    "PA_FLOOD":         [("WR3", "OUT"), ("WR1", "GO"), ("TE", "FLAT"), ("RB", "DRAG")],
    # côté lancer des RPO : jeu rapide, sans le RB (il porte la feinte)
    "RPO_INSIDE_ZONE_THROW":  [("WR3", "SLANT"), ("WR1", "HITCH"), ("TE", "STICK")],
    "RPO_READ_THROW":         [("WR3", "STICK"), ("WR1", "HITCH"), ("TE", "FLAT")],
    "RPO_ALERT_THROW":        [("WR1", "FADE"), ("WR3", "SCREEN"), ("TE", "STICK")],
    "RPO_PEEK_THROW":         [("WR1", "SLANT"), ("WR2", "HITCH"), ("TE", "STICK")],
    "RPO_POWER_THROW":        [("TE", "SEAM"), ("WR1", "SLANT"), ("WR3", "HITCH")],
    "RPO_OUTSIDE_ZONE_THROW": [("WR1", "HITCH"), ("WR3", "ARROW"), ("TE", "FLAT")],
}

# dessin du site pour chaque concept de passe : route des autres éligibles (slots 8 WR1 · 9 WR2 · 10 WR3 · 5 TE · 7 RB)
# et route de la cible par défaut — mêmes conventions que PASS_ASSIGN / TARGET_DEFAULT du site
DESSIN_PASSE = {
    "HITCH":            ({8: "HITCH", 9: "HITCH", 10: "SEAM", 5: "STICK", 7: "FLAT"}, "HITCH"),
    "CHOICE":           ({8: "GO", 9: "HITCH", 10: "CHOICE", 5: "DRAG", 7: "FLAT"}, "CHOICE"),
    "FL_SE_SCREEN":     ({8: "SCREEN_WR", 9: "STALK", 10: "STALK", 5: "BLOCK", 7: "FLAT"}, "SCREEN_WR"),
    "WR_TUNNEL_SCREEN": ({8: "STALK", 9: "TUNNEL", 10: "STALK", 5: "BLOCK", 7: "FLAT"}, "TUNNEL"),
    "MESH_WHEEL":       ({8: "CORNER", 9: "DRAG", 10: "DRAG", 5: "SEAM", 7: "WHEEL"}, "DRAG"),
    "PIVOT":            ({8: "GO", 9: "OUT", 10: "PIVOT", 5: "STICK", 7: "FLAT"}, "PIVOT"),
    "SPOT_SNAG":        ({8: "GO", 9: "CORNER", 10: "STICK", 5: "FLAT", 7: "DRAG"}, "CORNER"),
    "LEVELS":           ({8: "POST", 9: "IN", 10: "DRAG", 5: "SEAM", 7: "FLAT"}, "IN"),
    "Y_CROSS":          ({8: "POST", 9: "CURL", 10: "FLAT", 5: "DEEP_CROSS", 7: "FLAT"}, "DEEP_CROSS"),
    "DART_QUICK_DIG":   ({8: "SLANT", 9: "GO", 10: "IN", 5: "DRAG", 7: "FLAT"}, "IN"),
    "DOUBLE_DIG":       ({8: "DIG", 9: "DIG", 10: "SEAM", 5: "SEAM", 7: "FLAT"}, "DIG"),
    "FLOOD":            ({8: "POST", 9: "GO", 10: "OUT", 5: "FLAT", 7: "DRAG"}, "OUT"),
    "DEEP_CROSS":       ({8: "POST", 9: "DEEP_CROSS", 10: "DRAG", 5: "FLAT", 7: "DRAG"}, "DEEP_CROSS"),
    "DOUBLE_POST":      ({8: "POST", 9: "DIG", 10: "POST", 5: "DRAG", 7: "FLAT"}, "POST"),
    "DIVIDE":           ({8: "GO", 9: "GO", 10: "SEAM", 5: "SEAM", 7: "FLAT"}, "SEAM"),
    "SWITCH_VERTICALS": ({8: "SEAM", 9: "GO", 10: "WHEEL", 5: "BLOCK", 7: "FLAT"}, "GO"),
    "PA_SLIDE":         ({8: "POST", 9: "DEEP_CROSS", 10: "DIG", 5: "FLAT", 7: "FAKE"}, "DEEP_CROSS"),
    "PA_FLOOD":         ({8: "GO", 9: "GO", 10: "OUT", 5: "FLAT", 7: "FAKE"}, "OUT"),
    "RPO_INSIDE_ZONE_THROW":  ({8: "HITCH", 9: "HITCH", 10: "SLANT", 5: "STICK", 7: "FAKE"}, "SLANT"),
    "RPO_READ_THROW":         ({8: "HITCH", 9: "GO", 10: "STICK", 5: "FLAT", 7: "FAKE"}, "STICK"),
    "RPO_ALERT_THROW":        ({8: "GO", 9: "STALK", 10: "BUBBLE", 5: "STICK", 7: "FAKE"}, "GO"),
    "RPO_PEEK_THROW":         ({8: "SLANT", 9: "HITCH", 10: "STALK", 5: "STICK", 7: "FAKE"}, "SLANT"),
    "RPO_POWER_THROW":        ({8: "SLANT", 9: "GO", 10: "HITCH", 5: "SEAM", 7: "FAKE"}, "SEAM"),
    "RPO_OUTSIDE_ZONE_THROW": ({8: "HITCH", 9: "GO", 10: "ARROW", 5: "FLAT", 7: "FAKE"}, "HITCH"),
}

# route animée de la cible sur le site (bibliothèque partagée) quand le moteur ne la donne pas
ROUTE_CONCEPT = {c: d[1] for c, d in DESSIN_PASSE.items()
                 if d[1] in ROUTES or d[1] in ("IN", "OUT", "SLANT", "POST", "CORNER", "GO", "DRAG", "SEAM", "CURL", "DIG",
                                              "STICK", "FLAG")}


# =====================================================================================================================
# 4. PLAYS (formation × concept) — les nouveaux plays du playbook des franchises
# =====================================================================================================================
# play_id : (formation, concept). Les nouvelles formations reçoivent aussi des concepts existants (variantes : même
# budget du coordinateur, réparti entre plus de formations). Aucun play_id n'existe déjà (contrôlé par le notebook).
PLAYS = {
    # ---- GUN_TIGHT ----
    "GUN_TIGHT_INSIDE_ZONE": ("GUN_TIGHT", "INSIDE_RUN"), "GUN_TIGHT_RPO_INSIDE_ZONE": ("GUN_TIGHT", "RPO_INSIDE_ZONE"),
    "GUN_TIGHT_MESH_WHEEL": ("GUN_TIGHT", "MESH_WHEEL"), "GUN_TIGHT_PIVOT": ("GUN_TIGHT", "PIVOT"),
    "GUN_TIGHT_SPOT": ("GUN_TIGHT", "SPOT_SNAG"), "GUN_TIGHT_DART": ("GUN_TIGHT", "DART_QUICK_DIG"),
    "GUN_TIGHT_MESH": ("GUN_TIGHT", "MESH"),
    # ---- GUN_Y_OFF ----
    "GUN_Y_OFF_INSIDE_ZONE": ("GUN_Y_OFF", "INSIDE_RUN"), "GUN_Y_OFF_RPO_INSIDE_ZONE": ("GUN_Y_OFF", "RPO_INSIDE_ZONE"),
    "GUN_Y_OFF_RPO_READ": ("GUN_Y_OFF", "RPO_READ"), "GUN_Y_OFF_INVERTED_VEER": ("GUN_Y_OFF", "INVERTED_VEER"),
    "GUN_Y_OFF_POWER_READ": ("GUN_Y_OFF", "POWER_READ"), "GUN_Y_OFF_Y_CROSS": ("GUN_Y_OFF", "Y_CROSS"),
    "GUN_Y_OFF_LEVELS": ("GUN_Y_OFF", "LEVELS"), "GUN_Y_OFF_PA_SLIDE": ("GUN_Y_OFF", "PA_SLIDE"),
    "GUN_Y_OFF_WHAM": ("GUN_Y_OFF", "WHAM"),
    # ---- GUN_WING ----
    "GUN_WING_COUNTER": ("GUN_WING", "COUNTER"), "GUN_WING_QB_DRAW": ("GUN_WING", "QB_DRAW"),
    "GUN_WING_SHOVEL": ("GUN_WING", "SHOVEL_OPTION"), "GUN_WING_FLOOD": ("GUN_WING", "FLOOD"),
    "GUN_WING_PA_FLOOD": ("GUN_WING", "PA_FLOOD"), "GUN_WING_COUNTER_SWEEP": ("GUN_WING", "COUNTER_SWEEP"),
    # ---- GUN_STACK ----
    "GUN_STACK_CHOICE": ("GUN_STACK", "CHOICE"), "GUN_STACK_SWITCH": ("GUN_STACK", "SWITCH_VERTICALS"),
    "GUN_STACK_WR_SCREEN": ("GUN_STACK", "FL_SE_SCREEN"), "GUN_STACK_HITCH": ("GUN_STACK", "HITCH"),
    "GUN_STACK_QUICK_SLANT": ("GUN_STACK", "QUICK_SLANT"), "GUN_STACK_INSIDE_ZONE": ("GUN_STACK", "INSIDE_RUN"),
    # ---- GUN_QUADS ----
    "GUN_QUADS_DIVIDE": ("GUN_QUADS", "DIVIDE"), "GUN_QUADS_LEVELS": ("GUN_QUADS", "LEVELS"),
    "GUN_QUADS_TUNNEL": ("GUN_QUADS", "WR_TUNNEL_SCREEN"), "GUN_QUADS_QB_DRAW": ("GUN_QUADS", "QB_DRAW"),
    "GUN_QUADS_DRAW": ("GUN_QUADS", "DRAW"),
    # ---- GUN_TRIPS_OPEN ----
    "GUN_TRIPS_OPEN_RPO_ALERT": ("GUN_TRIPS_OPEN", "RPO_ALERT"), "GUN_TRIPS_OPEN_RPO_PEEK": ("GUN_TRIPS_OPEN", "RPO_PEEK"),
    "GUN_TRIPS_OPEN_FLOOD": ("GUN_TRIPS_OPEN", "FLOOD"), "GUN_TRIPS_OPEN_DOUBLE_POST": ("GUN_TRIPS_OPEN", "DOUBLE_POST"),
    "GUN_TRIPS_OPEN_SPEED_OPTION": ("GUN_TRIPS_OPEN", "SPEED_OPTION"),
    "GUN_TRIPS_OPEN_TUNNEL": ("GUN_TRIPS_OPEN", "WR_TUNNEL_SCREEN"), "GUN_TRIPS_OPEN_INSIDE_ZONE": ("GUN_TRIPS_OPEN", "INSIDE_RUN"),
    # ---- GUN_TRIPS_TIGHT ----
    "GUN_TRIPS_TIGHT_SPOT": ("GUN_TRIPS_TIGHT", "SPOT_SNAG"), "GUN_TRIPS_TIGHT_Y_CROSS": ("GUN_TRIPS_TIGHT", "Y_CROSS"),
    "GUN_TRIPS_TIGHT_COUNTER_SWEEP": ("GUN_TRIPS_TIGHT", "COUNTER_SWEEP"),
    "GUN_TRIPS_TIGHT_POWER": ("GUN_TRIPS_TIGHT", "POWER"), "GUN_TRIPS_TIGHT_STICK": ("GUN_TRIPS_TIGHT", "STICK"),
    # ---- GUN_FLEX ----
    "GUN_FLEX_HITCH": ("GUN_FLEX", "HITCH"), "GUN_FLEX_DOUBLE_DIG": ("GUN_FLEX", "DOUBLE_DIG"),
    "GUN_FLEX_MIDLINE": ("GUN_FLEX", "MIDLINE_OPTION"), "GUN_FLEX_RPO_READ": ("GUN_FLEX", "RPO_READ"),
    "GUN_FLEX_CURL": ("GUN_FLEX", "CURL"),
    # ---- SINGLEBACK_BUNCH ----
    "SINGLEBACK_BUNCH_SPOT": ("SINGLEBACK_BUNCH", "SPOT_SNAG"), "SINGLEBACK_BUNCH_MESH_WHEEL": ("SINGLEBACK_BUNCH", "MESH_WHEEL"),
    "SINGLEBACK_BUNCH_CHOICE": ("SINGLEBACK_BUNCH", "CHOICE"), "SINGLEBACK_BUNCH_PA_FLOOD": ("SINGLEBACK_BUNCH", "PA_FLOOD"),
    "SINGLEBACK_BUNCH_OUTSIDE_ZONE": ("SINGLEBACK_BUNCH", "OUTSIDE_RUN"),
    # ---- SINGLEBACK_WING ----
    "SINGLEBACK_WING_PIN_PULL": ("SINGLEBACK_WING", "PIN_PULL"), "SINGLEBACK_WING_WHAM": ("SINGLEBACK_WING", "WHAM"),
    "SINGLEBACK_WING_PA_SLIDE": ("SINGLEBACK_WING", "PA_SLIDE"), "SINGLEBACK_WING_Y_CROSS": ("SINGLEBACK_WING", "Y_CROSS"),
    "SINGLEBACK_WING_INSIDE_ZONE": ("SINGLEBACK_WING", "INSIDE_RUN"),
    # ---- SINGLEBACK_TIGHT ----
    "SINGLEBACK_TIGHT_BUCK_SWEEP": ("SINGLEBACK_TIGHT", "BUCK_SWEEP"), "SINGLEBACK_TIGHT_POWER_TOSS": ("SINGLEBACK_TIGHT", "POWER_TOSS"),
    "SINGLEBACK_TIGHT_PA_FLOOD": ("SINGLEBACK_TIGHT", "PA_FLOOD"), "SINGLEBACK_TIGHT_DOUBLE_DIG": ("SINGLEBACK_TIGHT", "DOUBLE_DIG"),
    "SINGLEBACK_TIGHT_POWER": ("SINGLEBACK_TIGHT", "POWER"),
    # ---- SINGLEBACK_DEUCE ----
    "SINGLEBACK_DEUCE_COUNTER_SWEEP": ("SINGLEBACK_DEUCE", "COUNTER_SWEEP"), "SINGLEBACK_DEUCE_POWER": ("SINGLEBACK_DEUCE", "POWER"),
    "SINGLEBACK_DEUCE_PA_FLOOD": ("SINGLEBACK_DEUCE", "PA_FLOOD"), "SINGLEBACK_DEUCE_OUTSIDE_ZONE": ("SINGLEBACK_DEUCE", "OUTSIDE_RUN"),
    # ---- SINGLEBACK_WING_PAIR ----
    "SINGLEBACK_WING_PAIR_BUCK_SWEEP": ("SINGLEBACK_WING_PAIR", "BUCK_SWEEP"),
    "SINGLEBACK_WING_PAIR_JET_ACTION": ("SINGLEBACK_WING_PAIR", "JET_ACTION"),
    "SINGLEBACK_WING_PAIR_DEEP_CROSS": ("SINGLEBACK_WING_PAIR", "DEEP_CROSS"),
    "SINGLEBACK_WING_PAIR_COUNTER": ("SINGLEBACK_WING_PAIR", "COUNTER"),
    # ---- SINGLEBACK_NASTY ----
    "SINGLEBACK_NASTY_PIN_PULL": ("SINGLEBACK_NASTY", "PIN_PULL"), "SINGLEBACK_NASTY_HITCH": ("SINGLEBACK_NASTY", "HITCH"),
    "SINGLEBACK_NASTY_DART": ("SINGLEBACK_NASTY", "DART_QUICK_DIG"), "SINGLEBACK_NASTY_INSIDE_ZONE": ("SINGLEBACK_NASTY", "INSIDE_RUN"),
    # ---- PISTOL_STRONG ----
    "PISTOL_STRONG_POWER_READ": ("PISTOL_STRONG", "POWER_READ"), "PISTOL_STRONG_POWER_TOSS": ("PISTOL_STRONG", "POWER_TOSS"),
    "PISTOL_STRONG_TRIPLE": ("PISTOL_STRONG", "TRIPLE_OPTION"), "PISTOL_STRONG_INVERTED_VEER": ("PISTOL_STRONG", "INVERTED_VEER"),
    "PISTOL_STRONG_PA_SLIDE": ("PISTOL_STRONG", "PA_SLIDE"), "PISTOL_STRONG_RPO_POWER": ("PISTOL_STRONG", "RPO_POWER"),
    "PISTOL_STRONG_POWER": ("PISTOL_STRONG", "POWER"),
    # ---- PISTOL_WING ----
    "PISTOL_WING_JET_ACTION": ("PISTOL_WING", "JET_ACTION"), "PISTOL_WING_RPO_POWER": ("PISTOL_WING", "RPO_POWER"),
    "PISTOL_WING_SPEED_OPTION": ("PISTOL_WING", "SPEED_OPTION"), "PISTOL_WING_PA_FLOOD": ("PISTOL_WING", "PA_FLOOD"),
    "PISTOL_WING_RPO_OUTSIDE_ZONE": ("PISTOL_WING", "RPO_OUTSIDE_ZONE"), "PISTOL_WING_OUTSIDE_ZONE": ("PISTOL_WING", "OUTSIDE_RUN"),
    # ---- PISTOL_FULL_HOUSE ----
    "PISTOL_FULL_HOUSE_TRIPLE": ("PISTOL_FULL_HOUSE", "TRIPLE_OPTION"),
    "PISTOL_FULL_HOUSE_COUNTER_SWEEP": ("PISTOL_FULL_HOUSE", "COUNTER_SWEEP"),
    "PISTOL_FULL_HOUSE_POWER_TOSS": ("PISTOL_FULL_HOUSE", "POWER_TOSS"),
    "PISTOL_FULL_HOUSE_PA_SLIDE": ("PISTOL_FULL_HOUSE", "PA_SLIDE"), "PISTOL_FULL_HOUSE_POWER": ("PISTOL_FULL_HOUSE", "POWER"),
    # ---- I_FORM_SLOT / I_FORM_WING / STRONG / WEAK ----
    "I_FORM_SLOT_POWER_TOSS": ("I_FORM_SLOT", "POWER_TOSS"), "I_FORM_SLOT_DEEP_CROSS": ("I_FORM_SLOT", "DEEP_CROSS"),
    "I_FORM_SLOT_DOUBLE_DIG": ("I_FORM_SLOT", "DOUBLE_DIG"), "I_FORM_SLOT_INSIDE_ZONE": ("I_FORM_SLOT", "INSIDE_RUN"),
    "I_FORM_WING_WHAM": ("I_FORM_WING", "WHAM"), "I_FORM_WING_BUCK_SWEEP": ("I_FORM_WING", "BUCK_SWEEP"),
    "I_FORM_WING_PA_SLIDE": ("I_FORM_WING", "PA_SLIDE"), "I_FORM_WING_POWER": ("I_FORM_WING", "POWER"),
    "STRONG_LEAD": ("STRONG", "INSIDE_RUN"), "STRONG_POWER_TOSS": ("STRONG", "POWER_TOSS"),
    "STRONG_POWER": ("STRONG", "POWER"), "STRONG_PA_FLOOD": ("STRONG", "PA_FLOOD"),
    "WEAK_ISO": ("WEAK", "INSIDE_RUN"), "WEAK_COUNTER": ("WEAK", "COUNTER"), "WEAK_PA_SLIDE": ("WEAK", "PA_SLIDE"),
    "WEAK_END_AROUND": ("WEAK", "END_AROUND"),
    # ---- WILDCAT (courses seulement) ----
    "WILDCAT_POWER": ("WILDCAT", "POWER"), "WILDCAT_INSIDE_ZONE": ("WILDCAT", "INSIDE_RUN"),
    "WILDCAT_JET_SWEEP": ("WILDCAT", "JET_SWEEP"),
    # ---- nouveaux concepts dans des formations existantes ----
    "SHOTGUN_HITCH": ("SHOTGUN", "HITCH"), "SHOTGUN_REVERSE": ("SHOTGUN", "REVERSE"),
    "SHOTGUN_RPO_INSIDE_ZONE": ("SHOTGUN", "RPO_INSIDE_ZONE"), "SHOTGUN_QB_SWEEP": ("SHOTGUN", "QB_SWEEP"),
    "SHOTGUN_LEVELS": ("SHOTGUN", "LEVELS"), "SHOTGUN_MIDLINE": ("SHOTGUN", "MIDLINE_OPTION"),
    "EMPTY_QB_DRAW": ("EMPTY", "QB_DRAW"), "EMPTY_DOUBLE_POST": ("EMPTY", "DOUBLE_POST"), "EMPTY_CHOICE": ("EMPTY", "CHOICE"),
    "TRIPS_LEVELS": ("TRIPS", "LEVELS"), "TRIPS_WR_SCREEN": ("TRIPS", "FL_SE_SCREEN"), "TRIPS_DOUBLE_REVERSE": ("TRIPS", "DOUBLE_REVERSE"),
    "BUNCH_MESH_WHEEL": ("BUNCH", "MESH_WHEEL"), "BUNCH_SPOT": ("BUNCH", "SPOT_SNAG"),
    "PISTOL_INVERTED_VEER": ("PISTOL", "INVERTED_VEER"), "PISTOL_RPO_READ": ("PISTOL", "RPO_READ"),
    "PISTOL_RPO_INSIDE_ZONE": ("PISTOL", "RPO_INSIDE_ZONE"),
    "SINGLEBACK_PIN_PULL": ("SINGLEBACK", "PIN_PULL"), "SINGLEBACK_Y_CROSS": ("SINGLEBACK", "Y_CROSS"),
    "SINGLEBACK_PA_SLIDE": ("SINGLEBACK", "PA_SLIDE"), "SINGLEBACK_JET_ACTION": ("SINGLEBACK", "JET_ACTION"),
    "ACE_PA_SLIDE": ("ACE", "PA_SLIDE"), "ACE_WHAM": ("ACE", "WHAM"), "JUMBO_WHAM": ("JUMBO", "WHAM"),
    "I_FORM_COUNTER_SWEEP": ("I_FORM", "COUNTER_SWEEP"), "I_FORM_PA_FLOOD": ("I_FORM", "PA_FLOOD"),
    "HEAVY_POWER_TOSS": ("HEAVY", "POWER_TOSS"), "PONY_TRIPLE": ("PONY", "TRIPLE_OPTION"),
    "PONY_RPO_INSIDE_ZONE": ("PONY", "RPO_INSIDE_ZONE"), "PONY_SPEED_OPTION": ("PONY", "SPEED_OPTION"),
}


NOMS_EXISTANTS = {"INSIDE_RUN": "Inside Zone", "OUTSIDE_RUN": "Outside Zone", "POWER": "Power", "COUNTER": "Counter",
                  "DRAW": "Draw", "MESH": "Mesh", "QUICK_SLANT": "Quick Slant", "STICK": "Stick", "CURL": "Curl",
                  "JET_SWEEP": "Jet Sweep"}


def nom_play(pid):
    f, c = PLAYS[pid]
    fn = FORMATIONS[f]["nom"] if f in FORMATIONS else f.replace("_", " ").title().replace("I Form", "I-Form")
    cn = CONCEPTS[c]["nom"] if c in CONCEPTS else NOMS_EXISTANTS.get(c, c.replace("_", " ").title())
    if pid.endswith("_LEAD"):
        cn = "Lead"
    elif pid.endswith("_ISO"):
        cn = "Iso"
    return f"{fn} {cn}"


# =====================================================================================================================
# 5. IDENTITÉS — part de chaque nouveau concept dans son ancre, formations préférées, exclusions
# =====================================================================================================================
# part (0-1) du budget RESTANT de l'ancre (après le playbook Roman) ; total par ancre ≤ 0,6 (contrôlé)
PARTS = {
    "CTX": {"HITCH": .10, "CHOICE": .15, "FL_SE_SCREEN": .15, "WR_TUNNEL_SCREEN": .10, "MESH_WHEEL": .15, "LEVELS": .20,
            "PIVOT": .10, "SPOT_SNAG": .15, "Y_CROSS": .20, "DART_QUICK_DIG": .15, "DOUBLE_DIG": .10, "DEEP_CROSS": .15,
            "FLOOD": .15, "DOUBLE_POST": .15, "DIVIDE": .10, "SWITCH_VERTICALS": .10, "PA_SLIDE": .15, "PA_FLOOD": .15,
            "WHAM": .08, "POWER_TOSS": .10, "PIN_PULL": .10, "BUCK_SWEEP": .08, "COUNTER_SWEEP": .12, "END_AROUND": .05,
            "REVERSE": .03, "DOUBLE_REVERSE": .02, "QB_DRAW": .10, "QB_SWEEP": .05, "POWER_READ": .15,
            "INVERTED_VEER": .12, "SPEED_OPTION": .06, "MIDLINE_OPTION": .06, "TRIPLE_OPTION": .04, "SHOVEL_OPTION": .08,
            "JET_ACTION": .08, "RPO_INSIDE_ZONE": .15, "RPO_READ": .06, "RPO_ALERT": .04, "RPO_PEEK": .04,
            "RPO_POWER": .12, "RPO_OUTSIDE_ZONE": .10},
    "VEC": {"HITCH": .05, "CHOICE": .10, "FL_SE_SCREEN": .20, "WR_TUNNEL_SCREEN": .15, "MESH_WHEEL": .20, "LEVELS": .10,
            "PIVOT": .05, "SPOT_SNAG": .08, "Y_CROSS": .10, "DART_QUICK_DIG": .10, "DOUBLE_DIG": .10, "DEEP_CROSS": .20,
            "FLOOD": .15, "DOUBLE_POST": .20, "DIVIDE": .20, "SWITCH_VERTICALS": .20, "PA_SLIDE": .10, "PA_FLOOD": .10,
            "PIN_PULL": .05, "COUNTER_SWEEP": .05, "END_AROUND": .08, "REVERSE": .05, "DOUBLE_REVERSE": .03,
            "QB_DRAW": .06, "JET_ACTION": .08, "RPO_INSIDE_ZONE": .10, "RPO_ALERT": .10, "RPO_PEEK": .10,
            "RPO_OUTSIDE_ZONE": .05},
    "AEG": {"HITCH": .20, "CHOICE": .15, "FL_SE_SCREEN": .10, "WR_TUNNEL_SCREEN": .10, "MESH_WHEEL": .10, "LEVELS": .20,
            "PIVOT": .15, "SPOT_SNAG": .20, "Y_CROSS": .10, "DART_QUICK_DIG": .20, "DOUBLE_DIG": .15, "DEEP_CROSS": .05,
            "FLOOD": .15, "DOUBLE_POST": .05, "DIVIDE": .05, "SWITCH_VERTICALS": .05, "PA_SLIDE": .15, "PA_FLOOD": .10,
            "WHAM": .10, "POWER_TOSS": .08, "PIN_PULL": .12, "BUCK_SWEEP": .08, "COUNTER_SWEEP": .08, "END_AROUND": .02,
            "REVERSE": .01, "QB_DRAW": .05, "POWER_READ": .05, "INVERTED_VEER": .03, "JET_ACTION": .05,
            "RPO_READ": .10, "RPO_INSIDE_ZONE": .08},
    "MNL": {"HITCH": .08, "CHOICE": .05, "FL_SE_SCREEN": .05, "WR_TUNNEL_SCREEN": .05, "MESH_WHEEL": .05, "LEVELS": .08,
            "PIVOT": .03, "SPOT_SNAG": .05, "Y_CROSS": .15, "DART_QUICK_DIG": .05, "DOUBLE_DIG": .12, "DEEP_CROSS": .15,
            "FLOOD": .08, "DOUBLE_POST": .08, "DIVIDE": .03, "PA_SLIDE": .25, "PA_FLOOD": .20,
            "WHAM": .15, "POWER_TOSS": .15, "PIN_PULL": .12, "BUCK_SWEEP": .15, "COUNTER_SWEEP": .12, "JET_ACTION": .05},
    # étape 6 — AXM : timing court / intermédiaire (Hitch, Snag, Choice, Levels, Y-Cross, dig) ; GLT : play action et
    # écrans pour profiter des terrains courts ; CPH : option, RPO, QB draw / sweep ; NVA : verticales et play action
    "AXM": {"HITCH": .20, "SPOT_SNAG": .20, "CHOICE": .25, "PIVOT": .15, "FL_SE_SCREEN": .15, "WR_TUNNEL_SCREEN": .15,
            "MESH_WHEEL": .20, "LEVELS": .20, "Y_CROSS": .20, "FLOOD": .10, "DART_QUICK_DIG": .20, "DOUBLE_DIG": .10,
            "DEEP_CROSS": .10, "DOUBLE_POST": .05, "DIVIDE": .05, "PA_SLIDE": .15, "PA_FLOOD": .10,
            "WHAM": .08, "JET_ACTION": .08, "RPO_READ": .08, "RPO_INSIDE_ZONE": .08, "POWER_TOSS": .10, "RPO_POWER": .05,
            "PIN_PULL": .10, "BUCK_SWEEP": .05, "COUNTER_SWEEP": .10, "QB_DRAW": .03},
    "GLT": {"HITCH": .08, "SPOT_SNAG": .08, "CHOICE": .10, "PIVOT": .05, "FL_SE_SCREEN": .20, "WR_TUNNEL_SCREEN": .15,
            "MESH_WHEEL": .15, "LEVELS": .10, "Y_CROSS": .10, "FLOOD": .15, "DART_QUICK_DIG": .10, "DOUBLE_DIG": .10,
            "DEEP_CROSS": .15, "DOUBLE_POST": .15, "DIVIDE": .10, "SWITCH_VERTICALS": .10, "PA_SLIDE": .20, "PA_FLOOD": .20,
            "WHAM": .05, "JET_ACTION": .10, "RPO_INSIDE_ZONE": .10, "RPO_ALERT": .05, "POWER_TOSS": .10, "POWER_READ": .05,
            "PIN_PULL": .08, "BUCK_SWEEP": .05, "END_AROUND": .05, "REVERSE": .03, "COUNTER_SWEEP": .10, "QB_DRAW": .05},
    "CPH": {"MIDLINE_OPTION": .12, "TRIPLE_OPTION": .10, "RPO_INSIDE_ZONE": .15, "RPO_READ": .10, "JET_ACTION": .10,
            "POWER_READ": .25, "INVERTED_VEER": .20, "RPO_POWER": .12, "SPEED_OPTION": .15, "QB_SWEEP": .10,
            "RPO_OUTSIDE_ZONE": .12, "END_AROUND": .08, "REVERSE": .05, "PIN_PULL": .05, "SHOVEL_OPTION": .20,
            "COUNTER_SWEEP": .15, "QB_DRAW": .30,
            "HITCH": .10, "SPOT_SNAG": .08, "CHOICE": .10, "FL_SE_SCREEN": .15, "WR_TUNNEL_SCREEN": .10, "MESH_WHEEL": .15,
            "LEVELS": .10, "FLOOD": .15, "Y_CROSS": .05, "DART_QUICK_DIG": .10, "DEEP_CROSS": .10, "DOUBLE_POST": .10,
            "DIVIDE": .05, "PA_SLIDE": .25, "PA_FLOOD": .20},
    "NVA": {"HITCH": .05, "SPOT_SNAG": .05, "CHOICE": .05, "FL_SE_SCREEN": .10, "WR_TUNNEL_SCREEN": .10, "MESH_WHEEL": .15,
            "LEVELS": .05, "Y_CROSS": .10, "FLOOD": .15, "DART_QUICK_DIG": .05, "DOUBLE_DIG": .15, "DEEP_CROSS": .25,
            "DOUBLE_POST": .25, "DIVIDE": .25, "SWITCH_VERTICALS": .25, "PA_SLIDE": .20, "PA_FLOOD": .25,
            "WHAM": .05, "JET_ACTION": .10, "RPO_ALERT": .10, "RPO_PEEK": .10, "POWER_TOSS": .08, "PIN_PULL": .08,
            "END_AROUND": .05, "REVERSE": .03, "COUNTER_SWEEP": .08},
    # palier 2 — PLS : petit lot de concepts rapides (écrans, Snag, Choice), RPO et zones ; ONX : équilibré, sûr ;
    # FRG : Duo / Power / Counter et play action de poche ; MRD : jeu court efficace, peu de risques
    "PLS": {"HITCH": .25, "SPOT_SNAG": .20, "CHOICE": .20, "PIVOT": .05, "FL_SE_SCREEN": .25, "WR_TUNNEL_SCREEN": .20,
            "MESH_WHEEL": .15, "LEVELS": .10, "Y_CROSS": .05, "FLOOD": .05, "DART_QUICK_DIG": .15, "DOUBLE_DIG": .05,
            "DEEP_CROSS": .05, "DOUBLE_POST": .05, "PA_SLIDE": .10, "PA_FLOOD": .05,
            "JET_ACTION": .10, "RPO_READ": .14, "RPO_INSIDE_ZONE": .20, "RPO_OUTSIDE_ZONE": .20, "RPO_ALERT": .08,
            "RPO_PEEK": .08, "POWER_TOSS": .05, "COUNTER_SWEEP": .05, "QB_DRAW": .05},
    "ONX": {"HITCH": .15, "SPOT_SNAG": .15, "CHOICE": .15, "PIVOT": .10, "FL_SE_SCREEN": .12, "WR_TUNNEL_SCREEN": .10,
            "MESH_WHEEL": .10, "LEVELS": .15, "Y_CROSS": .15, "FLOOD": .10, "DART_QUICK_DIG": .15, "DOUBLE_DIG": .10,
            "DEEP_CROSS": .10, "DOUBLE_POST": .05, "DIVIDE": .05, "PA_SLIDE": .20, "PA_FLOOD": .15,
            "WHAM": .08, "JET_ACTION": .08, "RPO_READ": .08, "RPO_INSIDE_ZONE": .08, "POWER_TOSS": .08,
            "PIN_PULL": .10, "BUCK_SWEEP": .05, "COUNTER_SWEEP": .10, "QB_DRAW": .03},
    "FRG": {"HITCH": .08, "CHOICE": .05, "FL_SE_SCREEN": .05, "WR_TUNNEL_SCREEN": .05, "MESH_WHEEL": .05, "LEVELS": .10,
            "PIVOT": .05, "SPOT_SNAG": .08, "Y_CROSS": .20, "DART_QUICK_DIG": .10, "DOUBLE_DIG": .15, "DEEP_CROSS": .15,
            "FLOOD": .10, "DOUBLE_POST": .08, "DIVIDE": .03, "PA_SLIDE": .30, "PA_FLOOD": .25,
            "WHAM": .20, "POWER_TOSS": .12, "PIN_PULL": .15, "BUCK_SWEEP": .15, "COUNTER_SWEEP": .15, "JET_ACTION": .03},
    "MRD": {"HITCH": .20, "CHOICE": .15, "FL_SE_SCREEN": .12, "WR_TUNNEL_SCREEN": .10, "MESH_WHEEL": .08, "LEVELS": .20,
            "PIVOT": .15, "SPOT_SNAG": .20, "Y_CROSS": .10, "DART_QUICK_DIG": .20, "DOUBLE_DIG": .12, "DEEP_CROSS": .05,
            "FLOOD": .12, "DOUBLE_POST": .03, "DIVIDE": .03, "PA_SLIDE": .15, "PA_FLOOD": .10,
            "WHAM": .10, "POWER_TOSS": .08, "PIN_PULL": .12, "BUCK_SWEEP": .08, "COUNTER_SWEEP": .08, "JET_ACTION": .05,
            "RPO_READ": .05, "RPO_INSIDE_ZONE": .05},
}
PART_MAX_ANCRE = 0.6

FORMATIONS_STYLE = {
    "CTX": {"GUN_TIGHT": .8, "GUN_Y_OFF": 1.2, "GUN_WING": .9, "GUN_STACK": .8, "GUN_QUADS": .5, "GUN_TRIPS_OPEN": 1.0,
            "GUN_TRIPS_TIGHT": .8, "GUN_FLEX": .9, "SINGLEBACK_BUNCH": .7, "SINGLEBACK_WING": .8, "SINGLEBACK_TIGHT": .6,
            "SINGLEBACK_DEUCE": .5, "SINGLEBACK_WING_PAIR": .5, "SINGLEBACK_NASTY": .6, "PISTOL_STRONG": 1.1,
            "PISTOL_WING": 1.1, "PISTOL_FULL_HOUSE": .7, "I_FORM_SLOT": .6, "I_FORM_WING": .6, "STRONG": .6, "WEAK": .5,
            "WILDCAT": .3},
    "VEC": {"GUN_TIGHT": 1.0, "GUN_Y_OFF": .6, "GUN_WING": .4, "GUN_STACK": 1.5, "GUN_QUADS": 1.4, "GUN_TRIPS_OPEN": 1.5,
            "GUN_TRIPS_TIGHT": 1.0, "GUN_FLEX": 1.0, "SINGLEBACK_BUNCH": .5, "SINGLEBACK_WING": .3, "SINGLEBACK_TIGHT": .2,
            "SINGLEBACK_DEUCE": .1, "SINGLEBACK_WING_PAIR": .1, "SINGLEBACK_NASTY": .4, "PISTOL_STRONG": .2,
            "PISTOL_WING": .4, "PISTOL_FULL_HOUSE": 0.0, "I_FORM_SLOT": .3, "I_FORM_WING": .1, "STRONG": .1, "WEAK": .1,
            "WILDCAT": 0.0},
    "AEG": {"GUN_TIGHT": 1.2, "GUN_Y_OFF": .9, "GUN_WING": .7, "GUN_STACK": .9, "GUN_QUADS": .6, "GUN_TRIPS_OPEN": .8,
            "GUN_TRIPS_TIGHT": 1.0, "GUN_FLEX": 1.1, "SINGLEBACK_BUNCH": 1.2, "SINGLEBACK_WING": 1.0,
            "SINGLEBACK_TIGHT": .9, "SINGLEBACK_DEUCE": .7, "SINGLEBACK_WING_PAIR": .6, "SINGLEBACK_NASTY": 1.0,
            "PISTOL_STRONG": .7, "PISTOL_WING": .8, "PISTOL_FULL_HOUSE": .4, "I_FORM_SLOT": .8, "I_FORM_WING": .7,
            "STRONG": .7, "WEAK": .6, "WILDCAT": .1},
    "MNL": {"GUN_TIGHT": .4, "GUN_Y_OFF": .5, "GUN_WING": .6, "GUN_STACK": .1, "GUN_QUADS": 0.0, "GUN_TRIPS_OPEN": .1,
            "GUN_TRIPS_TIGHT": .3, "GUN_FLEX": .2, "SINGLEBACK_BUNCH": .4, "SINGLEBACK_WING": 1.4, "SINGLEBACK_TIGHT": 1.4,
            "SINGLEBACK_DEUCE": 1.4, "SINGLEBACK_WING_PAIR": 1.2, "SINGLEBACK_NASTY": 1.0, "PISTOL_STRONG": 1.2,
            "PISTOL_WING": 1.0, "PISTOL_FULL_HOUSE": 1.3, "I_FORM_SLOT": .6, "I_FORM_WING": 1.5, "STRONG": 1.6,
            "WEAK": 1.3, "WILDCAT": .8},
    "AXM": {"GUN_TIGHT": 1.0, "GUN_Y_OFF": 1.0, "GUN_WING": .8, "GUN_STACK": 1.2, "GUN_QUADS": .6, "GUN_TRIPS_OPEN": 1.0,
            "GUN_TRIPS_TIGHT": 1.2, "GUN_FLEX": 1.1, "SINGLEBACK_BUNCH": 1.3, "SINGLEBACK_WING": 1.0,
            "SINGLEBACK_TIGHT": .7, "SINGLEBACK_DEUCE": .6, "SINGLEBACK_WING_PAIR": .6, "SINGLEBACK_NASTY": .8,
            "PISTOL_STRONG": .6, "PISTOL_WING": .7, "PISTOL_FULL_HOUSE": .3, "I_FORM_SLOT": .7, "I_FORM_WING": .5,
            "STRONG": .5, "WEAK": .5, "WILDCAT": 0.0},
    "GLT": {"GUN_TIGHT": .9, "GUN_Y_OFF": .9, "GUN_WING": .8, "GUN_STACK": .9, "GUN_QUADS": .7, "GUN_TRIPS_OPEN": 1.0,
            "GUN_TRIPS_TIGHT": .9, "GUN_FLEX": .9, "SINGLEBACK_BUNCH": .8, "SINGLEBACK_WING": .9, "SINGLEBACK_TIGHT": .8,
            "SINGLEBACK_DEUCE": .7, "SINGLEBACK_WING_PAIR": .6, "SINGLEBACK_NASTY": .7, "PISTOL_STRONG": .9,
            "PISTOL_WING": .9, "PISTOL_FULL_HOUSE": .6, "I_FORM_SLOT": .7, "I_FORM_WING": .7, "STRONG": .7, "WEAK": .6,
            "WILDCAT": .3},
    "CPH": {"GUN_TIGHT": 1.0, "GUN_Y_OFF": 1.2, "GUN_WING": 1.2, "GUN_STACK": .8, "GUN_QUADS": .5, "GUN_TRIPS_OPEN": 1.1,
            "GUN_TRIPS_TIGHT": .9, "GUN_FLEX": 1.0, "SINGLEBACK_BUNCH": .4, "SINGLEBACK_WING": .5, "SINGLEBACK_TIGHT": .3,
            "SINGLEBACK_DEUCE": .3, "SINGLEBACK_WING_PAIR": .3, "SINGLEBACK_NASTY": .4, "PISTOL_STRONG": 1.6,
            "PISTOL_WING": 1.6, "PISTOL_FULL_HOUSE": 1.2, "I_FORM_SLOT": .3, "I_FORM_WING": .3, "STRONG": .3, "WEAK": .3,
            "WILDCAT": .8},
    "NVA": {"GUN_TIGHT": .8, "GUN_Y_OFF": .8, "GUN_WING": .6, "GUN_STACK": 1.2, "GUN_QUADS": 1.2, "GUN_TRIPS_OPEN": 1.4,
            "GUN_TRIPS_TIGHT": .9, "GUN_FLEX": 1.0, "SINGLEBACK_BUNCH": .6, "SINGLEBACK_WING": .7, "SINGLEBACK_TIGHT": .6,
            "SINGLEBACK_DEUCE": .5, "SINGLEBACK_WING_PAIR": .4, "SINGLEBACK_NASTY": .7, "PISTOL_STRONG": .5,
            "PISTOL_WING": .5, "PISTOL_FULL_HOUSE": .2, "I_FORM_SLOT": .6, "I_FORM_WING": .5, "STRONG": .4, "WEAK": .4,
            "WILDCAT": 0.0},
    "PLS": {"GUN_TIGHT": 1.0, "GUN_Y_OFF": 1.0, "GUN_WING": 1.0, "GUN_STACK": 1.2, "GUN_QUADS": 1.0, "GUN_TRIPS_OPEN": 1.4,
            "GUN_TRIPS_TIGHT": 1.2, "GUN_FLEX": 1.2, "SINGLEBACK_BUNCH": .5, "SINGLEBACK_WING": .5, "SINGLEBACK_TIGHT": .3,
            "SINGLEBACK_DEUCE": .3, "SINGLEBACK_WING_PAIR": .3, "SINGLEBACK_NASTY": .3, "PISTOL_STRONG": .8,
            "PISTOL_WING": .8, "PISTOL_FULL_HOUSE": 0.0, "I_FORM_SLOT": .2, "I_FORM_WING": .2, "STRONG": .2, "WEAK": .2,
            "WILDCAT": 0.0},
    "ONX": {"GUN_TIGHT": 1.0, "GUN_Y_OFF": 1.0, "GUN_WING": .8, "GUN_STACK": .9, "GUN_QUADS": .6, "GUN_TRIPS_OPEN": .9,
            "GUN_TRIPS_TIGHT": 1.0, "GUN_FLEX": 1.0, "SINGLEBACK_BUNCH": 1.0, "SINGLEBACK_WING": 1.0,
            "SINGLEBACK_TIGHT": .9, "SINGLEBACK_DEUCE": .8, "SINGLEBACK_WING_PAIR": .7, "SINGLEBACK_NASTY": .9,
            "PISTOL_STRONG": .8, "PISTOL_WING": .8, "PISTOL_FULL_HOUSE": .5, "I_FORM_SLOT": .8, "I_FORM_WING": .7,
            "STRONG": .7, "WEAK": .6, "WILDCAT": .2},
    "FRG": {"GUN_TIGHT": .6, "GUN_Y_OFF": .6, "GUN_WING": .7, "GUN_STACK": .3, "GUN_QUADS": 0.0, "GUN_TRIPS_OPEN": .3,
            "GUN_TRIPS_TIGHT": .5, "GUN_FLEX": .4, "SINGLEBACK_BUNCH": .6, "SINGLEBACK_WING": 1.3, "SINGLEBACK_TIGHT": 1.4,
            "SINGLEBACK_DEUCE": 1.3, "SINGLEBACK_WING_PAIR": 1.1, "SINGLEBACK_NASTY": 1.2, "PISTOL_STRONG": 1.0,
            "PISTOL_WING": .9, "PISTOL_FULL_HOUSE": 1.0, "I_FORM_SLOT": .7, "I_FORM_WING": 1.3, "STRONG": 1.4,
            "WEAK": 1.1, "WILDCAT": .2},
    "MRD": {"GUN_TIGHT": 1.1, "GUN_Y_OFF": .9, "GUN_WING": .8, "GUN_STACK": .8, "GUN_QUADS": .4, "GUN_TRIPS_OPEN": .7,
            "GUN_TRIPS_TIGHT": .9, "GUN_FLEX": 1.0, "SINGLEBACK_BUNCH": 1.1, "SINGLEBACK_WING": 1.1, "SINGLEBACK_TIGHT": 1.0,
            "SINGLEBACK_DEUCE": .8, "SINGLEBACK_WING_PAIR": .7, "SINGLEBACK_NASTY": 1.0, "PISTOL_STRONG": .8,
            "PISTOL_WING": .8, "PISTOL_FULL_HOUSE": .5, "I_FORM_SLOT": .8, "I_FORM_WING": .8, "STRONG": .8, "WEAK": .7,
            "WILDCAT": 0.0},
}
# concepts qu'une franchise ne joue pas (identité) — en plus des parts nulles
#   MNL : courses toujours confiées à ses RB (rotation RB1 / RB2 du coordinateur) : ni QB, ni receveur, ni option, ni RPO
#   VEC : pas d'option (son QB reste dans la poche), pas de wildcat
_PORTEUR_NON_RB = {c for c, d in CONCEPTS.items() if d.get("porteur_course") or d.get("option")}
EXCLUS_CONCEPTS = {
    "MNL": _PORTEUR_NON_RB | {c for c, d in CONCEPTS.items() if d.get("rpo")} | {"JET_SWEEP"},
    "VEC": {c for c, d in CONCEPTS.items() if d.get("option")} | {"QB_SWEEP"},
    "AEG": {"TRIPLE_OPTION", "SPEED_OPTION", "MIDLINE_OPTION", "SHOVEL_OPTION", "QB_SWEEP"},
    "CTX": set(),
    #   étape 6 — NVA : son QB reste dans la poche (bras, lecture des safeties) ; AXM : pas d'option lourde ; CPH : tout
    "AXM": {"TRIPLE_OPTION", "SPEED_OPTION", "MIDLINE_OPTION", "SHOVEL_OPTION", "QB_SWEEP"},
    "GLT": {"TRIPLE_OPTION"},
    "CPH": set(),
    "NVA": {c for c, d in CONCEPTS.items() if d.get("option")} | {"QB_SWEEP"},
    #   palier 2 — FRG : QB de poche, courses aux RB (ni option, ni QB) ; ONX / MRD : pas d'option lourde ; PLS : RPO,
    #   lectures rapides, pas d'option triple
    "PLS": {"TRIPLE_OPTION", "MIDLINE_OPTION", "QB_SWEEP"},
    "ONX": {"TRIPLE_OPTION", "SPEED_OPTION", "MIDLINE_OPTION", "SHOVEL_OPTION", "QB_SWEEP"},
    "FRG": {c for c, d in CONCEPTS.items() if d.get("option")} | {"QB_SWEEP", "QB_DRAW", "RPO_READ", "RPO_PEEK"},
    "MRD": {"TRIPLE_OPTION", "SPEED_OPTION", "MIDLINE_OPTION", "SHOVEL_OPTION", "QB_SWEEP"},
}
EXCLUS_FORMATIONS = {"VEC": {"WILDCAT", "PISTOL_FULL_HOUSE"}, "MNL": {"GUN_QUADS"}, "AEG": set(), "CTX": set(),
                     "AXM": {"WILDCAT"}, "GLT": set(), "CPH": set(), "NVA": {"WILDCAT"},
                     "PLS": {"WILDCAT", "PISTOL_FULL_HOUSE"}, "ONX": set(), "FRG": {"GUN_QUADS"}, "MRD": set()}


def exclu(abbr, play_id):
    f, c = PLAYS[play_id]
    return c in EXCLUS_CONCEPTS.get(abbr, set()) or f in EXCLUS_FORMATIONS.get(abbr, set())


def parts_par_ancre(abbr):
    out = {}
    for c, p in PARTS.get(abbr, {}).items():
        a = CONCEPTS[c]["ancre"]
        out[a] = out.get(a, 0.0) + p
    return out


# =====================================================================================================================
# 6. FEUILLE D'APPEL — situations (mêmes clés que PB_SITUATIONS du notebook) et enchaînements (§25-26)
# =====================================================================================================================
_DEEP = ("DEEP_CROSS", "DOUBLE_POST", "DIVIDE", "SWITCH_VERTICALS")
_OPT = ("POWER_READ", "INVERTED_VEER", "MIDLINE_OPTION", "TRIPLE_OPTION", "SPEED_OPTION", "SHOVEL_OPTION")
_RPO = ("RPO_INSIDE_ZONE", "RPO_READ", "RPO_ALERT", "RPO_PEEK", "RPO_POWER", "RPO_OUTSIDE_ZONE")
_TRICK = {"END_AROUND": .5, "REVERSE": .3, "DOUBLE_REVERSE": .2}


def _m(base, **kw):
    d = dict(base)
    d.update(kw)
    return d


SITUATIONS = {
    "short": _m({c: 1.2 for c in _RPO}, WHAM=1.4, POWER_TOSS=1.0, PIN_PULL=.8, BUCK_SWEEP=.9, COUNTER_SWEEP=.8,
                QB_DRAW=.7, QB_SWEEP=.8, POWER_READ=1.4, INVERTED_VEER=1.3, MIDLINE_OPTION=1.4, TRIPLE_OPTION=1.2,
                SPEED_OPTION=.8, SHOVEL_OPTION=1.3, HITCH=1.3, CHOICE=1.2, SPOT_SNAG=1.2, PIVOT=1.2, DART_QUICK_DIG=1.2,
                Y_CROSS=.7, DEEP_CROSS=.4, FLOOD=.7, DOUBLE_POST=.4, DIVIDE=.5, SWITCH_VERTICALS=.5, PA_SLIDE=1.4,
                PA_FLOOD=1.2, FL_SE_SCREEN=.6, WR_TUNNEL_SCREEN=.6, **_TRICK,
                **{"@SINGLEBACK_TIGHT": 1.4, "@SINGLEBACK_DEUCE": 1.3, "@PISTOL_FULL_HOUSE": 1.5, "@STRONG": 1.4,
                   "@WEAK": 1.2, "@WILDCAT": 1.5, "@I_FORM_WING": 1.3, "@GUN_QUADS": .4, "@GUN_STACK": .7}),
    "long": _m({c: .7 for c in _RPO + _OPT}, QB_DRAW=1.6, FL_SE_SCREEN=1.3, WR_TUNNEL_SCREEN=1.4, FLOOD=1.4,
               Y_CROSS=1.4, DEEP_CROSS=1.3, DOUBLE_POST=1.3, DIVIDE=1.3, SWITCH_VERTICALS=1.3, MESH_WHEEL=1.2, LEVELS=1.2,
               DOUBLE_DIG=1.3, HITCH=.8, PIVOT=.9, SPOT_SNAG=.8, WHAM=.6, POWER_TOSS=.6, PIN_PULL=.7, BUCK_SWEEP=.7,
               COUNTER_SWEEP=.8, PA_SLIDE=.7, PA_FLOOD=.7,
               **{"@GUN_QUADS": 1.4, "@GUN_TRIPS_OPEN": 1.3, "@GUN_STACK": 1.2, "@PISTOL_FULL_HOUSE": .3, "@STRONG": .5,
                  "@WEAK": .5, "@WILDCAT": .2, "@SINGLEBACK_TIGHT": .5}),
    "red_zone": _m({c: .5 for c in _DEEP}, SPOT_SNAG=1.3, CHOICE=1.3, PIVOT=1.2, MESH_WHEEL=1.3, HITCH=1.1, FLOOD=1.1,
                   SWITCH_VERTICALS=.7, DEEP_CROSS=.6, Y_CROSS=.8, QB_DRAW=1.2, QB_SWEEP=1.2, POWER_READ=1.3,
                   INVERTED_VEER=1.2, PA_SLIDE=1.3, PA_FLOOD=1.2, FL_SE_SCREEN=.8, WR_TUNNEL_SCREEN=.7,
                   **{"@GUN_STACK": 1.3, "@SINGLEBACK_BUNCH": 1.3, "@GUN_TIGHT": 1.2, "@GUN_QUADS": 1.1,
                      "@SINGLEBACK_TIGHT": 1.2}),
    "goal_line": _m({c: .2 for c in _DEEP}, WHAM=1.5, POWER_TOSS=1.2, QB_DRAW=1.0, POWER_READ=1.4, INVERTED_VEER=1.3,
                    MIDLINE_OPTION=1.4, TRIPLE_OPTION=1.2, SHOVEL_OPTION=1.4, PA_SLIDE=1.6, PA_FLOOD=1.3, SPOT_SNAG=1.2,
                    CHOICE=1.2, PIVOT=1.2, FL_SE_SCREEN=.4, WR_TUNNEL_SCREEN=.4, END_AROUND=.6, REVERSE=.3,
                    DOUBLE_REVERSE=.2,
                    **{"@PISTOL_FULL_HOUSE": 1.8, "@WILDCAT": 1.6, "@SINGLEBACK_TIGHT": 1.6, "@SINGLEBACK_DEUCE": 1.5,
                       "@STRONG": 1.5, "@GUN_QUADS": .2, "@GUN_STACK": .8}),
    "backed_up": _m({c: .7 for c in _OPT}, REVERSE=.3, DOUBLE_REVERSE=.2, END_AROUND=.5, PA_SLIDE=.7, PA_FLOOD=.7,
                    FL_SE_SCREEN=.6, WR_TUNNEL_SCREEN=.6, WHAM=1.2, POWER_TOSS=1.1,
                    **{"@STRONG": 1.2, "@I_FORM_WING": 1.2, "@GUN_QUADS": .6, "@WILDCAT": .5}),
    "first_down": _m({c: 1.2 for c in _RPO}, PA_SLIDE=1.3, PA_FLOOD=1.3, JET_ACTION=1.2),
}

# relations entre concepts (§25) : (préparation, suite, type). Un concept de PRÉPARATION appelé récemment rend la SUITE
# un peu plus probable ; si la défense l'a vu au moins deux fois, la suite profite d'une petite réponse défensive
# (linebackers qui fondent sur la course, bord qui ferme) : « A PEUT créer la réponse X, B est UNE réponse possible ».
RELATIONS = [
    ("INSIDE_RUN", "BOOT", "SETUP"), ("INSIDE_RUN", "PLAY_ACTION", "SETUP"), ("INSIDE_RUN", "PA_SLIDE", "SETUP"),
    ("OUTSIDE_RUN", "PLAY_ACTION", "SETUP"), ("OUTSIDE_RUN", "PA_FLOOD", "SETUP"), ("OUTSIDE_RUN", "COUNTER", "COUNTER"),
    ("POWER", "COUNTER", "COUNTER"), ("POWER", "POWER_READ", "CONSTRAINT"), ("POWER", "RPO_POWER", "CONSTRAINT"),
    ("COUNTER", "POWER", "SEQUENCE"), ("JET_SWEEP", "INSIDE_RUN", "COMPLEMENT"), ("JET_SWEEP", "JET_ACTION", "COMPLEMENT"),
    ("JET_SWEEP", "BOOT", "SETUP"), ("JET_ACTION", "BOOT", "SETUP"), ("INSIDE_RUN", "RPO_INSIDE_ZONE", "CONSTRAINT"),
    ("RPO_INSIDE_ZONE", "COUNTER", "SEQUENCE"), ("OUTSIDE_RUN", "REVERSE", "COUNTER"), ("JET_SWEEP", "END_AROUND", "COUNTER"),
    ("QUICK_SLANT", "PIVOT", "CHANGEUP"), ("STICK", "PIVOT", "CHANGEUP"), ("SCREEN", "QB_DRAW", "CHANGEUP"),
    ("PIN_PULL", "PA_FLOOD", "SETUP"), ("BUCK_SWEEP", "COUNTER_SWEEP", "COUNTER"),
]
SEQUENCE = {"fenetre_appel": 4, "bonus_appel": 1.2, "fenetre_vu": 8, "vu_min": 2, "course": 0.3, "passe": 0.12}


PREPARATIONS = {}                     # suite -> concepts qui la préparent
for _a, _b, _t in RELATIONS:
    PREPARATIONS.setdefault(_b, []).append(_a)


def suites(concept):
    return [(b, t) for a, b, t in RELATIONS if a == concept]


def enchainement(concept, recents_appel, recents_defense):
    """(multiplicateur d'appel, réponse défensive) d'un concept selon ce que l'attaque vient d'appeler et ce que la
    défense a vu (listes de concepts, du plus ancien au plus récent)."""
    preps = PREPARATIONS.get(concept)
    if not preps:
        return 1.0, None
    m = SEQUENCE["bonus_appel"] if any(c in preps for c in recents_appel[-SEQUENCE["fenetre_appel"]:]) else 1.0
    vus = recents_defense[-SEQUENCE["fenetre_vu"]:]
    prep = max(preps, key=lambda a: vus.count(a))
    return m, (prep if vus.count(prep) >= SEQUENCE["vu_min"] else None)


# =====================================================================================================================
# 7. MOTIONS et SHIFTS (§05) — de l'information, pas une certitude
# =====================================================================================================================
MOTIONS = {
    # homme / zone : (déguisement retiré, séparation du joueur en motion) ; course : yards par classe de course
    "JET":    {"homme": (0.35, 0.15), "zone": (0.15, 0.0), "role": "WR3",
               "course": {"outside": 0.4, "perimeter": 0.5, "inside": 0.2, "option": 0.3, "gap": 0.1, "qb": 0.2}},
    "ORBIT":  {"homme": (0.30, 0.10), "zone": (0.10, 0.0), "role": "WR3",
               "course": {"option": 0.4, "inside": 0.3, "outside": 0.1, "gap": 0.1}},
    "ACROSS": {"homme": (0.40, 0.20), "zone": (0.10, 0.0), "role": "WR3", "course": {"inside": 0.1}},
    "RETURN": {"homme": (0.25, 0.25), "zone": (0.0, 0.0), "role": "WR3", "course": {}},
    "TRADE":  {"homme": (0.10, 0.0), "zone": (0.10, 0.0), "role": "TE", "course": {"gap": 0.2, "inside": 0.2}},
}
# probabilité de motion par concept (sinon pas de motion) ; les concepts existants n'en ont pas
MOTION_CONCEPT = {
    "JET_ACTION": {"JET": 1.0}, "WILDCAT_JET": {"JET": 1.0},
    **{c: {"JET": .3, "ORBIT": .2} for c in _RPO},
    **{c: {"ORBIT": .35} for c in _OPT},
    "END_AROUND": {"JET": .5}, "REVERSE": {"JET": .6}, "DOUBLE_REVERSE": {"JET": .6},
    "MESH_WHEEL": {"ACROSS": .4}, "CHOICE": {"RETURN": .25, "ACROSS": .2}, "PIVOT": {"RETURN": .3},
    "SPOT_SNAG": {"ACROSS": .25}, "LEVELS": {"ACROSS": .2}, "Y_CROSS": {"TRADE": .2}, "DEEP_CROSS": {"JET": .25},
    "PA_SLIDE": {"JET": .3, "TRADE": .15}, "PA_FLOOD": {"JET": .25, "TRADE": .15}, "FLOOD": {"ACROSS": .2},
    "HITCH": {"RETURN": .15}, "DOUBLE_DIG": {"TRADE": .2}, "SWITCH_VERTICALS": {"ACROSS": .2},
    "WHAM": {"TRADE": .3}, "POWER_TOSS": {"TRADE": .2}, "BUCK_SWEEP": {"JET": .2}, "COUNTER_SWEEP": {"ORBIT": .3},
    "PIN_PULL": {"JET": .2},
}
SHIFT_EFFET = {"course": 0.2, "deguisement": 0.10}


def choisir_motion(play_id, graine, n):
    """Motion du play (ou None), dans son flux."""
    f, c = PLAYS.get(play_id, (None, None))
    if c is None:
        return None
    table = MOTION_CONCEPT.get("WILDCAT_JET" if (f == "WILDCAT" and c == "JET_SWEEP") else c)
    if not table:
        return None
    r = flux(FLUX["motion"], graine, n).random()
    for m, p in sorted(table.items()):
        r -= p
        if r < 0:
            return m
    return None


def choisir_shift(formation, graine, n):
    depuis = SHIFT_DEPUIS.get(formation)
    if not depuis:
        return None
    return depuis if flux(FLUX["shift"], graine, n).random() < P_SHIFT else None


# =====================================================================================================================
# 8. PROTECTIONS (§11) — appelées avec chaque nouveau play de passe
# =====================================================================================================================
# poche : secondes gagnées ; rusher5 : part d'un 5e rusher ramassée ; retire : rôles qui restent bloquer ;
# retard : rôle dont la route part plus tard (chip)
PROTECTIONS = {
    "FIVE_MAN":       {"poche": -0.05, "rusher5": 0.0,  "retire": ()},
    "HALF_SLIDE":     {"poche": 0.0,   "rusher5": 0.05, "retire": ()},
    "FULL_SLIDE":     {"poche": 0.03,  "rusher5": 0.0,  "retire": ()},
    "MAN_PROTECTION": {"poche": 0.0,   "rusher5": 0.08, "retire": ()},
    "SCAT":           {"poche": 0.05,  "rusher5": 0.10, "retire": ()},
    "SIX_MAN":        {"poche": 0.10,  "rusher5": 0.15, "retire": ("RB",)},
    "SEVEN_MAN_MAX":  {"poche": 0.25,  "rusher5": 0.25, "retire": ("RB", "TE")},
    "CHIP":           {"poche": 0.08,  "rusher5": 0.05, "retire": (), "retard": ("RB", 0.4)},
}
# protection × pression : secondes (le slide vers l'overload le ramasse, l'homme gère mieux les croisements…)
PROTECTION_VS = {
    ("FULL_SLIDE", "OVERLOAD_BLITZ"): 0.10, ("FULL_SLIDE", "CROSS_DOG"): -0.10, ("HALF_SLIDE", "EDGE_BLITZ"): 0.05,
    ("MAN_PROTECTION", "CROSS_DOG"): 0.05, ("MAN_PROTECTION", "SIM_PRESSURE"): -0.08, ("FIVE_MAN", "SEVEN_MAN_PRESSURE"): -0.15,
    ("SCAT", "A_GAP_BLITZ"): 0.08, ("SIX_MAN", "MUG_BLITZ"): 0.08, ("CHIP", "EDGE_BLITZ"): 0.08, ("CHIP", "EDGE_RUSH"): 0.06,
    ("HALF_SLIDE", "ET_STUNT"): 0.04, ("FULL_SLIDE", "TEX_STUNT"): 0.04, ("MAN_PROTECTION", "TEX_STUNT"): -0.06,
}


def protection(concept):
    """Protection appelée avec un nouveau concept de passe (aucune pour les concepts existants)."""
    d = CONCEPTS.get(concept) or {}
    if d.get("famille") != P:
        return None
    if d.get("rpo_de") or concept in ("FL_SE_SCREEN", "WR_TUNNEL_SCREEN", "HITCH", "CHOICE"):
        return "FIVE_MAN"
    if concept in ("SWITCH_VERTICALS", "DIVIDE", "DOUBLE_POST"):
        return "SEVEN_MAN_MAX" if concept == "DOUBLE_POST" else "SIX_MAN"
    if d.get("pa"):
        return "FULL_SLIDE" if concept == "PA_SLIDE" else "SIX_MAN"
    if concept in ("DEEP_CROSS", "Y_CROSS"):
        return "CHIP"
    if concept in ("MESH_WHEEL", "SPOT_SNAG", "PIVOT"):
        return "SCAT"
    if concept in ("LEVELS", "FLOOD", "DOUBLE_DIG"):
        return "HALF_SLIDE"
    return "MAN_PROTECTION"


# =====================================================================================================================
# 9. DÉFENSE — paquets (couvertures, pressions, présentations), jeux de rush, fronts, mouvements
# =====================================================================================================================
# paquet : (concept(s) de base du coordinateur, famille, [(coquille, poids)], rushers, présentation, effets)
#   effets : deguisement (erreurs de lecture du QB en plus, ×(1+x)) · poche (s) · court (séparation des routes courtes) ·
#            vide {rôle: séparation} (le défenseur qui blitze laisse son receveur) · scramble (×) · profond (séparation)
PAQUETS = {
    # ---- homme ----
    "PRESS_MAN":       ("MAN", "homme", [("Cover 1 Press", 1.0)], 4, "1-high, press", {}),
    "OFF_MAN":         ("MAN", "homme", [("Cover 1 Off", 1.0)], 4, "1-high, off", {}),
    "COVER_1_ROBBER":  ("MAN", "homme", [("Cover 1 Robber", 1.0)], 4, "2-high rotating", {"deguisement": 0.25}),
    "COVER_2_MAN":     ("MAN", "homme", [("Cover 2 Man", 1.0)], 4, "2-high", {}),
    "BANJO":           ("MAN", "homme", [("Banjo", 1.0)], 4, "1-high", {}),
    "GREEN_DOG":       ("MAN", "homme", [("Cover 1", 1.0)], 4, "1-high", {"poche": -0.10}),
    # ---- zone ----
    "TAMPA_2":         ("COVER_2", "zone", [("Tampa 2", 1.0)], 4, "2-high", {}),
    "COVER_2_SINK":    ("COVER_2", "zone", [("Cover 2 Sink", 1.0)], 4, "2-high", {}),
    "COVER_3_SKY":     (("COVER_3", "ZONE"), "zone", [("Cover 3 Sky", 1.0)], 4, "2-high rotating", {"deguisement": 0.20}),
    "COVER_3_BUZZ":    (("COVER_3", "ZONE"), "zone", [("Cover 3 Buzz", 1.0)], 4, "2-high rotating", {"deguisement": 0.20}),
    "COVER_3_MATCH":   (("COVER_3", "ZONE"), "zone", [("Cover 3 Match", 1.0)], 4, "1-high", {}),
    "MATCH_QUARTERS":  ("COVER_4", "zone", [("Match Quarters", 1.0)], 4, "2-high", {}),
    "PALMS":           ("COVER_4", "zone", [("Palms", 1.0)], 4, "2-high", {}),
    "COVER_6":         ("COVER_4", "zone", [("Cover 6", 1.0)], 4, "2-high", {}),
    "COVER_8":         ("COVER_4", "zone", [("Cover 8", 1.0)], 4, "2-high", {}),
    # ---- pression présentée, pas jouée (4 rushers) ----
    "SIM_PRESSURE":    (("ZONE", "COVER_3"), "zone", [("Cover 3", 1.0)], 4, "mug", {"deguisement": 0.35, "court": -0.20}),
    "CREEPER":         (("ZONE", "COVER_3"), "zone", [("Cover 3", 0.6), ("Cover 2", 0.4)], 4, "mug", {"deguisement": 0.30, "court": -0.15}),
    "MUG_DROP":        ("ZONE", "zone", [("Cover 2", 0.5), ("Cover 3", 0.5)], 4, "double A-gap mug", {"deguisement": 0.35, "court": -0.10}),
    "EXCHANGE_PRESSURE": ("ZONE", "zone", [("Cover 3", 1.0)], 4, "mug", {"deguisement": 0.25, "poche": -0.10}),
    # ---- vraie pression ----
    "FIRE_ZONE":       ("BLITZ", "zone", [("Fire Zone", 1.0)], 5, "1-high", {"court": -0.10}),
    "COVER_2_FIRE":    ("BLITZ", "zone", [("Cover 2 Fire", 1.0)], 5, "2-high", {}),
    "SEVEN_MAN_PRESSURE": ("BLITZ", "homme", [("Cover 0", 1.0)], 7, "0-high", {"poche": -0.45}),
    "MUG_BLITZ":       ("BLITZ", "homme", [("Cover 1", 0.6), ("Cover 0", 0.4)], 5, "double A-gap mug", {"deguisement": 0.20, "poche": -0.15}),
    "OVERLOAD_BLITZ":  ("BLITZ", "homme", [("Cover 1", 0.7), ("Cover 0", 0.3)], 5, "1-high", {"poche": -0.20}),
    "A_GAP_BLITZ":     ("BLITZ", "homme", [("Cover 1", 1.0)], 5, "1-high", {"poche": -0.25, "scramble": 1.3}),
    "B_GAP_BLITZ":     ("BLITZ", "homme", [("Cover 1", 1.0)], 5, "1-high", {"poche": -0.20, "scramble": 1.2}),
    "EDGE_BLITZ":      ("BLITZ", "homme", [("Cover 1", 1.0)], 5, "1-high", {"poche": -0.10, "scramble": 0.7}),
    "CORNER_BLITZ":    ("BLITZ", "homme", [("Cover 1", 1.0)], 5, "1-high", {"poche": -0.15, "vide": {"WR1": 0.6}}),
    "SAFETY_BLITZ":    ("BLITZ", "homme", [("Cover 1", 1.0)], 5, "2-high rotating", {"poche": -0.10, "profond": 0.3, "deguisement": 0.15}),
    "NICKEL_BLITZ":    ("BLITZ", "homme", [("Cover 1", 1.0)], 5, "1-high", {"poche": -0.15, "vide": {"WR3": 0.5}}),
    "CROSS_DOG":       ("BLITZ", "homme", [("Cover 1", 1.0)], 5, "1-high", {"poche": -0.20, "deguisement": 0.10}),
    # ---- contre la course (appel BOX_STACK) ----
    "BOX_ROBBER":      ("BOX_STACK", "homme", [("Cover 1 Robber", 1.0)], 4, "1-high", {}),
    "BOX_SKY":         ("BOX_STACK", "zone", [("Cover 3 Sky", 1.0)], 4, "1-high, safety down", {}),
}
# les deux derniers sont des variantes d'appel BOX_STACK : mêmes coquilles que COVER_1_ROBBER / COVER_3_SKY
ALIAS["concepts"].update({"BOX_ROBBER": "COVER_1_ROBBER contre la course", "BOX_SKY": "COVER_3_SKY contre la course"})

# nouvelles coquilles : avantage des routes par classe, routes qui attaquent leur faiblesse, probabilité d'un double
COQUILLES = {
    "Cover 1 Press":  ({"court": -0.2, "moyen": 0.2, "profond": -0.2},
                       {"FADE": 0.4, "GO": 0.3, "QUICK_SLANT": 0.3, "HITCH": -0.3, "STICK": -0.2}, 0.12),
    "Cover 1 Off":    ({"court": 0.4, "moyen": 0.0, "profond": -0.5},
                       {"HITCH": 0.5, "STICK": 0.4, "OUT": 0.3, "COMEBACK": 0.4, "CURL": 0.3}, 0.12),
    "Cover 1 Robber": ({"court": 0.1, "moyen": -0.1, "profond": -0.4},
                       {"DIG": -0.3, "CROSS": -0.3, "IN": -0.2, "DRAG": 0.4, "SLANT": 0.3, "QUICK_SLANT": 0.3,
                        "WHEEL": 0.4, "FADE": 0.2}, 0.08),
    "Cover 2 Man":    ({"court": -0.1, "moyen": 0.0, "profond": -0.7},
                       {"DRAG": 0.5, "CROSS": 0.4, "WHEEL": 0.2, "SEAM": -0.3, "POST": -0.2, "CHOICE": 0.4,
                        "DEEP_CROSS": 0.3}, 0.20),
    "Banjo":          ({"court": 0.0, "moyen": 0.1, "profond": -0.4},
                       {"DRAG": -0.4, "CROSS": -0.3, "WHEEL": -0.3, "ARROW": -0.2, "PIVOT": -0.2, "CORNER": 0.2}, 0.10),
    "Tampa 2":        ({"court": 0.2, "moyen": 0.3, "profond": -0.4},
                       {"CORNER": 0.8, "FLAG": 0.7, "OUT": 0.3, "HITCH": 0.3, "FLAT": 0.2, "DIG": -0.2,
                        "DEEP_CROSS": 0.2}, 0.20),
    "Cover 2 Sink":   ({"court": 0.4, "moyen": 0.4, "profond": -0.3},
                       {"CORNER": 0.2, "FLAG": 0.2, "FLAT": 0.5, "OUT": 0.4, "SEAM": 0.6, "POST": 0.5}, 0.22),
    "Cover 3 Sky":    ({"court": 0.4, "moyen": 0.2, "profond": -0.6},
                       {"OUT": 0.1, "SEAM": 0.6, "CURL": 0.4, "DIG": 0.3}, 0.08),
    "Cover 3 Buzz":   ({"court": 0.5, "moyen": 0.1, "profond": -0.6},
                       {"FLAT": 0.4, "SEAM": 0.3, "CURL": 0.2, "OUT": 0.4, "ARROW": 0.3}, 0.08),
    "Cover 3 Match":  ({"court": 0.4, "moyen": 0.1, "profond": -0.7},
                       {"SEAM": -0.1, "FLAT": 0.2, "CURL": 0.2, "OUT": 0.2, "DIG": 0.2, "CROSS": 0.2}, 0.10),
    "Match Quarters": ({"court": 0.7, "moyen": 0.0, "profond": -0.9},
                       {"DRAG": 0.3, "POST": -0.2, "FLAT": 0.3, "OUT": 0.3, "CURL": 0.1}, 0.26),
    "Palms":          ({"court": 0.5, "moyen": 0.1, "profond": -0.8},
                       {"OUT": -0.2, "FLAT": -0.1, "DIG": 0.4, "CURL": 0.2, "SEAM": 0.2}, 0.24),
    "Cover 6":        ({"court": 0.6, "moyen": 0.3, "profond": -0.7},
                       {"CORNER": 0.4, "FLAG": 0.3, "DIG": 0.2, "SEAM": 0.3, "CURL": 0.1}, 0.24),
    "Cover 8":        ({"court": 0.6, "moyen": 0.2, "profond": -0.75},
                       {"CORNER": 0.3, "FLAG": 0.4, "DIG": 0.3, "SEAM": 0.2, "OUT": 0.2}, 0.24),
    "Fire Zone":      ({"court": 0.6, "moyen": 0.3, "profond": -0.6},
                       {"QUICK_SLANT": 0.2, "HITCH": 0.3, "SEAM": 0.5, "FLAT": 0.3, "STICK": 0.2}, 0.0),
    "Cover 2 Fire":   ({"court": 0.6, "moyen": 0.6, "profond": -0.2},
                       {"CORNER": 0.5, "SEAM": 0.5, "FLAG": 0.4, "HITCH": 0.3}, 0.0),
}
# coquilles qui jouent comme une couverture existante pour les affectations en homme (bloc A / C)
COQUILLE_HOMME = {"Cover 1 Press": "Cover 1", "Cover 1 Off": "Cover 1", "Cover 1 Robber": "Cover 1",
                  "Cover 2 Man": "Cover 1", "Banjo": "Cover 1"}

# part des appels d'un concept de base transformés en paquet, par franchise (le reste : l'appel de base, comme avant)
PAQUETS_STYLE = {
    "CTX": {"MAN": {"PRESS_MAN": .15, "OFF_MAN": .15, "COVER_1_ROBBER": .20, "COVER_2_MAN": .15, "GREEN_DOG": .05},
            "ZONE": {"SIM_PRESSURE": .10, "CREEPER": .05, "MUG_DROP": .05, "EXCHANGE_PRESSURE": .05, "COVER_3_SKY": .15,
                     "COVER_3_BUZZ": .10, "COVER_3_MATCH": .15},
            "COVER_2": {"TAMPA_2": .20, "COVER_2_SINK": .10},
            "COVER_3": {"COVER_3_SKY": .15, "COVER_3_BUZZ": .10, "COVER_3_MATCH": .20, "SIM_PRESSURE": .10, "CREEPER": .05},
            "COVER_4": {"MATCH_QUARTERS": .25, "PALMS": .15, "COVER_6": .20, "COVER_8": .10},
            "BLITZ": {"FIRE_ZONE": .20, "COVER_2_FIRE": .10, "MUG_BLITZ": .10, "OVERLOAD_BLITZ": .10, "A_GAP_BLITZ": .05,
                      "EDGE_BLITZ": .05, "CORNER_BLITZ": .05, "SAFETY_BLITZ": .05, "NICKEL_BLITZ": .05, "CROSS_DOG": .05,
                      "SEVEN_MAN_PRESSURE": .02},
            "BOX_STACK": {"BOX_SKY": .20, "BOX_ROBBER": .20}},
    "VEC": {"MAN": {"PRESS_MAN": .35, "OFF_MAN": .05, "COVER_1_ROBBER": .15, "COVER_2_MAN": .15, "GREEN_DOG": .10},
            "ZONE": {"SIM_PRESSURE": .10, "CREEPER": .10, "MUG_DROP": .10, "EXCHANGE_PRESSURE": .05, "COVER_3_SKY": .10,
                     "COVER_3_BUZZ": .05, "COVER_3_MATCH": .05},
            "COVER_2": {"TAMPA_2": .10, "COVER_2_SINK": .05},
            "COVER_3": {"COVER_3_SKY": .10, "COVER_3_BUZZ": .05, "COVER_3_MATCH": .05, "SIM_PRESSURE": .10, "CREEPER": .10},
            "COVER_4": {"MATCH_QUARTERS": .15, "PALMS": .05, "COVER_6": .10, "COVER_8": .05},
            "BLITZ": {"FIRE_ZONE": .15, "COVER_2_FIRE": .05, "MUG_BLITZ": .15, "OVERLOAD_BLITZ": .10, "A_GAP_BLITZ": .08,
                      "B_GAP_BLITZ": .05, "EDGE_BLITZ": .05, "CORNER_BLITZ": .08, "SAFETY_BLITZ": .06, "NICKEL_BLITZ": .08,
                      "CROSS_DOG": .06, "SEVEN_MAN_PRESSURE": .05},
            "BOX_STACK": {"BOX_ROBBER": .20, "BOX_SKY": .10}},
    "AEG": {"MAN": {"PRESS_MAN": .05, "OFF_MAN": .25, "COVER_1_ROBBER": .10, "COVER_2_MAN": .10},
            "ZONE": {"SIM_PRESSURE": .15, "CREEPER": .10, "MUG_DROP": .05, "EXCHANGE_PRESSURE": .05, "COVER_3_SKY": .15,
                     "COVER_3_BUZZ": .15, "COVER_3_MATCH": .20},
            "COVER_2": {"TAMPA_2": .30, "COVER_2_SINK": .15},
            "COVER_3": {"COVER_3_SKY": .15, "COVER_3_BUZZ": .15, "COVER_3_MATCH": .20, "SIM_PRESSURE": .10, "CREEPER": .10},
            "COVER_4": {"MATCH_QUARTERS": .30, "PALMS": .20, "COVER_6": .20, "COVER_8": .10},
            "BLITZ": {"FIRE_ZONE": .30, "COVER_2_FIRE": .20, "MUG_BLITZ": .03, "OVERLOAD_BLITZ": .03, "A_GAP_BLITZ": .03,
                      "EDGE_BLITZ": .03, "CORNER_BLITZ": .03, "SAFETY_BLITZ": .03, "NICKEL_BLITZ": .03, "CROSS_DOG": .03},
            "BOX_STACK": {"BOX_SKY": .25, "BOX_ROBBER": .10}},
    "MNL": {"MAN": {"PRESS_MAN": .20, "OFF_MAN": .05, "COVER_1_ROBBER": .30, "COVER_2_MAN": .05, "GREEN_DOG": .10},
            "ZONE": {"SIM_PRESSURE": .05, "CREEPER": .05, "MUG_DROP": .05, "COVER_3_SKY": .25, "COVER_3_BUZZ": .10,
                     "COVER_3_MATCH": .05},
            "COVER_2": {"TAMPA_2": .10, "COVER_2_SINK": .05},
            "COVER_3": {"COVER_3_SKY": .25, "COVER_3_BUZZ": .10, "COVER_3_MATCH": .05, "SIM_PRESSURE": .05, "CREEPER": .05},
            "COVER_4": {"MATCH_QUARTERS": .10, "PALMS": .05, "COVER_6": .05, "COVER_8": .05},
            "BLITZ": {"FIRE_ZONE": .15, "MUG_BLITZ": .10, "A_GAP_BLITZ": .15, "B_GAP_BLITZ": .10, "EDGE_BLITZ": .10,
                      "OVERLOAD_BLITZ": .05, "SAFETY_BLITZ": .05, "CROSS_DOG": .05, "SEVEN_MAN_PRESSURE": .03},
            "BOX_STACK": {"BOX_ROBBER": .30, "BOX_SKY": .30}},
    # étape 6 — AXM : couvertures « match », discipline ; GLT : pressions de toutes origines, presse, déguisement ;
    # CPH : athlétique, souple ; NVA : deux safeties profonds (Cover 6, Quarters, Tampa 2), peu de pression
    "AXM": {"MAN": {"PRESS_MAN": .10, "OFF_MAN": .20, "COVER_1_ROBBER": .15, "COVER_2_MAN": .15},
            "ZONE": {"SIM_PRESSURE": .10, "CREEPER": .05, "COVER_3_SKY": .10, "COVER_3_BUZZ": .10, "COVER_3_MATCH": .30},
            "COVER_2": {"TAMPA_2": .20, "COVER_2_SINK": .15},
            "COVER_3": {"COVER_3_SKY": .10, "COVER_3_BUZZ": .10, "COVER_3_MATCH": .30, "SIM_PRESSURE": .10},
            "COVER_4": {"MATCH_QUARTERS": .35, "PALMS": .20, "COVER_6": .15, "COVER_8": .05},
            "BLITZ": {"FIRE_ZONE": .25, "COVER_2_FIRE": .15, "MUG_BLITZ": .05, "OVERLOAD_BLITZ": .05, "A_GAP_BLITZ": .05,
                      "EDGE_BLITZ": .05, "NICKEL_BLITZ": .05},
            "BOX_STACK": {"BOX_SKY": .20, "BOX_ROBBER": .15}},
    "GLT": {"MAN": {"PRESS_MAN": .40, "OFF_MAN": .05, "COVER_1_ROBBER": .15, "COVER_2_MAN": .10, "GREEN_DOG": .15},
            "ZONE": {"SIM_PRESSURE": .20, "CREEPER": .15, "MUG_DROP": .15, "EXCHANGE_PRESSURE": .10, "COVER_3_SKY": .05},
            "COVER_2": {"TAMPA_2": .10, "COVER_2_SINK": .05},
            "COVER_3": {"COVER_3_SKY": .05, "COVER_3_BUZZ": .05, "SIM_PRESSURE": .20, "CREEPER": .15},
            "COVER_4": {"MATCH_QUARTERS": .10, "COVER_6": .05},
            "BLITZ": {"FIRE_ZONE": .10, "COVER_2_FIRE": .05, "MUG_BLITZ": .12, "OVERLOAD_BLITZ": .10, "A_GAP_BLITZ": .10,
                      "B_GAP_BLITZ": .08, "EDGE_BLITZ": .06, "CORNER_BLITZ": .08, "SAFETY_BLITZ": .08, "NICKEL_BLITZ": .08,
                      "CROSS_DOG": .05, "SEVEN_MAN_PRESSURE": .05},
            "BOX_STACK": {"BOX_ROBBER": .25, "BOX_SKY": .10}},
    "CPH": {"MAN": {"PRESS_MAN": .15, "OFF_MAN": .10, "COVER_1_ROBBER": .20, "COVER_2_MAN": .10, "GREEN_DOG": .05},
            "ZONE": {"SIM_PRESSURE": .10, "CREEPER": .05, "MUG_DROP": .05, "COVER_3_SKY": .15, "COVER_3_BUZZ": .10,
                     "COVER_3_MATCH": .10},
            "COVER_2": {"TAMPA_2": .15, "COVER_2_SINK": .10},
            "COVER_3": {"COVER_3_SKY": .15, "COVER_3_BUZZ": .10, "COVER_3_MATCH": .10, "SIM_PRESSURE": .10},
            "COVER_4": {"MATCH_QUARTERS": .20, "PALMS": .10, "COVER_6": .10, "COVER_8": .05},
            "BLITZ": {"FIRE_ZONE": .20, "COVER_2_FIRE": .05, "MUG_BLITZ": .10, "OVERLOAD_BLITZ": .05, "A_GAP_BLITZ": .05,
                      "EDGE_BLITZ": .08, "CORNER_BLITZ": .05, "SAFETY_BLITZ": .05, "NICKEL_BLITZ": .05},
            "BOX_STACK": {"BOX_SKY": .20, "BOX_ROBBER": .20}},
    "NVA": {"MAN": {"PRESS_MAN": .05, "OFF_MAN": .25, "COVER_1_ROBBER": .05, "COVER_2_MAN": .30},
            "ZONE": {"SIM_PRESSURE": .05, "COVER_3_SKY": .20, "COVER_3_BUZZ": .10, "COVER_3_MATCH": .20},
            "COVER_2": {"TAMPA_2": .35, "COVER_2_SINK": .20},
            "COVER_3": {"COVER_3_SKY": .20, "COVER_3_BUZZ": .10, "COVER_3_MATCH": .20},
            "COVER_4": {"MATCH_QUARTERS": .30, "PALMS": .15, "COVER_6": .30, "COVER_8": .10},
            "BLITZ": {"FIRE_ZONE": .30, "COVER_2_FIRE": .25, "MUG_BLITZ": .03, "EDGE_BLITZ": .03},
            "BOX_STACK": {"BOX_SKY": .30, "BOX_ROBBER": .05}},
    # palier 2 — PLS : appels simples, alignement rapide (Cover 3, Quarters) ; ONX : appâts et rotations (Robber,
    # Cover 3 Match, Mug drop, Palms, Cover 2 Fire) ; FRG : gagner à quatre, peu de blitz ; MRD : Cover 2 / Cover 3
    "PLS": {"MAN": {"PRESS_MAN": .10, "OFF_MAN": .20, "COVER_1_ROBBER": .10, "COVER_2_MAN": .10},
            "ZONE": {"SIM_PRESSURE": .05, "COVER_3_SKY": .30, "COVER_3_BUZZ": .15, "COVER_3_MATCH": .10},
            "COVER_2": {"TAMPA_2": .15, "COVER_2_SINK": .10},
            "COVER_3": {"COVER_3_SKY": .30, "COVER_3_BUZZ": .15, "COVER_3_MATCH": .10, "SIM_PRESSURE": .05},
            "COVER_4": {"MATCH_QUARTERS": .30, "PALMS": .05, "COVER_6": .10},
            "BLITZ": {"FIRE_ZONE": .30, "COVER_2_FIRE": .10, "A_GAP_BLITZ": .05, "EDGE_BLITZ": .05, "NICKEL_BLITZ": .05},
            "BOX_STACK": {"BOX_SKY": .25, "BOX_ROBBER": .10}},
    "ONX": {"MAN": {"PRESS_MAN": .25, "OFF_MAN": .10, "COVER_1_ROBBER": .35, "COVER_2_MAN": .15},
            "ZONE": {"SIM_PRESSURE": .10, "CREEPER": .05, "MUG_DROP": .20, "EXCHANGE_PRESSURE": .05, "COVER_3_SKY": .10,
                     "COVER_3_BUZZ": .15, "COVER_3_MATCH": .25},
            "COVER_2": {"TAMPA_2": .20, "COVER_2_SINK": .25},
            "COVER_3": {"COVER_3_SKY": .10, "COVER_3_BUZZ": .15, "COVER_3_MATCH": .25, "SIM_PRESSURE": .10},
            "COVER_4": {"MATCH_QUARTERS": .25, "PALMS": .25, "COVER_6": .15, "COVER_8": .10},
            "BLITZ": {"FIRE_ZONE": .20, "COVER_2_FIRE": .20, "MUG_BLITZ": .08, "CORNER_BLITZ": .05, "SAFETY_BLITZ": .05,
                      "NICKEL_BLITZ": .05, "CROSS_DOG": .03},
            "BOX_STACK": {"BOX_ROBBER": .30, "BOX_SKY": .15}},
    "FRG": {"MAN": {"PRESS_MAN": .15, "OFF_MAN": .15, "COVER_1_ROBBER": .25, "COVER_2_MAN": .10},
            "ZONE": {"SIM_PRESSURE": .05, "COVER_3_SKY": .25, "COVER_3_BUZZ": .10, "COVER_3_MATCH": .10},
            "COVER_2": {"TAMPA_2": .20, "COVER_2_SINK": .05},
            "COVER_3": {"COVER_3_SKY": .25, "COVER_3_BUZZ": .10, "COVER_3_MATCH": .10, "SIM_PRESSURE": .05},
            "COVER_4": {"MATCH_QUARTERS": .15, "PALMS": .05, "COVER_6": .05},
            "BLITZ": {"FIRE_ZONE": .15, "A_GAP_BLITZ": .12, "B_GAP_BLITZ": .10, "EDGE_BLITZ": .08, "CROSS_DOG": .05},
            "BOX_STACK": {"BOX_ROBBER": .25, "BOX_SKY": .30}},
    "MRD": {"MAN": {"PRESS_MAN": .05, "OFF_MAN": .30, "COVER_1_ROBBER": .05, "COVER_2_MAN": .25},
            "ZONE": {"SIM_PRESSURE": .05, "COVER_3_SKY": .25, "COVER_3_BUZZ": .15, "COVER_3_MATCH": .20},
            "COVER_2": {"TAMPA_2": .30, "COVER_2_SINK": .25},
            "COVER_3": {"COVER_3_SKY": .25, "COVER_3_BUZZ": .15, "COVER_3_MATCH": .20},
            "COVER_4": {"MATCH_QUARTERS": .25, "PALMS": .15, "COVER_6": .25, "COVER_8": .10},
            "BLITZ": {"FIRE_ZONE": .30, "COVER_2_FIRE": .25, "EDGE_BLITZ": .03},
            "BOX_STACK": {"BOX_SKY": .30, "BOX_ROBBER": .05}},
}
P_BANJO = 0.5          # contre une formation à receveurs groupés / empilés, l'homme passe en banjo une fois sur deux
FORMATIONS_GROUPEES = {"BUNCH", "SINGLEBACK_BUNCH", "GUN_STACK", "GUN_TRIPS_TIGHT"}

# jeux de rush à 4 (appels sans blitz) : (poche en s, bruit de poche ×, scramble ×)
RUSH = {"ET_STUNT": (-0.08, 1.25, 1.0), "TEX_STUNT": (-0.08, 1.25, 1.0), "INTERIOR_STUNT": (-0.06, 1.2, 1.1),
        "LONG_STUNT": (-0.12, 1.4, 1.1), "CONTAIN_RUSH": (0.12, 1.0, 0.5), "INTERIOR_COLLAPSE": (-0.10, 1.0, 1.2),
        "EDGE_RUSH": (-0.05, 1.0, 0.85)}
RUSH_STYLE = {
    "CTX": {"ET_STUNT": .06, "TEX_STUNT": .06, "INTERIOR_STUNT": .04, "LONG_STUNT": .03, "CONTAIN_RUSH": .05,
            "INTERIOR_COLLAPSE": .03, "EDGE_RUSH": .03},
    "VEC": {"ET_STUNT": .08, "TEX_STUNT": .08, "INTERIOR_STUNT": .05, "LONG_STUNT": .05, "CONTAIN_RUSH": .02,
            "INTERIOR_COLLAPSE": .05, "EDGE_RUSH": .05},
    "AEG": {"ET_STUNT": .05, "TEX_STUNT": .05, "INTERIOR_STUNT": .02, "LONG_STUNT": .02, "CONTAIN_RUSH": .08,
            "INTERIOR_COLLAPSE": .02, "EDGE_RUSH": .02},
    "MNL": {"ET_STUNT": .05, "TEX_STUNT": .05, "INTERIOR_STUNT": .03, "LONG_STUNT": .02, "CONTAIN_RUSH": .03,
            "INTERIOR_COLLAPSE": .08, "EDGE_RUSH": .05},
    "AXM": {"ET_STUNT": .05, "TEX_STUNT": .05, "INTERIOR_STUNT": .03, "LONG_STUNT": .02, "CONTAIN_RUSH": .06,
            "INTERIOR_COLLAPSE": .03, "EDGE_RUSH": .03},
    "GLT": {"ET_STUNT": .10, "TEX_STUNT": .10, "INTERIOR_STUNT": .07, "LONG_STUNT": .07, "CONTAIN_RUSH": .02,
            "INTERIOR_COLLAPSE": .05, "EDGE_RUSH": .06},
    "CPH": {"ET_STUNT": .06, "TEX_STUNT": .06, "INTERIOR_STUNT": .03, "LONG_STUNT": .03, "CONTAIN_RUSH": .06,
            "INTERIOR_COLLAPSE": .03, "EDGE_RUSH": .04},
    "NVA": {"ET_STUNT": .04, "TEX_STUNT": .04, "INTERIOR_STUNT": .02, "LONG_STUNT": .02, "CONTAIN_RUSH": .10,
            "INTERIOR_COLLAPSE": .03, "EDGE_RUSH": .03},
    "PLS": {"ET_STUNT": .03, "TEX_STUNT": .03, "INTERIOR_STUNT": .02, "LONG_STUNT": .01, "CONTAIN_RUSH": .06,
            "INTERIOR_COLLAPSE": .03, "EDGE_RUSH": .05},
    "ONX": {"ET_STUNT": .06, "TEX_STUNT": .06, "INTERIOR_STUNT": .03, "LONG_STUNT": .02, "CONTAIN_RUSH": .06,
            "INTERIOR_COLLAPSE": .03, "EDGE_RUSH": .04},
    "FRG": {"ET_STUNT": .05, "TEX_STUNT": .05, "INTERIOR_STUNT": .04, "LONG_STUNT": .02, "CONTAIN_RUSH": .04,
            "INTERIOR_COLLAPSE": .12, "EDGE_RUSH": .08},
    "MRD": {"ET_STUNT": .04, "TEX_STUNT": .04, "INTERIOR_STUNT": .02, "LONG_STUNT": .02, "CONTAIN_RUSH": .10,
            "INTERIOR_COLLAPSE": .02, "EDGE_RUSH": .02},
}

# fronts (§12.3) : variantes d'alignement à l'intérieur d'une formation défensive existante ; effet en yards sur les
# courses, par classe (déterministe), et sur la poche (s) quand la défense est face à une passe
FRONTS = {
    "4_3_OVER":       {"formations": ("4_3",), "course": {"inside": -0.2, "outside": 0.2}},
    "4_3_UNDER":      {"formations": ("4_3",), "course": {"inside": 0.1, "gap": -0.2}},
    "4_3_EVEN":       {"formations": ("4_3",), "course": {"outside": -0.1, "option": 0.2}},
    "BEAR":           {"formations": ("4_3",), "course": {"inside": -0.8, "gap": -0.5, "outside": 0.6, "perimeter": 0.8,
                                                          "option": 0.4, "qb": -0.3}},
    "TITE":           {"formations": ("3_4",), "course": {"inside": -0.5, "gap": -0.3, "outside": 0.4, "perimeter": 0.3}},
    "HYBRID":         {"formations": ("3_4", "NICKEL"), "course": {"inside": 0.1, "option": -0.3, "perimeter": -0.2}},
    "MINT":           {"formations": ("NICKEL",), "course": {"inside": -0.4, "gap": -0.2, "outside": 0.3, "option": -0.1}},
    "STACK":          {"formations": ("NICKEL",), "course": {"inside": 0.2, "gap": 0.1, "outside": -0.3, "perimeter": -0.4,
                                                             "option": -0.2}},
    "SHORT_YARDAGE":  {"formations": ("4_3", "3_4"), "course": {"inside": -0.6, "gap": -0.6, "outside": 0.5,
                                                                "perimeter": 0.9}, "situation": "short"},
    "NASCAR":         {"formations": ("NICKEL", "DIME"), "course": {"inside": 0.6, "gap": 0.5, "qb": 0.4},
                       "poche": -0.12, "situation": "long"},
    "EMPTY_SPECIFIC": {"formations": ("NICKEL", "DIME"), "course": {"inside": 0.3, "qb": 0.2}, "poche": 0.05,
                       "court": -0.2, "contre": "EMPTY"},
}
FRONTS_STYLE = {
    "CTX": {"4_3_OVER": .25, "4_3_UNDER": .25, "4_3_EVEN": .10, "BEAR": .05, "TITE": .20, "HYBRID": .20, "MINT": .20,
            "STACK": .15, "SHORT_YARDAGE": .40, "NASCAR": .30, "EMPTY_SPECIFIC": .50},
    "VEC": {"4_3_OVER": .20, "4_3_UNDER": .20, "4_3_EVEN": .20, "BEAR": .15, "TITE": .15, "HYBRID": .30, "MINT": .10,
            "STACK": .25, "SHORT_YARDAGE": .30, "NASCAR": .45, "EMPTY_SPECIFIC": .40},
    "AEG": {"4_3_OVER": .35, "4_3_UNDER": .20, "4_3_EVEN": .05, "BEAR": .05, "TITE": .25, "HYBRID": .10, "MINT": .30,
            "STACK": .05, "SHORT_YARDAGE": .35, "NASCAR": .30, "EMPTY_SPECIFIC": .60},
    "MNL": {"4_3_OVER": .20, "4_3_UNDER": .30, "4_3_EVEN": .10, "BEAR": .30, "TITE": .35, "HYBRID": .10, "MINT": .20,
            "STACK": .10, "SHORT_YARDAGE": .60, "NASCAR": .15, "EMPTY_SPECIFIC": .30},
    "AXM": {"4_3_OVER": .30, "4_3_UNDER": .20, "4_3_EVEN": .10, "BEAR": .05, "TITE": .20, "HYBRID": .15, "MINT": .25,
            "STACK": .10, "SHORT_YARDAGE": .35, "NASCAR": .30, "EMPTY_SPECIFIC": .55},
    "GLT": {"4_3_OVER": .15, "4_3_UNDER": .20, "4_3_EVEN": .15, "BEAR": .20, "TITE": .15, "HYBRID": .30, "MINT": .10,
            "STACK": .25, "SHORT_YARDAGE": .35, "NASCAR": .55, "EMPTY_SPECIFIC": .40},
    "CPH": {"4_3_OVER": .20, "4_3_UNDER": .20, "4_3_EVEN": .20, "BEAR": .05, "TITE": .15, "HYBRID": .30, "MINT": .15,
            "STACK": .20, "SHORT_YARDAGE": .35, "NASCAR": .30, "EMPTY_SPECIFIC": .45},
    "NVA": {"4_3_OVER": .25, "4_3_UNDER": .20, "4_3_EVEN": .10, "BEAR": .05, "TITE": .20, "HYBRID": .15, "MINT": .25,
            "STACK": .05, "SHORT_YARDAGE": .30, "NASCAR": .25, "EMPTY_SPECIFIC": .55},
    "PLS": {"4_3_OVER": .25, "4_3_UNDER": .20, "4_3_EVEN": .15, "BEAR": .05, "TITE": .15, "HYBRID": .15, "MINT": .20,
            "STACK": .05, "SHORT_YARDAGE": .30, "NASCAR": .25, "EMPTY_SPECIFIC": .45},
    "ONX": {"4_3_OVER": .25, "4_3_UNDER": .20, "4_3_EVEN": .10, "BEAR": .10, "TITE": .20, "HYBRID": .20, "MINT": .25,
            "STACK": .10, "SHORT_YARDAGE": .35, "NASCAR": .30, "EMPTY_SPECIFIC": .55},
    "FRG": {"4_3_OVER": .25, "4_3_UNDER": .30, "4_3_EVEN": .15, "BEAR": .30, "TITE": .30, "HYBRID": .05, "MINT": .15,
            "STACK": .10, "SHORT_YARDAGE": .60, "NASCAR": .20, "EMPTY_SPECIFIC": .30},
    "MRD": {"4_3_OVER": .35, "4_3_UNDER": .20, "4_3_EVEN": .05, "BEAR": .05, "TITE": .25, "HYBRID": .10, "MINT": .30,
            "STACK": .05, "SHORT_YARDAGE": .35, "NASCAR": .30, "EMPTY_SPECIFIC": .60},
}
FORMATIONS_VIDES = {"EMPTY", "GUN_QUADS"}         # l'attaque n'a personne dans le champ arrière

# mouvements de front sur les courses (§12.3, front movement) : écart-type des yards, moyenne nulle (un mouvement
# deviné juste ferme le trou, deviné faux l'ouvre) ; probabilité d'un mouvement par franchise
MOUVEMENTS = {"STEM": 0.6, "SHIFT": 0.5, "SLANT": 1.2, "ANGLE": 1.0, "SPIN": 0.8, "LOOP": 1.2, "CRASH": 1.5}
MOUVEMENTS_STYLE = {"CTX": .20, "VEC": .30, "AEG": .12, "MNL": .25, "AXM": .15, "GLT": .40, "CPH": .22, "NVA": .12,
                    "PLS": .10, "ONX": .18, "FRG": .30, "MRD": .12}

# classe de course des concepts existants (pour les fronts et la motion)
CLASSE_COURSE = {"INSIDE_RUN": "inside", "TRAP": "inside", "DRAW": "inside", "QB_SNEAK": "inside",
                 "POWER": "gap", "COUNTER": "gap", "OUTSIDE_RUN": "outside", "JET_SWEEP": "perimeter",
                 "READ_OPTION": "option"}
CLASSE_COURSE.update({c: d["classe"] for c, d in CONCEPTS.items() if d["famille"] == R})


def _tirage_parts(parts, r):
    """parts {clé: probabilité} (somme ≤ 1) -> clé ou None, avec un tirage r dans [0, 1)."""
    for k, p in sorted(parts.items()):
        r -= p
        if r < 0:
            return k
    return None


def choisir_paquet(abbr, concept_defensif, formation_attaque, graine, n):
    """Paquet défensif (ou None : l'appel de base, comme avant) — flux « xp-paquet »."""
    rng = flux(FLUX["paquet"], graine, n)
    r1, r2 = rng.random(), rng.random()
    if concept_defensif == "MAN" and formation_attaque in FORMATIONS_GROUPEES and r1 < P_BANJO:
        return "BANJO"
    parts = PAQUETS_STYLE.get(abbr, {}).get(concept_defensif, {})
    return _tirage_parts(parts, r2)


def choisir_rush(abbr, concept_defensif, paquet, graine, n):
    if concept_defensif in ("BLITZ", "BOX_STACK") or (paquet and PAQUETS[paquet][3] > 4):
        return None
    return _tirage_parts(RUSH_STYLE.get(abbr, {}), flux(FLUX["rush"], graine, n).random())


def choisir_front(abbr, formation_defensive, situations, formation_attaque, graine, n):
    """Front à l'intérieur de la formation défensive (ou None : l'alignement de base)."""
    style = FRONTS_STYLE.get(abbr, {})
    cands = {}
    for f, d in FRONTS.items():
        if formation_defensive not in d["formations"]:
            continue
        if d.get("situation") and d["situation"] not in situations:
            continue
        if d.get("contre") == "EMPTY" and formation_attaque not in FORMATIONS_VIDES:
            continue
        cands[f] = style.get(f, 0.0)
    if not cands:
        return None
    # les fronts de situation passent en premier (ils répondent à la situation), puis les autres se partagent le reste
    r = flux(FLUX["front"], graine, n).random()
    prio = {f: p for f, p in cands.items() if FRONTS[f].get("situation") or FRONTS[f].get("contre")}
    if prio:
        k = _tirage_parts(prio, r)
        if k:
            return k
        r = (r - sum(prio.values())) / max(1e-9, 1 - sum(prio.values()))
    reste = {f: p for f, p in cands.items() if f not in prio}
    tot = sum(reste.values())
    if tot > 1:
        reste = {f: p / tot for f, p in reste.items()}
    return _tirage_parts(reste, max(0.0, r))


def tirer_mouvement(abbr, graine, n):
    """(mouvement, écart en yards) d'un front sur une course — moyenne nulle."""
    rng = flux(FLUX["mouvement"], graine, n)
    if rng.random() >= MOUVEMENTS_STYLE.get(abbr, 0.0):
        return None, 0.0
    m = sorted(MOUVEMENTS)[int(rng.random() * len(MOUVEMENTS)) % len(MOUVEMENTS)]
    return m, round(gauss_borne(rng, MOUVEMENTS[m], 3.0), 2)


# =====================================================================================================================
# 10. LECTURES — RPO et options : la défense appelée décide (en probabilité), le QB peut se tromper
# =====================================================================================================================
# probabilité de LANCER sur un RPO, selon l'appel défensif (boîte chargée -> lancer ; boîte légère -> donner)
RPO_LANCER = {
    "post":  {"BOX_STACK": 0.65, "BLITZ": 0.55, "MAN": 0.35, "ZONE": 0.35, "COVER_3": 0.35, "COVER_2": 0.15,
              "COVER_4": 0.15},
    "alert": {"BOX_STACK": 0.55, "BLITZ": 0.55, "MAN": 0.50, "ZONE": 0.15, "COVER_3": 0.20, "COVER_2": 0.10,
              "COVER_4": 0.10},
    "peek":  {"BOX_STACK": 0.45, "BLITZ": 0.50, "MAN": 0.50, "ZONE": 0.20, "COVER_3": 0.20, "COVER_2": 0.15,
              "COVER_4": 0.15},
}
# option : le défenseur lu (le bord) ferme sur le dos -> le QB garde ; il reste large -> il donne
OPTION_GARDE = {"BOX_STACK": 1.35, "BLITZ": 1.25, "MAN": 1.0, "ZONE": 0.9, "COVER_3": 0.9, "COVER_2": 0.8,
                "COVER_4": 0.8}


def p_erreur_lecture(qb):
    """Le QB se trompe parfois de lecture (decision_making) : jamais nul, jamais majoritaire."""
    dm = float(((qb or {}).get("ratings") or {}).get("decision_making", 75))
    return max(0.05, min(0.30, 0.22 - (dm - 70) * 0.008))


def lecture_rpo(concept, concept_defensif, qb, graine, n):
    """('GIVE' | 'THROW', bonne lecture ?) — flux « xp-rpo »."""
    rng = flux(FLUX["rpo"], graine, n)
    p = RPO_LANCER[CONCEPTS[concept]["rpo"]].get(concept_defensif, 0.3)
    bon = "THROW" if rng.random() < p else "GIVE"
    if rng.random() < p_erreur_lecture(qb):
        return ("GIVE" if bon == "THROW" else "THROW"), False
    return bon, True


def lecture_option(concept, concept_defensif, qb, graine, n):
    """Rôle du porteur d'une option (QB, RB, WR3, TE) — flux « xp-option »."""
    rng = flux(FLUX["option"], graine, n)
    base = dict(CONCEPTS[concept]["option"])
    k = OPTION_GARDE.get(concept_defensif, 1.0)
    if "QB" in base:
        base["QB"] *= k
    tot = sum(base.values())
    r = rng.random() * tot
    choix = sorted(base)[-1]
    for role in sorted(base):
        r -= base[role]
        if r < 0:
            choix = role
            break
    if rng.random() < p_erreur_lecture(qb) * 0.5:       # mauvaise lecture : le ballon part à l'autre option
        autres = [x for x in sorted(base) if x != choix]
        choix = autres[int(rng.random() * len(autres)) % len(autres)] if autres else choix
    return choix


# =====================================================================================================================
# 11. EFFETS — courses (yards) et passes (appel transmis à moteur.decider_passe)
# =====================================================================================================================
def effet_course(concept, front=None, motion=None, shift=None, mouvement_yards=0.0, suite=False):
    """Yards ajoutés à une course (déterministe sauf le mouvement, déjà tiré) : front, motion, shift, enchaînement."""
    cl = CLASSE_COURSE.get(concept, "inside")
    d = 0.0
    if front:
        d += FRONTS[front]["course"].get(cl, 0.0)
    if motion:
        d += MOTIONS[motion]["course"].get(cl, 0.0)
    if shift:
        d += SHIFT_EFFET["course"]
    if suite:
        d += SEQUENCE["course"]
    return round(d + mouvement_yards, 2)


def appel_passe(concept, paquet=None, rush=None, front=None, motion=None, shift=None, suite=False):
    """Ce que l'extension transmet au moteur pour une passe (moteur.decider_passe(..., appel=...)) ; None si rien."""
    a = {}
    if paquet:
        base, fam, coq, rushers, pres, eff = PAQUETS[paquet]
        a.update({"paquet": paquet, "famille": fam, "coquilles": coq, "rushers": rushers, "presente": pres})
        a.update({k: v for k, v in eff.items()})
    if rush:
        a["rush"] = rush
        dp, br, sc = RUSH[rush]
        a["poche"] = a.get("poche", 0.0) + dp
        a["bruit_poche"] = br
        a["scramble"] = a.get("scramble", 1.0) * sc
    if front and FRONTS[front].get("poche"):
        a["poche"] = a.get("poche", 0.0) + FRONTS[front]["poche"]
    if front and FRONTS[front].get("court"):
        a["court"] = a.get("court", 0.0) + FRONTS[front]["court"]
    prot = protection(concept)
    if prot:
        pr = PROTECTIONS[prot]
        a["protection"] = prot
        a["poche"] = a.get("poche", 0.0) + pr["poche"] + PROTECTION_VS.get((prot, paquet or rush or ""), 0.0)
        a["rusher5"] = pr["rusher5"]
        a["retire"] = list(pr["retire"])
        if pr.get("retard"):
            a["retard"] = list(pr["retard"])
    if motion:
        a["motion"] = motion
        a["motion_role"] = MOTIONS[motion]["role"]
        a["motion_sep"] = {"homme": MOTIONS[motion]["homme"][1], "zone": MOTIONS[motion]["zone"][1]}
    if shift:
        a["shift"] = shift
    if suite:
        a["suite"] = True
        a["suite_sep"] = SEQUENCE["passe"]
    return a or None


def ajuster_lectures(lectures, appel):
    """Protection : rôles qui restent bloquer (retirés, le checkdown reste en dernier) ; chip : route qui part plus tard."""
    if not appel or not lectures:
        return lectures
    retire = set(appel.get("retire") or ())
    out = [dict(l) for l in lectures if l["role"] not in retire] or [dict(l) for l in lectures]
    if appel.get("retard"):
        role, dt = appel["retard"]
        for l in out:
            if l["role"] == role:
                l["ouverture"] = round(l["ouverture"] + dt, 2)
    for l in out[:-1]:
        if l["niveau"] == "checkdown":
            l["niveau"] = "tertiaire"
    out[-1]["niveau"] = "checkdown"
    return out


def deguisement(appel, famille):
    """Erreurs de lecture du QB en plus (+) ou en moins (−) : présentation contre information (motion, shift)."""
    if not appel:
        return 0.0
    d = float(appel.get("deguisement", 0.0))
    m = appel.get("motion")
    if m:
        moins = MOTIONS[m]["homme" if famille == "homme" else "zone"][0]
        d = d * 0.5 - moins if d > 0 else d - moins
    if appel.get("shift"):
        d -= SHIFT_EFFET["deguisement"]
    return round(max(-0.6, min(0.6, d)), 3)


# =====================================================================================================================
# 12. BRANCHEMENT dans les autres modules de moteur/ (appelé par le notebook quand l'extension est allumée)
# =====================================================================================================================
def brancher():
    """Inscrit routes, progressions, coquilles défensives et familles de concepts. Idempotent."""
    from . import progressions, reaction_defensive, plan_de_jeu
    for nom, r in ROUTES.items():
        progressions.ROUTES.setdefault(nom, {"classe": r["classe"], "ouverture": r["ouverture"]})
    for c, prog in PROGRESSIONS.items():
        progressions.PROGRESSIONS.setdefault(c, list(prog))
        progressions.PROGRESSIONS_B.setdefault(c, list(prog))
    for coq, (av, avr, dbl) in COQUILLES.items():
        reaction_defensive.AVANTAGE.setdefault(coq, dict(av))
        reaction_defensive.AVANTAGE_ROUTE.setdefault(coq, dict(avr))
        reaction_defensive.DOUBLE_BASE.setdefault(coq, dbl)
    for c, d in CONCEPTS.items():
        for fam in d.get("plan", ()):
            getattr(plan_de_jeu, fam).add(c)
    return {"routes": len(ROUTES), "progressions": len(PROGRESSIONS), "coquilles": len(COQUILLES),
            "concepts": len(CONCEPTS), "formations": len(FORMATIONS), "plays": len(PLAYS), "paquets": len(PAQUETS)}


def resume():
    """Comptes du catalogue (contrôles du notebook, rapport)."""
    return {"formations": len(FORMATIONS), "plays": len(PLAYS),
            "concepts_course": sum(1 for d in CONCEPTS.values() if d["famille"] == R),
            "concepts_passe": sum(1 for d in CONCEPTS.values() if d["famille"] == P and not d.get("rpo_de")),
            "rpo": sum(1 for d in CONCEPTS.values() if d.get("rpo")), "routes": len(ROUTES), "paquets": len(PAQUETS),
            "coquilles": len(COQUILLES), "fronts": len(FRONTS), "rush": len(RUSH), "mouvements": len(MOUVEMENTS),
            "motions": len(MOTIONS), "protections": len(PROTECTIONS), "relations": len(RELATIONS),
            "alias": sum(len(v) for v in ALIAS.values()), "reserve": len(RESERVE)}
