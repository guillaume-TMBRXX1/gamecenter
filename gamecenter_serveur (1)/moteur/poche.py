"""La poche et la ligne offensive (étape 7.1 « moteur plus intelligent », 21/10/2026).

Avant : la poche était un chrono — un seul « temps avant la pression » par passe (moteur.reaction_defensive), puis lancer,
pression, scramble ou sack (moteur.decision_qb, bloc B). Personne ne gagnait de duel, la poche n'avait pas de forme et
le QB ne bougeait pas dedans.

Ce module décompose ce temps, sans le changer (il est calibré : niveau des unités, rushers, protection, jeu de rush) :
  1. LES DUELS : chaque rusher face à son bloqueur — EDGE contre tackle (bord), DT contre guard (intérieur), le centre
     double le DT le plus dangereux ; les blitzeurs prennent le centre libre, puis le RB / TE qui restent protéger,
     sinon ils arrivent libres. Marge = rush (pass_rush, strength) − protection (pass_block, strength).
  2. LA PRESSION : au temps avant la pression, UN duel est perdu — tiré selon les marges (un profil, pas un niveau : le
     niveau est déjà dans le temps) ; les autres cèdent plus tard ou jamais. Forme de la poche : « edge » (les bords
     tournent autour des tackles : la poche se courbe en fer à cheval), « interior » (un DT enfonce le guard dans le
     QB), « collapse » (un second duel cède dans la foulée).
  3. LA RÉACTION DU QB (pocket awareness, mobilité) : pression des bords -> il MONTE dans la poche (step up) et garde
     quelques dixièmes ; pression intérieure -> il GLISSE de l'autre côté (slide) ; poche refermée -> il SORT de la
     poche (escape) du côté libre et LANCE EN COURANT (précision moindre, routes courtes et moyennes) ou jette le
     ballon hors du terrain, sinon scramble ou sack.
Python pur ; hasard dans son propre flux (« poche ») : le hasard du moteur n'est pas consommé.
"""
import math

VERSION = "poche-1"
FLUX = "poche"

OL = ("LT", "LG", "C", "RG", "RT")
COTE_OL = {"LT": "left", "LG": "left", "C": "middle", "RG": "right", "RT": "right"}
# marge d'un duel : poids des notes ; notes par défaut quand un joueur n'en a pas (RB / TE qui bloquent, LB / DB qui rushent)
POIDS_RUSH = {"pass_rush": 0.65, "strength": 0.35}
POIDS_BLOC = {"pass_block": 0.65, "strength": 0.35}
DEFAUT_RUSH = {"LB": 64.0, "S": 58.0, "CB": 55.0}
DEFAUT_BLOC = {"TE": 62.0, "RB": 56.0, "FB": 64.0}
DOUBLE = 9.0                     # un DT doublé (centre libre) perd d'autant
ECHELLE = 6.0                    # tirage du duel perdu : poids exp(marge / ECHELLE)
BORD = 1.15                      # un rusher de bord gagne un peu plus souvent (vitesse, angle)
LIBRE = 6.0                      # un blitzeur que personne ne prend
SECOND = {"base": 5.5, "echelle": 12.0, "collapse": 0.55}    # second duel perdu : délai moyen (s) ; « collapse » en deçà
# jeux de rush de l'extension (moteur.playbook_expansion.RUSH) : où la pression a le plus de chances de venir
RUSH_COTE = {"EDGE_RUSH": ("edge", 1.8), "INTERIOR_COLLAPSE": ("interior", 1.8), "INTERIOR_STUNT": ("interior", 1.5),
             "TEX_STUNT": ("interior", 1.4), "ET_STUNT": ("interior", 1.3), "LONG_STUNT": ("interior", 1.3),
             "CONTAIN_RUSH": ("interior", 1.3)}
# réaction du QB (attributs effectifs du bloc B autour de REF = 80 ; mobilité : note brute)
REACTION = {
    "monte": {"base": 0.40, "pa": 0.012, "min": 0.10, "max": 0.80, "gain": (0.20, 0.40)},     # step up (edge)
    "glisse": {"base": 0.30, "pa": 0.010, "min": 0.08, "max": 0.65, "gain": (0.15, 0.30)},    # slide (interior)
    "sort": {"base": 0.14, "mob": 0.012, "pa": 0.006, "collapse": 0.12, "min": 0.03, "max": 0.70,
             "gain": (0.50, 0.90)},                                                              # escape
}
AVANCE = 0.12                    # la pression arrive d'autant plus tôt : compense le temps gagné en réagissant (calibration)
EN_COURANT = {"inc": 1.10, "int": 1.08, "classes": ("court", "moyen")}   # lancer en courant : précision, routes
FIN_HORS_POCHE = {"throwaway": 1.4, "scramble": 1.3, "sack": 1.0}        # sorti de la poche : il peut jeter le ballon


def _borne(x, a, b):
    return max(a, min(b, x))


def _note(j, cle, defaut):
    return float(((j or {}).get("ratings") or {}).get(cle, defaut))


def force_rush(j):
    d = DEFAUT_RUSH.get((j or {}).get("pos"), 70.0)
    return sum(w * _note(j, k, d) for k, w in POIDS_RUSH.items())


def force_bloc(j):
    d = DEFAUT_BLOC.get((j or {}).get("pos"), 70.0)
    return sum(w * _note(j, k, d) for k, w in POIDS_BLOC.items())


def _qui(j):
    return None if not j else {"id": j.get("id", ""), "name": j.get("name", ""), "pos": j.get("pos", "")}


def affecter(ligne, rushers_dispo, n_rushers, protecteurs=()):
    """Duels de la passe : [{rusher, bloqueur, cote, type, marge, libre, double}].

    ligne         : {"LT": joueur, …, "RT": joueur} (joueur : {"id", "name", "pos", "ratings"})
    rushers_dispo : {"EDGE": [..], "DT": [..], "LB": [..], "S": [..], "CB": [..]} (titulaires d'abord)
    n_rushers     : rushers de l'appel (moteur.reaction_defensive : 3 à 7)
    protecteurs   : RB / TE qui restent protéger (protection de l'extension, plan de jeu du bloc D)
    """
    edges, dts = list(rushers_dispo.get("EDGE") or []), list(rushers_dispo.get("DT") or [])
    blitz = list(rushers_dispo.get("LB") or []) + list(rushers_dispo.get("S") or [])[:1] + list(rushers_dispo.get("CB") or [])[:1]
    base = [("EDGE", edges[0] if edges else None, "LT"), ("EDGE", edges[1] if len(edges) > 1 else None, "RT"),
            ("DT", dts[0] if dts else None, "LG"), ("DT", dts[1] if len(dts) > 1 else None, "RG")]
    base = [b for b in base if b[1] is not None]
    n = max(3, min(7, int(n_rushers or 4)))
    if n == 3:                                   # rush à trois : le second DT recule
        base = [b for b in base if not (b[0] == "DT" and b[2] == "RG")]
    duels = []
    for kind, r, poste in base[:n]:
        b = ligne.get(poste)
        duels.append({"rusher": r, "bloqueur": b, "cote": COTE_OL[poste], "type": "edge" if kind == "EDGE" else "interior",
                      "marge": force_rush(r) - force_bloc(b), "libre": b is None, "double": False})
    restants = n - len(duels)
    libres_bloc = [("C", ligne.get("C"))] + [(p.get("pos", "RB"), p) for p in protecteurs]
    for k in range(max(0, restants)):
        r = blitz[k] if k < len(blitz) else None
        if r is None:
            break
        if libres_bloc:
            poste, b = libres_bloc.pop(0)
            cote = "middle" if poste == "C" else ("right" if k % 2 else "left")
            duels.append({"rusher": r, "bloqueur": b, "cote": cote, "type": "interior" if poste in ("C", "RB") else "edge",
                          "marge": force_rush(r) - force_bloc(b), "libre": False, "double": False})
        else:
            duels.append({"rusher": r, "bloqueur": None, "cote": "middle" if k % 2 == 0 else ("left" if k % 4 == 1 else "right"),
                          "type": "interior" if r.get("pos") == "LB" else "edge", "marge": 15.0, "libre": True, "double": False})
    if libres_bloc and libres_bloc[0][0] == "C":           # le centre libre double le DT le plus dangereux
        dt = [d for d in duels if d["type"] == "interior" and d["rusher"] and d["rusher"].get("pos") == "DT"]
        if dt:
            cible = max(dt, key=lambda d: d["marge"])
            cible["double"] = True
            cible["marge"] -= DOUBLE
    return duels


class Poche:
    """La poche d'une passe : duels, duel perdu au temps avant la pression, forme, réaction du QB."""

    def __init__(self, duels, rng, rush=None):
        self.duels, self.ttp, self.rng, self.rush = duels, None, rng, rush
        self.premier, self.second, self.forme, self.cote = None, None, "clean", None
        self.reaction = None

    def armer(self, ttp):
        """Le temps avant la pression du QB (bloc B : poche, pocket awareness) : quel duel cède alors, et les suivants."""
        self.ttp = float(ttp)
        self._pression()
        return self

    def _pression(self):
        if not self.duels:
            return
        pref = RUSH_COTE.get(self.rush or "")
        w = []
        for d in self.duels:
            x = math.exp(_borne(d["marge"], -30.0, 30.0) / ECHELLE) * (BORD if d["type"] == "edge" else 1.0)
            if d["libre"]:
                x *= LIBRE
            if pref and d["type"] == pref[0]:
                x *= pref[1]
            w.append(x)
        u, acc, i0 = self.rng.random() * sum(w), 0.0, len(w) - 1
        for i, x in enumerate(w):
            acc += x
            if u <= acc:
                i0 = i
                break
        for i, d in enumerate(self.duels):
            if i == i0:
                d["t"] = round(self.ttp, 2)
            elif d["libre"]:
                d["t"] = round(self.ttp + 0.1 + 0.2 * self.rng.random(), 2)
            else:
                moy = SECOND["base"] * math.exp(-_borne(d["marge"], -30.0, 30.0) / SECOND["echelle"])
                d["t"] = round(self.ttp + self.rng.expovariate(1.0 / max(0.1, moy)), 2)
        self.premier = self.duels[i0]
        autres = sorted((d for d in self.duels if d is not self.premier), key=lambda d: d["t"])
        self.second = autres[0] if autres else None
        if self.second is not None and self.second["t"] - self.ttp <= SECOND["collapse"]:
            self.forme = "collapse"
        else:
            self.forme = self.premier["type"]
        self.cote = self.premier["cote"]

    def reagir(self, qb_iq, mobilite):
        """Réaction du QB quand la pression arrive : {"kind": step_up / slide / escape / none, "gain": s, "side"}."""
        pa = float((qb_iq or {}).get("pocket_awareness", 80.0))
        rng, R = self.rng, REACTION
        if self.premier is None:
            self.reaction = {"kind": "none", "gain": 0.0, "side": None}
            return self.reaction
        libre = {"left": "right", "right": "left"}.get(self.cote) or ("left" if rng.random() < 0.5 else "right")
        if self.forme == "edge":
            p = _borne(R["monte"]["base"] + (pa - 80) * R["monte"]["pa"], R["monte"]["min"], R["monte"]["max"])
            if rng.random() < p:
                self.reaction = {"kind": "step_up", "gain": round(rng.uniform(*R["monte"]["gain"]), 2), "side": None}
                return self.reaction
        elif self.forme == "interior":
            p = _borne(R["glisse"]["base"] + (pa - 80) * R["glisse"]["pa"], R["glisse"]["min"], R["glisse"]["max"])
            if rng.random() < p:
                self.reaction = {"kind": "slide", "gain": round(rng.uniform(*R["glisse"]["gain"]), 2), "side": libre}
                return self.reaction
        s = R["sort"]
        p = s["base"] + (float(mobilite) - 70) * s["mob"] + (pa - 80) * s["pa"] + (s["collapse"] if self.forme == "collapse" else 0.0)
        if rng.random() < _borne(p, s["min"], s["max"]):
            self.reaction = {"kind": "escape", "gain": round(rng.uniform(*s["gain"]), 2), "side": libre}
            return self.reaction
        self.reaction = {"kind": "none", "gain": 0.0, "side": None}
        return self.reaction

    def journal(self, decision=None):
        """Ce que le GameFeed garde (play.pocket) : duels (qui, contre qui, quand), forme, réaction, lancer en courant."""
        t_fin = getattr(decision, "temps_lancer", None)
        reac = self.reaction or {"kind": "none", "gain": 0.0, "side": None}
        sous = self.premier is not None and t_fin is not None and t_fin >= self.ttp - 1e-9
        out = {"version": VERSION, "ttp": round(self.ttp, 2) if self.ttp is not None else None,
               "shape": self.forme if sous else "clean",
               "duels": [{"rusher": _qui(d["rusher"]), "blocker": _qui(d["bloqueur"]), "side": d["cote"], "type": d["type"],
                          "margin": round(d["marge"], 1), "free": d["libre"], "double": d["double"], "t": d.get("t")}
                         for d in self.duels]}
        if sous:
            out["beaten"] = self.duels.index(self.premier)
            out["reaction"] = reac["kind"]
            if reac.get("side"):
                out["side"] = reac["side"]
            out["on_run"] = bool(getattr(decision, "en_courant", False))
        return out

    def vainqueur(self):
        """Le rusher qui a gagné son duel (crédité du sack)."""
        return (self.premier or {}).get("rusher")
