"""Front office, étape FO-1 — les leviers des supporters dans le moteur (programme/Front_office_plan.md).

Chaque semaine, les supporters d'une franchise (les comptes dont c'est l'équipe favorite) répondent à UNE question ;
la même question pour les 24 franchises une semaine donnée, selon une rotation fixe (index de la semaine). Trois
réponses : un côté, « choix du coordinateur » (rien ne change), l'autre côté. Le choix place le réglage du coordinateur
au bas ou en haut de ses bornes d'identité : il reste « dans l'identité de l'équipe ».

  - LEVIERS : le catalogue (id, intitulés anglais pour le site, options, réglage touché, côté attaque / défense) ;
  - ROTATION, levier_de_semaine(index) : la question de la semaine ;
  - placer(bornes, position) / valeur(...) : le réglage au bas, au milieu ou en haut des bornes ;
  - lire_fichier, choix_de_semaine : le fichier GC_FANS (format ci-dessous), validé — tout ce qui est absent,
    illisible ou inconnu laisse les coordinateurs décider, sans erreur ;
  - appliquer / restaurer : sur les coordinateurs du notebook (objets à attributs) ; les deux leviers sans attribut de
    coordinateur (couverture, profondeur) vivent dans un dictionnaire de la semaine lu par le moteur ;
  - poids_profondeur : les poids des plays de passe d'un playbook avec le levier de profondeur.

Le choix ne vaut QUE pour la semaine : le notebook restaure les réglages des coordinateurs avant l'ajustement
hebdomadaire (staffs_next_week), qui ne dérive donc pas.

Format du fichier GC_FANS (produit par le serveur à l'étape FO-3, data/fans/fans_<lundi>.json) :

    {
      "version": 1,
      "week": "2026-11-16",              lundi de la semaine où les choix s'appliquent (autre semaine : ignoré)
      "lever": "quatrieme",              doit être le levier de la rotation pour cette semaine (sinon : ignoré)
      "closed_at": "2026-11-13T23:30:00+01:00",      facultatif (information)
      "teams": {
        "CTX": {"choice": "agressif", "votes": 37,
                "counts": {"prudent": 5, "coordinateur": 10, "agressif": 22}},     counts facultatif
        "VEC": {"choice": "coordinateur", "votes": 3}
      }
    }

Une franchise absente, un choix inconnu, moins de MIN_VOTES votes ou une égalité en tête des counts : le coordinateur
décide (source « coordinators »). Python pur, sans hasard.
"""
import json
import math

VERSION = "supporters-1"
MIN_VOTES = 5                        # en dessous : « the coordinator kept his plan » (décision du 07/11)
COORD = "coordinateur"
SOURCE_FANS, SOURCE_COORD = "fans", "coordinators"

# =====================================================================================================================
# 1. CATALOGUE — options dans l'ordre affiché : [côté « bas » des bornes, coordinateur, côté « haut »]
# =====================================================================================================================
LEVIERS = {
    "quatrieme": {
        "label": "4th down", "question": "How bold should we be on fourth down?",
        "side": "offense", "setting": "go_max_to_go",
        "options": [("prudent", "Play it safe"), (COORD, "Coordinator's call"), ("agressif", "Go for it")]},
    "course_passe": {
        "label": "Run or pass", "question": "Should we lean on the run or the pass?",
        "side": "offense", "setting": "pass_shift",
        "options": [("plus_course", "More runs"), (COORD, "Coordinator's call"), ("plus_passe", "More passes")]},
    "blitz": {
        "label": "Blitz", "question": "How often should the defense send extra rushers?",
        "side": "defense", "setting": "blitz_rate",
        "options": [("moins", "Blitz less"), (COORD, "Coordinator's call"), ("plus", "Blitz more")]},
    "couverture": {
        "label": "Coverage", "question": "Zone or man-to-man coverage?",
        "side": "defense", "setting": "man_weight",
        "options": [("zone", "More zone"), (COORD, "Coordinator's call"), ("homme", "More man-to-man")]},
    "profondeur": {
        "label": "Passing depth", "question": "Short passes or deep shots?",
        "side": "offense", "setting": "deep_weight",
        "options": [("courtes", "Shorter passes"), (COORD, "Coordinator's call"), ("longues", "Deeper passes")]},
}
ROTATION = ("quatrieme", "course_passe", "blitz", "couverture", "profondeur")
ORIGINE = 8                          # index de la semaine qui ouvre la rotation (semaine du 16/11/2026 : le 4e essai)

# 4e essai : la ligne à partir de laquelle le coordinateur joue un 4e essai (go_min_yard_line, sans bands) bouge
# aussi de LIGNE_4E yards (prudent : plus loin, agressif : plus près de son camp), bornée à LIGNE_4E_BORNES (la plage
# de transformation.agressivite). 0 : seul go_max_to_go bouge.
LIGNE_4E = 8                         # décision du 09/11 : go_max_to_go ET la ligne (écart visible chaque semaine)
LIGNE_4E_BORNES = (30, 62)

# réglages sans attribut de coordinateur : valeur neutre (= le coordinateur)
NEUTRE = {"man_weight": 1.0, "deep_weight": 1.0}

# =====================================================================================================================
# 2. BORNES DES LEVIERS 4 ET 5 (identité de chaque franchise — bible, refonte des playbooks)
# =====================================================================================================================
# couverture : multiplicateur du poids MAN du coordinateur (après l'identité, 12.2 vicies septies) ;
# profondeur : multiplicateur des concepts profonds et intermédiaires (les courts et écrans sont divisés d'autant),
# budget de passe du coordinateur conservé. 1,0 = le coordinateur.
BORNES_COUVERTURE = {
    "CTX": (0.44, 1.88), "VEC": (0.61, 1.86), "AEG": (0.49, 5.18), "MNL": (0.61, 1.66), "AXM": (0.41, 1.93),
    "GLT": (0.62, 1.59), "CPH": (0.5, 1.8), "NVA": (0.5, 7.3), "PLS": (0.3, 2.09), "ONX": (0.35, 2.03),
    "FRG": (0.53, 1.77), "MRD": (0.5, 5.74), "APX": (0.54, 1.74), "LTC": (0.36, 2.01), "ZPH": (0.43, 1.91),
    "BST": (0.58, 1.84), "GRZ": (0.51, 1.79), "MRG": (0.36, 2.01), "GMB": (0.57, 1.84), "PRM": (0.45, 1.87),
    "SPK": (0.56, 1.85), "CTD": (0.42, 2.4), "TDL": (0.37, 1.99), "CMT": (0.48, 1.83),
}
BORNES_PROFONDEUR = {
    "CTX": (0.8, 1.4), "VEC": (0.8, 1.4), "AEG": (0.65, 1.25), "MNL": (0.7, 1.35), "AXM": (0.65, 1.25),
    "GLT": (0.65, 1.25), "CPH": (0.7, 1.35), "NVA": (0.8, 1.4), "PLS": (0.65, 1.25), "ONX": (0.65, 1.25),
    "FRG": (0.8, 1.4), "MRD": (0.65, 1.25), "APX": (0.65, 1.25), "LTC": (0.65, 1.25), "ZPH": (0.8, 1.4),
    "BST": (0.65, 1.25), "GRZ": (0.8, 1.4), "MRG": (0.7, 1.35), "GMB": (0.7, 1.35), "PRM": (0.8, 1.4),
    "SPK": (0.8, 1.4), "CTD": (0.7, 1.35), "TDL": (0.7, 1.35), "CMT": (0.65, 1.25),
}
BORNES_DEFAUT = {"man_weight": (0.6, 1.6), "deep_weight": (0.7, 1.4)}

# familles de concepts (comme outils/moteur/identite_playbooks.py) ; play-action, RPO et le reste : neutres
COURTS = frozenset(("QUICK_SLANT", "STICK", "SHORT_OUT", "HITCH", "SPOT_SNAG", "PIVOT", "CHOICE", "CURL", "DRAG", "MESH",
                    "MESH_WHEEL", "DART_QUICK_DIG", "SCREEN", "FL_SE_SCREEN", "WR_TUNNEL_SCREEN"))
LONGS = frozenset(("IN", "CROSS", "Y_CROSS", "LEVELS", "DOUBLE_DIG", "FLOOD", "SAIL", "DAGGER", "DEEP_CROSS", "CHAMP",
                   "SALEM", "DEEP_POST", "CORNER", "DOUBLE_POST", "FOUR_VERTS", "SWITCH_VERTICALS", "DIVIDE"))


# =====================================================================================================================
# 3. FONCTIONS PURES
# =====================================================================================================================
def options(levier):
    return [o for o, _ in LEVIERS[levier]["options"]]


def levier_de_semaine(index):
    """Le levier de la semaine d'index `index` (week.index du notebook) : rotation fixe, la même pour tous."""
    return ROTATION[(int(index) - ORIGINE) % len(ROTATION)]


def position(levier, choix):
    """'bas' | 'haut' | None (coordinateur ou choix inconnu)."""
    ops = options(levier)
    if choix == ops[0]:
        return "bas"
    if choix == ops[2]:
        return "haut"
    return None


def placer(bornes, pos, entier=False):
    """Le réglage au bas, au milieu ou en haut des bornes (lo, hi)."""
    lo, hi = bornes
    v = {"bas": lo, "haut": hi, "milieu": (lo + hi) / 2}[pos]
    return int(math.floor(v + 0.5)) if entier else round(v, 4)


def bornes(levier, abbr, coordinateur=None):
    """Bornes (lo, hi) du réglage du levier pour la franchise. Leviers 1-3 : les bands du coordinateur (objet
    OffensiveCoordinator / DefensiveCoordinator, ou dict {"bands": …}) ; leviers 4-5 : les tables ci-dessus."""
    s = LEVIERS[levier]["setting"]
    if s == "man_weight":
        return tuple(BORNES_COUVERTURE.get(abbr, BORNES_DEFAUT[s]))
    if s == "deep_weight":
        return tuple(BORNES_PROFONDEUR.get(abbr, BORNES_DEFAUT[s]))
    bands = coordinateur.get("bands") if isinstance(coordinateur, dict) else getattr(coordinateur, "bands", None)
    b = (bands or {}).get(s)
    return tuple(b) if b else None


def valeur(levier, choix, actuel, b):
    """Valeur du réglage pour la semaine : bas / haut des bornes, ou la valeur actuelle (coordinateur)."""
    pos = position(levier, choix)
    if pos is None or b is None:
        return actuel
    return placer(b, pos, entier=isinstance(actuel, int) and not isinstance(actuel, bool))


def lire_fichier(chemin):
    """Le fichier GC_FANS (dict) ou None (pas de chemin, absent, illisible, pas un objet JSON)."""
    if not chemin:
        return None
    try:
        with open(chemin, encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return d if isinstance(d, dict) else None


def _egalite(counts):
    try:
        vals = sorted((int(v) for v in counts.values()), reverse=True)
    except (TypeError, ValueError, AttributeError):
        return False
    return len(vals) >= 2 and vals[0] == vals[1]


def choix_de_semaine(donnees, lundi, levier, equipes):
    """{abbr: {"choice", "source", "votes"}} pour toutes les franchises de `equipes`. Tout ce qui ne colle pas
    (fichier absent, autre semaine, autre levier, franchise absente, choix inconnu, trop peu de votes, égalité) :
    le coordinateur décide."""
    out = {a: {"choice": COORD, "source": SOURCE_COORD, "votes": 0} for a in equipes}
    if not isinstance(donnees, dict) or levier not in LEVIERS:
        return out
    if donnees.get("lever") != levier or (donnees.get("week") is not None and str(donnees.get("week")) != str(lundi)):
        return out
    teams = donnees.get("teams")
    if not isinstance(teams, dict):
        return out
    ops = options(levier)
    for a in equipes:
        t = teams.get(a)
        if not isinstance(t, dict):
            continue
        try:
            votes = int(t.get("votes") or 0)
        except (TypeError, ValueError):
            votes = 0
        out[a]["votes"] = max(0, votes)
        c = t.get("choice")
        if c not in ops or c == COORD or votes < MIN_VOTES:
            continue
        if isinstance(t.get("counts"), dict) and _egalite(t["counts"]):
            continue
        out[a].update(choice=c, source=SOURCE_FANS)
    return out


def _coordinateur(staff, levier):
    return getattr(staff, LEVIERS[levier]["side"])


def appliquer(staff, abbr, levier, choix, semaine):
    """Applique le choix à la franchise. staff : objet .offense / .defense (coordinateurs du notebook) ; semaine :
    {réglage: {abbr: valeur}} pour les réglages sans attribut (man_weight, deep_weight), mis à jour en place.
    Renvoie l'enregistrement {setting, coordinator, value, bands} (coordinator = valeur à restaurer)."""
    lv = LEVIERS[levier]
    s = lv["setting"]
    coord = _coordinateur(staff, levier)
    b = bornes(levier, abbr, coord)
    if s in NEUTRE:
        actuel = NEUTRE[s]
        v = valeur(levier, choix, actuel, b)
        if v != actuel:
            semaine.setdefault(s, {})[abbr] = v
    else:
        actuel = getattr(coord, s)
        v = valeur(levier, choix, actuel, b)
        setattr(coord, s, v)
    rec = {"setting": s, "coordinator": actuel, "value": v, "bands": list(b) if b else None}
    if levier == "quatrieme" and LIGNE_4E and hasattr(coord, "go_min_yard_line"):
        pos, ligne = position(levier, choix), coord.go_min_yard_line
        d = {"bas": LIGNE_4E, "haut": -LIGNE_4E}.get(pos, 0)
        rec["go_min_yard_line"] = {"coordinator": ligne,
                                   "value": max(LIGNE_4E_BORNES[0], min(LIGNE_4E_BORNES[1], ligne + d)) if d else ligne}
        coord.go_min_yard_line = rec["go_min_yard_line"]["value"]
    return rec


def restaurer(staff, abbr, levier, rec, semaine):
    """Remet le réglage du coordinateur (avant l'ajustement hebdomadaire : rien n'est reporté)."""
    s = LEVIERS[levier]["setting"]
    if s in NEUTRE:
        (semaine.get(s) or {}).pop(abbr, None)
    else:
        setattr(_coordinateur(staff, levier), s, rec["coordinator"])
    if "go_min_yard_line" in rec:
        _coordinateur(staff, levier).go_min_yard_line = rec["go_min_yard_line"]["coordinator"]


def poids_profondeur(lignes, k):
    """lignes : [(play, concept, poids)] d'un playbook de passe ; k : multiplicateur (deep_weight). Concepts longs
    × k, courts ÷ k, les autres inchangés ; total ramené à celui d'entrée (budget du coordinateur). Renvoie les poids."""
    if not k or k == 1.0:
        return [w for _, _, w in lignes]
    out = [w * k if c in LONGS else w / k if c in COURTS else w for _, c, w in lignes]
    t0, t1 = sum(w for _, _, w in lignes), sum(out)
    return [w * t0 / t1 for w in out] if t1 > 0 else [w for _, _, w in lignes]


def question(levier, index, lundi, staffs, valeurs_coord=None):
    """week.json → fan_vote : la question de la semaine `index` (lundi `lundi`). staffs : {abbr: staff} ;
    valeurs_coord : {abbr: valeur actuelle} pour remplacer celle lue sur le coordinateur."""
    lv = LEVIERS[levier]
    s = lv["setting"]
    teams = {}
    for a, staff in staffs.items():
        coord = _coordinateur(staff, levier)
        b = bornes(levier, a, coord)
        cur = (valeurs_coord or {}).get(a, NEUTRE.get(s, getattr(coord, s, None)))
        ops = options(levier)
        teams[a] = {"current": cur, "bands": list(b) if b else None,
                    "values": {ops[0]: valeur(levier, ops[0], cur, b), COORD: cur, ops[2]: valeur(levier, ops[2], cur, b)}}
    return {"version": VERSION, "index": index, "week": lundi, "lever": levier, "label": lv["label"],
            "question": lv["question"], "side": lv["side"], "setting": s,
            "options": [{"id": o, "label": l} for o, l in lv["options"]], "teams": teams}


def controle(equipes, staffs):
    """Liste d'anomalies du catalogue et des bornes (vide = OK)."""
    err = []
    if set(ROTATION) != set(LEVIERS) or len(ROTATION) != len(set(ROTATION)):
        err.append("rotation : chaque levier une fois")
    for lv, d in LEVIERS.items():
        ops = options(lv)
        if len(ops) != 3 or ops[1] != COORD or len(set(ops)) != 3:
            err.append(f"{lv} : options {ops}")
    for a in equipes:
        for lv in LEVIERS:
            b = bornes(lv, a, _coordinateur(staffs[a], lv)) if a in staffs else None
            if b is None or not b[0] <= b[1]:
                err.append(f"{a} {lv} : bornes {b}")
                continue
            s = LEVIERS[lv]["setting"]
            if s in NEUTRE and not b[0] <= NEUTRE[s] <= b[1]:
                err.append(f"{a} {lv} : {NEUTRE[s]} hors de {b}")
    return err


# =====================================================================================================================
# 4. CHIFFRES DE LA SEMAINE (FO-4 : écran Front office) — sur les GameFeed des matchs terminés
# =====================================================================================================================
# ce que chaque levier fait bouger, mesuré sur les matchs d'une franchise : (numérateur, dénominateur)
MESURE = {"quatrieme": ("go4", "q4"), "course_passe": ("runs", "snaps"), "blitz": ("blitz", "dsnaps"),
          "couverture": ("man", "dsnaps"), "profondeur": ("longs", "passes")}
_COURSES = frozenset(("INSIDE_RUN", "TRAP", "DRAW", "WHAM", "QB_DRAW", "POWER", "COUNTER", "PIN_PULL", "OUTSIDE_RUN",
                      "BUCK_SWEEP", "COUNTER_SWEEP", "POWER_TOSS", "JET_SWEEP", "JET_ACTION", "END_AROUND", "REVERSE",
                      "DOUBLE_REVERSE", "READ_OPTION", "POWER_READ", "INVERTED_VEER", "MIDLINE_OPTION", "SHOVEL_OPTION",
                      "SPEED_OPTION", "TRIPLE_OPTION", "QB_SWEEP", "RPO_ALERT", "RPO_INSIDE_ZONE", "RPO_OUTSIDE_ZONE",
                      "RPO_PEEK", "RPO_POWER", "RPO_READ"))


def mesurer_match(feed, home, away):
    """Comptes d'un match terminé pour chaque franchise : {abbr: {q4, go4, snaps, runs, passes, longs, dsnaps, blitz,
    man}} (mêmes définitions que moteur/empreinte.py ; « longs » : concepts intermédiaires et profonds, LONGS)."""
    abbr = {"home": home, "away": away}
    vide = lambda: {"q4": 0, "go4": 0, "snaps": 0, "runs": 0, "passes": 0, "longs": 0, "dsnaps": 0, "blitz": 0, "man": 0}
    M = {home: vide(), away: vide()}
    for p in feed.get("plays") or []:
        att = abbr.get(p.get("offense"))
        if not att:
            continue
        d = M[away if att == home else home]
        c = p.get("call") or {}
        typ, k = c.get("type"), c.get("concept")
        if p.get("down") == 4 and typ in ("run", "pass", "punt", "field_goal"):
            M[att]["q4"] += 1
            M[att]["go4"] += typ in ("run", "pass") and k not in ("KNEEL", "SPIKE")
        if typ not in ("run", "pass") or not k or k in ("KNEEL", "SPIKE"):
            continue
        o = M[att]
        course = k in _COURSES
        o["snaps"] += 1
        o["runs"] += course
        if not course:
            o["passes"] += 1
            o["longs"] += k in LONGS
        dd = (c.get("defense") or {}).get("concept")
        d["dsnaps"] += 1
        d["blitz"] += dd == "BLITZ"
        d["man"] += dd == "MAN"
    return M


def chiffres(levier, comptes):
    """comptes = {abbr: [comptes de ses matchs]} -> {"teams": {abbr: {"value", "games"}}, "league": moyenne | None}."""
    num, den = MESURE[levier]
    out = {}
    for a, ms in comptes.items():
        n, d = sum(m[num] for m in ms), sum(m[den] for m in ms)
        out[a] = {"value": round(n / d, 4) if d else None, "games": len(ms)}
    vals = [v["value"] for v in out.values() if v["value"] is not None]
    return {"teams": out, "league": round(sum(vals) / len(vals), 4) if vals else None}

