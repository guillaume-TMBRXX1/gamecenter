"""Trajectoires du moteur, palier 1 : les passes (chantier du 05/11/2026, approche « descriptive »).

Le moteur décide chaque passe dans un état après le snap (bloc A) : pour CHAQUE receveur, sa route, sa séparation, son
statut (LIBRE / SERRE / COUVERT / DOUBLE) et, au bloc C, le défenseur responsable et l'oubli de couverture (bust). Le
GameFeed n'en gardait que la cible ; le site inventait le reste (qui est démarqué, quel défenseur suit qui).

`geo_passe` résume cet état sous une forme compacte pour le GameFeed (play.geo), sans rien tirer au hasard ni rien
changer : mêmes résultats, mêmes cotes. Le site dessine à partir de là (la couverture suit le moteur).

    play.geo = {"v": "geo-1", "k": "pass",
                "cov": "Cover 3", "fam": "zone", "dbl": "WR1" | None,
                "tt": 2.4,            # secondes : lancer (ou fin de l'action sans lancer)
                "ttp": 2.8,           # secondes avant la pression
                "tgt": "TE" | None,   # cible réelle
                "rec": [[rôle, séparation en yards, statut, défenseur responsable, bust], …]}

Statut : "L" libre, "S" serré, "C" couvert, "D" doublé. Défenseur : son identifiant (ex. "PRM_CB1") ou None (zone sans
responsable, ou bloc A). Séparation en yards au moment du lancer : conversion d'affichage de l'écart du moteur (en « pas »
de note) bornée par le statut, qui fait foi — LIBRE 3 à 7 yd, SERRE 1,6 à 2,9 yd, COUVERT 0,4 à 1,5 yd, DOUBLÉ 0,8 yd.
"""
from . import reaction_defensive as RD

VERSION = "geo-1"
STATUTS = {RD.LIBRE: "L", RD.SERRE: "S", RD.COUVERT: "C", RD.DOUBLE: "D"}
ORDRE = ("WR1", "WR2", "WR3", "TE", "RB")          # ordre stable dans le GameFeed (cases du site : 8, 9, 10, 5, 7)

# conversion d'affichage « pas » -> yards (seuils du moteur : LIBRE dès 0,9 pas, SERRE dès 0)
SEP_BASE, SEP_PAR_PAS, SEP_MIN, SEP_MAX, SEP_DOUBLE = 1.6, 1.6, 0.4, 7.0, 0.8


def separation_yards(pas, statut):
    """Séparation affichée (yards) pour un écart du moteur en « pas » et son statut."""
    if statut == RD.DOUBLE:
        return SEP_DOUBLE
    y = SEP_BASE + SEP_PAR_PAS * float(pas)
    lo, hi = {RD.LIBRE: (3.0, SEP_MAX), RD.SERRE: (1.6, 2.9)}.get(statut, (SEP_MIN, 1.5))   # le statut fait foi
    return round(min(hi, max(lo, y)), 1)


def geo_passe(etat, decision):
    """play.geo d'une passe décidée : état après le snap de chaque receveur + lancer. etat : PostSnapState (ou son dict),
    decision : QBDecision (ou son dict). Aucun tirage : purement descriptif."""
    E = etat if isinstance(etat, dict) else etat.to_dict()
    D = decision if isinstance(decision, dict) else decision.__dict__
    recs = E.get("receveurs") or {}
    rang = {r: i for i, r in enumerate(ORDRE)}
    rec = []
    for role in sorted(recs, key=lambda r: (rang.get(r, 99), r)):
        e = recs[role]
        statut = e.get("statut")
        rec.append([role, separation_yards(e.get("separation", 0.0), statut), STATUTS.get(statut, "C"),
                    e.get("couvreur_id") or None, 1 if e.get("bust") else 0])
    return {"v": VERSION, "k": "pass",
            "cov": E.get("couverture") or None, "fam": E.get("famille") or None, "dbl": E.get("double_sur") or None,
            "tt": round(float(D.get("temps_lancer") or 0.0), 2), "ttp": round(float(E.get("temps_pression") or 0.0), 2),
            "tgt": D.get("cible") or None, "rec": rec}


def controler(geo):
    """Problèmes d'un play.geo de passe (liste vide : conforme). Sert aux contrôles du notebook et aux tests."""
    pb = []
    if not isinstance(geo, dict) or geo.get("v") != VERSION or geo.get("k") != "pass":
        return ["version ou type"]
    roles = [r[0] for r in geo.get("rec") or []]
    if len(set(roles)) != len(roles):
        pb.append("receveur en double")
    for r in geo.get("rec") or []:
        if len(r) != 5 or r[2] not in "LSCD" or not (SEP_MIN <= r[1] <= SEP_MAX):
            pb.append(f"receveur mal formé : {r}")
    if geo.get("tgt") and geo["tgt"] not in roles:
        pb.append("cible absente des receveurs")
    if geo.get("tt", 0) < 0 or geo.get("ttp", 0) < 0:
        pb.append("temps négatif")
    return pb
