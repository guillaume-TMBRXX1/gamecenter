"""Combinés sur un même match (« Same Game Combo », 30/10/2026, README section 86).

2 ou 3 sélections d'un même match, une par marché (moneyline, spread, total), avant le coup d'envoi. On ne multiplie
pas les cotes : « Win GRZ » et « GRZ −0,5 » sont presque le même pari. On calcule la probabilité que tout gagne
ENSEMBLE, à partir des probabilités du moteur publiées pour chaque sélection (les cotes simples ne changent pas) :

  ÉCART M (domicile − extérieur, entier)  moneyline et spread sont des seuils sur M : victoire domicile = M ≥ 1,
            extérieur = M ≤ −1 (égalité : moneyline remboursée), domicile couvre −2,5 = M ≥ 3, extérieur +2,5 = M ≤ 2.
            Deux seuils sur M donnent un intervalle (« gagne de 1 à 2 points »), calculé sans hypothèse :
            P(lo ≤ M ≤ hi) = G(lo) − G(hi + 1), G(k) = P(M ≥ k) connu aux points 0, 1 et à la ligne du spread ;
  TOTAL T   lié à M par une copule gaussienne de corrélation ρ : RHO_FAVORI = −0,05, mesuré sur 1 155 matchs joués
            (écart du favori contre total, écarts à la ligne) : presque indépendants. Les 50 simulations d'une
            affiche sont trop peu pour un ρ par match (± 0,14) ; une cote qui porte « corr_mt » l'impose ;
  MARGE     celle d'un combiné ordinaire : espérance visée = produit, sur les sélections, de (cote × probabilité
            juste), soit la marge de chaque cote simple ; aucune marge en plus ;
  ÉGALITÉ   (≈ 4 % des matchs) la moneyline est remboursée et le combiné continue sur les autres sélections, à leur
            cote ensemble calculée au moment du pari (« push_price ») ; la cote du combiné en tient compte.
PLANCHER  un intervalle borné des deux côtés (« gagne de 1 à 2 points ») vient de la différence de deux probabilités
            tirées de 50 simulations : bruitée. Sa probabilité est au moins PLANCHER_POINT par point d'écart couvert
            (la cote baisse, jamais l'inverse).
Refusé : un combiné impossible (« impossible ») ou qui n'ajoute rien à sa meilleure sélection (« redundant »).
Le site calcule la même cote (gamecenter_source.html, sgpPrice) ; le serveur la recalcule au moment du pari.
"""
import math
from statistics import NormalDist

VERSION = "meme-match-1"
MIN_LEGS, MAX_LEGS = 2, 3
RHO_FAVORI = -0.05            # vu du favori ; vu du domicile : −0,05 s'il est favori, +0,05 sinon
P_MIN = 0.01                    # en dessous : « impossible »
GAIN_MIN = 1.02                 # cote ≤ meilleure sélection × 1,02 : « redundant »
COTE_MAX = 30.0
PLANCHER_POINT = 0.025          # intervalle borné des deux côtés : au moins 2,5 % par point d'écart couvert
PAS = 400                       # intégration numérique (milieux) sur la copule

_N = NormalDist()


def _dec(am):
    return 1 + (am / 100 if am > 0 else 100 / -am)


_AUTRE = {"home": "away", "away": "home", "over": "under", "under": "over"}


def _juste(prix, cote):
    """Probabilité juste d'un côté, prix proportionnels retirés (cote = 1 / (p (1 + marge)))."""
    a, b = 1 / _dec(prix[cote]), 1 / _dec(prix[_AUTRE[cote]])
    return a / (a + b)


def _phi_inv(p):
    if p <= 0:
        return -math.inf
    if p >= 1:
        return math.inf
    return _N.inv_cdf(p)


def _ks(spread_home):
    """Le domicile couvre la ligne spread_home (x,5) si M ≥ ks."""
    return math.floor(-spread_home) + 1


def modele(o):
    """Ce qu'il faut savoir d'une cote d'avant-match (game.pregame_odds) : G(k) aux points connus, P(over), ρ."""
    pt = float(o.get("p_tie") or 0.0)
    ph = float(o["p_home"])
    G = {0: 1 - (1 - ph) * (1 - pt), 1: ph * (1 - pt)}
    ks = _ks(o["spread_home"])
    pc = o.get("p_home_cover")
    pc = float(pc) if pc is not None else _juste(o["spread_prices"], "home")
    if ks not in G:
        G[ks] = pc
    # G décroît : on corrige le bruit des simulations (une ligne de spread incohérente avec la moneyline)
    pts = sorted(G)
    for i in range(1, len(pts)):
        G[pts[i]] = min(G[pts[i]], G[pts[i - 1]])
    po = o.get("p_over")
    po = float(po) if po is not None else _juste(o["total_prices"], "over")
    rho = o.get("corr_mt")
    if rho is None:
        rho = RHO_FAVORI if o["spread_home"] < 0 else -RHO_FAVORI
    rho = max(-0.9, min(0.9, float(rho)))
    return {"G": G, "ks": ks, "p_over": po, "rho": rho, "p_home": ph, "p_cover": pc, "p_tie": pt}


def _contrainte(m, mk, side):
    """Intervalle [lo, hi] sur M (None = sans borne) d'une sélection moneyline / spread."""
    if mk == "ml":
        return (1, None) if side == "home" else (None, -1)
    ks = m["ks"]
    return (ks, None) if side == "home" else (None, ks - 1)


def _g(m, k):
    if k is None:
        return None
    return m["G"][k]


def _p_juste(m, mk, side):
    if mk == "ml":
        return m["p_home"] if side == "home" else 1 - m["p_home"]
    if mk == "sp":
        return m["p_cover"] if side == "home" else 1 - m["p_cover"]
    return m["p_over"] if side == "over" else 1 - m["p_over"]


def _joint(m, lo, hi, tot):
    """P(lo ≤ M ≤ hi et la sélection du total tot ∈ {None, "over", "under"})."""
    glo = 1.0 if lo is None else _g(m, lo)
    ghi = 0.0 if hi is None else _g(m, hi + 1)
    pm = glo - ghi
    if pm <= 1e-12:
        return 0.0
    k = 1.0
    if lo is not None and hi is not None:
        k = max(pm, min(PLANCHER_POINT * (hi - lo + 1), glo, 1 - ghi)) / pm
    if tot is None:
        return pm * k
    rho, c = m["rho"], _phi_inv(1 - m["p_over"])
    ua, ub = 1 - glo, 1 - ghi                           # bornes de M dans l'échelle uniforme (copule)
    s = math.sqrt(1 - rho * rho)
    acc, du = 0.0, (ub - ua) / PAS
    for i in range(PAS):
        z = _N.inv_cdf(min(1 - 1e-12, max(1e-12, ua + (i + 0.5) * du)))
        p_over = 1 - _N.cdf((c - rho * z) / s)
        acc += p_over if tot == "over" else 1 - p_over
    return acc * du * k


def _intervalle(m, legs):
    lo, hi = None, None
    for mk, side in legs:
        if mk == "tot":
            continue
        a, b = _contrainte(m, mk, side)
        if a is not None:
            lo = a if lo is None else max(lo, a)
        if b is not None:
            hi = b if hi is None else min(hi, b)
    return lo, hi


def prix(o, legs, decs):
    """Cote d'un combiné sur un même match. o = game.pregame_odds ; legs = [(marché, côté)] ; decs = cotes
    décimales des sélections (celles du site). Renvoie {"price_dec", "push_price", "p"} ou {"refus": raison}."""
    if not MIN_LEGS <= len(legs) <= MAX_LEGS:
        return {"refus": "legs"}
    if len({mk for mk, _ in legs}) != len(legs):
        return {"refus": "same_market"}
    m = modele(o)
    tot = next((s for mk, s in legs if mk == "tot"), None)
    lo, hi = _intervalle(m, legs)
    if lo is not None and hi is not None and lo > hi:
        return {"refus": "impossible"}
    p_all = _joint(m, lo, hi, tot)
    if p_all < P_MIN:
        return {"refus": "impossible"}
    V = 1.0
    for (mk, side), d in zip(legs, decs):
        V *= d * _p_juste(m, mk, side)
    push_price, p_tie_reste = None, 0.0
    if any(mk == "ml" for mk, _ in legs):              # égalité : moneyline remboursée, le reste continue
        reste = [(l, d) for l, d in zip(legs, decs) if l[0] != "ml"]
        rl = [l for l, _ in reste]
        ok = all((0 >= m["ks"]) if s == "home" else (0 <= m["ks"] - 1) for mk, s in rl if mk == "sp")
        if ok:
            p_tie_reste = _joint(m, 0, 0, tot)
        if len(reste) == 1:
            push_price = reste[0][1]
        else:
            r = prix(o, rl, [d for _, d in reste])
            push_price = r.get("price_dec")
            if push_price is None:                      # le reste seul n'est pas un combiné possible
                return {"refus": r["refus"]}
    D = (V - p_tie_reste * (push_price or 0.0)) / p_all
    if D <= max(decs) * GAIN_MIN:
        return {"refus": "redundant"}
    if len(legs) == 3:                                  # une sélection de trop : la cote d'une paire suffit
        for i in range(3):
            r = prix(o, legs[:i] + legs[i + 1:], decs[:i] + decs[i + 1:])
            if D <= r.get("price_dec", 0.0) * GAIN_MIN:
                return {"refus": "redundant"}
    D = min(D, COTE_MAX)
    out = {"price_dec": round(D, 4), "p": round(p_all, 5)}
    if push_price is not None:
        out["push_price"] = round(push_price, 4)
    return out
