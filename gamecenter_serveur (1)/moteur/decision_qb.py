"""QBDecisionEngine : la progression du QB (bloc A).

Le QB lit les cibles dans l'ordre du playbook (primaire -> secondaire -> tertiaire -> checkdown). Chaque
lecture arrive quand la route s'ouvre et au moins un « pas de lecture » après la précédente. Si la pression
arrive avant qu'il ait lancé : lancer quand même sous pression, throwaway, scramble, passe forcée ou sack.

Le bloc A n'utilise que deux notes existantes, avec un poids modéré : decision_making (pas de lecture,
discipline : moins de passes forcées, plus de throwaways) et mobility (scramble). Le bloc B ajoutera les
attributs dédiés (processing, pocket awareness, aggressiveness…).
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

    def to_dict(self):
        return asdict(self)


def _note(qb, cle, defaut=70):
    return float(((qb or {}).get("ratings") or {}).get(cle, defaut))


def pas_de_lecture(qb):
    dm = _note(qb, "decision_making")
    return max(PAS["min"], min(PAS["max"], PAS["base"] - (dm - 75) * PAS["dm_pente"]))


class QBDecisionEngine:
    """Décide qui reçoit le ballon (ou ce qui arrive à la place)."""

    def decide(self, etat, lectures, qb, rng):
        """
        etat     : PostSnapState (moteur.reaction_defensive)
        lectures : progression (même ordre que pour etat)
        qb       : {"id", "name", "ratings"} du QB titulaire
        rng      : flux dédié
        """
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
