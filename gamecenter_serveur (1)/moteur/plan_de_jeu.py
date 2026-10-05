"""AdaptiveGameplanEngine : plan de jeu par adversaire et adaptation en match (bloc D).

Prolonge les coordinateurs adaptatifs de V21 (notebook 12.2 quater : concept / formation mis de côté, hurry-up,
horloge, défense qui répond à ce qui fait mal) avec deux choses qui leur manquaient :

1. PLAN DE JEU (avant le match, par adversaire) — `plan_de_jeu(attaque, defense)` : un rapport de scouting tiré des
   notes et des réglages du staff adverse, sans hasard :
     - fréquence de blitz du coordinateur adverse -> part du jeu rapide (quick game, screens, draws) ;
     - couvertures préférées (homme / zone) -> concepts qui battent l'homme (croisements, mesh, slants) ou la zone
       (curl, stick, dagger, sail, champ) ;
     - zones fortes / faibles : duel de chaque receveur contre son vis-à-vis en homme -> CIBLE FAVORITE (le meilleur
       mismatch) ; fond du terrain (receveurs contre safeties) -> part des passes profondes ;
     - répartition course / passe : écart des notes d'unité (course contre défense de course, passe contre défense de
       passe) -> léger déplacement de la probabilité de passer ;
     - en défense : la menace principale de l'attaque adverse (receveur le plus dangereux) -> bracket préparé.

2. MÉMOIRE DE TENDANCES (pendant le match) — `MemoireTendances` : ce que chaque camp a VU de l'autre (cibles du QB,
   blitz sur 3e essai, pression, doubles couvertures, jeu rapide contre le blitz), puis `AdaptiveGameplanEngine` :
     ATTAQUE   o_quick    blitz répétés (sur 3e essai) -> quick pass / screen / draw ;
               o_protect  sacks ou passes pressées sur blitz -> un RB reste pour protéger (poche plus longue,
                          une route de moins) — sauf une attaque qui force (VEC) ;
               o_away     un receveur doublé à répétition -> la progression bascule vers WR2 / TE / RB ;
     DÉFENSE   d_bracket  un receveur trop ciblé (et productif) -> bracket / double sur lui ;
               d_rotate   CONTRE-AJUSTEMENT : l'attaque a basculé vers une autre cible -> le bracket la suit ;
               d_disguise CONTRE-AJUSTEMENT : le jeu rapide punit le blitz -> moins de blitz sur 3e essai, deux
                          safeties profonds (pression simulée).
   Chaque ajustement dure `tenue` snaps et porte sa RAISON (« 5 of his last 8 targets ») : le site l'affiche dans le
   play-by-play et le commentaire. Chaque franchise a son profil (CTX réagit vite, AEG lentement et longtemps, VEC
   ne protège pas et garde son blitz, MNL têtu).

Effets sur la passe (moteur.decider_passe, argument `plan`) : bracket (le double va sur le receveur visé, plus
souvent), protection (RB retiré des routes, poche plus longue), progression réordonnée (receveur doublé évité,
cible favorite lue en premier une fois sur trois — tirage dans le flux « plan-de-jeu », garde-fou 2).
Tout le reste est déterministe (aucun hasard : mêmes actions vues -> mêmes ajustements).
"""
from .reaction_defensive import talent_route, talent_couverture, _affectations_homme

# ---------- familles de concepts ----------
QUICK = {"QUICK_SLANT", "SHORT_OUT", "STICK", "SCREEN", "DRAG", "MESH"}          # jeu rapide (lancer < 1,2 s)
DRAWS = {"DRAW"}
PROFONDS = {"FOUR_VERTS", "DEEP_POST", "CORNER", "PLAY_ACTION", "CHAMP", "DAGGER", "SAIL", "BOOT", "POP"}
BATTRE_HOMME = {"MESH", "CROSS", "QUICK_SLANT", "DRAG", "SHORT_OUT"}               # croisements, picks, routes vives
BATTRE_ZONE = {"CURL", "STICK", "DAGGER", "SAIL", "CHAMP", "IN"}                   # entre les zones, floods
COUVERTURES_HOMME = {"MAN", "BLITZ"}
CIBLES = ("WR1", "WR2", "WR3", "TE")                                               # menaces (le RB : soupape)

# ---------- plan de jeu : poids ----------
PLAN = {
    "blitz_ref": 0.15,         # fréquence de blitz « normale » ; au-dessus, plus de jeu rapide
    "quick": 1.6,              # +60 % de jeu rapide par tranche de 0,15 de blitz au-dessus de la référence
    "quick_max": 1.35,
    "schema": 0.30,            # concepts anti-homme / anti-zone selon la part d'homme (± 15 % au plus)
    "fond": 0.025,             # passes profondes : par point d'écart receveurs - safeties
    "fond_borne": (0.85, 1.20),
    "course": 0.004,           # probabilité de passer : par point d'écart d'unités (course - passe)
    "course_max": 0.05,
    "favori": 0.33,            # la cible favorite est lue en premier une fois sur trois (si elle est dans la lecture)
    "favori_ecart": 3.0,       # ... seulement si son mismatch dépasse d'au moins 3 points celui du 2e meilleur duel
    "bracket_plan": 0.08,      # bracket préparé avant le match : + 8 points de probabilité de double sur la menace
}

# ---------- adaptation en match : profils (identités de la feuille de route, comme V21) ----------
PROFILS = {
    #        fenêtre de mémoire · seuils de déclenchement · durée · effets
    "CTX": dict(fenetre=8, blitz3=2, blitz_part=0.40, pression=3, doubles=3, cible_part=0.40, cible_min=4,
                cible_ok=0.50, tenue=10, protege=True, quick=1.55, bracket=0.50, rotation=3, deguise=2, deguise_k=0.45),
    "VEC": dict(fenetre=8, blitz3=3, blitz_part=0.50, pression=3, doubles=4, cible_part=0.45, cible_min=5,
                cible_ok=0.50, tenue=6, protege=False, quick=1.30, bracket=0.40, rotation=4, deguise=3, deguise_k=0.70),
    "AEG": dict(fenetre=10, blitz3=3, blitz_part=0.45, pression=3, doubles=3, cible_part=0.42, cible_min=5,
                cible_ok=0.45, tenue=14, protege=True, quick=1.45, bracket=0.55, rotation=3, deguise=2, deguise_k=0.45),
    "MNL": dict(fenetre=10, blitz3=3, blitz_part=0.50, pression=3, doubles=4, cible_part=0.50, cible_min=6,
                cible_ok=0.50, tenue=10, protege=True, quick=1.25, bracket=0.45, rotation=4, deguise=3, deguise_k=0.55),
}
PROFIL_DEFAUT = PROFILS["CTX"]
PROTECTION = {"poche": 0.20, "rusher5": 0.10}     # s gagnées par la protection ; un 5e rusher ramassé en partie
#   (0,35 / 0,15 au départ : la protection punissait trop l'équipe qui blitze le plus — VEC 42,6 % au test 12.3)
MONTRER = {"d_rotate": 2}                           # ajustements affichés au plus N fois par équipe et par match (1 sinon)

TEXTES = {
    "o_quick": "Answers the blitz with the quick game",
    "o_protect": "Keeps a back in to protect",
    "o_away": "Works away from the double on {label}",
    "d_bracket": "Brackets {label}",
    "d_rotate": "Rotates the bracket to {label}",
    "d_disguise": "Disguises the pressure, two deep",
    "plan_o": "Game plan: {label}",
    "plan_d": "Defensive game plan: {label}",
}


def _borne(x, a, b):
    return max(a, min(b, x))


def _part_homme(couvertures):
    tot = sum(couvertures.values()) or 1.0
    return sum(w for k, w in couvertures.items() if k in COUVERTURES_HOMME) / tot


def _menace(receveurs):
    """Rôle du receveur le plus dangereux (talent de route), parmi les menaces (pas le RB)."""
    roles = [r for r in CIBLES if receveurs.get(r)]
    return max(roles, key=lambda r: talent_route(receveurs[r], r)) if roles else ""


# =====================================================================================================
# 1. plan de jeu (avant le match)
# =====================================================================================================
def plan_de_jeu(attaque, defense):
    """Plan d'une attaque face à une défense adverse (et plan de la défense adverse contre cette attaque).

    attaque : {"abbr", "receveurs": {rôle: {"id", "name", "ratings"}}, "units": {"pass_off", "run_off"}}
    defense : {"abbr", "defenseurs": {"CB", "S", "LB": [...]}, "units": {"pass_def", "run_def"},
               "blitz_rate": float, "couvertures": {concept: poids}}
    Renvoie un dict sérialisable : concepts favorisés (multiplicateurs), déplacement course / passe, cible favorite,
    menace à brackéter, et le résumé lisible des deux plans.
    """
    rec, defs = attaque.get("receveurs") or {}, defense.get("defenseurs") or {}
    uo, ud = attaque.get("units") or {}, defense.get("units") or {}
    blitz = float(defense.get("blitz_rate", PLAN["blitz_ref"]))
    homme = _part_homme(defense.get("couvertures") or {"ZONE": 1.0})
    # multiplicateurs de concepts
    m_quick = _borne(1 + PLAN["quick"] * max(0.0, blitz - PLAN["blitz_ref"]), 1.0, PLAN["quick_max"])
    m_homme = 1 + PLAN["schema"] * (homme - 0.5)
    m_zone = 1 - PLAN["schema"] * (homme - 0.5)
    # duels en homme (Cover 1) : le mismatch de chaque receveur
    aff = _affectations_homme(list(CIBLES), defs, "Cover 1")
    duels = {}
    for r in CIBLES:
        if rec.get(r):
            d = aff.get(r)
            duels[r] = round(talent_route(rec[r], r) - (talent_couverture(d) if d else 70.0), 1)
    favori = max(duels, key=duels.get) if duels else ""
    # fond du terrain : les deux meilleurs receveurs extérieurs contre les safeties
    wr = [talent_route(rec[r], r) for r in ("WR1", "WR2") if rec.get(r)]
    s = [talent_couverture(x) for x in (defs.get("S") or []) if x]
    ecart_fond = (sum(wr) / len(wr) - sum(s) / len(s)) if wr and s else 0.0
    m_fond = _borne(1 + PLAN["fond"] * ecart_fond, *PLAN["fond_borne"])
    concepts = {}
    for c in QUICK | DRAWS:
        concepts[c] = concepts.get(c, 1.0) * m_quick
    for c in BATTRE_HOMME:
        concepts[c] = concepts.get(c, 1.0) * m_homme
    for c in BATTRE_ZONE:
        concepts[c] = concepts.get(c, 1.0) * m_zone
    for c in PROFONDS:
        concepts[c] = concepts.get(c, 1.0) * m_fond
    concepts = {k: round(v, 3) for k, v in sorted(concepts.items())}
    # course / passe : l'avantage relatif des unités
    gap = (uo.get("run_off", 75) - ud.get("run_def", 75)) - (uo.get("pass_off", 75) - ud.get("pass_def", 75))
    passe = round(_borne(-PLAN["course"] * gap, -PLAN["course_max"], PLAN["course_max"]), 3)
    menace = _menace(rec)
    nom = lambda r: (rec.get(r) or {}).get("name", r)
    # résumé lisible (site : onglet « Game plan », première action de chaque équipe)
    o = []
    if m_quick >= 1.1:
        o.append("quick game vs the blitz")
    o.append("beat man coverage" if homme >= 0.5 else "attack the zones")
    if m_fond >= 1.08:
        o.append("take shots deep")
    elif m_fond <= 0.92:
        o.append("stay underneath")
    if passe <= -0.02:
        o.append("lean on the run")
    elif passe >= 0.02:
        o.append("throw it more")
    if favori:
        o.append(f"target {nom(favori)}")
    return {
        "offense": attaque.get("abbr"), "defense": defense.get("abbr"),
        "concepts": concepts, "pass_shift": passe, "favori": favori,
        "favori_ecart": round(duels.get(favori, 0.0) - max([v for r, v in duels.items() if r != favori] or [0.0]), 1),
        "duels": duels, "blitz": round(blitz, 3), "man_share": round(homme, 3), "deep_gap": round(ecart_fond, 1),
        "menace": menace,
        "resume_attaque": ", ".join(o),
        "resume_defense": f"bracket {nom(menace)}" if menace else "",
        "noms": {r: (rec.get(r) or {}).get("name", "") for r in rec},
    }


def multiplicateur_concept(plan, etat_attaque, concept, down):
    """Poids d'un concept de la feuille d'appel : plan de jeu × ajustement en match (o_quick)."""
    m = (plan or {}).get("concepts", {}).get(concept, 1.0)
    if etat_attaque is not None and "o_quick" in etat_attaque.actifs:
        k = etat_attaque.profil["quick"]
        if down < 3:
            k = 1 + (k - 1) / 2                         # surtout sur 3e essai (là où le blitz arrive)
        if concept in QUICK or concept in DRAWS:
            m *= k
        elif concept in PROFONDS:
            m /= k
    return m


# =====================================================================================================
# 2. mémoire de tendances (pendant le match)
# =====================================================================================================
class MemoireTendances:
    """Ce qu'un camp a vu de l'attaque adverse (si défense) ou de la défense adverse (si attaque).

    Une action observée (dict, construit par le notebook depuis le play_log) :
        {"type": "PASS" / "RUN", "down", "concept", "blitz": bool, "cible": rôle ("" sans lancer),
         "double": rôle doublé ("" sinon), "reussite": bool, "yards": int, "sack": bool, "presse": bool,
         "complete": bool}
    """

    def __init__(self, fenetre=8):
        self.fenetre = fenetre
        self.passes = []          # actions de passe (dropbacks), les plus récentes à la fin
        self.troisiemes = []      # dropbacks sur 3e essai
        self.n = 0                # actions vues (courses comprises)

    def observer(self, a):
        self.n += 1
        if a.get("type") != "PASS":
            return
        self.passes.append(a)
        if a.get("down") == 3:
            self.troisiemes.append(a)
        del self.passes[:-40], self.troisiemes[:-12]

    # ---- ce que l'ATTAQUE voit de la défense ----
    def blitz_troisiemes(self, n=4):
        t = self.troisiemes[-n:]
        return sum(1 for a in t if a.get("blitz")), len(t)

    def blitz_recents(self):
        p = self.passes[-self.fenetre:]
        return sum(1 for a in p if a.get("blitz")), len(p)

    def pression_blitz(self):
        """Sacks et lancers pressés sur blitz dans la fenêtre."""
        return sum(1 for a in self.passes[-self.fenetre:] if a.get("blitz") and (a.get("sack") or a.get("presse")))

    def doubles(self):
        """{rôle: nombre de doubles vus} dans la fenêtre."""
        out = {}
        for a in self.passes[-self.fenetre:]:
            if a.get("double"):
                out[a["double"]] = out.get(a["double"], 0) + 1
        return out

    # ---- ce que la DÉFENSE voit de l'attaque ----
    def cibles(self, depuis=None):
        """{rôle: [cibles, réussites, yards]} sur la fenêtre (ou depuis l'action n° `depuis` des passes)."""
        p = self.passes[-self.fenetre:] if depuis is None else self.passes[depuis:]
        out = {}
        for a in p:
            r = a.get("cible")
            if not r:
                continue
            c = out.setdefault(r, [0, 0, 0])
            c[0] += 1
            c[1] += bool(a.get("reussite"))
            c[2] += int(a.get("yards") or 0) if a.get("complete") else 0
        return out

    def quick_contre_blitz(self):
        """Jeu rapide réussi contre le blitz dans la fenêtre (ce qui punit le blitz)."""
        return sum(1 for a in self.passes[-self.fenetre:]
                   if a.get("blitz") and a.get("concept") in QUICK and a.get("reussite"))


class EtatAdaptation:
    """Ajustements actifs d'un camp (attaque ou défense d'une équipe) dans un match."""

    def __init__(self, profil):
        self.profil = dict(profil)
        self.actifs = {}          # type -> snaps restants
        self.bracket = ""         # rôle brackété (défense)
        self.bracket_depuis = 0   # n° de passe observée au début du bracket (pour la rotation)
        self.evite = ""           # rôle évité dans la progression (attaque)
        self.montres = {}         # type -> nombre de fois affiché

    def tic(self):
        for k in list(self.actifs):
            self.actifs[k] -= 1
            if self.actifs[k] <= 0:
                del self.actifs[k]
                if k in ("d_bracket", "d_rotate") and "d_bracket" not in self.actifs and "d_rotate" not in self.actifs:
                    self.bracket = ""
                if k == "o_away":
                    self.evite = ""

    def montrer(self, kind):
        n = self.montres.get(kind, 0)
        if n >= MONTRER.get(kind, 1):
            return False
        self.montres[kind] = n + 1
        return True


def evenement(kind, label=None, raison=""):
    return {"kind": kind, "label": label, "text": TEXTES[kind].format(label=label or ""), "reason": raison}


class AdaptiveGameplanEngine:
    """Décide les ajustements d'un camp à partir de ce qu'il a vu (déterministe)."""

    def attaque(self, mem, etat, noms=None):
        """Ajustements de l'attaque face à la défense observée. Renvoie la liste des événements à afficher."""
        P, ev, noms = etat.profil, [], noms or {}
        etat.tic()
        b3, n3 = mem.blitz_troisiemes()
        br, nr = mem.blitz_recents()
        if "o_quick" not in etat.actifs and ((n3 >= 2 and b3 >= P["blitz3"]) or (nr >= 6 and br / nr >= P["blitz_part"])):
            etat.actifs["o_quick"] = P["tenue"]
            raison = f"blitzed on {b3} of the last {n3} third downs" if b3 >= P["blitz3"] else f"blitz on {br} of the last {nr} dropbacks"
            if etat.montrer("o_quick"):
                ev.append(evenement("o_quick", None, raison))
        pb = mem.pression_blitz()
        if P["protege"] and "o_protect" not in etat.actifs and pb >= P["pression"]:
            etat.actifs["o_protect"] = P["tenue"]
            if etat.montrer("o_protect"):
                ev.append(evenement("o_protect", None, f"{pb} sacks or hurried throws off the blitz"))
        dbl = mem.doubles()
        if dbl:
            role, n = max(sorted(dbl.items()), key=lambda x: x[1])
            if n >= P["doubles"] and etat.evite != role:
                etat.evite = role
                etat.actifs["o_away"] = P["tenue"]
                if etat.montrer("o_away"):
                    ev.append(evenement("o_away", noms.get(role, role),
                                        f"doubled on {n} of the last {len(mem.passes[-mem.fenetre:])} dropbacks"))
        return ev

    def defense(self, mem, etat, noms=None):
        """Ajustements de la défense face à l'attaque observée (bracket, rotation, pression déguisée)."""
        P, ev, noms = etat.profil, [], noms or {}
        etat.tic()
        if not etat.bracket:
            c = mem.cibles()
            tot = sum(v[0] for v in c.values())
            if tot >= P["cible_min"]:
                role, (n, ok, y) = max(sorted((r, v) for r, v in c.items() if r in CIBLES) or [("", (0, 0, 0))],
                                       key=lambda x: x[1][0])
                if role and n / tot >= P["cible_part"] and n >= 3 and (ok / n >= P["cible_ok"] or y >= 40):
                    etat.bracket, etat.bracket_depuis = role, len(mem.passes)
                    etat.actifs["d_bracket"] = P["tenue"]
                    if etat.montrer("d_bracket"):
                        ev.append(evenement("d_bracket", noms.get(role, role), f"{n} of the last {tot} targets"))
        else:
            # contre-ajustement : l'attaque a basculé vers une autre cible depuis le bracket
            c = mem.cibles(depuis=etat.bracket_depuis)
            tot = sum(v[0] for v in c.values())
            autres = sorted((r, v) for r, v in c.items() if r in CIBLES and r != etat.bracket)
            if autres and tot >= P["rotation"]:
                role, (n, ok, y) = max(autres, key=lambda x: x[1][0])
                if n >= P["rotation"] - 1 and n / tot >= 0.5 and (ok >= 2 or y >= 25):
                    etat.bracket, etat.bracket_depuis = role, len(mem.passes)
                    etat.actifs.pop("d_bracket", None)
                    etat.actifs["d_rotate"] = P["tenue"]
                    if etat.montrer("d_rotate"):
                        ev.append(evenement("d_rotate", noms.get(role, role), f"{n} of {tot} targets since the bracket"))
        q = mem.quick_contre_blitz()
        if "d_disguise" not in etat.actifs and q >= P["deguise"]:
            etat.actifs["d_disguise"] = P["tenue"]
            if etat.montrer("d_disguise"):
                ev.append(evenement("d_disguise", None, f"the quick game beat the blitz {q} times"))
        return ev


# =====================================================================================================
# 3. plan d'une passe (transmis à moteur.decider_passe) et progression ajustée
# =====================================================================================================
def plan_passe(plan_attaque, etat_attaque, plan_defense, etat_defense):
    """Ce que le plan de jeu et les ajustements actifs changent pour la passe de cette action.

    plan_attaque : plan_de_jeu(attaque, défense) (cible favorite) ; plan_defense : le même dict (menace préparée)
    — la défense prépare un bracket sur la menace de l'attaque.
    """
    out = {}
    pa = plan_attaque or {}
    if pa.get("favori") and pa.get("favori_ecart", 0) >= PLAN["favori_ecart"]:
        out["favori"], out["p_favori"] = pa["favori"], PLAN["favori"]
    if etat_attaque is not None:
        if "o_protect" in etat_attaque.actifs:
            out["protection"] = True
        if etat_attaque.evite:
            out["evite"] = etat_attaque.evite
            if out.get("favori") == etat_attaque.evite:
                out.pop("favori"); out.pop("p_favori")
    if etat_defense is not None and etat_defense.bracket:
        out["bracket"], out["p_bracket"] = etat_defense.bracket, etat_defense.profil["bracket"]
    elif (plan_defense or {}).get("menace"):
        out["bracket"], out["p_bracket_bonus"] = plan_defense["menace"], PLAN["bracket_plan"]
    if etat_defense is not None and "d_disguise" in etat_defense.actifs:
        out["deguise"] = True
    return out


NIVEAUX = ("primaire", "secondaire", "tertiaire", "checkdown")


def appliquer_progression(lectures, plan, rng):
    """Progression du QB selon le plan : protection (RB retiré), receveur doublé évité, cible favorite en premier.

    rng : flux « plan-de-jeu » de l'action (un tirage au plus : la cible favorite). Renvoie (lectures, notes).
    """
    if not plan or not lectures:
        return lectures, {}
    L = [dict(l) for l in lectures]
    notes = {}
    if plan.get("protection") and len(L) >= 3 and L[0]["role"] != "RB" and any(l["role"] == "RB" for l in L):
        L = [l for l in L if l["role"] != "RB"]
        notes["protection"] = True
    ev = plan.get("evite")
    if ev and len(L) >= 3 and L[0]["role"] == ev:
        L[0], L[1] = L[1], L[0]
        notes["away"] = ev
    fav = plan.get("favori")
    if fav and len(L) >= 3 and fav != ev:
        i = next((k for k, l in enumerate(L[:-1]) if l["role"] == fav), None)
        if i and rng.random() < plan.get("p_favori", 0.0):
            L.insert(0, L.pop(i))
            notes["focus"] = fav
    if notes:
        for k, l in enumerate(L):
            l["niveau"] = NIVEAUX[min(k, 2)]
        L[-1]["niveau"] = "checkdown"
    return L, notes


def options_reaction(plan):
    """Arguments de DefensiveReactionEngine.react pour ce plan (bracket, protection)."""
    if not plan:
        return {}
    out = {}
    if plan.get("bracket"):
        out["bracket"] = plan["bracket"]
        if "p_bracket" in plan:
            out["p_bracket"] = plan["p_bracket"]
        if "p_bracket_bonus" in plan:
            out["p_bracket_bonus"] = plan["p_bracket_bonus"]
    if plan.get("protection"):
        out["bonus_poche"] = PROTECTION["poche"]
        out["bonus_rusher5"] = PROTECTION["rusher5"]
    return out
