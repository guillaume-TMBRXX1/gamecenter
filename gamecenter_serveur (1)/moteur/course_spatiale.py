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
    "dt": 0.1,                 # pas de temps (s)
    "t_max": 8.0,              # durée maximale après le contact
    "rayon": 1.0,              # yards : distance de plaquage
    "evitement": 6.0,          # yards : distance à laquelle le porteur évite un défenseur
    "p_plaquage": 0.62,        # réussite d'un plaquage à notes égales
    "k_plaquage": 0.012,       # par point (tackling − max(agilité, puissance) du porteur)
    "gene": 0.6,               # secondes de gêne après un plaquage manqué
    "chute": 0.6,              # yards gagnés en tombant (moyenne, + puissance)
    "k_chute": 0.03,           # par point de puissance au-delà de 70
    "vit_porteur": 1.0,        # échelle de vitesse du porteur
    "vit_defense": 1.0,        # échelle de vitesse des défenseurs
    "perte": 0.55,             # plaquage cassé : le porteur garde cette part de sa vitesse (il perd son élan)
    "renfort": 0.10,           # réussite du plaquage en plus par autre défenseur à moins de 2,5 yards
    "pousse": 1.0,             # yards de poussée au premier contact (il encaisse le choc et avance), + puissance
    "vit_arriere": 1.0,        # échelle de vitesse des safeties et corners (angles de poursuite en profondeur)
    # profondeur du contact (yards depuis la ligne) selon le niveau du bloc F : uniforme [a, b]
    "profondeur": {"ligne": (-0.5, 1.5), "linebacker": (2.0, 5.0), "second rideau": (6.0, 10.0)},
}

# vitesse par défaut des postes sans note de vitesse (ligne défensive)
VITESSE_POSTE = {"EDGE": 76, "DT": 66, "LB": 80, "S": 84, "CB": 86}


def vitesse_max(note, echelle=1.0):
    """Note de vitesse 60-99 -> 7,0 à 9,9 yards par seconde."""
    return (7.0 + (note - 60) * 0.075) * echelle


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
    dep = profondeur_contact(t_pre, niveau, rng, P)
    D = []
    for x, y, pos, r, i in placer(defenseurs, niveau, dep, y0, plaqueur_id, rng):
        v = vitesse_max(r.get("speed", VITESSE_POSTE.get(pos, 75)), P["vit_arriere"] if pos in ("S", "CB") else P["vit_defense"])
        v *= 0.9 + 0.002 * (r.get("run_support", r.get("tackling", 75)) - 70)
        D.append([x, y, v, r.get("tackling", 75), 0.0, i])                 # x, y, vitesse, tackling, gêne, id
    if dep >= float(t_pre) - 1e-9 and t_pre <= 0:
        pass                                            # course stoppée derrière la ligne : pas de poussée
    else:
        dep += max(0.0, rng.gauss(P["pousse"] + (pu - 70) * P["k_chute"], 0.6))   # il encaisse le premier choc et avance
    px, py = dep, y0
    vmax, acc = vitesse_max(vit, P["vit_porteur"]), 3.0 + (acc0 - 60) * 0.08
    v, t, manques, chemin = 0.0, 0.0, 0, []
    dt, ev, rayon = P["dt"], P["evitement"], P["rayon"]
    hypot = math.hypot
    fin = {"plaqueur": None, "sortie": False, "td": False}
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
        v = min(vmax, v + acc * dt)
        ux, uy = ax / nn, ay / nn
        px += v * ux * dt
        py += v * uy * dt
        if trace:
            chemin.append((round(px, 1), round(py, 1)))
        if py < 0.3 or py > 53.0:
            fin["sortie"] = True
            break
        if px >= but:
            px, fin["td"] = but, True
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
                if rng.random() < P["p_plaquage"] + (q[3] - max(ag, pu)) * P["k_plaquage"] + aide * P["renfort"]:
                    px += max(0.0, rng.gauss(P["chute"] + (pu - 70) * P["k_chute"], 0.5))
                    fin["plaqueur"] = q[5]
                    plaque = True
                    break
                manques += 1
                q[4] = P["gene"]
                v *= P["perte"]                         # il casse le plaquage mais perd son élan
                continue
            lead = min(1.2, dd / (q[2] + 1e-6))         # angle de poursuite : vers le point d'interception
            tx, ty = px + v * ux * lead - q[0], py + v * uy * lead - q[1]
            tn = hypot(tx, ty) or 1.0
            s = min(q[2] * dt, dd)
            q[0] += tx / tn * s
            q[1] += ty / tn * s
        if plaque:
            break
    if px >= but:                                       # plaqué en tombant dans l'en-but : touchdown
        px, fin["td"], fin["plaqueur"] = but, True, None
    total = px
    k = math.floor(total)
    yards = int(k + (1 if rng.random() < total - k else 0))           # arrondi sans biais
    if fin["td"]:
        yards = int(math.ceil(but))
    return {"version": VERSION, "yards": yards, "contact": round(dep, 1), "apres": round(total - dep, 1),
            "plaqueur": fin["plaqueur"], "manques": manques, "sortie": fin["sortie"], "td": fin["td"],
            "chemin": chemin if trace else None}
