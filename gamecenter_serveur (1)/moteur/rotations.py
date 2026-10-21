"""Le banc, les packages, la fatigue et les rotations (étape 7.3 de la feuille de route « moteur plus intelligent »,
21/10/2026).

Avant : 25 joueurs par franchise (QB, 2 RB, 3 WR, TE, 5 OL, 2 EDGE, 2 DT, 3 LB, 2 CB, 2 S, K, P) ; personne ne sortait
jamais ; seule fatigue : le plafond de « touches » du porteur (≤ 3 yards, inchangé). En nickel ou en dime il n'y avait
pas toujours de 3e CB, en 12 personnel pas de 2e TE.

7.3.1 — LE BANC (plan validé par Guillaume le 21/10) : 11 remplaçants par franchise (36 joueurs) — QB2, RB3, WR4, TE2,
un OT et un OG remplaçants, EDGE3, DT3, LB4, CB3, S3. Niveau ≈ 7 points sous le titulaire (3 à 12), trois profils :
  VÉTÉRAN      solide, sans marge (29-33 ans, potentiel ≈ 0) ;
  JEUNE        à potentiel, plus loin du titulaire, progresse avec ses snaps (bloc E : 21-24 ans, potentiel 8-12) ;
  SPÉCIALISTE  un profil, pas un niveau : proche du titulaire sur sa spécialité (CB de slot, EDGE de pass rush…), plus
               loin ailleurs.
Noms tirés des réservoirs des recrues de l'étape 6 (12.1) : aucun nom complet déjà porté dans la ligue (retraités
compris), ni deux fois parmi les nouveaux (les doublons existants restent). Ids : <équipe>_<poste><n> (CTX_QB2,
CTX_RT2 pour l'OT, CTX_LG2 pour l'OG…). Les notes d'unité (cotes, appels) restent calculées sur les titulaires.

Déterministe : tout vient du flux dédié « rotations » (chaînes de graine fixes) ; le hasard du moteur n'est pas consommé.
"""
import random

VERSION = "rotations-1"
FLUX = "rotations"

VETERAN, JEUNE, SPECIALISTE = "veteran", "prospect", "specialist"
PROFILS = (VETERAN, JEUNE, SPECIALISTE)

# remplaçant : (poste au roster, n° de l'id, postes qu'il couvre, libellé du tableau de profondeur)
BANC = (
    ("QB", 2, ("QB",), "QB2"),
    ("RB", 3, ("RB",), "RB3"),
    ("WR", 4, ("WR",), "WR4"),
    ("TE", 2, ("TE",), "TE2"),
    ("RT", 2, ("LT", "RT"), "OT"),
    ("LG", 2, ("LG", "RG", "C"), "OG"),
    ("EDGE", 3, ("EDGE",), "EDGE3"),
    ("DT", 3, ("DT",), "DT3"),
    ("LB", 4, ("LB",), "LB4"),
    ("CB", 3, ("CB",), "CB3"),
    ("S", 3, ("S",), "S3"),
)
TAILLE_BANC = len(BANC)
NUMERO = {b[0]: b[1] for b in BANC}           # poste du remplaçant -> n° de son id

# mélange de profils d'un banc (11 places) ; identité d'âge des franchises (bloc E, AGE_EQUIPE) : SPK jeune, CTD vétérane
MELANGE = {None: {VETERAN: 4, JEUNE: 4, SPECIALISTE: 3},
           "SPK": {VETERAN: 2, JEUNE: 6, SPECIALISTE: 3},
           "CTD": {VETERAN: 6, JEUNE: 2, SPECIALISTE: 3}}

# spécialité d'un spécialiste : (nom affiché, notes proches du titulaire)
SPECIALITES = {
    "QB": ("mobile QB", ("mobility",)),
    "RB": ("third-down back", ("speed", "elusiveness")),
    "WR": ("deep threat", ("speed", "acceleration")),
    "TE": ("blocking tight end", ("run_block",)),
    "RT": ("swing tackle", ("pass_block",)),
    "LG": ("road grader", ("run_block", "strength")),
    "EDGE": ("pass rush specialist", ("pass_rush",)),
    "DT": ("run stuffer", ("strength", "tackling")),
    "LB": ("coverage linebacker", ("coverage", "speed")),
    "CB": ("slot corner", ("coverage", "acceleration")),
    "S": ("box safety", ("run_support", "tackling")),
}

# écart au titulaire (points, par note) : (bas, haut) du décalage commun, puis bruit par note
ECART = {VETERAN: (-6.5, -4.0), JEUNE: (-12.0, -8.5)}
ECART_SPECIALITE = (-3.0, -0.5)               # spécialiste : sur sa spécialité
ECART_AUTRES = (-11.5, -8.0)                  # spécialiste : ailleurs
BRUIT = 1.5
ECART_OVR = (-12.0, -3.0)                     # écart moyen au titulaire, borné (≈ −7 en moyenne)
# la rotation de la ligne défensive : DT3 et EDGE3 jouent un tiers à la moitié des snaps (≈ 65 % et 50 %), ils sont
# plus proches de leurs titulaires ; les autres remplaçants, qui jouent peu, un peu plus loin (moyenne du banc ≈ −7)
ECART_POSTE = {"DT": 3.0, "EDGE": 3.0}
ECART_AUTRES_POSTES = -0.6
PHYSIQUE = frozenset({"speed", "acceleration", "mobility", "throw_power", "power", "strength", "elusiveness"})
NOTE_MIN, NOTE_MAX = 40, 99

# âge, rythme de développement et potentiel (bloc E) par profil
AGE = {VETERAN: (29.5, 32.5), JEUNE: (21.5, 24.0), SPECIALISTE: (25.0, 29.0)}
AGE_QB_VETERAN = (31.0, 35.0)
DEV = {VETERAN: (("slow", 0.5), ("normal", 0.5)),
       JEUNE: (("normal", 0.35), ("fast", 0.45), ("star", 0.20)),
       SPECIALISTE: (("slow", 0.2), ("normal", 0.7), ("fast", 0.1))}
POTENTIEL = {VETERAN: (0.0, 1.0), JEUNE: (8.0, 12.0), SPECIALISTE: (2.0, 5.0)}


def _rng(*parts):
    return random.Random("|".join([FLUX] + [str(p) for p in parts]))


def pid(equipe, poste, n):
    return f"{equipe}_{poste}{n}"


def profils(equipe):
    """{poste du banc: profil} pour une franchise (mélange de MELANGE, ordre tiré dans le flux, déterministe)."""
    m = MELANGE.get(equipe, MELANGE[None])
    sac = [p for p in PROFILS for _ in range(m[p])]
    _rng("profils", equipe).shuffle(sac)
    return {b[0]: p for b, p in zip(BANC, sac)}


def reference(titulaires, couvre):
    """Notes du titulaire de référence : le premier du poste ; plusieurs postes (OT, OG) : moyenne de leurs titulaires.
    titulaires : {poste: [notes du 1er, du 2e…]} (ordre du roster)."""
    rs = [titulaires[p][0] for p in couvre if titulaires.get(p)]
    if not rs:
        return {}
    return {k: sum(r[k] for r in rs) / len(rs) for k in rs[0]}


def notes(equipe, poste, profil, ref):
    """Notes du remplaçant d'après celles du titulaire de référence (entiers 40-99)."""
    rng = _rng("notes", pid(equipe, poste, NUMERO[poste]))
    spe = SPECIALITES[poste][1] if profil == SPECIALISTE else ()
    commun = rng.uniform(*ECART[profil]) if profil in ECART else 0.0
    d = {}
    for k in sorted(ref):
        if profil == SPECIALISTE:
            e = rng.uniform(*(ECART_SPECIALITE if k in spe else ECART_AUTRES))
        else:
            e = commun + rng.uniform(-BRUIT, BRUIT)
            if profil == VETERAN:
                e += 2.0 if k == "decision_making" else (-1.0 if k in PHYSIQUE else 0.0)
            elif profil == JEUNE:
                e += 1.5 if k in PHYSIQUE else -1.0
        d[k] = e
    dp = ECART_POSTE.get(poste, ECART_AUTRES_POSTES)
    d = {k: v + dp for k, v in d.items()}
    m = sum(d.values()) / len(d) if d else 0.0
    cale = min(ECART_OVR[1], max(ECART_OVR[0], m)) - m          # écart moyen borné à −12 / −3
    return {k: int(max(NOTE_MIN, min(NOTE_MAX, round(ref[k] + d[k] + cale)))) for k in sorted(ref)}


def profil_developpement(equipe, poste, profil):
    """Âge, rythme, potentiel et expérience de départ (bloc E) du remplaçant."""
    rng = _rng("developpement", pid(equipe, poste, NUMERO[poste]))
    lo, hi = AGE_QB_VETERAN if (poste == "QB" and profil == VETERAN) else AGE[profil]
    age = rng.uniform(lo, hi)
    u, acc, dev = rng.random(), 0.0, "normal"
    for nom, part in DEV[profil]:
        acc += part
        if u < acc:
            dev = nom
            break
    return {"age0": round(age, 2), "dev": dev, "potentiel": round(rng.uniform(*POTENTIEL[profil]), 1),
            "carriere": round(max(0.0, age - 21.5 + rng.uniform(-0.5, 0.5)), 2)}


def construire_banc(equipe, titulaires, gabarit):
    """Les 11 remplaçants d'une franchise (sans nom : voir noms()).

    titulaires : {poste: [notes…]} des titulaires (ordre du roster) · gabarit : {poste: [clés des notes]} (12.1).
    Renvoie [{"id", "pos", "depth": 2, "slot", "covers", "profile", "specialty", "ratings", "dev"}] dans l'ordre de
    BANC (ordre fixe : il donne les numéros de maillot)."""
    pr = profils(equipe)
    out = []
    for poste, n, couvre, slot in BANC:
        ref = reference(titulaires, couvre)
        ref = {k: ref.get(k, 60.0) for k in gabarit[poste]}
        p = pr[poste]
        out.append({"id": pid(equipe, poste, n), "pos": poste, "depth": 2, "slot": slot, "covers": list(couvre),
                    "profile": p, "specialty": SPECIALITES[poste][0] if p == SPECIALISTE else None,
                    "ratings": notes(equipe, poste, p, ref), "dev": profil_developpement(equipe, poste, p)})
    return out


def noms(ids, prenoms, familles, pris):
    """{id: « Prénom Nom »} pour les remplaçants `ids` (dans cet ordre) : jamais un nom de `pris` (tous les noms déjà
    portés dans la ligue, retraités compris), jamais deux fois. Tirage déterministe par id ; ValueError si le réservoir
    est épuisé."""
    pris = set(pris)
    out = {}
    libres = sorted({f"{a} {b}" for a in prenoms for b in familles} - pris)
    for i in ids:
        rng = _rng("nom", i)
        nom = None
        for _ in range(400):
            c = f"{rng.choice(prenoms)} {rng.choice(familles)}"
            if c not in pris:
                nom = c
                break
        if nom is None:                                     # réservoir presque plein : le premier libre, dans l'ordre
            libres = [x for x in libres if x not in pris]
            if not libres:
                raise ValueError("réservoir de noms épuisé")
            nom = libres[rng.randrange(len(libres))]
        out[i] = nom
        pris.add(nom)
    return out


def ecart_ovr(remplacant, ref):
    """Écart moyen (points) du remplaçant à son titulaire de référence."""
    ks = [k for k in remplacant if k in ref]
    return sum(remplacant[k] - ref[k] for k in ks) / len(ks) if ks else 0.0


def controler_banc(equipe, banc, titulaires=None):
    """Contrôles d'un banc (liste vide = OK) : 11 places, postes et ids attendus, profils, notes bornées, écart au
    titulaire dans ECART_OVR (avec `titulaires`)."""
    pb = []
    if len(banc) != TAILLE_BANC:
        pb.append(f"{equipe} : {len(banc)} remplaçants (attendu {TAILLE_BANC})")
    for (poste, n, couvre, slot), b in zip(BANC, banc):
        if b["id"] != pid(equipe, poste, n) or b["pos"] != poste:
            pb.append(f"{equipe} : {b['id']} ({b['pos']}) à la place de {pid(equipe, poste, n)}")
        if b.get("profile") not in PROFILS:
            pb.append(f"{b['id']} : profil {b.get('profile')}")
        if any(not NOTE_MIN <= v <= NOTE_MAX for v in b["ratings"].values()):
            pb.append(f"{b['id']} : note hors {NOTE_MIN}-{NOTE_MAX}")
        if titulaires is not None:
            e = ecart_ovr(b["ratings"], reference(titulaires, couvre))
            if not ECART_OVR[0] - 0.75 <= e <= ECART_OVR[1] + 0.75:      # arrondi des notes, bornes 40-99
                pb.append(f"{b['id']} : {e:+.1f} sous son titulaire (attendu {ECART_OVR[0]:g} à {ECART_OVR[1]:g})")
    return pb


# =====================================================================================================================
# 7.3.2 — LES PACKAGES : le personnel de l'appel fait entrer les joueurs
# 7.3.3 — FATIGUE ET ROTATIONS
# =====================================================================================================================
# Alignement d'une action : 11 places par unité, dans l'ordre du site (OFF_SLOT / DEF_SLOT) ; chaque place a son
# titulaire (le 1er du poste, le 2e…), un remplaçant peut la prendre (rotation, garbage time) et un package la donne à
# un autre poste (2e TE à la place du WR3 en 12 personnel, CB3 à la place du LB3 en nickel…).
PLACES = {"off": ("LT", "LG", "C", "RG", "RT", "QB", "RB", "TE", "WR1", "WR2", "WR3"),
          "def": ("EDGE1", "EDGE2", "DT1", "DT2", "LB1", "LB2", "LB3", "CB1", "CB2", "S1", "S2")}
POSTE_PLACE = {"LT": ("LT", 1), "LG": ("LG", 1), "C": ("C", 1), "RG": ("RG", 1), "RT": ("RT", 1), "QB": ("QB", 1),
               "RB": ("RB", 1), "TE": ("TE", 1), "WR1": ("WR", 1), "WR2": ("WR", 2), "WR3": ("WR", 3),
               "EDGE1": ("EDGE", 1), "EDGE2": ("EDGE", 2), "DT1": ("DT", 1), "DT2": ("DT", 2), "LB1": ("LB", 1),
               "LB2": ("LB", 2), "LB3": ("LB", 3), "CB1": ("CB", 1), "CB2": ("CB", 2), "S1": ("S", 1), "S2": ("S", 2)}
COTE_POSTE = {p: "off" for p in ("QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT")}
COTE_POSTE.update({p: "def" for p in ("EDGE", "DT", "LB", "CB", "S")})

# packages : (place, poste qui la prend). Attaque : selon le personnel de la formation (moteur.playbook_expansion) et
# quelques formations dont le site nomme les places (I-form : fullback, HEAVY : 6e OL…) ; défense : selon le paquet.
PERSONNEL_PACKAGE = {"11": (), "12": (("WR3", "TE"),), "13": (("WR3", "TE"), ("WR2", "TE")),
                     "21": (("WR3", "RB"),), "22": (("WR3", "RB"), ("WR2", "TE")), "10": (("TE", "WR"),)}
FORMATION_PACKAGE = {"EMPTY": (("RB", "WR"),), "HEAVY": (("WR1", "OL"), ("WR3", "RB")),
                     "JUMBO": (("WR1", "TE"), ("WR3", "RB"))}
DEFENSE_PACKAGE = {"NICKEL": (("LB3", "CB"),), "DIME": (("LB3", "CB"), ("LB2", "S")), "GOAL_LINE": (("CB2", "LB"),)}

# énergie (0-100) : ce qu'un snap coûte selon le poste (les DL et les RB plus que les OL et le QB), × LONGUE sur une
# longue action, × HURRY_UP pour la défense face à une attaque sans huddle ; ce qu'un snap hors du terrain rend (banc,
# touche), la mi-temps ; le malus d'un joueur fatigué (points sur ses notes de duel : un profil, pas un niveau)
COUT = {"QB": 0.7, "RB": 3.1, "WR": 1.9, "TE": 2.1, "LT": 1.6, "LG": 1.6, "C": 1.6, "RG": 1.6, "RT": 1.6,
        "EDGE": 3.0, "DT": 3.5, "LB": 2.1, "CB": 1.9, "S": 1.7}
LONGUE = (15, 1.6)                     # action d'au moins 15 yards (ou 7 s) : coût × 1,6
LONGUE_SECONDES = 7
HURRY_UP = 1.3                         # défense face à une attaque sans huddle : coût × 1,3, pas de rotation pendant le drive
TEMPO_IDENTITE = {"PLS"}               # identité « fatigue de la défense » (tempo, no-huddle — « Speed »)
RECUP_SNAP = 1.5                       # par snap passé hors du terrain (banc ou touche)
RECUP_MI_TEMPS = 35.0
REFERENCE = 85.0                       # énergie sans effet ; au-dessus, un joueur frais gagne un peu ; en dessous, il perd
PENTE = 0.10                           # points de note par point d'énergie d'écart à REFERENCE
MALUS_MAX = 5.0                        # perte au plus (énergie ≤ 35)
BONUS_MAX = 1.5                        # gain au plus (énergie 100)
SANS_MALUS = frozenset({"decision_making", "throw_accuracy", "accuracy", "leg_power"})

# rotations du coordinateur : part des snaps visée par les titulaires (DT ≈ 65-70 %, EDGE ≈ 75 %, RB1 ≈ 60-65 % ;
# OL, QB et les autres : 100 % hors garbage time), modulée par l'identité de la franchise
ROTATION = {"DT": (("DT1", "DT2"), 0.675), "EDGE": (("EDGE1", "EDGE2"), 0.75), "RB": (("RB",), 0.625)}
STYLE_ROTATION = {   # franchise -> {groupe: part visée} (les autres : ROTATION)
    "FRG": {"DT": 0.72, "EDGE": 0.79},             # « Dominate » : ses lignes restent sur le terrain
    "MNL": {"DT": 0.71, "RB": 0.60},               # physique : RB2 en rotation (rb2_share 0,4)
    "GLT": {"DT": 0.64, "EDGE": 0.71},             # « Disrupt » : rotation large, des rushers frais
    "ONX": {"EDGE": 0.72}, "GRZ": {"DT": 0.70},
    "CTD": {"DT": 0.70, "EDGE": 0.78, "RB": 0.66},  # vétérans
    "SPK": {"DT": 0.64, "EDGE": 0.72, "RB": 0.60},  # jeunes : on fait jouer le banc
    "PLS": {"RB": 0.60}, "TDL": {"RB": 0.60},
}
QUOTA = 3.0                            # points d'énergie par snap de retard sur la part visée
RESTE = 8.0                            # préférence pour le joueur déjà sur le terrain (pas de va-et-vient)
BRUIT_ROTATION = 2.0
TROISIEME = 15.0                       # pénalité du 2e remplaçant d'un groupe (RB3)
# garbage time : probabilité de victoire > 98 % au 4e quart-temps -> les remplaçants entrent (QB2 compris)
GARBAGE_WP = 0.98
GARBAGE_SORTIE = 0.95                  # on n'en sort que si le match redevient serré
GARBAGE_ECART = 17                     # trois possessions
GARBAGE_FIN = 8.0 / 15.0               # les 8 dernières minutes du 4e quart-temps (part du quart qui reste)
GARBAGE = (("QB", "QB"), ("RB", "RB"), ("WR1", "WR"), ("TE", "TE"), ("LT", "OL"), ("LG", "OL"), ("EDGE1", "EDGE"),
           ("DT1", "DT"), ("LB1", "LB"), ("CB1", "CB"), ("S1", "S"))
OL = ("LT", "LG", "C", "RG", "RT")


# calibration (garde-fou 3) : la rotation met des remplaçants sur le terrain, surtout en défense (DT3, EDGE3, CB3 :
# un tiers à la moitié des snaps) et répartit les courses (moins de « touches » par RB) ; sans correction, la ligue
# marquait ≈ 2,4 points de plus. Points ajoutés aux notes d'unité défensives jouées (pas à celles du roster, ni aux
# cotes : elles sont calculées ensuite sur le moteur allumé).
CALIBRATION = {"pass_def": 1.2, "run_def": 2.0}


def _famille(poste):
    return "OL" if poste in OL else poste


def profondeur(joueurs):
    """{poste: [ids]} dans l'ordre du roster (titulaires puis remplaçants). joueurs : [{"id", "pos"}]."""
    out = {}
    for j in joueurs:
        out.setdefault(j["pos"], []).append(j["id"])
    return out


def part_visee(equipe, groupe):
    return STYLE_ROTATION.get(equipe, {}).get(groupe, ROTATION[groupe][1])


def malus(energie):
    """Points retirés aux notes de duel (négatif : gagnés) selon l'énergie : PENTE × (REFERENCE − énergie), borné à
    −BONUS_MAX … MALUS_MAX. Un profil, pas un niveau : quelques points, dans un sens ou dans l'autre."""
    return max(-BONUS_MAX, min(MALUS_MAX, PENTE * (REFERENCE - energie)))


def notes_fatiguees(notes, energie):
    """Notes jouées selon l'énergie (entiers 40-99) ; les notes mentales et de botté ne bougent pas."""
    m = malus(energie)
    if abs(m) < 0.5:
        return dict(notes)
    return {k: (v if k in SANS_MALUS else max(NOTE_MIN, min(NOTE_MAX, int(round(v - m))))) for k, v in notes.items()}


def cout_snap(poste, gain=0, secondes=0, hurry=False):
    c = COUT.get(poste, 1.5)
    if abs(gain or 0) >= LONGUE[0] or (secondes or 0) >= LONGUE_SECONDES:
        c *= LONGUE[1]
    return c * (HURRY_UP if hurry else 1.0)


class Rotations:
    """Les rotations d'une équipe pendant un match : énergie, snaps, alignement de chaque unité, garbage time."""

    def __init__(self, equipe, joueurs):
        self.equipe = equipe
        self.pos = {j["id"]: j["pos"] for j in joueurs}
        self.prof = profondeur(joueurs)
        self.energie = {j["id"]: 100.0 for j in joueurs}
        self.snaps = {j["id"]: 0 for j in joueurs}
        self.n = {"off": 0, "def": 0}
        self.base = {c: {pl: self._titulaire(pl) for pl in PLACES[c]} for c in PLACES}
        self.dernier = {c: dict(self.base[c]) for c in PLACES}
        self.paquet = {c: set() for c in PLACES}
        self.garbage = False

    def _titulaire(self, place):
        poste, rang = POSTE_PLACE[place]
        ids = self.prof.get(poste) or []
        return ids[rang - 1] if len(ids) >= rang else None

    def _candidats(self, famille, pris, place=None):
        """Joueurs d'une famille de postes qui ne sont pas dans `pris`, dans l'ordre de la profondeur ; pour l'OL, les
        remplaçants d'abord, et le tackle de rechange pour une place de tackle ou un 6e OL, le guard à l'intérieur."""
        if famille == "OL":
            tackle = place in (None, "LT", "RT", "WR1")
            postes = ("RT", "LT", "LG", "RG", "C") if tackle else ("LG", "RG", "C", "RT", "LT")
            ids = [i for p in postes for i in self.prof.get(p, [])]
            ids = sorted(ids, key=lambda i: (i in self.base["off"].values(), ids.index(i)))
        else:
            ids = list(self.prof.get(famille, []))
        return [i for i in ids if i not in pris]

    def _rotation(self, groupe, rng, figee):
        """Occupants des places d'un groupe en rotation (DT, EDGE, RB) : énergie + retard sur la part visée."""
        places, _ = ROTATION[groupe]
        poste = POSTE_PLACE[places[0]][0]
        cands = self.prof.get(poste, [])
        if len(cands) <= len(places):
            return {pl: self.base[COTE_POSTE[poste]][pl] for pl in places}
        c = COTE_POSTE[poste]
        avant = {pl: self.dernier[c][pl] for pl in places}
        if figee:
            return avant
        tit = [self.base[c][pl] for pl in places]
        cible = part_visee(self.equipe, groupe)
        reste_part = max(0.0, len(places) * (1.0 - cible))       # le 1er remplaçant prend le reste (RB2, DT3…)
        rempl = [i for i in cands if i not in tit]
        n = self.n[c]

        def score(i):
            visee = cible if i in tit else (reste_part if i == rempl[0] else 0.0)
            s = self.energie[i] + QUOTA * (visee * n - self.snaps[i]) + rng.uniform(-BRUIT_ROTATION, BRUIT_ROTATION)
            if i not in tit and i != rempl[0]:
                s -= TROISIEME                          # le RB3 ne prend la place que d'un RB épuisé
            return s + (RESTE if i in avant.values() else 0.0)

        choisis = sorted(cands, key=lambda i: (-score(i), cands.index(i)))[:len(places)]
        occ = {pl: i for pl, i in avant.items() if i in choisis}
        libres = [i for i in choisis if i not in occ.values()]
        for pl in places:
            if pl not in occ:
                t = self.base[c][pl]
                occ[pl] = t if t in libres else libres[0]
                libres.remove(occ[pl])
        return occ

    def alignement(self, cote, formation=None, personnel=None, paquet=None, rng=None, garbage=False, figee=False):
        """Occupants des 11 places de l'unité `cote` pour cette action -> (occupants {place: id}, subs).
        figee : pas de rotation (défense face au hurry-up pendant un drive : elle ne peut pas changer).
        subs : [{"in", "out", "pos", "reason"}] par rapport à la dernière action de l'unité (vide si rien ne change)."""
        rng = rng or random.Random(0)
        occ0 = dict(self.base[cote])
        for groupe, (places, _) in ROTATION.items():
            if COTE_POSTE[POSTE_PLACE[places[0]][0]] == cote:
                occ0.update(self._rotation(groupe, rng, figee))
        repos = set()
        if garbage:                               # les titulaires sortent, leurs remplaçants entrent
            for pl, fam in GARBAGE:
                if pl in occ0 and occ0[pl] is not None:
                    pris = set(occ0.values()) | repos
                    r = next((i for i in self._candidats(fam, pris, pl)
                              if i not in self.base[cote].values()), None)
                    if r is not None:
                        repos.add(self.base[cote][pl])
                        if occ0[pl] != self.base[cote][pl]:   # déjà un remplaçant (rotation) : le titulaire se repose
                            repos.add(occ0[pl])
                        occ0[pl] = r
        regles = (DEFENSE_PACKAGE.get(paquet or "", ()) if cote == "def" else
                  FORMATION_PACKAGE.get(formation or "") or PERSONNEL_PACKAGE.get(personnel or "11", ()))
        paq = set()
        for pl, fam in regles:
            pris = set(occ0.values()) | repos
            r = next(iter(self._candidats(fam, pris, pl)), None)
            if r is not None:
                occ0[pl] = r
                paq.add(pl)
        subs = []
        for pl in PLACES[cote]:
            a, b = self.dernier[cote].get(pl), occ0.get(pl)
            if a != b and b is not None:
                raison = "package" if (pl in paq or pl in self.paquet[cote]) else \
                    "garbage" if (garbage or self.garbage) else "fatigue"
                subs.append({"in": b, "out": a, "pos": pl, "reason": raison})
        self.dernier[cote], self.paquet[cote] = dict(occ0), paq
        self.garbage = garbage
        return occ0, subs

    def jouer(self, cote, occupants, gain=0, secondes=0, hurry=False):
        """Un snap de l'unité `cote` : énergie de ceux qui jouent, récupération des autres, snaps comptés."""
        sur = set(i for i in occupants.values() if i)
        self.n[cote] += 1
        for i, e in self.energie.items():
            if i in sur:
                self.snaps[i] += 1
                self.energie[i] = max(0.0, e - cout_snap(self.pos[i], gain, secondes, hurry and cote == "def"))
            else:
                self.energie[i] = min(100.0, e + RECUP_SNAP)

    def recuperer(self, points):
        for i in self.energie:
            self.energie[i] = min(100.0, self.energie[i] + points)

    def mi_temps(self):
        self.recuperer(RECUP_MI_TEMPS)

    def resume(self):
        """{id: {"snaps", "pct", "energy"}} (part des snaps de son unité)."""
        out = {}
        for i, s in self.snaps.items():
            n = self.n[COTE_POSTE.get(self.pos[i], "off")] if self.pos[i] in COTE_POSTE else 0
            out[i] = {"snaps": s, "pct": round(100.0 * s / n) if n else 0, "energy": round(self.energie[i])}
        return out


def garbage_time(wp_meneur, quart, deja=False, part_du_quart=0.0, ecart=None):
    """Garbage time : match plié en fin de match — 4e quart-temps, dans ses GARBAGE_FIN dernières minutes (part du
    quart qui reste), probabilité de victoire du meneur > 98 % ET au moins trois possessions d'écart (GARBAGE_ECART :
    à une possession, 98 % à deux minutes de la fin n'est pas un match plié) ; une fois entré, on n'en sort que sous
    95 % ou à moins de trois possessions."""
    if quart != 4 or part_du_quart > GARBAGE_FIN or (ecart is not None and abs(ecart) < GARBAGE_ECART):
        return False
    return wp_meneur > (GARBAGE_SORTIE if deja else GARBAGE_WP)
