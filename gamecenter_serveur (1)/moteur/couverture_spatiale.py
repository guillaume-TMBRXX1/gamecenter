"""Causal léger, bloc 3 : la couverture, duel du receveur et de son défenseur pendant la route (06/11/2026).

Avant ce bloc, la séparation d'un receveur au moment où le QB le lit (bloc A, moteur/reaction_defensive.py) était un
écart de notes : (talent de route − talent de couverture) / 20, plus l'avantage de la route contre la couverture et un
bruit. Le terrain n'y était pour rien : un GO et un SLANT pesaient la vitesse de la même façon.

Ici, ce terme d'écart de notes vient d'un duel joué sur le terrain, au pas de DT secondes, jusqu'à l'instant où le QB
peut lire la route (« ouverture » de la route + le drop) :
  RECEVEUR  il court sa route (tige puis cassure, angle et sens propres à chaque route), à sa vitesse et avec son
            accélération ; à la cassure il perd de la vitesse, moins s'il court bien ses routes (route_running) ;
  HOMME     le défenseur assigné part à son coussin (presse en Cover 0 / 1, plus loin sinon), recule en miroir ; à la
            cassure il ne réagit qu'après un temps de réaction (sa couverture contre la qualité de route du receveur),
            puis le poursuit à sa vitesse ;
  ZONE      les défenseurs de la tranche que la route attaque tiennent leur point (profondeur de la zone) ; quand le
            receveur entre dans leur rayon, ils ferment sur lui après un temps de réaction ; la séparation est la
            distance au plus proche.
La séparation en yards est ramenée à l'échelle du bloc A (« pas ») par une droite par famille (homme / zone) et classe
de route (court / moyen / profond), calibrée pour que la ligue garde ses taux de receveurs libres, serrés et couverts
(outils/moteur/semaine_couverture_spatiale.py). Le hasard a son flux (« couverture-spatiale|<graine>|<action>|<rôle> ») :
le moteur n'en consomme pas plus qu'avant. ≈ 0,05 ms par receveur.
"""
import math

from . import aleatoire

VERSION = "couverture-spatiale-1"

DT = 0.05
LARGEUR = 53.3
MILIEU = LARGEUR / 2
DEPART = 0.15                  # le QB ne lit jamais une route avant son ouverture + le drop (moteur.decision_qb.DEPART)

PARAMS = {
    "coussin_presse": (0.8, 2.0),      # yards : Cover 0, Cover 1
    "coussin_off": (4.0, 7.0),         # yards : homme hors presse
    "recul": 0.85,                     # le défenseur recule moins vite qu'il ne court
    "reaction": 0.30,                  # s : temps de réaction à la cassure (notes égales)
    "k_reaction": 0.012,               # s par point (route_running − coverage)
    "reaction_min": 0.08,
    "perte_cassure": 0.45,             # part de la vitesse perdue à la cassure (route_running 70)
    "k_cassure": 0.006,                # par point de route_running au-delà de 70
    "rayon_zone": 7.0,                 # yards : un défenseur de zone ferme quand le receveur entre dans ce rayon
    "reaction_zone": 0.35,
    "presse_retard": 0.25,
    "hanches": 0.25,                   # s : le défenseur en recul se retourne pour courir
    "fenetre": 0.6,                    # s après la cassure : la fenêtre où le ballon arrive
    "cede": 0.6,                       # en recul, le défenseur cède du terrain à cette part du rythme du receveur
    "p_presse": 0.6,                   # Cover 0 / 1 : part des duels joués en presse
    "release": 0.8,                    # yards perdus par le défenseur au jam (notes égales)
    "k_release": 0.04,                 # par point (route_running − coverage)
    "devant": 0.6,                     # défenseur encore devant le receveur : part du coussin restant comptée
    "contact": 0.7,                    # yards : un défenseur de zone s'arrête à ce contact
    "devant_vertical": 0.15,           # défenseur au-dessus d'une route verticale : elle est couverte
    "k_lateral": 0.3,
    "laisse": 5.0,                     # yards : un défenseur de zone ne s'écarte pas plus de son repère
    "vitesse_zone": 0.7,               # part de sa vitesse quand il ferme dans sa zone                  # zone profonde : yards de séparation par yard d'écart à son repère             # s : le receveur pressé met ce temps à se libérer (release)
    # droite yards -> pas, par (famille, classe, groupe de rôle) : pas = a + b * yards. Calibrée le 06/11/2026 sur les
    # 83 430 duels d'une semaine (même moyenne et même dispersion que l'écart de notes d'avant, par groupe) :
    "droite": {
        ("homme", "court", "RB"): (-1.0336, 0.5041),
        ("homme", "court", "TE"): (-0.4665, 0.1313),
        ("homme", "court", "WR"): (-0.4881, 0.1985),
        ("homme", "moyen", "TE"): (-0.395, 0.215),
        ("homme", "moyen", "WR"): (-0.5926, 0.2696),
        ("homme", "profond", "RB"): (-1.6861, 1.4277),
        ("homme", "profond", "TE"): (-0.7664, 0.585),
        ("homme", "profond", "WR"): (-0.7571, 0.6173),
        ("zone", "court", "RB"): (-0.5924, 0.0517),
        ("zone", "court", "TE"): (-0.23, 0.07),
        ("zone", "court", "WR"): (-0.3402, 0.1763),
        ("zone", "moyen", "TE"): (-0.2043, 0.0855),
        ("zone", "moyen", "WR"): (-0.3024, 0.1021),
        ("zone", "profond", "RB"): (-1.1636, 0.0827),
        ("zone", "profond", "TE"): (-0.6872, 0.2759),
        ("zone", "profond", "WR"): (-0.3579, 0.1598),
    },
}

# route : (profondeur de la cassure, angle de la cassure en degrés depuis la verticale ; signe + vers le milieu,
# − vers la touche ; > 90 : retour vers le QB)
ROUTES = {
    "SCREEN": (0.0, -95.0), "QUICK_SLANT": (2.5, 45.0), "STICK": (5.0, 150.0), "FLAT": (1.0, -80.0),
    "SLANT": (4.0, 45.0), "DRAG": (4.0, 90.0), "OUT": (7.5, -90.0), "CURL": (10.0, 160.0), "IN": (10.0, 90.0),
    "CROSS": (4.5, 75.0), "FLAG": (10.0, -45.0), "SEAM": (60.0, 0.0), "DIG": (12.0, 90.0), "POST": (12.5, 37.5),
    "CORNER": (12.5, -37.5), "GO": (60.0, 0.0),
}
VERTICALES = {"GO", "SEAM", "POST", "CORNER", "FLAG"}
# départ du receveur (x depuis la ligne, y en travers) selon son rôle
DEPART_ROLE = {"WR1": (0.0, 8.0), "WR2": (0.0, 45.3), "WR3": (-1.0, 17.5), "TE": (0.0, 22.5), "RB": (-5.0, 26.0)}
# points des zones : profondeur selon la classe que la route attaque
PROFONDEUR_ZONE = {"court": (3.0, 6.0), "moyen": (7.0, 12.0), "profond": (13.0, 20.0)}
# repères en travers des zones (flats et hooks, curls, tiers profonds)
REPERES = {"court": (6.0, 18.0, 35.3, 47.3), "moyen": (12.0, 26.6, 41.3), "profond": (9.0, 26.6, 44.3)}


def _note(r, cle, defaut=75.0):
    return float((r or {}).get(cle, defaut))


def vitesse(note):
    """Note de vitesse -> yards par seconde (80 -> 8,5)."""
    return 8.5 + (note - 80.0) * 0.06


def chemin_receveur(role, route, t_fin, r):
    """Positions du receveur à chaque pas jusqu'à t_fin, et l'instant de sa cassure. r : notes du receveur."""
    x, y = DEPART_ROLE.get(role, (0.0, MILIEU))
    prof, angle = ROUTES.get(route, (8.0, 45.0))
    vers_milieu = 1.0 if y < MILIEU else -1.0
    vmax = vitesse(_note(r, "speed"))
    acc = 3.5 + (_note(r, "acceleration", _note(r, "speed")) - 60) * 0.08
    rr = _note(r, "route_running", 70.0)
    v, t, out, casse, t_casse = 0.0, 0.0, [], False, None
    ux, uy = 1.0, 0.0
    if route == "SCREEN":
        a = math.radians(angle)
        ux, uy = math.cos(a), vers_milieu * math.sin(a)
        casse, t_casse = True, 0.0
    while t < t_fin - 1e-9:
        t += DT
        v = min(vmax, v + acc * DT)
        x += v * ux * DT
        y += v * uy * DT
        if not casse and x >= prof:
            casse, t_casse = True, t
            a = math.radians(angle)
            ux, uy = math.cos(a), vers_milieu * math.sin(a)
            perte = max(0.1, PARAMS["perte_cassure"] - (rr - 70) * PARAMS["k_cassure"]) * min(1.0, abs(angle) / 90.0)
            v *= 1.0 - perte
        y = min(LARGEUR - 0.5, max(0.5, y))
        out.append((x, y))
    return out, t_casse


def _point(chemin, s_cum, s):
    """Point du chemin du receveur à l'abscisse curviligne s."""
    if s <= 0 or not chemin:
        return chemin[0] if chemin else (0.0, MILIEU)
    for k in range(1, len(s_cum)):
        if s_cum[k] >= s:
            f = (s - s_cum[k - 1]) / max(1e-9, s_cum[k] - s_cum[k - 1])
            (x0, y0), (x1, y1) = chemin[k - 1], chemin[k]
            return x0 + f * (x1 - x0), y0 + f * (y1 - y0)
    return chemin[-1]


def separation(role, route, classe, ouverture, receveur, defenseurs, famille, couverture, graine, n, params=PARAMS):
    """Séparation (yards) du receveur dans sa fenêtre : à la cassure + FENETRE s (route qui casse), sinon quand le QB
    peut le lire (ouverture de la route + drop).

    receveur   : {"ratings"} ; defenseurs : en homme, [le défenseur assigné] ; en zone, ceux de la tranche
    Renvoie (yards, détail) — détail : {"t", "casse"}.
    """
    P = params
    rng = aleatoire.flux("couverture-spatiale", graine, f"{n}|{role}")
    r = (receveur or {}).get("ratings") or {}
    rr = _note(r, "route_running", 70.0)
    t_lire = max(0.4, float(ouverture) + DEPART)
    x0, y0 = DEPART_ROLE.get(role, (0.0, MILIEU))
    depart = [(x0, y0)]
    chemin, t_casse = chemin_receveur(role, route, 6.0, r)
    chemin = depart + chemin
    t_fin = t_lire if (t_casse is None or t_casse <= 0) else min(6.0, max(t_lire * 0.8, t_casse + P["fenetre"]))
    k_fin = max(1, min(len(chemin) - 1, int(round(t_fin / DT))))
    s_cum = [0.0]
    for k in range(1, len(chemin)):
        s_cum.append(s_cum[-1] + math.hypot(chemin[k][0] - chemin[k - 1][0], chemin[k][1] - chemin[k - 1][1]))
    rx, ry = chemin[k_fin]
    vertical = route in VERTICALES
    if famille == "homme" or classe == "profond":
        if famille == "homme":
            d = (defenseurs or [None])[0] or {}
            presse = couverture in ("Cover 0", "Cover 1") and rng.random() < P["p_presse"]
            coussin = rng.uniform(*(P["coussin_presse"] if presse else P["coussin_off"]))
            lateral = 0.0
            reac0 = P["reaction"]
        else:                                            # zone profonde : le safety de la tranche le prend par-dessus
            reperes = REPERES["profond"]
            ds = defenseurs or [{}]
            i = min(range(len(ds)), key=lambda j: abs(reperes[j % len(reperes)] - ry))
            d = ds[i]
            presse = False
            coussin = rng.uniform(*PROFONDEUR_ZONE["profond"]) - x0
            lateral = max(0.0, abs(reperes[i % len(reperes)] + rng.uniform(-2.5, 2.5) - ry) - P["rayon_zone"]) * P["k_lateral"]
            reac0 = P["reaction_zone"]
        dr = d.get("ratings") or {}
        cov = _note(dr, "coverage", 75.0)
        vd = vitesse(_note(dr, "speed", 82))
        # en 2D, par phases : recul (ou course après s'être retourné) le long de la ligne du receveur ; à la cassure, il
        # garde son mouvement le temps de réagir ; ensuite il fonce sur le receveur (jusqu'au contact)
        dx, dy = x0 + coussin, y0
        if presse:                                       # au jam : le meilleur des deux gagne le release
            dx = x0 + coussin - max(0.0, P["release"] + (rr - cov) * P["k_release"] + rng.gauss(0, 0.4))
        reac = max(P["reaction_min"], reac0 + (rr - cov) * P["k_reaction"] + rng.gauss(0, 0.06))
        retourne, gel, vx_d = presse, 0.0, 1.0           # vx_d : sens de son mouvement le long de la tige (+ : vers le fond)
        t_reagit = (t_casse + reac) if (t_casse is not None and t_casse > 0) else None
        if t_casse is not None and t_casse <= 0:          # écran : il réagit au snap
            t_reagit = reac
        for k in range(1, k_fin + 1):
            t = k * DT
            px, py = chemin[k]
            if t_reagit is not None and t >= t_reagit:   # il a lu la cassure : il fonce sur le receveur
                ex, ey = px - dx, py - dy
                e = math.hypot(ex, ey)
                st = min(vd * DT, max(0.0, e - P["contact"]))
                if e > 1e-9:
                    dx, dy = dx + ex / e * st, dy + ey / e * st
                continue
            if not retourne and dx - px <= 1.0:          # le receveur arrive sur lui : il se retourne
                retourne, gel = True, P["hanches"]
            if gel > 0:
                gel -= DT
                continue
            v = vd if retourne else vd * P["recul"]
            if retourne:                                 # il court avec lui, sans le dépasser (jusqu'au contact)
                cible = px - P["contact"] if t_casse is None or t < t_casse else dx + v * DT
                dx = min(dx + v * DT, max(dx, cible))
            else:                                        # recul : il cède du terrain à une part du rythme du receveur
                vr_x = (chemin[k][0] - chemin[k - 1][0]) / DT if t_casse is None or t < t_casse else P["cede"] * v
                dx += min(v, max(0.0, P["cede"] * vr_x)) * DT
            dy += max(-v * DT, min(v * DT, (py if (t_casse is None or t < t_casse) else dy) - dy))
        if dx > rx + 0.5 and vertical:                   # au-dessus d'une route verticale : elle est couverte
            sep = (dx - rx) * P["devant_vertical"] + abs(dy - ry) * 0.5
        else:
            sep = math.hypot(rx - dx, ry - dy)
        return sep + lateral, {"t": round(t_fin, 2), "casse": t_casse}
    # zone : chaque défenseur de la tranche tient un point (repères fixes du terrain), ferme quand le receveur entre dans
    # son rayon ; la séparation est la distance au plus proche dans la fenêtre
    a, b = PROFONDEUR_ZONE.get(classe, PROFONDEUR_ZONE["moyen"])
    reperes = REPERES.get(classe, REPERES["moyen"])
    zs = []
    for i, d in enumerate(defenseurs or [{}]):
        dr = d.get("ratings") or {}
        zy = reperes[i % len(reperes)] + rng.uniform(-2.5, 2.5)
        zx = rng.uniform(a, b)
        zs.append([zx, zy, vitesse(_note(dr, "speed", 82)) * P["vitesse_zone"],
                   max(P["reaction_min"], P["reaction_zone"] - (_note(dr, "coverage", 75) - 75) * P["k_reaction"]
                       + (rr - 75) * P["k_reaction"] * 0.5), None, zx, zy])
    for k in range(1, k_fin + 1):
        t = k * DT
        px, py = chemin[k]
        for z in zs:
            if z[4] is None and math.hypot(px - z[0], py - z[1]) < P["rayon_zone"]:
                z[4] = t                              # il voit le receveur entrer
            if z[4] is not None and t >= z[4] + z[3]:
                ex, ey = px - z[0], py - z[1]
                e = math.hypot(ex, ey)
                st = min(z[2] * DT, max(0.0, e - P["contact"]))
                if e > 1e-9:
                    nx, ny = z[0] + ex / e * st, z[1] + ey / e * st
                    lx, ly = nx - z[5], ny - z[6]
                    ll = math.hypot(lx, ly)
                    if ll > P["laisse"]:                 # il ne quitte pas sa zone
                        nx, ny = z[5] + lx / ll * P["laisse"], z[6] + ly / ll * P["laisse"]
                    z[0], z[1] = nx, ny
    return min(math.hypot(rx - z[0], ry - z[1]) for z in zs), {"t": round(t_fin, 2), "casse": t_casse}


GROUPE = {"RB": "RB", "TE": "TE"}                 # les autres rôles : WR


def en_pas(yards, famille, classe, role=None, params=PARAMS):
    """Séparation en yards -> terme de duel du bloc A (« pas ») : droite par famille, classe de route et groupe de rôle
    (RB, TE, WR : chaque groupe garde son niveau moyen du bloc A, le duel décide des écarts entre joueurs)."""
    D = params["droite"]
    a, b = D.get((famille, classe, GROUPE.get(role, "WR"))) or D.get((famille, classe, "WR")) or (-0.4, 0.15)
    return a + b * yards
