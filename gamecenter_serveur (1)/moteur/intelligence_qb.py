"""Intelligence du QB (bloc B) : les 8 attributs qui pèsent sur ses décisions.

    awareness          voit vite la situation (blitz, route « hot », soupape) ; temps de reconnaissance au snap
    processing         vitesse de lecture : temps entre deux lectures de la progression
    coverage_reading   lit juste la couverture : moins d'erreurs sur le statut d'un receveur (libre / serré / couvert)
    decision_making    discipline : ne force pas dans une couverture fermée, choisit le throwaway plutôt que le sack
    pocket_awareness   sent la pression arriver : glisse dans la poche, gagne du temps, évite des sacks
    pressure_response  garde sa lecture et sa précision quand la poche se referme
    anticipation       lance avant que le receveur ne soit démarqué (fenêtres serrées, lancer plus tôt)
    aggressiveness     style (pas une qualité) : tente les fenêtres serrées et les passes forcées plutôt que de descendre

Les rosters des franchises n'ont que 4 notes de QB (throw_power, throw_accuracy, mobility, decision_making) ; les
attributs absents sont DÉRIVÉS de ces notes (resserrés autour de 80 : COMPRESSION), de l'identité de la franchise (PROFILS) et d'un petit écart propre au
joueur (hash de son id : déterministe, sans consommer aucun hasard). Un attribut présent dans les notes du joueur
(clé du même nom) est pris tel quel. Ils ne s'ajoutent PAS à ses notes : l'OVR, les notes d'unité et les cotes ne
bougent pas ; le GameFeed les exporte à part (roster[].qb_iq) pour la fiche du QB.
"""
import random

ATTRIBUTS = ("awareness", "processing", "coverage_reading", "decision_making", "pocket_awareness",
             "pressure_response", "anticipation", "aggressiveness")
LIBELLES = {"awareness": "Awareness", "processing": "Processing", "coverage_reading": "Coverage reading",
            "decision_making": "Decision making", "pocket_awareness": "Pocket awareness",
            "pressure_response": "Pressure response", "anticipation": "Anticipation",
            "aggressiveness": "Aggressiveness"}

# attribut -> poids des notes existantes (dm = decision_making, acc = throw_accuracy, pow = throw_power, mob = mobility)
DERIVATION = {
    "awareness":         {"dm": 0.75, "acc": 0.25},
    "processing":        {"dm": 0.70, "acc": 0.30},
    "coverage_reading":  {"dm": 0.85, "acc": 0.15},
    "pocket_awareness":  {"dm": 0.60, "mob": 0.40},
    "pressure_response": {"dm": 0.50, "acc": 0.30, "pow": 0.20},
    "anticipation":      {"dm": 0.55, "acc": 0.45},
}
AGRESSIVITE_BASE = 50          # style : 50 = neutre ; + 0,3 par point de throw_power au-dessus de 80
NIVEAU, COMPRESSION = 80, 0.5  # attribut dérivé = 80 + 50 % de l'écart des notes à 80 (garde l'équilibre des franchises)
ECART_JOUEUR = 3               # écart propre au joueur : ± 3 points au plus

# identité des franchises (programme 12.1) : ce qui distingue leur QB à notes égales
PROFILS = {
    "CTX": {"processing": 2, "coverage_reading": 3, "awareness": 2, "aggressiveness": 5},         # intelligence, instinct
    "VEC": {"anticipation": 4, "pocket_awareness": -2, "aggressiveness": 28},                    # précision, risque
    "AEG": {"pocket_awareness": 5, "coverage_reading": 3, "pressure_response": 2, "aggressiveness": -18},  # discipline
    "MNL": {"pressure_response": 4, "pocket_awareness": 2, "aggressiveness": -5},                 # physique, solide
    # étape 6 (franchises 05-08 de la bible des identités)
    "AXM": {"processing": 3, "anticipation": 4, "coverage_reading": 2, "aggressiveness": -8},     # exécution, timing
    "GLT": {"pressure_response": 2, "aggressiveness": 8},                                        # opportuniste
    "CPH": {"awareness": 2, "pressure_response": 3, "pocket_awareness": -2, "aggressiveness": 4},  # mobile, improvise
    "NVA": {"coverage_reading": 2, "anticipation": -2, "pocket_awareness": 2, "aggressiveness": 22},  # bras, coups profonds
    # palier 2 (franchises 09-12)
    "PLS": {"processing": 5, "anticipation": 2, "pressure_response": 2, "aggressiveness": -4},  # vite, sans forcer
    "ONX": {"coverage_reading": 2, "pocket_awareness": 2, "aggressiveness": -14},                # protège le ballon
    "FRG": {"pocket_awareness": 4, "pressure_response": 3, "aggressiveness": -6},               # poche tenue
    "MRD": {"coverage_reading": 3, "pocket_awareness": 3, "aggressiveness": -20},               # territoire, prudence
    # palier 3 (franchises 13-16)
    "APX": {"anticipation": 3, "processing": 2, "pressure_response": 2, "aggressiveness": 0},     # finition
    "LTC": {"processing": 5, "coverage_reading": 2, "anticipation": 2, "aggressiveness": 2},      # lecture du nombre
    "ZPH": {"processing": 4, "anticipation": 4, "coverage_reading": 3, "aggressiveness": 12},     # distribution
    "BST": {"pocket_awareness": 2, "coverage_reading": 2, "aggressiveness": -14},                # prudente
}

_CLES = {"dm": "decision_making", "acc": "throw_accuracy", "pow": "throw_power", "mob": "mobility"}


def _borne(x):
    return int(round(max(30.0, min(99.0, x))))


def attributs_qb(joueur, franchise=None):
    """{attribut: note 30-99} d'un QB ({"id", "ratings"}) ; franchise = abréviation (profil d'identité)."""
    r = (joueur or {}).get("ratings") or {}
    notes = {k: float(r.get(v, 75)) for k, v in _CLES.items()}
    profil = PROFILS.get(franchise or "", {})
    rng = random.Random(f"qb-iq|{(joueur or {}).get('id', '')}")
    out = {}
    for a in ATTRIBUTS:
        if a in r:
            out[a] = _borne(float(r[a]))
            continue
        if a == "decision_making":
            out[a] = _borne(notes["dm"])
            continue
        if a == "aggressiveness":
            base = AGRESSIVITE_BASE + 0.3 * (notes["pow"] - 80)
        else:
            base = NIVEAU + COMPRESSION * (sum(w * notes[k] for k, w in DERIVATION[a].items()) - NIVEAU)
        out[a] = _borne(base + profil.get(a, 0) + rng.randint(-ECART_JOUEUR, ECART_JOUEUR))
    return out
