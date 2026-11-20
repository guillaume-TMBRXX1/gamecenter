"""Statistiques de suivi (« Next Gen Stats », affichées « Tracking » sur le site ; programme/Next_Gen_Stats_plan.md).

Lecture seule : tout vient de ce que le moteur a déjà écrit dans chaque GameFeed (play.decision, play.geo, play.pocket,
play.run, play.subs). Rien ne change dans le moteur, le notebook ou le calcul du samedi. Le serveur ne passe que des
matchs TERMINÉS : jamais une action pas encore jouée.

  compter(feed, modeles)    comptes bruts d'un match, par joueur et par équipe (calculés une fois par match terminé)
  agreger(comptes)          somme des comptes de plusieurs matchs (+ matchs joués par équipe)
  tableaux(agg, modeles)    statistiques finales par groupe (passeurs, receveurs, porteurs, rush, couverture,
                            plaquages, blocs, équipes) : joueurs qualifiés, valeur, moyenne de la ligue
  stat_du_jour(tab, cle)    la statistique gratuite du Day recap (une seule, vraie)
  entrainer(feeds)          modèles « attendus » (xComp, xYAC, xRush) appris sur des semaines passées

Définitions (anglais sur le site, « How it's measured ») :
  - Un dropback = une passe décidée par le bloc A (play.decision), pénalités exclues (l'action est annulée).
  - Une tentative = un lancer (action LANCER) qui finit complété, incomplet, intercepté ou en touchdown.
  - Séparation = celle du moteur à la cible (geo.rec, en yards, bornée par le statut : libre 3-7, serré 1,6-2,9,
    couvert 0,4-1,5, doublé 0,8). C'est elle qui décide de la réception. La trace geo.cov ne sert qu'au dessin.
  - Air yards = profondeur de la route courue par la cible (call.route.depth) ; YAC = gain moins air yards.
  - Rôle -> joueur : WR1/WR2/WR3 -> <EQ>_WR1…, TE -> <EQ>_TE1, RB -> <EQ>_RB1, puis chaque remplacement (play.subs)
    change le titulaire du rôle jusqu'au suivant (vérifié : 42 588 cibles sur 42 588, semaine du 16/11).
  - Rush gagné = le rusher bat son bloqueur avant le lancer (pocket.duels[].t <= decision.throw_time).
  - Course : 1er contact = 1re position du porteur dans geo.sim.c (x depuis la ligne de mêlée) ; plaquage manqué =
    geo.sim.ev [instant, défenseur, 0].
"""
import collections
import math

VERSION = "ngs-1"

_TENTATIVE = {"complete", "incomplete", "interception", "touchdown", "fumble_lost"}
_COMPLETE = {"complete", "touchdown", "fumble_lost"}
_COURSE = {"run", "touchdown", "fumble_lost"}
_ROLE_DEFAUT = {"TE": "TE1", "RB": "RB1"}
SERRE = ("C", "D")                       # fenêtre serrée : cible couverte ou doublée


# ------------------------------------------------------------------ modèles « attendus »
def bande_prof(d):
    if d is None:
        return "?"
    return "b" if d < 0 else "s" if d < 5 else "m" if d < 10 else "i" if d < 20 else "d"


def bande_tt(t):
    if t is None:
        return "?"
    return "q" if t < 1.5 else "n" if t < 2.5 else "l" if t < 3.5 else "x"


def bande_boite(b):
    if b is None:
        return "?"
    return "5" if b <= 5 else "9" if b >= 9 else str(int(b))


def bande_down(dn, tg):
    return f"{min(int(dn or 1), 3)}{'c' if (tg or 10) <= 2 else 'm' if (tg or 10) <= 6 else 'l'}"


def _cles_comp(st, prof, pression, tt):
    """Clés du plus fin au plus large (la case parente lisse une case qui a peu d'actions)."""
    p = "p" if pression else "c"
    return [f"{st}|{prof}|{p}|{tt}", f"{st}|{prof}|{p}", f"{st}|{prof}", st, ""]


def _cles_yac(st, prof, rc):
    return [f"{st}|{prof}|{rc}", f"{st}|{prof}", st, ""]


def _cles_rush(boite, cls, dn):
    return [f"{boite}|{cls}|{dn}", f"{boite}|{cls}", cls, ""]


LISSAGE = 25                              # poids de la case parente (en actions)


def _estime(table, cles):
    """Moyenne lissée : chaque case tire vers sa parente avec un poids LISSAGE (de la plus large à la plus fine)."""
    v = None
    for k in reversed(cles):
        n, s = table.get(k, (0, 0.0))
        if v is None:
            v = s / n if n else 0.0
        else:
            v = (s + LISSAGE * v) / (n + LISSAGE)
    return v


def x_comp(m, st, prof, pression, tt):
    return _estime(m["comp"], _cles_comp(st, bande_prof(prof), pression, bande_tt(tt))) if m else None


def x_yac(m, st, prof, rc):
    return _estime(m["yac"], _cles_yac(st, bande_prof(prof), rc or "?")) if m else None


def x_rush(m, boite, cls, dn, tg):
    return _estime(m["rush"], _cles_rush(bande_boite(boite), cls or "?", bande_down(dn, tg))) if m else None


def entrainer(feeds, semaines=()):
    """Modèles appris sur des GameFeeds (semaines PASSÉES) : {comp, yac, rush}, chaque table {clé: [n, somme]}."""
    T = {"comp": collections.defaultdict(lambda: [0, 0.0]), "yac": collections.defaultdict(lambda: [0, 0.0]),
         "rush": collections.defaultdict(lambda: [0, 0.0])}

    def ajoute(t, cles, v):
        for k in cles:
            c = T[t][k]; c[0] += 1; c[1] += v
    for F in feeds:
        for P in _actions(F):
            q = P["q"]
            if q["kind"] == "att":
                ajoute("comp", _cles_comp(q["st"], bande_prof(q["ay"]), q["prs"], bande_tt(q["tt"])), float(q["cmp"]))
                if q["cmp"] and q["ay"] is not None:
                    ajoute("yac", _cles_yac(q["st"], bande_prof(q["ay"]), q["rc"] or "?"), float(q["yds"] - q["ay"]))
            elif q["kind"] == "run":
                ajoute("rush", _cles_rush(bande_boite(q["box"]), q["cls"] or "?", bande_down(q["dn"], q["tg"])),
                       float(q["yds"]))
    out = {"version": VERSION, "weeks": list(semaines)}
    for t, tab in T.items():
        out[t] = {k: [n, round(s, 2)] for k, (n, s) in sorted(tab.items())}
    return out


def _table_modele(m):
    """Le JSON garde des listes [n, somme] : on les lit comme des couples."""
    if not m:
        return None
    return {t: {k: (v[0], v[1]) for k, v in m.get(t, {}).items()} for t in ("comp", "yac", "rush")}


# ------------------------------------------------------------------ lecture d'un GameFeed
def _actions(F):
    """Chaque action utile d'un match, résumée : {"P": action, "off": équipe, "def": équipe, "q": résumé, "roles": …}."""
    G = F.get("game") or {}
    ab = {s: (G.get(s) or {}).get("abbr") for s in ("home", "away")}
    titulaires = {}                                       # (équipe, rôle) -> identifiant
    for P in F.get("plays") or []:
        for s in P.get("subs") or []:
            if s.get("in") and s.get("pos"):
                titulaires[(s["in"].split("_")[0], s["pos"])] = s["in"]
        off = ab.get(P.get("offense"))
        if not off:
            continue
        de = ab["away"] if off == ab["home"] else ab["home"]
        res, gain = P.get("result"), P.get("gain") or 0
        if res == "penalty" or (P.get("call") or {}).get("type") in ("kneel", "spike"):
            continue
        dec, geo = P.get("decision"), P.get("geo") or {}

        def qui(role, eq=off):
            return titulaires.get((eq, role)) or f"{eq}_{_ROLE_DEFAUT.get(role, role)}"
        if dec:
            act = dec.get("action")
            route = (P.get("call") or {}).get("route") or {}
            rec = {r[0]: r for r in geo.get("rec") or []}
            tgt = dec.get("target") or {}
            cib = rec.get(tgt.get("role")) if tgt else None
            tt = dec.get("throw_time") if dec.get("throw_time") is not None else geo.get("tt")
            q = {"kind": "db", "act": act, "res": res, "yds": gain, "tt": tt, "prs": bool(dec.get("pressure")),
                 "ttp": dec.get("time_to_pressure"), "blitz": bool(dec.get("blitz")), "read": dec.get("read"),
                 "mis": bool(dec.get("misread")), "qb": (dec.get("qb") or {}).get("id"),
                 "tgt": tgt.get("id"), "st": cib[2] if cib else None, "sep": cib[1] if cib else None,
                 "ay": route.get("depth"), "rc": dec.get("reception"), "cov": (dec.get("coverer") or {}).get("id"),
                 "cmp": res in _COMPLETE, "routes": [], "sack": res == "sack", "scr": act == "SCRAMBLE",
                 "away": act == "THROWAWAY"}
            if act == "LANCER" and res in _TENTATIVE and q["tgt"]:
                q["kind"] = "att"
                q["zone"] = zone_passe(geo, tgt.get("role"), P.get("ball_y"), route.get("depth"))
            for r in geo.get("rec") or []:
                q["routes"].append((qui(r[0]), r[1], r[2]))
            yield {"P": P, "off": off, "def": de, "q": q}
            continue
        if geo.get("k") == "run" and res in _COURSE:
            car = ((P.get("players") or {}).get("carrier") or {}).get("id")
            sim = geo.get("sim") or {}
            c0 = (sim.get("c") or [None])[0]
            q = {"kind": "run", "car": car, "yds": gain, "box": (P.get("run") or {}).get("box"), "cls": geo.get("cls"),
                 "dn": P.get("down"), "tg": P.get("to_go"), "ybc": c0[0] if c0 else None,
                 "ev": sim.get("ev") or [], "duels": geo.get("duels") or [],
                 "lane": couloir_course(geo)}
            yield {"P": P, "off": off, "def": de, "q": q}


# ------------------------------------------------------------------ cartes (NGS-6) : où vont les passes, où courent les porteurs
# Repère du moteur (vérifié le 19/11/2026 sur 2 852 courses) : une course notée L part vers les y plus petits que la balle,
# quelle que soit l'équipe qui attaque — y croissant = vers la droite de l'attaque.
COULOIRS_PASSE = ("L", "M", "R")                 # gauche, milieu (à 6 yards au plus de la balle), droite
PROFONDEURS = ("b", "s", "i", "d")               # derrière la ligne, 0-9, 10-19, 20+ yards
MILIEU = 6.0
COULOIRS_COURSE = ("LO", "LI", "RI", "RO")       # extérieur / intérieur, de chaque côté
_EXTERIEUR = {"outside", "perimeter", "option"}


def zone_passe(geo, role, ball_y, prof=None):
    """(couloir, profondeur) d'une passe : le couloir d'après le bout de la route de la cible au lancer (geo.cov, dixièmes
    de yard, en travers) ; la profondeur, celle de la route (prof, comme l'aDOT), sinon le bout de la trace."""
    cov = geo.get("cov") or {}
    r = next((x for x in cov.get("r") or [] if x and x[0] == role), None)
    if not r or len(r) < 5 or not r[4] or ball_y is None:
        return None
    x, y = r[4][-1][0] / 10, r[4][-1][1] / 10
    if prof is not None:
        x = prof
    dy = y - ball_y
    ln = "L" if dy < -MILIEU else "R" if dy > MILIEU else "M"
    return ln, "b" if x < 0 else "s" if x < 10 else "i" if x < 20 else "d"


def couloir_course(geo):
    """Couloir d'une course : côté (L / R) et extérieur (outside, perimeter, option) ou intérieur."""
    sd = geo.get("side")
    if sd not in ("L", "R"):
        return None
    return sd + ("O" if geo.get("cls") in _EXTERIEUR else "I")


def _carte_passe(c, q):
    z = q.get("zone")
    if not z:
        return
    k = f"pc:{z[0]}{z[1]}:"
    c[k + "a"] += 1; c[k + "c"] += q["cmp"]; c[k + "y"] += q["yds"] if q["cmp"] else 0
    c[k + "t"] += q["res"] == "touchdown"; c[k + "i"] += q["res"] == "interception"


def cartes(c):
    """Les cartes d'un joueur à partir de ses comptes : {"pass": [[couloir, profondeur, a, c, y, td, int], …],
    "run": [[couloir, n, yards, yards au-delà de l'attendu], …]} (cases vides omises)."""
    out = {}
    pas = []
    for ln in COULOIRS_PASSE:
        for pr in PROFONDEURS:
            k = f"pc:{ln}{pr}:"
            if c.get(k + "a"):
                pas.append([ln, pr, c[k + "a"], c.get(k + "c", 0), c.get(k + "y", 0), c.get(k + "t", 0), c.get(k + "i", 0)])
    if pas:
        out["pass"] = pas
    run = [[ln, c[f"rc:{ln}:n"], c.get(f"rc:{ln}:y", 0), round(c.get(f"rc:{ln}:x", 0), 1)]
           for ln in COULOIRS_COURSE if c.get(f"rc:{ln}:n")]
    if run:
        out["run"] = run
    return out


def ligue_cartes(agg):
    """Repères de la ligue pour les cartes : complétion par case, yards par course par couloir."""
    tot = collections.Counter()
    for pid, c in agg["players"].items():
        nom, pos, eq = agg["names"].get(pid) or [pid, "", ""]
        if pos == "QB":
            for k, v in c.items():
                if k.startswith("pc:"):
                    tot[k] += v
        for k, v in c.items():
            if k.startswith("rc:"):
                tot[k] += v
    return cartes(tot)


def _roster(F):
    out = {}
    G = F.get("game") or {}
    for s in ("home", "away"):
        tm = G.get(s) or {}
        for j in tm.get("roster") or []:
            if j.get("id"):
                out[j["id"]] = (j.get("name") or j["id"], j.get("pos") or "", tm.get("abbr"))
    return out


def compter(F, modeles=None):
    """Comptes bruts d'un match : {"players": {id: {…}}, "teams": {abbr: {…}}, "names": {id: [nom, poste, équipe]}}."""
    M = _table_modele(modeles)
    J = collections.defaultdict(collections.Counter)
    E = collections.defaultdict(collections.Counter)
    noms = _roster(F)
    vus = set()

    def nomme(pid, nom=None, pos=None, eq=None):
        if pid and pid not in noms:
            noms[pid] = (nom or pid, pos or "", eq or pid.split("_")[0])

    for A in _actions(F):
        P, q, off, de = A["P"], A["q"], A["off"], A["def"]
        dec = P.get("decision") or {}
        if q["kind"] in ("db", "att"):
            qb = q["qb"]
            nomme(qb, (dec.get("qb") or {}).get("name"), "QB", off)
            o, d = E[off], E[de]
            o["o_db"] += 1; d["d_db"] += 1
            o["o_prs"] += q["prs"]; d["d_prs"] += q["prs"]
            k = "d_blz" if q["blitz"] else "d_nob"
            d[k + "_db"] += 1; d[k + "_y"] += q["yds"]
            d["d_blitz"] += q["blitz"]
            if qb:
                vus.add(qb); j = J[qb]
                j["db"] += 1; j["prs_db"] += q["prs"]; j["sk"] += q["sack"]; j["scr"] += q["scr"]; j["away"] += q["away"]
                j["db_y"] += q["yds"]
                if q["prs"] and q["ttp"] is not None:
                    j["ttp_n"] += 1; j["ttp_s"] += q["ttp"]
            for pid, sep, st in q["routes"]:
                vus.add(pid); r = J[pid]
                r["rt"] += 1; r["rt_open"] += st == "L"; r["rt_sep"] += sep or 0
            if q["kind"] == "att":
                xc = x_comp(M, q["st"], q["ay"], q["prs"], q["tt"])
                o["o_att"] += 1; o["o_cmp"] += q["cmp"]; o["o_sep"] += q["sep"] or 0
                d["d_att"] += 1; d["d_cmp"] += q["cmp"]; d["d_sep"] += q["sep"] or 0
                if xc is not None:
                    o["o_xc"] += xc; d["d_xc"] += xc
                if q["tt"] is not None:
                    o["o_tt_n"] += 1; o["o_tt_s"] += q["tt"]
                if qb:
                    j = J[qb]
                    j["att"] += 1; j["cmp"] += q["cmp"]; j["pyds"] += q["yds"] if q["cmp"] else 0
                    _carte_passe(j, q)
                    j["int"] += q["res"] == "interception"
                    if q["tt"] is not None:
                        j["tt_n"] += 1; j["tt_s"] += q["tt"]
                    if q["ay"] is not None:
                        j["ay_n"] += 1; j["ay_s"] += q["ay"]
                    j["tw"] += q["st"] in SERRE
                    if q["read"]:
                        j["rd_n"] += 1; j["rd_1"] += q["read"] == 1
                    j["mis"] += q["mis"]
                    if q["prs"]:
                        j["prs_att"] += 1; j["prs_cmp"] += q["cmp"]
                    if xc is not None:
                        j["xc"] += xc; j["xc_n"] += 1; j["xc_cmp"] += q["cmp"]
                r = J[q["tgt"]]
                nomme(q["tgt"], (dec.get("target") or {}).get("name"), "", off)
                vus.add(q["tgt"])
                r["tgt"] += 1; r["rec"] += q["cmp"]; r["ryds"] += q["yds"] if q["cmp"] else 0
                _carte_passe(r, q)
                r["sep_s"] += q["sep"] or 0
                if q["ay"] is not None:
                    r["ay_n"] += 1; r["ay_s"] += q["ay"]
                if q["rc"] == "contested":
                    r["ct_t"] += 1; r["ct_c"] += q["cmp"]
                if xc is not None:
                    r["xc"] += xc; r["xc_n"] += 1; r["xc_cmp"] += q["cmp"]
                if q["cmp"] and q["ay"] is not None:
                    yac = q["yds"] - q["ay"]
                    r["yac_n"] += 1; r["yac_s"] += yac
                    xy = x_yac(M, q["st"], q["ay"], q["rc"])
                    if xy is not None:
                        r["xyac_n"] += 1; r["xyac_s"] += yac - xy
                cv = q["cov"]
                if cv:
                    nomme(cv, (dec.get("coverer") or {}).get("name"), (dec.get("coverer") or {}).get("pos"), de)
                    vus.add(cv); c = J[cv]
                    c["cv_t"] += 1; c["cv_c"] += q["cmp"]; c["cv_y"] += q["yds"] if q["cmp"] else 0
                    c["cv_sep"] += q["sep"] or 0
                    if xc is not None:
                        c["cv_xc"] += xc
            # la poche : chaque duel de protection (rusher contre bloqueur)
            po = P.get("pocket") or {}
            tt = q["tt"]
            duels = po.get("duels") or []
            premier = None
            for du in duels:
                ru, bl = (du.get("rusher") or {}), (du.get("blocker") or {})
                t = du.get("t")
                gagne = t is not None and tt is not None and t <= tt
                if ru.get("id"):
                    nomme(ru["id"], ru.get("name"), ru.get("pos"), de); vus.add(ru["id"])
                    r = J[ru["id"]]
                    r["pr_d"] += 1; r["pr_w"] += gagne; r["pr_dbl"] += bool(du.get("double"))
                    r["pr_free"] += bool(du.get("free"))
                    if gagne and (premier is None or t < premier[0]):
                        premier = (t, ru["id"])
                if bl.get("id") and not du.get("free"):
                    nomme(bl["id"], bl.get("name"), bl.get("pos"), off); vus.add(bl["id"])
                    b = J[bl["id"]]
                    b["pb_d"] += 1; b["pb_w"] += not gagne
            if q["prs"] and premier:
                J[premier[1]]["prs"] += 1
        elif q["kind"] == "run":
            car = q["car"]
            o, d = E[off], E[de]
            xr = x_rush(M, q["box"], q["cls"], q["dn"], q["tg"])
            o["o_car"] += 1; o["o_ryds"] += q["yds"]
            d["d_car"] += 1; d["d_ryds"] += q["yds"]
            if xr is not None:
                o["o_xr"] += xr; d["d_xr"] += xr
            if car:
                c = (P.get("players") or {}).get("carrier") or {}
                nomme(car, c.get("name"), "", off); vus.add(car)
                j = J[car]
                j["car"] += 1; j["ruyds"] += q["yds"]; j["stuff"] += q["yds"] <= 0
                j["box8"] += (q["box"] or 0) >= 8
                if xr is not None:
                    j["xr_n"] += 1; j["xr_s"] += q["yds"] - xr
                if q["lane"]:
                    j[f"rc:{q['lane']}:n"] += 1; j[f"rc:{q['lane']}:y"] += q["yds"]
                    if xr is not None:
                        j[f"rc:{q['lane']}:x"] += q["yds"] - xr
                if q["ybc"] is not None:
                    j["ct_n"] += 1; j["ybc_s"] += q["ybc"]; j["yaco_s"] += q["yds"] - q["ybc"]
                    j["mtf"] += sum(1 for e in q["ev"] if len(e) > 2 and not e[2])
            for e in q["ev"]:
                if len(e) > 2 and e[1]:
                    nomme(e[1], None, None, de); vus.add(e[1])
                    t = J[e[1]]; t["tk_a"] += 1; t["tk_m"] += not e[2]
            for du in q["duels"]:
                if len(du) >= 3 and du[0] and du[1]:
                    nomme(du[0], None, None, off); nomme(du[1], None, None, de)
                    vus.add(du[0]); vus.add(du[1])
                    J[du[0]]["rb_d"] += 1; J[du[0]]["rb_w"] += du[2] > 0
    G = F.get("game") or {}
    out = {"players": {k: {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items() if b}
                       for k, v in J.items()},
           "teams": {k: {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items() if b} for k, v in E.items()},
           "names": {k: list(noms[k]) for k in vus if k in noms},
           "gp": [(G.get(s) or {}).get("abbr") for s in ("home", "away")]}
    return out


def agreger(comptes):
    """Somme de comptes de plusieurs matchs, et matchs joués par équipe."""
    J = collections.defaultdict(collections.Counter)
    E = collections.defaultdict(collections.Counter)
    noms, gp = {}, collections.Counter()
    for c in comptes:
        for k, v in c["players"].items():
            J[k].update(v)
        for k, v in c["teams"].items():
            E[k].update(v)
        noms.update(c["names"])
        for t in c.get("gp") or []:
            if t:
                gp[t] += 1
    return {"players": J, "teams": E, "names": noms, "gp": gp}


# ------------------------------------------------------------------ le catalogue affiché
def _r(a, b, k=1.0):
    return a / b * k if b else None


# Chaque groupe : qui est qualifié (compte, par match de son équipe), tri par défaut, colonnes.
# Colonne : (clé, titre court, fonction(compte, ligue) -> valeur, format, sens, aide)
#   format : "s" secondes · "yd" yards · "pct" part (0-1) · "pp" points de pourcentage (signe) · "n" nombre · "sy" yards
#            signés · "sn" yards signés, entiers
#   sens   : +1 plus haut = mieux · -1 plus bas = mieux · 0 neutre
GROUPES = [
    {"key": "passing", "label": "Passing", "who": "Quarterbacks", "qual": ("att", 14), "sort": "cpoe",
     "cols": [
         ("tt", "Time to throw", lambda c, L: _r(c["tt_s"], c["tt_n"]), "s", 0,
          "Average time from the snap to the release, on every throw."),
         ("adot", "aDOT", lambda c, L: _r(c["ay_s"], c["ay_n"]), "yd", 0,
          "Average depth of target: how deep the route of the receiver he throws to goes."),
         ("cpoe", "CPOE", lambda c, L: _cpoe(c, L), "pp", 1,
          "Completion % over expected. The expected rate comes from past weeks: the receiver's separation, the depth, "
          "pressure and time to throw. Positive: he completes more than an average QB would on the same throws."),
         ("cmp", "Comp %", lambda c, L: _r(c["cmp"], c["att"]), "pct", 1, "Completed passes per attempt."),
         ("agg", "Aggressive", lambda c, L: _r(c["tw"], c["att"]), "pct", 0,
          "Share of throws into a tight window: the target was covered or double-covered."),
         ("fr", "1st read", lambda c, L: _r(c["rd_1"], c["rd_n"]), "pct", 0,
          "Share of throws to his first read in the progression."),
         ("prs", "Pressured", lambda c, L: _r(c["prs_db"], c["db"]), "pct", -1,
          "Share of dropbacks under pressure."),
         ("prsc", "Comp % pressured", lambda c, L: _r(c["prs_cmp"], c["prs_att"]), "pct", 1,
          "Completion % when the pass rush got home before the throw."),
         ("ttp", "Time to pressure", lambda c, L: _r(c["ttp_s"], c["ttp_n"]), "s", 1,
          "When he is pressured: average time from the snap to the first rusher getting home."),
         ("sk", "Sack %", lambda c, L: _r(c["sk"], c["db"]), "pct", -1, "Sacks per dropback."),
         ("scr", "Scramble %", lambda c, L: _r(c["scr"], c["db"]), "pct", 0, "Dropbacks where he takes off and runs."),
     ]},
    {"key": "receiving", "label": "Receiving", "who": "Receivers", "qual": ("tgt", 3), "sort": "tgt",
     "cols": [
         ("sep", "Separation", lambda c, L: _r(c["sep_s"], c["tgt"]), "yd", 1,
          "Average distance to the nearest defender when the ball is thrown to him (the engine's own measure)."),
         ("open", "Open rate", lambda c, L: _r(c["rt_open"], c["rt"]), "pct", 1,
          "Share of all his routes, thrown to him or not, where he gets open."),
         ("tgt", "Targets", lambda c, L: c["tgt"], "n", 0, "Passes thrown to him."),
         ("share", "Target share", lambda c, L: _r(c["tgt"], L["team_tgt"].get(c["_team"])), "pct", 0,
          "His part of his team's targets."),
         ("croe", "Catch % over exp.", lambda c, L: _croe(c, L), "pp", 1,
          "Catch rate over expected, from the same model as CPOE."),
         ("yac", "YAC / rec", lambda c, L: _r(c["yac_s"], c["yac_n"]), "yd", 1,
          "Yards after the catch: the gain past the depth of his route."),
         ("yacoe", "YAC over exp.", lambda c, L: _r(c["xyac_s"], c["xyac_n"]) - L["off_y"] if c["xyac_n"] else None, "sy", 1,
          "YAC per catch over what an average receiver gets on the same catch (separation, depth, contact)."),
         ("adot", "aDOT", lambda c, L: _r(c["ay_s"], c["ay_n"]), "yd", 0, "Average depth of his targets."),
         ("ct", "Contested catch %", lambda c, L: _r(c["ct_c"], c["ct_t"]), "pct", 1,
          "Catches per contested target (a defender on him at the catch)."),
     ]},
    {"key": "rushing", "label": "Rushing", "who": "Ball carriers", "qual": ("car", 6), "sort": "ryoe_c",
     "cols": [
         ("ryoe_c", "RYOE / carry", lambda c, L: _ryoe(c, L), "sy", 1,
          "Rushing yards over expected per carry. Expected from past weeks, with only what is known before the snap: "
          "men in the box, type of run, down and distance."),
         ("ryoe", "RYOE", lambda c, L: _ryoe(c, L, total=True), "sn", 1, "Rushing yards over expected, in total."),
         ("ypc", "Yds / carry", lambda c, L: _r(c["ruyds"], c["car"]), "yd", 1, "Rushing yards per carry."),
         ("ybc", "Before contact", lambda c, L: _r(c["ybc_s"], c["ct_n"]), "yd", 1,
          "Yards gained before the first defender reaches him, per carry."),
         ("yaco", "After contact", lambda c, L: _r(c["yaco_s"], c["ct_n"]), "yd", 1,
          "Yards gained after the first contact, per carry."),
         ("mtf", "Missed tackles", lambda c, L: c["mtf"], "n", 1, "Tackles he made defenders miss."),
         ("box8", "8+ box %", lambda c, L: _r(c["box8"], c["car"]), "pct", 0,
          "Share of carries against eight or more men in the box."),
         ("stuff", "Stuffed %", lambda c, L: _r(c["stuff"], c["car"]), "pct", -1, "Carries for no gain or a loss."),
     ]},
    {"key": "passrush", "label": "Pass rush", "who": "Pass rushers", "qual": ("pr_d", 12), "sort": "prwr",
     "cols": [
         ("prwr", "Win rate", lambda c, L: _r(c["pr_w"], c["pr_d"]), "pct", 1,
          "Pass rush win rate: he beats his blocker before the ball is out."),
         ("prs", "Pressures", lambda c, L: c["prs"], "n", 1, "Times he is the first rusher to get home."),
         ("dbl", "Double-teamed", lambda c, L: _r(c["pr_dbl"], c["pr_d"]), "pct", 0,
          "Share of his rushes against two blockers."),
         ("free", "Unblocked", lambda c, L: c["pr_free"], "n", 0, "Rushes where nobody blocked him."),
         ("rush", "Rushes", lambda c, L: c["pr_d"], "n", 0, "Pass rushes."),
     ]},
    {"key": "coverage", "label": "Coverage", "who": "Cover defenders", "qual": ("cv_t", 2), "sort": "cvy",
     "cols": [
         ("cvoe", "Catch % over exp.", lambda c, L: _cvoe(c, L), "pp", -1,
          "Catch rate allowed over expected when he is the defender responsible. Negative: tighter than average."),
         ("cvt", "Targets", lambda c, L: c["cv_t"], "n", 0, "Passes thrown at the receiver he is responsible for."),
         ("cvc", "Comp % allowed", lambda c, L: _r(c["cv_c"], c["cv_t"]), "pct", -1, "Completions allowed per target."),
         ("cvs", "Separation allowed", lambda c, L: _r(c["cv_sep"], c["cv_t"]), "yd", -1,
          "Average separation of his receiver at the throw."),
         ("cvy", "Yds / target", lambda c, L: _r(c["cv_y"], c["cv_t"]), "yd", -1, "Receiving yards allowed per target."),
     ]},
    {"key": "tackling", "label": "Tackling", "who": "Tacklers", "qual": ("tk_a", 1.5), "sort": "mtr",
     "cols": [
         ("mtr", "Missed tackle %", lambda c, L: _r(c["tk_m"], c["tk_a"]), "pct", -1,
          "Missed tackles per tackle attempt on run plays."),
         ("tka", "Attempts", lambda c, L: c["tk_a"], "n", 0, "Tackle attempts on run plays."),
         ("tkm", "Missed", lambda c, L: c["tk_m"], "n", -1, "Missed tackles on run plays."),
     ]},
    {"key": "blocking", "label": "Blocking", "who": "Blockers", "qual": ("pb_d", 15), "sort": "pbwr",
     "cols": [
         ("pbwr", "Pass block win rate", lambda c, L: _r(c["pb_w"], c["pb_d"]), "pct", 1,
          "He holds his rusher until the ball is out."),
         ("rbwr", "Run block win rate", lambda c, L: _r(c["rb_w"], c["rb_d"]), "pct", 1,
          "He wins his block at the point of attack on runs."),
         ("pbd", "Pass blocks", lambda c, L: c["pb_d"], "n", 0, "Pass protection snaps against a rusher."),
     ]},
]

EQUIPES = {"key": "teams", "label": "Teams", "who": "Teams", "sort": "o_cpoe",
           "cols": [
               ("o_tt", "Time to throw", lambda c, L: _r(c["o_tt_s"], c["o_tt_n"]), "s", 0, "Offense: time to throw."),
               ("o_prs", "Pressure allowed", lambda c, L: _r(c["o_prs"], c["o_db"]), "pct", -1,
                "Offense: share of dropbacks under pressure."),
               ("o_cpoe", "CPOE", lambda c, L: _r(c["o_cmp"] - c["o_xc"], c["o_att"], 100) - L["off_c"]
                if c["o_att"] else None, "pp", 1, "Offense: completion % over expected."),
               ("o_sep", "Separation", lambda c, L: _r(c["o_sep"], c["o_att"]), "yd", 1,
                "Offense: average separation of the target."),
               ("o_ryoe", "RYOE / carry", lambda c, L: _r(c["o_ryds"] - c["o_xr"], c["o_car"]) - L["off_r"]
                if c["o_car"] else None, "sy", 1, "Offense: rushing yards over expected per carry."),
               ("d_prs", "Pressure rate", lambda c, L: _r(c["d_prs"], c["d_db"]), "pct", 1,
                "Defense: share of opponent dropbacks under pressure."),
               ("d_blitz", "Blitz rate", lambda c, L: _r(c["d_blitz"], c["d_db"]), "pct", 0,
                "Defense: share of dropbacks where it blitzes."),
               ("d_blz_y", "Yds/db, blitz", lambda c, L: _r(c["d_blz_y"], c["d_blz_db"]), "yd", -1,
                "Defense: yards allowed per dropback when it blitzes."),
               ("d_nob_y", "Yds/db, no blitz", lambda c, L: _r(c["d_nob_y"], c["d_nob_db"]), "yd", -1,
                "Defense: yards allowed per dropback without a blitz."),
           ]}


def _cpoe(c, L):
    return _r(c["xc_cmp"] - c["xc"], c["xc_n"], 100) - L["off_c"] if c["xc_n"] else None


def _croe(c, L):
    return _cpoe(c, L)


def _cvoe(c, L):
    return _r(c["cv_c"] - c["cv_xc"], c["cv_t"], 100) - L["off_c"] if c["cv_t"] else None


def _ryoe(c, L, total=False):
    if not c["xr_n"]:
        return None
    if total:
        return c["xr_s"] - L["off_r"] * c["xr_n"]
    return c["xr_s"] / c["xr_n"] - L["off_r"]


_ARRONDI = {"s": 2, "yd": 1, "pct": 3, "pp": 1, "n": 0, "sy": 2, "sn": 0}


def _rond(v, fmt):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    n = _ARRONDI.get(fmt, 2)
    return int(round(v)) if n == 0 else round(v, n)


def _ligue(agg):
    """Recentrage de la ligue : les modèles viennent des semaines passées ; si le moteur a bougé depuis, la ligue
    entière serait décalée. On retire l'écart moyen de la ligue (CPOE et RYOE de la ligue = 0 par construction)."""
    E = agg["teams"]
    att = sum(c["o_att"] for c in E.values()); cmp_ = sum(c["o_cmp"] for c in E.values())
    xc = sum(c["o_xc"] for c in E.values())
    car = sum(c["o_car"] for c in E.values()); ry = sum(c["o_ryds"] for c in E.values())
    xr = sum(c["o_xr"] for c in E.values())
    tgt = collections.Counter()
    xy = sum(c.get("xyac_s", 0) for c in agg["players"].values())
    xyn = sum(c.get("xyac_n", 0) for c in agg["players"].values())
    for pid, c in agg["players"].items():
        if c.get("tgt"):
            tgt[(agg["names"].get(pid) or [None, None, pid.split("_")[0]])[2]] += c["tgt"]
    return {"off_c": (cmp_ - xc) / att * 100 if att else 0.0, "off_r": (ry - xr) / car if car else 0.0, "off_y": xy / xyn if xyn else 0.0,
            "team_tgt": tgt}


def _poste_ok(g, pos):
    """Les receveurs sont des WR/TE/RB, les passeurs des QB, etc. : un défenseur crédité d'une cible n'est pas listé."""
    if not pos:
        return True
    return {"passing": pos == "QB", "receiving": pos in ("WR", "TE", "RB", "FB"),
            "rushing": pos in ("RB", "QB", "WR", "FB", "TE"),
            "passrush": pos in ("EDGE", "DT", "DE", "LB", "NT", "OLB", "ILB", "CB", "S", "DL"),
            "coverage": pos in ("CB", "S", "LB", "NB", "FS", "SS", "OLB", "ILB"),
            "tackling": pos not in ("QB", "WR", "TE", "RB", "LT", "LG", "C", "RG", "RT", "OL"),
            "blocking": pos in ("LT", "LG", "C", "RG", "RT", "OL", "TE", "RB", "FB")}.get(g, True)


def tableaux(agg, modeles=None, ligue=None, facteur=1.0):
    """Statistiques finales : {"groups": [{key, label, who, cols: [...], rows: [...], league: {...}}], "teams": {...}}.
    Une ligne = un joueur qualifié (assez d'actions pour les matchs joués par son équipe). ligue : recentrage imposé
    (celui de la semaine, pour un seul match) ; sinon celui de agg. facteur : multiplie les seuils (0 : tout joueur qui a
    au moins une action du groupe, pour le récap d'un match)."""
    L = ligue or _ligue(agg)
    out = []
    for G in GROUPES:
        qk, par = G["qual"]
        rows = []
        for pid, c in agg["players"].items():
            nom, pos, eq = (agg["names"].get(pid) or [pid, "", pid.split("_")[0]])
            if not _poste_ok(G["key"], pos):
                continue
            gp = agg["gp"].get(eq, 0)
            if not gp or not c[qk] or c[qk] < par * gp * facteur:
                continue
            c = collections.Counter(c); c["_team"] = eq
            v = {k: _rond(f(c, L), fmt) for k, _, f, fmt, _, _ in G["cols"]}
            rows.append({"id": pid, "name": nom, "pos": pos, "team": eq, "n": c[qk], "v": v})
        rows.sort(key=lambda r: (r["v"].get(G["sort"]) is None, -(r["v"].get(G["sort"]) or 0) *
                                 next(s or 1 for k, _, _, _, s, _ in G["cols"] if k == G["sort"]), r["name"]))
        ligue = {}
        for k, _, _, fmt, _, _ in G["cols"]:
            xs = [r["v"][k] for r in rows if r["v"].get(k) is not None]
            ligue[k] = _rond(sum(xs) / len(xs), fmt) if xs else None
        out.append({"key": G["key"], "label": G["label"], "who": G["who"], "sort": G["sort"], "min": [qk, par],
                    "cols": [{"k": k, "l": l, "f": fmt, "s": s, "h": h} for k, l, _, fmt, s, h in G["cols"]],
                    "rows": rows, "league": ligue})
    rows = []
    for eq, c in agg["teams"].items():
        v = {k: _rond(f(c, L), fmt) for k, _, f, fmt, _, _ in EQUIPES["cols"]}
        rows.append({"id": eq, "name": eq, "pos": "", "team": eq, "n": agg["gp"].get(eq, 0), "v": v})
    rows.sort(key=lambda r: (r["v"].get("o_cpoe") is None, -(r["v"].get("o_cpoe") or 0), r["team"]))
    ligue = {}
    for k, _, _, fmt, _, _ in EQUIPES["cols"]:
        xs = [r["v"][k] for r in rows if r["v"].get(k) is not None]
        ligue[k] = _rond(sum(xs) / len(xs), fmt) if xs else None
    out.append({"key": "teams", "label": EQUIPES["label"], "who": EQUIPES["who"], "sort": EQUIPES["sort"], "min": None,
                "cols": [{"k": k, "l": l, "f": fmt, "s": s, "h": h} for k, l, _, fmt, s, h in EQUIPES["cols"]],
                "rows": rows, "league": ligue})
    return {"version": VERSION, "groups": out, "models": bool(modeles), "_ligue": L}


# ------------------------------------------------------------------ la statistique gratuite du jour
# (groupe, colonne, titre, phrase) : une par jour, en rotation ; le meilleur joueur qualifié dans le bon sens.
DU_JOUR = [
    ("passing", "tt", "Fastest release", "gets the ball out in"),
    ("receiving", "sep", "Most separation", "gets open by"),
    ("rushing", "ryoe_c", "Best rusher over expected", "gains over expected per carry:"),
    ("passrush", "prwr", "Top pass rusher", "beats his blocker on"),
    ("passing", "cpoe", "Most accurate passer", "completes over expected by"),
    ("blocking", "pbwr", "Best pass protector", "holds his rusher on"),
    ("receiving", "yacoe", "Most yards after the catch", "adds over expected per catch:"),
]


def stat_du_jour(tab, cle):
    """La statistique gratuite du Day recap (cle : n'importe quel entier stable dans la journée)."""
    if not tab:
        return None
    par = {g["key"]: g for g in tab["groups"]}
    for i in range(len(DU_JOUR)):
        gk, ck, titre, phrase = DU_JOUR[(cle + i) % len(DU_JOUR)]
        g = par.get(gk)
        if not g or not g["rows"]:
            continue
        col = next(c for c in g["cols"] if c["k"] == ck)
        rows = [r for r in g["rows"] if r["v"].get(ck) is not None]
        if not rows:
            continue
        sens = col["s"] or 1
        if col["f"] == "s" and ck == "tt":
            sens = -1                                      # le lancer le plus rapide
        best = min(rows, key=lambda r: (-r["v"][ck] * sens, r["name"]))
        return {"title": titre, "group": gk, "col": ck, "label": col["l"], "fmt": col["f"], "help": col["h"],
                "id": best["id"], "name": best["name"], "pos": best["pos"], "team": best["team"],
                "value": best["v"][ck], "league": g["league"].get(ck), "phrase": phrase}
    return None


# ------------------------------------------------------------------ fiches (NGS-5) : un joueur, une équipe, un match
# La statistique phare de chaque poste (gratuite sur la fiche du joueur) : (groupe, colonne).
# Une seconde colonne sert de repli quand la première n'a pas de valeur (sans modèles : ni CPOE ni RYOE).
PHARE = {"QB": ("passing", "cpoe", "tt"), "WR": ("receiving", "sep"), "TE": ("receiving", "sep"),
         "RB": ("rushing", "ryoe_c", "ypc"), "FB": ("rushing", "ryoe_c", "ypc"), "EDGE": ("passrush", "prwr"), "DT": ("passrush", "prwr"), "LB": ("tackling", "mtr"),
         "CB": ("coverage", "cvy"), "S": ("coverage", "cvy"), "LT": ("blocking", "pbwr"), "LG": ("blocking", "pbwr"),
         "C": ("blocking", "pbwr"), "RG": ("blocking", "pbwr"), "RT": ("blocking", "pbwr")}


def _rang(rows, k, s, v):
    """Rang de v parmi les lignes qualifiées (1 = le meilleur ; sens neutre : la plus grande valeur d'abord)."""
    xs = [r["v"][k] for r in rows if r["v"].get(k) is not None]
    if v is None or not xs:
        return None
    sens = -1 if s == -1 else 1
    return 1 + sum(1 for x in xs if x * sens > v * sens)


def _publique(tab):
    """Le JSON public des tableaux (sans le recentrage interne)."""
    return {k: v for k, v in tab.items() if not k.startswith("_")} if tab else None


def joueur(agg, tab, pid):
    """La fiche de suivi d'un joueur cette semaine : {"id", "name", "pos", "team", "headline", "groups"}.
    headline : la statistique phare de son poste (valeur, rang parmi les qualifiés, moyenne de la ligue) — gratuite.
    groups : chaque groupe où il a des actions, toutes les colonnes avec leur rang (Pro). Un joueur pas encore
    qualifié a ses valeurs, sans rang."""
    c = agg["players"].get(pid) if agg else None
    nom, pos, eq = (agg["names"].get(pid) if agg else None) or [pid, "", pid.split("_")[0]]
    out = {"id": pid, "name": nom, "pos": pos, "team": eq, "headline": None, "groups": [], "charts": {}}
    if not c:
        return out
    out["charts"] = cartes(c)
    L = tab["_ligue"]
    par_g = {g["key"]: g for g in tab["groups"]}
    gp = agg["gp"].get(eq, 0)
    for G in GROUPES:
        qk, seuil = G["qual"]
        if not c.get(qk) or not _poste_ok(G["key"], pos):
            continue
        cc = collections.Counter(c); cc["_team"] = eq
        T = par_g[G["key"]]
        ok = bool(gp) and cc[qk] >= seuil * gp
        stats = []
        for k, l, f, fmt, sn, h in G["cols"]:
            v = _rond(f(cc, L), fmt)
            stats.append({"k": k, "l": l, "f": fmt, "s": sn, "h": h, "v": v, "league": T["league"].get(k),
                          "rank": _rang(T["rows"], k, sn, v) if ok else None})
        out["groups"].append({"key": G["key"], "label": G["label"], "n": cc[qk], "min": [qk, seuil * gp],
                              "qualified": ok, "of": len(T["rows"]), "stats": stats})
    ph = PHARE.get(pos)
    if ph:
        g = next((x for x in out["groups"] if x["key"] == ph[0]), None)
        st = None
        for k in ph[1:]:
            st = next((x for x in g["stats"] if x["k"] == k and x["v"] is not None), None) if g else None
            if st:
                break
        if st:
            out["headline"] = dict(st, group=g["label"], qualified=g["qualified"], of=g["of"], n=g["n"], min=g["min"])
    return out


def equipe(tab, team):
    """Le profil de suivi d'une équipe : chaque colonne du groupe Teams, sa valeur, son rang sur les équipes."""
    T = next((g for g in tab["groups"] if g["key"] == "teams"), None) if tab else None
    r = next((x for x in T["rows"] if x["team"] == team), None) if T else None
    if not r:
        return None
    return {"team": team, "games": r["n"], "of": len(T["rows"]),
            "stats": [dict(c, v=r["v"].get(c["k"]), league=T["league"].get(c["k"]),
                           rank=_rang(T["rows"], c["k"], c["s"], r["v"].get(c["k"]))) for c in T["cols"]]}


def match(comptes, modeles, ligue):
    """Le suivi d'un match terminé : le profil de chaque équipe sur ce match et ses joueurs marquants (le passeur, le
    receveur le plus ciblé, le porteur le plus utilisé, le meilleur rusher), recentrés comme la semaine (ligue)."""
    agg = agreger([comptes])
    tab = tableaux(agg, modeles, dict(ligue, team_tgt=_ligue(agg)["team_tgt"]), facteur=0)  # cibles : celles du match
    par_g = {g["key"]: g for g in tab["groups"]}
    out = {"teams": [], "cols": par_g["teams"]["cols"]}
    choix = (("passing", "QB", lambda r: r["n"]), ("receiving", "Target", lambda r: r["n"]),
             ("rushing", "Carrier", lambda r: r["n"]), ("passrush", "Rusher", lambda r: (r["v"].get("prs") or 0, r["n"])))
    for eq in comptes.get("gp") or []:
        r = next((x for x in par_g["teams"]["rows"] if x["team"] == eq), None)
        if not r:
            continue
        pls = []
        for gk, role, cle in choix:
            G = par_g[gk]
            cands = [x for x in G["rows"] if x["team"] == eq]
            if cands:
                x = max(cands, key=cle)
                pls.append({"role": role, "group": gk, "id": x["id"], "name": x["name"], "pos": x["pos"], "n": x["n"],
                            "v": x["v"], "cols": [c["k"] for c in G["cols"]]})
        out["teams"].append({"team": eq, "v": r["v"], "players": pls})
    out["player_cols"] = {k: par_g[k]["cols"] for k in ("passing", "receiving", "rushing", "passrush")}
    return out


# ------------------------------------------------------------------ NGS-6 : récompenses de la semaine, historique
def _meilleur(tab, gk, ck):
    """Le meilleur joueur qualifié d'une colonne (dans son sens ; le temps de lancer : le plus court)."""
    g = next((x for x in tab["groups"] if x["key"] == gk), None) if tab else None
    if not g:
        return None, None
    col = next(c for c in g["cols"] if c["k"] == ck)
    rows = [r for r in g["rows"] if r["v"].get(ck) is not None]
    if not rows:
        return None, None
    sens = -1 if ck == "tt" else (col["s"] or 1)
    return min(rows, key=lambda r: (-r["v"][ck] * sens, r["name"])), col


def recompenses(tab):
    """Les récompenses de la semaine (une par statistique de DU_JOUR) : [{title, group, col, label, fmt, help, id, name,
    pos, team, value, league}]."""
    out = []
    par = {g["key"]: g for g in tab["groups"]} if tab else {}
    for gk, ck, titre, phrase in DU_JOUR:
        best, col = _meilleur(tab, gk, ck)
        if best:
            out.append({"title": titre, "group": gk, "col": ck, "label": col["l"], "fmt": col["f"], "help": col["h"],
                        "id": best["id"], "name": best["name"], "pos": best["pos"], "team": best["team"],
                        "value": best["v"][ck], "league": par[gk]["league"].get(ck), "phrase": phrase})
    return out


def historique(semaines, pid, nom, cle=None):
    """La statistique phare d'un joueur semaine après semaine : semaines = [(index, agg, tab)] dans l'ordre ; seulement
    les semaines où ce poste du roster était tenu par le même joueur (un rookie peut reprendre l'identifiant d'un
    retraité). cle : (groupe, colonne) imposés (sinon la stat phare de chaque semaine)."""
    out = []
    for idx, agg, tab in semaines:
        if not agg or not tab:
            continue
        n = agg["names"].get(pid)
        if not n or (nom and n[0] != nom):
            continue
        j = joueur(agg, tab, pid)
        h = j["headline"]
        if cle:
            g = next((x for x in j["groups"] if x["key"] == cle[0]), None)
            st = next((x for x in g["stats"] if x["k"] == cle[1]), None) if g else None
            h = dict(st, group=g["label"], qualified=g["qualified"], of=g["of"], n=g["n"]) if st else None
        if h and h["v"] is not None:
            out.append({"week": idx, "k": h["k"], "l": h["l"], "f": h["f"], "s": h["s"], "v": h["v"], "rank": h["rank"],
                        "of": h["of"], "qualified": h["qualified"], "league": h["league"]})
    return out


def formater(v, f, unite=True):
    """Une valeur dans son unité, comme le site (trkFmt) : « 1.84 s », « 14.3% », « +3.9 pts », « +2.57 yd »."""
    if v is None:
        return "—"
    def sg(x, d):
        return ("+" if x > 0 else "−" if x < 0 else "") + f"{abs(x):.{d}f}"
    if f == "s":
        return f"{v:.2f}" + (" s" if unite else "")
    if f == "yd":
        return f"{v:.1f}" + (" yd" if unite else "")
    if f == "pct":
        return f"{v * 100:.1f}%"
    if f == "pp":
        return sg(v, 1) + (" pts" if unite else "")
    if f == "sy":
        return sg(v, 2) + (" yd" if unite else "")
    if f == "sn":
        return sg(round(v), 0) + (" yd" if unite else "")
    return f"{round(v):,}"
