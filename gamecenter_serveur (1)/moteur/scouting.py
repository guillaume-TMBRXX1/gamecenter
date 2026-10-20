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

  6. IDÉE 6 (20/10/2026, notebook 12.2 vicies bis) — LA MÉMOIRE D'UNE SEMAINE À L'AUTRE : le « film » de chaque attaque
     (ses appels joués des semaines passées, oubli de 0,5 par semaine) amorce le carnet de la défense — étudié
     formation par formation, plafonné en actions équivalentes, effacé pendant le match (a priori < film < match) —
     et le self-scout de l'attaque (match OU film) ; une défense qui a la réputation de lire compte comme « elle lit ».
     Fin du module : film_match, film_suivant, film_pour, reputation, observations_feed (amorce depuis les GameFeeds).

« Un profil, pas un niveau » : la vitesse d'apprentissage et l'oubli viennent des profils de 12.2 quater et du bloc D
(`profil_defense`, `profil_attaque`) ; l'engagement et le bluff sont l'identité de la franchise (SCOUT) ; le poids du
film vient de la fenêtre du bloc D (POIDS_FILM).
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

# idée 6 — la mémoire d'une semaine à l'autre (le « film ») : voir la fin du module
VERSION_MEMOIRE = "scouting-2"   # play.scout.version quand le film est branché
FILM_VERSION = "film-1"
OUBLI_SEMAINE = 0.5              # film de la semaine suivante = film × 0,5 + la semaine jouée (≈ 2 semaines au plus)
POIDS_SIENS = 1.5                # les matchs que la défense a joués elle-même contre cette attaque pèsent 1,5 fois
# actions équivalentes par situation : la défense étudie le film formation par formation (« from I-Form on 1st down ») ;
# les situations générales (down & distance, zone, personnel) restent celles du match — sur le film, elles sont proches
# de la moyenne de la ligue et noieraient les séries du match (mesuré : 5,0 lectures par match au lieu de 5,7)
FILM_MAX = {"ddf": 8.0, "form": 3.0, "dd": 0.0, "zone": 0.0, "pers": 0.0}
# l'attaque se juge avant de choisir sa formation (down & distance, zone) : elle sait ce qu'elle y a montré
FILM_MAX_SOI = {"ddf": 8.0, "form": 6.0, "dd": 20.0, "zone": 10.0, "pers": 0.0}
FILM_DEMI_VIE = 24.0             # le film s'efface pendant le match (snaps de l'attaque) : le match prend le dessus
FILM_CONF_MAX = 0.80             # confiance d'une tendance vue surtout sur le film, au plus
FILM_MIN = 0.5                   # comptes plus petits (une demi-action) : oubliés (taille du film bornée)
CLES_PAIRE = ("form",)           # comptes gardés par paire défense / attaque (ses propres matchs ; taille du film)
REPUTATION = {"matchs": 3.0, "key": 3.5, "juste": 0.60}    # défense « qui lit » : lectures par match, part de justes
# poids du film (0,6 - 1,4) : 1 + 0,1 × (fenêtre du bloc D − 8), sauf identités : les méthodiques et les vétérans
# étudient le film, la jeune SPK y croit peu, les équipes qui jouent leur jeu restent sobres
POIDS_FILM = {"AEG": 1.3, "CTD": 1.3, "MRD": 1.3, "SPK": 0.6, "MNL": 0.8, "FRG": 0.8, "GRZ": 0.8}

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
    "MNL": (0.50, 0.10, 1),   # physique : joue son jeu
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
    "BST": (0.60, 0.30, 3),   # lockdown : lit et ferme, sans parier (déjà la meilleure défense ; 12.3, 20/10)
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
    """Ce qu'une attaque a montré, situation par situation, avec oubli (demi-vie en snaps de cette attaque).
    Idée 6 : une couche « film » (ce qu'on sait d'avant le match, `amorcer`) s'ajoute aux comptes du match et
    s'efface à son propre rythme ; sans film, le carnet est exactement celui de l'idée 5."""

    def __init__(self, demi_vie=16.0):
        self.f = 0.5 ** (1.0 / max(1.0, float(demi_vie)))
        self.t = 0                   # snaps observés
        self.cles = {}               # clé -> {"t", "pas", "run", "fam": {}, "vu": [passes, courses] (bruts)}
        self.recents = []            # derniers jeux : "RUN" / "PASS"
        self.film = {}               # clé -> {"pas", "run", "fam", "vu": [passes, courses] (du film, pondérés)}
        self.film_f = 1.0            # oubli du film par snap du match
        self.film_info = None        # {"games", "own"} : matchs sur le film (pondérés par l'oubli hebdomadaire)
        self.film_ou = False         # self-scout : tendance du match OU du film (le film ne noie pas le match)
        self._sources = (True, True)  # (match, film) lus par `lire`

    def _vieillir(self, s):
        k = self.f ** (self.t - s["t"])
        if k != 1.0:
            s["pas"] *= k
            s["run"] *= k
            for f_ in s["fam"]:
                s["fam"][f_] *= k
            s["t"] = self.t

    def amorcer(self, film, demi_vie=None, info=None, ou=False):
        """Idée 6 : film = {clé: {"pas", "run", "fam", "vu"}} déjà mis à l'échelle (`film_pour`) ; il s'efface d'une
        demi-vie `demi_vie` (snaps de l'attaque observés dans le match)."""
        self.film = {c: {"pas": v["pas"], "run": v["run"], "fam": dict(v.get("fam") or {}), "vu": list(v["vu"])}
                     for c, v in (film or {}).items() if v["pas"] + v["run"] > 0}
        self.film_f = 0.5 ** (1.0 / max(1.0, float(demi_vie or FILM_DEMI_VIE)))
        self.film_info = info if self.film else None
        self.film_ou = bool(ou)

    def _k_film(self):
        return self.film_f ** self.t

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
        """Une cassure qui a réussi : ce qu'on croyait savoir de ces situations compte moitié moins (film compris)."""
        for c in cles:
            s = self.cles.get(c)
            if s is not None:
                self._vieillir(s)
                s["pas"] *= k
                s["run"] *= k
                for f_ in s["fam"]:
                    s["fam"][f_] *= k
            fi = self.film.get(c) if self.film else None
            if fi is not None:
                fi["pas"] *= k
                fi["run"] *= k
                for f_ in fi["fam"]:
                    fi["fam"][f_] *= k

    def lire(self, cles, a_priori, k0):
        """Prédiction mélangée : {"p": part des passes, "n": actions vues (pondérées), "cle": meilleure preuve,
        "fam": famille la plus vue du côté prédit et sa part, "film": part du film dans la preuve}."""
        num = den = 0.0
        n_max, meilleure, fams = 0.0, None, {}
        avec_match, avec_film = self._sources
        kf = self._k_film() if self.film else 0.0
        w_film = 0.0
        for c in cles:
            s = self.cles.get(c) if avec_match else None
            fi = self.film.get(c) if self.film and avec_film else None
            if s is None and fi is None:
                continue
            if s is not None:
                self._vieillir(s)
                pas, run = s["pas"], s["run"]
            else:
                pas = run = 0.0
            nf = 0.0
            if fi is not None:
                fp, fr = kf * fi["pas"], kf * fi["run"]
                nf = fp + fr
                pas, run = pas + fp, run + fr
            n = pas + run
            if n <= 0:
                continue
            pc = POIDS_CLE.get(c[0], 0.5)
            p = (pas + a_priori * k0) / (n + k0)
            w = n * pc
            num += w * p
            den += w
            w_film += nf * pc
            if n > n_max:
                n_max = n
            if meilleure is None or w > meilleure[1]:
                meilleure = (c, w)
            if s is not None:
                for f_, v in s["fam"].items():
                    fams[f_] = fams.get(f_, 0.0) + v * pc
            if fi is not None:
                for f_, v in fi["fam"].items():
                    fams[f_] = fams.get(f_, 0.0) + kf * v * pc
        if den <= 0:
            return {"p": a_priori, "n": 0.0, "cle": None, "fam": None, "part_fam": 0.0, "film": 0.0}
        p = num / den
        cote = "PASS" if p >= 0.5 else "RUN"
        dans = FAMILLES_PASSE if cote == "PASS" else FAMILLES_COURSE
        tot = sum(v for f_, v in fams.items() if f_ in dans)
        top = max(((f_, v) for f_, v in fams.items() if f_ in dans), key=lambda x: (x[1], x[0]), default=(None, 0))
        return {"p": p, "n": n_max, "cle": meilleure[0], "fam": top[0], "part_fam": top[1] / tot if tot else 0.0,
                "film": w_film / den}

    def preuve(self, cle):
        """Comptes bruts d'une situation (pour le texte : « 7 of his last 8 »)."""
        s = self.cles.get(cle)
        return tuple(s["vu"]) if s else (0, 0)

    def preuve_film(self, cle):
        """Comptes du film d'une situation (pondérés par l'oubli hebdomadaire, arrondis pour le texte)."""
        fi = self.film.get(cle) if self.film else None
        return (int(round(fi["vu"][0])), int(round(fi["vu"][1]))) if fi else (0, 0)


ORDRE_TEXTE = ("ddf", "form", "dd", "pers", "zone")   # pour raconter : la situation la plus précise d'abord


def cle_parlante(carnet, cles, cote, n_min=3, part=0.7, film=False):
    """La situation qui raconte le mieux la tendance : la plus précise où l'attaque a fait `cote` au moins `part` des
    `n_min`+ fois (« 7 of 8 runs on 1st down from I-Form » plutôt que « … between the 20s ») ; film=True : dans les
    comptes du film (idée 6)."""
    par = dict(cles)
    for typ in ORDRE_TEXTE:
        if typ not in par:
            continue
        pas, run = (carnet.preuve_film if film else carnet.preuve)((typ, par[typ]))
        vu = pas if cote == "PASS" else run
        if pas + run >= n_min and vu >= part * (pas + run):
            return (typ, par[typ])
    return None


def tendance(carnet, cles, profil, a_priori):
    """La tendance de l'attaque dans cette situation : None ou {"cote", "p", "conf", "n", "cle", "fam", ...}.
    Carnet « film_ou » (self-scout, idée 6) : la tendance du match seul (idée 5), sinon celle du film seul."""
    if carnet is None:
        return None
    if carnet.film_ou and carnet.film:
        try:
            carnet._sources = (True, False)
            t = _tendance(carnet, cles, profil, a_priori)
            if t is None:
                carnet._sources = (False, True)
                t = _tendance(carnet, cles, profil, a_priori)
        finally:
            carnet._sources = (True, True)
        return t
    return _tendance(carnet, cles, profil, a_priori)


def _tendance(carnet, cles, profil, a_priori):
    r = carnet.lire(cles, a_priori, profil["k0"])
    p = r["p"]
    conf = max(p, 1 - p)
    if r["n"] < profil["n_min"] or conf < SEUIL or abs(p - a_priori) < ECART:
        return None
    cote = "PASS" if p >= 0.5 else "RUN"
    sur_film = r.get("film", 0.0) >= 0.5           # idée 6 : la preuve vient surtout du film
    cle = (cle_parlante(carnet, cles, cote, film=True) if sur_film else None) or cle_parlante(carnet, cles, cote) \
        or r["cle"]
    pas, run = (carnet.preuve_film if sur_film else carnet.preuve)(cle) if cle else (0, 0)
    t = {"cote": cote, "p": round(p, 3), "conf": round(conf, 3), "n": round(r["n"], 2), "cle": cle,
         "fam": r["fam"] if r["part_fam"] >= 0.5 else None, "part_fam": round(r["part_fam"], 3),
         "vu": pas if cote == "PASS" else run, "sur": pas + run, "a_priori": a_priori}
    if r.get("film") and carnet.film_info:
        t["film"] = dict(carnet.film_info, part=round(r["film"], 3))
    return t


def _confiance(t):
    """0,6 au seuil d'une tendance nette, 1 vingt points au-delà. Idée 6 : une tendance vue surtout sur le film est
    plafonnée à FILM_CONF_MAX (le film ne vaut pas le match)."""
    conf = t["conf"]
    if (t.get("film") or {}).get("part", 0.0) >= 0.5:
        conf = min(conf, FILM_CONF_MAX)
    return 0.6 + 0.4 * _borne((conf - SEUIL) / 0.2, 0.0, 1.0)


def engagement(t, profil, graine, n):
    """La défense s'engage-t-elle sur la tendance t ? (probabilité, tirage) — flux « scouting-def »."""
    if t is None:
        return False, 0.0
    p = profil["engagement"] * _confiance(t)
    u = flux(FLUX_DEF, graine, n).random()
    return u < p, round(p, 3)


def se_sait_lue(signaux):
    """La défense a-t-elle montré qu'elle lit ? signaux : {"lu_juste": n, "reponse": bool, "stoppees": n,
    "reputation": bool (idée 6 : elle a beaucoup lu, et juste, sur le film des semaines passées)}."""
    s = signaux or {}
    return bool(s.get("lu_juste", 0) >= 1 or s.get("reponse") or s.get("stoppees", 0) >= 2 or s.get("reputation"))


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
    f = t.get("film") or {}
    if f.get("part", 0.0) >= 0.5:                  # idée 6 : « film: 41 of 52 runs on 1st down, 19 games »
        return f"film: {t['vu']} of {t['sur']} {quoi}{(' ' + sit_texte) if sit_texte else ''}, {f['games']} games"
    return f"{t['vu']} of {t['sur']} {quoi}{(' ' + sit_texte) if sit_texte else ''}"


# ---------- idée 6 : la mémoire d'une semaine à l'autre (le film) ----------
# Le film d'une attaque = ce qu'une défense voit avant le snap (down & distance, formation, personnel, zone) et ce qui
# a été joué (course / passe, famille), sur tous ses matchs des semaines passées, avec un oubli d'une semaine à l'autre.
# Il entre dans le carnet comme une couche à part (Carnet.amorcer), plafonnée en actions équivalentes (FILM_MAX × poids
# du coordinateur) : le film garde les proportions de l'attaque, pas sa masse. Aucun hasard.
def poids_film(abbr, fenetre=8):
    if abbr in POIDS_FILM:
        return POIDS_FILM[abbr]
    return _borne(1.0 + 0.1 * (float(fenetre) - 8.0), 0.6, 1.4)


def cle_texte(c):
    return f"{c[0]}|{c[1]}"


def cle_de(txt):
    typ, val = txt.split("|", 1)
    return (typ, val)


def observation(down, distance, yard_line, formation, personnel, cote, concept, classe_course=None):
    """Une action vue sur le film : (clés de situation, côté, famille)."""
    return (situations(down, distance, yard_line, formation, personnel), cote, famille(cote, concept, classe_course))


def observations_feed(feed, classe_course=None):
    """Actions d'un GameFeed exporté (amorce depuis les semaines de data/weeks) :
    [(attaque, défense, clés, côté, famille)] — mêmes actions que le journal (courses et passes, sans genou ni spike)."""
    g = feed.get("game") or {}
    ab = {"home": (g.get("home") or {}).get("abbr"), "away": (g.get("away") or {}).get("abbr")}
    out = []
    for pl in feed.get("plays") or []:
        call = pl.get("call") or {}
        if call.get("type") not in ("run", "pass") or call.get("play_id") in ("KNEEL", "SPIKE") \
                or pl.get("down") is None or pl.get("los_x") is None:
            continue
        side = pl.get("offense")
        off, de = ab.get(side), ab.get("away" if side == "home" else "home")
        if not off or not de:
            continue
        yl = (pl["los_x"] - 10) if side == "home" else (110 - pl["los_x"])
        cote = "PASS" if call["type"] == "pass" else "RUN"
        cles, cote, fam = observation(pl["down"], pl["to_go"], int(round(yl)), call.get("formation"),
                                      call.get("personnel"), cote, call.get("concept"),
                                      (classe_course or {}).get(call.get("concept")))
        out.append((off, de, cles, cote, fam))
    return out


def lectures_feed(feed):
    """{défense: [lectures, justes]} d'un GameFeed (play.scout.def) — la réputation des défenses."""
    g = feed.get("game") or {}
    ab = {"home": (g.get("home") or {}).get("abbr"), "away": (g.get("away") or {}).get("abbr")}
    out = {}
    for pl in feed.get("plays") or []:
        d = (pl.get("scout") or {}).get("def")
        if d and ab.get(d.get("team")):
            r = out.setdefault(ab[d["team"]], [0, 0])
            r[0] += 1
            r[1] += bool(d.get("right"))
    return out


def film_vide():
    return {"version": FILM_VERSION, "semaines": 0, "attaques": {}, "paires": {}, "defenses": {}}


def _compter(cles_d, txt, cote, fam, avec_fam=True):
    e = cles_d.get(txt)
    if e is None:
        e = cles_d[txt] = [0.0, 0.0, {}] if avec_fam else [0.0, 0.0]
    e[0 if cote == "PASS" else 1] += 1.0
    if avec_fam and fam:
        e[2][fam] = e[2].get(fam, 0.0) + 1.0


def film_match(film, off, de, observations, lectures=None):
    """Ajoute un match au film de la semaine : les actions de l'attaque `off` contre la défense `de`
    (observations : [(clés, côté, famille)]) et, pour la réputation de `de`, ses lectures (lectures, justes)."""
    a = film["attaques"].setdefault(off, {"matchs": 0.0, "cles": {}})
    pa = film["paires"].setdefault(f"{de}|{off}", {"matchs": 0.0, "cles": {}})
    d = film["defenses"].setdefault(de, {"matchs": 0.0, "key": 0.0, "juste": 0.0})
    a["matchs"] += 1.0
    pa["matchs"] += 1.0
    d["matchs"] += 1.0
    if lectures:
        d["key"] += float(lectures[0])
        d["juste"] += float(lectures[1])
    for cles, cote, fam in observations:
        for c in cles:
            _compter(a["cles"], cle_texte(c), cote, fam)
            if c[0] in CLES_PAIRE:
                _compter(pa["cles"], cle_texte(c), cote, fam, avec_fam=False)
    return film


def _r(x):
    return round(x, 1)


def film_suivant(prev, semaine, oubli=OUBLI_SEMAINE, derniere=None):
    """Film de la semaine suivante = film précédent × oubli + la semaine jouée ; comptes < FILM_MIN oubliés. Série
    géométrique bornée : le film ne pèse jamais plus de 1 / (1 − oubli) semaines."""
    out = film_vide()
    out["semaines"] = (prev or {}).get("semaines", 0) + 1
    if derniere:
        out["derniere"] = derniere

    def fondre(src, k, dst):
        for nom in ("attaques", "paires"):
            for team, v in sorted(((src or {}).get(nom) or {}).items()):
                o = dst[nom].setdefault(team, {"matchs": 0.0, "cles": {}})
                o["matchs"] += k * v["matchs"]
                for txt, e in sorted(v["cles"].items()):
                    x = o["cles"].get(txt)
                    if x is None:
                        x = o["cles"][txt] = [0.0, 0.0, {}] if len(e) > 2 else [0.0, 0.0]
                    x[0] += k * e[0]
                    x[1] += k * e[1]
                    if len(e) > 2:
                        for f_, w in sorted(e[2].items()):
                            x[2][f_] = x[2].get(f_, 0.0) + k * w
        for team, v in sorted(((src or {}).get("defenses") or {}).items()):
            o = dst["defenses"].setdefault(team, {"matchs": 0.0, "key": 0.0, "juste": 0.0})
            for kk in ("matchs", "key", "juste"):
                o[kk] += k * v[kk]

    fondre(prev, oubli, out)
    fondre(semaine, 1.0, out)
    for nom in ("attaques", "paires"):
        for team in list(out[nom]):
            v = out[nom][team]
            v["matchs"] = _r(v["matchs"])
            for txt in list(v["cles"]):
                e = v["cles"][txt]
                if e[0] + e[1] < FILM_MIN:
                    del v["cles"][txt]
                    continue
                e[0], e[1] = _r(e[0]), _r(e[1])
                if len(e) > 2:
                    e[2] = {f_: _r(w) for f_, w in e[2].items() if w >= FILM_MIN}
            if not v["cles"]:
                del out[nom][team]
    for team, v in out["defenses"].items():
        for kk in ("matchs", "key", "juste"):
            v[kk] = _r(v[kk])
    return out


def film_pour(film, de, off, poids=1.0, siens=POIDS_SIENS, plafonds=None):
    """Le film de l'attaque `off` tel que la défense `de` l'a étudié (de=None : l'attaque sur elle-même, FILM_MAX_SOI),
    mis à l'échelle pour Carnet.amorcer : {clé: {"pas", "run", "fam", "vu"}}, info {"games", "own"} ; ({}, None) sans
    film."""
    a = ((film or {}).get("attaques") or {}).get(off)
    if not a or poids <= 0:
        return {}, None
    pa = ((film.get("paires") or {}).get(f"{de}|{off}") or {}) if de else {}
    pc = pa.get("cles") or {}
    mx = plafonds or (FILM_MAX if de else FILM_MAX_SOI)
    out = {}
    for txt, e in sorted(a["cles"].items()):
        c = cle_de(txt)
        pp = pc.get(txt) or (0.0, 0.0)
        rp, rr = e[0] + (siens - 1.0) * pp[0], e[1] + (siens - 1.0) * pp[1]
        n = rp + rr
        if n <= 0:
            continue
        k = min(n, mx.get(c[0], 0.0)) * poids / n
        if k <= 0:
            continue
        kf = k * n / (e[0] + e[1]) if e[0] + e[1] > 0 else k
        out[c] = {"pas": rp * k, "run": rr * k, "fam": {f_: w * kf for f_, w in sorted(e[2].items())},
                  "vu": [rp, rr]}
    info = {"games": int(round(a["matchs"])), "own": int(round(pa.get("matchs", 0.0)))}
    return out, info


def reputation(film, de):
    """La défense `de` a-t-elle la réputation de lire (beaucoup de lectures, souvent justes, sur le film) ?"""
    d = ((film or {}).get("defenses") or {}).get(de)
    if not d or d["matchs"] < REPUTATION["matchs"] or d["key"] <= 0:
        return False
    return d["key"] / d["matchs"] >= REPUTATION["key"] and d["juste"] / d["key"] >= REPUTATION["juste"]


def film_cle(film):
    """Empreinte courte et stable du film (clé du cache des cotes)."""
    import hashlib
    import json
    if not film:
        return None
    return hashlib.sha1(json.dumps(film, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:12]


def film_tendances(carnet, profil, n=2):
    """Rapport d'avant-match : les `n` tendances nettes que la défense apporte du film, down & distance × formation
    (les plus éloignées de l'a priori, au moins 6 actions sur le film) : [{"dd", "formation", "cote", "p", "vu", "sur"}]."""
    out = []
    for (typ, val) in sorted(carnet.film):
        if typ != "ddf":
            continue
        dd, form = val.split("|", 1)
        ap = A_PRIORI.get(dd, 0.6)
        t = tendance(carnet, [(typ, val)], profil, ap)
        if t is not None and t["sur"] >= 6 and (t.get("film") or {}).get("part", 0.0) >= 0.5:
            out.append({"dd": dd, "formation": form, "cote": t["cote"], "p": t["p"], "vu": t["vu"], "sur": t["sur"],
                        "ecart": abs(t["p"] - ap) * min(1.0, t["sur"] / 20.0)})
    out.sort(key=lambda x: (-x["ecart"], x["dd"], x["formation"]))
    return [{k: v for k, v in x.items() if k != "ecart"} for x in out[:n]]


def controler_film(film, equipes=None):
    """Bornes du film (audit) : version, comptes ≥ 0, matchs > 0, familles ≤ comptes, équipes connues."""
    pb = []
    if not isinstance(film, dict) or film.get("version") != FILM_VERSION:
        return ["film : version inconnue"]
    eq = set(equipes or [])
    for nom in ("attaques", "paires"):
        for team, v in (film.get(nom) or {}).items():
            noms = team.split("|")
            if eq and not set(noms) <= eq:
                pb.append(f"film {nom} : équipe inconnue {team}")
            if v.get("matchs", 0) <= 0:
                pb.append(f"film {nom} {team} : aucun match")
            for txt, e in v.get("cles", {}).items():
                if txt.split("|", 1)[0] not in FILM_MAX:
                    pb.append(f"film {nom} {team} : clé {txt}")
                if e[0] < 0 or e[1] < 0:
                    pb.append(f"film {nom} {team} {txt} : compte négatif")
                if len(e) > 2 and sum(e[2].values()) > e[0] + e[1] + 0.05 * (len(e[2]) + 2) + 1e-6:   # arrondis au dixième
                    pb.append(f"film {nom} {team} {txt} : familles > comptes")
    for team, d in (film.get("defenses") or {}).items():
        if eq and team not in eq:
            pb.append(f"film défenses : équipe inconnue {team}")
        if not (0 <= d["juste"] <= d["key"] + 0.01) or d["matchs"] < 0:
            pb.append(f"film défense {team} : lectures hors bornes")
    return pb
