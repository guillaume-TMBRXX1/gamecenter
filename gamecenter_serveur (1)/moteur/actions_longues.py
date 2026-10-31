"""Actions longues et retours d'interception (chantier du 30/10/2026, README section 85).

Constat (semaine du 26/10, 279 matchs) : les tables de yards de la V0.2 (calculate_run_yards : course bornée à 25 yards ;
calculate_pass_yards : passe complétée bornée à 40) sont toujours le socle du moteur ; les couches suivantes (bloc C :
yards après réception ±3 ; bloc F : ajustement de la course) restent autour. Par match (les deux équipes) : 0,64 course
de 20 yards et plus, aucune de 40 ; 5,1 passes complétées de 20 yards et plus, 0,07 de 40 (≈ 1, 0,2, 7,5 et 1 en NFL).
Et un retour d'interception tiré entre −5 et 0 yard : le défenseur qui intercepte s'arrête aussitôt.

Ce module ajoute la QUEUE des distributions, sans changer leur moyenne :
  COURSE    le porteur qui passe le 2e rideau (gain déjà ≥ SEUIL_COURSE) peut s'échapper : chance selon sa vitesse et
            son agilité contre la vitesse des safeties ; yards en plus tirés d'une loi exponentielle (beaucoup de petits
            ajouts, quelques très longs), sans limite autre que l'en-but (le moteur arrête le gain à la ligne de but) ;
  PASSE     la réception lancée profond (gain ≥ SEUIL_PROFOND) peut filer, et une réception plus courte peut devenir
            une longue course après la réception (YAC) : vitesse du receveur contre celle de la couverture ;
  MOYENNE   pour garder les yards moyens par action (calibrage des scores, des cotes et du test d'équilibre), un gain
            « moyen » (bornes RABOT) perd en moyenne p yard(s), p réglé pour compenser l'ajout moyen (cellule : P_RABOT) ;
  INTERCEPTION  le ballon est intercepté à la profondeur de la passe (route de la cible), puis le défenseur le ramène :
            souvent quelques yards, parfois loin, jusqu'à l'en-but adverse (pick-six), selon sa vitesse contre la
            poursuite de l'attaque. Interception dans l'en-but sans retour : touchback.
Tout est un tirage dans un flux dédié (moteur/aleatoire.py, « longues|graine|n° d'action ») : le hasard du moteur
n'est pas consommé. Notes : vitesse et agilité ramenées à la moyenne de la ligue (MOY_VITESSE).
"""
import math

from . import aleatoire

VERSION = "longues-1"

MOY_VITESSE = 82.0              # vitesse moyenne d'un porteur / défenseur de la ligue (notes 60-99)

# course : échappée au-delà du 2e rideau
SEUIL_COURSE = 8                # gain déjà acquis pour « passer » le 2e rideau
P_COURSE = 0.05                # chance d'échappée d'un porteur moyen contre des safeties moyens
K_COURSE = 0.045                # par point de vitesse d'écart (porteur - safeties)
MOY_COURSE = 30.0               # yards en plus, moyenne de la loi exponentielle
# passe : profonde qui file, ou réception courte qui devient une longue course (YAC)
SEUIL_PROFOND = 16
P_PROFOND = 0.30
MOY_PROFOND = 19.0
SEUIL_YAC = 6
P_YAC = 0.11
MOY_YAC = 15.0
K_PASSE = 0.04
# compensation : -1 yard sur une part des gains moyens
RABOT = {"run": (2, 10), "pass": (4, 18)}
# retour d'interception
P_RETOUR_NUL = 0.16             # glissé / poussé en touche / à genou aussitôt
MOY_RETOUR = 8.5                # retour ordinaire (loi exponentielle)
P_ECHAPPEE_INT = 0.21           # le retour qui trouve de l'espace
MOY_ECHAPPEE_INT = 32.0
K_INT = 0.05
AIR_DEFAUT = 10                 # profondeur d'une interception sans route connue


def _vitesse(r, *cles):
    r = r or {}
    v = [r[k] for k in cles if isinstance(r.get(k), (int, float))]
    return sum(v) / len(v) if v else MOY_VITESSE


def _chance(base, k, ecart):
    """Chance de base modulée par l'écart de vitesse (logistique, bornée entre base/3 et base·3)."""
    f = math.exp(k * ecart)
    return max(base / 3, min(base * 3, base * f))


def _exp(rng, moyenne):
    return -moyenne * math.log(1.0 - rng.random())


def ajout(kind, gain, porteur, defense, rng):
    """Yards en plus d'une course (kind="run") ou d'une passe complétée (kind="pass") : échappée ou rien.
    porteur, defense : notes ({"speed": …}) ; defense = liste des défenseurs du 2e rideau (safeties, CB, LB).
    Renvoie (yards en plus ≥ 0, étiquette ou None)."""
    vp = _vitesse(porteur, "speed", "acceleration", "elusiveness") if kind == "run" else _vitesse(porteur, "speed", "acceleration")
    vd = sum(_vitesse(d, "speed") for d in defense) / len(defense) if defense else MOY_VITESSE
    if kind == "run":
        if gain < SEUIL_COURSE:
            return 0, None
        if rng.random() < _chance(P_COURSE, K_COURSE, vp - vd):
            return int(round(_exp(rng, MOY_COURSE))), "breakaway"
        return 0, None
    if gain >= SEUIL_PROFOND:
        if rng.random() < _chance(P_PROFOND, K_PASSE, vp - vd):
            return int(round(_exp(rng, MOY_PROFOND))), "deep"
    elif gain >= SEUIL_YAC:
        if rng.random() < _chance(P_YAC, K_PASSE, vp - vd):
            return int(round(_exp(rng, MOY_YAC))), "yac"
    return 0, None


def rabot(kind, gain, p, rng):
    """Compensation de la moyenne sur un gain « moyen » : −p yard en espérance (⌊p⌋ yards, plus 1 avec la
    probabilité de la partie décimale de p)."""
    lo, hi = RABOT[kind]
    if not lo <= gain <= hi:
        return 0
    k = int(p)
    return -(k + (1 if rng.random() < p - k else 0))


def retour_interception(ligne, air, intercepteur, attaque, rng):
    """Retour d'une interception. ligne : ligne de mêlée dans le repère de l'attaque (0 = son en-but, 100 = en-but
    adverse) ; air : profondeur de la passe. Renvoie {air, point, retour, fin, td, touchback, echappee} — point et fin
    dans le repère de l'attaque (fin ≤ 0 : touchdown de la défense)."""
    point = max(1, min(110, ligne + max(0, int(air))))
    if point >= 100:                                     # dans l'en-but : on reste à genou (touchback)
        if rng.random() < 0.75:
            return {"air": point - ligne, "point": min(point, 105), "retour": 0, "fin": 100, "td": False,
                    "touchback": True, "echappee": False}
        point = 100
    vd = _vitesse(intercepteur, "speed", "acceleration")
    va = sum(_vitesse(a, "speed") for a in attaque) / len(attaque) if attaque else MOY_VITESSE
    echappee = False
    if rng.random() < P_RETOUR_NUL:
        r = int(rng.random() * 3)
    else:
        r = _exp(rng, MOY_RETOUR)
        if rng.random() < _chance(P_ECHAPPEE_INT, K_INT, vd - va):
            r += _exp(rng, MOY_ECHAPPEE_INT)
            echappee = True
        r = int(round(r))
    fin = point - r
    td = fin <= 0
    if td:
        r, fin = point, 0
    return {"air": point - ligne, "point": point, "retour": r, "fin": fin, "td": td, "touchback": False,
            "echappee": echappee}


def tirer_ajout(graine, n, kind, gain, porteur, defense, p_rabot):
    """ajout() puis la compensation, dans le flux dédié « longues|graine|n ». Renvoie (delta, étiquette)."""
    rng = aleatoire.flux("longues", graine, n)
    plus, tag = ajout(kind, gain, porteur, defense, rng)
    if plus:
        return plus, tag
    return rabot(kind, gain, p_rabot, rng), None


def tirer_retour(graine, n, ligne, air, intercepteur, attaque):
    return retour_interception(ligne, air, intercepteur, attaque, aleatoire.flux("longues-int", graine, n))


CONVERSIONS = ("pat_good", "pat_missed", "two_point_good", "two_point_failed")


def fin_de_periode(plays):
    """Pick-six sur la dernière action d'une mi-temps ou du match (GameFeed) : comme un touchdown ordinaire, l'action
    reste « live » et c'est la transformation qui la suit, jouée dans la même période, horloge à 0, qui termine la
    mi-temps (« half ») ou le match. Sans cela la transformation passait après la mi-temps (3e quart-temps) et le site
    sautait la pause de la mi-temps (semaine du 02/11, w6-r275). Modifie plays sur place ; renvoie le nombre de cas."""
    n = 0
    for p, q in zip(plays, plays[1:]):
        st = (p.get("after") or {}).get("status")
        if not ((p.get("int_return") or {}).get("td") and st in ("half", "final") and q.get("result") in CONVERSIONS):
            continue
        q["quarter"] = p["quarter"]
        q["clock_start"] = q["clock_end"] = 0
        q["after"]["status"] = st
        p["after"]["status"] = "live"
        n += 1
    return n
