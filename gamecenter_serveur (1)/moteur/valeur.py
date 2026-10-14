"""Valeur d'une situation : points attendus (EP) et probabilité de victoire (WP) ; décision du 4e essai.

Constat (semaine du 12/10/2026, 279 matchs) : le 4e essai suivait deux seuils fixes du coordinateur (`go_max_to_go`,
`go_min_yard_line`) — jouer ou non, sans calcul : 4e et 1 entre ses 30 et le milieu de terrain joué 20 % du temps,
4e et 4-6 entre les 35 et les 10 adverses 11 % ; seules les 45 dernières secondes du Q2 / Q4 avaient un calcul
(fin_de_periode).

Ce module donne une VALEUR à chaque option, partout sur le terrain et à tout moment :
  EP  points attendus d'un 1er essai à `en_but` yards de l'en-but adverse : prochain score de la mi-temps (touchdown
      7, field goal 3, safety −2 ; positif pour l'équipe qui a le ballon). Mesuré sur 597 matchs du moteur (semaines du
      28/09 au 12/10, 77 283 actions) : le moteur marque plus que la NFL (≈ 52 points par match), sa table aussi.
  WP  probabilité de victoire de l'équipe qui a le ballon : la marge finale suit une loi normale centrée sur
      écart + EP de la possession (+ l'avantage attendu des unités sur le temps qui reste), d'écart-type
      SIGMA × (part du match qui reste)^EXPOSANT — mesuré : 13,2 points sur un match, 10,3 à mi-match, 5,8 au dernier
      dixième (les points arrivent par paquets de 3 et 7 : plus large en fin de match qu'une racine carrée).
  4e essai : JOUER (conversion mesurée par distance, gain moyen quand c'est converti), FIELD GOAL (même barème que le
      moteur, distance ≤ portée du coordinateur), PUNT (net mesuré selon la position). Chaque option mène à un état dont
      on lit la WP ; le choix est le meilleur, à un biais près : l'IDENTITÉ du coordinateur (agressivité, 0 prudent -> 1
      agressif, depuis ses réglages du 4e essai) déplace la frontière de BIAIS points, et la prudence grandit dans son
      propre camp (PRUDENCE_CAMP). Les écarts de WP sont convertis
      en points (pente de la WP au score actuel) pour que le biais ait le même sens au 1er quart-temps et à la fin.
      Match gagné (pente presque nulle, attaque qui mène) : None — le coordinateur garde sa règle (garbage time).
      Menée, l'équipe perd sa prudence au fil du dernier quart-temps : il faut tenter sa chance.
Déterministe (aucun tirage). Même état -> même décision.
"""
import math

VERSION = "valeur-1"

# EP d'un 1er essai (et 10, ou « and goal ») selon la distance de l'en-but (centre de tranche de 5 yards, lissé sur 3)
EP_1ER = {2: 6.38, 7: 6.24, 12: 5.92, 17: 5.59, 22: 5.26, 27: 4.95, 32: 4.58, 37: 4.24, 42: 3.85, 47: 3.47,
          52: 3.08, 57: 2.73, 62: 2.48, 67: 2.12, 72: 1.86, 77: 1.50, 82: 1.03, 87: 0.53, 92: -0.05, 97: -0.22}
# conversion d'un 3e / 4e essai selon la distance à gagner (mesurée, lissée, décroissante ; 15 = 15 et plus)
CONVERSION = {1: .67, 2: .60, 3: .565, 4: .555, 5: .54, 6: .50, 7: .44, 8: .41, 9: .38, 10: .345, 11: .31, 12: .25,
              13: .21, 14: .17, 15: .12}
# gain moyen quand l'essai est converti (mesuré)
GAIN_CONVERTI = {1: 7.8, 2: 8.3, 3: 9.1, 4: 11.3, 5: 11.6, 6: 11.9, 7: 13.2, 8: 14.5, 9: 15.3, 10: 15.9, 11: 16.3,
                 12: 16.6, 13: 17.9, 14: 18.6, 15: 21.5}
# punt : yards nets (de la ligne de scrimmage au départ de l'adversaire) selon la distance de l'en-but (mesuré)
PUNT_NET = {30: 14.0, 35: 20.2, 40: 27.9, 45: 34.6, 50: 40.9, 55: 44.3, 60: 45.1}
DEPART_APRES_SCORE = 75          # en-but de l'équipe qui reçoit le coup d'envoi (touchback aux 25)
VALEUR_TD = 6.94                 # 6 + point après touchdown (≈ 94 %)
SIGMA = 13.2                     # écart-type de la marge sur un match entier (mesuré)
EXPOSANT = 0.38                  # mesuré : 7,3 au dernier cinquième, 8,7 aux 3 derniers dixièmes
SIGMA_MIN = 1.5
AVANTAGE_PAR_POINT = 0.5         # marge attendue par point d'écart des unités (attaque − défense) sur un match entier
TEMPS_DRIVE = (20, 1.6)          # s (échelle NFL) : temps pour aller marquer depuis `en_but` (20 + 1,6 s par yard)
QUART_NFL = 900
P_FG_MIN = 0.20                  # en dessous, le field goal n'est pas une option
BIAIS = (-2.5, 0.5)              # points : agressivité 0 (prudent) … 1 (agressif)
PRUDENCE_CAMP = 1.5              # points de plus exigés pour jouer depuis sa ligne de but (0 au milieu du terrain) :
                                 # un échec dans son camp se paie (et se voit) plus qu'ailleurs
PENTE_MIN = 0.001                # WP par point : en dessous, le match est plié -> comparaison des points attendus


def _interp(table, x):
    ks = sorted(table)
    if x <= ks[0]:
        return table[ks[0]]
    if x >= ks[-1]:
        return table[ks[-1]]
    for a, b in zip(ks, ks[1:]):
        if a <= x <= b:
            return table[a] + (table[b] - table[a]) * (x - a) / (b - a)
    return table[ks[-1]]


def points_attendus(en_but):
    """EP d'un 1er essai à `en_but` yards de l'en-but adverse (1-99)."""
    return _interp(EP_1ER, max(1, min(99, en_but)))


def conversion(a_gagner, ecart_unites=0.0):
    p = CONVERSION[max(1, min(15, int(round(a_gagner))))]
    return max(0.02, min(0.95, p * max(0.8, min(1.2, 1 + 0.015 * ecart_unites))))


def probabilite_fg(distance, special_teams_rating=75.0):
    """Même barème que le moteur (calculate_field_goal_probability, notebook 07 ; fin_de_periode)."""
    base = (0.98 if distance <= 30 else 0.92 if distance <= 40 else 0.80 if distance <= 50 else 0.65 if distance <= 60
            else 0.45 if distance <= 70 else 0.15)
    return round(max(0.01, min(0.99, base + (special_teams_rating - 75) / 100)), 4)


def depart_apres_punt(en_but):
    """En-but de l'équipe qui reçoit le punt."""
    net = _interp(PUNT_NET, en_but)
    return max(1, min(99, 100 - en_but + net))


def _phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def _densite(z):
    return math.exp(-z * z / 2) / math.sqrt(2 * math.pi)


def _poids_possession(secondes_mi_temps, k, en_but):
    """Part de l'EP d'une possession qui compte encore (fin de mi-temps : plus le temps d'aller marquer)."""
    if secondes_mi_temps is None:
        return 1.0
    besoin = (TEMPS_DRIVE[0] + TEMPS_DRIVE[1] * max(1, en_but)) * k
    return max(0.0, min(1.0, secondes_mi_temps / max(1.0, besoin)))


def _loi(ecart, part, ep, avantage):
    mu = ecart + ep + avantage * part
    sd = max(SIGMA_MIN, SIGMA * max(0.0, part) ** EXPOSANT)
    return mu, sd


def probabilite_victoire(ecart, part_restante, en_but=None, avantage=0.0, poids_ep=1.0):
    """WP de l'équipe qui a le ballon (1er essai à `en_but` ; None : sans possession).

    ecart : ses points − ceux de l'adversaire ; part_restante : part du temps réglementaire qui reste (0-1) ;
    avantage : marge attendue sur un match entier (unités) ; poids_ep : part de l'EP qui compte encore.
    """
    ep = 0.0 if en_but is None else poids_ep * points_attendus(en_but)
    mu, sd = _loi(ecart, part_restante, ep, avantage)
    return _phi(mu / sd)


def _etat(prise, ecart, en_but, part, avantage, temps):
    """WP de l'attaque d'origine quand `prise` ("att" / "def") a le ballon à `en_but` yards de SON en-but adverse.

    temps = (secondes qui restent dans la mi-temps, échelle k) : la possession ne vaut son EP que si elle a le temps."""
    poids = _poids_possession(temps[0], temps[1], en_but)
    if prise == "att":
        return probabilite_victoire(ecart, part, en_but, avantage, poids)
    return 1.0 - probabilite_victoire(-ecart, part, en_but, -avantage, poids)


def _ep_etat(prise, points, en_but):
    """Points attendus (vue de l'attaque d'origine) : points marqués + EP de la possession suivante."""
    ep = points_attendus(en_but)
    return points + (ep if prise == "att" else -ep)


def agressivite_biais(agressivite):
    a = max(0.0, min(1.0, float(agressivite)))
    return BIAIS[0] + a * (BIAIS[1] - BIAIS[0])


def options_4e(en_but, a_gagner, ecart, part, k=1.0, secondes_mi_temps=None, special_teams_rating=75.0,
               ecart_unites=0.0, fg_max=65, avantage=0.0):
    """{option: (WP, EP)} pour JOUER / FG / PUNT (FG absent hors de portée)."""
    temps = (secondes_mi_temps, k)
    en_but = max(1, int(round(en_but)))
    a_gagner = max(1, int(round(a_gagner)))
    p = conversion(a_gagner, ecart_unites)
    out = {}
    # JOUER : converti -> 1er essai plus loin (ou touchdown) ; manqué -> ballon à l'adversaire sur place
    rate = ("def", ecart, 100 - en_but)
    if a_gagner >= en_but:                                    # 4e et but
        reussi = ("def", ecart + VALEUR_TD, DEPART_APRES_SCORE)
        pts_ok = VALEUR_TD
    else:
        nouvel = en_but - GAIN_CONVERTI[min(15, a_gagner)]
        if nouvel <= 0:
            reussi, pts_ok = ("def", ecart + VALEUR_TD, DEPART_APRES_SCORE), VALEUR_TD
        else:
            reussi, pts_ok = ("att", ecart, nouvel), 0.0
    wp = p * _etat(*reussi, part, avantage, temps) + (1 - p) * _etat(*rate, part, avantage, temps)
    ep = p * _ep_etat(reussi[0], pts_ok, reussi[2]) + (1 - p) * _ep_etat("def", 0.0, rate[2])
    out["JOUER"] = (wp, ep, p)
    # FIELD GOAL (distance = en-but + 17) : réussi -> 3 points, coup d'envoi ; manqué -> ballon à l'adversaire sur place
    dist = en_but + 17
    pf = probabilite_fg(dist, special_teams_rating)
    if dist <= fg_max and pf >= P_FG_MIN:
        ok, ko = ("def", ecart + 3, DEPART_APRES_SCORE), ("def", ecart, 100 - en_but)
        wp = pf * _etat(*ok, part, avantage, temps) + (1 - pf) * _etat(*ko, part, avantage, temps)
        ep = pf * _ep_etat("def", 3.0, DEPART_APRES_SCORE) + (1 - pf) * _ep_etat("def", 0.0, 100 - en_but)
        out["FG"] = (wp, ep, pf)
    # PUNT
    adv = depart_apres_punt(en_but)
    out["PUNT"] = (_etat("def", ecart, adv, part, avantage, temps), _ep_etat("def", 0.0, adv), None)
    return out


def quatrieme_essai(en_but, a_gagner, ecart, quart, secondes, quart_secondes=180, special_teams_rating=75.0,
                    ecart_unites=0.0, agressivite=0.5, fg_max=65, duree_action=6):
    """Décision du 4e essai : {"choix": "JOUER" | "FG" | "PUNT", "wp": {…}, "ep": {…}, "p": {…}, "raison", …}, ou None
    quand l'attaque a déjà gagné (le coordinateur garde sa règle). Menée, la prudence d'identité s'efface au fil du
    dernier quart-temps (en prolongation, menée = dernière possession : plus aucune prudence).

    en_but : yards jusqu'à l'en-but adverse ; ecart : attaque − défense ; quart : 1-4 (5+ : prolongation) ;
    secondes : secondes restantes dans le quart-temps ; quart_secondes : longueur d'un quart-temps du match ;
    agressivite : 0-1 (transformation.agressivite des réglages du coordinateur) ; fg_max : portée du coordinateur.
    """
    k = quart_secondes / QUART_NFL
    total = 4 * quart_secondes
    if quart <= 4:
        reste = (4 - quart) * quart_secondes + max(0, secondes - duree_action)
        part = max(0.0, reste / total)
        mi_temps = (secondes if quart in (2, 4) else secondes + quart_secondes) - duree_action
    else:
        part, mi_temps = max(0.0, (secondes - duree_action) / total), secondes - duree_action
    avantage = AVANTAGE_PAR_POINT * max(-15.0, min(15.0, ecart_unites))
    opts = options_4e(en_but, a_gagner, ecart, part, k, mi_temps, special_teams_rating, ecart_unites, fg_max, avantage)
    # pente de la WP (par point) : conversion des écarts de WP en points, pour le biais d'identité
    mu, sd = _loi(ecart, part, 0.0, avantage)
    pente = _densite(mu / sd) / sd
    biais = agressivite_biais(agressivite)
    prudence = PRUDENCE_CAMP * max(0.0, en_but - 50) / 50
    if pente < PENTE_MIN and ecart >= 0:
        return None                                       # match gagné (ou nul et sans enjeu) : règle du coordinateur
    if ecart < 0:
        # menée, la prudence s'efface quand le temps file : entière jusqu'au dernier quart-temps, nulle à la fin
        urgence = 0.0 if quart >= 5 else max(0.0, min(1.0, part * 4))
        biais, prudence = biais * urgence, prudence * urgence
    pente = max(pente, 1e-12)
    def score(opt):
        wp, ep, _ = opts[opt]
        v = wp / pente                                    # en points
        return v + (biais - prudence if opt == "JOUER" else 0.0)
    menee = ecart < 0
    choix = max(sorted(opts), key=lambda o: (round(score(o), 9), menee and o == "JOUER"))   # menée : à égalité, jouer
    kick = max((o for o in opts if o != "JOUER"), key=lambda o: opts[o][0])
    wp_j, ep_j, p_j = opts["JOUER"]
    wp_k, ep_k, _ = opts[kick]
    nom = {"JOUER": "go", "FG": "field goal", "PUNT": "punt"}
    detail = f"{nom['JOUER']} {wp_j:.0%} vs {nom[kick]} {wp_k:.0%} win prob."
    if choix == "JOUER":
        raison = f"{p_j:.0%} to convert · " + detail
    else:
        raison = detail
    return {"version": VERSION, "choix": choix,
            "wp": {o: round(v[0], 4) for o, v in opts.items()},
            "ep": {o: round(v[1], 3) for o, v in opts.items()},
            "p": {o: (None if v[2] is None else round(v[2], 3)) for o, v in opts.items()},
            "biais": round(biais - prudence, 2), "objectif": "win probability",
            "raison": raison}
