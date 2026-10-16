"""Temps d'écran de la retransmission : le match se joue en TEMPS RÉEL (15/10/2026).

Historique : jusqu'au 14/10, chaque action durait 6,5 s à l'écran ; le 14/10 (ecran-1), l'horloge s'écoulait en
continu mais accélérée (≈ 26 s d'horloge par seconde d'écran avant le snap) pour tenir 15 min avec des quarts-temps de
15 min : « les actions vont trop vite ». Retour de Guillaume (15/10) : quarts-temps de 4 min joués en temps réel, chrono
d'avant-snap de 10 s au plus, 3 temps morts de 15 s par équipe et par mi-temps, moins de 30 min par match.

Désormais (ecran-2), une seconde d'écran = une seconde de match, pour chaque action (calculé à l'export du GameFeed,
lu par le serveur et par le site) :
  avant le snap : horloge qui tourne (course dans le terrain, passe complétée…) : le temps que le moteur a fait courir
                  entre les deux actions (horloge réelle, moteur/horloge.py : 9 s en rythme normal, 4 s en hurry-up,
                  10 s pour tuer l'horloge) — l'horloge du match et le chrono des 10 s descendent ensemble ;
                  horloge arrêtée (passe incomplète, sortie du terrain, changement de possession, nouveau quart-temps,
                  avertissement des 2 minutes…) : seul le chrono des 10 s tourne, au rythme de l'équipe ; temps mort :
                  TEMPS_MORT s de décompte (bannière TIMEOUT), puis le chrono ;
  l'action      : l'animation ; l'horloge s'écoule de pt secondes (le temps de jeu du moteur) à partir du snap, au
                  rythme réel — si l'action dure plus longtemps que l'animation, l'horloge continue juste après ;
  après         : le reste du temps de jeu (pt − l'animation), plus une pause quand l'horloge est arrêtée (plus longue
                  après un score ou une perte de balle). Horloge qui tourne : pas de pause, le chrono repart aussitôt.
Coups d'envoi, transformations : pas de chrono, l'horloge est arrêtée (changement de phase).
Durée garantie : pauses de retransmission comprises (PAUSES : 10 s entre deux quarts-temps, 40 s à la mi-temps), un
match ne dépasse pas BUDGET s ; au-delà, seuls les temps où l'horloge est arrêtée et qui ne sont pas fixés par la règle
(chrono utilisé horloge arrêtée, pauses après l'action, mise en place des coups de pied) sont raccourcis, jusqu'à leurs
minimums — l'horloge du match, les temps où elle tourne et les temps morts de 15 s restent en temps réel.
"""

VERSION = "ecran-2"

CHRONO = 10             # chrono d'avant-snap (s), au début de chaque action de mêlée
TEMPS_MORT = 15         # durée d'un temps mort (s)
# horloge arrêtée : chrono utilisé avant le snap selon le rythme de l'attaque
UTILISE_ARRETE = {"presse": 3, "normal": 5, "tue": 8}
AVANT_SPECIAL = {"kickoff": 4.0, "extra_point": 3.0, "two_point": 4.0}
# l'animation de l'action (s) ; l'horloge, elle, s'écoule du temps de jeu du moteur
ACTION = {"run": 3.6, "pass": 4.2, "punt": 4.4, "kickoff": 4.4, "field_goal": 3.4, "extra_point": 2.8,
          "two_point": 3.8, "kneel": 2.0, "spike": 1.4}
ETIREMENT = (0.85, 1.4)  # l'animation suit le temps de jeu entre 0,85 et 1,4 fois sa durée naturelle
APRES = 0.6              # pause après l'action, horloge arrêtée
PAUSES = {"q": 10, "half": 40}            # serveur.BREAK_SEC
BUDGET = 28 * 60                          # durée maximale d'un match à l'écran, pauses comprises (< 30 min)
MINIMUM = {"utilise": 2.0, "special": 2.0, "apres": 0.3, "score": 1.5}
APRES_SCORE = 3.0        # … après un score ou une perte de balle


def _naturelle(p):
    c = p.get("call") or {}
    t, pid = c.get("type"), c.get("play_id")
    if pid == "KNEEL":
        return ACTION["kneel"]
    if pid == "SPIKE":
        return ACTION["spike"]
    a = ACTION.get(t, 3.8)
    kr, pr = p.get("kick_return") or {}, p.get("punt_return") or {}
    if t == "kickoff" and kr and not kr.get("touchback"):
        a += min(3.0, (kr.get("return") or 0) / 15)
    if t == "punt" and pr:
        a += min(3.2, (pr.get("return") or 0) / 12) if pr.get("result") == "return" else 0 if pr.get("result") == "fair_catch" else 0.6
    return a


def _score(p):
    r = p.get("result")
    return r in ("touchdown", "field_goal_good", "safety", "interception", "fumble_lost", "two_point_good",
                 "pat_good") or bool((p.get("punt_return") or {}).get("td") or (p.get("kick_return") or {}).get("td"))


def _rythme(p, prev):
    """Rythme de l'attaque quand l'horloge est arrêtée : pressée (menée, fin de mi-temps), qui tue le temps, normal."""
    q, s = p.get("quarter") or 1, p.get("clock_start") or 0
    sc = (prev or p).get("after", {}).get("score") or {"home": 0, "away": 0}
    off = p.get("offense")
    ecart = (sc.get(off, 0) - sc.get("away" if off == "home" else "home", 0)) if off in ("home", "away") else 0
    fin = s <= 120 and q in (2, 4)
    if fin and (q == 2 or ecart <= 0):
        return "presse"
    if q == 4 and ecart > 0 and s <= 120:
        return "tue"
    return "normal"


def pauses(plays):
    """Pauses de retransmission (fins de quart-temps, mi-temps) — comme serveur.play_ends."""
    n = 0
    for p in plays:
        a = p.get("after") or {}
        if p.get("try_follows"):
            continue
        if a.get("status") == "half":
            n += PAUSES["half"]
        elif a.get("status") == "live" and p.get("clock_end") is not None and p["clock_end"] <= 0:
            n += PAUSES["q"]
    return n


def chronologie(plays, budget=BUDGET):
    """Pour chaque action : {"sec", "pre", "act", "post", "c0", "pt", "pc": [début, snap] | None, "to": côté | None,
    "tw": secondes de temps mort avant le chrono, "rt": 1}.

    c0 : l'horloge au début de l'avant-snap (elle descend jusqu'à clock_start, 1 s par seconde) ; pt : secondes de jeu
    de l'action (l'horloge les écoule à partir du snap, 1 s par seconde). Le total (pauses comprises) tient dans
    `budget` secondes (None : pas de limite).
    """
    L = _lignes(plays)
    if budget:
        fixe = sum(l["fixe"] for l in L) + pauses(plays)
        souple = sum(v for l in L for v, _ in l["souple"].values())
        marge = sum(v - m for l in L for v, m in l["souple"].values())
        exces = fixe + souple - budget
        if exces > 0 and marge > 0:
            f = max(0.0, 1 - exces / marge)
            for l in L:
                l["souple"] = {k: (m + (v - m) * f, m) for k, (v, m) in l["souple"].items()}
    out = []
    for l in L:
        sp = {k: v for k, (v, _) in l["souple"].items()}
        utilise = sp.get("utilise")
        pc = None if l["pc"] is None else [CHRONO, max(0, int(round(CHRONO - (utilise if utilise is not None else l["couru"]))))]
        pre = round(l["tw"] + l["couru"] + sp.get("utilise", 0) + sp.get("special", 0), 2)
        post = round(l["reste"] + sp.get("apres", 0), 2)
        out.append({"sec": round(pre + l["act"] + post, 2), "pre": pre, "act": l["act"], "post": post,
                    "c0": l["c0"], "pt": l["pt"], "pc": pc, "to": l["to"], "tw": l["tw"], "rt": 1})
    return out


def _lignes(plays):
    """Les temps de chaque action : fixes (horloge qui tourne, animation, temps mort) et souples (horloge arrêtée)."""
    out = []
    for i, p in enumerate(plays):
        prev = plays[i - 1] if i else None
        nxt = plays[i + 1] if i + 1 < len(plays) else None
        c = p.get("call") or {}
        k = p.get("clock") or {}
        runoff = int(k.get("runoff") or 0)
        g = max(0, int(p.get("clock_start") or 0) - int(p.get("clock_end") or 0))
        pt = max(0, g - runoff)                                      # temps de jeu de l'action (le reste : après elle)
        same_q = prev is not None and prev.get("quarter") == p.get("quarter")
        pk = (prev or {}).get("clock") or {}
        couru = int(pk.get("runoff") or 0) if same_q else 0          # l'horloge a tourné avant ce snap
        to = pk.get("timeout") if same_q else None
        tw = TEMPS_MORT if to else 0
        t = c.get("type")
        special = t in ("kickoff", "extra_point", "two_point") or p.get("conversion")
        souple = {}
        if special:
            pc = None
            souple["special"] = (AVANT_SPECIAL.get(t, AVANT_SPECIAL["extra_point"]), MINIMUM["special"])
        else:
            pc = CHRONO
            if not couru:
                souple["utilise"] = (float(min(UTILISE_ARRETE[_rythme(p, prev)], CHRONO)), MINIMUM["utilise"])
        nat = _naturelle(p)
        act = round(min(max(pt, nat * ETIREMENT[0]), nat * ETIREMENT[1]) if pt > 0 else nat, 2)
        reste = max(0.0, pt - act)                                    # l'horloge court encore après l'animation
        tourne = runoff > 0 and nxt is not None and nxt.get("quarter") == p.get("quarter")
        if not tourne:
            souple["apres"] = (APRES_SCORE, MINIMUM["score"]) if _score(p) else (APRES, MINIMUM["apres"])
        out.append({"fixe": tw + couru + act + reste, "souple": souple, "tw": tw, "couru": couru, "act": act,
                    "reste": round(reste, 2), "pc": pc, "c0": int(p.get("clock_start") or 0) + couru, "pt": pt, "to": to})
    return out
