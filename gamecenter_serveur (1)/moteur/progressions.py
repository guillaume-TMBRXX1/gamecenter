"""Progressions de lecture du playbook (bloc A).

Pour chaque concept de passe : cible primaire, secondaire, tertiaire et checkdown, chacune avec sa route.
Le QB lit dans cet ordre (QBDecisionEngine) ; s'il ne trouve personne : scramble, throwaway ou sack.

Rôles : WR1, WR2, WR3 (slot), TE, RB. Les routes portent les noms de la bibliothèque de routes du notebook
(ROUTE_LIBRARY, cellules 10.4 et 12.2 ter) + FLAT (ajoutée au bloc A pour le checkdown du RB) ; SCREEN
reste le cas particulier animé à part par le site.
"""

# classe de profondeur (pour la lecture de couverture) et instant où le QB peut lancer sur la route
# (secondes après le snap, lancer en anticipation compris)
ROUTES = {
    "SCREEN":      {"classe": "court", "ouverture": 0.7},
    "QUICK_SLANT": {"classe": "court", "ouverture": 0.8},
    "STICK":       {"classe": "court", "ouverture": 0.9},
    "FLAT":        {"classe": "court", "ouverture": 1.0},
    "SLANT":       {"classe": "court", "ouverture": 1.0},
    "DRAG":        {"classe": "court", "ouverture": 1.1},
    "OUT":         {"classe": "moyen", "ouverture": 1.3},
    "CURL":        {"classe": "moyen", "ouverture": 1.4},
    "IN":          {"classe": "moyen", "ouverture": 1.6},
    "CROSS":       {"classe": "moyen", "ouverture": 1.7},
    "FLAG":        {"classe": "moyen", "ouverture": 1.7},
    "SEAM":        {"classe": "moyen", "ouverture": 1.8},
    "DIG":         {"classe": "moyen", "ouverture": 1.8},
    "POST":        {"classe": "profond", "ouverture": 2.1},
    "CORNER":      {"classe": "profond", "ouverture": 2.1},
    "GO":          {"classe": "profond", "ouverture": 2.2},
}

ROLES = ("WR1", "WR2", "WR3", "TE", "RB")
NIVEAUX = ("primaire", "secondaire", "tertiaire", "checkdown")

# concept -> [(rôle, route)] dans l'ordre de lecture : primaire, secondaire, tertiaire, checkdown
PROGRESSIONS = {
    # concepts de base (playbook générique, 15 plays + 10.5)
    "QUICK_SLANT": [("WR1", "QUICK_SLANT"), ("WR2", "SLANT"), ("TE", "DRAG"), ("RB", "FLAT")],
    "SHORT_OUT":   [("WR1", "OUT"), ("WR2", "QUICK_SLANT"), ("TE", "STICK"), ("RB", "FLAT")],
    "CROSS":       [("WR1", "CROSS"), ("WR2", "DIG"), ("TE", "DRAG"), ("RB", "FLAT")],
    "SCREEN":      [("RB", "SCREEN"), ("WR3", "QUICK_SLANT"), ("TE", "DRAG"), ("WR1", "STICK")],
    "FOUR_VERTS":  [("WR1", "GO"), ("WR2", "GO"), ("TE", "SEAM"), ("RB", "FLAT")],
    "DEEP_POST":   [("WR1", "POST"), ("WR2", "DIG"), ("TE", "CROSS"), ("RB", "FLAT")],
    "PLAY_ACTION": [("WR1", "POST"), ("WR2", "CORNER"), ("TE", "CROSS"), ("RB", "FLAT")],
    "CORNER":      [("WR1", "CORNER"), ("WR2", "IN"), ("TE", "DRAG"), ("RB", "FLAT")],
    "IN":          [("WR1", "IN"), ("WR2", "POST"), ("TE", "STICK"), ("RB", "FLAT")],
    "DRAG":        [("WR1", "DRAG"), ("WR2", "DIG"), ("TE", "STICK"), ("RB", "FLAT")],
    # « Roman 2014 » (V20)
    "STICK":       [("TE", "STICK"), ("WR3", "OUT"), ("WR1", "GO"), ("RB", "FLAT")],
    "CURL":        [("WR1", "CURL"), ("WR2", "OUT"), ("TE", "STICK"), ("RB", "FLAT")],
    "CHAMP":       [("WR1", "CORNER"), ("WR2", "CURL"), ("TE", "STICK"), ("RB", "FLAT")],
    "DAGGER":      [("WR1", "DIG"), ("WR2", "SEAM"), ("TE", "DRAG"), ("RB", "FLAT")],
    "SAIL":        [("WR1", "FLAG"), ("WR2", "GO"), ("TE", "FLAT"), ("RB", "DRAG")],
    "MESH":        [("WR1", "DRAG"), ("WR2", "DRAG"), ("TE", "CORNER"), ("RB", "FLAT")],
    "BOOT":        [("WR1", "FLAG"), ("WR2", "CROSS"), ("TE", "FLAT"), ("RB", "DRAG")],
    "POP":         [("TE", "SEAM"), ("WR1", "POST"), ("WR2", "IN"), ("RB", "FLAT")],
}
PROGRESSION_DEFAUT = [("WR1", "CURL"), ("WR2", "OUT"), ("TE", "STICK"), ("RB", "FLAT")]

# formations où un rôle n'est pas éligible (HEAVY : WR1 aligné en 6e OL, cf. 12.2 ter)
INELIGIBLES = {"HEAVY": {"WR1"}}
# rôle de remplacement quand un rôle manque ou n'est pas éligible (route conservée)
REMPLACANTS = {"WR1": ("WR2", "WR3", "TE"), "WR2": ("WR3", "TE", "WR1"), "WR3": ("WR2", "TE", "WR1"),
               "TE": ("WR3", "WR2", "RB"), "RB": ("TE", "WR3")}


def progression(concept, formation=None, roles_presents=ROLES):
    """Liste ordonnée des lectures : [{"niveau", "role", "route", "classe", "ouverture"}].

    Un rôle absent du roster ou inéligible dans la formation est remplacé par le premier remplaçant libre ;
    sans remplaçant, la lecture est retirée. Le checkdown reste toujours en dernier.
    """
    base = PROGRESSIONS.get(concept, PROGRESSION_DEFAUT)
    exclus = INELIGIBLES.get(formation or "", set())
    dispo = [r for r in roles_presents if r not in exclus]
    pris, out = set(), []
    for i, (role, route) in enumerate(base):
        choix = role if role in dispo and role not in pris else \
            next((r for r in REMPLACANTS.get(role, ()) if r in dispo and r not in pris), None)
        if choix is None:
            continue
        pris.add(choix)
        geo = ROUTES[route]
        out.append({"niveau": NIVEAUX[min(i, 3)], "role": choix, "route": route,
                    "classe": geo["classe"], "ouverture": geo["ouverture"]})
    if out:
        out[-1]["niveau"] = "checkdown"
    return out
