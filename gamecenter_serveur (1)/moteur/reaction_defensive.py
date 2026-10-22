"""DefensiveReactionEngine : l'état post-snap (bloc A).

À partir de l'appel défensif (concept du coordinateur : MAN, ZONE, COVER_2/3/4, BLITZ, BOX_STACK…), des
receveurs alignés (routes de la progression) et des défenseurs, construit ce que le QB va lire :
  - la couverture réelle (homme / zone, Cover 0-1-2-3-4) et le nombre de rushers ;
  - pour chaque receveur : séparation (en « pas » de couverture) et statut libre / serré / couvert / double ;
  - le temps avant que la pression n'arrive.

Abstraction statistique, pas de physique : séparation = écart de notes (route vs couverture) + avantage de la
route contre cette couverture (zones faibles connues) + bruit tiré dans le flux dédié.
Tout est déterministe pour un même rng (garde-fou 2).
"""
from dataclasses import dataclass, field, asdict

from .aleatoire import gauss_borne

LIBRE, SERRE, COUVERT, DOUBLE = "LIBRE", "SERRE", "COUVERT", "DOUBLE"

# concept défensif du coordinateur -> (famille, [(couverture, poids)], rushers)
COUVERTURES = {
    "MAN":       ("homme", [("Cover 1", 1.0)], 4),
    "ZONE":      ("zone", [("Cover 3", 0.6), ("Cover 2", 0.4)], 4),
    "COVER_2":   ("zone", [("Cover 2", 1.0)], 4),
    "COVER_3":   ("zone", [("Cover 3", 1.0)], 4),
    "COVER_4":   ("zone", [("Cover 4", 1.0)], 4),
    "BLITZ":     ("homme", [("Cover 0", 0.45), ("Cover 1", 0.55)], 5),
    "BOX_STACK": ("homme", [("Cover 1", 1.0)], 4),
}
COUVERTURE_DEFAUT = ("zone", [("Cover 3", 1.0)], 4)

# avantage de la route contre la couverture (en pas de séparation), par classe de profondeur
AVANTAGE = {
    "Cover 0": {"court": 0.5, "moyen": 0.3, "profond": 0.5},
    "Cover 1": {"court": 0.1, "moyen": 0.1, "profond": -0.4},
    "Cover 2": {"court": 0.2, "moyen": 0.5, "profond": -0.3},
    "Cover 3": {"court": 0.5, "moyen": 0.2, "profond": -0.6},
    "Cover 4": {"court": 0.8, "moyen": 0.1, "profond": -0.9},
}
# routes qui attaquent précisément la faiblesse d'une couverture (en plus de la classe)
AVANTAGE_ROUTE = {
    "Cover 2": {"CORNER": 0.8, "FLAG": 0.7, "SEAM": 0.6, "POST": 0.5, "DIG": 0.2},
    "Cover 3": {"FLAT": 0.3, "SEAM": 0.5, "CURL": 0.3, "OUT": 0.3},
    "Cover 4": {"DIG": 0.3, "CURL": 0.2, "DRAG": 0.3},
    "Cover 1": {"CROSS": 0.5, "DRAG": 0.5, "SLANT": 0.3, "QUICK_SLANT": 0.3},
    "Cover 0": {"QUICK_SLANT": 0.4, "STICK": 0.3, "FLAT": 0.3},
}
# poids de l'écart de notes : en homme le duel compte plein, en zone il est amorti
POIDS_DUEL = {"homme": 1.0, "zone": 0.6}
ECHELLE_DUEL = 20.0            # points de note pour un « pas » de séparation
# probabilité qu'un safety se décale sur la meilleure menace (bracket / double)
DOUBLE_BASE = {"Cover 0": 0.0, "Cover 1": 0.12, "Cover 2": 0.22, "Cover 3": 0.08, "Cover 4": 0.26}
SEUIL_LIBRE, SEUIL_SERRE = 0.9, 0.0
BONUS_CHECKDOWN = 0.6          # le checkdown est la soupape : la défense regarde plus loin
BONUS_HOT = 0.4                # contre 5-6 rushers, la route courte « hot » se libère
BRUIT = 0.9

# chrono de la poche (secondes) : base, effet du niveau de pression (0-1, 03E), rushers en plus
POCHE = {"base": 3.3, "pente_pression": 1.2, "rusher5": 0.30, "rusher6": 0.20, "bruit": 0.45, "min": 1.3}


@dataclass
class EtatReceveur:
    role: str
    id: str
    nom: str
    route: str
    classe: str
    niveau: str
    defenseur: str
    separation: float
    statut: str
    # bloc C (moteur.intelligence_joueurs) : défenseur responsable, coverage bust, écart de route
    couvreur_id: str = ""
    couvreur_nom: str = ""
    bust: bool = False
    ecart_route: float = 0.0


@dataclass
class PostSnapState:
    concept_defensif: str
    famille: str                 # homme / zone
    couverture: str              # Cover 0 … Cover 4
    rushers: int
    blitz: bool
    double_sur: str              # rôle du receveur doublé (ou "")
    temps_pression: float        # secondes avant que la pression n'arrive
    receveurs: dict = field(default_factory=dict)     # rôle -> EtatReceveur
    # extension du playbook (moteur.playbook_expansion) : paquet joué, présentation, effets sur le QB
    paquet: str = ""             # paquet défensif réellement joué ("" : l'appel de base)
    presente: str = ""           # ce que la défense a montré avant le snap
    deguisement: float = 0.0     # erreurs de lecture du QB en plus (+) / en moins (− : motion, shift)
    scramble: float = 1.0        # multiplicateur des sorties de poche (contain, blitz intérieur…)

    def to_dict(self):
        d = asdict(self)
        d["receveurs"] = {r: asdict(e) for r, e in self.receveurs.items()}
        return d


def _note(r, cle, defaut=70):
    return float((r.get("ratings") or {}).get(cle, defaut))


def talent_route(joueur, role):
    """Capacité à se démarquer (0-100). Le RB n'a pas de note de route : vitesse et accélération, décotées."""
    if role == "RB":
        return 0.5 * _note(joueur, "speed") + 0.5 * _note(joueur, "acceleration") - 8
    vit = _note(joueur, "speed")
    return 0.55 * _note(joueur, "route_running") + 0.30 * vit + 0.15 * _note(joueur, "acceleration", vit)


def talent_couverture(defenseur):
    return 0.7 * _note(defenseur, "coverage") + 0.3 * _note(defenseur, "speed")


def _tirage(poids, rng):
    total = sum(w for _, w in poids)
    x = rng.random() * total
    for item, w in poids:
        x -= w
        if x <= 0:
            return item
    return poids[-1][0]


def _affectations_homme(roles, defs, couverture):
    """Duels en homme : CB1-WR1, CB2-WR2, S2 (ou S1) sur le slot, LB sur TE et RB.
    En Cover 1 le S1 reste libre au fond (aide) ; en Cover 0 il prend un receveur. Étape 7.3 : un 3e CB sur le terrain
    (nickel, dime) prend le slot."""
    cb, s, lb = defs.get("CB", []), defs.get("S", []), defs.get("LB", [])
    pool = {"WR1": cb[:1], "WR2": cb[1:2], "WR3": cb[2:3] or s[1:2] or s[:1], "TE": lb[:1] or s[:1],
            "RB": lb[1:2] or lb[:1]}
    if couverture == "Cover 0" and s:
        pool["TE"] = s[:1]
    return {r: (pool.get(r) or lb[:1] or cb[:1] or [None])[0] for r in roles}


def _defenseurs_zone(classe, defs):
    """Zone : le receveur est lu par les défenseurs de la tranche qu'il attaque (moyenne de leurs notes)."""
    cb, s, lb = defs.get("CB", []), defs.get("S", []), defs.get("LB", [])
    return {"court": lb + cb, "moyen": lb[:1] + cb + s[1:], "profond": s + cb}.get(classe) or (cb + s + lb)


class DefensiveReactionEngine:
    """Construit le PostSnapState d'une passe."""

    def react(self, concept_defensif, lectures, receveurs, defenseurs, niveau_pression, rng, bruit=BRUIT,
              echelle=ECHELLE_DUEL, bracket="", p_bracket=None, p_bracket_bonus=0.0, bonus_poche=0.0,
              bonus_rusher5=0.0, appel=None):
        """
        concept_defensif : appel du coordinateur ("COVER_2", "BLITZ"…)
        lectures         : progression (moteur.progressions.progression)
        receveurs        : {rôle: {"id", "name", "ratings"}}
        defenseurs       : {"CB": [...], "S": [...], "LB": [...]} (ordre du depth chart)
        niveau_pression  : 0-1, rush contre protection (fonction pure 03E du notebook, blitz compris)
        rng              : flux dédié (moteur.aleatoire.flux)
        bruit            : écart-type du bruit de séparation (bloc C : plus petit, l'écart de route prend le reste ;
                           mêmes tirages consommés)
        echelle          : points de note pour un « pas » de séparation (bloc C : intelligence_joueurs.ECHELLE_C,
                           20 comme au bloc A — le niveau des joueurs reste dans ce duel de notes)
        bracket          : bloc D (moteur.plan_de_jeu) — rôle que la défense a choisi de doubler (au lieu de la
                           meilleure menace) ; p_bracket : probabilité minimale du double (jamais en
                           Cover 0) ; p_bracket_bonus : points ajoutés à la base (bracket préparé avant le match).
                           Même tirage consommé qu'au bloc A.
        bonus_poche      : bloc D — protection (un RB reste bloquer) : secondes gagnées avant la pression ;
                           bonus_rusher5 : part du 5e rusher ramassée par ce bloqueur
        appel            : extension du playbook (moteur.playbook_expansion.appel_passe) — paquet défensif (coquille,
                           rushers, présentation, receveur laissé par un blitzeur…), jeu de rush, front, protection,
                           motion, shift, enchaînement. None : bloc D à l'identique (mêmes tirages, mêmes valeurs).
        """
        a = appel or {}
        if a.get("paquet"):
            famille, choix, rushers = a["famille"], a["coquilles"], a["rushers"]
        else:
            famille, choix, rushers = COUVERTURES.get(concept_defensif, COUVERTURE_DEFAUT)
        couverture = _tirage(choix, rng)
        blitz = concept_defensif == "BLITZ"
        if blitz and couverture == "Cover 0":
            rushers = max(rushers, 6)
        roles = [l["role"] for l in lectures]
        homme = {}
        if famille == "homme":
            comme = couverture
            if a:
                from .playbook_expansion import COQUILLE_HOMME
                comme = COQUILLE_HOMME.get(couverture, couverture)
            homme = _affectations_homme(roles, defenseurs, comme)

        # séparation de chaque receveur
        etats, brut = {}, {}
        for l in lectures:
            role = l["role"]
            j = receveurs.get(role) or {}
            if famille == "homme":
                d = homme.get(role)
                tc, nom_d = (talent_couverture(d), d.get("name", "")) if d else (60.0, "")
            else:
                zone = _defenseurs_zone(l["classe"], defenseurs)
                tc = sum(talent_couverture(d) for d in zone) / len(zone) if zone else 70.0
                nom_d = "zone"
            sep = POIDS_DUEL[famille] * (talent_route(j, role) - tc) / echelle
            sep += AVANTAGE.get(couverture, {}).get(l["classe"], 0.0)
            sep += AVANTAGE_ROUTE.get(couverture, {}).get(l["route"], 0.0)
            if l["niveau"] == "checkdown":
                sep += BONUS_CHECKDOWN
            if rushers >= 5 and l["classe"] == "court":
                sep += BONUS_HOT
            sep += gauss_borne(rng, bruit, 2.5)
            if a:
                sep += _effet_appel(a, l, famille)
            brut[role] = (sep, nom_d, j)

        # double couverture : un safety penche sur la meilleure menace hors checkdown (souvent WR1)
        double_sur = ""
        menaces = [l for l in lectures if l["niveau"] != "checkdown" and l["route"] != "SCREEN"]
        if menaces:
            cible = max(menaces, key=lambda l: talent_route(receveurs.get(l["role"]) or {}, l["role"]))
            visee = next((l for l in menaces if l["role"] == bracket), None) if bracket else None
            if visee is not None:
                cible = visee                    # bloc D : la défense double le receveur qu'elle a choisi
            p = DOUBLE_BASE.get(couverture, 0.0)
            if p > 0:
                p = max(0.0, min(0.6, p + (talent_route(receveurs.get(cible["role"]) or {}, cible["role"]) - 80) * 0.01))
                if visee is not None:
                    p = min(0.75, max(p, p_bracket) if p_bracket is not None else p + p_bracket_bonus)
            if rng.random() < p:
                double_sur = cible["role"]

        for l in lectures:
            role = l["role"]
            sep, nom_d, j = brut[role]
            if double_sur and role != double_sur:
                sep += 0.25                      # le safety parti aider laisse de la place ailleurs
            if role == double_sur:
                sep -= 1.6
                statut = LIBRE if sep >= 1.5 else DOUBLE
            else:
                statut = LIBRE if sep >= SEUIL_LIBRE else SERRE if sep >= SEUIL_SERRE else COUVERT
            etats[role] = EtatReceveur(role=role, id=j.get("id", ""), nom=j.get("name", ""), route=l["route"],
                                       classe=l["classe"], niveau=l["niveau"], defenseur=nom_d,
                                       separation=round(sep, 2), statut=statut)

        t = POCHE["base"] - (niveau_pression - 0.5) * POCHE["pente_pression"]
        if rushers >= 5:
            t -= POCHE["rusher5"] - bonus_rusher5
        t += bonus_poche
        if rushers >= 6:
            t -= POCHE["rusher6"]
        if a:
            if rushers >= 5:
                t += a.get("rusher5", 0.0) * POCHE["rusher5"]
            if rushers >= 7:
                t -= POCHE["rusher6"]
            t += a.get("poche", 0.0)
            k = a.get("bruit_poche", 1.0)
            t += gauss_borne(rng, POCHE["bruit"] * k, 1.0 * k)
        else:
            t += gauss_borne(rng, POCHE["bruit"], 1.0)
        etat = PostSnapState(concept_defensif=concept_defensif, famille=famille, couverture=couverture,
                             rushers=rushers, blitz=blitz, double_sur=double_sur,
                             temps_pression=round(max(POCHE["min"], t), 2), receveurs=etats)
        if a:
            from .playbook_expansion import deguisement
            etat.paquet, etat.presente = a.get("paquet", ""), a.get("presente", "")
            etat.deguisement = deguisement(a, famille)
            etat.scramble = float(a.get("scramble", 1.0))
        return etat


def _effet_appel(a, lecture, famille):
    """Séparation ajoutée par l'extension du playbook (paquet, front, motion, enchaînement) — sans tirage."""
    d = 0.0
    if lecture["classe"] == "court":
        d += a.get("court", 0.0)
    if lecture["classe"] == "profond":
        d += a.get("profond", 0.0)
    d += (a.get("vide") or {}).get(lecture["role"], 0.0)
    if a.get("motion_role") == lecture["role"]:
        d += (a.get("motion_sep") or {}).get(famille, 0.0)
    if a.get("suite") and lecture["niveau"] == "primaire":
        d += a.get("suite_sep", 0.0)
    d += (a.get("anticipation") or {}).get(lecture["classe"], 0.0)     # défense engagée (moteur.scouting)
    return d
