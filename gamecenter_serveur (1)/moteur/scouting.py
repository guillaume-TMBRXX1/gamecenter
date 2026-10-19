"""Appel de jeu qui apprend et reste imprévisible (étape 5 « moteur plus intelligent », 19/10/2026).

Pendant le match, chaque DÉFENSE tient un carnet de ce que l'attaque adverse a montré, situation par situation, et
chaque ATTAQUE tient le même carnet sur elle-même (« self-scout ») :
  1. SITUATIONS : down & distance (1st, 2nd / 3rd long, moyen, court, 4th), formation, personnel, zone du terrain
     (son camp, milieu, territoire adverse, zone rouge, goal-to-go) et le croisement down & distance × formation.
     Pour chacune : courses / passes et famille du jeu (course intérieure, extérieure, jeu rapide, passe moyenne,
     profonde, screen / draw, play action). Les comptes s'OUBLIENT (demi-vie en snaps de cette attaque).
  2. TENDANCE NETTE : la part de passes de chaque situation part de l'a priori de la ligue (A_PRIORI, par down &
     distance, force `k0`) ; les situations du snap sont mélangées, pondérées par ce qui a été vu (la plus précise
     compte davantage). Nette = au moins `n_min` actions vues, prédiction d'au moins SEUIL d'un côté, et un écart
     d'au moins ECART à l'a priori (passer sur un 3e et 9, tout le monde le sait : ce n'est pas une tendance).
  3. LA DÉFENSE S'ENGAGE (« KEY ») sur une tendance nette avec une probabilité qui est son profil (engagement) ×
     la confiance — flux « scouting-def ». Engagée : priorité course ou passe, concept contre la famille attendue ;
     l'anticipation (ANTICIPATION) paie si elle devine juste et coûte si l'attaque la punit.
  4. L'ATTAQUE SE SAIT LUE quand sa tendance est nette dans la situation du snap ET que la défense lui a montré
     qu'elle lit (une défense engagée et juste, une réponse de 12.2 quater contre la course ou le jeu court, des
     courses stoppées) ; elle CASSE sa tendance (« BREAK ») selon son profil (bluff) — flux « scouting-att » :
     play action après une série de courses, passe sur un down de course (ou draw / screen sur un down de passe),
     même formation pour le jeu opposé. Plafond par match ; jamais en hurry-up ni en tuant l'horloge.
  5. Une cassure qui réussit sème le doute : la défense divise par deux ce qu'elle croyait savoir de la situation.

« Un profil, pas un niveau » : la vitesse d'apprentissage et l'oubli viennent des profils de 12.2 quater et du bloc D
(`profil_defense`, `profil_attaque`) ; l'engagement et le bluff sont l'identité de la franchise (SCOUT).
Python pur ; hasard dans des flux dédiés (moteur.aleatoire.flux) : le hasard du moteur n'est jamais consommé.
"""
from .aleatoire import flux

VERSION = "scouting-1"
FLUX_DEF = "scouting-def"        # la défense s'engage-t-elle ?
FLUX_ATT = "scouting-att"        # l'attaque casse-t-elle sa tendance ?

SEUIL = 0.66                     # prédiction minimale d'un côté
ECART = 0.10                     # écart minimal à l'a priori de la ligue
BLUFF_K = 2.0                    # probabilité de casser = BLUFF_K × bluff × vigilance × confiance (au plus P_MAX)
P_MAX = 0.9
POIDS_CLE = {"dd": 1.0, "form": 0.8, "pers": 0.5, "zone": 0.5, "ddf": 1.6}   # la plus précise compte davantage

# part des passes de la ligue par down & distance (moteur complet, 48 matchs du 19/10 : 61 % de passes)
A_PRIORI = {"1": 0.58, "2-long": 0.72, "2-mid": 0.51, "2-short": 0.53, "3-long": 0.83, "3-mid": 0.53,
            "3-short": 0.48, "4": 0.84}

# familles de jeu (concept final du play_log)
SCREENS = {"SCREEN", "FL_SE_SCREEN", "WR_TUNNEL_SCREEN", "DRAW", "QB_DRAW"}
PLAY_ACTION = {"PLAY_ACTION", "PA_FLOOD", "PA_SLIDE", "BOOT", "POP"}
RAPIDES = {"QUICK_SLANT", "HITCH", "SPOT_SNAG", "STICK", "CHOICE", "PIVOT", "SHORT_OUT", "DRAG", "SLANT",
           "QUICK_OUT", "SHORT_PASS", "FADE"}
PROFONDES = {"FOUR_VERTS", "DIVIDE", "SWITCH_VERTICALS", "CHAMP", "CORNER", "DEEP_CROSS", "DEEP_POST", "DOUBLE_POST"}
EXTERIEURES = {"outside", "perimeter"}
FAMILLES_COURSE = ("inside", "outside", "screen")
FAMILLES_PASSE = ("quick", "medium", "deep", "screen", "pa")

# effet d'anticipation d'une défense engagée (en défenseurs de boîte pour la course, en pas de séparation pour la passe)
ANTICIPATION = {
    "course_juste": 1,           # engagée sur la course, c'est une course : un défenseur de plus dans le trou
    "course_juste_yds": -0.8,    # ... et le porteur est lu plus vite (yards, en plus de la boîte plafonnée à 9)
    "course_fausse": -1,         # engagée sur la passe, c'est une course : boîte allégée
    "course_fausse_yds": 1.0,    # ... et les rushers ont pris le large (draw, course dans leur dos)
    "passe_juste": -0.7,         # engagée sur la passe : la famille attendue est couverte de près
    "passe_juste_autre": -0.25,  # ... les autres routes un peu
    "poche_juste": -0.3,         # engagée sur la passe : le rush part plus tôt (secondes de poche)
    "poche_fausse": 0.25,        # engagée sur la course : les rushers attendent la course
    "passe_fausse": 0.9,         # engagée sur la course, c'est une passe : les linebackers mordent
    "pa_fausse": 1.3,            # ... et sur un play action, davantage
}

# identité : (engagement de la défense sur une tendance nette, bluff de l'attaque, cassures au plus par match)
#   engagement haut : défenses qui lisent et attaquent le ballon (ONX, BST) ou qui parient (GLT, SPK, GMB) ;
#   bluff bas : « on joue notre jeu » (MNL, FRG, GRZ) ; bluff haut : joueurs d'échecs (MRG, CTX, LTC, PRM, CTD, GMB)
SCOUT = {
    "CTX": (0.60, 0.55, 5),   # très adaptative, lit vite
    "VEC": (0.45, 0.25, 3),   # force son jeu
    "AEG": (0.40, 0.35, 3),   # méthodique : lente mais sûre
    "MNL": (0.50, 0.05, 1),   # physique : joue son jeu
    "AXM": (0.50, 0.45, 4),   # précise, le QB a les clés
    "GLT": (0.80, 0.40, 4),   # imprévisible, parie
    "CPH": (0.45, 0.30, 3),   # l'option : la lecture est dans le jeu
    "NVA": (0.45, 0.25, 3),   # verticale
    "PLS": (0.50, 0.35, 4),   # tempo
    "ONX": (0.75, 0.35, 3),   # ball hawk : lit et attaque le ballon
    "FRG": (0.50, 0.05, 1),   # tranchées : joue son jeu
    "MRD": (0.40, 0.35, 3),   # patiente
    "APX": (0.55, 0.45, 4),   # créative
    "LTC": (0.55, 0.55, 5),   # spread : chaque défenseur doit choisir
    "ZPH": (0.45, 0.20, 2),   # air raid : volume
    "BST": (0.70, 0.25, 3),   # lockdown : lit et ferme
    "GRZ": (0.60, 0.10, 1),   # défense contre la course ; attaque sobre
    "MRG": (0.50, 0.70, 7),   # play action : manipuler la défense
    "GMB": (0.70, 0.60, 6),   # audacieuse
    "PRM": (0.55, 0.55, 5),   # polyvalente
    "SPK": (0.75, 0.25, 3),   # jeune : apprend vite, oublie vite, parie trop
    "CTD": (0.45, 0.55, 5),   # vétérans : lit et attend
    "TDL": (0.50, 0.40, 4),   # zone large, bootleg
    "CMT": (0.50, 0.35, 3),   # équilibrée
}
SCOUT_DEFAUT = (0.50, 0.35, 3)


def _borne(x, a, b):
    return max(a, min(b, x))


# ---------- profils (dérivés de 12.2 quater et du bloc D) ----------
def profil_defense(abbr, trigger=2, fenetre=8):
    """Défense : n_min et force de l'a priori depuis `trigger` (12.2 quater : 1 = répond au premier coup) ;
    demi-vie (snaps de l'attaque) depuis `fenetre` (bloc D : mémoire courte ou longue)."""
    eng = SCOUT.get(abbr, SCOUT_DEFAUT)[0]
    return {"n_min": 2 + int(trigger), "k0": 1.0 + int(trigger), "demi_vie": 2.0 * float(fenetre),
            "engagement": eng}


def profil_attaque(abbr, learn=0.6, patience=3, fenetre=8):
    """Attaque : vigilance (voit-elle qu'elle est lue) depuis `learn` (12.2 quater) ; n_min depuis `patience` ;
    demi-vie depuis `fenetre` (bloc D) ; bluff et plafond : SCOUT."""
    _, bluff, casse_max = SCOUT.get(abbr, SCOUT_DEFAUT)
    return {"n_min": 1 + int(patience), "k0": 3.0, "demi_vie": 2.0 * float(fenetre),
            "vigilance": _borne(0.4 + 0.6 * float(learn), 0.4, 1.0), "bluff": bluff, "casse_max": int(casse_max)}


# ---------- situations ----------
def down_distance(down, distance):
    if down <= 1:
        return "1"
    if down >= 4:
        return "4"
    return f"{down}-{'long' if distance >= 7 else 'mid' if distance >= 3 else 'short'}"


def zone(yard_line, distance):
    a_faire = 100 - yard_line
    if distance >= a_faire:
        return "goal"
    if yard_line < 20:
        return "own"
    if yard_line < 60:
        return "mid"
    return "terr" if yard_line < 80 else "red"


def situations(down, distance, yard_line, formation=None, personnel=None):
    """Clés de situation d'un snap : [(type, valeur)]."""
    dd = down_distance(down, distance)
    cles = [("dd", dd), ("zone", zone(yard_line, distance))]
    if formation:
        cles += [("form", formation), ("ddf", f"{dd}|{formation}")]
    if personnel:
        cles.append(("pers", str(personnel)))
    return cles


def famille(cote, concept, classe_course=None):
    """Famille d'un jeu joué : course (inside, outside, screen = draw) ou passe (quick, medium, deep, screen, pa)."""
    c = concept or ""
    if cote == "RUN":
        if c in SCREENS:
            return "screen"
        return "outside" if (classe_course or "") in EXTERIEURES else "inside"
    if c in SCREENS:
        return "screen"
    if c in PLAY_ACTION:
        return "pa"
    if c in RAPIDES:
        return "quick"
    return "deep" if c in PROFONDES else "medium"


# ---------- le carnet ----------
class Carnet:
    """Ce qu'une attaque a montré, situation par situation, avec oubli (demi-vie en snaps de cette attaque)."""

    def __init__(self, demi_vie=16.0):
        self.f = 0.5 ** (1.0 / max(1.0, float(demi_vie)))
        self.t = 0                   # snaps observés
        self.cles = {}               # clé -> {"t", "pas", "run", "fam": {}, "vu": [passes, courses] (bruts)}
        self.recents = []            # derniers jeux : "RUN" / "PASS"

    def _vieillir(self, s):
        k = self.f ** (self.t - s["t"])
        if k != 1.0:
            s["pas"] *= k
            s["run"] *= k
            for f_ in s["fam"]:
                s["fam"][f_] *= k
            s["t"] = self.t

    def observer(self, cles, cote, fam=None):
        self.t += 1
        for c in cles:
            s = self.cles.get(c)
            if s is None:
                s = self.cles[c] = {"t": self.t, "pas": 0.0, "run": 0.0, "fam": {}, "vu": [0, 0]}
            self._vieillir(s)
            if cote == "PASS":
                s["pas"] += 1.0
                s["vu"][0] += 1
            else:
                s["run"] += 1.0
                s["vu"][1] += 1
            if fam:
                s["fam"][fam] = s["fam"].get(fam, 0.0) + 1.0
        self.recents = (self.recents + [cote])[-6:]

    def douter(self, cles, k=0.5):
        """Une cassure qui a réussi : ce qu'on croyait savoir de ces situations compte moitié moins."""
        for c in cles:
            s = self.cles.get(c)
            if s is not None:
                self._vieillir(s)
                s["pas"] *= k
                s["run"] *= k
                for f_ in s["fam"]:
                    s["fam"][f_] *= k

    def lire(self, cles, a_priori, k0):
        """Prédiction mélangée : {"p": part des passes, "n": actions vues (pondérées), "cle": meilleure preuve,
        "fam": famille la plus vue du côté prédit et sa part}."""
        num = den = 0.0
        n_max, meilleure, fams = 0.0, None, {}
        for c in cles:
            s = self.cles.get(c)
            if s is None:
                continue
            self._vieillir(s)
            n = s["pas"] + s["run"]
            if n <= 0:
                continue
            p = (s["pas"] + a_priori * k0) / (n + k0)
            w = n * POIDS_CLE.get(c[0], 0.5)
            num += w * p
            den += w
            if n > n_max:
                n_max = n
            if meilleure is None or w > meilleure[1]:
                meilleure = (c, w)
            for f_, v in s["fam"].items():
                fams[f_] = fams.get(f_, 0.0) + v * POIDS_CLE.get(c[0], 0.5)
        if den <= 0:
            return {"p": a_priori, "n": 0.0, "cle": None, "fam": None, "part_fam": 0.0}
        p = num / den
        cote = "PASS" if p >= 0.5 else "RUN"
        dans = FAMILLES_PASSE if cote == "PASS" else FAMILLES_COURSE
        tot = sum(v for f_, v in fams.items() if f_ in dans)
        top = max(((f_, v) for f_, v in fams.items() if f_ in dans), key=lambda x: (x[1], x[0]), default=(None, 0))
        return {"p": p, "n": n_max, "cle": meilleure[0], "fam": top[0], "part_fam": top[1] / tot if tot else 0.0}

    def preuve(self, cle):
        """Comptes bruts d'une situation (pour le texte : « 7 of his last 8 »)."""
        s = self.cles.get(cle)
        return tuple(s["vu"]) if s else (0, 0)


ORDRE_TEXTE = ("ddf", "form", "dd", "pers", "zone")   # pour raconter : la situation la plus précise d'abord


def cle_parlante(carnet, cles, cote, n_min=3, part=0.7):
    """La situation qui raconte le mieux la tendance : la plus précise où l'attaque a fait `cote` au moins `part` des
    `n_min`+ fois (« 7 of 8 runs on 1st down from I-Form » plutôt que « … between the 20s »)."""
    par = dict(cles)
    for typ in ORDRE_TEXTE:
        if typ not in par:
            continue
        pas, run = carnet.preuve((typ, par[typ]))
        vu = pas if cote == "PASS" else run
        if pas + run >= n_min and vu >= part * (pas + run):
            return (typ, par[typ])
    return None


def tendance(carnet, cles, profil, a_priori):
    """La tendance de l'attaque dans cette situation : None ou {"cote", "p", "conf", "n", "cle", "fam", ...}."""
    if carnet is None:
        return None
    r = carnet.lire(cles, a_priori, profil["k0"])
    p = r["p"]
    conf = max(p, 1 - p)
    if r["n"] < profil["n_min"] or conf < SEUIL or abs(p - a_priori) < ECART:
        return None
    cote = "PASS" if p >= 0.5 else "RUN"
    cle = cle_parlante(carnet, cles, cote) or r["cle"]
    pas, run = carnet.preuve(cle) if cle else (0, 0)
    return {"cote": cote, "p": round(p, 3), "conf": round(conf, 3), "n": round(r["n"], 2), "cle": cle,
            "fam": r["fam"] if r["part_fam"] >= 0.5 else None, "part_fam": round(r["part_fam"], 3),
            "vu": pas if cote == "PASS" else run, "sur": pas + run, "a_priori": a_priori}


def _confiance(t):
    """0,6 au seuil d'une tendance nette, 1 vingt points au-delà."""
    return 0.6 + 0.4 * _borne((t["conf"] - SEUIL) / 0.2, 0.0, 1.0)


def engagement(t, profil, graine, n):
    """La défense s'engage-t-elle sur la tendance t ? (probabilité, tirage) — flux « scouting-def »."""
    if t is None:
        return False, 0.0
    p = profil["engagement"] * _confiance(t)
    u = flux(FLUX_DEF, graine, n).random()
    return u < p, round(p, 3)


def se_sait_lue(signaux):
    """La défense a-t-elle montré qu'elle lit ? signaux : {"lu_juste": n, "reponse": bool, "stoppees": n}."""
    s = signaux or {}
    return bool(s.get("lu_juste", 0) >= 1 or s.get("reponse") or s.get("stoppees", 0) >= 2)


def type_cassure(t, recents, dd):
    """Comment casser la tendance t : « pa » (play action après une série de courses), « run_down_pass » (passe sur
    un down de course), « pass_down_run » (draw / screen sur un down de passe) ou « same_formation » (le jeu opposé
    depuis la formation qui trahit la tendance ; sans elle, le notebook en fait « against_tendency »)."""
    if t["cote"] == "RUN":
        if sum(1 for x in recents[-4:] if x == "RUN") >= 3:
            return "pa"
        if dd.endswith("short") or dd == "1":
            return "run_down_pass" if dd.endswith("short") else "pa"
        return "same_formation"
    if dd.endswith("long") or dd == "4":
        return "pass_down_run"
    return "same_formation"


def cassure(t, profil, signaux, deja, situation, graine, n):
    """L'attaque casse-t-elle sa tendance t ? -> (None | type, probabilité) — flux « scouting-att ».
    situation : {"mode", "down", "dd", "recents", "exclu"} ; deja : cassures déjà faites dans le match."""
    s = situation or {}
    if t is None or s.get("exclu") or s.get("mode") in ("hurry", "clock") or s.get("down", 1) >= 4:
        return None, 0.0
    if deja >= profil["casse_max"] or not se_sait_lue(signaux):
        return None, 0.0
    p = min(P_MAX, BLUFF_K * profil["bluff"] * profil["vigilance"] * _confiance(t))
    u = flux(FLUX_ATT, graine, n).random()
    if u >= p:
        return None, round(p, 3)
    return type_cassure(t, s.get("recents") or [], s.get("dd") or "1"), round(p, 3)


def anticipation(cle_cote, cle_fam, joue_cote, joue_fam):
    """Effet d'une défense engagée sur `cle_cote` (famille `cle_fam`) contre le jeu joué.
    Course : {"boite": ±1, "yds": yards} ; passe : {"court", "moyen", "profond"} en pas de séparation et "poche" en
    secondes (+ : pour l'attaque)."""
    if joue_cote == "RUN":
        if cle_cote == "RUN":
            return {"boite": ANTICIPATION["course_juste"], "yds": ANTICIPATION["course_juste_yds"]}
        return {"boite": ANTICIPATION["course_fausse"], "yds": ANTICIPATION["course_fausse_yds"]}
    if cle_cote == "RUN":
        v = ANTICIPATION["pa_fausse"] if joue_fam == "pa" else ANTICIPATION["passe_fausse"]
        return {"court": v, "moyen": v, "profond": v, "poche": ANTICIPATION["poche_fausse"]}
    j, a, pj = ANTICIPATION["passe_juste"], ANTICIPATION["passe_juste_autre"], ANTICIPATION["poche_juste"]
    if cle_fam in ("quick", "screen"):
        return {"court": j, "moyen": a, "profond": 0.0, "poche": pj}
    if cle_fam == "deep":
        return {"court": 0.0, "moyen": a, "profond": j, "poche": pj}
    if cle_fam in ("medium", "pa"):
        return {"court": a, "moyen": j, "profond": a, "poche": pj}
    return {"court": (j + a) / 2, "moyen": (j + a) / 2, "profond": (j + a) / 2, "poche": pj}


def juste(cle_cote, joue_cote):
    return cle_cote == joue_cote


def raison(t, sit_texte):
    """Texte court de la preuve : « 7 of 8 runs on 1st & 10 from I-form »."""
    quoi = "passes" if t["cote"] == "PASS" else "runs"
    return f"{t['vu']} of {t['sur']} {quoi}{(' ' + sit_texte) if sit_texte else ''}"
