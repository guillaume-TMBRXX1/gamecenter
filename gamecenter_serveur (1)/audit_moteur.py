"""Audit du moteur : contrôle chaque action de chaque match d'une ou plusieurs semaines exportées.

    python3 audit_moteur.py data/weeks                  # toutes les semaines du dossier
    python3 audit_moteur.py data/weeks/week_2026-10-12  # une semaine
    python3 audit_moteur.py data/weeks --json rapport.json

Code de sortie 1 si une anomalie BLOQUANTE est trouvée (score faux, horloge qui recule, match sans fin…) :
le calcul du samedi (GitHub) s'arrête alors AVANT de publier la semaine.
Les ALERTES (statistiques inhabituelles) sont signalées sans bloquer.
"""
import json, os, sys, glob, statistics
from collections import Counter, defaultdict

try:                                    # bloc E (V26) : notes effectives et contrôles de l'état des joueurs
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from moteur import developpement as _dev
except Exception:                       # audit sans le dossier moteur/ : contrôles du bloc E réduits
    _dev = None
try:                                    # idée 6 : bornes du film de scouting (scouting_next_week)
    from moteur import scouting as _sc
except Exception:
    _sc = None
try:                                    # étape 7.2 : règles des pénalités pendant l'action
    from moteur import penalites as _pe
except Exception:
    _pe = None
try:                                    # étape 7.3 : le banc, les packages, les rotations
    from moteur import rotations as _ro
except Exception:
    _ro = None
try:                                    # étape 7.4 : les blessures, l'infirmerie
    from moteur import blessures as _bl
except Exception:
    _bl = None

BLOQUANT, ALERTE = "BLOQUANT", "ALERTE"


class Audit:
    def __init__(self):
        self.items = []            # (niveau, semaine, match, seq, message)
        self.counts = Counter()

    def add(self, lvl, week, gid, seq, msg):
        self.items.append((lvl, week, gid, seq, msg))
        self.counts[lvl] += 1


def other(side):
    return "away" if side == "home" else "home"


def check_game(A, week, g_sched, feed):
    gid = g_sched["id"]
    game, plays = feed["game"], feed["plays"]
    qs = game.get("quarter_seconds", 180)
    bad = lambda seq, m: A.add(BLOQUANT, week, gid, seq, m)
    warn = lambda seq, m: A.add(ALERTE, week, gid, seq, m)
    if not plays:
        bad(None, "match sans aucune action"); return None
    prev = None
    halves = 0
    retours = any(p.get("kick_return") for p in plays)      # bloc 2 : moteur avec coups d'envoi après les scores
    marque = ("field_goal_good", "pat_good", "pat_missed", "two_point_good", "two_point_failed")
    score = {"home": 0, "away": 0}
    for i, p in enumerate(plays):
        s, a = p["seq"], p["after"]
        if s != i + 1:
            bad(s, f"numérotation : action {s} à la position {i + 1}")
        q = p["quarter"]
        ot = game.get("overtime") or {}                 # playoffs : prolongations jusqu'à un vainqueur (11.6)
        qmax = 4 + max(1, int(ot.get("periods") or 1)) if ot.get("rule") == "playoff" else 5
        if q < 1 or q > qmax:
            bad(s, f"quart-temps impossible : {q}")
        if not (0 <= p["clock_end"] <= p["clock_start"] <= qs):
            bad(s, f"horloge incohérente : {p['clock_start']} → {p['clock_end']} (quart de {qs} s)")
        if p["result"] != "kickoff" and p["down"] is not None:
            if p["down"] not in (1, 2, 3, 4):
                bad(s, f"down impossible : {p['down']}")
            if p["to_go"] is None or p["to_go"] <= 0:
                bad(s, f"distance à franchir impossible : {p['to_go']}")
        for k in ("los_x",):
            if p[k] is None or not (0 <= p[k] <= 120):
                bad(s, f"{k} hors du terrain : {p[k]}")
        if p.get("win_prob_home") is not None and not (0 <= p["win_prob_home"] <= 1):
            bad(s, f"probabilité de victoire hors [0,1] : {p['win_prob_home']}")
        # --- score : jamais en baisse, sauts possibles 0/2/3/6/7/8 (1 : point après touchdown, bloc 2) ---
        ns = a["score"]
        dh, da = ns["home"] - score["home"], ns["away"] - score["away"]
        if dh < 0 or da < 0:
            bad(s, f"le score recule : {score} → {ns}")
        for side, d in (("home", dh), ("away", da)):
            if d not in (0, 1, 2, 3, 6, 7, 8):
                bad(s, f"saut de score impossible pour {side} : +{d}")
        if dh and da:
            bad(s, "les deux équipes marquent sur la même action")
        scorer = "home" if dh else "away" if da else None
        r = p["result"]
        prt = bool((p.get("punt_return") or {}).get("td"))      # touchdown sur retour de punt (12.2 sexdecies)
        if prt and (r != "punt" or scorer is None or scorer == p["offense"] or (dh or da) != 6
                    or (not p.get("try_follows") and a["status"] == "live")):
            bad(s, f"touchdown sur retour de punt mal compté ({dh}/{da}) : 6 points pour le receveur, puis sa transformation")
        if r == "touchdown" and not scorer:
            bad(s, "touchdown sans points")
        if r == "field_goal_good" and (scorer != p["offense"] or (dh or da) != 3):
            bad(s, f"field goal réussi mal compté ({dh}/{da})")
        if r == "safety" and (scorer is None or scorer == p["offense"] or (dh or da) != 2):
            bad(s, f"safety mal compté ({dh}/{da}) : 2 points pour la défense")
        if (r == "touchdown" or prt) and p.get("try_follows") and (dh or da) != 6:
            bad(s, f"touchdown suivi d'une transformation : 6 points attendus ({dh}/{da})")
        if r in ("pat_good", "two_point_good") and (scorer != p["offense"] or (dh or da) != (1 if r == "pat_good" else 2)):
            bad(s, f"transformation réussie mal comptée ({r} : {dh}/{da})")
        if r in ("pat_good", "pat_missed", "two_point_good", "two_point_failed"):
            prev_prt = prev is not None and (prev.get("punt_return") or {}).get("td")
            if prev is None or not prev.get("try_follows") or not (
                    (prev["result"] == "touchdown" and prev["offense"] == p["offense"])
                    or (prev_prt and prev["offense"] != p["offense"])):
                bad(s, f"transformation « {r} » sans touchdown de la même équipe juste avant")
            if p["clock_start"] != p["clock_end"]:
                bad(s, "une transformation ne prend pas de temps de jeu")
        elif p.get("conversion") or (prev is not None and prev.get("try_follows")):
            bad(s, "touchdown annoncé avec transformation (try_follows), mais l'action suivante n'en est pas une")
        if (dh or da) == 1 and r != "pat_good":
            bad(s, f"1 point hors d'un point après touchdown (« {r} »)")
        if r in ("incomplete", "punt", "field_goal_missed", "kickoff", "pat_missed", "two_point_failed") and scorer and not prt:
            bad(s, f"des points sur une action « {r} »")
        if r in ("run", "complete") and scorer:
            warn(s, f"points sur « {r} » sans touchdown (+{dh or da})")
        score = dict(ns)
        # --- coups d'envoi (bloc 2) : après chaque score, touchback aux 25 ---
        kr = p.get("kick_return")
        if retours and prev is not None and prev["after"]["status"] == "live" and q <= 4 and (
                prev["result"] in marque or (prev["result"] == "touchdown" and not prev.get("try_follows"))) \
                and p["call"]["type"] != "kickoff":
            bad(s, f"pas de coup d'envoi après le score (« {prev['result']} » → « {r} »)")
        if kr and kr.get("touchback") and a["status"] == "live" and a["los_x"] != (35 if p["offense"] == "home" else 85):
            bad(s, f"touchback : départ attendu aux 25 ({a['los_x']})")
        if kr and kr.get("td") and (r != "touchdown" or not p.get("try_follows") and a["status"] == "live"):
            bad(s, "touchdown sur retour mal annoncé (résultat ou transformation)")
        # --- continuité avec l'action précédente ---
        if prev is not None:
            pa = prev["after"]
            if pa["status"] == "final":
                bad(s, "action après la fin du match")
            same_q = prev["quarter"] == q
            if same_q and p["clock_start"] != prev["clock_end"]:
                bad(s, f"l'horloge saute : fin {prev['clock_end']} s → début {p['clock_start']} s")
            if not same_q:
                if q != prev["quarter"] + 1:
                    bad(s, f"quart-temps sauté : {prev['quarter']} → {q}")
                if prev["clock_end"] != 0:
                    warn(s, f"quart-temps {prev['quarter']} terminé à {prev['clock_end']} s")
                if p["clock_start"] != qs and q <= 4:
                    warn(s, f"quart-temps {q} commence à {p['clock_start']} s")
            if pa["status"] == "live":
                if p["offense"] != pa["offense"]:
                    bad(s, f"le ballon change d'équipe entre deux actions ({pa['offense']} → {p['offense']})")
                if p["los_x"] != pa["los_x"]:
                    bad(s, f"le ballon se déplace entre deux actions ({pa['los_x']} → {p['los_x']})")
                if p["result"] != "kickoff" and pa["down"] is not None and (p["down"], p["to_go"]) != (pa["down"], pa["to_go"]):
                    bad(s, f"down / distance changent entre deux actions ({pa['down']}&{pa['to_go']} → {p['down']}&{p['to_go']})")
        # --- changements de possession ---
        pc = p["possession_change"]
        if a["status"] == "live":
            if pc in ("punt", "turnover", "downs", "missed_fg") and a["offense"] == p["offense"]:
                bad(s, f"« {pc} » mais la même équipe garde le ballon")
            if pc is None and r != "kickoff" and a["offense"] != p["offense"]:
                bad(s, "changement d'équipe sans raison")
            if r in ("interception", "fumble_lost") and pc not in ("turnover", "score"):
                bad(s, f"« {r} » sans changement de possession ({pc})")
            if p["down"] == 4 and pc is None and a["down"] != 1 and r not in ("kickoff", "touchdown", "penalty"):   # bloc 2 : TD puis transformation
                bad(s, f"4e tentative ratée sans perte du ballon ({r}, gain {p['gain']} sur {p['to_go']})")
            # progression des tentatives
            if pc is None and r in ("run", "complete", "incomplete", "sack") and p["down"] and \
                    not (p.get("penalty") or {}).get("accepted"):
                gained = (p["gain"] or 0) >= p["to_go"]
                if gained and a["down"] != 1:
                    bad(s, f"premier essai obtenu (+{p['gain']} sur {p['to_go']}) mais down {a['down']}")
                if not gained and a["down"] != p["down"] + 1:
                    bad(s, f"tentative {p['down']} → {a['down']} sans premier essai (+{p['gain']} sur {p['to_go']})")
        if a["status"] == "half":
            halves += 1
            if q != 2:
                bad(s, f"mi-temps au quart-temps {q}")
        check_penalty(A, week, gid, p, scorer)
        # --- joueurs ---
        pl = p.get("players") or {}
        if r in ("run", "complete", "touchdown") and p["call"]["type"] in ("run", "pass") and not (pl.get("carrier") or {}).get("name"):
            warn(s, f"« {r} » sans porteur du ballon")
        if p["call"]["type"] == "pass" and r in ("complete", "incomplete", "interception") and not pl.get("passer"):
            warn(s, "passe sans passeur")
        # --- ajustements des coordinateurs (V21) et du plan de jeu (bloc D, V25) ---
        for x in p.get("adjust") or []:
            if x.get("team") not in ("home", "away") or not x.get("text"):
                bad(s, f"ajustement mal formé : {x}")
            elif x.get("kind") in ("o_quick", "o_protect", "o_away", "d_bracket", "d_rotate", "d_disguise") and not x.get("reason"):
                warn(s, f"ajustement « {x['kind']} » sans raison")
        # --- cotes en direct ---
        o = p.get("odds") or {}
        if a["status"] == "live" and o.get("ml"):
            for side, v in o["ml"].items():
                if v is None or abs(v) < 100:
                    bad(s, f"cote américaine impossible pour {side} : {v}")
            if o.get("total") is not None and o["total"] < ns["home"] + ns["away"]:
                bad(s, f"total en direct ({o['total']}) sous les points déjà marqués ({ns['home'] + ns['away']})")
        prev = p
    last = plays[-1]
    if last["after"]["status"] != "final":
        bad(last["seq"], "le match ne se termine pas (dernière action non finale)")
    if halves != 1:
        bad(None, f"{halves} mi-temps au lieu d'une")
    fs = game.get("final_score")
    if fs != last["after"]["score"]:
        bad(None, f"score final {fs} ≠ score de la dernière action {last['after']['score']}")
    res = g_sched.get("result") or {}
    if fs and (res.get("home"), res.get("away")) != (fs["home"], fs["away"]):
        bad(None, f"résultat du calendrier {res} ≠ score final {fs}")
    if g_sched["phase"] != "regular" and fs and fs["home"] == fs["away"]:
        bad(None, "match de playoffs terminé à égalité")
    if last["clock_end"] != 0 and not game.get("overtime"):
        warn(last["seq"], f"match fini avec {last['clock_end']} s au chrono sans prolongation")
    gp = game.get("gameplan")
    if gp is not None and not (set(gp) <= {"home", "away"} and all(isinstance(v, dict) for v in gp.values())):
        bad(None, f"plan de jeu mal formé : {gp}")
    po = game.get("pregame_odds") or {}
    if not po.get("ml"):
        bad(None, "pas de cotes d'avant-match")
    ratings = {}
    for side in ("home", "away"):                       # bloc E (V26) : roster[].progression
        for r in (game.get(side) or {}).get("roster") or []:
            ratings[r["id"]] = r.get("ratings") or {}
            pg = r.get("progression")
            if pg is None:
                continue
            if any(not 40 <= v <= 99 for v in (r.get("ratings") or {}).values()):
                bad(None, f"{r['id']} : note hors 40-99 {r['ratings']}")
            if {k: pg["base"][k] + d for k, d in (pg.get("delta") or {}).items()} != (r.get("ratings") or {}):
                bad(None, f"{r['id']} : notes ≠ base + écart ({r.get('ratings')} / {pg.get('base')} / {pg.get('delta')})")
            if abs(pg.get("form", 0)) > 3.0 + 1e-9:
                bad(None, f"{r['id']} : forme {pg.get('form')} hors ± 3")
            if not pg.get("history"):
                warn(None, f"{r['id']} : courbe de progression vide")
    return {"plays": len(plays), "pts": (fs or {}).get("home", 0) + (fs or {}).get("away", 0),
            "home": fs["home"] if fs else 0, "away": fs["away"] if fs else 0,
            "tie": bool(fs and fs["home"] == fs["away"]), "ot": bool(game.get("overtime")),
            "res": Counter(p["result"] for p in plays),
            "flags": sum(1 for p in plays if p.get("penalty")), "penalty_model": game.get("penalty_model"),
            "td_len": [p["gain"] for p in plays if p["result"] == "touchdown" and p["gain"] is not None],
            "ratings": ratings}


def check_penalty(A, week, gid, p, scorer):
    """Étape 7.2 : un drapeau pendant l'action — type, équipe, yards, choix selon la probabilité de victoire, effet."""
    pen = p.get("penalty")
    s = p["seq"]
    bad = lambda m: A.add(BLOQUANT, week, gid, s, m)
    if not pen:
        if p["result"] == "penalty":
            bad("action « penalty » sans play.penalty")
        return
    if _pe is not None and pen.get("type") not in _pe.TYPES:
        bad(f"pénalité hors de la liste (pendant l'action seulement) : {pen.get('type')}"); return
    off = _pe is not None and pen["type"] in _pe.DE_L_ATTAQUE
    if _pe is not None and pen.get("team") != ("offense" if off else "defense"):
        bad(f"pénalité {pen['type']} attribuée à « {pen.get('team')} »")
    if not (pen.get("player") or {}).get("id"):
        bad("pénalité sans joueur")
    if bool(pen.get("accepted")) == bool(pen.get("declined")):
        bad("pénalité ni acceptée ni refusée (ou les deux)")
    w = pen.get("wp") or {}
    if w.get("accept") is not None and w.get("decline") is not None:
        best = (max if pen.get("chooser") == "offense" else min)(w["accept"], w["decline"])
        if w["accept" if pen.get("accepted") else "decline"] != best:
            bad(f"choix contraire à la probabilité de victoire ({pen.get('chooser')} : {w})")
    if not pen.get("accepted"):
        if p["result"] == "penalty":
            bad("pénalité refusée mais action annulée")
        return
    if pen.get("nullified") != (p["result"] == "penalty") or (pen.get("nullified") and not pen.get("play_before")):
        bad(f"pénalité acceptée : action annulée {pen.get('nullified')} / résultat « {p['result']} »")
    if scorer:
        bad("des points sur une action annulée par une pénalité")
    af, a = pen.get("after") or {}, p["after"]
    if a["status"] == "live" and (a["down"], a["to_go"]) != (af.get("down"), af.get("togo")):
        bad(f"après la pénalité : {a['down']}&{a['to_go']} au lieu de {af.get('down')}&{af.get('togo')}")
    if pen.get("auto_first") and af.get("down") != 1 or pen.get("replay_down") and af.get("down") != p["down"]:
        bad(f"pénalité : essai {p['down']} → {af.get('down')} (premier essai {pen.get('auto_first')}, rejoué {pen.get('replay_down')})")
    y = pen.get("yards")
    if _pe is not None and pen["type"] in _pe.YARDS and (y is None or y < 0 or y > _pe.YARDS[pen["type"]]):
        bad(f"pénalité de {y} yards ({pen['type']} : {_pe.YARDS[pen['type']]} au plus)")


# numéros de maillot par poste (affichage, cellule 11.5 du notebook)
JERSEY = {"QB": range(1, 20), "K": range(1, 20), "P": range(1, 20), "RB": range(20, 50),
          "WR": [*range(10, 20), *range(80, 90)], "TE": [*range(80, 90), *range(40, 50)],
          **{p: range(50, 80) for p in ("LT", "LG", "C", "RG", "RT")},
          "EDGE": [*range(90, 100), *range(50, 60)], "DT": range(90, 100), "LB": range(40, 60), "CB": range(20, 40),
          "S": range(20, 50)}


def check_rotations(A, week, g_sched, feed):
    """Étape 7.3 : rosters de 36 (titulaires puis remplaçants), numéros, alignement de chaque action reconstitué depuis
    play.subs (11 par côté, postes de l'unité, personne deux fois, joueurs du roster), porteur et défenseur crédité sur
    le terrain, snaps cohérents. Renvoie les noms des remplaçants (contrôle de la ligue dans check_week)."""
    game = feed["game"]
    if not game.get("rotation_model") or _ro is None:
        return None
    gid = g_sched["id"]
    bad = lambda seq, m: A.add(BLOQUANT, week, gid, seq, m)
    warn = lambda seq, m: A.add(ALERTE, week, gid, seq, m)
    R, cur, snaps, n = {}, {}, Counter(), Counter()
    noms = []
    sortis, blesses = {}, 0                 # 7.4.1 : {côté: {id: action de la blessure}} (pas les blessures légères)
    for side in ("home", "away"):
        ro = (game.get(side) or {}).get("roster") or []
        R[side] = {r["id"]: r for r in ro}
        libres = sum(1 for r in ro[25 + _ro.TAILLE_BANC:] if r.get("profile") == "free_agent")    # 7.4.2
        if len(ro) != 25 + _ro.TAILLE_BANC + libres or \
                [r.get("depth") for r in ro] != [1] * 25 + [2] * (_ro.TAILLE_BANC + libres):
            bad(None, f"{side} : roster de {len(ro)} joueurs (25 titulaires, {_ro.TAILLE_BANC} remplaçants et les "
                      f"joueurs libres attendus)")
        if len(R[side]) != len(ro):
            bad(None, f"{side} : un joueur deux fois dans le roster")
        nums = [r.get("number") for r in ro]
        if len(set(nums)) != len(nums):
            bad(None, f"{side} : numéros de maillot en double")
        for r in ro:
            if r.get("number") not in JERSEY.get(r["pos"], range(1, 100)):
                bad(None, f"{r['id']} : n° {r.get('number')} hors de la plage du poste {r['pos']}")
        noms += [(r["name"], r["id"], (r.get("progression") or {}).get("rookie")) for r in ro if r.get("depth") == 2]
        prof = {}
        for r in ro:
            prof.setdefault(r["pos"], []).append(r["id"])
        for cote in ("off", "def"):
            base = {}
            for pl in _ro.PLACES[cote]:
                poste, rang = _ro.POSTE_PLACE[pl]
                ids = prof.get(poste) or []
                base[pl] = ids[rang - 1] if len(ids) >= rang else None
            cur[(side, cote)] = base
    for p in feed["plays"]:
        if p["call"].get("type") not in ("run", "pass"):
            continue
        s = p["seq"]
        att = p["offense"]
        de = "away" if att == "home" else "home"
        for x in p.get("subs") or []:
            side = att if x.get("side") == "off" else de
            if x.get("pos") not in _ro.PLACES.get(x.get("side"), ()):
                bad(s, f"changement à une place inconnue : {x}"); continue
            if x.get("in") not in R[side] or (x.get("out") is not None and x["out"] not in R[side]):
                bad(s, f"changement avec un joueur hors du roster : {x}"); continue
            if x.get("reason") not in ("package", "fatigue", "garbage", "injury", "return", "absence"):
                bad(s, f"changement sans raison connue : {x}")
            cur[(side, x["side"])][x["pos"]] = x["in"]
        on = {}
        for side, cote in ((att, "off"), (de, "def")):
            v = list(cur[(side, cote)].values())
            if len(v) != 11 or None in v or len(set(v)) != 11:
                bad(s, f"{side} {cote} : {len(set(v) - {None})} joueurs alignés ({cur[(side, cote)]})")
            for i in v:
                if i and _ro.COTE_POSTE.get(R[side][i]["pos"]) != cote:
                    bad(s, f"{i} ({R[side][i]['pos']}) aligné en {'attaque' if cote == 'off' else 'défense'}")
                snaps[i] += 1
            n[(side, cote)] += 1
            on[cote] = set(v)
        for side, cote in ((att, "off"), (de, "def")):          # 7.4 : un absent ne joue pas, un blessé ne revient pas
            for i in on[cote]:
                if (R[side].get(i) or {}).get("status") == "out":
                    bad(s, f"{i} aligné alors qu'il est absent (infirmerie)")
                if i in sortis.get(side, {}) and sortis[side][i] < s:
                    bad(s, f"{i} aligné après sa blessure (action {sortis[side][i]})")
        b = p.get("injury")
        if b:
            side = b.get("team")
            if b.get("id") not in R.get(side, {}):
                bad(s, f"blessé hors du roster : {b}")
            elif b["id"] not in on["off" if side == att else "def"]:
                bad(s, f"blessé {b['id']} pas sur le terrain")
            if b.get("severity") != "minor":
                sortis.setdefault(side, {})[b["id"]] = s
            blesses += 1
        pp = p.get("players") or {}
        car = (pp.get("carrier") or {}).get("id")
        if car and car not in on["off"]:
            bad(s, f"porteur {car} pas sur le terrain")
        q = (pp.get("passer") or {}).get("id")
        if q and q not in on["off"]:
            bad(s, f"passeur {q} pas sur le terrain")
        d = (pp.get("defender") or {}).get("name")
        if d and d not in {R[de][i]["name"] for i in on["def"]}:
            warn(s, f"défenseur crédité {d} pas sur le terrain")
    if game.get("injury_model") and blesses != len(game.get("injuries") or []):
        bad(None, f"{blesses} actions avec une blessure, {len(game.get('injuries') or [])} blessures au match")
    for side in ("home", "away"):
        us = (game.get(side) or {}).get("unit_snaps") or {}
        for cote in ("off", "def"):
            if us.get(cote) is not None and us[cote] != n[(side, cote)]:
                bad(None, f"{side} : {us[cote]} snaps en {cote} annoncés, {n[(side, cote)]} actions de scrimmage")
        for i, r in R[side].items():
            if r.get("snaps") is not None and r["snaps"] != snaps[i]:
                bad(None, f"{i} : {r['snaps']} snaps annoncés, {snaps[i]} d'après les changements")
    return noms


def check_week(A, folder):
    name = os.path.basename(os.path.normpath(folder))
    w = json.load(open(os.path.join(folder, "week.json"), encoding="utf-8"))
    sched = w["schedule"]
    stats = []
    banc_noms, tous_noms = set(), set()                 # étape 7.3 : noms des remplaçants uniques dans la ligue
    blesses = {}                                        # 7.4 : blessés de « semaines » de la semaine {id: (ko, match)}
    for g in sorted(sched, key=lambda x: (x["kickoff"], x["id"])):
        try:
            feed = json.load(open(os.path.join(folder, g["feed"]), encoding="utf-8"))
        except Exception as e:
            A.add(BLOQUANT, name, g["id"], None, f"fichier du match illisible : {e}"); continue
        check_semaine_blesses(A, name, g, feed, blesses)
        check_scout(A, name, g, feed)
        nb = check_rotations(A, name, g, feed)
        if nb:
            banc_noms.update((nom, pid) for nom, pid, rookie in nb if not rookie)
            tous_noms.update((r["name"], r["id"]) for s in ("home", "away") for r in feed["game"][s].get("roster") or [])
        st = check_game(A, name, g, feed)
        if st:
            st["phase"] = g["phase"]; st["id"] = g["id"]; stats.append(st)
    # --- semaine ---
    vues = {}                                           # bloc E : notes figées pendant toute la semaine
    for st in stats:
        for pid, r in st.pop("ratings", {}).items():
            if vues.setdefault(pid, r) != r:
                A.add(BLOQUANT, name, st["id"], None, f"{pid} : notes qui changent pendant la semaine ({vues[pid]} / {r})")
    check_progression(A, name, w)
    check_film(A, name, folder, w)
    check_infirmerie(A, name, w)
    porteurs = Counter(nom for nom, _ in tous_noms)
    doublons = sorted(nom for nom, _ in banc_noms if porteurs[nom] > 1)
    if doublons:
        A.add(ALERTE, name, None, None, f"remplaçants dont le nom est porté par un autre joueur : {doublons[:5]}")
    reg = [g for g in sched if g["phase"] == "regular"]
    teams = list(w["teams"]) if isinstance(w["teams"], dict) else [t["abbr"] for t in w["teams"]]
    per = Counter()
    pairs = Counter()
    for g in reg:
        per[g["home"]] += 1; per[g["away"]] += 1
        pairs[tuple(sorted((g["home"], g["away"])))] += 1
    # 4 équipes : 36 matchs, 18 par équipe, chaque affiche 6 fois ; étape 6, 8 équipes : 56, 14, 2 (aller-retour)
    nslots = max((g["slot"] for g in reg), default=0)
    if len(reg) != len(teams) // 2 * nslots or any(per[t] != nslots for t in teams):
        A.add(BLOQUANT, name, None, None, f"calendrier : {len(reg)} matchs, par équipe {dict(per)}")
    if len(pairs) != len(teams) * (len(teams) - 1) // 2 or len(set(pairs.values())) != 1:
        A.add(BLOQUANT, name, None, None, f"affiches : {dict(pairs)}")
    # classement recalculé à partir des résultats
    wins = Counter(); ties = Counter()
    for g in reg:
        r = g["result"]
        if r["home"] > r["away"]: wins[g["home"]] += 1
        elif r["away"] > r["home"]: wins[g["away"]] += 1
        else: ties[g["home"]] += 1; ties[g["away"]] += 1
    for row in w.get("standings") or []:
        t = row.get("team")
        if t and ("wins" in row or "w" in row):
            ww = row.get("wins", row.get("w"))
            if ww != wins[t]:
                A.add(BLOQUANT, name, None, None, f"classement : {t} a {ww} victoires, les résultats en donnent {wins[t]}")
    final = next((g for g in sched if g["phase"] == "ai_bowl"), None)
    if final and final.get("result"):
        r = final["result"]; champ = final["home"] if r["home"] > r["away"] else final["away"]
        if w.get("champion") != champ:
            A.add(BLOQUANT, name, None, None, f"champion {w.get('champion')} ≠ vainqueur de la Grand Final {champ}")
    semis = [g for g in sched if g["phase"] == "semifinal"]
    if final and semis and all(g.get("result") for g in semis):
        winners = {g["home"] if g["result"]["home"] > g["result"]["away"] else g["away"] for g in semis}
        if {final["home"], final["away"]} != winners:
            A.add(BLOQUANT, name, None, None, f"Grand Final {final['home']}–{final['away']} ≠ vainqueurs des demi-finales {winners}")
    # étape 6, 24 équipes : les demi-finales sont les finales de conférence entre champions de division
    league = (w.get("week") or {}).get("league")
    order = [r["team"] for r in w.get("standings") or []]
    if league and semis and order:
        pos = {a: i for i, a in enumerate(order)}
        for conf, divs in league.items():
            champs = {min(ts, key=lambda a: pos.get(a, 99)) for ts in divs.values()}
            if not any({g["home"], g["away"]} == champs for g in semis):
                A.add(BLOQUANT, name, None, None, f"finale de conférence {conf} : {sorted(champs)} attendus")
    return stats


def check_infirmerie(A, name, w):
    """Étape 7.4.2 : le rapport « injuries » de week.json — chaque absent est « out » au roster de son équipe (et
    personne d'autre), chaque joueur libre est au banc."""
    rep = w.get("injuries")
    if not rep:
        return
    rosters = {a: {r["id"]: r for r in t.get("roster") or []} for a, t in (w.get("teams") or {}).items()}
    out = {o["id"] for o in rep.get("out") or []}
    for o in rep.get("out") or []:
        r = rosters.get(o["team"], {}).get(o["id"])
        if not r or r.get("status") != "out":
            A.add(BLOQUANT, name, None, None, f"absent {o['id']} pas « out » au roster de {o['team']}")
    for a, rs in rosters.items():
        for i, r in rs.items():
            if r.get("status") == "out" and i not in out:
                A.add(BLOQUANT, name, None, None, f"{i} « out » au roster sans être au rapport des absents")
    for x in rep.get("signings") or []:
        r = rosters.get(x["team"], {}).get(x["id"])
        if not r or r.get("profile") != "free_agent":
            A.add(BLOQUANT, name, None, None, f"joueur libre {x['id']} pas au banc de {x['team']}")
    joues = {}
    for x in rep.get("in_week") or []:
        joues.setdefault(x.get("game"), []).append(x)
    for gid, xs in joues.items():                      # 7.4 : chaque blessé de la semaine a sa blessure au match
        g = next((g for g in w.get("schedule") or [] if g["id"] == gid), None)
        if g is None:
            A.add(BLOQUANT, name, gid, None, f"blessé de la semaine dans un match inconnu : {xs[0]['id']}")
    n = len(rosters) or 1
    if len(out) / n > 4:
        A.add(ALERTE, name, None, None, f"infirmerie : {len(out) / n:.1f} absents par équipe (≈ 2 attendus)")


def check_semaine_blesses(A, name, g, feed, blesses):
    """Étape 7.4 (23/10) : un blessé de « semaines » ne rejoue pas les matchs suivants de la semaine — il est « out » au
    roster des matchs qui commencent après le sien (l'alignement : check_rotations)."""
    game = feed.get("game") or {}
    if not game.get("injury_model"):
        return
    for side in ("home", "away"):
        for r in (game.get(side) or {}).get("roster") or []:
            b = blesses.get(r["id"])
            if b and b[0] < g["kickoff"] and r.get("status") != "out":
                A.add(BLOQUANT, name, g["id"], None, f"{r['id']} blessé en {b[1]} (semaines) mais pas « out » ensuite")
    for p in feed.get("plays") or []:
        b = p.get("injury")
        if b and b.get("severity") == "weeks":
            blesses.setdefault(b["id"], (g["kickoff"], g["id"]))


def check_infirmerie_suite(A, name, w, prev):
    """Étape 7.4.2 : les absents d'une semaine sont ceux de l'infirmerie publiée par la précédente (players_next_week)."""
    inf = (prev.get("players_next_week") or {}).get("infirmerie")
    if _bl is None or inf is None or not w.get("injuries"):
        return
    attendus = set(_bl.absents(inf))
    out = {o["id"] for o in w["injuries"].get("out") or []}
    if attendus != out:
        A.add(BLOQUANT, name, None, None, f"absents ≠ infirmerie de la semaine précédente : {sorted(attendus ^ out)[:5]}")


def check_scout(A, name, g, feed):
    """Idée 6 : ce que la défense sait du film (play.scout.def.film) est cohérent avec le rapport d'avant-match."""
    game = feed.get("game") or {}
    mem = game.get("scout_memory")
    for p in feed.get("plays") or []:
        sc = p.get("scout") or {}
        if sc.get("version") == "scouting-2" and not mem:
            A.add(BLOQUANT, name, g["id"], p.get("seq"), "play.scout : version scouting-2 sans game.scout_memory")
        f = (sc.get("def") or {}).get("film")
        if f is None:
            continue
        if not mem or not isinstance(f.get("games"), int) or f["games"] < 1 or not (0 <= f.get("own", 0) <= f["games"]) \
                or not (0.0 <= f.get("part", -1) <= 1.0):
            A.add(BLOQUANT, name, g["id"], p.get("seq"), f"play.scout.def.film hors bornes : {f}")
        rep = (game.get("scout_film") or {}).get(sc["def"].get("team")) or {}
        if rep and rep.get("games") != f.get("games"):
            A.add(BLOQUANT, name, g["id"], p.get("seq"), f"play.scout.def.film : {f.get('games')} matchs, rapport {rep.get('games')}")


def check_film(A, name, folder, w):
    """Idée 6 : le film de la semaine suivante (scouting_next_week.json) dans ses bornes."""
    ref = w.get("scouting_next_week")
    if not ref:
        return
    try:
        film = json.load(open(os.path.join(folder, ref["file"]), encoding="utf-8")) if ref.get("file") else ref
    except Exception as e:
        A.add(BLOQUANT, name, None, None, f"scouting_next_week illisible : {e}"); return
    teams = list(w["teams"]) if isinstance(w["teams"], dict) else [t["abbr"] for t in w["teams"]]
    if _sc is not None:
        for pb in _sc.controler_film(film, teams):
            A.add(BLOQUANT, name, None, None, f"scouting_next_week : {pb}")
    if film.get("semaines", 0) < 1 or ref.get("weeks") != film.get("semaines"):
        A.add(BLOQUANT, name, None, None, f"scouting_next_week : {film.get('semaines')} semaines (renvoi : {ref.get('weeks')})")


def check_progression(A, name, w):
    """Bloc E (V26) : état des joueurs pour la semaine suivante (players_next_week) et rapport (progression)."""
    etat, rap = w.get("players_next_week"), w.get("progression")
    if etat is None:
        return
    J = etat.get("joueurs") or {}
    roster = {r["id"] for t in (w["teams"].values() if isinstance(w["teams"], dict) else w["teams"]) for r in t.get("roster") or []
              if r.get("profile") != "free_agent"}          # 7.4.2 : un joueur libre est signé pour la semaine
    if roster and set(J) != roster:
        A.add(BLOQUANT, name, None, None, f"players_next_week : {len(J)} joueurs pour {len(roster)} au roster")
    if _dev is not None:
        for pb in _dev.controler(etat):
            A.add(BLOQUANT, name, None, None, f"players_next_week : {pb}")
    if etat.get("semaines", 0) < 1:
        A.add(BLOQUANT, name, None, None, "players_next_week : aucune semaine de progression comptée")
    # bornes du garde-fou EN VIGUEUR quand la semaine a été produite (guard_bounds), pas celles d'aujourd'hui :
    # une semaine déjà publiée n'est pas refusée parce que les bornes ont été resserrées depuis (09/10)
    bornes = (rap or {}).get("guard_bounds") or (_dev.BORNES_AVANT_0910 if _dev is not None else {"unit": 3.0})
    e_max, f_max = bornes.get("unit", 3.0), bornes.get("force")
    for t, us in ((rap or {}).get("team_units") or {}).items():
        for u, d in us.items():
            if abs(d) > e_max + 1e-6:
                A.add(BLOQUANT, name, None, None, f"progression : {t} {u} à {d:+.2f} de sa base (± {e_max} au plus)")
    for t, f in ((rap or {}).get("team_strength") or {}).items():
        if f_max is not None and abs(f) > f_max + 0.005:
            A.add(BLOQUANT, name, None, None, f"progression : force de {t} à {f:+.2f} de sa base (± {f_max} au plus)")
    if rap and rap.get("league_drift_max", 0) > 0.5:
        A.add(ALERTE, name, None, None, f"progression : dérive de la ligue {rap['league_drift']}")


def stat_alerts(A, stats, label):
    """Alertes statistiques sur l'ensemble des matchs (repères mesurés sur 1 008 matchs, fiche technique)."""
    if not stats:
        return {}
    pts = [s["pts"] for s in stats]; npl = [s["plays"] for s in stats]
    hw = sum(1 for s in stats if s["home"] > s["away"]) / len(stats)
    ties = sum(s["tie"] for s in stats)
    tot = Counter(); [tot.update(s["res"]) for s in stats]
    tdl = [x for s in stats for x in s["td_len"]]
    summ = {"matchs": len(stats), "points_moyens": round(statistics.mean(pts), 1), "points_min": min(pts), "points_max": max(pts),
            "actions_moyennes": round(statistics.mean(npl), 1), "actions_min": min(npl), "actions_max": max(npl),
            "victoires_domicile": round(hw, 3), "nuls": ties, "prolongations": sum(s["ot"] for s in stats),
            "par_match": {k: round(v / len(stats), 2) for k, v in tot.most_common()},
            "td_longueur_moyenne": round(statistics.mean(tdl), 1) if tdl else None}
    pen = [s["flags"] for s in stats if s.get("penalty_model")]
    if pen:
        summ["drapeaux_par_match"] = round(statistics.mean(pen), 2)
        if not 4.0 <= summ["drapeaux_par_match"] <= 12.0:
            A.add(ALERTE, label, None, None, f"pénalités : {summ['drapeaux_par_match']} drapeaux par match (≈ 8 attendus)")
    for s in stats:
        if s["pts"] > 120: A.add(ALERTE, label, s["id"], None, f"score très élevé : {s['home']}-{s['away']}")
        if s["pts"] < 6: A.add(ALERTE, label, s["id"], None, f"score très bas : {s['home']}-{s['away']}")
        if not 90 <= s["plays"] <= 220: A.add(ALERTE, label, s["id"], None, f"nombre d'actions inhabituel : {s['plays']}")
    return summ


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_json = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    if out_json in args: args.remove(out_json)
    root = args[0] if args else "data/weeks"
    folders = [root] if os.path.exists(os.path.join(root, "week.json")) else sorted(
        d for d in glob.glob(os.path.join(root, "week_*")) if os.path.exists(os.path.join(d, "week.json")))
    A = Audit(); allstats = []; per_week = {}
    # deux semaines ne doivent jamais rejouer les mêmes matchs (même numéro de semaine = mêmes graines)
    sig = {}
    for f in folders:
        w = json.load(open(os.path.join(f, "week.json"), encoding="utf-8"))
        key = json.dumps([(g["home"], g["away"], g.get("result")) for g in w["schedule"] if g["phase"] == "regular"])
        idx = w["week"].get("index")
        for other_name, (okey, oidx) in sig.items():
            if okey == key:
                A.add(BLOQUANT, os.path.basename(f), None, None, f"semaine identique à {other_name} (mêmes résultats : mêmes graines)")
            elif idx is not None and idx == oidx:
                A.add(BLOQUANT, os.path.basename(f), None, None, f"même numéro de semaine ({idx}) que {other_name} : graines identiques")
        sig[os.path.basename(f)] = (key, idx)
    for k, f in enumerate(folders):
        if k:                                           # 7.4.2 : les absents viennent de l'infirmerie de la précédente
            try:
                check_infirmerie_suite(A, os.path.basename(f),
                                       json.load(open(os.path.join(f, "week.json"), encoding="utf-8")),
                                       json.load(open(os.path.join(folders[k - 1], "week.json"), encoding="utf-8")))
            except (OSError, ValueError):
                pass
        st = check_week(A, f)
        per_week[os.path.basename(f)] = stat_alerts(A, st, os.path.basename(f))
        allstats += st
    total = stat_alerts(Audit(), allstats, "total")
    print(f"Audit du moteur — {len(folders)} semaine(s), {total.get('matchs', 0)} matchs, "
          f"{sum(s['plays'] for s in allstats)} actions")
    print(f"  {A.counts[BLOQUANT]} anomalie(s) bloquante(s), {A.counts[ALERTE]} alerte(s)")
    for lvl in (BLOQUANT, ALERTE):
        byk = defaultdict(list)
        for it in A.items:
            if it[0] == lvl:
                byk[it[4].split(" :")[0].split(" (")[0]].append(it)
        for k, its in sorted(byk.items(), key=lambda kv: -len(kv[1])):
            ex = its[0]
            print(f"  [{lvl}] {k} — {len(its)} fois · ex. {ex[1]} {ex[2]} action {ex[3]} : {ex[4]}")
    print("  Repères :", json.dumps(total, ensure_ascii=False))
    if out_json:
        json.dump({"bloquant": A.counts[BLOQUANT], "alertes": A.counts[ALERTE], "total": total, "semaines": per_week,
                   "anomalies": [dict(zip(("niveau", "semaine", "match", "action", "message"), it)) for it in A.items]},
                  open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sys.exit(1 if A.counts[BLOQUANT] else 0)


if __name__ == "__main__":
    main()
