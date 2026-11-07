"""Causal léger, bloc 4 : la poche, duels de protection joués sur le terrain (07/11/2026).

Avant ce bloc, le temps avant la pression d'une passe était tiré (moteur/reaction_defensive.py : base, niveau de
pression des unités, rushers, appel, bruit), puis moteur/poche.py désignait le duel perdu à cet instant, d'autant plus
probable que la marge du rusher sur son bloqueur était grande. Un tackle dominant changeait qui arrivait, pas quand.

Ici chaque duel de la passe (moteur.poche.affecter : EDGE contre tackle, DT contre guard, centre qui double, blitzeurs
pris par le centre, le RB ou le TE, sinon libres) est joué au pas de DT secondes :
  DÉPART    le QB recule à sa profondeur (drop) ; chaque rusher part de sa place : le bord est large (arc plus long),
            l'intérieur est en face du guard, le blitzeur au deuxième niveau ;
  ENGAGÉ    le bloqueur le prend ; à chaque pas le rusher peut se défaire du bloc, d'autant plus vite que sa marge
            (pass_rush, force contre pass_block, force) est grande ; à l'intérieur il enfonce aussi le bloqueur vers le
            QB (bull rush), selon la même marge ; une double équipe le freine (marge déjà réduite par moteur.poche) ;
  LIBRE     défait (ou sans bloqueur), il court sur le QB à sa vitesse ;
  PRESSION  quand il entre dans le rayon du QB. Le premier arrivé fait la pression ; c'est le duel perdu.
Le temps du premier est ramené à l'échelle du moteur par une droite par nombre de rushers, calibrée pour que la ligue
garde la moyenne et la dispersion du temps avant la pression d'avant (sacks, pression, complétion inchangés).
Hasard : flux « poche-spatiale|<graine>|<n° d'action> » (le hasard du moteur n'est pas consommé).
"""
import math

from . import aleatoire

VERSION = "poche-spatiale-1"

DT = 0.05
PARAMS = {
    "drop": 7.0,                 # yards : profondeur du QB derrière la ligne
    "rayon": 1.5,                # yards : la pression arrive quand un rusher entre dans ce rayon
    "engage": 0.35,              # s : le temps de prendre contact
    "taux": 0.42,                # défaites par seconde à marge nulle
    "k_taux": 0.10,              # facteur exp(marge * k) sur ce taux (marge en points de note)
    "arc": 1.35,                 # le bord fait le tour : chemin plus long
    "pousse": 0.55,              # yards par seconde d'enfoncement à l'intérieur, à marge nulle
    "k_pousse": 0.05,            # par point de marge
    "vitesse_libre": 7.0,        # yards par seconde d'un rusher défait (ligne) ; blitzeur : sa note de vitesse
    "reaction_libre": 0.25,      # s : le blitzeur libre lit le snap
    "ramasse": 0.4,              # part des blitzeurs libres ramassés tard par une ligne qui glisse
    "ramasse_marge": 8.0,        # marge du blitzeur ramassé (il a l'élan, le bloqueur est en retard)
    "trafic": 0.8,               # s : retard au plus d'un blitzeur libre à travers le trafic
    "t_max": 8.0,
    # droite temps simulé -> temps avant la pression du moteur, par nombre de rushers (3, 4, 5, 6 et plus)
    "droite": {3: (0.0, 1.0), 4: (0.0, 1.0), 5: (0.0, 1.0), 6: (0.0, 1.0)},
}
VITESSE_POSTE = {"EDGE": 7.6, "DT": 6.8, "LB": 8.0, "S": 8.4, "CB": 8.6}
PREFERENCE_RUSH = {"EDGE_RUSH": "edge", "INTERIOR_COLLAPSE": "interior", "INTERIOR_STUNT": "interior",
                   "TEX_STUNT": "interior", "ET_STUNT": "interior", "LONG_STUNT": "interior", "CONTAIN_RUSH": "interior"}


def _vitesse(r):
    rr = (r or {}).get("ratings") or {}
    if "speed" in rr:
        return 8.5 + (float(rr["speed"]) - 80.0) * 0.06
    return VITESSE_POSTE.get((r or {}).get("pos"), 7.2)


def duel(d, rng, params=PARAMS, rush=None):
    """Instant (s après le snap) où ce rusher atteint le QB ; d : un duel de moteur.poche.affecter."""
    P = params
    r = d.get("rusher") or {}
    marge = max(-30.0, min(30.0, float(d.get("marge", 0.0))))
    pref = PREFERENCE_RUSH.get(rush or "")
    if pref and d.get("type") == pref:
        marge += 3.0                                      # le jeu de rush vise ce type de duel
    v = _vitesse(r)
    if d.get("libre"):                                    # personne ne le prend d'office
        if rng.random() < P["ramasse"]:                   # la ligne glisse : il est ramassé tard
            d = dict(d, libre=False, marge=marge + P["ramasse_marge"], type="interior")
        else:                                             # il lit le snap et fonce, à travers le trafic
            dist = P["drop"] + (5.0 if r.get("pos") in ("S", "CB") else 3.5) - P["rayon"]
            return P["reaction_libre"] + dist / v + rng.uniform(0.0, P["trafic"])
    bord = d.get("type") == "edge"
    reste = (P["drop"] + 1.0) * (P["arc"] if bord else 1.0) - P["rayon"]   # chemin jusqu'au QB
    t = P["engage"]
    taux = P["taux"] * math.exp(marge * P["k_taux"])
    pousse = 0.0 if bord else max(0.0, P["pousse"] + marge * P["k_pousse"])
    while t < P["t_max"]:
        t += DT
        if rng.random() < taux * DT:                      # il se défait du bloc
            vl = min(v, P["vitesse_libre"]) if r.get("pos") in ("EDGE", "DT") else v
            return t + reste / vl
        reste -= pousse * DT                              # il enfonce le bloqueur vers le QB
        if reste <= 0:
            return t
    return P["t_max"]


def simuler(duels, graine, n, rushers, params=PARAMS, rush=None):
    """Instants de chaque duel et temps avant la pression à l'échelle du moteur : (temps, ttp)."""
    rng = aleatoire.flux("poche-spatiale", graine, n)
    ts = [duel(d, rng, params, rush) for d in duels]
    if not ts:
        return ts, None
    a, b = params["droite"].get(max(3, min(6, int(rushers or 4))), (0.0, 1.0))
    return ts, a + b * min(ts)
