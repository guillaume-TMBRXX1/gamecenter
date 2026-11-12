"""Front office FO-5 : la draft des supporters (moteur). Python pur, sans import du notebook, déterministe.

Décisions de Guillaume (plan du 09/11/2026 et réponses du 11/11) :
    qui           seulement les TITULAIRES qui partent à la retraite (un remplaçant du banc reçoit la recrue d'aujourd'hui,
                  developpement.recrue) ;
    annonce       au calcul de la semaine N (14.1, progression_fin_semaine), les titulaires qui partent à la fin de N
                  sont annoncés : week.json → draft (« dernière saison », vote pendant la semaine N) ; au calcul de N+1,
                  exactement ces joueurs-là sont remplacés (la promesse faite aux supporters ne change pas) ;
    prospects     trois par départ, tirés chacun dans son flux « prospect|<semaine>|<id>|<k> », la base du poste gardée
                  (référence de l'anti-inflation et du garde-fou d'équipe), trois profils (PROFILS, mesurés : README du
                  serveur, section 113) :
                    pret          « Ready now » — notes proches de la base, potentiel modeste ;
                    potentiel     « High ceiling » — plus jeune, plus bas, potentiel haut, croissance rapide (rattrape
                                  « Ready now » en 6 à 8 semaines) ;
                    intelligence  « Football IQ » — mental haut (décision au-dessus de la base), avance d'expérience
                                  (bonus d'intelligence du bloc E), physique plus bas ;
    coordinateur  sans choix valable des supporters (moins de MIN_VOTES votes, égalité en tête) : le choix du
                  coordinateur, selon l'identité — SPK (franchise jeune) le gros potentiel, CTD (vétérans) le prêt ; les
                  autres : le prêt pour un QB, sinon un tirage fixe par départ (50 % prêt, 30 % potentiel, 20 % IQ).

Déroulé (notebook, cellule 12.2 sexdecies) :
    semaine N   developpement.semaine_suivante(..., draft=annonceur(noms_ligue)) : le titulaire qui part est remplacé
                dans players_next_week par le prospect du COORDINATEUR (garde-fou d'équipe appliqué avec lui) ; l'annonce
                (trois prospects complets) va dans week.json → draft ;
    semaine N+1 appliquer(etat, annonces, choix) : si les supporters ont choisi un autre prospect, il prend la place, puis
                developpement.stabiliser (anti-inflation, garde-fou) ; recrue.drafted_by_fans = True dans les deux cas
                où les supporters ont décidé ; week.json → drafted.
"""
import copy
import random

from moteur import developpement as D

VERSION = 1
PROFILS = ("pret", "potentiel", "intelligence")
LABELS = {"pret": "Ready now", "potentiel": "High ceiling", "intelligence": "Football IQ"}
MIN_VOTES = 5                       # comme le vote de la semaine (moteur/supporters.py)

# écart sous la base par catégorie de note (points ; négatif = au-dessus), âge, potentiel, rythme, expérience de départ
PROFIL = {
    "pret": {"age": (23.5, 25.0), "ecart": {"physique": (0.5, 2.0), "technique": (1.5, 3.0), "mental": (2.0, 4.0)},
             "potentiel": (3.0, 5.0), "dev": (("slow", 0.2), ("normal", 0.6), ("fast", 0.2)),
             "carriere": 1.0, "apprentissage": 1.0},
    "potentiel": {"age": (21.0, 22.0), "ecart": {"physique": (4.0, 7.0), "technique": (6.0, 9.0), "mental": (8.0, 11.0)},
                  "potentiel": (13.0, 16.0), "dev": (("normal", 0.2), ("fast", 0.5), ("star", 0.3)),
                  "carriere": 0.0, "apprentissage": 0.0},
    "intelligence": {"age": (22.5, 24.0), "ecart": {"physique": (4.0, 6.0), "technique": (2.0, 4.0),
                                                    "mental": (-2.0, 0.0)},
                     "potentiel": (7.0, 9.0), "dev": (("slow", 0.2), ("normal", 0.6), ("fast", 0.2)),
                     "carriere": 1.5, "apprentissage": 3.5},
}
COORD_EQUIPE = {"SPK": "potentiel", "CTD": "pret"}            # identité d'âge des franchises (developpement.AGE_EQUIPE)
COORD_POSTE = {"QB": "pret"}
COORD_TIRAGE = (("pret", 0.5), ("potentiel", 0.3), ("intelligence", 0.2))


def _rng(*parts):
    return random.Random("|".join(str(p) for p in parts))


def _tirer(rng, parts):
    u, acc = rng.random(), 0.0
    for nom, p in parts:
        acc += p
        if u < acc:
            return nom
    return parts[-1][0]


def prospect(j, pid, semaines, cle, profil, noms, pris=()):
    """Prospect `profil` pour la place de `j` (même id, même base) : flux « prospect|<cle>|<id>|<k> »."""
    k = PROFILS.index(profil)
    P = PROFIL[profil]
    rng = _rng("prospect", cle, pid, k)
    prenoms, familles = noms
    nom = None
    for _ in range(200):
        nom = f"{rng.choice(prenoms)} {rng.choice(familles)}"
        if nom not in pris:
            break
    a = rng.uniform(*P["age"])
    dev = _tirer(rng, P["dev"])
    pot = round(rng.uniform(*P["potentiel"]), 1)
    actuelle = {}
    for att, v in sorted(j["base"].items()):
        x = v - rng.uniform(*P["ecart"][D.categorie(att)])
        haut = min(float(D.NOTE_MAX), v + pot + (3.0 if D.categorie(att) == "mental" else 0.0))   # developpement.plafond
        actuelle[att] = round(max(float(D.NOTE_MIN), min(haut, x)), 3)
    return dict(age0=round(a - semaines / D.SEMAINES_PAR_AN, 2), dev=dev, potentiel=pot, carriere=P["carriere"],
                name=nom, pos=j["pos"], team=j["team"], base=dict(j["base"]), actuelle=actuelle, forme=0.0,
                apprentissage=P["apprentissage"], bonus_iq=0.0, historique=[],
                recrue={"semaine": cle, "remplace": j["name"], "profile": profil, "drafted_by_fans": False})


IQ_POINTS = 3.0                    # FO-6 (décision du 12/11) : Football IQ = OVR + 3 points par point de bonus d'expérience


def bonus_iq_estime(j, etat):
    """Bonus d'expérience qu'aurait `j` dans la ligue de `etat` (developpement.stabiliser : IQ_K × (apprentissage −
    moyenne du groupe), borné) ; la moyenne des titulaires de son groupe d'intelligence, ou de tous les titulaires."""
    g = D.IQ_GROUPE.get(j["pos"])
    xs = [x.get("apprentissage", 0.0) for x in (etat or {}).get("joueurs", {}).values()
          if not x.get("banc") and (g is None or D.IQ_GROUPE.get(x["pos"]) == g)]
    m = sum(xs) / len(xs) if xs else 0.0
    return max(-D.IQ_MAX, min(D.IQ_MAX, D.IQ_K * (j.get("apprentissage", 0.0) - m)))


def football_iq(j, bonus=None):
    """La note « Football IQ » du site (40-99) : la décision d'un QB, sinon OVR + IQ_POINTS × bonus d'expérience."""
    n = D.notes_effectives(j)
    if "decision_making" in n:
        return int(n["decision_making"])
    b = j.get("bonus_iq", 0.0) if bonus is None else bonus
    return int(max(D.NOTE_MIN, min(D.NOTE_MAX, round(D.ovr(n) + IQ_POINTS * b))))


def resume(r, semaines, etat=None):
    """Ce que le site montre d'un prospect : nom, âge, OVR, potentiel (OVR de base + potentiel), rythme, notes,
    Football IQ (avec le bonus d'expérience qu'il aurait dans la ligue de `etat`)."""
    o = D.ovr(D.notes_effectives(r))
    return {"name": r["name"], "age": int(D.age(r, semaines)), "ovr": o, "dev": r["dev"],
            "potential": min(D.NOTE_MAX, int(D.ovr(r["base"]) + r["potentiel"] + 0.5)),
            "ratings": D.notes_effectives(r), "iq": football_iq(r, bonus_iq_estime(r, etat) if etat else 0.0)}


def choix_coordinateur(pid, team, pos, cle):
    """Le prospect que prend le coordinateur sans choix valable des supporters (déterministe)."""
    if team in COORD_EQUIPE:
        return COORD_EQUIPE[team]
    if pos in COORD_POSTE:
        return COORD_POSTE[pos]
    return _tirer(_rng("draft-coordinateur", cle, pid), COORD_TIRAGE)


def annonceur(noms_ligue=False):
    """Pour developpement.semaine_suivante(draft=…) : fonction (etat, pid, j, cle, noms, pris) -> (prospect du
    coordinateur, annonce). Les noms des prospects d'une même semaine ne se répètent pas (ni entre eux, ni dans la ligue
    si noms_ligue, sinon dans l'équipe)."""
    deja = set()

    def draft(etat, pid, j, cle, noms, pris):
        s = etat["semaines"]
        pr, vus = [], set(pris) | deja
        for p in PROFILS:
            r = prospect(j, pid, s, cle, p, noms, vus)
            vus.add(r["name"])
            deja.add(r["name"])
            pr.append(r)
        coord = choix_coordinateur(pid, j["team"], j["pos"], cle)
        annonce = {"id": pid, "team": j["team"], "pos": j["pos"], "retired": j["name"],
                   "age": int(D.age(j, s)), "ovr": D.ovr(D.notes_effectives(j)), "week": cle, "coordinator": coord,
                   "ratings": D.notes_effectives(j), "iq": football_iq(j), "seasons": len(j.get("historique") or []),
                   "prospects": [{"profile": p, "label": LABELS[p], **resume(r, s, etat), "player": r}
                                 for p, r in zip(PROFILS, pr)]}
        return copy.deepcopy(pr[PROFILS.index(coord)]), annonce
    return draft


def choix_supporters(annonce, fans):
    """(profil, source, votes) : le choix des supporters s'il est valable (≥ MIN_VOTES votes, profil connu, pas
    d'égalité en tête des counts), sinon celui du coordinateur. fans = {"choice", "votes", "counts"} ou None."""
    coord = annonce["coordinator"]
    if not isinstance(fans, dict):
        return coord, "coordinators", 0
    try:
        votes = int(fans.get("votes") or 0)
    except (TypeError, ValueError):
        votes = 0
    c = fans.get("choice")
    counts = fans.get("counts") if isinstance(fans.get("counts"), dict) else {}
    top = sorted(((int(v or 0), k) for k, v in counts.items() if k in PROFILS), reverse=True)
    if c not in PROFILS or votes < MIN_VOTES or (len(top) > 1 and top[0][0] == top[1][0]) or (top and top[0][1] != c):
        return coord, "coordinators", votes
    return c, "fans", votes


def lire_choix(donnees, lundi):
    """Le bloc « draft » du fichier GC_FANS ({id: {choice, votes, counts}}) s'il est pour la semaine `lundi`, sinon {}."""
    if not isinstance(donnees, dict) or str(donnees.get("week")) != str(lundi):
        return {}
    d = donnees.get("draft")
    return d if isinstance(d, dict) else {}


def appliquer(etat, annonces, choix, unites=None):
    """Semaine N+1 (avant les cotes) : chaque annonce de la semaine N reçoit son prospect. Modifie `etat` (état de la
    semaine, = players_next_week de N) ; renvoie week.json → drafted [{id, team, pos, retired, profile, name, source,
    votes, coordinator}]. Un remplacement par un autre prospect que celui du coordinateur relance stabiliser."""
    out, change = [], False
    for a in annonces or []:
        pid = a["id"]
        cur = etat["joueurs"].get(pid)
        coord = a["coordinator"]
        attendu = next(p for p in a["prospects"] if p["profile"] == coord)["player"]["name"]
        if not cur or cur.get("name") != attendu:
            out.append({"id": pid, "team": a["team"], "pos": a["pos"], "retired": a["retired"], "profile": None,
                        "name": cur.get("name") if cur else None, "source": "missing", "votes": 0,
                        "coordinator": coord})
            continue
        profil, source, votes = choix_supporters(a, (choix or {}).get(pid))
        if profil != coord:
            nouveau = copy.deepcopy(next(p for p in a["prospects"] if p["profile"] == profil)["player"])
            etat["joueurs"][pid] = nouveau
            change = True
        if source == "fans":
            etat["joueurs"][pid].setdefault("recrue", {})["drafted_by_fans"] = True
        out.append({"id": pid, "team": a["team"], "pos": a["pos"], "retired": a["retired"], "profile": profil,
                    "name": etat["joueurs"][pid]["name"], "source": source, "votes": votes, "coordinator": coord})
    if change:
        D.stabiliser(etat, unites)
    return out


def controle(annonces, etat_suivant):
    """Anomalies d'une semaine (vide = OK) : trois profils dans l'ordre, base du poste gardée par les trois, noms
    distincts, titulaires seulement, place tenue par le prospect du coordinateur dans players_next_week."""
    err, noms = [], []
    J = (etat_suivant or {}).get("joueurs") or {}
    for a in annonces or []:
        pid = a.get("id")
        pr = a.get("prospects") or []
        if [p.get("profile") for p in pr] != list(PROFILS):
            err.append(f"{pid} : profils {[p.get('profile') for p in pr]}")
            continue
        if a.get("coordinator") not in PROFILS:
            err.append(f"{pid} : choix du coordinateur {a.get('coordinator')}")
            continue
        bases = {tuple(sorted(p["player"]["base"].items())) for p in pr}
        if len(bases) != 1:
            err.append(f"{pid} : bases différentes entre prospects")
        noms += [p["player"]["name"] for p in pr]
        j = J.get(pid)
        if j is None:
            err.append(f"{pid} : absent de players_next_week")
            continue
        if j.get("banc"):
            err.append(f"{pid} : remplaçant annoncé (titulaires seulement)")
        if tuple(sorted(j["base"].items())) not in bases:
            err.append(f"{pid} : base du poste non gardée")
        coord = next(p for p in pr if p["profile"] == a["coordinator"])["player"]
        if j.get("name") != coord["name"] or (j.get("recrue") or {}).get("profile") != a["coordinator"]:
            err.append(f"{pid} : la place n'est pas tenue par le prospect du coordinateur")
    if len(noms) != len(set(noms)):
        err.append("noms de prospects en double")
    return err
