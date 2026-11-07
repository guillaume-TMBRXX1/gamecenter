# ============================================================
# NFL SIM — 12.2 duotricies — CAUSAL LÉGER, BLOC 2 : LA COURSE APRÈS LA RÉCEPTION (06/11/2026)
# ============================================================
# Programme « causal léger, bloc par bloc » (décision de Guillaume, 05/11/2026). Bloc 1 (12.2 untricies) : la course
# après le contact. Bloc 2 : la course après la réception d'une passe complétée.
#
# Avant : yards = table V0.2 + blocs A-C (profondeur de la cible, séparation, receveur contre défenseur) + actions
# longues (passe profonde qui file, YAC, compensées par un rabot). Maintenant, pour une passe décidée et complétée :
#   - jusqu'à la réception rien ne change : la table, les blocs A-C et le profil du QB tirent les yards (T) ;
#   - le receveur attrape au bout de sa route (profondeur de la route, jamais plus loin que T), en courant ; le défenseur
#     qui le couvrait est à la séparation du bloc A (play.geo) ; les autres ont lu le lancer, la ligne a chargé le QB ;
#   - moteur/course_spatiale.py (apres_reception) joue la suite comme au bloc 1 : poursuite, plaquages, touche, en-but ;
#     le plaqueur crédité est celui qui l'arrête ;
#   - ni actions longues ni rabot pour ces passes (la longue course après la réception vient de la simulation).
# Hasard : flux « reception-spatiale|<graine>|<n° d'action> » (le hasard du moteur n'est pas consommé).
# Journal (additif) : decision.yac = {air, apres, manques, sortie, td, plaqueur}. GameFeed (additif, 07/11/2026) :
# play.geo.sim = la trace de la simulation pour le dessin du site (moteur.course_spatiale.trace_compacte : receveur et
# défenseurs proches tous les 0,2 s depuis la réception, x depuis la ligne de mêlée, y en travers ; plaquages manqués et
# réussi : [instant, défenseur, 0 / 1]).
# Interrupteur RECEPTION_SPATIALE_ENABLED (GC_RECEPTION_SPATIALE=0 : moteur d'avant, à l'identique, contrôlé ci-dessous).

import importlib as _rs_il
import json as _rs_json
import os as _rs_os

RECEPTION_SPATIALE_ENABLED = bool(moteur) and _rs_os.environ.get("GC_RECEPTION_SPATIALE", "1") != "0"
if moteur:
    import moteur.course_spatiale
    CS = _rs_il.reload(moteur.course_spatiale)
    if _rs_os.environ.get("GC_CS_PARAMS"):                       # le bloc 1 garde ses réglages (rechargement)
        CS.PARAMS.update(_rs_json.loads(_rs_os.environ["GC_CS_PARAMS"]))
    if _rs_os.environ.get("GC_RS_PARAMS"):                       # calibration (outils/moteur/semaine_course_spatiale.py)
        CS.PARAMS_RECEPTION.update(_rs_json.loads(_rs_os.environ["GC_RS_PARAMS"]))

_rs_sig = lambda g: [(e.get("kind"), e.get("play_id"), e.get("carrier_id"), e.get("yards_gained"), e.get("outcome"),
                      e.get("credited_defender")) for e in g["play_log"]]
if "_RS_ARCH_BASE" not in globals():
    _RS_ARCH_BASE = _apply_archetype_modifier
    _RS_CREDIT_BASE = _credit_defender
    _RS_CLOCK_BASE = advance_game_clock
    _RS_QB_BASE = _apply_qb_pass_modifier
    _RS_REF_MATCHS = (("MNL", "CTX", 32_001), ("VEC", "PRM", 32_002))
    _RS_REF = [(_g["home_score"], _g["away_score"], _rs_sig(_g)) for _g in
               (franchise_game(h, a, seed=s) for h, a, s in _RS_REF_MATCHS)]
_RS_CTX = {}


def _rs_defense(team, couvreur_id):
    """Les onze du bloc F ; le défenseur qui couvrait y entre s'il n'y était pas (nickel, 3e safety : à la place d'un LB)."""
    d = _rf_defense(team)
    if couvreur_id and all(x["id"] != couvreur_id for x in d):
        q = next((p for p in team.roster if p.player_id == couvreur_id), None)
        if q is not None:
            k = max((i for i, x in enumerate(d) if x["pos"] == "LB"), default=len(d) - 1)
            d[k] = _rf_joueur(q)
    return d


def _rs_route(dec):
    """(profondeur, sens, longueur de la cassure) de la route lancée ; screen ou route inconnue : derrière la ligne."""
    r = ROUTE_LIBRARY.get(dec.get("route_name") or "")
    if not r:
        return -1.0, "HORIZONTAL", 3.0
    return float(r["depth"]), r["direction"], float(r.get("break_run") or 0.0) * 0.6


def _apply_archetype_modifier(play, carrier, random_engine):
    """Passe décidée et complétée : ni actions longues ni rabot (la suite de la réception se jouera sur le terrain)."""
    global ACTIONS_LONGUES_ENABLED
    c = _AL_CTX
    dec = c.get("dec") or {}
    geo = (dec.get("log") or {}).get("geo") or {}
    _RS_CTX.clear()
    actif = (RECEPTION_SPATIALE_ENABLED and carrier is not None and play.outcome == PlayOutcome.PASS_COMPLETE
             and dec.get("action") == "LANCER" and geo.get("tgt") and _al_actif())
    if not actif:
        return _RS_ARCH_BASE(play, carrier, random_engine)
    garde, ACTIONS_LONGUES_ENABLED = ACTIONS_LONGUES_ENABLED, False
    try:
        play, info = _RS_ARCH_BASE(play, carrier, random_engine)
    finally:
        ACTIONS_LONGUES_ENABLED = garde
    _RS_CTX.update(n=c["n"], log=c["log"], de=c["de"], carrier=carrier, geo=geo, dec=dec, ligne=c["ligne"], g=c["g"])
    return play, info


def _apply_qb_pass_modifier(play, qb, random_engine):
    """Profil du QB d'avant (ses yards comptent avant la réception), puis la suite de la réception sur le terrain."""
    play, info = _RS_QB_BASE(play, qb, random_engine)
    c = _RS_CTX
    if c.get("geo") and "res" not in c and len(c["log"]) == c["n"] and play.outcome == PlayOutcome.PASS_COMPLETE:
        geo = c["geo"]
        rec = next((x for x in geo.get("rec") or [] if x[0] == geo["tgt"]), None)
        sep, couvreur = (rec[1], rec[3]) if rec else (1.5, None)
        air, sens, cassure = _rs_route(c["dec"])
        r = CS.apres_reception(_rf_joueur(c["carrier"]), _rs_defense(c["de"], couvreur), air, play.yards_gained,
                               geo["tgt"], sens, cassure, couvreur, sep, 100 - c["ligne"], c["g"], c["n"], trace=True)
        play.yards_gained = r["yards"]
        tr = CS.trace_compacte(r)                      # le dessin du site (play.geo.sim) : receveur, défenseurs, plaquages
        if tr:
            geo["sim"] = tr
        c["res"] = {k: r[k] for k in ("air", "apres", "manques", "sortie", "td", "plaqueur")}
    return play, info


def _credit_defender(defense_team, category, random_engine):
    """Plaquage d'une réception simulée : celui qui l'a arrêté (le tirage du moteur est consommé comme avant)."""
    p = _RS_CREDIT_BASE(defense_team, category, random_engine)
    c = _RS_CTX
    w = (c.get("res") or {}).get("plaqueur")
    if category == "TACKLE" and w and c.get("de") is defense_team and len(c["log"]) == c["n"] + 1:
        q = next((x for x in defense_team.roster if x.player_id == w), None)
        if q is not None:
            return q
    return p


def advance_game_clock(game_clock, seconds_elapsed):
    """Horloge d'avant ; la réception simulée garde au journal ce qu'elle a joué (decision.yac)."""
    r = _RS_CLOCK_BASE(game_clock, seconds_elapsed)
    c = _RS_CTX
    if c.get("res") and len(c["log"]) > c["n"]:
        d = c["log"][c["n"]].get("decision")
        if d is not None and "yac" not in d:
            d["yac"] = dict(c["res"])
        c.clear()
    return r


# ---------- contrôles ----------
if moteur:
    # 1. coupé : le moteur d'avant à l'identique (mêmes matchs, mêmes plaqueurs)
    RECEPTION_SPATIALE_ENABLED, _rs_save = False, RECEPTION_SPATIALE_ENABLED
    _rs_off = [franchise_game(h, a, seed=s) for h, a, s in _RS_REF_MATCHS]
    assert [(_g["home_score"], _g["away_score"], _rs_sig(_g)) for _g in _rs_off] == _RS_REF, "réception spatiale coupée : moteur changé"
    RECEPTION_SPATIALE_ENABLED = _rs_save
    # 2. allumé : déterministe, chaque réception décidée a sa simulation, plaqueur cohérent
    if RECEPTION_SPATIALE_ENABLED:
        _rs_a, _rs_b = (franchise_game(*_RS_REF_MATCHS[0][:2], seed=_RS_REF_MATCHS[0][2]) for _ in range(2))
        assert _rs_sig(_rs_a) == _rs_sig(_rs_b), "réception spatiale non déterministe"
        _rs_rec = [e for e in _rs_a["play_log"] if (e.get("decision") or {}).get("yac")]
        assert len(_rs_rec) > 15, len(_rs_rec)
        for _e in _rs_rec:
            _y = _e["decision"]["yac"]
            assert _e.get("outcome") == "PASS_COMPLETE", _e.get("outcome")
            assert not _y["plaqueur"] or _e.get("credited_defender") is not None \
                or _e["yard_line"] + _e["yards_gained"] >= 100 \
                or (_e.get("penalty") or {}).get("nullified"), _e      # touchdown, action annulée : pas de plaqueur
    print(f"✅ 12.2 duotricies — course après la réception {'simulée sur le terrain' if RECEPTION_SPATIALE_ENABLED else 'coupée'}"
          + (f" ({len(_rs_rec)} réceptions simulées sur un match de contrôle)" if RECEPTION_SPATIALE_ENABLED else ""))
else:
    print("⚠️ 12.2 duotricies — moteur/ introuvable : réception d'avant")
