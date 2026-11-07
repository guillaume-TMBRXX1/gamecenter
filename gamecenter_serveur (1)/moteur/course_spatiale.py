"""Causal léger, bloc 1 : la course après le premier contact, simulée dans l'espace (chantier du 06/11/2026).

Avant ce bloc, les yards d'une course venaient d'une table (V0.2), ajustée par le bloc F (moteur/course.py : boîte, trou,
duels, lecture, contact — dont un terme « puissance contre tackling ») puis par les actions longues (moteur/
actions_longues.py : l'échappée au-delà du 2e rideau, et un « rabot » qui gardait la moyenne). Le résultat était tiré,
les joueurs ne le décidaient qu'en moyenne.

Ici, jusqu'au premier contact rien ne change (table + bloc F) ; à partir du contact, le porteur et les défenseurs
jouent la suite sur le terrain :
  DÉPART    le porteur est au point de contact : la profondeur dépend du niveau du contact décidé par le bloc F (ligne,
            linebacker, second rideau) et ne dépasse pas les yards déjà tirés (une course stoppée reste stoppée) ;
  DÉFENSE   les onze défenseurs du moteur placés selon leur poste et ce niveau (ligne engagée près de la ligne, LB au
            2e niveau, safeties et corners derrière) ; le plaqueur du bloc F est au contact ;
  SIMULATION pas de DT secondes : le porteur court vers l'en-but en s'écartant des défenseurs devant lui (agilité),
            chaque défenseur suit un angle de poursuite (vitesse) ; au contact, un plaquage est tenté (tackling contre
            agilité ou puissance, plus sûr avec des coéquipiers autour) : manqué, le défenseur est gêné un instant et le
            porteur perd son élan ; réussi, le porteur tombe vers l'avant (puissance) ; touche et en-but l'arrêtent.
Les notes pèsent donc par ce qu'elles font : vitesse (qui rattrape qui), agilité et puissance (plaquages manqués,
yards après contact), tackling. Le hasard a son flux (« course-spatiale|<graine>|<n° d'action> ») : le moteur n'en
consomme pas plus qu'avant. Purement Python, ≈ 0,1 ms par course (prototype du 06/11 : + 1,4 % du temps d'un match).

Les réglages (PARAMS) sont calibrés pour que la distribution des yards de course reste celle de la ligue (moyenne,
courses de 10, 20 et 40 yards et plus) : outils/moteur/semaine_course_spatiale.py.
"""
import math

from . import aleatoire

VERSION = "course-spatiale-1"

PARAMS = {
    # calibrés le 06/11/2026 (outils/moteur/semaine_course_spatiale.py, puis réglage hors moteur sur les 11 869 courses
    # d'une semaine) : distribution des yards de course, points et avantage du terrain de la ligue ; un porteur du quart
    # le mieux noté gagne ≈ 1,2 yard de plus par course que celui du quart le moins bien noté
    "dt": 0.1,                 # pas de temps (s)
    "t_max": 8.0,              # durée maximale après le contact
    "rayon": 1.0,              # yards : distance de plaquage
    "evitement": 6.0,          # yards : distance à laquelle le porteur évite un défenseur
    "p_contact": 0.401,        # le premier plaquage, celui du défenseur au contact
    "p_plaquage": 0.507,       # réussite d'un plaquage à notes égales (ligne, linebackers)
    "p_arriere": 0.688,        # même chose pour un safety ou un corner
    "k_plaquage": 0.011,       # par point (tackling − max(agilité, puissance) du porteur)
    "renfort": 0.377,          # réussite du plaquage en plus par autre défenseur à moins de 2,5 yards
    "gene": 1.184,             # secondes de gêne après un plaquage manqué
    "perte": 0.913,            # plaquage cassé : le porteur garde cette part de sa vitesse
    "chute": 0.1,              # yards gagnés en tombant (moyenne, + puissance)
    "k_chute": 0.003,          # par point de puissance au-delà de 70 (chute et poussée)
    "pousse": 0.0,             # yards de poussée au premier contact, + puissance
    "elan": 0.787,             # au contact, le porteur court déjà : cette part de sa vitesse maximale
    "pente": 0.035,            # yards par seconde par point de note de vitesse (écart entre rapides et lents)
    "vit_porteur": 1.0,        # échelle de vitesse du porteur
    "vit_defense": 1.146,      # échelle de vitesse des défenseurs (ligne, linebackers)
    "vit_arriere": 1.093,      # échelle de vitesse des safeties et corners
    "anticipe": 2.377,         # secondes : jusqu'où un défenseur anticipe le point d'interception
    "fatigue": 0.001,          # longue course : vitesse perdue par yard au-delà de "fatigue_dep" yards après le contact
    "fatigue_dep": 22.198,
    "fatigue_min": 0.588,      # il garde au moins cette part de sa vitesse
    # profondeur du contact (yards depuis la ligne) selon le niveau du bloc F : uniforme [a, b]
    "profondeur": {"ligne": (-0.86, 1.14), "linebacker": (2.87, 5.87), "second rideau": (6.43, 10.43)},
}

# vitesse par défaut des postes sans note de vitesse (ligne défensive)
VITESSE_POSTE = {"EDGE": 76, "DT": 66, "LB": 80, "S": 84, "CB": 86}


def vitesse_max(note, echelle=1.0, pente=0.075):
    """Note de vitesse -> yards par seconde (pente 0,075 : 60-99 -> 7,0 à 9,9 ; 80 -> 8,5 quelle que soit la pente)."""
    return (8.5 + (note - 80) * pente) * echelle


def profondeur_contact(t_pre, niveau, rng, params=PARAMS):
    """Yards gagnés au moment du premier contact : la profondeur du niveau, jamais plus que les yards déjà tirés."""
    a, b = params["profondeur"].get(niveau, params["profondeur"]["linebacker"])
    return min(float(t_pre), rng.uniform(a, b))


def placer(defenseurs, niveau, depart, y0, plaqueur_id, rng):
    """Positions des défenseurs au moment du contact : [x, y, poste, notes, id] (x depuis la ligne de mêlée)."""
    out = []
    for d in defenseurs:
        pos, r = d.get("pos"), d.get("ratings") or {}
        if d.get("id") == plaqueur_id:
            x, y = depart + 0.8, y0 + rng.uniform(-0.5, 0.5)
        elif pos in ("EDGE", "DT"):
            x, y = rng.uniform(-0.5, 1.5), y0 + rng.uniform(-6, 6)
        elif pos == "LB":
            x, y = max(depart - 1.5, rng.uniform(2.0, 6.0)), y0 + rng.uniform(-8, 8)
        elif pos == "S":
            x, y = max(depart + 2.0, rng.uniform(8.0, 15.0)), y0 + rng.uniform(-14, 14)
        else:                                   # CB et autres
            x, y = max(depart + 1.0, rng.uniform(5.0, 12.0)), (rng.uniform(3, 12) if rng.random() < 0.5 else rng.uniform(41, 50))
        out.append([x, min(52.3, max(1.0, y)), pos, r, d.get("id")])
    return out


def apres_contact(porteur, defenseurs, niveau, t_pre, y0, plaqueur_id, but, graine, n, params=PARAMS, trace=False):
    """La course à partir du premier contact.

    porteur    : {"ratings": {speed, acceleration, elusiveness, power}} ; defenseurs : [{"id", "pos", "ratings"}] (les onze)
    niveau     : "ligne" / "linebacker" / "second rideau" (bloc F) ; t_pre : yards tirés avant ce bloc (table + bloc F)
    y0         : position en travers du porteur (0 à 53,3) ; but : yards jusqu'à l'en-but
    Renvoie {"yards" (total, entier), "contact" (yards au contact), "apres", "plaqueur" (id ou None), "manques",
             "sortie", "td", "chemin" (si trace)}.
    """
    P = params
    rng = aleatoire.flux("course-spatiale", graine, n)
    p = porteur.get("ratings") or {}
    vit, acc0 = p.get("speed", 80), p.get("acceleration", p.get("speed", 80))
    ag, pu = p.get("elusiveness", 75), p.get("power", 75)
    dep = contact = profondeur_contact(t_pre, niveau, rng, P)
    D = []
    for x, y, pos, r, i in placer(defenseurs, niveau, dep, y0, plaqueur_id, rng):
        v = vitesse_max(r.get("speed", VITESSE_POSTE.get(pos, 75)), P["vit_arriere"] if pos in ("S", "CB") else P["vit_defense"],
                        P.get("pente", 0.075))
        v *= 0.9 + 0.002 * (r.get("run_support", r.get("tackling", 75)) - 70)
        base = P["p_arriere"] if pos in ("S", "CB") else P["p_plaquage"]
        D.append([x, y, v, r.get("tackling", 75), 0.0, i, P.get("p_contact", base) if i == plaqueur_id else base, base])
        # x, y, vitesse, tackling, gêne, id, réussite de base de son prochain plaquage, réussite en terrain découvert
    if dep >= float(t_pre) - 1e-9 and t_pre <= 0:
        pass                                            # course stoppée derrière la ligne : pas de poussée
    else:
        dep += max(0.0, rng.gauss(P["pousse"] + (pu - 70) * P["k_chute"], 0.6))   # il encaisse le premier choc et avance
    vmax, acc = vitesse_max(vit, P["vit_porteur"], P.get("pente", 0.075)), 3.0 + (acc0 - 60) * 0.08
    total, yards, fin, manques, chemin = _simuler(dep, y0, vmax * P.get("elan", 0.0), vmax, acc, ag, pu, dep, D, but, rng, P,
                                                 trace)
    return {"version": VERSION, "yards": yards, "contact": round(contact, 1), "apres": round(total - contact, 1),
            "plaqueur": fin["plaqueur"], "manques": manques, "sortie": fin["sortie"], "td": fin["td"],
            "chemin": chemin if trace else None, "trace": fin.get("trace") if trace else None}


def _simuler(x0, y0, v, vmax, acc, ag, pu, dep, D, but, rng, P, trace=False):
    """La course du porteur au milieu des défenseurs D (voir apres_contact), partie de (x0, y0) à la vitesse v ;
    dep : point d'où l'usure d'une longue course se compte. Renvoie (total, yards entiers, fin, manques, chemin)."""
    px, py = x0, y0
    t, manques, chemin = 0.0, 0, []
    dt, ev, rayon = P["dt"], P["evitement"], P["rayon"]
    hypot = math.hypot
    fin = {"plaqueur": None, "sortie": False, "td": False}
    tr = None
    if trace:                                           # trace complète (export du dessin) : porteur, défenseurs, plaquages
        tr = {"c": [(px, py)], "d": {q[5]: [(q[0], q[1])] for q in D}, "ev": []}
        fin["trace"] = tr

    def _pas():
        if tr is not None:
            tr["c"].append((px, py))
            for q in D:
                tr["d"][q[5]].append((q[0], q[1]))
    while t < P["t_max"]:
        t += dt
        ax, ay = 1.0, 0.0                               # vers l'en-but, en s'écartant des défenseurs devant lui
        for q in D:
            dx, dy = q[0] - px, q[1] - py
            dd = hypot(dx, dy)
            if dd < ev and dx > -1.0:
                w = (ev - dd) / ev * (0.6 + ag / 200)
                ay -= w * dy / (dd + 1e-6)
                ax -= 0.4 * w * dx / (dd + 1e-6)
        nn = hypot(ax, ay) or 1.0
        loin = px - dep - P["fatigue_dep"]                 # une longue course l'use : les poursuivants le reprennent
        vcap = vmax * max(P["fatigue_min"], 1.0 - P["fatigue"] * loin) if loin > 0 else vmax
        v = min(vcap, v + acc * dt)
        ux, uy = ax / nn, ay / nn
        px += v * ux * dt
        py += v * uy * dt
        if trace:
            chemin.append((round(px, 1), round(py, 1)))
        if py < 0.3 or py > 53.0:
            fin["sortie"] = True
            _pas()
            break
        if px >= but:
            px, fin["td"] = but, True
            _pas()
            break
        plaque = False
        for q in D:
            if q[4] > 0:
                q[4] -= dt
                continue
            dx, dy = px - q[0], py - q[1]
            dd = hypot(dx, dy)
            if dd < rayon:
                aide = sum(1 for o in D if o is not q and o[4] <= 0 and hypot(px - o[0], py - o[1]) < 2.5)
                if rng.random() < q[6] + (q[3] - max(ag, pu)) * P["k_plaquage"] + aide * P["renfort"]:
                    px += max(0.0, rng.gauss(P["chute"] + (pu - 70) * P["k_chute"], 0.5))
                    fin["plaqueur"] = q[5]
                    plaque = True
                    if tr is not None:
                        tr["ev"].append((round(t, 2), q[5], 1))
                    break
                manques += 1
                if tr is not None:
                    tr["ev"].append((round(t, 2), q[5], 0))
                q[4], q[6] = P["gene"], q[7]            # raté : ses plaquages suivants sont en terrain découvert
                v *= P["perte"]                         # il casse le plaquage mais perd son élan
                continue
            # angle de poursuite : le point où il coupe la course du porteur (s'il va tout droit à sa vitesse)
            wx, wy = v * ux, v * uy
            aa = wx * wx + wy * wy - q[2] * q[2]
            bb = 2 * (dx * wx + dy * wy)
            lead = 0.0
            if abs(aa) > 1e-6:
                disc = bb * bb - 4 * aa * dd * dd
                if disc >= 0:
                    r1, r2 = (-bb - math.sqrt(disc)) / (2 * aa), (-bb + math.sqrt(disc)) / (2 * aa)
                    lead = min([r for r in (r1, r2) if r > 0] or [0.0])
            lead = min(lead, P["anticipe"]) if lead > 0 else min(1.2, dd / (q[2] + 1e-6))
            tx, ty = px + wx * lead - q[0], py + wy * lead - q[1]
            tn = hypot(tx, ty) or 1.0
            s = min(q[2] * dt, dd)
            q[0] += tx / tn * s
            q[1] += ty / tn * s
        _pas()
        if plaque:
            break
    if px >= but:                                       # plaqué en tombant dans l'en-but : touchdown
        px, fin["td"], fin["plaqueur"] = but, True, None
    total = px
    k = math.floor(total)
    yards = int(k + (1 if rng.random() < total - k else 0))           # arrondi sans biais
    if fin["td"]:
        yards = int(math.ceil(but))
    return total, yards, fin, manques, chemin


# ---------------------------------------------------------------------------------------------------------------------
# Bloc 2 : la course après la réception (passe complétée)
# ---------------------------------------------------------------------------------------------------------------------
VERSION_RECEPTION = "reception-spatiale-1"

PARAMS_RECEPTION = dict(PARAMS, **{
    # calibrés le 06/11/2026 (semaine de test, puis réglage hors moteur sur les 12 819 réceptions d'une semaine
    # enregistrée) : distribution des yards par passe complétée de la ligue
    "p_contact": 0.918,        # le premier plaquage du défenseur qui couvrait le receveur
    "p_plaquage": 0.549,       # ligne, linebackers
    "p_arriere": 0.284,        # safeties et corners en terrain découvert
    "k_plaquage": 0.009,
    "renfort": 0.4,
    "gene": 0.746,
    "perte": 0.878,
    "chute": 0.077,
    "elan": 0.504,             # le receveur attrape en courant : cette part de sa vitesse maximale
    "pente": 0.016,            # la vitesse pèse surtout par l'écart qu'elle crée avant la réception (blocs A-C)
    "vit_defense": 0.988,
    "vit_arriere": 1.149,
    "anticipe": 2.27,
    "lecture": 0.753,          # les autres défenseurs ont lu le lancer : part du chemin vers le point de réception
    "lecture_max": 9.634,      # yards au plus pendant le vol du ballon
    "air_bruit": 0.054,        # yards : le point de réception autour de la profondeur de la route
    "ecart": 1.139,            # échelle de la séparation du bloc A au moment de la réception
    "dessus": (0.732, 9.345),  # yards : un safety reste au-dessus d'une route profonde (par rapport à la réception)
})

LARGEUR = 53.3
MILIEU = LARGEUR / 2
# position en travers du receveur au snap, selon son rôle ; décalage de la route à la réception
Y_ROLE = {"WR1": 8.0, "WR2": 45.3, "WR3": 17.0, "TE": 22.5, "RB": 28.0}
SENS_ROUTE = {"INSIDE": 1, "OUTSIDE": -1, "HORIZONTAL": 1, "VERTICAL": 0}


def point_reception(role, direction, decalage):
    """Position en travers à la réception : place du rôle, puis la route (vers le milieu, la touche ou à travers)."""
    y = Y_ROLE.get(role, MILIEU)
    vers_milieu = 1 if y < MILIEU else -1
    y += vers_milieu * SENS_ROUTE.get(direction or "", 0) * decalage
    return min(LARGEUR - 2.0, max(2.0, y))


def placer_reception(defenseurs, xc, yc, couvreur_id, sep, rng, P=PARAMS_RECEPTION):
    """Défenseurs au moment de la réception : [x, y, poste, notes, id]. Le défenseur qui couvrait est à `sep` yards
    (en retard, côté intérieur le plus souvent) ; la ligne a chargé le QB (derrière le jeu) ; les autres tenaient leur
    zone et ont lu le lancer (une part du chemin vers le ballon)."""
    out = []
    for d in defenseurs:
        pos, r, i = d.get("pos"), d.get("ratings") or {}, d.get("id")
        if i == couvreur_id:
            a = rng.uniform(0.0, 1.1)
            cote = 1 if yc < MILIEU else -1                 # il vient de l'intérieur
            if rng.random() < 0.3:
                cote = -cote
            x, y = xc - sep * math.cos(a), yc + cote * sep * math.sin(a)
            out.append([x, min(LARGEUR - 0.5, max(0.5, y)), pos, r, i])
            continue
        if pos in ("EDGE", "DT"):
            x, y = rng.uniform(-6.0, -1.0), MILIEU + rng.uniform(-6, 6)
        elif pos == "LB":
            x, y = rng.uniform(4.0, 9.0), MILIEU + rng.uniform(-12, 12)
        elif pos == "S":
            x, y = rng.uniform(10.0, 18.0), (rng.uniform(10, 22) if rng.random() < 0.5 else rng.uniform(31, 43))
            x = max(x, xc + rng.uniform(*P["dessus"]))
        else:
            x, y = rng.uniform(3.0, 12.0), (rng.uniform(4, 12) if rng.random() < 0.5 else rng.uniform(41, 49))
        if pos not in ("EDGE", "DT"):                       # il a lu le lancer : vers le point de réception
            dx, dy = xc - x, yc - y
            dd = math.hypot(dx, dy) or 1.0
            s = min(P["lecture"] * dd, P["lecture_max"])
            x, y = x + dx / dd * s, y + dy / dd * s
            dd = math.hypot(xc - x, yc - y)
            mini = max(1.2, sep + 0.5)                      # personne n'est plus près que celui qui couvrait
            if dd < mini:
                k = mini / (dd or 1.0)
                x, y = xc - (xc - x) * k, yc - (yc - y) * k
        out.append([x, min(LARGEUR - 0.5, max(0.5, y)), pos, r, i])
    return out


def apres_reception(receveur, defenseurs, air, t_pre, role, direction, decalage, couvreur_id, sep, but, graine, n,
                    params=PARAMS_RECEPTION, trace=False):
    """La course du receveur à partir de la réception.

    receveur   : {"pos", "ratings"} ; defenseurs : les onze ({"id", "pos", "ratings"})
    air        : profondeur de la route (yards depuis la ligne) ; t_pre : yards tirés avant ce bloc (table + blocs A-C)
    role, direction, decalage : rôle du receveur (WR1…RB), sens et longueur de la cassure de sa route (position en
                 travers) ; couvreur_id, sep : le défenseur qui couvrait et la séparation (yards) au lancer
    Renvoie {"version", "yards" (total, entier), "air" (point de réception), "apres", "plaqueur", "manques", "sortie",
             "td", "chemin" (si trace)}.
    """
    P = params
    rng = aleatoire.flux("reception-spatiale", graine, n)
    p = receveur.get("ratings") or {}
    vit, acc0 = p.get("speed", 80), p.get("acceleration", p.get("speed", 80))
    ag = p.get("elusiveness", p.get("route_running", 75))
    pu = p.get("power", 65 if receveur.get("pos") == "WR" else 75)
    xc = min(float(t_pre), float(air) + rng.uniform(-P["air_bruit"], P["air_bruit"]))
    yc = point_reception(role, direction, decalage)
    D = []
    for x, y, pos, r, i in placer_reception(defenseurs, xc, yc, couvreur_id, max(0.4, sep * P["ecart"]), rng, P):
        v = vitesse_max(r.get("speed", VITESSE_POSTE.get(pos, 75)), P["vit_arriere"] if pos in ("S", "CB") else P["vit_defense"],
                        P.get("pente", 0.075))
        v *= 0.9 + 0.002 * (r.get("run_support", r.get("tackling", 75)) - 70)
        base = P["p_arriere"] if pos in ("S", "CB") else P["p_plaquage"]
        D.append([x, y, v, r.get("tackling", 75), 0.0, i, P.get("p_contact", base) if i == couvreur_id else base, base])
    vmax, acc = vitesse_max(vit, P["vit_porteur"], P.get("pente", 0.075)), 3.0 + (acc0 - 60) * 0.08
    total, yards, fin, manques, chemin = _simuler(xc, yc, vmax * P.get("elan", 0.0), vmax, acc, ag, pu, xc, D, but, rng,
                                                 P, trace)
    return {"version": VERSION_RECEPTION, "yards": yards, "air": round(xc, 1), "apres": round(total - xc, 1),
            "plaqueur": fin["plaqueur"], "manques": manques, "sortie": fin["sortie"], "td": fin["td"],
            "chemin": chemin if trace else None, "trace": fin.get("trace") if trace else None}


def trace_compacte(r, depart_x=0.0, pas=2, rayon=5.0, dt=None):
    """Trace d'une simulation (apres_contact / apres_reception avec trace=True) pour le GameFeed : un point tous les
    `pas` pas de temps (0,2 s par défaut), arrondi au dixième ; seulement les défenseurs passés à moins de `rayon` yards
    du porteur ou qui ont tenté un plaquage. x depuis la ligne de mêlée, y en travers (0 à 53,3).
    Renvoie {"dt", "c": [[x, y], …], "d": [[id, [[x, y], …]], …], "ev": [[t, id, 1 réussi / 0 manqué], …]} ou None."""
    tr = r.get("trace") if isinstance(r, dict) else None
    if not tr or not tr.get("c"):
        return None
    dt = (dt or PARAMS["dt"]) * pas
    n = len(tr["c"])
    garde = list(range(0, n, pas))
    if garde[-1] != n - 1:
        garde.append(n - 1)
    rd = lambda p: [round(p[0], 1), round(p[1], 1)]
    c = [rd(tr["c"][k]) for k in garde]
    acteurs = {e[1] for e in tr["ev"]}
    d = []
    for i, pts in tr["d"].items():
        proche = any(math.hypot(pts[k][0] - tr["c"][k][0], pts[k][1] - tr["c"][k][1]) < rayon for k in range(min(len(pts), n)))
        if proche or i in acteurs:
            d.append([i, [rd(pts[min(k, len(pts) - 1)]) for k in garde]])
    return {"dt": round(dt, 2), "c": c, "d": d, "ev": [[e[0], e[1], e[2]] for e in tr["ev"]]}
