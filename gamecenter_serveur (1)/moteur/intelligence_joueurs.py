"""Intelligence des joueurs (bloc C) : receveurs et défenseurs, au-delà de leurs notes d'unité.

Receveurs (WR, TE, RB) — 6 attributs :
    route_iq              précision de la route : petit écart entre la route dessinée et la route courue (moins de
                          dispersion, cassure au bon endroit)
    release               se libère du jam à la ligne (press, couverture homme)
    separation            crée l'écart à la cassure (vitesse, explosivité)
    coverage_recognition  reconnaît zone / homme : se pose dans le trou de la zone, joue le levier en homme
    catch_in_traffic      réception sous pression : capte avec un défenseur qui arrive (fenêtre serrée)
    contested_catch       gagne le ballon disputé (receveur couvert ou doublé)

Défenseurs (CB, S, LB) — 7 attributs :
    play_recognition      reconnaît le jeu : play action, screen (ne mord pas, ne se fait pas bloquer)
    zone_iq               tient sa zone, lit les yeux du QB, ferme le trou
    man_iq                colle son receveur en homme (jam, technique)
    awareness             voit la soupape et la route « hot », plus d'interceptions sur les ballons disputés
    reaction              réagit à la cassure (ferme l'écart, arrive sur le ballon)
    discipline            garde sa responsabilité : ne laisse pas de « coverage bust » (receveur oublié)
    pursuit               poursuite après la réception (moins de yards après le catch)

Abstraction statistique, pas de physique fine (programme, bloc C) : les attributs déplacent la SÉPARATION de l'état
post-snap (moteur.reaction_defensive, avant la lecture du QB), la RÉCEPTION (multiplicateurs d'incomplète et
d'interception transmis à la résolution) et les YARDS APRÈS LA RÉCEPTION. L'écart entre route dessinée et route
réelle est un tirage dont la moyenne et la dispersion dépendent du route_iq ; un « coverage bust » (le défenseur
mord sur le play action, perd son receveur) arrive plus souvent contre un défenseur peu discipliné.

Les rosters n'ont que 4 notes par poste : comme pour le QB (bloc B), les attributs absents sont DÉRIVÉS des notes
(resserrés autour de 80), de l'identité de la franchise (PROFILS) et d'un petit écart propre au joueur (hash de son
id). Une clé du même nom dans les notes est prise telle quelle. Ils ne s'ajoutent PAS aux notes (OVR, notes
d'unité, cotes d'avant-match inchangés) ; le GameFeed les exporte à part (roster[].player_iq).
Ce qui pèse, c'est le PROFIL du joueur : l'écart d'un attribut à son propre NIVEAU (ses notes de route ou de
couverture, celles du duel du bloc A, ramenées sur l'échelle des attributs). Le niveau, lui, est déjà dans le duel de
notes du bloc A (moteur.reaction_defensive) : le recompter doublait l'écart entre les franchises (au test 12.3, MNL et
ses DB les plus faibles de la ligue tombaient à 36-41 %). Un CB de 90 reste meilleur qu'un CB de 75 (bloc A) ; le
bloc C dit en plus s'il est meilleur en homme qu'en zone, discipliné ou joueur, vif sur la cassure… Seule une part
POIDS de cet écart pèse (POIDS_NIVEAU : part du niveau, 0 par défaut).
"""
from .reaction_defensive import talent_route, talent_couverture
import random

from .aleatoire import gauss_borne
from .reaction_defensive import (LIBRE, SERRE, COUVERT, DOUBLE, SEUIL_LIBRE, SEUIL_SERRE,
                                 _affectations_homme, _defenseurs_zone)

ATTRIBUTS_RECEVEUR = ("route_iq", "release", "separation", "coverage_recognition", "catch_in_traffic",
                      "contested_catch")
ATTRIBUTS_DEFENSEUR = ("play_recognition", "zone_iq", "man_iq", "awareness", "reaction", "discipline", "pursuit")
LIBELLES = {"route_iq": "Route IQ", "release": "Release", "separation": "Separation",
            "coverage_recognition": "Zone / man recognition", "catch_in_traffic": "Catch in traffic",
            "contested_catch": "Contested catch", "play_recognition": "Play recognition", "zone_iq": "Zone IQ",
            "man_iq": "Man IQ", "awareness": "Awareness", "reaction": "Reaction", "discipline": "Discipline",
            "pursuit": "Pursuit"}
POSTES_RECEVEUR = ("WR", "TE", "RB")
POSTES_DEFENSEUR = ("CB", "S", "LB")

# attribut -> {note: poids} par poste ; « ajust » : décalage du poste (un RB n'est pas un receveur de métier)
DERIVATION = {
    "WR": {"route_iq": {"route_running": 0.8, "catching": 0.2},
           "release": {"acceleration": 0.5, "route_running": 0.3, "speed": 0.2},
           "separation": {"speed": 0.45, "acceleration": 0.35, "route_running": 0.2},
           "coverage_recognition": {"route_running": 0.6, "catching": 0.4},
           "catch_in_traffic": {"catching": 0.8, "route_running": 0.2},
           "contested_catch": {"catching": 0.7, "acceleration": 0.2, "speed": 0.1}},
    "TE": {"route_iq": {"route_running": 0.8, "catching": 0.2},
           "release": {"run_block": 0.4, "route_running": 0.3, "speed": 0.3},
           "separation": {"speed": 0.6, "route_running": 0.4},
           "coverage_recognition": {"route_running": 0.6, "catching": 0.4},
           "catch_in_traffic": {"catching": 0.7, "run_block": 0.3},
           "contested_catch": {"catching": 0.6, "run_block": 0.4}},
    "RB": {"route_iq": {"elusiveness": 0.4, "acceleration": 0.3, "speed": 0.3, "ajust": -4},
           "release": {"acceleration": 0.6, "elusiveness": 0.4},
           "separation": {"speed": 0.4, "acceleration": 0.3, "elusiveness": 0.3},
           "coverage_recognition": {"elusiveness": 0.5, "acceleration": 0.5, "ajust": -3},
           "catch_in_traffic": {"power": 0.5, "elusiveness": 0.5, "ajust": -2},
           "contested_catch": {"power": 0.6, "elusiveness": 0.4, "ajust": -4}},
    "CB": {"play_recognition": {"coverage": 0.6, "tackling": 0.4},
           "zone_iq": {"coverage": 0.85, "acceleration": 0.15},
           "man_iq": {"coverage": 0.6, "speed": 0.25, "acceleration": 0.15},
           "awareness": {"coverage": 0.6, "tackling": 0.4},
           "reaction": {"acceleration": 0.5, "coverage": 0.3, "speed": 0.2},
           "discipline": {"coverage": 0.5, "tackling": 0.5},
           "pursuit": {"speed": 0.6, "tackling": 0.4}},
    "S":  {"play_recognition": {"coverage": 0.4, "run_support": 0.4, "tackling": 0.2},
           "zone_iq": {"coverage": 0.8, "run_support": 0.2},
           "man_iq": {"coverage": 0.6, "speed": 0.4},
           "awareness": {"coverage": 0.6, "tackling": 0.2, "run_support": 0.2},
           "reaction": {"speed": 0.5, "coverage": 0.5},
           "discipline": {"tackling": 0.4, "run_support": 0.3, "coverage": 0.3},
           "pursuit": {"speed": 0.5, "tackling": 0.5}},
    "LB": {"play_recognition": {"coverage": 0.4, "tackling": 0.4, "strength": 0.2},
           "zone_iq": {"coverage": 0.8, "tackling": 0.2},
           "man_iq": {"coverage": 0.5, "speed": 0.5, "ajust": -3},
           "awareness": {"coverage": 0.5, "tackling": 0.5},
           "reaction": {"speed": 0.6, "coverage": 0.4},
           "discipline": {"tackling": 0.5, "coverage": 0.3, "strength": 0.2},
           "pursuit": {"speed": 0.5, "tackling": 0.5}},
}
NIVEAU, COMPRESSION = 80, 0.5     # attribut dérivé = 80 + 50 % de l'écart des notes à 80 (comme le QB, bloc B)
ECART_JOUEUR = 3                  # écart propre au joueur : ± 3 points au plus

# identité des franchises (programme 12.1) : ce qui distingue leurs joueurs à notes égales
PROFILS = {
    "CTX": {"route_iq": 3, "coverage_recognition": 4,                                   # intelligence, instinct
            "play_recognition": 4, "awareness": 2, "zone_iq": 1},
    "VEC": {"release": 1, "separation": 1,                                              # précision, prise de risque
            "reaction": 4, "man_iq": 3, "discipline": -6},
    "AEG": {"route_iq": 2, "catch_in_traffic": 2,                                       # discipline, protection
            "zone_iq": 4, "discipline": 6, "awareness": 2},
    "MNL": {"contested_catch": 6, "catch_in_traffic": 4, "release": 2,                  # physique, force
            "pursuit": 5, "man_iq": 4, "reaction": 2, "discipline": 2, "play_recognition": 2},
    # étape 6 (franchises 05-08 de la bible des identités)
    "AXM": {"route_iq": 4, "coverage_recognition": 2, "catch_in_traffic": 2,               # précision, timing
            "zone_iq": 2, "discipline": 3, "awareness": 1},
    "GLT": {"release": 1,                                                               # chaos : presse et parie
            "man_iq": 4, "reaction": 3, "pursuit": 2, "discipline": -5},
    "CPH": {"separation": 2, "release": 1,                                              # espace, athlétisme
            "pursuit": 3, "reaction": 2, "play_recognition": 1},
    "NVA": {"separation": 2, "contested_catch": 3, "route_iq": -1,                       # verticale ; défense profonde
            "zone_iq": 3, "awareness": 3, "discipline": 2},
    # palier 2 (franchises 09-12)
    "PLS": {"release": 2, "separation": 1, "route_iq": 2,                                 # rythme : tout va vite
            "pursuit": 2, "reaction": 1, "discipline": -1},
    "ONX": {"catch_in_traffic": 1,                                                      # chasse au ballon
            "zone_iq": 5, "awareness": 5, "reaction": 4, "play_recognition": 4, "man_iq": 2, "discipline": -2},
    "FRG": {"contested_catch": 3, "catch_in_traffic": 3, "separation": -1,              # physique
            "pursuit": 2, "play_recognition": 2, "discipline": 2},
    "MRD": {"route_iq": 2, "catch_in_traffic": 1,                                       # discipline, zone
            "zone_iq": 4, "discipline": 5, "awareness": 2},
    # palier 3 (franchises 13-16)
    "APX": {"contested_catch": 3, "catch_in_traffic": 3, "route_iq": 1,                 # espaces réduits
            "man_iq": 2, "play_recognition": 2, "discipline": 1},
    "LTC": {"separation": 2, "release": 2, "route_iq": 2,                                # espacement, YAC
            "zone_iq": 2, "reaction": 2, "discipline": 2},
    "ZPH": {"route_iq": 3, "separation": 2, "catch_in_traffic": 2,                       # volume, distribution
            "zone_iq": 2, "awareness": 1},
    "BST": {"release": 1,                                                               # couverture verrouillée
            "man_iq": 6, "zone_iq": 4, "awareness": 4, "reaction": 3, "discipline": 4},
}

# ---- poids des attributs (en « pas » de séparation, pour 10 points d'écart EFFECTIF) ----
REF = 80
POIDS = 0.45                      # part de l'écart d'un attribut au niveau du joueur qui pèse
POIDS_NIVEAU = 0.0                # part de l'écart du niveau à REF (déjà dans le duel de notes du bloc A)
C = {
    "release": 0.30,              # release contre man_iq (homme) ; en zone : ZONE_RELEASE de l'effet
    "zone_release": 0.25,
    "separation": 0.30,           # separation contre reaction, à la cassure (court : moitié)
    "reconnaissance": 0.30,       # coverage_recognition contre zone_iq (zone) / man_iq (homme, moitié)
    "soupape": 0.20,              # awareness du défenseur sur le checkdown et la route « hot »
    "screen": 0.35,               # play_recognition contre le screen
    # écart entre route dessinée et route courue : moyenne et dispersion selon le route_iq
    "route_moy": 0.15, "route_sigma": 0.55, "route_sigma_pente": 1 / 30, "route_sigma_min": 0.30,
    "route_sigma_max": 0.85,
    # coverage bust : le défenseur perd son receveur (mord sur le play action, double move, mauvaise passation)
    "bust_base": 0.008, "bust_discipline": 1 / 18, "bust_lecture": 1 / 30, "bust_pa": 2.2,
    "bust_double_move": 1.5, "bust_min": 0.002, "bust_max": 0.08, "bust_sep": 1.7,
    "bust_plancher": 1.6,         # receveur oublié : seul (libre, même s'il était doublé)
    # réception (multiplicateurs transmis à moteur.resolution)
    "libre_inc": 0.03,            # route au bon endroit : moins de ballons perdus sur un receveur libre
    "trafic_inc": 0.10, "trafic_int": 0.08,          # catch_in_traffic contre reaction
    "dispute_inc": 0.12, "dispute_int": 0.10,        # contested_catch contre man_iq / zone_iq ; awareness
    "mod_min": 0.6, "mod_max": 1.5,
    # yards après la réception : separation contre pursuit (yards pour 10 points d'écart effectif)
    "yac": 0.9, "yac_max": 3.0,
}
BRUIT_C = 0.65                    # bruit générique de la séparation au bloc C (l'écart de route prend le reste)
ECHELLE_C = 20.0                  # points de note pour un « pas » de séparation au bloc C (comme au bloc A : le niveau
                                  # reste dans le duel de notes)
CONCEPTS_PA = {"PLAY_ACTION", "BOOT", "POP"}
DOUBLE_MOVES = {"CORNER", "POST", "FLAG", "GO"}
OUVERT, TRAFIC, DISPUTE = "open", "traffic", "contested"


def _borne(x, a, b):
    return max(a, min(b, x))


def _rng_joueur(joueur, nature):
    return random.Random(f"{nature}|{(joueur or {}).get('id', '')}")


def _derive(joueur, poste, attributs, franchise, nature):
    r = (joueur or {}).get("ratings") or {}
    regles = DERIVATION[poste]
    profil = PROFILS.get(franchise or "", {})
    rng = _rng_joueur(joueur, nature)
    out = {}
    for a in attributs:
        ecart = rng.randint(-ECART_JOUEUR, ECART_JOUEUR)          # toujours tiré : l'ordre ne dépend pas des notes
        if a in r:
            out[a] = int(round(_borne(float(r[a]), 30, 99)))
            continue
        w = regles[a]
        base = sum(p * float(r.get(k, 75)) for k, p in w.items() if k != "ajust")
        v = NIVEAU + COMPRESSION * (base - NIVEAU) + w.get("ajust", 0) + profil.get(a, 0) + ecart
        out[a] = int(round(_borne(v, 30, 99)))
    return out


def attributs_receveur(joueur, poste="WR", franchise=None):
    """{attribut: note 30-99} d'un receveur (WR, TE ou RB) — {"id", "ratings"}."""
    return _derive(joueur, poste if poste in POSTES_RECEVEUR else "WR", ATTRIBUTS_RECEVEUR, franchise, "rec-iq")


def attributs_defenseur(joueur, poste="CB", franchise=None):
    """{attribut: note 30-99} d'un défenseur de couverture (CB, S ou LB)."""
    return _derive(joueur, poste if poste in POSTES_DEFENSEUR else "CB", ATTRIBUTS_DEFENSEUR, franchise, "def-iq")


def attributs_joueur(joueur, poste, franchise=None):
    """Attributs du bloc C d'un joueur, ou None pour un poste qui n'en a pas."""
    if poste in POSTES_RECEVEUR:
        return attributs_receveur(joueur, poste, franchise)
    if poste in POSTES_DEFENSEUR:
        return attributs_defenseur(joueur, poste, franchise)
    return None


def niveau(joueur):
    """Niveau du joueur sur l'échelle des attributs : ses notes de route (receveur) ou de couverture (défenseur),
    celles du duel du bloc A, resserrées autour de 80 comme les attributs dérivés. REF sans notes."""
    r = (joueur or {}).get("ratings") or {}
    iq = (joueur or {}).get("iq") or {}
    if not r:
        return float(REF)
    if "route_iq" in iq:
        t = talent_route(joueur, "WR" if "route_running" in r else "RB")
    elif "coverage" in r or "zone_iq" in iq:
        t = talent_couverture(joueur)
    else:
        return float(REF)
    return NIVEAU + COMPRESSION * (t - NIVEAU)


def _e(joueur, cle):
    """Écart EFFECTIF d'un attribut : POIDS × (attribut − niveau du joueur) + POIDS_NIVEAU × (niveau − REF) ;
    0 sans attributs."""
    v = ((joueur or {}).get("iq") or {}).get(cle)
    if v is None:
        return 0.0
    n = niveau(joueur)
    return POIDS * (float(v) - n) + POIDS_NIVEAU * (n - REF)


def _statut(sep, double):
    if double:
        return LIBRE if sep >= 1.5 else DOUBLE
    return LIBRE if sep >= SEUIL_LIBRE else SERRE if sep >= SEUIL_SERRE else COUVERT


def couvreurs(etat, lectures, defenseurs, rng):
    """Défenseur responsable de chaque receveur : en homme, celui de l'affectation ; en zone, un défenseur de la
    tranche attaquée (tirage dans le flux du bloc C)."""
    roles = [l["role"] for l in lectures]
    if etat.famille == "homme":
        aff = _affectations_homme(roles, defenseurs, etat.couverture)
        return {r: aff.get(r) for r in roles}
    out = {}
    for l in lectures:
        zone = [d for d in _defenseurs_zone(l["classe"], defenseurs) if d]
        out[l["role"]] = zone[int(rng.random() * len(zone))] if zone else None
    return out


def ajuster_post_snap(etat, lectures, receveurs, defenseurs, concept, rng):
    """Bloc C : la séparation de chaque receveur selon son intelligence et celle du défenseur responsable.

    Modifie etat.receveurs (séparation, statut, couvreur, bust, écart de route) ; renvoie {rôle: défenseur}.
    rng : flux dédié du bloc C (le flux des décisions du QB n'est pas consommé).
    """
    qui = couvreurs(etat, lectures, defenseurs, rng)
    lb = (defenseurs.get("LB") or [None])[0]
    for l in lectures:
        role = l["role"]
        e = etat.receveurs[role]
        j, d = receveurs.get(role) or {}, qui.get(role) or {}
        homme = etat.famille == "homme"
        delta = 0.0
        if l["route"] != "SCREEN":
            rel = C["release"] * (_e(j, "release") - _e(d, "man_iq")) / 10
            delta += rel if homme else C["zone_release"] * rel
            k = 0.5 if l["classe"] == "court" else 1.0
            delta += k * C["separation"] * (_e(j, "separation") - _e(d, "reaction")) / 10
            if homme:
                delta += 0.5 * C["reconnaissance"] * (_e(j, "coverage_recognition") - _e(d, "man_iq")) / 10
            else:
                delta += C["reconnaissance"] * (_e(j, "coverage_recognition") - _e(d, "zone_iq")) / 10
        else:
            delta -= C["screen"] * _e(lb, "play_recognition") / 10
        if l["niveau"] == "checkdown" or (etat.rushers >= 5 and l["classe"] == "court"):
            delta -= C["soupape"] * _e(d, "awareness") / 10
        # écart entre la route dessinée et la route courue
        riq = _e(j, "route_iq")
        sigma = _borne(C["route_sigma"] * (1 - riq * C["route_sigma_pente"]), C["route_sigma_min"], C["route_sigma_max"])
        ecart_route = C["route_moy"] * riq / 10 + gauss_borne(rng, sigma, 2.0)
        delta += ecart_route
        # coverage bust : le défenseur responsable perd son receveur
        p = C["bust_base"] * (1 - _e(d, "discipline") * C["bust_discipline"]) * (1 - _e(d, "play_recognition") * C["bust_lecture"])
        if concept in CONCEPTS_PA:
            p *= C["bust_pa"]
        if l["route"] in DOUBLE_MOVES:
            p *= C["bust_double_move"]
        bust = l["route"] != "SCREEN" and rng.random() < _borne(p, C["bust_min"], C["bust_max"])
        if bust:
            delta += C["bust_sep"]
        sep = e.separation + delta
        if bust:
            sep = max(sep, C["bust_plancher"])
        e.separation = round(sep, 2)
        e.statut = _statut(e.separation, role == etat.double_sur)
        e.couvreur_id, e.couvreur_nom = d.get("id", ""), d.get("name", "")
        e.bust, e.ecart_route = bust, round(ecart_route, 2)
    return qui


def modificateurs_reception(receveur, defenseur, statut, famille):
    """(m_int, m_inc, type de réception) d'un ballon lancé, selon le receveur et le défenseur responsable.

    libre : open · serré : traffic (réception sous pression) · couvert / double : contested (ballon disputé)."""
    m_int = m_inc = 1.0
    if statut == LIBRE:
        m_inc *= 1 - C["libre_inc"] * _e(receveur, "route_iq") / 10
        kind = OUVERT
    elif statut == SERRE:
        g = (_e(receveur, "catch_in_traffic") - _e(defenseur, "reaction")) / 10
        m_inc *= 1 - C["trafic_inc"] * g
        m_int *= 1 - C["trafic_int"] * g
        kind = TRAFIC
    else:
        cle = "man_iq" if famille == "homme" else "zone_iq"
        g = (_e(receveur, "contested_catch") - _e(defenseur, cle)) / 10
        m_inc *= 1 - C["dispute_inc"] * g
        m_int *= 1 + C["dispute_int"] * (_e(defenseur, "awareness") - _e(receveur, "contested_catch")) / 10
        kind = DISPUTE
    return (round(_borne(m_int, C["mod_min"], C["mod_max"]), 4), round(_borne(m_inc, C["mod_min"], C["mod_max"]), 4),
            kind)


def yards_apres_reception(receveur, defenseur):
    """Yards ajoutés après la réception : separation du receveur contre pursuit du défenseur (borné)."""
    y = C["yac"] * (_e(receveur, "separation") - _e(defenseur, "pursuit")) / 10
    return _borne(y, -C["yac_max"], C["yac_max"])
