"""QBDecisionEngine : la progression du QB (bloc A).

Le QB lit les cibles dans l'ordre du playbook (primaire -> secondaire -> tertiaire -> checkdown). Chaque
lecture arrive quand la route s'ouvre et au moins un « pas de lecture » après la précédente. Si la pression
arrive avant qu'il ait lancé : lancer quand même sous pression, throwaway, scramble, passe forcée ou sack.

Bloc A (QB sans attributs d'intelligence) : deux notes existantes, avec un poids modéré : decision_making (pas
de lecture, discipline : moins de passes forcées, plus de throwaways) et mobility (scramble).

Bloc B (QB avec qb["iq"], moteur.intelligence_qb) : les 8 attributs pèsent sur la décision sans la rendre certaine.
  - chrono de poche : reconnaissance au snap (awareness), temps entre deux lectures (processing), lancer avant
    l'ouverture (anticipation) contre le temps avant la pression, que le QB allonge en glissant dans la poche
    (pocket awareness) ; dans la dernière fenêtre avant la pression, il est PRESSÉ ;
  - lecture de la couverture : le QB décide sur le statut qu'il PERÇOIT ; il se trompe parfois (coverage reading,
    plus en zone, plus quand il est pressé et que sa pressure response est faible) : il lance alors dans une
    couverture qu'il croyait ouverte (interception plus probable) ou passe à côté d'un receveur libre ;
  - style : aggressiveness (fenêtres serrées, passes forcées) tempéré par decision_making ;
  - fin de poche : scramble (mobility, pocket awareness), throwaway (decision making, awareness), passe forcée
    (aggressiveness), sinon sack : un QB qui garde le ballon trop longtemps est sacké.
Même un QB élite se trompe (erreur de lecture jamais nulle, bruit de la séparation).
"""
from dataclasses import dataclass, asdict

from .reaction_defensive import LIBRE, SERRE, COUVERT, DOUBLE

LANCER, THROWAWAY, SCRAMBLE, SACK = "LANCER", "THROWAWAY", "SCRAMBLE", "SACK"

# probabilité de lancer sur une lecture, selon son statut (checkdown à part)
P_LANCER = {LIBRE: 0.92, SERRE: 0.50, COUVERT: 0.04, DOUBLE: 0.03}
P_LANCER_PRIMAIRE_SERRE = 0.60      # la première lecture serrée est plus souvent tentée (timing du concept)
P_LANCER_CHECKDOWN = {LIBRE: 0.97, SERRE: 0.80, COUVERT: 0.10, DOUBLE: 0.05}
DEPART = 0.15                        # drop : la première lecture n'arrive jamais avant ouverture + 0,15 s
PAS = {"base": 0.45, "dm_pente": 1 / 250, "min": 0.38, "max": 0.75}
# sous pression : lancer sur la meilleure lecture vue (si libre / serrée), sinon options de fin d'action
P_SOUS_PRESSION = {LIBRE: 0.85, SERRE: 0.45}
FIN = {"throwaway": 0.30, "throwaway_dm": 1 / 200, "scramble_mob": 0.009, "scramble_seuil": 62,
       "forcee": 0.16, "forcee_dm": -1 / 300}

# ---- bloc B : poids des attributs, autour d'un QB de référence (REF : niveau moyen des titulaires de la ligue) ----
ORDRE = (DOUBLE, COUVERT, SERRE, LIBRE)            # du plus fermé au plus ouvert
REF = 80
POIDS = 0.45                   # part de l'écart à REF qui pèse (qualités) — garde l'équilibre des franchises (12.3)
B = {
    "pas": {"base": 0.45, "pente": 1 / 300, "min": 0.30, "max": 0.80},        # processing
    "depart": {"base": 0.15, "pente": 0.003, "min": 0.05, "max": 0.30},       # awareness
    "anticipation": 0.005, "anticipation_max": 0.15,   # s gagnées sur l'ouverture de la route (lancer avant la cassure)
    "poche": 0.006, "poche_max": 0.20,                 # s gagnées / perdues dans la poche (pocket awareness)
    "hate": 0.45,                                      # fenêtre avant la pression où le QB est pressé
    "erreur": {"base": 0.09, "pente": 1 / 40, "min": 0.02, "max": 0.30, "zone": 1.25, "homme": 0.85, "presse_ref": 85, "presse_pente": 1 / 40},
    "optimiste": 0.6,                                  # part des erreurs qui voient plus ouvert que la réalité
    "serre_aggr": 0.005, "serre_antic": 0.004,         # tenter la fenêtre serrée
    "ferme_aggr": 1 / 30, "ferme_dm": 1 / 60,          # lancer dans une couverture fermée
    "pression_pr": 0.006,                              # sous pression, lancer quand même sur la meilleure lecture
    "fin": {"scramble_pa": 0.002, "away_aw": 1 / 250, "away_pa": 1 / 250, "force_aggr": 1 / 250},
    # résolution (multiplicateurs transmis à moteur.resolution)
    "res": {"antic_inc": 1 / 250, "antic_int": 1 / 300, "pr": 1 / 80, "pr_min": 0.75, "pr_max": 1.25, "erreur_int": 1.25},
}


@dataclass
class QBDecision:
    action: str                  # LANCER / THROWAWAY / SCRAMBLE / SACK
    cible_prevue: str            # rôle de la cible primaire
    cible: str                   # rôle de la cible réelle ("" sans lancer)
    lecture: int                 # n° de la lecture lancée (1 = première), 0 sans lancer
    lectures: int                # lectures effectivement faites
    statut: str                  # statut de la cible au lancer ("" sans lancer)
    sous_pression: bool
    forcee: bool                 # passe dans une couverture fermée
    temps_lancer: float          # secondes après le snap (ou instant de la fin de l'action)
    # bloc B (valeurs par défaut = bloc A)
    percu: str = ""              # statut que le QB a CRU voir au lancer
    erreur_lecture: bool = False # percu != statut réel
    presse: bool = False         # lancer / fin d'action dans la fenêtre de pression
    temps_poche: float = 0.0     # temps avant la pression, allongé ou raccourci par le QB dans la poche
    mod_int: float = 1.0         # multiplicateurs de la résolution (anticipation, pressure response, erreur)
    mod_inc: float = 1.0
    bloc: str = "A"

    def to_dict(self):
        return asdict(self)


def _note(qb, cle, defaut=70):
    return float(((qb or {}).get("ratings") or {}).get(cle, defaut))


def pas_de_lecture(qb):
    dm = _note(qb, "decision_making")
    return max(PAS["min"], min(PAS["max"], PAS["base"] - (dm - 75) * PAS["dm_pente"]))


def _borne(x, a, b):
    return max(a, min(b, x))


def _iq(qb, cle):
    """Attribut effectif : REF + POIDS × écart (aggressiveness, un style, pèse en entier)."""
    v = float((qb.get("iq") or {}).get(cle, REF))
    return v if cle == "aggressiveness" else REF + POIDS * (v - REF)


def chrono_b(qb):
    """(reconnaissance au snap, pas de lecture, avance de l'anticipation, temps gagné dans la poche) — bloc B."""
    depart = _borne(B["depart"]["base"] - (_iq(qb, "awareness") - REF) * B["depart"]["pente"],
                    B["depart"]["min"], B["depart"]["max"])
    pas = _borne(B["pas"]["base"] - (_iq(qb, "processing") - REF) * B["pas"]["pente"], B["pas"]["min"], B["pas"]["max"])
    avance = _borne((_iq(qb, "anticipation") - REF) * B["anticipation"], -B["anticipation_max"], B["anticipation_max"])
    poche = _borne((_iq(qb, "pocket_awareness") - REF) * B["poche"], -B["poche_max"], B["poche_max"])
    return depart, pas, avance, poche


def p_erreur_lecture(qb, famille, presse):
    """Probabilité de mal lire le statut d'un receveur (jamais nulle : un QB élite peut se tromper)."""
    e = B["erreur"]
    p = e["base"] * (1 + (REF - _iq(qb, "coverage_reading")) * e["pente"])
    p *= e["zone"] if famille == "zone" else e["homme"]
    if presse:
        p *= 1 + max(0.0, e["presse_ref"] - _iq(qb, "pressure_response")) * e["presse_pente"]
    return _borne(p, e["min"], e["max"])


def percevoir(statut, p_err, rng):
    """Statut vu par le QB : parfois un cran plus ouvert (optimiste) ou plus fermé (pessimiste) que la réalité."""
    if rng.random() >= p_err:
        return statut
    i = ORDRE.index(statut) + (1 if rng.random() < B["optimiste"] else -1)
    return ORDRE[_borne(i, 0, len(ORDRE) - 1)]


def p_lancer_b(qb, percu, niveau, premiere):
    """Probabilité de lancer sur une lecture, selon le statut perçu et le style du QB."""
    aggr, dm = _iq(qb, "aggressiveness"), _iq(qb, "decision_making")
    if niveau == "checkdown":
        p = P_LANCER_CHECKDOWN[percu]
    elif premiere and percu == SERRE:
        p = P_LANCER_PRIMAIRE_SERRE
    else:
        p = P_LANCER[percu]
    if percu == SERRE:
        p += (aggr - 50) * B["serre_aggr"] + (_iq(qb, "anticipation") - REF) * B["serre_antic"]
    elif percu in (COUVERT, DOUBLE):
        p *= max(0.2, 1 + (aggr - 50) * B["ferme_aggr"]) * max(0.3, 1 - (dm - REF) * B["ferme_dm"])
    return _borne(p, 0.0, 0.99)


def modificateurs_b(qb, statut, presse, erreur_optimiste):
    """Multiplicateurs (interception, incomplète) transmis à la résolution."""
    R = B["res"]
    m_int = m_inc = 1.0
    if statut in (SERRE, COUVERT, DOUBLE):              # l'anticipation sert dans les fenêtres serrées
        a = _iq(qb, "anticipation") - REF
        m_inc *= max(0.6, 1 - a * R["antic_inc"])
        m_int *= max(0.6, 1 - a * R["antic_int"])
    if presse:                                          # pressure response : garde sa précision sous la pression
        k = _borne(1 + (REF - _iq(qb, "pressure_response")) * R["pr"], R["pr_min"], R["pr_max"])
        m_int *= k
        m_inc *= k
    if erreur_optimiste:                                # il n'a pas vu le défenseur : interception plus probable
        m_int *= R["erreur_int"]
    return round(m_int, 4), round(m_inc, 4)


class QBDecisionEngine:
    """Décide qui reçoit le ballon (ou ce qui arrive à la place)."""

    def decide(self, etat, lectures, qb, rng):
        """
        etat     : PostSnapState (moteur.reaction_defensive)
        lectures : progression (même ordre que pour etat)
        qb       : {"id", "name", "ratings"} du QB titulaire (+ "iq" : attributs du bloc B)
        rng      : flux dédié
        """
        if (qb or {}).get("iq"):
            return self.decide_b(etat, lectures, qb, rng)
        primaire = lectures[0]["role"] if lectures else ""
        pas = pas_de_lecture(qb)
        t, vues, n = 0.0, [], 0
        ttp = etat.temps_pression
        for i, l in enumerate(lectures):
            t = max(l["ouverture"] + DEPART, t + pas) if i else l["ouverture"] + DEPART
            if t > ttp:
                break                                   # la pression arrive avant cette lecture
            n += 1
            e = etat.receveurs[l["role"]]
            vues.append((l, e))
            if l["niveau"] == "checkdown":
                p = P_LANCER_CHECKDOWN[e.statut]
            elif i == 0 and e.statut == SERRE:
                p = P_LANCER_PRIMAIRE_SERRE
            else:
                p = P_LANCER[e.statut]
            if rng.random() < p:
                return QBDecision(LANCER, primaire, l["role"], i + 1, n, e.statut, t > ttp - 0.3,
                                  e.statut in (COUVERT, DOUBLE), round(t, 2))

        # plus personne à lire, ou la pression est là
        t_fin = round(max(t, ttp) if n == len(lectures) else ttp, 2)
        jouables = [(l, e) for l, e in vues if e.statut in (LIBRE, SERRE)]
        if jouables:
            l, e = max(jouables, key=lambda le: le[1].separation)
            if rng.random() < P_SOUS_PRESSION[e.statut]:
                return QBDecision(LANCER, primaire, l["role"], lectures.index(l) + 1, n, e.statut, True, False, t_fin)
        dm, mob = _note(qb, "decision_making"), _note(qb, "mobility")
        p_scr = max(0.0, (mob - FIN["scramble_seuil"]) * FIN["scramble_mob"])
        p_away = max(0.05, FIN["throwaway"] + (dm - 70) * FIN["throwaway_dm"])
        p_force = max(0.04, FIN["forcee"] + (dm - 70) * FIN["forcee_dm"])
        r = rng.random()
        if r < p_scr:
            return QBDecision(SCRAMBLE, primaire, "", 0, n, "", True, False, t_fin)
        if r < p_scr + p_away:
            return QBDecision(THROWAWAY, primaire, "", 0, n, "", True, False, t_fin)
        if r < p_scr + p_away + p_force and lectures:
            cands = vues or [(lectures[0], etat.receveurs[lectures[0]["role"]])]
            l, e = max(cands, key=lambda le: le[1].separation)
            return QBDecision(LANCER, primaire, l["role"], lectures.index(l) + 1, n, e.statut, True,
                              e.statut in (COUVERT, DOUBLE), t_fin)
        return QBDecision(SACK, primaire, "", 0, n, "", True, False, t_fin)

    def decide_b(self, etat, lectures, qb, rng):
        """Bloc B : chrono de poche, statut perçu, style du QB (voir l'en-tête du module)."""
        primaire = lectures[0]["role"] if lectures else ""
        depart, pas, avance, poche = chrono_b(qb)
        ttp = round(max(0.8, etat.temps_pression + poche), 2)
        hate = ttp - B["hate"]
        t, vues, n = 0.0, [], 0
        for i, l in enumerate(lectures):
            ouvre = max(0.45, l["ouverture"] - avance) + depart
            t = max(ouvre, t + pas) if i else ouvre
            if t > ttp:
                break                                   # la pression arrive avant cette lecture
            n += 1
            e = etat.receveurs[l["role"]]
            presse = t > hate
            percu = percevoir(e.statut, p_erreur_lecture(qb, etat.famille, presse), rng)
            vues.append((l, e, percu))
            if rng.random() < p_lancer_b(qb, percu, l["niveau"], i == 0):
                return self._lancer_b(qb, primaire, l, e, percu, i + 1, n, presse, round(t, 2), ttp)

        # plus personne à lire, ou la pression est là
        t_fin = round(max(t, ttp) if n == len(lectures) else ttp, 2)
        jouables = [v for v in vues if v[2] in (LIBRE, SERRE)]
        if jouables:
            l, e, percu = max(jouables, key=lambda v: (ORDRE.index(v[2]), v[1].separation))
            p = P_SOUS_PRESSION[percu] + (_iq(qb, "pressure_response") - REF) * B["pression_pr"]
            if rng.random() < _borne(p, 0.05, 0.95):
                return self._lancer_b(qb, primaire, l, e, percu, lectures.index(l) + 1, n, True, t_fin, ttp)
        F = B["fin"]
        dm, mob = _iq(qb, "decision_making"), float(((qb or {}).get("ratings") or {}).get("mobility", 70))
        aw, pa, aggr = _iq(qb, "awareness"), _iq(qb, "pocket_awareness"), _iq(qb, "aggressiveness")
        p_scr = max(0.0, (mob - FIN["scramble_seuil"]) * FIN["scramble_mob"] + (pa - REF) * F["scramble_pa"])
        p_away = max(0.05, FIN["throwaway"] + (dm - 70) * FIN["throwaway_dm"] + (aw - REF) * F["away_aw"]
                     + (pa - REF) * F["away_pa"])
        p_force = max(0.04, FIN["forcee"] + (dm - 70) * FIN["forcee_dm"] + (aggr - 50) * F["force_aggr"])
        r = rng.random()
        fin = dict(percu="", erreur_lecture=False, presse=True, temps_poche=ttp, bloc="B")
        if r < p_scr:
            return QBDecision(SCRAMBLE, primaire, "", 0, n, "", True, False, t_fin, **fin)
        if r < p_scr + p_away:
            return QBDecision(THROWAWAY, primaire, "", 0, n, "", True, False, t_fin, **fin)
        if r < p_scr + p_away + p_force and lectures:
            cands = vues or [(lectures[0], etat.receveurs[lectures[0]["role"]], etat.receveurs[lectures[0]["role"]].statut)]
            l, e, percu = max(cands, key=lambda v: (ORDRE.index(v[2]), v[1].separation))
            return self._lancer_b(qb, primaire, l, e, percu, lectures.index(l) + 1, n, True, t_fin, ttp)
        return QBDecision(SACK, primaire, "", 0, n, "", True, False, t_fin, **fin)

    @staticmethod
    def _lancer_b(qb, primaire, l, e, percu, lecture, n, presse, t, ttp):
        optimiste = ORDRE.index(percu) > ORDRE.index(e.statut)
        m_int, m_inc = modificateurs_b(qb, e.statut, presse, optimiste)
        return QBDecision(LANCER, primaire, l["role"], lecture, n, e.statut, presse, e.statut in (COUVERT, DOUBLE), t,
                          percu=percu, erreur_lecture=percu != e.statut, presse=presse, temps_poche=ttp,
                          mod_int=m_int, mod_inc=m_inc, bloc="B")
