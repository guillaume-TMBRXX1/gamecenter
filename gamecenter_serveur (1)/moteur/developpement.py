"""Progression des joueurs (bloc E) : notes de base, actuelle, forme, développement, potentiel ; âge et expérience.

Décisions de Guillaume (05/10/2026, début du bloc E) :
    échelle de temps   une saison = une semaine (18 matchs par équipe) ; une « année » = SEMAINES_PAR_AN = 4 semaines :
                       l'âge augmente d'un an toutes les 4 semaines (plafond, puis régression physique) ;
    portée             les VRAIES notes évoluent (notes du poste -> notes d'unité, OVR et cotes, recalculées depuis le
                       roster) ; l'expérience pèse aussi sur les attributs d'intelligence des blocs B et C ;
    anti-inflation     (1) la moyenne de chaque note, par unité (QB, RB, WR, TE, OL, DL, LB, DB, ST) et sur la ligue,
                       est ramenée chaque semaine sur sa valeur de départ ; (2) chaque joueur est plafonné par son
                       potentiel et par 99 ; (3) garde-fou d'équipe (équilibre 40-60 %) : la FORCE d'une franchise
                       (moyenne de ses 4 notes d'unité) reste à ± FORCE_EQUIPE_MAX = 0,15 point de sa base (décalage
                       commun de ses notes : ses joueurs gardent leurs écarts entre eux) et chaque note d'unité à
                       ± ECART_EQUIPE_MAX = 0,5 (09/10 ; 0,2 et 0,75 au départ) (le moteur est très sensible : ≈ 15 points de % de victoires par point
                       de force — à ± 3 proposés au départ, VEC montait à 72 % et MNL tombait à 24 %) ;
    forme              figée pour toute la semaine : tout se met à jour ENTRE deux semaines (les cotes calculées
                       avant la semaine restent justes).

Pour chaque joueur (dict JSON, persistant d'une semaine à l'autre : week.json -> players_next_week) :
    base         notes d'origine du roster (12.1), entières — la référence de l'anti-inflation ;
    actuelle     notes développées (réelles, à virgule) : croissance vers le potentiel, régression avec l'âge ;
    forme        ± FORME_MAX points sur TOUTES les notes pour la semaine, tirée des performances de la semaine jouée ;
    potentiel    marge (points) au-dessus de la base que la croissance peut atteindre (plus grande chez les jeunes) ;
    dev          rythme de développement (slow · normal · fast · star) ;
    age0         âge au départ (déterministe, hash de l'id) ; âge = age0 + semaines / SEMAINES_PAR_AN ;
    carriere     années d'expérience (avant + jouées) ; apprentissage -> bonus d'intelligence (lecture, décision,
                 reconnaissance) relatif à la ligue (somme nulle : l'expérience d'un joueur se mesure aux autres).
Notes effectives d'une semaine = arrondi(actuelle + forme), bornées 40-99 : ce sont elles que le moteur joue.

Évolution PAR ATTRIBUT, selon sa catégorie : physique (vitesse, accélération, puissance, force, mobilité, bras,
jambe, esquive) — pic tôt (27-29 ans) puis régression rapide ; technique (précision, routes, réception, blocs,
pass rush, couverture, plaquage) — pic plus tard, régression lente ; mental (decision_making) — progresse avec
l'expérience, régresse très tard.

Tout est déterministe : chaque joueur tire dans son propre flux « progression|<semaine>|<id> » (garde-fou 2).
Python pur, aucun import du notebook : on échange des dict simples. Le notebook (12.2 nonies) fournit les stats de
la semaine (season_stats de 14.1) et une fonction de notes d'unité (franchise_unit_ratings) pour le garde-fou (3).
"""
import math
import random

VERSION = 1
SEMAINES_PAR_AN = 4
NOTE_MIN, NOTE_MAX = 40, 99
FORME_MAX = 3.0
ECART_EQUIPE_MAX = 0.5              # écart maximal d'UNE note d'unité d'une franchise à sa base (points)
FORCE_EQUIPE_MAX = 0.15             # écart maximal de sa FORCE (moyenne des 4 unités, décalage commun) ; None : sans
# Mesuré au test d'équilibre (1 008 matchs après 8 à 32 semaines de progression) : ≈ 15 points de % de victoires par
# point de force. À ± 3 par unité (première proposition) : VEC 72 % / MNL 24 % après 8 semaines ; ± 1 : MNL 34-36 % ;
# force ± 0,25 et unités ± 1 : MNL 40,1 % sur une trajectoire. Retenu (05/10) : force ± 0,2, unités ± 0,75.
# 09/10 : à ± 0,2 / 0,75, VEC 39,5-44,7 % après 8 à 52 semaines (la moyenne des unités prédit mal un match : VEC remis à
# sa base gagnait encore 43,8 %, ses adversaires ayant progressé là où VEC est faible). Force ± 0,15, unités ± 0,5 :
# 46-56 % pour les 4 franchises après 8, 16, 32 et 52 semaines.
UNITES_FORCE = ("pass_off", "run_off", "pass_def", "run_def")
HISTORIQUE_MAX = 52                 # points de la courbe gardés par joueur (un par semaine)
UNITES_GARDE = ("pass_off", "run_off", "pass_def", "run_def", "special_teams")

UNITE = {"QB": "QB", "RB": "RB", "WR": "WR", "TE": "TE", "LT": "OL", "LG": "OL", "C": "OL", "RG": "OL",
         "RT": "OL", "EDGE": "DL", "DT": "DL", "LB": "LB", "CB": "DB", "S": "DB", "K": "ST", "P": "ST"}
COTE = {"QB": "off", "RB": "off", "WR": "off", "TE": "off", "OL": "off", "DL": "def", "LB": "def", "DB": "def",
        "ST": "st"}
UNITES_DU_COTE = {"off": ("pass_off", "run_off"), "def": ("pass_def", "run_def"), "st": ("special_teams",)}

PHYSIQUE = frozenset({"speed", "acceleration", "mobility", "throw_power", "power", "strength", "leg_power",
                      "elusiveness"})
MENTAL = frozenset({"decision_making"})


def categorie(attribut):
    return "physique" if attribut in PHYSIQUE else "mental" if attribut in MENTAL else "technique"


# ---- développement (points par AN pour un rythme « normal », temps de jeu plein) ----
CROISSANCE = ((21, 4.0), (23, 3.4), (25, 2.4), (27, 1.2), (29, 0.4), (31, 0.0))       # (âge, points / an)
PIC = {"physique": 29.0, "technique": 31.0, "mental": 34.0}                           # début de la régression
PIC_RB = 27.0                                                                         # les RB s'usent plus tôt
REGRESSION = {"physique": (0.9, 0.7), "technique": (0.5, 0.35), "mental": (0.3, 0.2)}  # pts/an au pic, + par an
MENTAL_EXPERIENCE = 1.0               # décision : + points / an d'expérience (plafond : base + potentiel + 3)
BRUIT_NOTE = 0.30                     # bruit hebdomadaire par note (écart-type, points)
DEV = (("slow", 0.6, 0.25), ("normal", 1.0, 0.50), ("fast", 1.4, 0.20), ("star", 1.8, 0.05))  # rythme, ×, part
DEV_MULT = {n: m for n, m, _ in DEV}

# ---- retraites et recrues (étape 6, décision de Guillaume du 06/10/2026 : « retraite + recrue générée ») ----
#   un joueur part quand il atteint l'âge de la retraite de son poste, ou dès AGE_DECLIN ans si son OVR est tombé de
#   DECLIN_RETRAITE points sous sa base ; une RECRUE prend sa place au roster (même id : la place, pas la personne).
#   Elle garde la base du poste (la référence de l'anti-inflation et du garde-fou d'équipe : le niveau voulu de la
#   franchise), part EN DESSOUS (RECRUE_ECART points selon la catégorie de la note) avec un grand potentiel : la
#   croissance des jeunes la ramène vers la base en quelques « années » ; le garde-fou d'équipe tient la force.
AGE_RETRAITE = {"QB": 38.0, "K": 40.0, "P": 40.0}
AGE_RETRAITE_DEFAUT = 35.0
AGE_DECLIN, DECLIN_RETRAITE = 32.0, 10
RECRUE_AGE = (21.5, 23.5)
RECRUE_ECART = {"physique": (2.0, 5.0), "technique": (4.0, 8.0), "mental": (6.0, 10.0)}
RECRUE_POTENTIEL = (9.0, 13.0)
RECRUE_DEV = (("slow", 0.15), ("normal", 0.45), ("fast", 0.30), ("star", 0.10))

# ---- forme ----
FORME_INERTIE = 0.35                  # part de la forme de la semaine précédente gardée
FORME_PERF = 1.6                      # points de forme pour un écart-type de performance
FORME_BRUIT = 0.5
FORME_BILAN = 1.0                     # effet du bilan de l'équipe (± 0,5 point à 0 % / 100 % de victoires)

# ---- expérience -> intelligence (blocs B et C) ----
IQ_K, IQ_MAX = 0.6, 4.0               # bonus = IQ_K × (apprentissage − moyenne du groupe), borné à ± IQ_MAX
IQ_GROUPE = {"QB": "qb", "WR": "rec", "TE": "rec", "RB": "rec", "CB": "def", "S": "def", "LB": "def"}
IQ_MENTAUX = {
    "qb": ("awareness", "processing", "coverage_reading", "anticipation"),
    "rec": ("route_iq", "coverage_recognition"),
    "def": ("play_recognition", "zone_iq", "man_iq", "awareness", "discipline"),
}


# ------------------------------------------------------------------------------------------------------------------
# identité d'un joueur
# ------------------------------------------------------------------------------------------------------------------
def decoder_id(pid):
    """« CTX_EDGE2 » -> ("CTX", "EDGE", 2) ; id inconnu -> (préfixe, "", 1)."""
    equipe, _, reste = str(pid).partition("_")
    i = len(reste)
    while i > 0 and reste[i - 1].isdigit():
        i -= 1
    return equipe, reste[:i], int(reste[i:] or 1)


def _rng(*parts):
    return random.Random("|".join(str(p) for p in parts))


# étape 6, franchises 21-24 : identité d'âge d'une franchise (années ajoutées à l'âge tiré ; 0 pour les autres, dont les
# tirages restent identiques). SPK : effectif jeune, grand potentiel ; CTD : vétérans, notes hautes, déclin et retraites.
AGE_EQUIPE = {"SPK": -3.5, "CTD": 3.5}


def profil_initial(pid, poste, profondeur=1):
    """Âge, rythme de développement, potentiel et expérience de départ (déterministes, hash de l'id)."""
    rng = _rng("progression-profil", pid)
    if poste == "QB":
        age = rng.uniform(24.0, 33.5)
    elif poste in ("K", "P"):
        age = rng.uniform(24.0, 35.0)
    elif profondeur >= 2 and poste in ("RB", "WR", "LB"):
        age = rng.uniform(21.5, 27.5)
    else:
        age = rng.uniform(22.0, 31.5)
    decal = AGE_EQUIPE.get(decoder_id(pid)[0], 0.0)
    if decal:
        age = min(max(21.0, age + decal), AGE_RETRAITE.get(poste, AGE_RETRAITE_DEFAUT) - 1.0)
    jeune = max(0.0, min(1.0, (29.0 - age) / 7.0))           # 1 à 22 ans, 0 à 29 ans et plus
    u, acc, dev = rng.random(), 0.0, "normal"
    for nom, _, part in DEV:
        p = part * (1.0 + 0.6 * (jeune - 0.5)) if nom in ("fast", "star") else part
        acc += p
        if u < acc:
            dev = nom
            break
    potentiel = round(max(0.0, 10.0 * jeune ** 1.3 + rng.uniform(-1.5, 1.5)), 1)
    carriere = round(max(0.0, age - 21.5 + rng.uniform(-0.5, 0.5)), 2)
    return {"age0": round(age, 2), "dev": dev, "potentiel": potentiel, "carriere": carriere}


# ------------------------------------------------------------------------------------------------------------------
# état
# ------------------------------------------------------------------------------------------------------------------
def etat_initial(joueurs, origine=None):
    """joueurs : [{"id", "name", "pos", "team", "ratings" (notes de base)}] -> état de départ (semaine 0).

    Au départ, actuelle = base et forme = 0 : les notes effectives sont exactement celles du roster (le moteur joue
    comme sans le bloc E)."""
    J = {}
    for j in joueurs:
        pid = j["id"]
        equipe, poste, prof = decoder_id(pid)
        poste = j.get("pos") or poste
        base = {k: int(v) for k, v in (j.get("ratings") or {}).items()}
        J[pid] = dict(profil_initial(pid, poste, prof), name=j.get("name", pid), pos=poste,
                      team=j.get("team") or equipe, base=base, actuelle={k: float(v) for k, v in base.items()},
                      forme=0.0, apprentissage=0.0, bonus_iq=0.0, historique=[])
    return {"version": VERSION, "origine": origine, "semaines": 0, "derniere": None, "joueurs": J}


def completer(etat, joueurs):
    """Ajoute à `etat` (copie) les joueurs du roster qu'il ne connaît pas encore (notes de base, forme 0) et retire ceux
    qui n'y sont plus — ex. étape 6, nouvelles franchises."""
    import copy
    E = copy.deepcopy(etat)
    ids = {j["id"] for j in joueurs}
    neuf = etat_initial([j for j in joueurs if j["id"] not in E["joueurs"]])["joueurs"]
    E["joueurs"] = {pid: j for pid, j in E["joueurs"].items() if pid in ids}
    E["joueurs"].update(neuf)
    return E


def age(j, semaines):
    return j["age0"] + semaines / SEMAINES_PAR_AN


def notes_effectives(j):
    """Notes jouées cette semaine : arrondi(actuelle + forme), bornées 40-99 (entiers, comme le roster)."""
    f = j.get("forme", 0.0)
    return {k: int(max(NOTE_MIN, min(NOTE_MAX, math.floor(v + f + 0.5)))) for k, v in j["actuelle"].items()}


def ovr(notes):
    """Note globale = moyenne des notes (comme la fiche joueur du site)."""
    v = [x for x in (notes or {}).values() if isinstance(x, (int, float))]
    return int(math.floor(sum(v) / len(v) + 0.5)) if v else None


def plafond(j, attribut):
    p = j["base"][attribut] + j["potentiel"] + (3.0 if categorie(attribut) == "mental" else 0.0)
    return min(float(NOTE_MAX), p)


def bonus_intelligence(etat, pid, attribut):
    """Points ajoutés à un attribut d'intelligence (blocs B et C) par l'expérience ; 0 hors attributs mentaux."""
    j = (etat or {}).get("joueurs", {}).get(pid)
    if not j:
        return 0.0
    g = IQ_GROUPE.get(j["pos"])
    return j.get("bonus_iq", 0.0) if g and attribut in IQ_MENTAUX[g] else 0.0


def appliquer_bonus_iq(etat, pid, iq):
    """Copie de `iq` (attributs des blocs B / C) avec le bonus d'expérience sur les attributs mentaux (30-99)."""
    out = dict(iq or {})
    for k in out:
        b = bonus_intelligence(etat, pid, k)
        if b:
            out[k] = int(max(30, min(99, math.floor(out[k] + b + 0.5))))
    return out


def marquer_semaine(etat, index, lundi=None):
    """Ajoute à la courbe de chaque joueur le point de la semaine `index` (idempotent)."""
    for j in etat["joueurs"].values():
        h = j.setdefault("historique", [])
        if h and h[-1].get("week") == index:
            continue
        n = notes_effectives(j)
        h.append({"week": index, "start": lundi, "ovr": ovr(n), "form": round(j.get("forme", 0.0), 1),
                  "age": int(age(j, etat["semaines"]))})
        del h[:-HISTORIQUE_MAX]
    return etat


def resume_joueur(etat, pid):
    """Champ GameFeed roster[].progression (fiche joueur du site)."""
    j = etat["joueurs"].get(pid)
    if not j:
        return None
    n, b = notes_effectives(j), j["base"]
    return {"age": int(age(j, etat["semaines"])), "ovr": ovr(n), "ovr_base": ovr(b),
            "potential": min(NOTE_MAX, int(math.floor(ovr(b) + j["potentiel"] + 0.5))),
            "form": round(j.get("forme", 0.0), 1), "dev": j["dev"], "experience": round(j["carriere"], 1),
            "iq_bonus": round(j.get("bonus_iq", 0.0), 1),
            "base": dict(b), "delta": {k: n[k] - b[k] for k in n},
            "history": [{"week": p["week"], "ovr": p["ovr"], "form": p["form"]} for p in j.get("historique", [])],
            **({"rookie": {"week": j["recrue"]["semaine"], "replaces": j["recrue"]["remplace"]}} if j.get("recrue") else {})}


# ------------------------------------------------------------------------------------------------------------------
# performances de la semaine -> participation et forme
# ------------------------------------------------------------------------------------------------------------------
_GROUPE_PERF = {"QB": "QB", "RB": "RB", "WR": "REC", "TE": "REC", "LT": "OL", "LG": "OL", "C": "OL", "RG": "OL",
                "RT": "OL", "EDGE": "DL", "DT": "DL", "LB": "LB", "CB": "DB", "S": "DB", "K": "K", "P": "P"}


def _brut(pos, s, equipe, matchs):
    """Mesure brute de performance (None = trop peu de volume pour juger)."""
    g = max(1, matchs)
    if pos == "QB":
        a = s.get("pass_att", 0)
        return (s.get("pass_yds", 0) + 20 * s.get("pass_td", 0) - 45 * s.get("ints", 0)) / a if a >= 40 else None
    if pos == "RB":
        t = s.get("rush_att", 0) + s.get("targets", 0)
        return (s.get("rush_yds", 0) + s.get("rec_yds", 0) + 15 * (s.get("rush_td", 0) + s.get("rec_td", 0))) / t \
            if t >= 15 else None
    if pos in ("WR", "TE"):
        t = s.get("targets", 0)
        return (s.get("rec_yds", 0) + 15 * s.get("rec_td", 0)) / t if t >= 8 else None
    if pos in ("EDGE", "DT"):
        return (3 * s.get("sacks", 0) + 0.5 * s.get("tackles", 0) + 3 * s.get("forced_fumbles", 0)) / g
    if pos == "LB":
        return (s.get("tackles", 0) + 3 * s.get("sacks", 0) + 4 * s.get("def_int", 0)
                + 1.5 * s.get("passes_defended", 0) + 3 * s.get("forced_fumbles", 0)) / g
    if pos in ("CB", "S"):
        return (4 * s.get("def_int", 0) + 1.5 * s.get("passes_defended", 0) + 0.5 * s.get("tackles", 0)
                + 3 * s.get("forced_fumbles", 0)) / g
    if pos == "K":
        a = s.get("fg_att", 0)
        return s.get("fg_made", 0) / a if a >= 4 else None
    if pos in ("LT", "LG", "C", "RG", "RT"):          # la ligne : sa course et sa protection (stats d'équipe)
        e = equipe or {}
        ra, drop = e.get("rush_att", 0), e.get("pass_att", 0) + e.get("sacks_taken", 0)
        if ra < 20 or drop < 20:
            return None
        return e.get("rush_yds", 0) / ra - 25.0 * e.get("sacks_taken", 0) / drop
    return None


def performances(etat, stats_joueurs, stats_equipes, bilans=None):
    """{pid: (participation 0-1, performance en écarts-types bornée ± 1,5)} pour la semaine jouée."""
    stats_joueurs, stats_equipes, bilans = stats_joueurs or {}, stats_equipes or {}, bilans or {}
    brut, part = {}, {}
    rb_att = {}
    for pid, j in etat["joueurs"].items():
        if j["pos"] == "RB":
            rb_att[j["team"]] = rb_att.get(j["team"], 0) + (stats_joueurs.get(pid) or {}).get("rush_att", 0)
    for pid, j in etat["joueurs"].items():
        s, e = stats_joueurs.get(pid) or {}, stats_equipes.get(j["team"]) or {}
        matchs = e.get("games", 0)
        if not stats_equipes:                         # pas de stats : titulaires au complet, RB2 en rotation
            part[pid] = 0.3 if (j["pos"] == "RB" and decoder_id(pid)[2] >= 2) else 1.0
        elif matchs <= 0:
            part[pid] = 0.0
        elif j["pos"] == "RB":
            tot = rb_att.get(j["team"], 0)
            part[pid] = min(1.0, 1.6 * s.get("rush_att", 0) / tot) if tot else (1.0 if decoder_id(pid)[2] == 1 else 0.3)
        else:
            part[pid] = 1.0
        brut[pid] = _brut(j["pos"], s, e, matchs) if stats_equipes else None
    z = {}
    groupes = {}
    for pid, v in brut.items():
        if v is not None:
            groupes.setdefault(_GROUPE_PERF.get(etat["joueurs"][pid]["pos"], "?"), []).append(pid)
    for g, ids in groupes.items():
        vals = [brut[p] for p in ids]
        m = sum(vals) / len(vals)
        sd = math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals)) if len(vals) > 1 else 0.0
        for p in ids:
            z[p] = max(-1.5, min(1.5, (brut[p] - m) / sd)) if sd > 1e-9 else 0.0
    out = {}
    for pid, j in etat["joueurs"].items():
        b = bilans.get(j["team"])
        perf = z.get(pid, 0.0) + (FORME_BILAN * (b - 0.5) if b is not None else 0.0)
        out[pid] = (part[pid], max(-1.5, min(1.5, perf)))
    return out


# ------------------------------------------------------------------------------------------------------------------
# développement d'une note (une semaine)
# ------------------------------------------------------------------------------------------------------------------
def _interp(points, x):
    if x <= points[0][0]:
        return points[0][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return points[-1][1]


def croissance_annuelle(a):
    return _interp(CROISSANCE, a)


def regression_annuelle(a, cat, pos=None):
    pic = PIC_RB if (cat == "physique" and pos == "RB") else PIC[cat]
    if a < pic:
        return 0.0
    d0, pente = REGRESSION[cat]
    return d0 + pente * (a - pic)


def delta_note(j, attribut, a, participation, rng):
    """Variation d'une note sur une semaine (points), avant anti-inflation."""
    cat = categorie(attribut)
    v = j["actuelle"][attribut]
    jeu = 0.5 + 0.5 * participation                          # jouer fait progresser
    marge = max(0.0, plafond(j, attribut) - v)
    p = max(1.0, j["potentiel"])
    gain = croissance_annuelle(a) * DEV_MULT.get(j["dev"], 1.0) * jeu * min(1.0, marge / p)
    if cat == "mental":
        gain += MENTAL_EXPERIENCE * participation * min(1.0, marge / 3.0)
    perte = regression_annuelle(a, cat, j["pos"])
    return (gain - perte) / SEMAINES_PAR_AN + rng.gauss(0.0, BRUIT_NOTE)


# ------------------------------------------------------------------------------------------------------------------
# la semaine suivante
# ------------------------------------------------------------------------------------------------------------------
def _borner_actuelle(j):
    for k, v in j["actuelle"].items():
        j["actuelle"][k] = max(float(NOTE_MIN), min(plafond(j, k), min(float(NOTE_MAX), v)))


def groupe_ligue(pid, j):
    """Groupe de l'anti-inflation (1) : l'unité ; les RB titulaires et remplaçants à part (le RB1 porte l'essentiel des
    courses : une moyenne sur les 8 RB laissait monter les yards par course quand les RB1 progressaient)."""
    u = UNITE.get(j["pos"], j["pos"])
    return (u, decoder_id(pid)[2]) if j["pos"] == "RB" else (u, 0)


def _renormaliser(etat):
    """Anti-inflation (1) : moyenne de chaque note, par unité et sur la ligue, ramenée sur la base. Renvoie la
    dérive résiduelle maximale (points) après bornage."""
    groupes = {}
    for pid, j in etat["joueurs"].items():
        g = groupe_ligue(pid, j)
        for k in j["actuelle"]:
            groupes.setdefault(g + (k,), []).append(j)
    for _ in range(4):                       # ramener, borner (plafonds), recommencer : converge en 2-3 passes
        for (u, p, k), js in groupes.items():
            d = sum(j["base"][k] for j in js) / len(js) - sum(j["actuelle"][k] for j in js) / len(js)
            for j in js:
                j["actuelle"][k] += d
        for j in etat["joueurs"].values():
            _borner_actuelle(j)
    return max(abs(sum(j["base"][k] - j["actuelle"][k] for j in js) / len(js)) for (u, p, k), js in groupes.items())


def _recentrer_forme(etat):
    """Forme de moyenne nulle par groupe de la ligue. Recentrer puis borner à ± FORME_MAX, en plusieurs passes : une
    seule passe laissait la moyenne d'un petit groupe (4 à 8 TE ou QB) jusqu'à ± 0,5 point (dérive de la ligue)."""
    par_unite = {}
    for pid, j in etat["joueurs"].items():
        par_unite.setdefault(groupe_ligue(pid, j), []).append(j)
    for js in par_unite.values():
        for _ in range(6):
            m = sum(j["forme"] for j in js) / len(js)
            if abs(m) < 1e-6:
                break
            for j in js:
                j["forme"] = max(-FORME_MAX, min(FORME_MAX, j["forme"] - m))


def ecarts_unites(etat, unites, effectives=True):
    """{équipe: {unité: note effective − note de base}} avec unites(équipe, {pid: notes}) -> {unité: note}."""
    par_equipe = {}
    for pid, j in etat["joueurs"].items():
        par_equipe.setdefault(j["team"], {})[pid] = j
    out = {}
    for t, js in par_equipe.items():
        ue = unites(t, {p: notes_effectives(j) for p, j in js.items()})
        ub = unites(t, {p: dict(j["base"]) for p, j in js.items()})
        out[t] = {u: round(ue[u] - ub[u], 2) for u in UNITES_GARDE if u in ue and u in ub}
    return out


def force(ecarts):
    """Force d'une franchise par rapport à sa base : moyenne des écarts de ses 4 unités (attaque et défense)."""
    v = [ecarts[u] for u in UNITES_FORCE if u in ecarts]
    return sum(v) / len(v) if v else 0.0


def _decaler_force(t, js, ub, unites, force_max):
    """Garde-fou de FORCE : si la moyenne des 4 unités d'une franchise s'écarte de plus de force_max de sa base, toutes
    les notes (actuelles) de ses joueurs d'attaque et de défense sont décalées d'un même nombre de points c, le plus
    petit qui la ramène dans la borne. Les écarts ENTRE ses joueurs (le jeune qui monte, le vétéran qui baisse) sont
    gardés : seule la dérive commune de l'équipe est retirée. Renvoie c (0 si rien à faire)."""
    membres = [j for j in js.values() if COTE.get(UNITE.get(j["pos"], ""), "") in ("off", "def")]
    orig = [(j, dict(j["actuelle"])) for j in membres]

    def f(c):
        for j, a in orig:
            j["actuelle"] = {k: round(v + c, 3) for k, v in a.items()}
            _borner_actuelle(j)
        ue = unites(t, {p: notes_effectives(j) for p, j in js.items()})
        return force({u: ue[u] - ub[u] for u in UNITES_FORCE if u in ue})

    f0 = f(0.0)
    if abs(f0) <= force_max + 1e-9:
        return 0.0
    sens = -1.0 if f0 > 0 else 1.0
    g = lambda m: -sens * f(sens * m)                   # dérive dans son sens d'origine : décroît quand m augmente
    lo, hi = 0.0, abs(f0) - force_max + 2.0
    if g(hi) > force_max + 1e-9:                         # plafonds : il faut aller plus loin
        hi = abs(f0) + 8.0
    for _ in range(30):
        mid = (lo + hi) / 2
        if g(mid) <= force_max + 1e-9:
            hi = mid
        else:
            lo = mid
    f(sens * hi)
    return round(sens * hi, 3)


def _reduire_cote(t, js, ub, unites, cote, us, ecart_max):
    """Borne par UNITÉ : si une unité du côté `cote` s'écarte de plus de ecart_max de sa base, les écarts des joueurs de ce
    côté (développement et forme) sont multipliés par λ < 1, le plus grand qui respecte la borne. Renvoie λ."""
    membres = [j for j in js.values() if COTE.get(UNITE.get(j["pos"], ""), "") == cote]
    if not membres:
        return 1.0
    orig = [(j, dict(j["actuelle"]), j["forme"]) for j in membres]

    def ecart(lam):
        for j, a, f in orig:
            j["actuelle"] = {k: round(j["base"][k] + lam * (a[k] - j["base"][k]), 3) for k in a}
            j["forme"] = round(lam * f, 2)
        ue = unites(t, {p: notes_effectives(j) for p, j in js.items()})
        return max(abs(ue[u] - ub[u]) for u in us if u in ue)

    if ecart(1.0) <= ecart_max + 1e-9:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(24):
        mid = (lo + hi) / 2
        if ecart(mid) <= ecart_max + 1e-9:
            lo = mid
        else:
            hi = mid
    ecart(lo)
    return lo


def _garde_equipe(etat, unites, ecart_max=None, force_max=None):
    """Anti-inflation (3), garde-fou d'équipe : FORCE (moyenne des 4 unités) à ± force_max de sa base par un décalage
    commun des notes de l'équipe (_decaler_force), chaque UNITÉ à ± ecart_max par une réduction des écarts du côté
    concerné (_reduire_cote), en alternance ; si elles ne convergent pas, toute l'équipe est rapprochée de sa base (λ).
    Renvoie {équipe: {"force": décalage, côté: λ, "equipe": λ}} des corrections faites."""
    ecart_max = ECART_EQUIPE_MAX if ecart_max is None else ecart_max
    force_max = FORCE_EQUIPE_MAX if force_max is None else force_max
    fait = {}
    par_equipe = {}
    for pid, j in etat["joueurs"].items():
        par_equipe.setdefault(j["team"], {})[pid] = j
    for t, js in sorted(par_equipe.items()):
        ub = unites(t, {p: dict(j["base"]) for p, j in js.items()})

        def ecarts():
            ue = unites(t, {p: notes_effectives(j) for p, j in js.items()})
            return {u: ue[u] - ub[u] for u in UNITES_GARDE if u in ue}

        def dans_les_bornes():
            d = ecarts()
            return max(abs(v) for v in d.values()) <= ecart_max + 1e-9 and \
                (force_max is None or abs(force(d)) <= force_max + 1e-9)

        for _ in range(4):                           # force (décalage commun) puis unités (λ par côté), en alternance
            if force_max is not None:
                c = _decaler_force(t, js, ub, unites, force_max)
                if c:
                    fait.setdefault(t, {})["force"] = round(fait.get(t, {}).get("force", 0.0) + c, 3)
            for cote, us in UNITES_DU_COTE.items():
                lam = _reduire_cote(t, js, ub, unites, cote, us, ecart_max)
                if lam < 1.0:
                    fait.setdefault(t, {})[cote] = round(min(lam, fait.get(t, {}).get(cote, 1.0)), 3)
            if dans_les_bornes():
                break
        else:                                        # dernier recours : toute l'équipe rapprochée de sa base
            orig = [(j, dict(j["actuelle"]), j["forme"]) for j in js.values()]

            def poser(lam):
                for j, a, f in orig:
                    j["actuelle"] = {k: round(j["base"][k] + lam * (a[k] - j["base"][k]), 3) for k in a}
                    j["forme"] = round(lam * f, 2)
                return dans_les_bornes()

            lo, hi = 0.0, 1.0
            for _ in range(24):
                mid = (lo + hi) / 2
                if poser(mid):
                    lo = mid
                else:
                    hi = mid
            poser(lo)
            fait.setdefault(t, {})["equipe"] = round(lo, 3)
    return fait


def doit_partir(j, semaines):
    """Retraite : âge du poste atteint, ou déclin marqué (OVR à DECLIN_RETRAITE points sous sa base) après AGE_DECLIN."""
    a = age(j, semaines)
    if a >= AGE_RETRAITE.get(j["pos"], AGE_RETRAITE_DEFAUT):
        return True
    return a >= AGE_DECLIN and ovr(j["base"]) - ovr(notes_effectives(j)) >= DECLIN_RETRAITE


def recrue(j, pid, semaines, cle, noms, pris=()):
    """Recrue qui remplace `j` à la même place (id) : nom, âge, rythme et potentiel tirés dans le flux
    « recrue|<semaine>|<id> » ; base du poste gardée, notes actuelles en dessous (RECRUE_ECART)."""
    rng = _rng("recrue", cle, pid)
    prenoms, familles = noms
    nom = None
    for _ in range(200):
        nom = f"{rng.choice(prenoms)} {rng.choice(familles)}"
        if nom not in pris:
            break
    a = rng.uniform(*RECRUE_AGE)
    u, acc, dev = rng.random(), 0.0, "normal"
    for nm, part in RECRUE_DEV:
        acc += part
        if u < acc:
            dev = nm
            break
    actuelle = {k: max(float(NOTE_MIN), round(v - rng.uniform(*RECRUE_ECART[categorie(k)]), 3))
                for k, v in sorted(j["base"].items())}
    return dict(age0=round(a - semaines / SEMAINES_PAR_AN, 2), dev=dev,
                potentiel=round(rng.uniform(*RECRUE_POTENTIEL), 1), carriere=0.0, name=nom, pos=j["pos"],
                team=j["team"], base=dict(j["base"]), actuelle=actuelle, forme=0.0, apprentissage=0.0, bonus_iq=0.0,
                historique=[], recrue={"semaine": cle, "remplace": j["name"]})


def retraites(etat, cle, noms):
    """Remplace (en place) les joueurs qui partent par une recrue ; renvoie les mouvements (week.json)."""
    mouv = []
    for pid in sorted(etat["joueurs"]):
        j = etat["joueurs"][pid]
        if not doit_partir(j, etat["semaines"]):
            continue
        pris = {x["name"] for x in etat["joueurs"].values() if x["team"] == j["team"]}
        r = recrue(j, pid, etat["semaines"], cle, noms, pris)
        mouv.append({"id": pid, "team": j["team"], "pos": j["pos"], "retired": j["name"],
                     "age": int(age(j, etat["semaines"])), "ovr": ovr(notes_effectives(j)), "rookie": r["name"],
                     "rookie_age": int(age(r, etat["semaines"])), "rookie_ovr": ovr(notes_effectives(r))})
        etat["joueurs"][pid] = r
    return mouv


def semaine_suivante(etat, stats_joueurs=None, stats_equipes=None, unites=None, index=None, bilans=None,
                     lundi_suivant=None, recrues=None):
    """État au début de la semaine suivante, d'après la semaine jouée. Ne modifie pas `etat`.

    stats_joueurs : {pid: ligne de season_stats} · stats_equipes : {équipe: ligne d'équipe} · bilans : {équipe: % de
    victoires} · unites(équipe, {pid: notes}) -> notes d'unité (garde-fou d'équipe ; None : pas de garde) ·
    index : n° de la semaine jouée (clé du flux aléatoire) · recrues : (prénoms, noms) pour nommer les recrues
    (étape 6 ; None : pas de retraites, comportement du bloc E). Renvoie (nouvel_etat, rapport)."""
    import copy
    E = copy.deepcopy(etat)
    cle = index if index is not None else E["semaines"] + 1
    perf = performances(E, stats_joueurs, stats_equipes, bilans)
    avant = {pid: ovr(notes_effectives(j)) for pid, j in E["joueurs"].items()}
    for pid in sorted(E["joueurs"]):
        j = E["joueurs"][pid]
        rng = _rng("progression", cle, pid)
        participation, z = perf[pid]
        a = age(j, E["semaines"]) + 0.5 / SEMAINES_PAR_AN       # milieu de la semaine écoulée
        for k in sorted(j["actuelle"]):
            j["actuelle"][k] += delta_note(j, k, a, participation, rng)
        j["forme"] = max(-FORME_MAX, min(FORME_MAX, FORME_INERTIE * j["forme"] + FORME_PERF * z
                                         + rng.gauss(0.0, FORME_BRUIT)))
        j["apprentissage"] = j.get("apprentissage", 0.0) + participation / (1.0 + j["carriere"] / 3.0)
        j["carriere"] = round(j["carriere"] + participation / SEMAINES_PAR_AN, 3)
        _borner_actuelle(j)
    E["semaines"] += 1
    E["derniere"] = cle
    mouvements = retraites(E, cle, recrues) if recrues else []
    derive = _renormaliser(E)
    _recentrer_forme(E)
    # expérience -> intelligence : relative au groupe (somme nulle)
    grp = {}
    for pid, j in E["joueurs"].items():
        g = IQ_GROUPE.get(j["pos"])
        if g:
            grp.setdefault(g, []).append(j)
    for js in grp.values():
        m = sum(j["apprentissage"] for j in js) / len(js)
        for j in js:
            j["bonus_iq"] = round(max(-IQ_MAX, min(IQ_MAX, IQ_K * (j["apprentissage"] - m))), 2)
    for j in E["joueurs"].values():                # arrondi AVANT le garde-fou : il contrôle les notes enregistrées
        j["actuelle"] = {k: round(v, 3) for k, v in j["actuelle"].items()}
        j["forme"] = round(j["forme"], 2)
    garde = {}
    if unites:                                       # ligue (1-2) et équipe (3) : projections alternées, garde en dernier
        for _ in range(3):
            garde = _garde_equipe(E, unites)
            if not garde:
                break
            derive = _renormaliser(E)
            _recentrer_forme(E)                      # le garde-fou réduit aussi la forme (λ) : moyenne de la ligue à 0
            for j in E["joueurs"].values():
                j["actuelle"] = {k: round(v, 3) for k, v in j["actuelle"].items()}
                j["forme"] = round(j["forme"], 2)
        garde = _garde_equipe(E, unites) or garde
    rapport = rapport_semaine(E, avant, unites, garde, derive)
    rapport["semaine_jouee"] = cle
    if recrues:
        rapport["retirements"] = mouvements
    if lundi_suivant:
        rapport["pour_la_semaine"] = lundi_suivant
    return E, rapport


def rapport_semaine(etat, avant=None, unites=None, garde=None, derive=None):
    """Mesures de l'anti-inflation et mouvements de la semaine (pour week.json -> progression)."""
    J = etat["joueurs"]
    moy = {}
    for j in J.values():
        u = UNITE.get(j["pos"], j["pos"])
        n = notes_effectives(j)
        for k in n:
            m = moy.setdefault(u, [0.0, 0.0, 0])
            m[0] += n[k]; m[1] += j["base"][k]; m[2] += 1
    ligue = {u: round((m[0] - m[1]) / m[2], 2) for u, m in sorted(moy.items())}
    mouv = []
    if avant:
        for pid, j in J.items():
            o = ovr(notes_effectives(j))
            if avant.get(pid) is not None and o is not None and (j.get("recrue") or {}).get("semaine") != etat.get("derniere"):
                mouv.append((o - avant[pid], pid))
    mouv.sort(key=lambda x: (-x[0], x[1]))
    fmt = lambda d, pid: {"id": pid, "name": J[pid]["name"], "team": J[pid]["team"], "pos": J[pid]["pos"],
                          "age": int(age(J[pid], etat["semaines"])), "ovr": ovr(notes_effectives(J[pid])),
                          "change": d, "form": round(J[pid]["forme"], 1)}
    return {"weeks": etat["semaines"], "league_drift": ligue,
            "league_drift_max": round(max(abs(v) for v in ligue.values()), 2) if ligue else 0.0,
            "renorm_residual": round(derive, 3) if derive is not None else None,
            "team_units": ecarts_unites(etat, unites) if unites else None,
            "team_strength": {t: round(force(u), 2) for t, u in ecarts_unites(etat, unites).items()} if unites else None,
            "team_guard": garde or {},
            "risers": [fmt(d, p) for d, p in mouv[:5] if d > 0],
            "fallers": [fmt(d, p) for d, p in reversed(mouv[-5:]) if d < 0]}


def controler(etat, unites=None, ecart_max=None):
    """Contrôles d'un état (liste vide = OK) : bornes, plafonds, forme, garde d'équipe, dérive de la ligue."""
    ecart_max = ECART_EQUIPE_MAX if ecart_max is None else ecart_max
    pb = []
    for pid, j in etat.get("joueurs", {}).items():
        for k, v in notes_effectives(j).items():
            if not NOTE_MIN <= v <= NOTE_MAX:
                pb.append(f"{pid} {k} = {v} hors {NOTE_MIN}-{NOTE_MAX}")
        for k, v in j["actuelle"].items():
            if v > plafond(j, k) + 1e-6:
                pb.append(f"{pid} {k} = {v:.2f} au-dessus de son potentiel ({plafond(j, k):.1f})")
        if abs(j.get("forme", 0.0)) > FORME_MAX + 1e-9:
            pb.append(f"{pid} forme {j['forme']} hors ± {FORME_MAX}")
    if unites:
        for t, us in ecarts_unites(etat, unites).items():
            for u, d in us.items():
                if abs(d) > ecart_max + 1e-6:
                    pb.append(f"{t} {u} à {d:+.2f} de sa base (± {ecart_max} au plus)")
            fm = FORCE_EQUIPE_MAX
            if fm is not None and abs(force(us)) > fm + 1e-6:
                pb.append(f"{t} force à {force(us):+.2f} de sa base (± {fm} au plus)")
    r = rapport_semaine(etat)
    if r["league_drift_max"] > 1.0:
        pb.append(f"dérive de la ligue {r['league_drift']} (± 1 au plus)")
    return pb
