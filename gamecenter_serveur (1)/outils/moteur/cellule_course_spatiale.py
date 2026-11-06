# ============================================================
# NFL SIM — 12.2 untricies — CAUSAL LÉGER, BLOC 1 : LA COURSE APRÈS LE CONTACT (06/11/2026)
# ============================================================
# Programme « causal léger, bloc par bloc » (décision de Guillaume, 05/11/2026) : le résultat d'une action vient de ce
# qui se passe sur le terrain, sans réécrire le moteur. Bloc 1 : la course après le premier contact.
# Prototype du 05/11 : ≈ 0,08 ms par course simulée (≈ + 1,4 % du temps d'un match).
#
# Avant : yards = table (V0.2) + bloc F (dont « puissance contre tackling ») + actions longues (échappée au-delà du 2e
# rideau, compensée par un rabot). Maintenant, pour une course du bloc F (franchises) :
#   - jusqu'au premier contact rien ne change : la table et le bloc F tirent les yards (T) et le niveau du contact ;
#   - le porteur part du point de contact (profondeur du niveau, jamais plus que T : une course stoppée reste stoppée) ;
#   - moteur/course_spatiale.py joue la suite : les onze défenseurs placés selon leur poste, poursuite, plaquages
#     tentés, manqués ou réussis, touche, en-but ; le plaqueur crédité est celui qui l'arrête ;
#   - ni actions longues ni rabot pour ces courses (l'échappée vient de la simulation) ; le terme de contact du bloc F
#     (K_CONTACT) est coupé (la simulation joue ce duel).
# Hasard : flux « course-spatiale|<graine>|<n° d'action> » (le hasard du moteur n'est pas consommé).
# Journal (additif) : run.spatial = {contact, apres, manques, sortie, td, plaqueur}.
# Interrupteur COURSE_SPATIALE_ENABLED (GC_COURSE_SPATIALE=0 : moteur d'avant, à l'identique, contrôlé ci-dessous).

import importlib as _cs_il
import json as _cs_json
import os as _cs_os

COURSE_SPATIALE_ENABLED = bool(moteur) and _cs_os.environ.get("GC_COURSE_SPATIALE", "1") != "0"
if moteur:
    import moteur.course_spatiale
    CS = _cs_il.reload(moteur.course_spatiale)
    if _cs_os.environ.get("GC_CS_PARAMS"):                       # calibration (outils/moteur/semaine_course_spatiale.py)
        CS.PARAMS.update(_cs_json.loads(_cs_os.environ["GC_CS_PARAMS"]))

_cs_sig = lambda g: [(e.get("kind"), e.get("play_id"), e.get("carrier_id"), e.get("yards_gained"), e.get("outcome"),
                      e.get("credited_defender")) for e in g["play_log"]]
if "_CS_ARCH_BASE" not in globals():
    _CS_ARCH_BASE = _apply_archetype_modifier
    _CS_CLOCK_BASE = advance_game_clock
    _CS_K_CONTACT = RF.K_CONTACT if moteur else None
    _CS_REF_MATCHS = (("MNL", "CTX", 31_001), ("VEC", "PRM", 31_002))
    _CS_REF = [(_g["home_score"], _g["away_score"], _cs_sig(_g)) for _g in
               (franchise_game(h, a, seed=s) for h, a, s in _CS_REF_MATCHS)]
if moteur:
    RF.K_CONTACT = 0.0 if COURSE_SPATIALE_ENABLED else _CS_K_CONTACT
_CS_NIVEAU = {"ligne": "ligne", "linebacker": "linebacker", "second rideau": "second rideau"}


def _cs_y0(e):
    """En travers : le côté et la classe de la course (le bloc F ne place pas la course sur le terrain)."""
    ecart = 11.0 if e.get("classe") in ("outside", "perimeter") else 3.0
    return 26.65 + (-ecart if e.get("cote") == "L" else ecart)


def _apply_archetype_modifier(play, carrier, random_engine):
    """Course du bloc F : la suite du contact se joue sur le terrain (ni actions longues ni rabot) ; sinon, d'avant."""
    global ACTIONS_LONGUES_ENABLED
    c, e = _RF_CTX, _RF_CTX.get("etat")
    spatiale = (COURSE_SPATIALE_ENABLED and carrier is not None and e is not None and play.outcome == PlayOutcome.RUN
                and c.get("n") is not None and len(c.get("log") or []) == c["n"])
    if not spatiale:
        return _CS_ARCH_BASE(play, carrier, random_engine)
    garde, ACTIONS_LONGUES_ENABLED = ACTIONS_LONGUES_ENABLED, False
    try:
        play, info = _CS_ARCH_BASE(play, carrier, random_engine)
    finally:
        ACTIONS_LONGUES_ENABLED = garde
    but = 100 - (_AL_CTX.get("ligne") if _AL_CTX.get("n") == c["n"] else c.get("ligne", 25))
    r = CS.apres_contact(_rf_joueur(carrier), _rf_defense(c["de"]), _CS_NIVEAU.get(e["contact"], "linebacker"),
                         play.yards_gained, _cs_y0(e), e.get("plaqueur"), but, c["g"], c["n"])
    play.yards_gained = r["yards"]
    e["spatial"] = {k: r[k] for k in ("contact", "apres", "manques", "sortie", "td", "plaqueur")}
    if r["plaqueur"]:
        e["plaqueur"] = r["plaqueur"]                  # le plaqueur crédité (12.2 quindecies) est celui qui l'arrête
    return play, info


def advance_game_clock(game_clock, seconds_elapsed):
    """Horloge d'avant ; la course décidée garde au journal ce que la simulation a joué (run.spatial)."""
    r = _CS_CLOCK_BASE(game_clock, seconds_elapsed)
    c = _RF_CTX
    e = c.get("etat")
    if e is not None and e.get("spatial") and c.get("n") is not None and len(c.get("log") or []) > c["n"]:
        run = c["log"][c["n"]].get("run")
        if run is not None and "spatial" not in run:
            run["spatial"] = dict(e["spatial"])
    return r


# ---------- contrôles ----------
if moteur:
    # 1. coupé : le moteur d'avant à l'identique (mêmes matchs, mêmes plaqueurs)
    COURSE_SPATIALE_ENABLED, _cs_save = False, COURSE_SPATIALE_ENABLED
    RF.K_CONTACT = _CS_K_CONTACT
    _cs_off = [franchise_game(h, a, seed=s) for h, a, s in _CS_REF_MATCHS]
    assert [(_g["home_score"], _g["away_score"], _cs_sig(_g)) for _g in _cs_off] == _CS_REF, "course spatiale coupée : moteur changé"
    COURSE_SPATIALE_ENABLED = _cs_save
    RF.K_CONTACT = 0.0 if COURSE_SPATIALE_ENABLED else _CS_K_CONTACT
    # 2. allumé : déterministe, chaque course décidée a sa simulation, yards cohérents
    if COURSE_SPATIALE_ENABLED:
        _cs_a, _cs_b = (franchise_game(*_CS_REF_MATCHS[0][:2], seed=_CS_REF_MATCHS[0][2]) for _ in range(2))
        assert _cs_sig(_cs_a) == _cs_sig(_cs_b), "course spatiale non déterministe"
        _cs_runs = [e for e in _cs_a["play_log"] if (e.get("run") or {}).get("spatial")]
        assert len(_cs_runs) > 15, len(_cs_runs)
        for _e in _cs_runs:
            _s = _e["run"]["spatial"]
            assert _s["contact"] <= max(_e["yards_gained"], _s["contact"]) + 1e-9
            assert not _s["plaqueur"] or _e.get("credited_defender") is not None \
                or _e["yard_line"] + _e["yards_gained"] >= 100 \
                or (_e.get("penalty") or {}).get("nullified"), _e      # touchdown, action annulée : pas de plaqueur
    print(f"✅ 12.2 untricies — course après le contact {'simulée sur le terrain' if COURSE_SPATIALE_ENABLED else 'coupée'}"
          + (f" ({len(_cs_runs)} courses simulées sur un match de contrôle)" if COURSE_SPATIALE_ENABLED else ""))
else:
    print("⚠️ 12.2 untricies — moteur/ introuvable : course d'avant")
