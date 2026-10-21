"""Pénalités pendant l'action (étape 7.2 de la feuille de route « moteur plus intelligent », 21/10/2026).

Avant : aucune pénalité, ni dans le moteur ni sur le site. Décision de Guillaume (plan validé le 21/10) : seulement les
fautes PENDANT l'action — holding (attaque et défense), roughing the passer, interférences de passe (défense et attaque),
illegal contact — environ 8 drapeaux par match (les deux équipes, refusés compris) ; pas de faute d'avant le snap (false
start, offside, delay of game, illegal formation). L'équipe adverse accepte ou refuse selon la PROBABILITÉ DE VICTOIRE.

Qui commet la faute (un profil, pas un niveau) :
  HOLDING OFFENSIF   le bloqueur qui perd son duel (poche de l'étape 7.1) ; à la course, un bloqueur de la ligne / TE,
                     d'autant plus qu'il est faible au bloc de course.
  HOLDING DÉFENSIF   un défenseur en couverture, selon sa discipline.
  ILLEGAL CONTACT    un CB / S en couverture, selon sa discipline (tôt dans la route).
  INTERFÉRENCE (DPI) le défenseur responsable de la cible, sur un ballon disputé (plus souvent loin).
  INTERFÉRENCE (OPI) la cible, sur un ballon disputé.
  ROUGHING           le rusher qui a gagné son duel et touche le QB après le lancer (pression : bien plus souvent).
  Une équipe dont l'identité dit « discipline » en commet moins.

Ce qu'elles coûtent (règles NFL, moitié de la distance près des en-buts) :
  holding offensif, OPI : 10 yards depuis la ligne de scrimmage, essai rejoué ;
  holding défensif, illegal contact : 5 yards et premier essai automatique ;
  DPI : ballon à l'endroit de la faute (aux 1 si elle a lieu dans l'en-but), premier essai automatique ;
  roughing : 15 yards et premier essai automatique, ajoutés à la fin de l'action si la passe est complétée.
  Acceptée, une faute ANNULE l'action (sauf roughing après une passe complétée : l'action compte, les 15 yards s'ajoutent).

Accepter ou refuser : l'équipe qui subit la faute compare la probabilité de victoire des deux états (moteur/valeur.py :
même loi de la marge finale, points attendus d'un essai selon down, distance et position). Un drapeau au plus par action.
Pas de faute de la défense sur une interception, un fumble ou un safety (elle annulerait un changement de possession :
cas rares, laissés de côté), pas de roughing sur un touchdown (la NFL l'applique au coup d'envoi).

Déterministe : le tirage vient du flux dédié « penalites » (graine du match, n° d'action).
"""
import math

from moteur import valeur as V

VERSION = "penalites-1"
FLUX = "penalites"

OFF_HOLDING = "offensive_holding"
DEF_HOLDING = "defensive_holding"
ILLEGAL_CONTACT = "illegal_contact"
DPI = "defensive_pass_interference"
OPI = "offensive_pass_interference"
ROUGHING = "roughing_the_passer"
TYPES = (OFF_HOLDING, DEF_HOLDING, ILLEGAL_CONTACT, DPI, OPI, ROUGHING)
NOMS = {OFF_HOLDING: "Offensive holding", DEF_HOLDING: "Defensive holding", ILLEGAL_CONTACT: "Illegal contact",
        DPI: "Pass interference", OPI: "Offensive pass interference", ROUGHING: "Roughing the passer"}
COURTS = {OFF_HOLDING: "Holding", DEF_HOLDING: "Def. holding", ILLEGAL_CONTACT: "Illegal contact",
          DPI: "Pass interference", OPI: "Off. pass interference", ROUGHING: "Roughing the passer"}
DE_L_ATTAQUE = {OFF_HOLDING, OPI}
YARDS = {OFF_HOLDING: 10, OPI: 10, DEF_HOLDING: 5, ILLEGAL_CONTACT: 5, ROUGHING: 15}
PREMIER_ESSAI = {DEF_HOLDING, ILLEGAL_CONTACT, DPI, ROUGHING}

# probabilité par action (avant les multiplicateurs) — calibrée sur ≈ 8 drapeaux par match (12.2 vicies quater)
TAUX = {OFF_HOLDING: {"course": 0.0265, "passe": 0.021}, DEF_HOLDING: 0.024, ILLEGAL_CONTACT: 0.008, DPI: 0.068,
        OPI: 0.013, ROUGHING: 0.0075}
HOLDING_BATTU = 2.2              # holding offensif sur une passe : × si un duel de protection est perdu
RECEPTION = {DPI: {"contested": 2.6, "traffic": 1.2, "open": 0.25, None: 0.6},
             OPI: {"contested": 2.2, "traffic": 1.0, "open": 0.3, None: 0.5}}
PROFONDEUR = ((15, 1.5), (8, 1.0), (0, 0.45))          # interférences : (route au moins à, ×)
ROUGHING_PRESSION = 5.0          # le QB est atteint au moment du lancer
DISCIPLINE_EQUIPE = 0.82         # identité « discipline » : moins de fautes
GAIN_ESSAI = 4.5                 # gain moyen d'un 1er / 2e essai (points attendus d'un essai)


# ---------------------------------------------------------------- qui commet la faute

def _poids_discipline(d):
    """Discipline 0-100 (attributs des défenseurs, bloc C) -> poids : moins discipliné, plus de fautes."""
    return math.exp((70.0 - (60.0 if d is None else float(d))) / 12.0)


def _choisir(rng, pondere):
    pondere = [(j, w) for j, w in pondere if j is not None and w > 0]
    if not pondere:
        return None
    t = rng.random() * sum(w for _, w in pondere)
    for j, w in pondere:
        t -= w
        if t <= 0:
            return j
    return pondere[-1][0]


def _profondeur(p):
    for seuil, k in PROFONDEUR:
        if (p or 0.0) >= seuil:
            return k
    return PROFONDEUR[-1][1]


def candidats(action):
    """[(type, probabilité, joueurs pondérés [(joueur, poids)])] pour une action de jeu.

    action : {"genre": "run" | "pass", "issue": RUN | PASS_COMPLETE | PASS_INCOMPLETE | SACK | INTERCEPTION | FUMBLE…,
    "td", "safety", "lance" (ballon lancé vers une cible), "reception", "profondeur", "bloqueurs" [{joueur, marge,
    battu}], "couvreurs" [{joueur, discipline}], "couvreur_cible", "cible", "rushers" [joueur], "rusher_gagnant",
    "pression", "k_att", "k_def"} — joueur = {"id", "name", "pos"}.
    """
    out = []
    if action.get("safety"):
        return out
    k_att, k_def = action.get("k_att", 1.0), action.get("k_def", 1.0)
    issue = action.get("issue")
    renverse = issue in ("INTERCEPTION", "FUMBLE")            # la défense ne fait pas annuler un changement de possession
    bl = action.get("bloqueurs") or []
    if action.get("genre") == "run":
        out.append((OFF_HOLDING, TAUX[OFF_HOLDING]["course"] * k_att,
                    [(b["joueur"], math.exp(-b.get("marge", 0.0) / 10.0)) for b in bl]))
        return out
    battu = any(b.get("battu") for b in bl)
    out.append((OFF_HOLDING, TAUX[OFF_HOLDING]["passe"] * k_att * (HOLDING_BATTU if battu else 1.0),
                [(b["joueur"], 4.0 if b.get("battu") else math.exp(-b.get("marge", 0.0) / 8.0)) for b in bl]))
    cv = action.get("couvreurs") or []
    if not renverse:
        out.append((DEF_HOLDING, TAUX[DEF_HOLDING] * k_def,
                    [(c["joueur"], _poids_discipline(c.get("discipline"))) for c in cv]))
        out.append((ILLEGAL_CONTACT, TAUX[ILLEGAL_CONTACT] * k_def,
                    [(c["joueur"], _poids_discipline(c.get("discipline"))) for c in cv
                     if (c["joueur"] or {}).get("pos") in ("CB", "S")]))
    if action.get("lance"):
        rec, prof = action.get("reception"), _profondeur(action.get("profondeur"))
        if not renverse and issue != "PASS_COMPLETE":          # complétée : l'attaque refuserait toujours
            cc = action.get("couvreur_cible")
            jd = [(cc, 1.0)] if cc else [(c["joueur"], _poids_discipline(c.get("discipline"))) for c in cv]
            out.append((DPI, TAUX[DPI] * k_def * RECEPTION[DPI].get(rec, 0.6) * prof, jd))
        out.append((OPI, TAUX[OPI] * k_att * RECEPTION[OPI].get(rec, 0.5) * prof, [(action.get("cible"), 1.0)]))
        if not renverse and not action.get("td"):
            g = action.get("rusher_gagnant")
            jr = [(g, 1.0)] if g else [(r, 1.0) for r in action.get("rushers") or []]
            out.append((ROUGHING, TAUX[ROUGHING] * k_def * (ROUGHING_PRESSION if action.get("pression") else 1.0), jr))
    return out


def tirer(action, rng):
    """Un drapeau au plus : {"type", "joueur", "equipe": "offense" | "defense"} ou None. Un seul tirage décide s'il y a
    faute (la somme des probabilités reste petite), un second qui l'a commise."""
    u = rng.random()
    cumul = 0.0
    for t, p, joueurs in candidats(action):
        cumul += p
        if u < cumul:
            j = _choisir(rng, joueurs)
            if j is None:
                return None
            return {"type": t, "joueur": j, "equipe": "offense" if t in DE_L_ATTAQUE else "defense"}
    return None


# ---------------------------------------------------------------- ce qu'elles coûtent

def _a_gagner(yl, ligne, but):
    return 100 - yl if but else max(1, ligne - yl)


def appliquer(t, yl, down, togo, gain=0, td=False, issue=None, profondeur=None):
    """État après la faute ACCEPTÉE : {"yl", "down", "togo", "yards", "nullified", "auto_first", "replay_down"}.

    yl : ligne de scrimmage (0 = sa ligne de but, 100 = l'en-but adverse) ; gain : yards de l'action.
    yards : yards de la pénalité (moitié de la distance près des en-buts) ; pour la DPI, yards jusqu'à l'endroit de la faute.
    """
    but = togo >= 100 - yl
    ligne = yl + togo
    if t in DE_L_ATTAQUE:
        y = YARDS[t] if YARDS[t] <= yl / 2 else int(yl / 2)
        n = max(1, yl - y)
        return {"yl": n, "down": down, "togo": _a_gagner(n, ligne, but), "yards": yl - n, "nullified": True,
                "auto_first": False, "replay_down": True}
    debout = t == ROUGHING and issue == "PASS_COMPLETE" and not td
    base = yl + gain if debout else yl
    if t == DPI:
        n = min(99, yl + max(1, int(round(profondeur or 1))))
    else:
        reste = 100 - base
        y = YARDS[t] if YARDS[t] <= reste / 2 else int(reste / 2)
        n = min(99, base + y)
    return {"yl": n, "down": 1, "togo": min(10, 100 - n), "yards": n - base, "nullified": not debout,
            "auto_first": True, "replay_down": False}


def sans_faute(yl, down, togo, gain, td=False, issue=None):
    """État si la faute est REFUSÉE : l'action compte. {"kind": "att" | "td" | "adv", …} (vue de l'attaque)."""
    if td:
        return {"kind": "td"}
    if issue in ("INTERCEPTION", "FUMBLE"):
        return {"kind": "adv", "en_but": max(1, min(99, yl + gain))}
    n = max(1, min(99, yl + gain))
    if gain >= togo:
        return {"kind": "att", "yl": n, "down": 1, "togo": min(10, 100 - n)}
    if down >= 4:
        return {"kind": "adv", "en_but": n}
    return {"kind": "att", "yl": n, "down": down + 1, "togo": togo - gain}


# ---------------------------------------------------------------- accepter ou refuser

def _serie(down, togo):
    """Probabilité d'obtenir un premier essai depuis (down, distance) : 3e essai à la distance qui restera."""
    t3 = max(1.0, togo - GAIN_ESSAI * max(0, 3 - down))
    return V.conversion(t3)


def _echec(en_but):
    """Points attendus quand la série échoue : field goal à portée, sinon punt."""
    ko = -V.points_attendus(100 - en_but)
    if en_but <= 35:
        pf = V.probabilite_fg(en_but + 17)
        return pf * (3.0 - V.points_attendus(V.DEPART_APRES_SCORE)) + (1 - pf) * ko
    return -V.points_attendus(V.depart_apres_punt(en_but))


def points_attendus_essai(down, togo, en_but):
    """EP d'un essai quelconque : la table des 1ers essais (valeur.py) corrigée par la série qui reste à convertir."""
    en_but = max(1, min(99, en_but))
    ref = min(10, en_but)
    base = V.points_attendus(en_but)
    if down == 1 and togo == ref:
        return base

    def v(d, t):
        s = _serie(d, t)
        return s * V.points_attendus(max(1, en_but - t - 2)) + (1 - s) * _echec(en_but)
    return base + v(down, togo) - v(1, ref)


def points_etat(etat):
    """Points attendus d'un état (vue de l'attaque d'origine)."""
    if etat["kind"] == "td":
        return V.VALEUR_TD - V.points_attendus(V.DEPART_APRES_SCORE)
    if etat["kind"] == "adv":
        return -V.points_attendus(100 - etat["en_but"])
    return points_attendus_essai(etat["down"], etat["togo"], 100 - etat["yl"])


def wp_etat(etat, ecart, part):
    """Probabilité de victoire de l'attaque dans cet état (écart : attaque − défense ; part : temps qui reste, 0-1)."""
    mu, sd = V._loi(ecart, part, points_etat(etat), 0.0)
    return V._phi(mu / sd)


def arbitrer(action, yl, down, togo, gain, ecart, part, rng, td=False):
    """Le drapeau de l'action, ou None : {"version", "type", "name", "team", "player", "accepted", "declined",
    "chooser", "wp": {"accept", "decline"}, plus, acceptée : "yards", "nullified", "auto_first", "replay_down", "after"}.
    """
    f = tirer(action, rng)
    if f is None:
        return None
    issue = action.get("issue")
    out = {"version": VERSION, "type": f["type"], "name": NOMS[f["type"]], "team": f["equipe"], "player": f["joueur"],
           "chooser": "defense" if f["equipe"] == "offense" else "offense"}
    refus = sans_faute(yl, down, togo, gain, td, issue)
    acc = appliquer(f["type"], yl, down, togo, gain, td, issue, action.get("profondeur"))
    if f["equipe"] == "offense" and issue in ("INTERCEPTION", "FUMBLE"):
        accepter, wa, wr = False, None, None                   # la défense garde le ballon
    else:
        wa = wp_etat({"kind": "att", "yl": acc["yl"], "down": acc["down"], "togo": acc["togo"]}, ecart, part)
        wr = wp_etat(refus, ecart, part)
        accepter = wa > wr + 1e-9 if f["equipe"] == "defense" else wa < wr - 1e-9
    out.update(accepted=accepter, declined=not accepter,
               wp={"accept": None if wa is None else round(wa, 4), "decline": None if wr is None else round(wr, 4)})
    if accepter:
        out.update(yards=acc["yards"], nullified=acc["nullified"], auto_first=acc["auto_first"],
                   replay_down=acc["replay_down"], after={"yl": acc["yl"], "down": acc["down"], "togo": acc["togo"]})
    return out


def annonce(p, numero=None, equipe=None):
    """Annonce de l'arbitre : « Holding, offense, #74, 10 yards, repeat 2nd down » (anglais, comme le site)."""
    qui = "offense" if p["team"] == "offense" else "defense"
    num = f", #{numero}" if numero is not None else ""
    if not p["accepted"]:
        return f"{p['name']}, {qui}{num} — declined"
    if p["type"] == DPI:
        y = "spot foul"
    else:
        y = f"{p['yards']} yard{'s' if p['yards'] != 1 else ''}"
    suite = "repeat the down" if p["replay_down"] else "automatic first down"
    return f"{p['name']}, {qui}{num}, {y}, {suite}"
