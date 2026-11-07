# ============================================================
# NFL SIM — 12.2 tritricies — CAUSAL LÉGER, BLOC 3 : LA COUVERTURE (06/11/2026)
# ============================================================
# Programme « causal léger, bloc par bloc » (décision de Guillaume, 05/11/2026). Blocs 1 et 2 (12.2 untricies,
# duotricies) : la course après le contact, après la réception. Bloc 3 : la séparation des receveurs.
#
# Avant : séparation d'un receveur (bloc A, moteur/reaction_defensive.py) = écart de notes (route contre couverture) / 20
# + avantage de la route contre la couverture + bruit ; le statut (libre, serré, couvert, doublé) en découle et décide de
# la lecture du QB, de la complétion et de l'interception. Maintenant, le terme d'écart de notes vient d'un duel joué sur
# le terrain (moteur/couverture_spatiale.py) :
#   - le receveur court sa route (tige, cassure), à sa vitesse ; il perd moins de vitesse à la cassure s'il court bien ;
#   - en homme, son défenseur part à son coussin (presse en Cover 0 / 1), recule, se retourne quand le receveur arrive sur
#     lui, réagit à la cassure avec un temps de retard (couverture contre qualité de route), puis fonce ;
#   - en zone, les défenseurs de la tranche tiennent leur repère et ferment sur le receveur qui y entre ; le safety prend
#     la route verticale par-dessus ;
#   - la séparation dans la fenêtre (cassure + 0,6 s, ou l'ouverture de la route) est ramenée à l'échelle du bloc A par une
#     droite calibrée par famille et classe de route : la ligue garde ses taux de receveurs libres et couverts.
# Le reste ne change pas (avantages de couverture, bruit, checkdown, double, blocs B-D). Hasard : flux
# « couverture-spatiale|<graine>|<action>|<rôle> » (le hasard du moteur n'est pas consommé).
# GameFeed (additif, trajectoires étape 6, 07/11/2026) : play.geo.cov = la trace de chaque duel pour le dessin du site
# (moteur.couverture_spatiale.trace_compacte) : {"dt": 0,2, "r": [[rôle, cassure (s), presse 0 / 1, défenseur, chemin du
# receveur, chemin du défenseur], …]}, du snap à la fenêtre, x depuis la ligne de mêlée, y en travers (repères du moteur).
# Interrupteur COUVERTURE_SPATIALE_ENABLED (GC_COUVERTURE_SPATIALE=0 : moteur d'avant, à l'identique, contrôlé ci-dessous).

import importlib as _cv_il
import json as _cv_json
import os as _cv_os

COUVERTURE_SPATIALE_ENABLED = bool(moteur) and _cv_os.environ.get("GC_COUVERTURE_SPATIALE", "1") != "0"
if moteur:
    import moteur.couverture_spatiale
    import moteur.reaction_defensive
    CV = _cv_il.reload(moteur.couverture_spatiale)
    if _cv_os.environ.get("GC_CV_PARAMS"):                       # calibration (outils/moteur/semaine_course_spatiale.py)
        _cv_p = _cv_json.loads(_cv_os.environ["GC_CV_PARAMS"])
        if "droite" in _cv_p:
            _cv_p["droite"] = {tuple(k.split("|")): tuple(v) for k, v in _cv_p["droite"].items()}
        CV.PARAMS.update(_cv_p)

_cv_sig = lambda g: [(e.get("kind"), e.get("play_id"), e.get("carrier_id"), e.get("yards_gained"), e.get("outcome"),
                      (e.get("decision") or {}).get("status")) for e in g["play_log"]]
if "_CV_DEC_BASE" not in globals():
    _CV_DEC_BASE = _DECISION_PASS_HOOK
_CV_TR = {}
if "_CV_REF" not in globals():
    _CV_REF_MATCHS = (("MNL", "CTX", 33_001), ("VEC", "PRM", 33_002))
    moteur.reaction_defensive.DUEL = None
    _CV_REF = [(_g["home_score"], _g["away_score"], _cv_sig(_g)) for _g in
               (franchise_game(h, a, seed=s) for h, a, s in _CV_REF_MATCHS)]


def _cv_duel(role, lecture, joueur, defenseurs, famille, couverture, cle, ancien):
    """Terme de duel de la séparation (bloc A) : le duel joué sur le terrain, ramené en pas."""
    yards, det = CV.separation(role, lecture.get("route", ""), lecture.get("classe", "moyen"), lecture.get("ouverture", 1.5),
                               joueur, defenseurs, famille, couverture, cle[0], cle[1], trace=True)
    _CV_TR[role] = CV.trace_compacte(det)          # le dessin du site (play.geo.cov), aucun tirage de plus
    return CV.en_pas(yards, famille, lecture.get("classe", "moyen"), role)


def _DECISION_PASS_HOOK(offense_team, defense_team, chosen, def_concept, u_off, u_def, random_engine, n_action):
    """Passe décidée : les crochets d'avant, puis la trace des duels de couverture dans le résumé (decision.geo.cov)."""
    _CV_TR.clear()
    play, dec = _CV_DEC_BASE(offense_team, defense_team, chosen, def_concept, u_off, u_def, random_engine, n_action)
    geo = ((dec or {}).get("log") or {}).get("geo")
    if geo and _CV_TR:
        r = [[x[0]] + _CV_TR[x[0]] for x in geo.get("rec") or [] if _CV_TR.get(x[0])]
        if r:
            geo["cov"] = {"dt": round(CV.DT * 4, 2), "r": r}
    _CV_TR.clear()
    return play, dec


def _cv_brancher(actif):
    if moteur:
        moteur.reaction_defensive.DUEL = _cv_duel if actif else None


_cv_brancher(COUVERTURE_SPATIALE_ENABLED)

# ---------- contrôles ----------
if moteur:
    # 1. coupé : le moteur d'avant à l'identique
    _cv_brancher(False)
    _cv_off = [franchise_game(h, a, seed=s) for h, a, s in _CV_REF_MATCHS]
    assert [(_g["home_score"], _g["away_score"], _cv_sig(_g)) for _g in _cv_off] == _CV_REF, "couverture spatiale coupée : moteur changé"
    _cv_brancher(COUVERTURE_SPATIALE_ENABLED)
    # 2. allumé : déterministe, les statuts changent
    if COUVERTURE_SPATIALE_ENABLED:
        _cv_a, _cv_b = (franchise_game(*_CV_REF_MATCHS[0][:2], seed=_CV_REF_MATCHS[0][2]) for _ in range(2))
        assert _cv_sig(_cv_a) == _cv_sig(_cv_b), "couverture spatiale non déterministe"
        _cv_st = [(e.get("decision") or {}).get("status") for e in _cv_a["play_log"] if (e.get("decision") or {}).get("status")]
        assert len(_cv_st) > 15 and len(set(_cv_st)) >= 2, _cv_st
        # 3. play.geo.cov : chaque passe décidée du match de contrôle a la trace de ses duels (rôles de play.geo.rec)
        _cv_geo = [(e.get("decision") or {}).get("geo") for e in _cv_a["play_log"]]
        _cv_geo = [g for g in _cv_geo if g and g.get("k") == "pass"]
        _cv_cov = [g for g in _cv_geo if g.get("cov")]
        assert len(_cv_cov) >= 0.8 * len(_cv_geo) > 10, (len(_cv_cov), len(_cv_geo))
        for _g in _cv_cov:
            _roles = {x[0] for x in _g["rec"]}
            for _r in _g["cov"]["r"]:
                assert _r[0] in _roles and len(_r[4]) == len(_r[5]) >= 2, _r
        _cv_taille = sum(len(_cv_json.dumps(_g["cov"], separators=(",", ":"))) for _g in _cv_cov) / max(1, len(_cv_cov))
    print(f"✅ 12.2 tritricies — couverture {'jouée sur le terrain' if COUVERTURE_SPATIALE_ENABLED else 'coupée'}"
          + (f" (trace des duels : {len(_cv_cov)} passes sur {len(_cv_geo)}, {_cv_taille:.0f} octets par passe)"
             if COUVERTURE_SPATIALE_ENABLED else ""))
else:
    print("⚠️ 12.2 tritricies — moteur/ introuvable : couverture d'avant")
