# ============================================================
# NFL SIM — 12.2 quattuortricies — CAUSAL LÉGER, BLOC 4 : LA POCHE (07/11/2026)
# ============================================================
# Programme « causal léger, bloc par bloc » (décision de Guillaume, 05/11/2026). Blocs 1 à 3 (12.2 untricies à
# tritricies) : la course après le contact, après la réception, la couverture. Bloc 4 : le temps avant la pression.
#
# Avant : le temps avant la pression était tiré (bloc A : base, niveau des unités, rushers, appel, bruit), puis la poche
# (12.2 vicies ter, moteur/poche.py) désignait le duel perdu à cet instant. Maintenant, pour une passe d'un QB du bloc B
# (la poche existe) :
#   - chaque duel (EDGE contre tackle, DT contre guard, centre qui double, blitzeurs pris ou libres) est joué sur le
#     terrain (moteur/poche_spatiale.py) : contact, défaite du bloc selon la marge (pass_rush, force contre pass_block,
#     force), enfoncement à l'intérieur, course jusqu'au QB ; le bord fait le tour (chemin plus long) ; un blitzeur libre
#     fonce, parfois ramassé tard ;
#   - le premier arrivé fait la pression et c'est le duel perdu ; les autres cèdent à leur instant ;
#   - son temps est ramené à l'échelle du moteur par une droite par nombre de rushers (calibrée : la ligue garde la
#     moyenne et la dispersion du temps avant la pression d'avant).
# Le reste ne change pas : décision et lecture du QB (bloc B), réaction dans la poche, couverture (bloc 3), complétion,
# sack. Hasard : flux « poche-spatiale|<graine>|<n° d'action> » (le hasard du moteur n'est pas consommé).
# Interrupteur POCHE_SPATIALE_ENABLED (GC_POCHE_SPATIALE=0 : moteur d'avant, à l'identique, contrôlé ci-dessous).

import importlib as _ps_il
import json as _ps_json
import os as _ps_os

POCHE_SPATIALE_ENABLED = bool(moteur) and _ps_os.environ.get("GC_POCHE_SPATIALE", "1") != "0"
if moteur:
    import moteur.poche
    import moteur.poche_spatiale
    PSP = _ps_il.reload(moteur.poche_spatiale)
    if _ps_os.environ.get("GC_PS_PARAMS"):                       # calibration (outils/moteur/semaine_course_spatiale.py)
        _ps_p = _ps_json.loads(_ps_os.environ["GC_PS_PARAMS"])
        if "droite" in _ps_p:
            _ps_p["droite"] = {int(k): tuple(v) for k, v in _ps_p["droite"].items()}
        PSP.PARAMS.update(_ps_p)

_ps_sig = lambda g: [(e.get("kind"), e.get("play_id"), e.get("carrier_id"), e.get("yards_gained"), e.get("outcome"),
                      ((e.get("decision") or {}).get("pocket") or {}).get("ttp")) for e in g["play_log"]]
if "_PS_REF" not in globals():
    _PS_REF_MATCHS = (("MNL", "CTX", 34_001), ("VEC", "PRM", 34_002))
    moteur.poche.SIMULATION = None
    _PS_REF = [(_g["home_score"], _g["away_score"], _ps_sig(_g)) for _g in
               (franchise_game(h, a, seed=s) for h, a, s in _PS_REF_MATCHS)]


def _ps_simuler(duels, graine, n, rushers, rush, ancien=None):
    """Les duels de protection joués sur le terrain : instant de chaque rusher, temps avant la pression."""
    return PSP.simuler(duels, graine, n, rushers, rush=rush)


def _ps_brancher(actif):
    if moteur:
        moteur.poche.SIMULATION = _ps_simuler if actif else None


_ps_brancher(POCHE_SPATIALE_ENABLED)

# ---------- contrôles ----------
if moteur:
    # 1. coupé : le moteur d'avant à l'identique
    _ps_brancher(False)
    _ps_off = [franchise_game(h, a, seed=s) for h, a, s in _PS_REF_MATCHS]
    assert [(_g["home_score"], _g["away_score"], _ps_sig(_g)) for _g in _ps_off] == _PS_REF, "poche spatiale coupée : moteur changé"
    _ps_brancher(POCHE_SPATIALE_ENABLED)
    # 2. allumé : déterministe, des temps avant la pression simulés
    if POCHE_SPATIALE_ENABLED:
        _ps_a, _ps_b = (franchise_game(*_PS_REF_MATCHS[0][:2], seed=_PS_REF_MATCHS[0][2]) for _ in range(2))
        assert _ps_sig(_ps_a) == _ps_sig(_ps_b), "poche spatiale non déterministe"
        _ps_t = [((e.get("decision") or {}).get("pocket") or {}).get("ttp") for e in _ps_a["play_log"]]
        _ps_t = [t for t in _ps_t if t is not None]
        assert len(_ps_t) > 15 and len(set(_ps_t)) > 5, _ps_t
    print(f"✅ 12.2 quattuortricies — poche {'jouée sur le terrain' if POCHE_SPATIALE_ENABLED else 'coupée'}")
else:
    print("⚠️ 12.2 quattuortricies — moteur/ introuvable : poche d'avant")
