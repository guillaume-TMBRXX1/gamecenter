"""Checks avant le snap (étape 4 « moteur plus intelligent », 16/10/2026) : le QB lit la défense, la défense répond aux
motions.

Au snap, une fois l'appel offensif et la défense connus (paquet, front, motion : extension du playbook, 12.2 decies) :
  1. RÉPONSE À LA MOTION (défense) : quand l'attaque met un joueur en motion, la défense peut
       - « roll » : un safety tourne vers la motion — un défenseur de plus dans la boîte, la coquille se dévoile ;
       - « lock » (homme) : le défenseur suit le joueur en motion — le QB sait que c'est de l'homme ;
       - « bump » (zone) : les défenseurs se passent le joueur — rien ne se dévoile, la motion perd son effet sur le
         déguisement et la moitié de la séparation qu'elle donne en homme.
     Profil de la franchise (probabilité de réagir, goût pour la rotation), jamais un niveau.
  2. LECTURE DU QB : la défense MONTRE une boîte (défenseurs près de la ligne) et une coquille (1-high / 2-high) ; un
     paquet déguisé ment (« 2-high rotating » : un safety descend au snap, la boîte montrée a un défenseur de moins ;
     « mug » : des linebackers dans les intervalles qui reculent au snap, la boîte montrée en a un ou deux de plus). Le
     QB voit au travers selon son awareness et sa lecture de couverture (bloc B), moins le déguisement (que la motion
     et le shift réduisent déjà, extension) ; une rotation ou un « lock » lui dévoile tout.
  3. AUDIBLE : boîte lue chargée (8 et plus, pour 6 bloqueurs) contre une course → passe ; boîte lue légère (6 et
     moins) contre une passe, 6 yards ou moins à faire → course. La fréquence est l'IDENTITÉ de la franchise (liberté
     laissée au QB à la ligne, penchant vers la course ou la passe) modulée par l'awareness du QB.
     TROMPÉ : le QB a lu la boîte montrée au lieu de la vraie, et son check en dépend — mauvais audible (« mauvais »),
     ou audible qu'il aurait fait et qu'il ne fait pas (« manque »).
  4. CHRONO : un audible coûte COUT secondes du chrono d'avant-snap (+ COUT_REPONSE si la défense a répondu à une
     motion) ; l'horloge du match tourne d'autant si elle tournait. Il reste toujours au moins 1 s au snap ; une
     attaque qui tue l'horloge fait son check dans le temps qu'elle prend déjà.

Le gain d'un bon audible et le coût d'un mauvais ne sont PAS ajoutés ici : ils viennent du moteur (bloc F : yards de
la course selon la boîte réelle ; passe : déguisement de la lecture du QB). Python pur ; hasard dans des flux dédiés
(moteur.aleatoire.flux) : le hasard du moteur n'est jamais consommé.
"""
from .aleatoire import flux

VERSION = "presnap-1"
FLUX = "presnap"                 # lecture et audible
FLUX_DEF = "presnap-def"         # réponse à la motion
FLUX_JEU = "presnap-jeu"         # jeu choisi après l'audible (notebook)

CHARGEE, LEGERE = 8, 6           # boîte lue chargée (≥) / légère (≤) — 6 bloqueurs (bloc F)
DISTANCE_COURSE = 6              # passe → course seulement à 6 yards ou moins de la ligne à franchir
SECONDES_MIN = 15                # plus d'audible dans les 15 dernières secondes d'un quart-temps
COUT, COUT_REPONSE = 2, 1        # secondes de chrono d'avant-snap utilisées par un audible
CHRONO, RESTE_MIN = 10, 1        # chrono d'avant-snap ; il en reste au moins RESTE_MIN au snap

# ce que la défense montre : écart de la boîte montrée à la vraie, coquille montrée
PRESENTATION = {"2-high rotating": (-1, "2-high"), "mug": (1, None), "double A-gap mug": (2, None)}
# paquets dont la présentation est vraie (une vraie pression montrée en mug)
FRANCS = {"MUG_BLITZ"}
COQUILLE_APPEL = {"COVER_2": "2-high", "COVER_4": "2-high", "BOX_STACK": "1-high", "BLITZ": "1-high",
                  "MAN": "1-high", "ZONE": "1-high", "COVER_3": "1-high"}

# perception : probabilité de voir au travers d'une présentation trompeuse
VOIR = {"base": 0.55, "awareness": 0.02, "coverage_reading": 0.01, "min": 0.10, "max": 0.92}
REF_QB = 80
# fréquence de l'audible : liberté × (1 ± penchant) × facteur du QB (awareness) × intensité de la boîte
QB_PENTE, QB_MIN, QB_MAX = 0.03, 0.6, 1.4
INTENSITE = 0.3                  # boîte de 5 ou de 9 : 30 % de plus qu'une boîte de 6 ou de 8

# identité offensive : (liberté laissée au QB à la ligne, penchant : + vers la course, − vers la passe)
#   haute : attaques à tempo, aériennes, techniques, QB expérimentés ; basse : « on joue notre jeu »
LIBERTE = {
    "CTX": (0.32, 0.0),    # équilibrée, adaptative
    "VEC": (0.48, -0.3),   # offensive, orientée passe : sort de la course contre une boîte chargée
    "AEG": (0.16, 0.2),    # méthodique, contrôlée
    "MNL": (0.10, 0.5),    # physique, course et puissance : joue son jeu
    "AXM": (0.51, 0.0),    # West Coast précise : le QB a les clés à la ligne
    "GLT": (0.22, 0.0),    # imprévisible
    "CPH": (0.16, 0.2),    # option : la lecture est dans le jeu
    "NVA": (0.32, -0.3),   # verticale : un check vers la passe
    "PLS": (0.58, -0.1),   # tempo, no-huddle : tout se décide à la ligne
    "ONX": (0.26, 0.0),    # opportuniste
    "FRG": (0.10, 0.5),    # tranchées : joue son jeu
    "MRD": (0.29, 0.2),    # stratégique, patiente
    "APX": (0.42, 0.0),    # créative
    "LTC": (0.38, 0.1),    # spread : chaque défenseur doit choisir
    "ZPH": (0.54, -0.4),   # air raid
    "BST": (0.22, 0.1),    # identité défensive, attaque sobre
    "GRZ": (0.19, 0.3),    # attaque équilibrée, défense contre la course
    "MRG": (0.38, 0.0),    # manipuler la défense
    "GMB": (0.35, -0.1),   # audacieuse
    "PRM": (0.42, 0.0),    # polyvalente, duels choisis
    "SPK": (0.13, 0.0),    # jeune : le QB joue l'appel
    "CTD": (0.54, 0.1),    # expérimentée, posée
    "TDL": (0.16, 0.2),    # zone large et bootleg : système
    "CMT": (0.22, 0.0),    # vitesse et équipes spéciales
}
LIBERTE_DEFAUT = (0.26, 0.0)

# identité défensive face aux motions : (probabilité de réagir, part des rotations « roll »)
REPONSE = {
    "CTX": (0.60, 0.40), "VEC": (0.55, 0.30), "AEG": (0.75, 0.20), "MNL": (0.50, 0.50), "AXM": (0.60, 0.30),
    "GLT": (0.70, 0.60), "CPH": (0.55, 0.40), "NVA": (0.50, 0.40), "PLS": (0.50, 0.30), "ONX": (0.65, 0.40),
    "FRG": (0.50, 0.50), "MRD": (0.70, 0.20), "APX": (0.60, 0.40), "LTC": (0.55, 0.30), "ZPH": (0.45, 0.30),
    "BST": (0.80, 0.20), "GRZ": (0.65, 0.60), "MRG": (0.60, 0.40), "GMB": (0.55, 0.50), "PRM": (0.65, 0.40),
    "SPK": (0.45, 0.40), "CTD": (0.75, 0.30), "TDL": (0.55, 0.40), "CMT": (0.50, 0.40),
}
REPONSE_DEFAUT = (0.55, 0.40)


def _borne(x, a, b):
    return max(a, min(b, x))


def boite_montree(boite_reelle, paquet=None, presente=None):
    """Défenseurs que la défense montre près de la ligne avant le snap (5-9)."""
    if not paquet or paquet in FRANCS:
        return boite_reelle
    d = PRESENTATION.get(presente or "", (0, None))[0]
    return int(_borne(boite_reelle + d, 5, 9))


def coquilles(concept_defensif, paquet=None, presente=None, coquille_reelle=None):
    """(coquille montrée, coquille jouée) : « 1-high », « 2-high » ou « 0-high »."""
    reelle = coquille_reelle or COQUILLE_APPEL.get(concept_defensif, "1-high")
    if presente and presente.startswith("0-high"):
        reelle = "0-high"
    montree = reelle
    if paquet and paquet not in FRANCS:
        montree = PRESENTATION.get(presente or "", (0, None))[1] or (
            "2-high" if presente and presente.startswith("2-high") else reelle)
    return montree, reelle


def regard(boite):
    """Ce que dit une boîte : chargée, légère, neutre."""
    return "chargee" if boite >= CHARGEE else "legere" if boite <= LEGERE else "neutre"


def reponse_motion(defense, famille, motion, graine, n):
    """Réponse de la défense à une motion (None, « roll », « lock », « bump ») — flux « presnap-def »."""
    if not motion:
        return None
    p, p_roll = REPONSE.get(defense, REPONSE_DEFAUT)
    rng = flux(FLUX_DEF, graine, n)
    r1, r2 = rng.random(), rng.random()
    if r1 >= p:
        return None
    if r2 < p_roll:
        return "roll"
    return "lock" if famille == "homme" else "bump"


def p_voir(qb_iq, deguisement):
    """Probabilité que le QB voie au travers d'une présentation trompeuse."""
    iq = qb_iq or {}
    p = VOIR["base"] + (float(iq.get("awareness", REF_QB)) - REF_QB) * VOIR["awareness"] \
        + (float(iq.get("coverage_reading", REF_QB)) - REF_QB) * VOIR["coverage_reading"] - max(0.0, deguisement)
    return _borne(p, VOIR["min"], VOIR["max"])


def facteur_qb(qb_iq):
    return _borne(1 + (float((qb_iq or {}).get("awareness", REF_QB)) - REF_QB) * QB_PENTE, QB_MIN, QB_MAX)


def p_audible(attaque, qb_iq, vers, boite):
    """Probabilité de changer le jeu vers `vers` (« PASS » / « RUN ») devant une boîte lue `boite`."""
    lib, pen = LIBERTE.get(attaque, LIBERTE_DEFAUT)
    sens = (1 + pen) if vers == "RUN" else (1 - pen)
    ecart = (LEGERE - boite) if vers == "RUN" else (boite - CHARGEE)
    return _borne(lib * sens * facteur_qb(qb_iq) * (1 + INTENSITE * max(0, ecart)), 0.0, 0.95)


def vers_quoi(intention, boite_lue, situation):
    """Audible que la boîte lue justifie (« PASS » / « RUN » / None) — règles de la situation comprises."""
    s = situation or {}
    if s.get("secondes", 999) < SECONDES_MIN or s.get("interdit"):
        return None
    down, dist, mode = s.get("down", 1), s.get("distance", 10), s.get("mode")
    r = regard(boite_lue)
    if intention == "RUN" and r == "chargee":
        if mode == "clock":                                   # tuer l'horloge : on reste au sol
            return None
        if dist <= 1 and (down >= 3 or s.get("en_but", 99) <= 3):   # 3e / 4e et 1, goal line : la boîte chargée
            return None                                              # est attendue, on pousse
        return "PASS"
    if intention == "PASS" and r == "legere":
        if mode == "hurry" or dist > DISTANCE_COURSE:          # menée, l'horloge presse : on reste en l'air
            return None
        return "RUN"
    return None


def check(attaque, defense, intention, qb_iq, boite_reelle, situation, graine, n, concept_defensif=None,
          paquet=None, presente=None, famille=None, deguisement=0.0, motion=None, coquille_reelle=None):
    """Le check avant le snap. Renvoie un dict (voir le GameFeed play.presnap) :
        reponse        : réponse de la défense à la motion (None, roll, lock, bump)
        boite_reelle   : boîte au snap (après une rotation : +1) ; boite_montree, boite_lue
        coquille       : (montrée, jouée) ; vu : le QB a vu au travers (None : rien à voir)
        audible        : None, « PASS » ou « RUN » ; trompe : None, « mauvais » ou « manque »
        p              : probabilité d'audible devant la boîte lue (0 si rien à changer) ; u : tirage
    """
    reponse = reponse_motion(defense, famille, motion, graine, n)
    reelle = int(_borne(boite_reelle + (1 if reponse == "roll" else 0), 5, 9))
    montree = boite_montree(reelle, paquet, presente)
    coq = coquilles(concept_defensif, paquet, presente, coquille_reelle)
    revele = reponse in ("roll", "lock")
    if reponse == "bump":
        deguisement = max(deguisement, 0.0) + 0.1
    rng = flux(FLUX, graine, n)
    u_voir, u = rng.random(), rng.random()
    vu = None
    lue = reelle
    if montree != reelle or coq[0] != coq[1]:
        vu = True if revele else u_voir < p_voir(qb_iq, deguisement)
        lue = reelle if vu else montree
        if revele:
            montree = reelle
    v = vers_quoi(intention, lue, situation)
    p = p_audible(attaque, qb_iq, v, lue) if v else 0.0
    audible = v if (v and u < p) else None
    # le même tirage avec la vraie boîte : qu'aurait fait le QB s'il avait lu juste ?
    v_juste = vers_quoi(intention, reelle, situation)
    juste = v_juste if (v_juste and u < p_audible(attaque, qb_iq, v_juste, reelle)) else None
    trompe = None
    if vu is False and audible != juste:
        trompe = "mauvais" if audible else "manque"
    return {"version": VERSION, "reponse": reponse, "boite_reelle": reelle, "boite_montree": montree,
            "boite_lue": lue, "regard": regard(lue), "coquille": coq, "vu": vu, "audible": audible,
            "trompe": trompe, "p": round(p, 3), "u": round(u, 4)}


def cout(audible, reponse, chrono_utilise=None, mode=None):
    """Secondes de chrono d'avant-snap que coûte le check (0 quand l'attaque tue déjà l'horloge ou que le chrono ne
    le permet pas : il reste toujours RESTE_MIN s au snap). chrono_utilise : secondes déjà utilisées (None : inconnu,
    horloge arrêtée — le coût ne se voit qu'à l'écran)."""
    if not audible or mode == "clock":
        return 0
    c = COUT + (COUT_REPONSE if reponse else 0)
    if chrono_utilise is None:
        return c
    return max(0, min(c, CHRONO - RESTE_MIN - int(chrono_utilise)))


def preferer(concept, vers, quick=frozenset(), interieures=frozenset()):
    """Poids d'un jeu candidat après l'audible : passes rapides et courses intérieures d'abord (un « can » de la
    feuille d'appel), le reste reste possible."""
    if vers == "PASS":
        return 3.0 if concept in quick else 1.0
    return 3.0 if concept in interieures else 1.0
