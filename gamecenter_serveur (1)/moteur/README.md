# moteur/ — ENGINE INTELLIGENCE

Modules de décision du moteur GridironSim (`programme/Feuille_de_route.md`, étape 5). Python pur (bibliothèque
standard seulement), indépendants du notebook : on échange des `dict` simples (`{"id", "name", "ratings"}`).
Le notebook `NFL_Sim_GameCenter.ipynb` les importe (cellule **12.2 quinquies**) et les appelle depuis
`simulate_drive_franchise` (12.2) derrière l'interrupteur `DECISIONS_ENABLED` (allumé depuis V22.1).

## Bloc A — état post-snap, progression du QB, cible réelle (notebook V22, allumé en V22.1)

```
appel du coordinateur (play + couverture)
   │ progressions.progression(concept, formation)        primaire · secondaire · tertiaire · checkdown (+ routes)
   ▼
DefensiveReactionEngine.react(...)  ->  PostSnapState   couverture réelle (homme / zone, Cover 0-4), rushers,
   │                                                     receveur LIBRE / SERRE / COUVERT / DOUBLE, temps avant pression
   ▼
QBDecisionEngine.decide(...)        ->  QBDecision      LANCER (cible réelle, n° de lecture) · THROWAWAY · SCRAMBLE · SACK
   ▼
resolution.probabilites_ajustees(...)                   probabilités du tirage historique ajustées selon la décision
```

| Fichier | Rôle |
|---|---|
| `progressions.py` | progression de lecture de chaque concept de passe (18 concepts + défaut), routes et instant où le QB peut lancer ; HEAVY : WR1 inéligible |
| `reaction_defensive.py` | séparation = écart de notes (route vs couverture, 20 points de note par « pas ») + avantage de la route contre la couverture + bruit ; double couverture (bracket) sur la meilleure menace ; chrono de poche selon le niveau de pression (03E) et les rushers |
| `decision_qb.py` | lecture dans l'ordre ; lancer selon le statut ; sous pression : meilleure lecture vue, sinon scramble (mobility) / throwaway (decision_making) / passe forcée / sack |
| `resolution.py` | multiplicateurs (libre, serré, couvert, double, pression) + `CALIBRATION` (facteurs qui ramènent les moyennes de la ligue sur V21) ; yards selon la profondeur de la cible réelle ; yards de scramble |
| `stats.py` | statistiques des décisions : par cible réelle, par statut, par couverture, taux de première lecture, pression, scramble, throwaway |
| `aleatoire.py` | flux aléatoire dédié : `random.Random("decision-passe|<graine du match>|<n° d'action>")` — le hasard du moteur n'est jamais consommé par une décision |

## Bloc B — intelligence du QB, poche et pression (notebook V23, allumé)

```
QB titulaire ── intelligence_qb.attributs_qb(qb, franchise)   8 attributs (dérivés des 4 notes + identité + écart du joueur)
   ▼
QBDecisionEngine.decide_b(...)        chrono de poche : reconnaissance (awareness) · pas de lecture (processing) ·
   │                                  lancer avant l'ouverture (anticipation) · temps gagné dans la poche (pocket awareness)
   │                                  statut PERÇU : erreurs de lecture (coverage reading, zone, pression × pressure response)
   │                                  style : aggressiveness (fenêtres serrées, passes forcées) tempéré par decision making
   ▼                                  fin de poche : scramble · throwaway · passe forcée · sack (ballon gardé trop longtemps)
resolution.probabilites_ajustees(...) statut RÉEL + mod_int / mod_inc (anticipation, pressure response, erreur de lecture)
                                      normalisés par CALIBRATION_B
```

| Fichier | Rôle |
|---|---|
| `intelligence_qb.py` | les 8 attributs (awareness, processing, coverage reading, decision making, pocket awareness, pressure response, anticipation, aggressiveness) ; une clé du même nom dans les notes du joueur est prise telle quelle ; ne s'ajoutent PAS aux notes (OVR, unités, cotes inchangés) |
| `decision_qb.py` | `decide_b` (QB avec `qb["iq"]`) ; sans attributs : bloc A à l'identique. Poids : `B`, autour d'un QB de référence `REF = 80` (niveau moyen des titulaires) ; seule une part `POIDS` de l'écart d'une qualité à 80 pèse (aggressiveness, un style, pèse en entier) : c'est le réglage qui garde l'équilibre des franchises (12.3) |
| `progressions.py` | `PROGRESSIONS_B` : le slot (WR3) lu aussi sur CURL, FOUR_VERTS, DAGGER (bloc B seulement) |
| `resolution.py` | `CALIBRATION_B` ; `mod_int` / `mod_inc` de la décision |
| `stats.py` | erreurs de lecture, QB pressé, temps de poche, part des INT sur décision fautive (forcée / mal lue), part des sacks « ballon gardé », stats par QB (`par_qb`) |

Un QB élite se trompe aussi (erreur de lecture jamais nulle). Interrupteur du notebook : `QB_IQ_ENABLED`
(`GC_BLOC_B=0` : décisions du bloc A, moteur V22.1 + safety).

## Bloc C — intelligence des joueurs : receveurs et défenseurs (notebook V24, allumé)

```
receveurs (WR, TE, RB) ── intelligence_joueurs.attributs_joueur(j, poste, franchise)   6 attributs
défenseurs (CB, S, LB) ──                                                              7 attributs
   ▼
DefensiveReactionEngine.react(..., bruit=BRUIT_C, echelle=ECHELLE_C)   état post-snap (bloc A)
   ▼
intelligence_joueurs.ajuster_post_snap(...)   flux à part « joueurs-passe » : défenseur RESPONSABLE de chaque receveur
   │                                          (homme : son vis-à-vis ; zone : un défenseur de la tranche attaquée)
   │                                          release / man IQ · separation / reaction · reconnaissance / zone-man IQ ·
   │                                          awareness (soupape, route « hot ») · play recognition (screen) ·
   │                                          écart de route (route IQ : moyenne et dispersion) · coverage bust
   │                                          (discipline, play recognition ; play action et double move)
   ▼
QBDecisionEngine.decide(...)                  le QB (blocs A-B) lit cet état
   ▼
_completer_bloc_c                             réception : open · traffic (catch in traffic / reaction) · contested
                                              (contested catch / man-zone IQ ; awareness -> interceptions) ;
                                              yards après la réception (separation / pursuit) ; normalisés par CALIBRATION_C
```

| Fichier | Rôle |
|---|---|
| `intelligence_joueurs.py` | les attributs (route IQ, release, separation, zone / man recognition, catch in traffic, contested catch ; play recognition, zone IQ, man IQ, awareness, reaction, discipline, pursuit), dérivés des notes du poste, de l'identité de la franchise (`PROFILS`) et d'un écart propre au joueur — hors OVR ; `ajuster_post_snap`, `modificateurs_reception`, `yards_apres_reception`. **Ce qui pèse, c'est le profil** : l'écart d'un attribut au `niveau()` du joueur (ses notes de route / de couverture, celles du duel du bloc A) ; le niveau est déjà dans le duel de notes (`POIDS_NIVEAU = 0`). Poids : `POIDS` (part de l'écart au niveau), `C` (effets en « pas » de séparation pour 10 points d'écart effectif) |
| `reaction_defensive.py` | `react(..., bruit, echelle)` : au bloc C, bruit générique plus petit (l'écart de route prend le reste ; `echelle` du duel de notes inchangée, 20) ; champs `couvreur_id`, `couvreur_nom`, `bust`, `ecart_route` de chaque receveur |
| `decision_qb.py` | `QBDecision.reception`, `couvreur_id`, `couvreur_nom`, `bust`, `yards_c` (remplis par `moteur.decider_passe`) |
| `resolution.py` | `CALIBRATION_C` ; `ajustement_yards` ajoute `yards_c` |
| `stats.py` | réceptions par type, coverage busts (sur la cible, au total), stats par défenseur responsable (`par_couvreur`) |

Interrupteur du notebook : `PLAYER_IQ_ENABLED` (cellule 12.2 septies ; `GC_BLOC_C=0` : moteur V23, blocs A + B). Sans
attributs sur les receveurs, `decider_passe` rend exactement la décision du bloc B (même bruit, aucun champ du bloc C).

## Bloc D — adaptation en match et plan de jeu (notebook V25, allumé)

```
avant le match ── plan_de_jeu.plan_de_jeu(attaque, défense)    scouting sans hasard : blitz adverse -> jeu rapide ·
   │                                                           homme / zone -> concepts · duels en homme -> CIBLE
   │                                                           FAVORITE · receveurs / safeties -> passes profondes ·
   │                                                           unités -> course / passe · menace adverse -> bracket
   ▼
chaque snap ── MemoireTendances.observer(action)               ce que chaque camp a vu de l'autre (cibles, blitz sur 3e
   │                                                           essai, pression, doubles, jeu rapide contre le blitz)
   ▼
AdaptiveGameplanEngine.attaque / .defense                      o_quick · o_protect · o_away  /  d_bracket · d_rotate ·
   │                                                           d_disguise (contre-ajustements) — chacun avec sa raison
   ▼
feuille d'appel (multiplicateur_concept) · appel défensif · plan_passe(...) -> moteur.decider_passe(..., plan=...)
                                                               progression ajustée (flux « plan-de-jeu ») · bracket
                                                               et protection dans l'état post-snap
```

| Fichier | Rôle |
|---|---|
| `plan_de_jeu.py` | `plan_de_jeu` (plan par adversaire, poids `PLAN`), `MemoireTendances`, `EtatAdaptation`, `AdaptiveGameplanEngine` (profils `PROFILS` : CTX vite, AEG lent et long, VEC ne protège pas, MNL têtu ; affichage limité : `MONTRER`), `multiplicateur_concept`, `plan_passe`, `appliquer_progression` (protection : RB retiré ; receveur doublé évité ; cible favorite lue en premier avec la probabilité `PLAN["favori"]`), `options_reaction` |
| `reaction_defensive.py` | `react(..., bracket, p_bracket, p_bracket_bonus, bonus_poche, bonus_rusher5)` : le double va sur le receveur choisi (même tirage consommé, jamais en Cover 0) ; protection : poche plus longue, 5e rusher ramassé en partie |
| `decision_qb.py` | `QBDecision.plan` : ce que le plan a changé (bracket, double réel, protection, receveur évité, cible favorite) |
| `__init__.py` | `decider_passe(..., plan=None)` : sans plan, bloc C à l'identique |

Interrupteur du notebook : `GAMEPLAN_ENABLED` (cellule 12.2 octies ; `GC_BLOC_D=0` : moteur V24). Le notebook construit
les observations depuis le play_log, appelle le moteur une fois par snap et par camp, et transmet les événements au
journal des ajustements de V21 (`play.adjust`, avec `reason`).

## Bloc E — progression des joueurs (notebook V26, allumé)

Décisions de Guillaume (05/10/2026) : une saison = une semaine, **une « année » = 4 semaines** ; les **vraies notes**
évoluent (notes d'unité, OVR et cotes suivent) ; **anti-inflation** = moyenne de chaque note par unité ramenée sur sa
valeur de départ + plafonds (potentiel, 99) + **écart d'équipe borné** ; tout est **figé pendant la semaine** (forme
comprise). Bornes d'équipe retenues après mesure : **force** (moyenne des 4 notes d'unité) à ± 0,2 point de sa base,
chaque **note d'unité** à ± 0,75 — le moteur est très sensible (≈ 15 points de % de victoires par point de force : à ± 3
par unité, la valeur proposée au départ, VEC montait à 72 % et MNL tombait à 24 % après 8 semaines).

```
semaine jouée ── stats des joueurs et des équipes, bilans
   ▼
developpement.semaine_suivante(etat, ...)     flux « progression|<semaine>|<id> » par joueur
   │  participation (temps de jeu) · performance (écarts-types dans son groupe de poste) + bilan de l'équipe
   │  forme      = 0,35 × forme d'avant + 1,6 × performance + bruit, bornée ± 3
   │  par note   croissance (âge, rythme de développement, temps de jeu) vers le plafond (base + potentiel)
   │             − régression (âge, catégorie : physique / technique / mental) + bruit
   │  expérience années jouées ; apprentissage -> bonus d'intelligence (relatif à la ligue)
   ▼
anti-inflation   (1) moyenne par (unité, note) ramenée sur la base — RB1 et RB2 à part · (2) plafonds · (3) équipe : force
   ▼             ± 0,2 par un DÉCALAGE commun des notes de l'équipe (ses joueurs gardent leurs écarts entre eux), puis
                 chaque unité ± 0,75 par λ ≤ 1 sur les écarts du côté concerné ; en alternance, λ commun en dernier recours
état de la semaine suivante (JSON : week.json -> players_next_week)
   ▼
notes effectives = arrondi(actuelle + forme), 40-99 -> rosters ; attributs des blocs B / C + bonus d'expérience
```

| Fichier | Rôle |
|---|---|
| `developpement.py` | `etat_initial` (âge, rythme, potentiel, expérience déterministes : hash de l'id ; actuelle = base, forme 0 -> moteur identique), `semaine_suivante`, `notes_effectives`, `ovr`, `appliquer_bonus_iq` (attributs mentaux des blocs B / C : lecture, anticipation, route IQ, reconnaissance, zone / man IQ, awareness, discipline), `marquer_semaine` (courbe par semaine), `resume_joueur` (GameFeed `roster[].progression`), `completer` (joueurs ajoutés / retirés du roster), `rapport_semaine`, `controler` |

Catégories : **physique** (speed, acceleration, mobility, throw_power, power, strength, leg_power, elusiveness) — pic
29 ans (RB : 27), puis − 0,9 point par an, + 0,7 par an de plus ; **technique** (précision, routes, réception, blocs,
pass rush, couverture, plaquage, run support) — pic 31 ans, − 0,5 / an + 0,35 ; **mental** (decision_making) — + 1 point
par année jouée (plafond base + potentiel + 3), pic 34 ans. Croissance : 4 points par an à 21 ans, 2,4 à 25, 0,4 à 29
(× rythme : slow 0,6 · normal 1 · fast 1,4 · star 1,8 ; × 0,5 à 1 selon le temps de jeu), freinée près du plafond.

Interrupteur du notebook : `PROGRESSION_ENABLED` (cellule 12.2 nonies ; `GC_BLOC_E=0` : rosters de base chaque
semaine, moteur V25). Au départ (aucune semaine jouée), les notes sont celles du roster : le moteur joue comme V25.

**Retraites et recrues** (étape 6, décision de Guillaume du 06/10/2026 : « retraite + recrue générée ») — dans
`semaine_suivante(..., recrues=(prénoms, noms))`, après le vieillissement et avant l'anti-inflation :
`doit_partir` — âge de la retraite du poste (`AGE_RETRAITE` : QB 38, K / P 40, les autres 35) ou, dès 32 ans, OVR
tombé de 10 points sous sa base ; `recrue` — un joueur de 21,5-23,5 ans prend **la même place** (même id : la place au
roster, pas la personne ; nom tiré des listes de 12.1, unique dans l'équipe), garde la **base du poste** (référence de
l'anti-inflation et du garde-fou d'équipe : le niveau voulu de la franchise) et part **en dessous** (physique − 2 à 5,
technique − 4 à 8, mental − 6 à 10) avec un grand potentiel (9-13) et un rythme plus souvent rapide ; la croissance des
jeunes (≈ 1 point par semaine à 22 ans) le ramène vers la base en quelques semaines, le garde-fou d'équipe tient la
force pendant ce temps. Flux « recrue|<semaine>|<id> » (déterministe). Rapport : `progression.retirements` (week.json) ;
fiche : `roster[].progression.rookie = {week, replaces}` ; les recrues ne comptent pas dans les hausses / baisses de
la semaine. Sans `recrues` : bloc E à l'identique. Notebook : `RETRAITES_ENABLED` (`GC_RETRAITES`, allumé avec la
ligue de 8 ; la ligue de départ `GC_FRANCHISES=4` reste V28 à l'identique). Tests : `tests/test_retraites.py`.

## Extension du playbook V0.1 (notebook 12.2 decies, allumée)

Source : `programme/GRIDIRON_SIM_PLAYBOOK_EXPANSION_DATABASE_V0.1.md`. `playbook_expansion.py` est le **catalogue** de
ce que la base apporte et que le moteur n'avait pas ; **rien de ce qui existait n'est recréé** : chaque nom de la base
déjà porté par le moteur (même sous un autre nom : SMASH = CHAMP, MILLS = DEEP_POST, GUN_SPLIT = PONY, COVER_1 = MAN…)
est dans `ALIAS`, ce qui manque de définition est dans `RESERVE` (SALEM, SPILL_PROTECTION, personnel 10 avec les
rosters actuels, équipes spéciales).

```
appel du coordinateur (V20 + parts des nouveaux concepts dans leur ancre)        play · intention course / passe
   ▼
appel défensif (inchangé : MAN / ZONE / COVER_x / BLITZ / BOX_STACK)
   ▼  crochet du snap (12.2 decies), chaque système dans son flux « xp-… »
choisir_paquet · choisir_front · choisir_rush · tirer_mouvement      la défense : coquille réelle, présentation, front
choisir_motion · choisir_shift · enchainement                        l'attaque : information avant le snap, suite
lecture_rpo                                                          RPO : donner (course) ou lancer (passe décidée)
   ▼
passe  -> moteur.decider_passe(..., appel=appel_passe(...))          coquille / rushers / présentation (déguisement),
                                                                     receveur laissé par un blitzeur, protection
                                                                     (rôles retirés, chip), motion, enchaînement
course -> lecture_option (porteur) · effet_course (yards)            front, motion, shift, mouvement (moyenne nulle)
```

| Élément | Contenu |
|---|---|
| Formations (22) | gun tight, y-off, wing, stack, quads, trips open / tight, flex ; singleback bunch, wing, tight, deuce, wing pair, nasty ; pistol strong, wing, full house ; I-form slot, wing ; strong I, weak I ; wildcat — chacune avec son `personnel` (10 / 11 / 12 / 21 / 22), ses modificateurs (`mods`) et son alignement (site) ; `SHIFT_DEPUIS` (structure de départ d'un shift) |
| Compatibilité | `compatibilite(personnel, roster)` -> PRIMARY / SUPPORTED / UNNATURAL / INVALID (avec la raison structurelle) : un filtre, pas une fréquence |
| Concepts | 23 de course (dont 6 options et 6 RPO) et 18 de passe ; `ancre`, `porteur` (OffensivePlayType), `modif` (yards), `classe`, `plan` (familles du bloc D) ; `PROGRESSIONS` et `DESSIN_PASSE` ; 9 routes (`ROUTES`) |
| Plays (144) | `PLAYS` : nouveaux concepts dans les formations compatibles, et concepts existants dans les nouvelles formations |
| Identités | `PARTS` (part du budget restant de l'ancre, ≤ 0,6 par ancre), `FORMATIONS_STYLE`, `EXCLUS_CONCEPTS` / `EXCLUS_FORMATIONS` (MNL : courses toujours à ses RB ; VEC : pas d'option ni de wildcat) |
| Feuille d'appel | `SITUATIONS` (short, long, red_zone, goal_line, backed_up, first_down) ; `RELATIONS` / `enchainement` (préparation -> suite : appel un peu plus probable ; si la défense l'a vue deux fois, petite réponse défensive) |
| Motions, protections | `MOTIONS` (jet, orbit, across, return, trade : déguisement retiré, séparation contre l'homme, yards de course) ; `PROTECTIONS` (5 / 6 / 7, slides, man, chip, scat) et `PROTECTION_VS` |
| Défense | `PAQUETS` (33 : couvertures, pression présentée sans être jouée, vraie pression, variantes contre la course) et `PAQUETS_STYLE` ; `COQUILLES` (16 nouvelles coquilles : avantage des routes, double) ; `RUSH` ; `FRONTS` (11) et `MOUVEMENTS` |
| Lectures | `lecture_rpo` (la boîte : chargée -> lancer), `lecture_option` (le bord qui ferme -> le QB garde) ; le QB se trompe parfois (`p_erreur_lecture`, decision_making) |
| `brancher()` | inscrit routes, progressions, coquilles et familles du bloc D dans les autres modules (idempotent ; sans lui, les modules sont ceux du bloc E) |

Autres modules : `reaction_defensive.react(..., appel=None)` (coquille / rushers du paquet, `_effet_appel`, poche ;
`PostSnapState.paquet / presente / deguisement / scramble`), `decision_qb` (erreurs de lecture × (1 + déguisement),
sorties de poche × `scramble`), `decider_passe(..., appel=None)` (`ajuster_lectures` : protection). Sans appel : bloc E
à l'identique (mêmes tirages, mêmes valeurs — test). Interrupteur du notebook : `EXPANSION_ENABLED` (cellule 12.2 decies ;
`GC_EXPANSION=0` : moteur V26).

## Fin de période : field goal ou continuer (notebook 12.2 undecies, allumée)

Constat (V27, 240 matchs) : la dernière action d'un Q2 ou d'un Q4 à portée de field goal était presque toujours une
course ou une passe (4 field goals sur 166) — le moteur ne regardait le field goal qu'au 4e essai, jamais l'horloge.
`fin_de_periode.decider(quart, secondes, essai, a_gagner, en_but, ecart, special_teams_rating, ecart_unites, temps_morts)`
compare, dans les `FENETRE` (45) dernières secondes du Q2 et du Q4, « field goal maintenant » et « continuer » :

```
FG      p(distance, équipes spéciales) × 3 points          (même barème que calculate_field_goal_probability)
JOUER   touchdown · perte de balle · arrêt · gain (par zone de 5 yards, course / passe, × écart des unités)
        × durée de l'action (distribution mesurée) -> même décision au snap suivant, ou fin de la période,
        ou ballon rendu (4e essai manqué)
valeur  Q2 : points attendus · Q4 : probabilité de victoire (écart final : 1 / 0,5 / 0)
```

Pas de règle « s'il reste X secondes » : à 40 s de la fin à la ligne des 30, on joue ; à 3 s on tire ; mené de 4 et
plus, 3 points ne servent à rien ; près de la ligne de but, le touchdown peut valoir plus que 3 points (le moteur marque
55-63 % des actions à moins de 5 yards). Paramètres mesurés sur 160 matchs (`TEMPS`, `ZONES`, `ARRET`) ; modèle validé
contre le moteur (points réellement marqués depuis les mêmes situations). Temps morts : sans effet tant que le moteur
n'écoule pas l'horloge entre deux actions (`TEMPS_ENTRE_ACTIONS = 0`). Déterministe. Interrupteur du notebook :
`FIN_PERIODE_ENABLED` (`GC_FIN_PERIODE=0` : moteur V27). Tests : `test_fin_de_periode.py`.

## Horloge réelle et valeur des décisions (notebook 12.2 quaterdecies, 14/10/2026 — allumées)

Constat (semaine du 12/10, 279 matchs) : 0 s entre deux actions (tuer l'horloge ne tuait presque rien : 53 % de passes
pour l'équipe qui mène dans la dernière minute ; ni genou, ni spike, ni temps mort utile) et un 4e essai à deux seuils
fixes (4e et 1 entre ses 30 et le milieu de terrain joué 20 % du temps).

```
snap ── fin_de_periode (12.2 undecies, en secondes ÉQUIVALENTES)      field goal / jouer dans les dernières secondes
   │    horloge.avant_snap(...)                                       genou (victory formation) · spike
   │    valeur.quatrieme_essai(...)                                   4e essai : jouer / field goal / punt (WP + identité)
   ▼
action (moteur, inchangé)
   ▼
horloge.apres_action(...)  ->  temps jusqu'au snap suivant           arrêt (incomplète, possession, sortie en fin de
                                (ajouté à la durée de l'action)      mi-temps, 2 minutes, temps mort, spike, fire drill)
                                                                     ou huddle selon le tempo (normal / hurry / clock)
```

| Fichier | Rôle |
|---|---|
| `horloge.py` | `EtatHorloge` (temps morts par mi-temps, horloge arrêtée), `apres_action` (temps entre les actions ; sortie du terrain dans le flux « horloge »), `avant_snap` / `genou` / `spike`, `veut_arreter` (qui pose un temps mort), `veut_les_points` (fire drill), `secondes_equivalentes` (réglages en secondes de V21 et de la fin de période, mesurés sans temps entre les actions). Durées à l'échelle NFL (quart de 900 s), × `echelle(quart_secondes)` |
| `valeur.py` | `points_attendus` (1er essai, mesuré sur 597 matchs du moteur), `probabilite_victoire` (marge finale ~ normale, écart-type 13,2 × part restante^0,38, mesuré), `conversion`, `depart_apres_punt`, `options_4e`, `quatrieme_essai` (meilleure WP, convertie en points pour le biais d'identité : `BIAIS` selon l'agressivité du coordinateur, `PRUDENCE_CAMP` dans son camp ; match plié : None) |

Interrupteurs du notebook : `HORLOGE_ENABLED` (quart-temps `GC_QUART`, 900) et `VALEUR_ENABLED`, **allumés** (décision
de Guillaume du 14/10 : quarts de 15 min, retransmission ≈ 18 min) ; `GC_HORLOGE=0` / `GC_VALEUR=0` : moteur d'avant à
l'identique (contrôlé). Situation du match (menée : la prudence s'efface au fil du dernier quart-temps ; gagné : règle
d'avant ; dernières secondes, menée : fin de période). Mesures : README du serveur, section 53. Tests :
`test_horloge.py`, `test_valeur.py`.

## Bloc F — intelligence du jeu de course (notebook 12.2 quindecies, 14/10/2026, allumé)

Constat (552 matchs, 28 711 courses, horloge réelle) : la course était résolue au niveau de l'équipe, le porteur désigné
après coup ; effet « boîte » en tout ou rien (contre BOX_STACK 2,5 yards et 33 % de courses bloquées, contre le reste
≈ 6,7 yards) ; le concept ne rencontrait pas la défense ; ni les lignes au point d'attaque ni le profil du porteur ne
pesaient (régression : effets nuls ou de mauvais signe).

```
snap (12.2 decies) ── formation défensive, appel, paquet, front retenus
   ▼
tirage du moteur (simulate_run, unités) · concept · front / motion (extension) · intention défensive NEUTRE (même tirage)
   ▼
porteur désigné ── course.boite(...)            défenseurs dans la boîte (5-9) : formation, appel, paquet, front
   │               course.courir(...)           côté choisi (meilleurs duels, 65 %) · duels au point d'attaque (par
   │                                            rapport à la moyenne de chaque ligne) · chapeaux non bloqués · front
   │                                            contre la classe · trou ouvert / étroit / fermé · lecture (cutback,
   │                                            rebond, bloqué) · contact (plaqueur, yards après contact) · RB2 contre RB1
   ▼
yards + ajustement (flux « course », arrondi sans biais) · plaqueur crédité = défenseur au contact
```

| Fichier | Rôle |
|---|---|
| `course.py` | `boite`, `choisir_cote`, `courir` (état de la course et ajustement), `entier` ; tables `BOITE`, `POINT`, `FRONT_CLASSE` ; poids `K_TROU`, `K_PORTEUR`, `K_CONTACT`, `K_VITESSE`, `LECTURE` ; `CALIBRATION` (moyenne de la ligue gardée). **Tout est un profil, jamais un niveau** : le niveau des joueurs est déjà dans les notes d'unité du tirage du moteur (duels par rapport à la moyenne de chaque ligne ; vision, puissance, vitesse du porteur par rapport à sa note globale ; plaqueur et safety par rapport à la moyenne de leur défense) |

Interrupteur du notebook : `RUN_IQ_ENABLED` (`GC_BLOC_F=0` : moteur d'avant à l'identique, contrôlé). GameFeed :
`play.run` (box, side, hole, read, contact, tackler, front, key_block). Mesures : README du serveur, section 54. Tests :
`test_course.py`.

## Checks avant le snap (étape 4 « moteur plus intelligent », notebook 12.2 novodecies, 16/10/2026)

```
appel du huddle + défense (12.2 decies : paquet, front, motion)
   │  réponse à la motion (profil de la défense) : roll (+1 dans la boîte, la coquille se dévoile) · lock (homme : le
   │                                               défenseur suit) · bump (zone : rien ne se dévoile)
   │  ce que la défense MONTRE : « 2-high rotating » → un défenseur de moins dans la boîte · « mug » → un ou deux de plus
   │  lecture du QB : voit au travers (awareness, coverage reading − déguisement ; roll / lock : tout se voit)
   │  audible : boîte lue ≥ 8 contre une course → passe rapide ; ≤ 6 contre une passe (≤ 6 yards) → course intérieure ;
   │           fréquence = identité de la franchise (liberté, penchant) × awareness ; même formation si possible
   │  trompé : mauvais audible / audible manqué (le même tirage avec la vraie boîte)
   ▼
bloc F (boîte réelle) ou passe décidée (vu au travers : moitié moins d'erreurs dues au déguisement) ;
chrono d'avant-snap : 2 s par audible (+1 après une réponse à une motion), 1 s au moins au snap
```

| Fichier | Rôle |
|---|---|
| `presnap.py` | `check` (réponse à la motion, lecture, audible, trompé), `boite_montree`, `coquilles`, `regard`, `p_voir`, `p_audible`, `vers_quoi` (situations : tuer l'horloge, goal line, hurry-up, 15 dernières secondes), `cout` ; tables `LIBERTE` (identité offensive), `REPONSE` (identité défensive), `PRESENTATION`. Flux `presnap`, `presnap-def`, `presnap-jeu`. **Un profil, pas un niveau** : aucun yard ajouté — le gain d'un bon audible et le coût d'un mauvais viennent du moteur (bloc F, déguisement de la lecture) |

Interrupteur du notebook : `PRESNAP_ENABLED` (`GC_PRESNAP=0` : moteur d'avant à l'identique, contrôlé). GameFeed :
`play.presnap` (look, box_shown, box_real, box_read, shell_shown, shell_real, read, audible, from, to, fooled, motion,
motion_response, sec, clock, qb). Mesures : README du serveur, section 58. Tests : `test_presnap.py`.

## Appel de jeu qui apprend, et sa mémoire d'une semaine à l'autre (étapes 5 et 6 « moteur plus intelligent », notebook 12.2 vicies semel et bis, 19-21/10/2026)

```
fin de semaine (14.1) : film = film × 0,5 + appels joués de la semaine (situations vues avant le snap -> course / passe,
                        famille) ; scouting_next_week.json (à part, compact) ; amorce depuis les GameFeeds sinon (15.1)
début de match : carnet de la défense = film de l'attaque adverse, formation par formation (down & distance ×
                 formation, formation ; ses propres matchs × 1,5), plafonné (FILM_MAX × poids du coordinateur)
                 self-scout de l'attaque : match OU film (FILM_MAX_SOI : down & distance et zone compris)
à chaque snap : a priori de la ligue < film (s'efface : demi-vie de 24 snaps) < match -> tendance nette ?
                défense : KEY (confiance plafonnée à 0,80 si la preuve vient surtout du film) ; attaque : BREAK si elle
                se sait lue (lecture juste, réponse de 12.2 quater, courses stoppées, réputation de lectrice)
```

| Fichier | Rôle |
|---|---|
| `scouting.py` | Carnet (oubli, couche film : `amorcer`, mode « match OU film »), `tendance`, `engagement` (flux `scouting-def`), `cassure` (flux `scouting-att`), `anticipation`, profils `SCOUT` ; idée 6 : `film_match`, `film_suivant` (oubli hebdomadaire, comptes < FILM_MIN oubliés), `film_pour` (mise à l'échelle), `reputation`, `observations_feed` / `lectures_feed` (amorce), `film_tendances` (rapport d'avant-match), `controler_film` (audit), `film_cle` (cache des cotes). Aucun hasard dans le film |

Interrupteurs du notebook : `SCOUTING_ENABLED` (`GC_SCOUTING=0` : moteur d'avant), `MEMOIRE_ENABLED` (`GC_MEMOIRE=0` ou
film vide : idée 5 à l'identique, contrôlé). GameFeed : `play.scout` (`def.film = {games, own, part}`, `off.on_tape`),
`game.scout_film`, `game.scout_memory`. Mesures : README du serveur, sections 63 et 65. Tests : `test_scouting.py`.

## Étape 6 — plus de franchises (palier 1 : 8 équipes, palier 2 : 12, palier 3 : 16, palier 4 : 20, puis 24)

Les franchises 05-08 de la bible des identités (AXM Axiom Falcons, GLT Glitch Hornets, CPH Cipher Lynx, NVA Nova
Raptors ; noms proposés, à valider) sont décrites dans les tables EXISTANTES de chaque module — aucune logique propre à
une équipe : `intelligence_qb.PROFILS`, `intelligence_joueurs.PROFILS`, `plan_de_jeu.PROFILS`,
`playbook_expansion` (`FRANCHISES`, `PARTS`, `FORMATIONS_STYLE`, `EXCLUS_*`, `PAQUETS_STYLE`, `RUSH_STYLE`,
`FRONTS_STYLE`, `MOUVEMENTS_STYLE`). Le reste (rosters, coordinateurs, playbooks, adaptation V21) est dans le
notebook (12.1 à 12.2 quater). Détail et mesures : README du serveur, section 23.

**Palier 2 (12 équipes, 07/10/2026)** : franchises 09-12 (PLS Pulse Jackals, ONX Onyx Hawks, FRG Forge Bison, MRD
Meridian Owls ; à valider) ajoutées aux mêmes tables. Détail : README du serveur, section 25.

**Palier 3 (16 équipes, 07/10/2026)** : franchises 13-16 (APX Apex Vipers, LTC Lattice Wolves, ZPH Zephyr Condors,
BST Bastion Panthers ; à valider). Détail : README du serveur, section 26.

**Palier 4 (20 équipes, 07/10/2026)** : franchises 17-20 (GRZ Granite Grizzlies, MRG Mirage Cobras, GMB Gambit
Stallions, PRM Prism Chameleons ; à valider). Détail : README du serveur, section 27.

**Franchises 21-24 (24 équipes, 07/10/2026)** : SPK Spark Kestrels, CTD Citadel Rams, TDL Tidal Herons, CMT Comet
Stingrays (hors bible, à valider). Nouveau : `developpement.AGE_EQUIPE` (âge d'une franchise : SPK jeune, CTD
vétérane ; 0 ailleurs, tirages inchangés). Détail : README du serveur, section 28.

**Divisions, calibrage, contrôles (08/10/2026)** : forces recalibrées dans `FRANCHISE_SPECS` (12.1, notebook) — les
modules du moteur ne changent pas. Détail : README du serveur, section 29.

## Tests (quelques secondes)

```bash
cd "gamecenter_serveur (1)"
python3 -m unittest discover -s moteur/tests -t .
```

Primaire libre · primaire couvert / secondaire libre · tout couvert (checkdown, throwaway, sack) · double
couverture · blitz (moins de temps, plus de rushers, route « hot ») · Cover 4 (fond fermé, court ouvert) ·
QB mobile (plus de scrambles) · pression précoce · déterminisme (même graine = même décision, flux indépendant
du hasard global) · probabilités valides · agrégation des stats.

Bloc B (`test_bloc_b.py`, toujours en distribution) : processing 90 contre 65 sur la même situation · pression précoce
(pocket awareness) · poche qui se referme (lectures, QB pressé, fins d'action) · pressure response · coverage reading
(zone plus difficile) · erreur de lecture -> plus d'interceptions · aggressiveness · decision making · anticipation ·
un QB élite se trompe aussi · attributs dérivés (bornes, identité, déterminisme) · slot lu au bloc B seulement ·
sans attributs = bloc A · déterminisme · probabilités valides · stats par QB.

Bloc C (`test_bloc_c.py`, en distribution) : le niveau n'est pas compté deux fois (attributs au niveau des notes =
effet nul) · profil au-delà du niveau (même notes, CB « homme » contre CB « zone ») · **deux défenseurs de notes différentes face à la même situation** (man IQ
et reaction en homme, zone IQ en zone, discipline et play recognition -> coverage busts, play action, screen,
awareness sur la soupape) · route IQ (écart de route plus petit et moins dispersé) · release (surtout en homme) ·
reconnaissance de la zone · réception (open / traffic / contested, contested catch d'une star contre un receveur
faible, défenseur attentif -> interceptions) · yards après la réception · chaîne complète déterministe · sans attributs
= bloc B à l'identique · flux du bloc C séparé · stats.

Bloc D (`test_bloc_d.py`) : **détection de tendance** (cibles sur la fenêtre, blitz sur 3e essai, doubles, courses
ignorées) · **ajustement offensif** (blitz répétés -> quick game / screen / draw, surtout sur 3e essai ; protection après
la pression sur blitz, VEC ne protège pas ; bascule hors du double ; identité CTX plus rapide qu'AEG ; expiration) ·
**ajustement défensif** (receveur trop ciblé et productif -> bracket ; ciblé mais inefficace : rien ; le RB n'est pas
brackété ; bracket -> plus de doubles sur ce receveur, en distribution ; jamais en Cover 0 ; pression déguisée) ·
**contre-ajustement** (bracket -> l'attaque lit ailleurs -> le bracket tourne vers le TE -> l'évitement expire) · plan
de jeu (blitz, homme / zone, cible favorite = meilleur mismatch, course / passe, fond du terrain, déterministe) ·
progression (protection, screen, cible favorite une fois sur trois) · chaîne : sans plan = bloc C à l'identique,
déterministe, le bracket détourne les lancers, flux du plan séparé.

Bloc E (`test_bloc_e.py`) : **progression** (jeune avec du potentiel, rythme de développement, jouer fait progresser) ·
**régression** (vétéran : physique plus que technique, RB plus tôt, le mental progresse encore) · **potentiel**
(plafond jamais dépassé, sans potentiel pas de croissance) · âge (+1 toutes les 4 semaines) · **forme** (bonne semaine
-> bonne forme, en distribution ; bornée, centrée par unité ; sur toutes les notes ; bilan de l'équipe ; temps de jeu)
· **anti-inflation** (moyenne de la ligue stable sur 30 semaines ; garde-fou d'équipe ≤ 3 dans un cas extrême, sans
effacer la meilleure équipe ; bornes 40-99) · expérience (bonus d'intelligence relatif, somme nulle, seulement sur les
attributs mentaux) · **déterminisme** (même entrée -> même état, flux propre, entrée non modifiée, aller-retour JSON,
roster complété) · courbe (idempotente, bornée) · résumé de la fiche joueur.

Extension du playbook (`test_expansion.py`) : pas de doublon avec l'existant (formations, concepts, paquets, fronts,
routes, plays) · catalogue cohérent (plays, progressions, dessins, porteurs, parts ≤ 0,6 par ancre, identités) ·
chaque route dessinée existe sur le site · compatibilité de personnel (INVALID avec raison) · `brancher()` idempotent
et réversible · sans appel = bloc E · déterminisme · pression réelle contre présentée · présentation qui trompe le QB ·
motion qui révèle l'homme · protection max · blitz qui laisse un receveur · nouvelles coquilles · lectures RPO / option
(en distribution, le QB se trompe) · paquets (parts), banjo contre les groupes, fronts de situation, rush jamais sur
un blitz, mouvement de moyenne nulle · effets de course, motion, shift, enchaînement.

Scouting (`test_scouting.py`) : situations, carnet et oubli, tendance nette, engagement, cassure, anticipation, profils ;
idée 6 : **film vide = idée 5** · tendance dès le premier snap · plafonds (proportions, pas masse) · ses propres matchs
pèsent plus · **a priori < film < match** (le film s'efface) · confiance du film plafonnée · doute · self-scout match OU
film · **oubli hebdomadaire et stabilité sur 20 semaines** · vieux film oublié · arrondis · déterminisme et clé ·
réputation · rapport d'avant-match · GameFeed -> film (amorce).

## Calibration (garde-fou 3)

```bash
python3 outils/moteur/rapport_calibration.py --decisions off --sortie /tmp/v21.json          # référence V21
python3 outils/moteur/rapport_calibration.py --decisions on --reference /tmp/v21.json         # verdict (code 1 si hors tolérance)
python3 outils/moteur/calibrer_bloc_a.py --reference /tmp/v21.json                            # recalcule CALIBRATION
python3 outils/moteur/calibrer_bloc_a.py --reference /tmp/v21.json --bloc B                    # recalcule CALIBRATION_B
python3 outils/moteur/calibrer_bloc_a.py --reference /tmp/v21.json --bloc C                    # recalcule CALIBRATION_C
python3 outils/moteur/rapport_calibration.py --decisions on --bloc-c off                       # V23 (blocs A + B)
python3 outils/moteur/rapport_calibration.py --decisions on --bloc-d off                       # V24 (blocs A + B + C)
python3 outils/moteur/rapport_calibration.py --decisions on --bloc-e off                       # V25 (blocs A-D)
python3 outils/moteur/rapport_calibration.py --decisions on --semaines 16                      # bloc E : après 16 semaines
python3 outils/moteur/rapport_calibration.py --decisions on --expansion off                    # V26 (sans l'extension)
python3 outils/moteur/rapport_calibration.py --decisions on --fin-periode off                  # V27 (sans la fin de période)
```

Le rapport charge le notebook sans Jupyter (cellules jusqu'à 12.2 undecies) et joue le test d'équilibre de 12.3
(1 008 matchs, mêmes graines). Bloc E : `--semaines N` joue d'abord N semaines d'essai (36 matchs chacune) en faisant
progresser les joueurs, puis mesure avec les rosters atteints (`--graine-trajectoire` : autre trajectoire). Tolérances : `TOLERANCES` dans `rapport_calibration.py`.

## Validation complète (fin de programme, phases 13 et 14)

```bash
python3 outils/moteur/validation_complete.py --sortie outils/moteur/rapport_validation_complete.json   # ≈ 30 min, 3 cœurs
python3 outils/moteur/validation_complete.py --rapide                                                   # ≈ 6 min : vérifie l'outil
```

Un seul outil (workflow manuel « Validation complète » sur GitHub) : tests unitaires ; pour chaque étage du moteur
(V21, A, A-B, A-C, A-D, A-E) et après 8, 16, 32 et 52 semaines de progression, les 1 008 matchs du test d'équilibre
exportés en GameFeed, validés (`validate_gamefeed`) et audités action par action (`audit_moteur.check_game`),
identités stats joueurs = stats d'équipe (`season_stats` de 14.1), champs de chaque bloc ; déterminisme (rejeu dans
l'ordre et à l'envers, autre processus avec un autre `PYTHONHASHSEED`, trajectoire de progression rejouée) ;
non-régression (chaque étage redonne à l'identique son rapport publié, y compris les 4 trajectoires du rapport V26 ;
bloc E au départ = V25 match par match) ; calibration contre V21 ; repères stats joueurs / équipes et Next Gen Stats.
Code de sortie 1 si un contrôle bloquant échoue. La semaine réelle (cotes comprises) reste `generer_semaine.py` +
`audit_moteur.py`.

## Colab

Le notebook cherche `moteur/` dans `GC_MOTEUR_DIR`, le dossier courant, `./gamecenter_serveur (1)` et
`/content/gamecenter/gamecenter_serveur (1)`. Sur Colab, avant d'exécuter le notebook :

```python
!git clone https://<jeton GitHub>@github.com/guillaume-TMBRXX1/gamecenter.git /content/gamecenter
```

(dépôt privé : jeton « fine-grained » en lecture seule). Sans le dossier, le notebook tourne en V21 (interrupteur
forcé à coupé, message dans 12.2 quinquies) — sauf si `GC_MOTEUR_DIR` est donné ou `GC_DECISIONS=1` : il s'arrête alors.
`GC_DECISIONS=0` coupe l'interrupteur pour toute l'exécution.
