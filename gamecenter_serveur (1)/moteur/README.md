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
```

Le rapport charge le notebook sans Jupyter (cellules jusqu'à 12.2 nonies) et joue le test d'équilibre de 12.3
(1 008 matchs, mêmes graines). Bloc E : `--semaines N` joue d'abord N semaines d'essai (36 matchs chacune) en faisant
progresser les joueurs, puis mesure avec les rosters atteints (`--graine-trajectoire` : autre trajectoire). Tolérances : `TOLERANCES` dans `rapport_calibration.py`.

## Colab

Le notebook cherche `moteur/` dans `GC_MOTEUR_DIR`, le dossier courant, `./gamecenter_serveur (1)` et
`/content/gamecenter/gamecenter_serveur (1)`. Sur Colab, avant d'exécuter le notebook :

```python
!git clone https://<jeton GitHub>@github.com/guillaume-TMBRXX1/gamecenter.git /content/gamecenter
```

(dépôt privé : jeton « fine-grained » en lecture seule). Sans le dossier, le notebook tourne en V21 (interrupteur
forcé à coupé, message dans 12.2 quinquies) — sauf si `GC_MOTEUR_DIR` est donné ou `GC_DECISIONS=1` : il s'arrête alors.
`GC_DECISIONS=0` coupe l'interrupteur pour toute l'exécution.
