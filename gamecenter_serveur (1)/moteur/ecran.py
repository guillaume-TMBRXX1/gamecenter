"""Temps d'écran de la retransmission (14/10/2026) : l'horloge du match s'écoule en continu, le chrono des 40 s aussi.

Avant : chaque action durait 6,5 s à l'écran, qu'elle ait pris 3 s ou 40 s de match ; l'horloge sautait d'un bloc
d'une action à l'autre (« on ne s'y retrouve pas »), rien ne montrait si une équipe pressait ou tuait le temps, et un
match durait ≈ 18,5 min.

Désormais, pour chaque action (calculé à l'export du GameFeed, lu par le serveur et par le site) :
  avant le snap  : AVANT_MIN s, plus le temps du chrono des 40 s utilisé, accéléré VITESSE fois. Si l'horloge du
                   match tourne entre les deux actions (course dans le terrain, passe complétée…), elle s'écoule avec
                   le chrono — le temps entre les actions du moteur (horloge réelle, 12.2 quaterdecies) ; si elle est
                   arrêtée (passe incomplète, sortie, changement de possession, temps mort…), seul le chrono tourne,
                   au rythme de l'équipe (pressée, normal, qui tue le temps) ;
  l'action       : le temps de l'animation (course, passe, coup de pied, retour) ; l'horloge s'écoule du temps de jeu ;
  après          : APRES s (APRES_SCORE après un score ou une perte de balle).
Chrono des 40 s : 40 après une action, 25 après un temps mort, un changement de possession ou un quart-temps ; on lit
au snap ce qu'il restait (4 : l'équipe a tué le temps ; 25 : elle a pressé). Calibré pour ≈ 15 min par match, pauses
comprises (moyenne de la ligue).
"""

VERSION = "ecran-1"

VITESSE = 26.0          # secondes de chrono (et d'horloge qui tourne) par seconde d'écran, avant le snap
AVANT_MIN = 0.7         # le temps que les joueurs se replacent
FACTEUR = 0.8           # l'animation de l'action, un peu plus rapide qu'avant (6,5 s par action → ≈ 5,3 s en moyenne)
ACTION = {"run": 3.2, "pass": 3.7, "punt": 3.9, "kickoff": 3.9, "field_goal": 3.2, "extra_point": 2.6,
          "two_point": 3.4, "kneel": 1.8, "spike": 1.4}
APRES = 0.6
APRES_SCORE = 1.8
TEMPS_MORT = 1.2        # le temps mort à l'écran (bannière), en plus
CHRONO, CHRONO_COURT = 40, 25
# horloge arrêtée : chrono utilisé avant le snap selon le rythme de l'attaque
UTILISE_ARRETE = {"presse": 12, "normal": 24, "tue": 34}


def _action(p):
    c = p.get("call") or {}
    t, pid = c.get("type"), c.get("play_id")
    if pid == "KNEEL":
        return ACTION["kneel"]
    if pid == "SPIKE":
        return ACTION["spike"]
    a = ACTION.get(t, 3.4)
    kr, pr = p.get("kick_return") or {}, p.get("punt_return") or {}
    if t == "kickoff" and kr and not kr.get("touchback"):
        a += min(2.4, (kr.get("return") or 0) / 18)
    if t == "punt" and pr:
        a += min(2.6, (pr.get("return") or 0) / 14) if pr.get("result") == "return" else 0 if pr.get("result") == "fair_catch" else 0.5
    return round(a * FACTEUR, 2)


def _score(p):
    r = p.get("result")
    return r in ("touchdown", "field_goal_good", "safety", "interception", "fumble_lost") or bool(
        (p.get("punt_return") or {}).get("td") or (p.get("kick_return") or {}).get("td"))


def _rythme(p, prev):
    """Rythme de l'attaque quand l'horloge est arrêtée : pressée (menée, fin de mi-temps), qui tue le temps, normal."""
    q, s = p.get("quarter") or 1, p.get("clock_start") or 0
    sc = (prev or p).get("after", {}).get("score") or {"home": 0, "away": 0}
    off = p.get("offense")
    ecart = (sc.get(off, 0) - sc.get("away" if off == "home" else "home", 0)) if off in ("home", "away") else 0
    fin = s <= 120 and q in (2, 4)
    if fin and (q == 2 or ecart <= 0):
        return "presse"
    if q == 4 and ecart > 0 and s <= 300:
        return "tue"
    return "normal"


def chronologie(plays):
    """Pour chaque action : {"sec", "pre", "act", "post", "c0", "pt", "pc": [début, snap] | None, "to": côté | None}.

    c0 : l'horloge au début de l'avant-snap (elle descend jusqu'à clock_start) ; pt : secondes de jeu de l'action.
    """
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
        couru = int(pk.get("runoff") or 0) if same_q else 0          # l'horloge a tourné avant ce snap
        to = pk.get("timeout") if same_q else None
        special = c.get("type") in ("kickoff", "extra_point", "two_point") or p.get("conversion")
        if special:
            pc, utilise = None, 0
        else:
            debut = CHRONO_COURT if (to or not same_q or (prev or {}).get("possession_change")) else CHRONO
            utilise = couru if couru else UTILISE_ARRETE[_rythme(p, prev)]
            utilise = min(utilise, debut - 1)
            pc = [debut, debut - utilise]
        pre = round(AVANT_MIN + utilise / VITESSE + (TEMPS_MORT if to else 0), 2)
        act = _action(p)
        post = APRES_SCORE if _score(p) else APRES
        out.append({"sec": round(pre + act + post, 2), "pre": pre, "act": act, "post": post,
                    "c0": int(p.get("clock_start") or 0) + couru, "pt": pt, "pc": pc, "to": to})
    return out
