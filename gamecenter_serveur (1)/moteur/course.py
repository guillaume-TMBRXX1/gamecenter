"""Bloc F — intelligence du jeu de course : boîte, point d'attaque, duels de ligne, lecture du porteur, contact.

Constat (14/10/2026, 552 matchs, 28 711 courses, horloge réelle) : la course était résolue au niveau de l'équipe
(`simulate_run(run_off, run_def)` + modificateurs) ; le porteur était désigné après coup. Conséquences :
  - un effet « boîte » en tout ou rien : contre BOX_STACK (30 % des courses) 2,5 yards et 33 % de courses bloquées,
    contre tout le reste ≈ 6,7 yards et 25 % de courses de 10+ (intention défensive course / passe : ± 2 yards) ;
  - le concept ne rencontrait pas la défense (inside 5,3 · gap 5,7 · outside 5,4 yards) ;
  - les joueurs ne pesaient pas : un WR sur jet sweep courait comme le RB1 ; ni la ligne offensive ni la ligne
    défensive au point d'attaque, ni le profil du porteur ne changeaient le résultat (régression : effets nuls).

Ce module construit l'état d'une course après le snap et en tire un ajustement des yards :
  BOÎTE        défenseurs près de la ligne (formation défensive, appel, front, paquet) contre les bloqueurs (5 OL + TE) :
               un défenseur de plus que de bloqueurs = un « chapeau » non bloqué ; effet mesuré et borné (`BOITE`),
               qui remplace le ± 2 yards de l'intention défensive ;
  POINT D'ATTAQUE  côté (gauche / droite) et trous selon la classe du concept (inside : centre et guards contre DT et
               MLB ; gap : guard, tackle, TE contre DT, EDGE, LB ; outside / perimeter : tackle et TE contre EDGE, LB,
               safety ; option : le bord lu ; qb : le centre). L'attaque choisit le côté où ses duels sont meilleurs
               (probabilité `CHOIX_COTE`, ses observations du match) ;
  DUELS        bloc (run_block, strength) contre défenseur (strength, tackling) — par rapport à la MOYENNE de chaque ligne :
               le niveau des unités est déjà dans le tirage du moteur, ce module ne compte que ce qui le dépasse ;
  TROU         ouvert / étroit / fermé (marge des duels + chapeaux non bloqués + front contre la classe + bruit) ;
  LECTURE      trou fermé : le porteur lit (vision = elusiveness + acceleration) — cutback (inside, gap) ou rebond vers
               l'extérieur (outside, perimeter) ; sinon bloqué. Trou ouvert : la vitesse contre celle du safety ;
  CONTACT      premier défenseur au contact (au point d'attaque, le chapeau non bloqué, le LB qui remplit, le safety) ;
               yards après contact : power du porteur contre tackling du plaqueur.
               Tout est un PROFIL, jamais un niveau (le niveau est dans la note d'unité du tirage du moteur) : vision,
               puissance et vitesse du porteur par rapport à sa note globale ; plaqueur et safety par rapport à la
               moyenne de leur défense ;
  PORTEUR      écart du RB porteur au RB1 (le RB1 est dans la note d'unité) : le RB2 a ses propres notes (un WR ou le QB
               n'ont pas de notes de course comparables : leurs concepts portent déjà leur effet).
Hasard : flux dédié « course|<graine>|<n° d'action> ». Le hasard du moteur n'est pas consommé.
"""
import math

from . import aleatoire

VERSION = "course-1"

# boîte de base par formation défensive ; appels et paquets qui ajoutent / retirent un défenseur
BOITE_FORMATION = {"GOAL_LINE": 8, "4_3": 7, "3_4": 7, "NICKEL": 6, "DIME": 6}
BOITE_APPEL = {"BOX_STACK": 1, "BLITZ": 1}
BOITE_PAQUET = {"BOX_SKY": 0, "BOX_ROBBER": 0, "COVER_1_ROBBER": 1, "COVER_3_SKY": 1, "COVER_3_BUZZ": 1,
                "SEVEN_MAN_PRESSURE": 1, "MUG_BLITZ": 0}
BOITE_DIME = -1                  # dime : 6 au mieux, souvent 5 (un LB de moins)
BLOQUEURS = 6                    # 5 OL + 1 TE (personnel 11 / 12 : le moteur n'aligne qu'un TE au roster)
# yards (moyenne) selon la boîte, centré sur 7 (mesuré en NFL : ≈ 1 yard entre une boîte légère et une boîte chargée ;
# ici un peu plus, la ligue court à 5,5 yards)
BOITE = {5: 0.9, 6: 0.5, 7: 0.0, 8: -0.85, 9: -1.4}

# point d'attaque : (bloqueurs, défenseurs) par classe ; L / R = côté choisi, C = centre
POINT = {
    "inside":    (("C", "G"), ("DT", "LB")),
    "gap":       (("G", "T", "TE"), ("DT", "EDGE", "LB")),
    "outside":   (("T", "TE"), ("EDGE", "LB", "S")),
    "perimeter": (("T", "TE"), ("EDGE", "S", "CB")),
    "option":    (("T", "G"), ("EDGE", "LB")),
    "qb":        (("C", "G"), ("DT", "LB")),
}
COUPE = {"inside": "cutback", "gap": "cutback", "outside": "bounce", "perimeter": "bounce", "option": "keep",
         "qb": "cutback"}
# fronts : avantage (+) ou désavantage (−) de la défense contre la classe, en points de duel (FRONTS de l'extension)
FRONT_CLASSE = {"BEAR": {"inside": 3, "gap": 2, "outside": -2, "perimeter": -3},
                "TITE": {"inside": 2, "gap": 1.5, "outside": -1.5, "perimeter": -1.5},
                "SHORT_YARDAGE": {"inside": 2.5, "gap": 2.5, "outside": -2, "perimeter": -3},
                "MINT": {"inside": 1.5, "gap": 1, "outside": -1},
                "STACK": {"inside": -1, "outside": 1, "perimeter": 1.5},
                "NASCAR": {"inside": -2.5, "gap": -2, "qb": -1.5},
                "4_3_OVER": {"inside": 1, "outside": -1}, "4_3_UNDER": {"gap": 1, "inside": -0.5}}

CHOIX_COTE = 0.65                # l'attaque court du côté où ses duels sont meilleurs 65 % du temps
BRUIT = 8.0                      # bruit du trou (points de duel)
SEUIL = 8.0                      # trou ouvert au-delà de +SEUIL, fermé en deçà de −SEUIL
CHAPEAU = 5.0                    # chaque défenseur non bloqué au-delà du premier : −2,5 points de duel
K_TROU = 0.11                    # yards par point de duel (marge du trou)
K_PORTEUR = 0.10                 # yards par point d'écart du porteur au RB1
K_CONTACT = 0.05                 # yards après contact par point (power − tackling)
K_VITESSE = 0.08                 # yards par point de vitesse (porteur − safety), trou ouvert seulement
LECTURE = (0.35, 0.012)          # probabilité de trouver un cutback / rebond : base + par point de vision (profil)
GAIN_LECTURE = (2.0, 4.0)        # yards gagnés par un cutback / rebond réussi (uniforme)
PERTE_BLOQUE = (0.5, 2.0)        # yards perdus quand le trou est fermé et rien ne se trouve
CALIBRATION = 1.47               # yards ajoutés à toutes les courses : garde la moyenne de la ligue (rapport du bloc F)
BORNE = 8                        # ajustement borné à ± BORNE yards


def note_bloc(r):
    return 0.6 * r.get("run_block", 70) + 0.4 * r.get("strength", 70)


def note_def(r, poste):
    if poste in ("S", "CB"):
        return 0.5 * r.get("run_support", r.get("tackling", 70)) + 0.5 * r.get("tackling", 70)
    return 0.6 * r.get("strength", 70) + 0.4 * r.get("tackling", 70)


def note_porteur(r):
    return (r.get("speed", 70) + r.get("elusiveness", r.get("mobility", 70)) + r.get("power", 70)
            + r.get("acceleration", r.get("speed", 70))) / 4


def _moy(joueurs, cle):
    v = [j["ratings"][cle] for j in joueurs if cle in j["ratings"]]
    return sum(v) / len(v) if v else 70.0


def boite(formation_defensive, appel=None, paquet=None, front=None):
    """Défenseurs dans la boîte (5-9)."""
    b = BOITE_FORMATION.get(formation_defensive, 7) + BOITE_APPEL.get(appel, 0) + BOITE_PAQUET.get(paquet, 0)
    if formation_defensive == "DIME":
        b += BOITE_DIME
    if front in ("BEAR", "SHORT_YARDAGE"):
        b += 1
    return max(5, min(9, b))


def _cote(joueurs, poste, cote):
    """Joueurs d'un poste d'un côté : OL (LT/LG à gauche, RG/RT à droite, C au centre) ; défense : ordre du roster
    (le premier à gauche de l'attaque, le second à droite ; LB / S : le MLB au centre)."""
    if poste in ("G", "T"):
        nom = ("L" if cote == "L" else "R") + poste
        return [j for j in joueurs if j["pos"] == nom]
    if poste == "C":
        return [j for j in joueurs if j["pos"] == "C"]
    groupe = [j for j in joueurs if j["pos"] == poste]
    if not groupe:
        return []
    if poste in ("LB",) and len(groupe) >= 3:
        return [groupe[0]]                                     # le MLB remplit au centre ou du côté de la course
    i = 0 if cote == "L" else min(1, len(groupe) - 1)
    return [groupe[i]]


def _duels(attaque, defense, classe, cote, moy_ol, moy_dl):
    blo, dfs = POINT.get(classe, POINT["inside"])
    bloqueurs = [j for p in blo for j in _cote(attaque["bloqueurs"], p, cote)]
    defenseurs = [j for p in dfs for j in _cote(defense["defenseurs"], p, cote)]
    duels = []                                   # un duel par paire ; les défenseurs non bloqués viennent de la boîte
    for b, d in zip(bloqueurs, defenseurs):
        nd = note_def(d["ratings"], d["pos"]) - moy_dl
        nb = note_bloc(b["ratings"]) - moy_ol
        duels.append({"bloqueur": b["id"], "defenseur": d["id"], "marge": round(nb - nd, 1)})
    return duels, defenseurs


def _moyennes(attaque, defense):
    ol = [note_bloc(j["ratings"]) for j in attaque["bloqueurs"]]
    dl = [note_def(j["ratings"], j["pos"]) for j in defense["defenseurs"] if j["pos"] in ("DT", "EDGE", "LB")]
    return (sum(ol) / len(ol) if ol else 70.0), (sum(dl) / len(dl) if dl else 70.0)


def choisir_cote(attaque, defense, classe, rng):
    """Côté de la course : celui où la somme des marges est la meilleure, avec la probabilité CHOIX_COTE."""
    moy_ol, moy_dl = _moyennes(attaque, defense)
    m = {c: sum(d["marge"] for d in _duels(attaque, defense, classe, c, moy_ol, moy_dl)[0]) for c in ("L", "R")}
    meilleur = "L" if m["L"] >= m["R"] else "R"
    if rng.random() < CHOIX_COTE:
        return meilleur, m
    return ("R" if meilleur == "L" else "L"), m


def courir(concept, classe, attaque, defense, b, graine, n, front=None, rb1=None):
    """État d'une course et ajustement des yards.

    attaque : {"bloqueurs": [{"id", "pos" (LT LG C RG RT TE), "ratings"}], "porteur": {"id", "pos", "ratings"}}
    defense : {"defenseurs": [{"id", "pos" (EDGE DT LB S CB), "ratings"}]}
    b       : défenseurs dans la boîte (boite()) ; rb1 : notes du RB1 (référence du porteur, dans la note d'unité)
    Renvoie {"delta", "trou", "lecture", "cote", "boite", "chapeaux", "duel", "plaqueur", "contact", …}.
    """
    rng = aleatoire.flux("course", graine, n)
    classe = classe if classe in POINT else "inside"
    cote, marges = choisir_cote(attaque, defense, classe, rng)
    moy_ol, moy_dl = _moyennes(attaque, defense)
    duels, defenseurs = _duels(attaque, defense, classe, cote, moy_ol, moy_dl)
    chapeaux = max(0, b - BLOQUEURS)
    front_k = FRONT_CLASSE.get(front, {}).get(classe, 0)
    marge = (sum(d["marge"] for d in duels) / max(1, len(duels))) - front_k
    trou_pts = marge - CHAPEAU * max(0, chapeaux - 1) * 0.5 + rng.gauss(0.0, BRUIT)
    trou = "ouvert" if trou_pts > SEUIL else "ferme" if trou_pts < -SEUIL else "etroit"
    p = attaque["porteur"]["ratings"] if attaque.get("porteur") else {}
    ref = rb1 if rb1 is not None else p
    ecart_rb = note_porteur(p) - note_porteur(ref) if attaque.get("porteur", {}).get("pos") == "RB" else 0.0
    delta = BOITE.get(b, 0.0) + K_TROU * trou_pts + K_PORTEUR * ecart_rb
    lecture = "plan"
    # profil du porteur (au-delà de son niveau, déjà dans la note d'unité) : vision, puissance, vitesse par rapport à
    # sa note globale ; défenseurs : écart à la moyenne de leur défense
    niveau = note_porteur(p)
    vision = (p.get("elusiveness", p.get("mobility", 70)) + p.get("acceleration", p.get("speed", 70))) / 2 - niveau
    moy_tk = _moy(defense["defenseurs"], "tackling")
    moy_vit = _moy([j for j in defense["defenseurs"] if j["pos"] in ("S", "CB")], "speed")
    if trou == "ferme":
        if rng.random() < LECTURE[0] + LECTURE[1] * vision:
            lecture = COUPE[classe]
            delta += rng.uniform(*GAIN_LECTURE)
        else:
            lecture = "bloque"
            delta -= rng.uniform(*PERTE_BLOQUE)
    # premier défenseur au contact : au point d'attaque (trou fermé), le LB qui remplit, le safety (trou ouvert)
    if trou == "ferme" and lecture == "bloque":
        perdus = [d for d in duels if d["marge"] < 0] or duels
        plaqueur = min(perdus, key=lambda d: d["marge"])["defenseur"] if perdus else None
        contact = "ligne"
    elif trou == "ouvert":
        s = [j for j in defense["defenseurs"] if j["pos"] in ("S", "CB")]
        plaqueur = s[0]["id"] if s else None
        contact = "second rideau"
        if s:
            delta += K_VITESSE * ((p.get("speed", 70) - niveau) - (s[0]["ratings"].get("speed", moy_vit) - moy_vit))
    else:
        lbs = [j for j in defense["defenseurs"] if j["pos"] == "LB"]
        plaqueur = (lbs[0] if lbs else (defenseurs[0] if defenseurs else {"id": None}))["id"]
        contact = "linebacker"
    tq = next((j for j in defense["defenseurs"] if j["id"] == plaqueur), None)
    if tq is not None:
        delta += K_CONTACT * ((p.get("power", 70) - niveau) - (tq["ratings"].get("tackling", moy_tk) - moy_tk))
    delta = max(-BORNE, min(BORNE, delta + CALIBRATION))
    return {"version": VERSION, "delta": round(delta, 2), "trou": trou, "trou_pts": round(trou_pts, 1),
            "lecture": lecture, "cote": cote, "marges_cotes": {k: round(v, 1) for k, v in marges.items()},
            "boite": b, "chapeaux": chapeaux, "front": front, "classe": classe, "duels": duels,
            "plaqueur": plaqueur, "contact": contact}


def entier(delta, graine, n):
    """Ajustement en yards entiers, sans biais (arrondi au hasard, flux « course-arrondi »)."""
    k = math.floor(delta)
    return int(k + (1 if aleatoire.flux("course-arrondi", graine, n).random() < delta - k else 0))
