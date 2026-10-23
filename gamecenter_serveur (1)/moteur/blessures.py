"""Les blessures (étape 7.4 de la feuille de route « moteur plus intelligent », plan validé par Guillaume le 22/10/2026).

7.4.1 — LA BLESSURE PENDANT LE MATCH : à chaque action de l'attaque (les équipes spéciales ne changent pas), chaque
joueur sur le terrain a un petit risque, plus grand pour ceux qui prennent les coups — porteur plaqué, plaqueur, QB
sacké, lignes au contact — selon son poste, sa fatigue (énergie de 7.3) et son âge (bloc E). Gravité :
  LÉGÈRE     il sort quelques snaps de son unité, puis revient ;
  MATCH      il ne revient pas (disponible au match suivant) ;
  SEMAINES   absent une semaine ou plus, à partir de la semaine suivante (7.4.2 : rapport publié avant les cotes).
Une partie du corps (genou, cheville, ischios, épaule, commotion…) ; une commotion fait toujours sortir pour le match.
Le remplaçant de la place entre (banc de 7.3) ; sans remplaçant, un joueur d'une famille voisine glisse
(rotations.URGENCE). Le dernier QB valide ne se blesse pas (le moteur a besoin d'un passeur).

Fréquence (décision de Guillaume) : ≈ une sortie sur blessure tous les deux matchs, ≈ 2 absents par équipe et par
semaine (23 matchs par équipe et par semaine : les taux de la NFL en feraient 5 à 8).

7.4.2 — L'INFIRMERIE : une blessure de « semaines » rend le joueur absent à partir de la semaine suivante ; l'état
des joueurs (bloc E) garde l'infirmerie d'une semaine à l'autre ({id: {..., "weeks_left"}}) ; au début de la semaine,
les absents sont retirés de l'effectif AVANT les cotes (notes d'unité, rotations) et le rapport est publié dans
week.json (« injuries ») ; une famille de postes qui a plus d'absents que de remplaçants valides signe un joueur libre
pour la semaine (≈ 10 points sous le titulaire, nom jamais porté). Un absent ne joue pas, donc ne progresse pas
(participation nulle au bloc E).

Déterministe : tout vient du flux dédié « blessures » (graine du match, numéro de l'action).
"""
import random

VERSION = "blessures-1"
FLUX = "blessures"

LEGERE, MATCH, SEMAINES = "minor", "game", "weeks"

# risque par snap sur le terrain (avant ECHELLE), par famille de postes : les lignes et les joueurs de contact plus
# que le QB (protégé hors sack) ; les WR et les CB sur les actions où ils sont impliqués
RISQUE = {"QB": 0.25, "RB": 0.8, "WR": 0.45, "TE": 0.7, "OL": 0.6, "EDGE": 0.7, "DT": 0.75, "LB": 0.75, "CB": 0.5,
          "S": 0.55}
# multiplicateurs : le porteur plaqué, le plaqueur crédité, le QB sacké (et le sackeur), un gros gain (course
# lancée, plaquage en pleine vitesse)
PORTEUR, PLAQUEUR, SACK_QB, SACKEUR, GROS_GAIN = 9.0, 5.0, 14.0, 2.0, 1.5
GROS_GAIN_YARDS = 15
ECHELLE = 2.1e-4             # calibré sur 276 matchs : 0,51 sortie par match (BLESSURES_PAR_MATCH)
BLESSURES_PAR_MATCH = 0.5

# fatigue (énergie de 7.3) : sous FATIGUE_SEUIL, le risque monte jusqu'à × (1 + FATIGUE_MAX) à énergie nulle
FATIGUE_SEUIL, FATIGUE_MAX = 70.0, 0.8
# âge (bloc E) : + 6 % par année au-delà de 29 ans
AGE_SEUIL, AGE_PENTE = 29.0, 0.06

# gravité : (gravité, semaines, probabilité) ; légère : 2 à 10 snaps de son unité hors du terrain
GRAVITE = ((LEGERE, 0, 0.37), (MATCH, 0, 0.37), (SEMAINES, 1, 0.18), (SEMAINES, 2, 0.05), (SEMAINES, 3, 0.02),
           (SEMAINES, 4, 0.01))     # ≈ 1,5 nouvel absent par équipe et par semaine, ≈ 2 absents en même temps
SNAPS_LEGERE = (2, 10)

# parties du corps selon la gravité (poids) ; une commotion n'est jamais légère
PARTIES = {
    LEGERE: {"ankle": 3, "hand": 2, "ribs": 2, "shoulder": 2, "back": 1, "knee": 1},
    MATCH: {"ankle": 3, "hamstring": 3, "shoulder": 2, "concussion": 2, "groin": 1, "knee": 1, "ribs": 1},
    SEMAINES: {"knee": 3, "ankle": 3, "hamstring": 3, "concussion": 2, "shoulder": 2, "foot": 1, "groin": 1},
}
LIBELLE = {"ankle": "ankle", "hand": "hand", "ribs": "ribs", "shoulder": "shoulder", "back": "back", "knee": "knee",
           "hamstring": "hamstring", "concussion": "concussion", "groin": "groin", "foot": "foot"}


def famille(poste):
    return "OL" if poste in ("LT", "LG", "C", "RG", "RT") else poste


def facteur_fatigue(energie):
    if energie is None or energie >= FATIGUE_SEUIL:
        return 1.0
    return 1.0 + FATIGUE_MAX * (FATIGUE_SEUIL - max(0.0, energie)) / FATIGUE_SEUIL


def facteur_age(age):
    if age is None or age <= AGE_SEUIL:
        return 1.0
    return 1.0 + AGE_PENTE * (age - AGE_SEUIL)


def expositions(action, sur_le_terrain):
    """Poids de contact de chaque joueur sur le terrain pour une action de l'attaque.

    action         : entrée du journal (play_type, outcome, yards_gained, carrier_id, passer_id, credited_category)
    sur_le_terrain : [(id, poste, côté "off"/"def")] ; le plaqueur crédité : action["tackler_id"] (id, s'il est connu)
    Renvoie {id: poids} (sans ECHELLE, ni fatigue, ni âge)."""
    porteur = action.get("carrier_id")
    plaqueur = action.get("tackler_id")
    cat = action.get("credited_category")
    sack = cat == "SACK" or action.get("outcome") == "SACK"
    plaque = cat in ("TACKLE", "SACK") or action.get("outcome") in ("RUN", "PASS_COMPLETE", "SACK")
    gros = abs(action.get("yards_gained") or 0) >= GROS_GAIN_YARDS
    out = {}
    for i, poste, cote in sur_le_terrain:
        w = RISQUE.get(famille(poste), 0.5)
        if sack and i == action.get("passer_id"):
            w *= SACK_QB
        elif i == porteur and plaque:
            w *= PORTEUR * (GROS_GAIN if gros else 1.0)
        elif i == plaqueur:
            w *= (SACKEUR if sack else PLAQUEUR) * (GROS_GAIN if gros else 1.0)
        out[i] = w
    return out


def gravite(rng):
    x, acc = rng.random(), 0.0
    for g, semaines, p in GRAVITE:
        acc += p
        if x < acc:
            return g, semaines
    return GRAVITE[-1][0], GRAVITE[-1][1]


def partie(rng, g):
    poids = PARTIES[g]
    return rng.choices(list(poids), weights=list(poids.values()))[0]


def blessure(rng):
    """Une blessure tirée : {"part", "severity", "weeks", "snaps"} (snaps : légère seulement)."""
    g, semaines = gravite(rng)
    p = partie(rng, g)
    if p == "concussion" and g == LEGERE:          # jamais légère
        g = MATCH
    snaps = rng.randint(*SNAPS_LEGERE) if g == LEGERE else None
    return {"part": p, "severity": g, "weeks": semaines, "snaps": snaps}


def tirer(rng, poids, energie=None, age=None, proteges=()):
    """Les blessures de l'action : [(id, blessure)] (au plus une par action — un arrêt de jeu).

    poids    : {id: poids de contact} (expositions) ; energie / age : {id: valeur} (facultatifs)
    proteges : joueurs qui ne peuvent pas se blesser (le dernier QB valide)."""
    energie, age = energie or {}, age or {}
    tirs = []
    for i in sorted(poids):                          # ordre fixe : même tirage pour une même action
        p = ECHELLE * poids[i] * facteur_fatigue(energie.get(i)) * facteur_age(age.get(i))
        tirs.append((rng.random(), p, i))
    touches = [(x / p, i) for x, p, i in tirs if x < p and i not in proteges]
    if not touches:
        return []
    _, i = min(touches)                              # le plus « touché » des joueurs atteints
    return [(i, blessure(rng))]


def resume(blessures):
    """{"n", "minor", "game", "weeks", "par_famille"} pour un ensemble de blessures [{"pos", "severity"}]."""
    out = {"n": len(blessures), LEGERE: 0, MATCH: 0, SEMAINES: 0, "par_famille": {}}
    for b in blessures:
        out[b["severity"]] += 1
        f = famille(b.get("pos", "?"))
        out["par_famille"][f] = out["par_famille"].get(f, 0) + 1
    return out


# ---------- 7.4.2 : l'infirmerie ----------
ECART_JOUEUR_LIBRE = 10                    # points sous le titulaire qu'il remplace
NOTE_MIN, NOTE_MAX = 40, 99


def absents(infirmerie):
    """{id: fiche} des joueurs absents cette semaine (weeks_left > 0)."""
    return {i: f for i, f in (infirmerie or {}).items() if f.get("weeks_left", 0) > 0}


def infirmerie_suivante(infirmerie, nouvelles, semaine, valides=None):
    """L'infirmerie de la semaine suivante : les absents de cette semaine ont manqué une semaine de plus, les blessures
    de « semaines » de cette semaine s'ajoutent (la plus longue l'emporte).

    infirmerie : {id: fiche} au début de la semaine jouée · nouvelles : [blessure du match] (id, name, team, pos, part,
    severity, weeks) · semaine : n° de la semaine jouée · valides : {id: nom} des joueurs encore dans la ligue (un
    retraité remplacé par sa recrue sort de l'infirmerie ; None : pas de contrôle)."""
    out = {}
    for i, f in (infirmerie or {}).items():
        reste = f.get("weeks_left", 0) - 1
        if reste > 0:
            out[i] = dict(f, weeks_left=reste)
    for b in nouvelles:
        if b.get("severity") != SEMAINES or b.get("weeks", 0) <= 0:
            continue
        f = out.get(b["id"])
        if f is None or b["weeks"] > f["weeks_left"]:
            out[b["id"]] = {"name": b["name"], "team": b["team"], "pos": b["pos"], "part": b["part"],
                            "weeks_left": b["weeks"], "weeks": b["weeks"], "since_week": semaine}
    if valides is not None:
        out = {i: f for i, f in out.items() if valides.get(i) == f["name"]}
    return dict(sorted(out.items()))


def signatures(joueurs, absents_ids):
    """Joueurs libres à signer pour une équipe : [(poste, id remplacé)].

    joueurs : [(id, poste, remplaçant: bool)] de l'équipe (titulaires puis banc) · absents_ids : ids absents.
    Une famille de postes signe autant de joueurs libres qu'elle a d'absents en plus de ses remplaçants valides."""
    out = []
    par_famille = {}
    for i, poste, banc in joueurs:
        par_famille.setdefault(famille(poste), []).append((i, poste, banc))
    for fam, js in par_famille.items():
        partis = [(i, poste) for i, poste, _ in js if i in absents_ids]
        valides = [i for i, _, banc in js if banc and i not in absents_ids]
        for i, poste in partis[len(valides):]:
            out.append((poste, i))
    return out


def notes_joueur_libre(notes_titulaire):
    """Notes d'un joueur libre : celles du titulaire qu'il remplace, ECART_JOUEUR_LIBRE points plus bas."""
    return {k: max(NOTE_MIN, min(NOTE_MAX, int(v) - ECART_JOUEUR_LIBRE)) for k, v in notes_titulaire.items()}
