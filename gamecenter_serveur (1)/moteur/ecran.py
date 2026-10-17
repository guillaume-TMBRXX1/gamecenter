"""Temps d'écran de la retransmission : rythme rapide, chrono d'avant-snap et temps morts visibles (16/10/2026).

Historique : jusqu'au 14/10, chaque action durait 6,5 s à l'écran ; ecran-1 (14/10) : horloge continue mais très
accélérée (« trop vite ») ; ecran-2 (15/10) : temps réel, une seconde d'écran = une seconde de match (≈ 25 min par
match : « les actions sont trop lentes »). Retour de Guillaume (16/10) : pas besoin de temps réel — une dynamique rapide
et nerveuse, le rythme des matchs de la semaine (≈ 6,5 s par action), ≈ 20 min par match et jamais plus de 25 ; garder le
chrono d'avant-snap et les temps morts ; l'horloge tourne sauf cas particuliers, sans trop accélérer.

ecran-3, pour chaque action (calculé à l'export du GameFeed, lu par le serveur et par le site) :
  avant le snap : le chrono d'avant-snap (10 s) descend de ce que l'équipe a utilisé — horloge qui tourne : le temps
                  que le moteur a fait courir entre les deux actions (moteur/horloge.py : ≈ 3 s en situation classique,
                  donc ≈ 7 restantes au snap ; 0 à 2 en hurry-up ; 9 ou 10 pour tuer l'horloge), l'horloge du match
                  descend avec lui ; horloge arrêtée (passe incomplète, sortie du terrain, changement de possession,
                  quart-temps, avertissement des 2 minutes…) : le chrono seul, au rythme de l'équipe. VITESSE secondes
                  de chrono par seconde d'écran, au moins AVANT_MIN s. Temps mort : décompte de 15 s montré en
                  TEMPS_MORT s, puis le chrono ;
  l'action      : l'animation (un peu plus rapide qu'en ecran-2) ; l'horloge s'écoule du temps de jeu pendant ce temps ;
  après         : APRES s (APRES_SCORE après un score ou une perte de balle).
Checks avant le snap (play.presnap, 16/10/2026) : l'audible coûte des secondes de chrono (horloge qui tourne : déjà dans
le temps couru par le moteur ; horloge arrêtée : ajoutées au chrono utilisé) ; une motion, un audible ou une réponse à la
motion gardent au moins AVANT_CHECK s d'écran avant le snap, une défense qui se déguise AVANT_DEGUISE s, le temps de les voir.
Coups d'envoi, transformations : pas de chrono, horloge arrêtée.
Durée garantie : pauses de retransmission comprises (PAUSES : 10 s entre deux quarts-temps, 40 s à la mi-temps), un
match ne dépasse pas BUDGET s ; au-delà, les temps où l'horloge est arrêtée et qui ne sont pas fixés par la règle
(chrono horloge arrêtée, pauses, mise en place des coups de pied) sont raccourcis jusqu'à leurs minimums.
"""

VERSION = "ecran-3"

CHRONO = 10             # chrono d'avant-snap (s)
TEMPS_MORT_AFFICHE = 15  # décompte d'un temps mort (s affichées)…
TEMPS_MORT = 4.0        # … montré en TEMPS_MORT s d'écran
VITESSE = 1.1           # secondes de chrono (et d'horloge qui tourne) par seconde d'écran, avant le snap
AVANT_MIN = 1.2         # le temps que les joueurs se replacent (au moins)
AVANT_CHECK = 2.6       # … au moins, quand l'avant-snap montre quelque chose : motion, audible du QB, défense qui se
                        # décale (checks avant le snap, moteur/presnap.py) — l'horloge descend alors plus lentement
AVANT_DEGUISE = 2.0     # … quand seule la défense se déguise (le temps de montrer sa boîte puis de se décaler au snap)
# horloge arrêtée : chrono utilisé avant le snap selon le rythme de l'attaque (secondes restantes : 9, 7, 1)
UTILISE_ARRETE = {"presse": 1, "normal": 3, "tue": 9}
AVANT_SPECIAL = {"kickoff": 2.0, "extra_point": 1.5, "two_point": 1.8}
# l'animation de l'action (s) ; l'horloge s'écoule du temps de jeu du moteur pendant ce temps
ACTION = {"run": 3.3, "pass": 3.8, "punt": 4.0, "kickoff": 4.0, "field_goal": 3.1, "extra_point": 2.5,
          "two_point": 3.4, "kneel": 1.8, "spike": 1.3}
ETIREMENT = (0.9, 1.15)  # l'animation suit un peu le temps de jeu (rapport au temps de jeu moyen PT_MOYEN)
PT_MOYEN = 5.5
APRES = 0.8              # pause après l'action
APRES_SCORE = 2.0        # … après un score ou une perte de balle
PAUSES = {"q": 10, "half": 40}            # serveur.BREAK_SEC
BUDGET = 24 * 60 + 30                     # durée maximale d'un match à l'écran, pauses comprises (< 25 min)
MINIMUM = {"utilise": 0.6, "check": 1.8, "special": 1.0, "apres": 0.3, "score": 1.0}


def _naturelle(p):
    c = p.get("call") or {}
    t, pid = c.get("type"), c.get("play_id")
    if pid == "KNEEL":
        return ACTION["kneel"]
    if pid == "SPIKE":
        return ACTION["spike"]
    a = ACTION.get(t, 3.5)
    kr, pr = p.get("kick_return") or {}, p.get("punt_return") or {}
    if t == "kickoff" and kr and not kr.get("touchback"):
        a += min(2.6, (kr.get("return") or 0) / 16)
    if t == "punt" and pr:
        a += min(2.8, (pr.get("return") or 0) / 13) if pr.get("result") == "return" else 0 if pr.get("result") == "fair_catch" else 0.5
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
    "tw": secondes d'écran du temps mort, "tl": secondes de temps mort affichées}.

    c0 : l'horloge au début de l'avant-snap (elle descend jusqu'à clock_start) ; pt : secondes de jeu de l'action
    (l'horloge les écoule pendant l'animation). Le total (pauses comprises) tient dans `budget` s (None : sans limite).
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
        pre = round(l["tw"] + l["chrono"] + sp.get("utilise", 0) + sp.get("special", 0), 2)
        post = round(sp.get("apres", 0), 2)
        out.append({"sec": round(pre + l["act"] + post, 2), "pre": pre, "act": l["act"], "post": post,
                    "c0": l["c0"], "pt": l["pt"], "pc": l["pc"], "to": l["to"], "tw": l["tw"],
                    "tl": TEMPS_MORT_AFFICHE if l["tw"] else 0})
    return out


def _lignes(plays):
    """Les temps de chaque action : fixes (horloge qui tourne, animation, temps mort) et souples (horloge arrêtée)."""
    out = []
    for i, p in enumerate(plays):
        prev = plays[i - 1] if i else None
        c = p.get("call") or {}
        k = p.get("clock") or {}
        runoff = int(k.get("runoff") or 0)
        g = max(0, int(p.get("clock_start") or 0) - int(p.get("clock_end") or 0))
        pt = max(0, g - runoff)                                      # temps de jeu de l'action (le reste : après elle)
        same_q = prev is not None and prev.get("quarter") == p.get("quarter")
        pk = (prev or {}).get("clock") or {}
        tourne = same_q and bool(pk) and pk.get("stop") is None      # l'horloge tourne jusqu'au snap
        couru = int(pk.get("runoff") or 0) if same_q else 0          # … ou un moment (avertissement des 2 minutes)
        to = pk.get("timeout") if same_q else None
        tw = TEMPS_MORT if to else 0
        t = c.get("type")
        special = t in ("kickoff", "extra_point", "two_point") or p.get("conversion")
        ps = p.get("presnap") or {}
        montre = bool(ps) and bool(ps.get("audible") or ps.get("motion_response") or ps.get("motion"))
        deguise = bool(ps) and (ps.get("box_shown") != ps.get("box_real") or ps.get("shell_shown") != ps.get("shell_real"))
        amin = AVANT_CHECK if montre else AVANT_DEGUISE if deguise else AVANT_MIN
        montre = montre or deguise
        souple, chrono, pc = {}, 0.0, None
        if special:
            souple["special"] = (AVANT_SPECIAL.get(t, AVANT_SPECIAL["extra_point"]) + couru / VITESSE, MINIMUM["special"])
        elif tourne:
            utilise = min(couru, CHRONO)
            pc = [CHRONO, CHRONO - utilise]
            chrono = round(max(amin, utilise / VITESSE), 2)          # l'horloge du match descend avec le chrono
        else:
            chrono = round(couru / VITESSE, 2)                       # l'horloge a couru puis s'est arrêtée
            utilise = min(UTILISE_ARRETE[_rythme(p, prev)] + int(ps.get("sec") or 0), CHRONO - 1)   # + l'audible
            pc = [CHRONO, CHRONO - utilise]
            souple["utilise"] = (max(amin, utilise / VITESSE), MINIMUM["check"] if montre else MINIMUM["utilise"])
        nat = _naturelle(p)
        f = min(max(pt / PT_MOYEN, ETIREMENT[0]), ETIREMENT[1]) if pt > 0 and t in ("run", "pass") else 1.0
        act = round(nat * f, 2)
        souple["apres"] = (APRES_SCORE, MINIMUM["score"]) if _score(p) else (APRES, MINIMUM["apres"])
        out.append({"fixe": tw + chrono + act, "souple": souple, "tw": tw, "chrono": chrono, "act": act, "pc": pc,
                    "c0": int(p.get("clock_start") or 0) + couru, "pt": pt, "to": to})
    return out
