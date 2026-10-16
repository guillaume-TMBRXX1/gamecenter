"""Horloge réelle : le temps qui s'écoule ENTRE deux actions, temps morts, avertissement des 2 minutes, genou, spike.

Constat (semaine du 12/10/2026, 279 matchs) : le moteur n'écoule l'horloge que pendant les actions (3 à 8 s) ; entre
deux snaps, 0 s. Conséquences : « tuer l'horloge » ne tue presque rien (une équipe qui mène dans la dernière minute passe
encore 53 % du temps), les temps morts ne servent à rien, personne ne pose le genou, et des quarts-temps de 3 minutes
suffisent pour ≈ 130 actions offensives par match (le compte d'un vrai match NFL).

Ce module décide, après chaque action, combien de temps passe avant le snap suivant :
  - l'horloge S'ARRÊTE : passe incomplète, changement de possession (score, perte de balle, punt, field goal, 4e essai
    manqué), sortie du terrain dans les 2 dernières minutes du Q2 et les 5 dernières du Q4, avertissement des 2 minutes
    (Q2, Q4), temps mort ; spike (l'action suivante part horloge arrêtée) ;
  - sinon elle TOURNE : temps de huddle et d'horloge de jeu selon le TEMPO de l'attaque (normal, hurry-up, tuer
    l'horloge) et l'identité du coordinateur (`tempo`) ; une sortie du terrain hors des fins de mi-temps n'arrête
    l'horloge qu'un moment (elle repart au signal de l'arbitre) ;
  - TEMPS MORTS (3 par mi-temps, 2 en prolongation) : l'équipe menée en fin de match les pose pour arrêter l'horloge
    (en défense contre une attaque qui la fait tourner, en attaque pendant son drive) ; en fin de Q2, l'attaque qui a le
    temps de marquer aussi ;
  - GENOU (victory formation) : l'équipe qui mène pose le genou quand les genoux qui lui restent avant le 4e essai
    écoulent tout le temps, même si la défense pose ses temps morts ; en fin de Q2, dans son camp, quand il ne reste
    presque rien ;
  - SPIKE : l'attaque qui court après le temps, sans temps mort, arrête l'horloge en sacrifiant un essai (1er essai,
    dernière minute) ; FIRE DRILL : à portée de field goal, quand 3 points comptent et que l'horloge allait s'écouler,
    l'unité de field goal entre en courant et tire avec 3 s au chrono.

Échelle : les durées sont celles d'un vrai match (quart de 900 s) ; `echelle = quart_secondes / 900` les ramène à la
longueur de quart-temps du moteur (180 s aujourd'hui : × 0,2). Les durées d'action (3-8 s, moteur) ne changent pas.
Tirages (sortie du terrain) dans le flux dédié « horloge|<graine>|<n° d'action> » : le hasard du moteur n'est jamais
consommé. Tout le reste est déterministe.
"""
from . import aleatoire

VERSION = "horloge-1"

QUART_NFL = 900                # secondes d'un vrai quart-temps : les durées ci-dessous sont à cette échelle
AVERTISSEMENT = 120            # avertissement des 2 minutes (Q2, Q4)
SORTIE_ARRET_Q2 = 120          # sortie du terrain : l'horloge reste arrêtée jusqu'au snap (2 dernières min du Q2…)
SORTIE_ARRET_Q4 = 300          # … et 5 dernières du Q4 ; ailleurs, elle repart au signal de l'arbitre
TEMPS_MORTS = 3                # par mi-temps
TEMPS_MORTS_PROLONGATION = 2

# temps entre la fin d'une action et le snap suivant, horloge qui tourne (s, échelle NFL)
# normal 36 s : calibré pour garder le nombre d'actions du moteur sans horloge (≈ 131 actions offensives, retransmission
# ≈ 18 min) avec des quarts-temps de 15 min — mesuré sur 552 matchs (README, « Horloge réelle »)
ENTRE = {"normal": 36, "hurry": 16, "clock": 40}
ENTRE_MAX = 40                 # horloge de jeu : 40 s (genou : la défense ne peut rien sans temps mort)
# format TEMPS RÉEL (15/10/2026, Guillaume : quarts-temps de 4 min joués en temps réel, chrono d'avant-snap de 10 s au
# plus) : quart-temps de QUART_TEMPS_REEL s ou moins -> le temps entre deux actions est lu en secondes de chrono
# d'avant-snap (AVANT_SNAP_REEL s) au lieu d'être ramené à l'échelle. 16/10/2026 (Guillaume) : secondes RESTANTES au snap
# — ≈ 7 en situation classique, 8, 9 ou 10 en hurry-up (no huddle), 0 ou 1 pour tuer l'horloge : secondes UTILISÉES
# tirées dans le flux « chrono » (CHRONO_UTILISE ; 15/10 : 9 / 4 / 10 fixes)
QUART_TEMPS_REEL = 300
AVANT_SNAP_REEL = 10
CHRONO_UTILISE = {"normal": (2, 3, 3, 4), "hurry": (0, 1, 2), "clock": (9, 10)}
TEMPO_PAR_POINT = 3            # identité : `tempo` du coordinateur (−1 rapide … +1 lent) -> ± 3 s
SORTIE_ARRETE_TOUJOURS = True  # 15/10/2026 (Guillaume) : une sortie du terrain arrête toujours l'horloge
REPART_SORTIE = 0.45           # sortie du terrain hors fin de mi-temps : part du temps normal qui s'écoule encore
DUREE_GENOU = 2                # secondes d'un genou
DUREE_SPIKE = 1                # secondes d'un spike

# probabilité qu'une action finisse hors du terrain (course / passe complétée) ; + PRESSE_SORTIE en hurry-up
# (routes vers la touche, porteur qui sort volontairement)
# 16/10/2026 (Guillaume) : seulement une passe vers un receveur extérieur (WR1 / WR2, sauf route vers l'intérieur) ou une
# route vers l'extérieur, et une course vers l'extérieur (sweep, toss, outside zone) — jamais un receveur attrapé au
# milieu du terrain qui pique à 90° vers la touche ; ces actions-là sortent plus souvent
SORTIE = {"RUN": 0.30, "PASS": 0.40}
COURSES_EXTERIEURES = ("OUTSIDE_RUN", "POWER_TOSS", "COUNTER_SWEEP", "JET_SWEEP", "TOSS", "SWEEP", "STRETCH",
                       "OUTSIDE_ZONE", "END_AROUND", "REVERSE", "SPEED_OPTION", "PITCH")
SORTIE_PRESSE = 0.14
# une course ne sort que si le porteur a eu le temps d'aller jusqu'à la touche (≈ 20 yards depuis la hash mark) :
# un gain d'au moins SORTIE_GAIN yards (rebond du bloc F : SORTIE_GAIN_REBOND) ; jamais un cutback (il rentre)
SORTIE_GAIN, SORTIE_GAIN_REBOND = 3, 2

# fenêtres de fin de match (s, échelle NFL)
FIN_MATCH = 150                # Q4 : l'équipe menée pose ses temps morts dans les 2:30 dernières
ECART_MAX = 16                 # … si elle est à deux possessions au plus
FIN_Q2 = 120                   # Q2 : l'attaque qui peut marquer pose ses temps morts dans les 2 dernières minutes
EN_BUT_Q2 = 65                 # … si elle est à 65 yards de l'en-but au plus
SPIKE_FIN = 60                 # spike dans la dernière minute
GENOU_Q2 = 40                  # Q2 : genou dans son camp quand il reste moins de 40 s
GENOU_Q2_EN_BUT = 60           # … à 60 yards de l'en-but au moins
GENOU_EGALITE = 20             # Q4 à égalité, dans son camp, moins de 20 s : genou (le nul ou la prolongation) plutôt
GENOU_EGALITE_EN_BUT = 60      # qu'une action désespérée ou un field goal hors de portée (14/10/2026)
FEU = 18                       # « fire drill » : sans temps mort, l'unité de field goal entre en courant si l'horloge
RESTE_FEU = 3                  # allait s'écouler (au moins 18 s) ; elle tire avec 3 s au chrono
EN_BUT_FG = 47                 # à portée : field goal de 64 yards au plus (fin_de_periode.DISTANCE_MAX)


def echelle(quart_secondes):
    """Facteur des durées « NFL » pour un quart-temps de `quart_secondes` (180 s -> 0,2)."""
    return float(quart_secondes) / QUART_NFL


def _s(x, k):
    """Durée NFL `x` à l'échelle `k`, en secondes entières (au moins 1 si x > 0)."""
    return 0 if x <= 0 else max(1, int(round(x * k)))


class EtatHorloge:
    """État de l'horloge d'un match : temps morts de chaque équipe, horloge arrêtée ou non avant le snap suivant."""

    def __init__(self, equipes, quart_secondes):
        self.k = echelle(quart_secondes)
        self.quart_secondes = int(quart_secondes)
        self.equipes = tuple(equipes)
        self.mi_temps = 1
        self.temps_morts = {e: TEMPS_MORTS for e in self.equipes}
        self.arretee = True                  # coup d'envoi : l'horloge part au snap
        self.journal = []                    # (n° d'action, équipe, raison) des temps morts

    def mi_temps_de(self, quart):
        return 1 if quart <= 2 else 2 if quart <= 4 else 3

    def suivre(self, quart):
        """Nouvelle mi-temps (ou prolongation) : temps morts remis à 3 (2 en prolongation)."""
        m = self.mi_temps_de(quart)
        if m != self.mi_temps:
            self.mi_temps = m
            n = TEMPS_MORTS if m <= 2 else TEMPS_MORTS_PROLONGATION
            self.temps_morts = {e: n for e in self.equipes}
            self.arretee = True

    def to_dict(self):
        return {"temps_morts": dict(self.temps_morts), "arretee": self.arretee, "mi_temps": self.mi_temps}


def veut_arreter(equipe_attaque, attaque, quart, secondes, ecart_attaque, en_but, k):
    """L'équipe `attaque` (True : l'attaque, False : la défense) veut-elle arrêter l'horloge ?

    ecart_attaque : points de l'attaque − points de la défense ; en_but : yards de l'attaque jusqu'à l'en-but.
    """
    ecart = ecart_attaque if attaque else -ecart_attaque          # du point de vue de l'équipe
    if quart == 4 or quart >= 5:
        if secondes > _s(FIN_MATCH, k):
            return False
        if attaque:
            return ecart <= 0 and ecart >= -ECART_MAX - 8                 # menée ou à égalité : le temps de marquer
        return ecart < 0 and ecart >= -ECART_MAX                          # défense menée : récupérer le ballon à temps
    if quart == 2 and attaque:
        return secondes <= _s(FIN_Q2, k) and en_but <= EN_BUT_Q2
    return False


def genou(quart, secondes, essai, ecart_attaque, en_but, temps_morts_defense, k, duree_action=5):
    """L'attaque pose-t-elle le genou ? (victory formation, ou fin de Q2 dans son camp)."""
    if secondes <= 0:
        return False
    if (quart == 4 and ecart_attaque == 0 and essai < 4 and en_but >= GENOU_EGALITE_EN_BUT
            and secondes <= _s(GENOU_EGALITE, k)):
        return True                                            # égalité, loin de l'en-but, quelques secondes
    if ecart_attaque <= 0 and quart != 2:
        return False
    if quart == 4 or quart >= 5:
        if quart >= 5:
            return False                                       # prolongation : il faut marquer
        n = 4 - essai                                          # genoux avant le 4e essai
        if n <= 0:
            return False
        stops = min(n, temps_morts_defense)
        capacite = n * DUREE_GENOU + (n - stops) * _s(ENTRE_MAX, k)
        return secondes <= capacite
    if quart == 2:
        if essai == 4 and secondes > DUREE_GENOU:
            return False                                       # au 4e essai, un genou rendrait le ballon : punt
        return ecart_attaque >= -3 and en_but >= GENOU_Q2_EN_BUT and secondes <= max(_s(GENOU_Q2, k), duree_action)
    return False


def spike(quart, secondes, essai, ecart_attaque, en_but, horloge_arretee, temps_morts_attaque, k):
    """L'attaque arrête-t-elle l'horloge par un spike (1er essai, dernière minute, sans temps mort) ?"""
    if horloge_arretee or temps_morts_attaque > 0 or essai != 1:
        return False
    if secondes > _s(SPIKE_FIN, k) or secondes <= DUREE_SPIKE + 1:
        return False
    if quart == 4:
        return -ECART_MAX <= ecart_attaque <= 0
    if quart == 2:
        return en_but <= EN_BUT_Q2
    return False


def avant_snap(etat, quart, secondes, essai, ecart_attaque, en_but, attaque, defense):
    """Décision avant le snap : "KNEEL", "SPIKE" ou None (jeu normal)."""
    etat.suivre(quart)
    if genou(quart, secondes, essai, ecart_attaque, en_but, etat.temps_morts.get(defense, 0), etat.k):
        return "KNEEL"
    if spike(quart, secondes, essai, ecart_attaque, en_but, etat.arretee, etat.temps_morts.get(attaque, 0), etat.k):
        return "SPIKE"
    return None


def continue_drive(action):
    """L'attaque garde-t-elle le ballon après cette action ? (sinon l'horloge s'arrête : changement de possession)."""
    if action.get("kind") != "OFF":
        return False
    out = action.get("outcome")
    if out in ("INTERCEPTION", "FUMBLE", "FUMBLE_LOST", "TOUCHDOWN") or action.get("fumble"):
        return False
    y, yl = int(action.get("yards_gained") or 0), int(action.get("yard_line") or 0)
    if y >= 100 - yl or y <= -yl:                             # touchdown, safety
        return False
    if action.get("down") == 4 and y < int(action.get("distance") or 0):
        return False                                          # 4e essai manqué
    return True


def vers_la_touche(action):
    """L'action peut-elle finir hors du terrain ? Passe vers un receveur extérieur (WR1 / WR2) sur une route qui ne
    rentre pas, ou route vers l'extérieur ; course vers l'extérieur (concept, ou rebond du bloc F) avec assez de gain
    pour atteindre la touche (16/10/2026 : une course bloquée à la ligne ne « sortait » plus 25 yards plus loin)."""
    if action.get("play_type") == "PASS":
        d = action.get("route_direction")
        if d == "OUTSIDE":
            return True
        cle = str(action.get("carrier_id") or "").rsplit("_", 1)[-1]
        return cle in ("WR1", "WR2") and d in ("VERTICAL", None) and action.get("play_concept") != "SCREEN"
    if action.get("play_type") == "RUN":
        r = action.get("run") or {}
        if r.get("read") == "cutback":
            return False
        gain = int(action.get("yards_gained") or 0)
        if r.get("read") == "bounce":
            return gain >= SORTIE_GAIN_REBOND
        return action.get("play_concept") in COURSES_EXTERIEURES and gain >= SORTIE_GAIN
    return False


def apres_action(etat, action, secondes_apres, ecart_attaque, mode=None, tempo=0, graine=None, numero=0,
                 secondes_avant=None):
    """Temps qui s'écoule entre la fin de `action` et le snap suivant.

    action        : entrée du journal du moteur (kind, play_type, outcome, yards_gained, down, distance, yard_line,
                    quarter, offense, defense) ; `play_id` "KNEEL" / "SPIKE" pour un genou / un spike
    secondes_apres: secondes restantes dans le quart-temps à la fin de l'action (avant ce temps-là)
    ecart_attaque : points de l'attaque − points de la défense (avant l'action)
    mode          : tempo de l'attaque pour le snap suivant (None / "hurry" / "clock", V21) ; tempo : identité (−1…+1)
    secondes_avant: secondes restantes au snap de l'action (avertissement des 2 minutes)
    Renvoie {"runoff": s, "stop": raison ou None, "timeout": équipe ou None, "oob": bool}.
    """
    k = etat.k
    q = int(action.get("quarter") or 1)
    etat.suivre(q)
    att, dfn = action.get("offense"), action.get("defense")
    res = {"runoff": 0, "stop": None, "timeout": None, "oob": False}
    if secondes_apres <= 0:
        etat.arretee = True
        res["stop"] = "fin du quart-temps"
        return res
    pid = action.get("play_id")
    if pid == "SPIKE":
        etat.arretee, res["stop"] = True, "spike"
        return res
    if not continue_drive(action):
        etat.arretee, res["stop"] = True, "changement de possession"
        return res
    if action.get("play_type") == "PASS" and action.get("outcome") == "PASS_INCOMPLETE":
        etat.arretee, res["stop"] = True, "passe incomplète"
        return res
    # avertissement des 2 minutes : à la première interruption après 2:00 (ici : l'action qui passe sous 2:00)
    w = _s(AVERTISSEMENT, k)
    avertissement = q in (2, 4) and secondes_avant is not None and secondes_avant > w >= secondes_apres
    if avertissement:
        etat.arretee, res["stop"] = True, "avertissement des 2 minutes"
        return res
    # sortie du terrain (course, passe complétée, scramble) : flux dédié
    reel = etat.quart_secondes <= QUART_TEMPS_REEL
    if reel:
        c = aleatoire.flux("chrono", graine, numero)
        entre = c.choice(CHRONO_UTILISE.get(mode or "normal", CHRONO_UTILISE["normal"]))
        if mode not in ("hurry", "clock"):
            entre += round(float(tempo or 0))                   # identité : −1 rapide … +1 lent
    else:
        entre = ENTRE.get(mode or "normal", ENTRE["normal"])
        if mode not in ("hurry", "clock"):
            entre += TEMPO_PAR_POINT * float(tempo or 0)
    if pid == "KNEEL":
        entre = AVANT_SNAP_REEL if reel else ENTRE_MAX
    elif action.get("outcome") in ("RUN", "PASS_COMPLETE"):
        rng = aleatoire.flux("horloge", graine, numero)
        p = SORTIE.get(action.get("play_type"), 0.1) + (SORTIE_PRESSE if mode == "hurry" else 0.0)
        if not vers_la_touche(action):
            p = 0.0
        if mode == "clock":
            p *= 0.3                                          # le porteur reste dans le terrain
        if rng.random() < p:
            res["oob"] = True
            fin_mi_temps = (q == 2 and secondes_apres <= _s(SORTIE_ARRET_Q2, k)) or \
                           (q >= 4 and secondes_apres <= _s(SORTIE_ARRET_Q4, k))
            if fin_mi_temps or SORTIE_ARRETE_TOUJOURS:
                etat.arretee, res["stop"] = True, "sortie du terrain"
                return res
            entre *= REPART_SORTIE
    # au plus le chrono d'avant-snap (40 s à l'échelle ; temps réel : 10 s)
    runoff = max(0, min(int(round(entre)), AVANT_SNAP_REEL)) if reel else min(_s(entre, k), int(ENTRE_MAX * k))
    # l'horloge passe sous 2:00 pendant le huddle : elle s'arrête à 2:00
    if q in (2, 4) and secondes_apres > w and secondes_apres - runoff < w:
        res.update(runoff=secondes_apres - w, stop="avertissement des 2 minutes")
        etat.arretee = True
        return res
    # temps mort : l'équipe qui veut arrêter l'horloge et en a encore
    en_but = 100 - (int(action.get("yard_line") or 0) + int(action.get("yards_gained") or 0))
    for equipe, cote_attaque in ((dfn, False), (att, True)):
        if etat.temps_morts.get(equipe, 0) > 0 and runoff > 0 and \
                veut_arreter(att, cote_attaque, q, secondes_apres, ecart_attaque, en_but, k):
            etat.temps_morts[equipe] -= 1
            etat.journal.append((numero, equipe, "attaque" if cote_attaque else "défense"))
            res.update(runoff=0, stop="temps mort", timeout=equipe)
            etat.arretee = True
            return res
    # fire drill : l'horloge allait s'écouler avec l'attaque à portée, quand 3 points comptent
    if runoff >= secondes_apres > _s(FEU, k) and en_but <= EN_BUT_FG and veut_les_points(q, ecart_attaque):
        res.update(runoff=secondes_apres - _s(RESTE_FEU, k), stop="unité de field goal")
        etat.arretee = True
        return res
    res["runoff"] = min(runoff, secondes_apres)
    etat.arretee = False
    return res


def veut_les_points(quart, ecart_attaque):
    """Un field goal sur la dernière action compte-t-il ? (Q2 : toujours ; Q4 et prolongation : égalité ou menée de 3)."""
    if quart == 2:
        return True
    return quart >= 4 and -3 <= ecart_attaque <= 0


def secondes_equivalentes(secondes, k, action_moyenne=5.4, entre_moyen=None):
    """Secondes « du moteur sans horloge » équivalentes à `secondes` réelles (même nombre d'actions restantes).

    Les réglages en secondes de V21 (hurry-up, tuer l'horloge, prevent) et de la fin de période ont été mesurés quand
    une action prenait 5,4 s d'horloge ; avec le temps entre les actions, chaque snap en prend davantage.
    """
    if entre_moyen is None:
        entre_moyen = ENTRE_MOYEN * k
    return secondes * action_moyenne / (action_moyenne + entre_moyen)


# temps moyen qui s'écoule entre deux snaps (arrêts compris), échelle NFL — mesuré (voir README, « Horloge réelle »)
ENTRE_MOYEN = 20.4
# même chose pour une attaque qui court après le temps (hurry-up, sorties, temps morts) — fin de période
ENTRE_PRESSE = 7.2
