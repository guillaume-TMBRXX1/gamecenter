# Feuille de route — GridironSim (mise à jour le 06/10/2026, validation complète de l'étape 5, extension du playbook branchée)

Ordre choisi par Guillaume. **Une conversation par étape (ou par bloc)** : en début de conversation, lire ce fichier,
puis `programme/Mise_en_ligne.md`, `programme/Bilan_prototype.md` et `notebook/NFL_Sim_fiche_technique.md`
(fichiers du projet Claude, hors dépôt) et le `README.md` du serveur (`gamecenter_serveur (1)/README.md`).
**Cette version, dans le dépôt, remplace celle du 03/10** (l'étape 5 « plus de franchises » est remplacée par le
programme ENGINE INTELLIGENCE ; l'extension des franchises vient après, en étape 6).

Le site se met à jour par le dépôt GitHub privé `guillaume-TMBRXX1/gamecenter` (sous-dossier `gamecenter_serveur (1)/`) :
tout changement fusionné dans `main` est redéployé par Railway. Toujours tester en local avant de pousser
(`audit_moteur.py`, tests du notebook, tests `outils/audio/*`, `tserver.py`, `tavance.py`, `taccounts.py`, `tparis2.py`,
`tsearch.py`, `tadjust.py`). Ne jamais relancer `--premiere` (la semaine 1 existe).

## Tableau

| # | Étape | État | Touche |
|---|---|---|---|
| 0 | Valider la règle de départage | ✅ validée le 03/10/2026 | — |
| 1 | Comptes joueurs + classement multi-semaines | ✅ en ligne le 03/10 (`5366e55`) | serveur + site |
| 2 | Paris plus riches (combinés, cash-out, historique) | ✅ en ligne le 03/10 (`baab4d3`) | serveur + site |
| 3 | Playbooks plus variés (V19) · 3 bis recherche · 3 ter « Roman 2014 » (V20) | ✅ en ligne le 03/10 | notebook + site |
| 4 | IA adaptatives en direct (notebook V21) | ✅ poussé le 03/10 (`9c610ab`), semaines à partir du 12/10 | notebook + site |
| — | Hors feuille de route, 03-04/10 : fluidité mobile / iPad, Audio System V0.1 → V0.4 (commentaire, foule, effets ElevenLabs hors ligne ; musique originale CC0), accueil économe et sans spoiler (aperçus, teasers), Exhibition (match V21 hors calendrier) | ✅ en ligne (PR #1 → #10) | site + serveur |
| **5** | **ENGINE INTELLIGENCE** — un vrai système décisionnel (programme ci-dessous, blocs A → E) | **en cours** — ✅ bloc A allumé (notebook V22.1, PR #12 + #13) ; ✅ safety + bloc B allumés (notebook V23) ; ✅ bloc C allumé (notebook V24) ; ✅ bloc D allumé (notebook V25) ; ✅ bloc E allumé (notebook V26) ; ✅ **validation complète** (06/10, un point à décider : yards / course après plusieurs semaines) ; **prochain : étape 6** | notebook (+ modules Python) + site + serveur |
| 5 bis | Extension du playbook V0.1 (base de connaissances football) branchée au moteur (notebook V27) | ✅ 06/10, notebook V27 | notebook (+ module) + site |
| 5 ter | Décisions de fin de Q2 / Q4 : field goal ou continuer (notebook V28) | ✅ 06/10 | notebook (+ module) + site |
| 6 | Plus de franchises / divisions | après l'étape 5 | notebook + site + serveur |
| 7 | Publicités | reportées à la fin | site + serveur — voir `Publicites_plan.md` |

---

## 5 — ENGINE INTELLIGENCE

### Objectif
Passer de `GAME STATE → PLAY CALL → PLAY EXECUTION → RESULT` à :

`GAME STATE → PLAY CALL → PRE-SNAP READ → SNAP → POST-SNAP STATE → PLAYER DECISIONS → PLAY OUTCOME → LEARNING / TENDENCIES → NEXT PLAY`

**Règle d'or** : chercher « une décision logique compte tenu de la situation, des capacités du joueur et de ce qui
s'est passé avant », pas seulement « un résultat réaliste ».

### Constat de départ (vérifié dans le notebook le 04/10)
Le résultat d'une passe (complète / incomplète / sack / interception, yards) est tiré à partir des **notes d'unité de
l'équipe** (`_fr_unit(…, "pass_off")` contre `"pass_def"` → `simulate_pass`) ; receveur et défenseur sont désignés
**après coup**, pour les stats et l'animation (cellule 431 : « les ratings individuels ne servent qu'à l'attribution
des stats et à l'animation, pas encore au résultat du jeu »). Le programme inverse cette causalité : **la décision
produit le résultat**. C'est le cœur du travail.

### Décisions prises (04/10/2026)
1. **Ce programme remplace l'ancienne étape 5** ; l'extension des franchises passe en étape 6, avec exactement les mêmes
   systèmes (aucune logique codée pour les 4 équipes de test).
2. **Résolution « ajustée » d'abord** : le moteur de décision construit l'état post-snap, choisit la cible et **ajuste
   les probabilités** transmises à la résolution existante ; horloge, downs, score, pertes de balle, stats, yards après
   réception et prolongation restent ceux d'aujourd'hui. Interrupteur `DECISIONS_ENABLED` : l'ancien chemin reste
   intact (tests, comparaison). Une résolution entièrement causale pourra venir plus tard, si les mesures le justifient.
3. **Nouveaux moteurs en modules Python du dépôt**, importés par le notebook, avec des tests unitaires qui tournent en
   quelques secondes (le calcul du samedi, qui exécute le notebook dans le dépôt, n'est pas gêné). Le notebook reste
   l'orchestrateur et garde ses cellules de contrôle. *Colab : cloner le dépôt avant d'exécuter (à documenter dans le bloc A).*
4. **Calibration actuelle conservée comme cible** : % de complétion, taux de sack, interceptions, yards par tentative,
   ≈ 3,5 pertes de balle par match (décision du 03/10), points par match, équilibre 40-60 % (tolérance à fixer au bloc A
   à partir des mesures de V21).

### Architecture
Modules indépendants, appelés par les fonctions historiques sans les remplacer :
`PostSnapState` / `DefensiveReactionEngine` · `QBDecisionEngine` · `PlayerDecisionEngine` · `AdaptiveGameplanEngine`
(prolonge l'adaptation V21, 12.2 quater) · `PlayerDevelopmentEngine`.

### Garde-fous (valables pour CHAQUE bloc — font partie de la « définition de fini »)
1. **Rétrocompatibilité** : avec l'interrupteur coupé, les tests existants passent à l'identique.
2. **Déterminisme** : chaque nouveau système tire dans **son propre flux aléatoire**, dérivé de la graine du match et
   du numéro d'action (précédent : placement latéral V18, « hasard séparé »). Même graine + même état + mêmes équipes
   + mêmes notes → mêmes décisions et mêmes résultats. Test dédié.
3. **Rapport de calibration automatique** avant / après sur ≈ 1 000 matchs (le test d'équilibre existant) : complétion,
   sacks, INT, YPA, pertes de balle, points, drives, premiers downs, équilibre par équipe. Hors tolérance = on corrige
   avant de continuer.
4. **Cotes du moteur** : tout bloc qui change la distribution des résultats refait la calibration en direct (13.4, puis
   13.1 / `outils/fit_live.py` si besoin). Leçon de l'étape 4 : l'adaptation avait poussé 13.4 à « outsiders +24 % ».
5. **Temps de calcul** : une semaine = ≈ 2 700 matchs (300 par affiche pour les cotes) ; aujourd'hui 16-20 min sur
   GitHub, limite du job 75 min. Mesure à chaque bloc ; budget : **≤ 2 × le temps actuel**.
6. **Visible pour le spectateur** : chaque bloc ajoute ce qu'il produit au GameFeed (champs additifs, schéma
   rétrocompatible), au site (terrain, play-by-play, fiche joueur, stats) et, si utile, au commentateur
   (nouvelles prises via le workflow « Commentaire audio »).
7. **Semaine re-produite et auditée** avec le nouveau notebook (`audit_moteur.py` : 0 anomalie bloquante) avant d'être
   utilisée par le calcul du samedi.
8. **Un bloc à la fois** : jamais deux systèmes non testés empilés.

### Blocs (ordre obligatoire)

**Bloc A — état post-snap, progression du QB, cible réelle** *(phases 1, 3 et 4 du programme d'origine, regroupées :
une lecture n'a de sens que s'il y a un état défensif à lire)* — notebook V22
- Le playbook définit pour chaque passe : cible primaire, secondaire, tertiaire, checkdown, options scramble / throwaway.
- `DefensiveReactionEngine` produit un état post-snap : pour chaque receveur *libre / serré / couvert / double*, couverture
  (homme / zone, Cover 1-2-3-4…), blitz, temps avant pression.
- `QBDecisionEngine` lit dans l'ordre : primaire → secondaire → TE → RB → scramble / throwaway / sack.
- Enregistrer **cible prévue** et **cible réelle** ; stats : complétions / incomplètes / INT par cible réelle, pression,
  sack, scramble, throwaway ; taux de première lecture.
- Commencer par **mesurer l'existant** (stats de passe de V21, temps par match) : c'est la référence du rapport de calibration.
- Site : cible réelle sur le terrain (la route animée suit le receveur choisi), « off his first read » dans le play-by-play.
- Tests : primaire libre, primaire couvert / secondaire libre, tout couvert (checkdown / throwaway / sack), double couverture, blitz.

**Bloc B — intelligence du QB, poche et pression** *(phases 2 et 5)* — notebook V23
- Attributs : awareness, processing, coverage reading, decision making, pocket awareness, pressure response,
  anticipation, aggressiveness — ils **pèsent** sur les décisions sans les rendre certaines (un QB élite peut se tromper).
- Chrono de poche : temps de traitement du QB contre arrivée de la pression ; sacks et interceptions deviennent
  (en partie) la conséquence de mauvaises décisions.
- Site / stats : temps avant le lancer, pression, scramble animé ; fiche QB avec ces attributs.
- Tests : processing 90 vs 65 sur la même situation (distribution, pas un seul tirage), pression précoce, collapsing pocket.

**Bloc C — intelligence des joueurs** *(phases 6 et 7)* — notebook V24
- Receveurs : route IQ, release, séparation, reconnaissance zone / homme, réception sous pression, contested catch
  (abstraction statistique : écart entre route dessinée et comportement réel, pas de physique fine).
- Défenseurs : play recognition, zone IQ, man IQ, awareness, réaction, discipline, pursuit.
- Tests : deux défenseurs de notes différentes face à la même situation réagissent différemment (en distribution).

**Bloc D — adaptation en match et plan de jeu** *(phases 8 et 9)* — notebook V25
- **Prolonge V21** (concepts / formations mis de côté, couverture qui change, blitz, hurry-up) avec une mémoire de
  tendances : blitz répétés sur 3e down → quick pass / screen / draw / protection ; WR1 trop ciblé → attention, bracket,
  double ; puis l'attaque bascule vers WR2 / TE / RB ; contre-ajustements.
- Plan de jeu : tendances défensives / offensives, zones fortes / faibles, formations préférées, fréquence de blitz,
  couvertures, répartition course / passe, cibles favorites → play calling.
- Site : les ajustements restent dans le play-by-play et le commentaire (existant V21), enrichis des nouvelles raisons.
- Tests : détection de tendance, ajustement offensif, ajustement défensif, contre-ajustement.

**Bloc E — progression des joueurs** *(phases 10, 11 et 12)* — notebook V26
- Notes séparées : base, actuelle, forme, développement, potentiel ; évolution **par attribut** (pas seulement l'OVR) ;
  expérience (lecture, décision, reconnaissance) et âge (plafond / régression physique).
- **À décider au début du bloc** : l'échelle de temps (ici une saison = une semaine de 18 matchs par équipe : qu'est-ce
  qu'une « année » ?), la persistance d'une semaine à l'autre (comme `staffs_next_week`), un **garde-fou anti-inflation**
  (moyenne de ligue stable, plafonds).
- Site : fiche joueur avec l'évolution (courbe par semaine).
- Tests : progression, régression, potentiel, forme, évolution d'attributs, évolution déterministe.

**Fin de programme — validation complète** *(phases 13 et 14)* : tests unitaires et d'intégration de tous les modules,
simulation complète, statistiques, déterminisme, non-régression (score, drives, actions, premiers downs, passe, course,
pertes de balle, sacks, stats joueurs / équipes, Next Gen Stats). Puis **étape 6 : plus de franchises**, avec ces systèmes.

### Objectif final (exemple de chaîne visée)
2nd & 7 · PA Shot · cible primaire WR1 · défense Cover 2 + safety qui penche sur WR1 → snap → play action → le QB voit
le safety → WR1 défavorable → progression vers WR2 → WR2 se démarque → passe complète. Action suivante : la défense
repère l'usage répété de WR2 → la couverture s'ajuste → le QB le voit → le TE se libère → changement de cible.

---

## Bloc A — ✅ terminé le 04/10/2026 (notebook V22.1, décisions allumées)

**V22 — branchement** (PR #12, interrupteur coupé) :
- Modules `gamecenter_serveur (1)/moteur/` (Python pur, `moteur/README.md`) : `progressions` (primaire, secondaire,
  tertiaire, checkdown et routes de 18 concepts ; HEAVY : WR1 inéligible), `reaction_defensive`
  (`DefensiveReactionEngine` → `PostSnapState` : homme / zone Cover 0-4, rushers, receveur LIBRE / SERRE / COUVERT /
  DOUBLE, temps avant pression), `decision_qb` (`QBDecisionEngine` : lecture dans l'ordre → cible réelle, throwaway,
  scramble, sack), `resolution` (probabilités ajustées + normalisation), `stats`, `aleatoire` (flux dédié
  `decision-passe|graine|n° d'action`). 23 tests unitaires (< 1 s), dont les 5 situations demandées + déterminisme ;
  workflow GitHub « Tests moteur ».
- Notebook V22 : cellule **12.2 quinquies** (import du dossier, branchement dans `simulate_drive_franchise`, GameFeed
  `play.decision` + route de la cible réelle, textes « Pass thrown away » / « X scramble », contrôles) ;
  `DECISIONS_ENABLED` **coupé par défaut** (`GC_DECISIONS=1` pour l'allumer). Coupé : GameFeed identiques à V21
  (20 matchs comparés octet par octet ; 1 008 matchs : toutes les mesures identiques ; semaine du 12/10 produite par
  `generer_semaine.py` en V21 et en V22 : contenu identique, `audit_moteur.py` 0 anomalie bloquante — seul l'ordre des
  clés des stats défensives varie, comme déjà d'une exécution à l'autre en V21 : ordre d'un `set` Python).
- Site (et cellule 427) : « · off his first read » dans le play-by-play ; la route animée est déjà celle du porteur,
  donc de la cible réelle.
- `generer_semaine.py` / `simuler_exhibition.py` : `GC_MOTEUR_DIR` (exhibition : `--sans-decisions` depuis V22.1).
- Outils : `outils/moteur/rapport_calibration.py` (rapport automatique, verdict), `outils/moteur/calibrer_bloc_a.py`
  (facteurs de normalisation), `outils/moteur/reference_v21.json` (référence), `outils/moteur/rapport_v22_bloc_a.json`.

**V22.1 — allumage** (PR #13) : `DECISIONS_ENABLED` allumé par défaut (`GC_DECISIONS=0` : moteur V21) ; moteur/
introuvable avec `GC_MOTEUR_DIR` donné → le calcul s'arrête (jamais de semaine V21 en silence) ; tests du moteur lancés
avant chaque calcul du samedi ; cache des cotes distinct allumé / coupé. Vérifié :
- 12.3 décisions allumées : équilibre et identités (passe VEC > CTX > AEG > MNL, blitz, 4e essais, gros gains, course
  MNL, défense AEG) passent.
- 13.4 (cotes en direct, 1 008 matchs neufs) passe, mieux qu'en V21 : écart moyen 0,006 (V21 : 0,013), extrêmes à
  ±0,013, outsiders −4,6 %.
- 13.2 : contrôle désormais les cotes publiées (300 simulations, avant 150) avec une tolérance de biais statistique
  (2,5 écarts-types, au moins 3 %). Avec 3 % fixes (1,7 écart-type), l'échantillon de 12.3 — un tirage bas : 47,9 % de
  victoires à domicile, 48,8 % sur 4 jeux de 1 008 matchs — sortait à −3,3 % ; 300 simulations neuves : 49,8 %.
- Bug de V21 corrigé : sans règle de safety, le porteur pouvait être arrêté DERRIÈRE son en-but (73 matchs sur 1 008
  en V21 ; visible sur le site, détecté par la semaine d'exemple de 14.2 quand le ballon sortait du terrain) → arrêt
  sur la ligne des 1. Le moteur coupé n'est donc plus identique octet par octet à V21 dans ces matchs-là.
- Semaine du 12/10 produite par `generer_semaine.py` (notebook complet, décisions allumées) en 1 701 s :
  `audit_moteur.py` 0 anomalie bloquante (mêmes types d'alerte que les semaines en ligne), 2 915 passes décidées,
  aucune action dans un en-but, cotes sur tous les matchs ; le serveur la charge et la sert.

**Rapport de calibration** (test d'équilibre 12.3, 1 008 matchs, mêmes graines ; tolérances de la PR #12, fusionnée) :

| Mesure | V21 | V22.1 allumé | Tolérance |
|---|---|---|---|
| Complétion | 65,4 % | 65,2 % | ± 2 points |
| Sacks / dropback | 8,1 % | 8,2 % | ± 1 point |
| INT / tentative | 2,4 % | 2,5 % | ± 0,5 point |
| Yards / tentative | 7,67 | 7,53 | ± 0,3 |
| Yards nets / dropback | 6,62 | 6,52 | ± 0,3 |
| Yards / course | 5,64 | 5,64 | ± 0,2 |
| Pertes de balle / match | 3,61 | 3,72 | ± 0,3 |
| Points / match | 51,8 | 51,4 | ± 2 |
| Drives / match | 21,0 | 21,1 | ± 1 |
| Premiers downs / match | 42,7 | 42,9 | ± 2 |
| Actions / match | 126,5 | 127,1 | ± 5 |
| Part de dropbacks | 59,0 % | 58,7 % | ± 2 points |
| Victoires CTX · VEC · AEG · MNL | 48,5 · 48,8 · 47,0 · 55,7 % | 53,8 · 48,5 · 52,4 · 45,3 % | chacune 40-60 % |
| Temps par match | 128-140 ms | 133 ms (× 1,04 au plus) | ≤ × 2 |

Temps : notebook V21 complet sans semaine 19,3 min sur la machine de test (13.4 : 256 s, 12.3 : 153 s) ;
une semaine complète (`generer_semaine.py`) 1 733 s en V21 et 1 747 s en V22 coupé, mesurées en parallèle sur la
même machine (× 1,01). Décisions allumées, le notebook complet s'arrête en 13.2 (« moneyline mal calibrée » :
biais −3,4 % pour ±3 % tolérés) — attendu, c'est le garde-fou 4 ; d'ici là, temps par match × 1,02.
Décisions (V22 allumé) : 1re lecture 43,8 % des lancers, sous pression 16,9 %, lancer à 2,16 s en moyenne,
≈ 2 scrambles, 4 throwaways et 3,4 fins de poche sans solution par match ; cibles WR1 36,9 % · WR2 25,6 % ·
TE 18,9 % · RB 11,5 % · WR3 3,2 % (avant : WR1 ≈ 55-60 %, RB seulement sur les screens).

**Choix faits pendant le calibrage** (à relire) :
- Écart de notes receveur / défenseur : 20 points de note pour un « pas » de séparation. À 8 points, les écarts des
  rosters (WR MNL 68-74 contre CB AEG 87-90) rendaient MNL presque toujours couvert : MNL tombait à 31-39 %.
- Les probabilités de base gardent l'écart des notes d'unité (`pass_off` contre `pass_def`) : la décision module,
  elle ne remplace pas (cohérent avec la décision n° 2).
- Effets de concept 12.2 (profond / court) : ceux de la route réellement lancée ; aucun sans lancer.
- Scramble = course du QB (comme en NFL : la tentative de passe devient une course).

**Reste hors dépôt** : mettre à jour la fiche technique du notebook (V22 / V22.1, cellule 12.2 quinquies, 13.2).

**À surveiller (bloc A)** :
- MNL perd ≈ 10 points de victoires (55,7 → 45,3 % au test d'équilibre) : ses receveurs sont les plus faibles de la
  ligue ; l'ajustement hebdomadaire (12.3) et le bloc B (intelligence du QB) peuvent le faire bouger.
- Taux de 1re lecture 43,8 % et WR3 peu ciblé (3 %) : à affiner au bloc B (processing, anticipation) et dans les
  progressions (le slot n'est lu que sur STICK / SCREEN).
- ~~**Safety**~~ : ✅ ajouté en V23 (voir « Bloc B » ci-dessous).

## Safety + Bloc B — ✅ terminés le 04/10/2026 (notebook V23, allumés)

**Safety** (validé seul avant le bloc B, garde-fou 8) — cellules 12.2, 11.6, 11.2, 11.5, 11.7, interrupteur
`SAFETY_ENABLED` :
- porteur, receveur ou QB sacké arrêté dans son propre en-but -> 2 points pour la défense, free kick de l'équipe qui
  a concédé depuis sa ligne des 20 (journal : entrée `KICKOFF` avec `free_kick`, distance dans un flux dédié
  `safety|graine|n° d'action`) ; en prolongation, un safety termine le match ; fumble perdu dans l'en-but : ligne
  des 1 (comme V22.1) ;
- GameFeed : `result: "safety"`, `possession_change: "safety"`, `safety_via` (run / complete / sack), `highlight:
  "SAFETY"`, texte « X downed · Safety » / « Sacked in the end zone · Safety », puis « Free kick, N yds » ;
- site : puce « SAFETY · 2 PTS », ballon dans l'en-but, éclair, play-by-play, stats, drive « Safety », commentaire
  écrit, foule et effets (parité audio vérifiée) ; cue enregistrée `SAFETY` (4 prises au catalogue, **à générer** :
  workflow « Commentaire audio », `seulement` = `SAFETY`) ; `audit_moteur.py` : 2 points pour la défense, sinon bloquant ;
- mesure (1 008 matchs, décisions du bloc A) : toutes les mesures identiques à V22.1 à ±0,01 près, points / match
  +0,3, safety dans ≈ 9 % des matchs (NFL ≈ 7 %) ; semaine du 12/10 produite (notebook complet, 13.2 / 13.4 passés)
  en 1 560 s, `audit_moteur.py` 0 anomalie bloquante.

**Bloc B — intelligence du QB, poche et pression** — cellule **12.2 sexies**, modules `moteur/intelligence_qb.py` et
`moteur/decision_qb.py` (`decide_b`), interrupteur `QB_IQ_ENABLED` (`GC_BLOC_B=0` : décisions du bloc A) :
- **8 attributs** (awareness, processing, coverage reading, decision making, pocket awareness, pressure response,
  anticipation, aggressiveness) : les rosters n'ont que 4 notes de QB -> dérivés de ces notes (resserrés autour de 80),
  de l'identité de la franchise (CTX lit, VEC ose, AEG protège le ballon, MNL encaisse) et d'un écart propre au joueur
  (hash de son id). **Hors OVR** : notes, unités et cotes d'avant-match inchangées. Fiche du QB sur le site.
  CTX 90 · 89 · 91 · 94 · 82 · 86 · 87 · 56 — VEC 88 · 82 · 87 · 89 · 80 · 85 · 88 · 85 — AEG 83 · 84 · 87 · 81 · 87 ·
  81 · 81 · 33 — MNL 81 · 76 · 82 · 79 · 78 · 82 · 81 · 47 (même ordre).
- **chrono de poche** : reconnaissance au snap (awareness), pas de lecture (processing), lancer avant l'ouverture
  (anticipation) contre le temps avant la pression, allongé / raccourci dans la poche (pocket awareness) ; dans les
  0,45 dernière seconde le QB est **pressé** ;
- **statut perçu** : erreurs de lecture (coverage reading ; plus en zone ; plus sous pression selon pressure response)
  -> passe dans une couverture crue ouverte (interception × 1,25) ou receveur libre ignoré ; jamais nulles (un élite se
  trompe) ; **style** : aggressiveness (fenêtres serrées, passes forcées) tempéré par decision making ; **fin de
  poche** : scramble, throwaway, passe forcée, sack (ballon gardé trop longtemps) ;
- le slot (WR3) est lu dans 3 concepts de plus (CURL, FOUR_VERTS, DAGGER) : 3,2 % -> 5,6 % des cibles ;
- GameFeed (additif) : `play.decision.{bloc, qb, perceived, misread, hurried, pocket_time}`, `roster[].qb_iq` ;
  site : scramble animé, « · under pressure », stats « Avg. time to throw », « Pressured dropbacks », « QB
  scrambles », fiche du QB ; commentaire écrit « holds it too long… sacked » ;
- tests : 20 tests du bloc B (`moteur/tests/test_bloc_b.py`, toujours en distribution) : processing 90 contre 65,
  pression précoce, poche qui se referme, pressure response, coverage reading, aggressiveness, decision making,
  anticipation, élite qui se trompe, déterminisme, bloc A intact sans attributs ; 43 tests en < 1 s.

**Rapport de calibration** (12.3, 1 008 matchs, mêmes graines ; `outils/moteur/rapport_v23_bloc_b.json`) :

| Mesure | V21 | V22.1 | V23 (safety + bloc B) | Tolérance |
|---|---|---|---|---|
| Complétion | 65,4 % | 65,2 % | 65,3 % | ± 2 points |
| Sacks / dropback | 8,1 % | 8,2 % | 8,3 % | ± 1 point |
| INT / tentative | 2,4 % | 2,5 % | 2,4 % | ± 0,5 point |
| Yards / tentative | 7,67 | 7,53 | 7,54 | ± 0,3 |
| Yards nets / dropback | 6,62 | 6,52 | 6,53 | ± 0,3 |
| Yards / course | 5,64 | 5,64 | 5,67 | ± 0,2 |
| Pertes de balle / match | 3,61 | 3,72 | 3,66 | ± 0,3 |
| Points / match | 51,8 | 51,4 | 51,8 | ± 2 |
| Drives / match | 21,0 | 21,1 | 21,1 | ± 1 |
| Premiers downs / match | 42,7 | 42,9 | 43,0 | ± 2 |
| Actions / match | 126,5 | 127,1 | 127,3 | ± 5 |
| Part de dropbacks | 59,0 % | 58,7 % | 58,9 % | ± 2 points |
| Victoires CTX · VEC · AEG · MNL | 48,5 · 48,8 · 47,0 · 55,7 % | 53,8 · 48,5 · 52,4 · 45,3 % | 57,6 · 45,0 · 53,3 · 44,0 % | chacune 40-60 % |
| Temps par match | 128-140 ms | 133 ms | ≈ 130 ms (× 0,95) | ≤ × 2 |

Décisions (V23) : 1re lecture 46,5 % (bloc A 43,8 %), QB pressé 22,8 % des lancers, lancer à 2,14 s, poche 3,21 s,
erreurs de lecture 7,5 % des lancers ; **35 % des interceptions viennent d'une passe forcée ou mal lue, 45 % des sacks
d'un ballon gardé trop longtemps** (le reste : pression / tirage). Par QB : CTX lance à 2,01 s, 49 % en 1re lecture,
6,5 % d'erreurs, 7,8 % de sacks · VEC 2,31 s, 48 % en 1re lecture, 7,6 % d'erreurs, 6,6 % de sacks, INT 2,9 % (le plus de passes forcées) · AEG 1,94 s,
9,9 % de sacks, 2,2 % d'INT · MNL 2,25 s, 42 % en 1re lecture, 9,4 % d'erreurs, 10,2 % de sacks.
Cotes : 13.2 passe (biais −1,5 % pour ±4,4 % tolérés ; Brier 0,2396 contre 0,2558 pour la formule de notes) ; 13.4
passe sans recalibrage (écart moyen 0,007, extrêmes ±0,006, outsiders −7,6 %). Semaine du 12/10 produite par
`generer_semaine.py` (notebook complet) en 1 591 s (V22.1 : 1 701 s) : `audit_moteur.py` 0 anomalie bloquante ;
site : les 39 matchs rejoués dans Chromium sans erreur, parité audio identique, test du commentaire enregistré passé.

**Choix faits pendant le calibrage** (à relire) :
- Poids des attributs : seule une part `POIDS = 0,45` de l'écart d'une qualité au QB de référence (80) pèse
  (aggressiveness, un style, pèse en entier). À 100 %, l'écart entre le QB de CTX (decision making 94) et celui de MNL
  (79) donnait CTX 62 % / MNL 38 % ; à 0,6, MNL 40,2 % (trop près de la limite). Mesuré : avec des QB identiques, MNL
  remonte à 48 % — c'est bien la qualité du QB qui pèse.
- Attributs dérivés resserrés autour de 80 (`COMPRESSION = 0,5`) ; profils d'identité modestes (± 2 à 5 points ;
  aggressiveness : VEC +28, AEG −18).
- Normalisation propre au bloc B : `CALIBRATION_B` (int 1,156 · sack 1,237 · inc 0,925 · yards 0,531).
- Le slot n'est lu davantage qu'au bloc B (`PROGRESSIONS_B`) : coupé, le bloc A reste identique.
- Bug corrigé sur le site : « off his first read » s'affichait sur un sack (QB qui avait décidé de lancer, rattrapé).

**À surveiller (bloc B)** :
- MNL 44,0 % et VEC 45,0 % (CTX 57,6 %) : l'écart de QB se voit ; l'ajustement hebdomadaire (12.3) et le bloc C
  (receveurs de MNL les plus faibles) peuvent le faire bouger. Si une franchise approche 40 / 60 %, baisser `POIDS`.
- Sacks : MNL 10,2 % et AEG 9,9 % contre VEC 6,6 % (ligne de VEC + QB) ; moyenne de la ligue inchangée.
- Le commentaire enregistré du safety reste à générer (workflow « Commentaire audio »).

**Exhibition** (site, onglet « Exhibition ») : VEC @ CTX V23 (`exh-v23-vec-ctx`, 30-26, graine 9 400 013) remplace
CTX-MNL V21 — choisi parmi 40 candidats pour ce qu'il montre : 61 lancers au-delà de la 1re lecture, 23 sous pression,
2 scrambles d'Ezra Vale, 4 throwaways, 5 sacks « ballon gardé », 2 safeties, 14 ajustements en direct.

**Reste hors dépôt** : fiche technique du notebook (V22 / V22.1 / V23 : cellules 12.2 quinquies, 12.2 sexies, safety).

## Bloc C — ✅ terminé le 04/10/2026 (notebook V24, allumé)

**Intelligence des joueurs** — cellule **12.2 septies**, module `moteur/intelligence_joueurs.py` (+ `decider_passe`,
`reaction_defensive`, `resolution`, `stats`), interrupteur `PLAYER_IQ_ENABLED` (`GC_BLOC_C=0` : moteur V23) :
- **Receveurs** (WR, TE, RB), 6 attributs : route IQ, release, separation, reconnaissance zone / homme, catch in
  traffic (réception sous pression), contested catch. **Défenseurs** (CB, S, LB), 7 attributs : play recognition,
  zone IQ, man IQ, awareness, reaction, discipline, pursuit. Dérivés des notes du poste (resserrés autour de 80), de
  l'identité de la franchise (CTX lit le jeu ; VEC se démarque et joue le ballon mais mord ; AEG tient ses zones, très
  discipliné ; MNL gagne les ballons disputés, défense physique en homme, poursuit) et d'un écart propre au joueur.
  **Hors OVR** : notes, unités et cotes d'avant-match inchangées. Fiche joueur sur le site.
- **Ce qui pèse, c'est le profil** : l'écart d'un attribut au **niveau** du joueur (ses notes de route ou de
  couverture, déjà dans le duel de notes du bloc A). Un CB de 90 reste meilleur qu'un CB de 75 (bloc A) ; le bloc C
  dit en plus s'il est meilleur en homme qu'en zone, discipliné ou joueur, vif sur la cassure…
- **État post-snap** : chaque receveur fait face au défenseur **responsable** (homme : son vis-à-vis ; zone : un
  défenseur de la tranche attaquée). Release contre man IQ, separation contre reaction, reconnaissance contre zone /
  man IQ, awareness sur la soupape et la route « hot », play recognition contre le screen. **Écart entre route
  dessinée et route courue** : tirage dont la moyenne et la dispersion dépendent du route IQ. **Coverage bust** (le
  défenseur perd son receveur, plus souvent sur play action et double move, selon discipline et play recognition) :
  receveur seul. Le QB (blocs A-B) lit ensuite cet état.
- **Réception** : libre (open), serrée (catch in traffic contre reaction), couverte ou doublée (contested catch contre
  man / zone IQ ; awareness du défenseur -> interceptions) ; **yards après la réception** : separation contre pursuit.
  Le défenseur responsable est crédité de l'interception et de la passe défendue sur un ballon disputé (12.2).
- **Hasard** : flux à part `joueurs-passe|graine|n° d'action` ; le flux des décisions du QB n'est pas consommé (sans
  attributs, `decider_passe` rend exactement la décision du bloc B — testé).
- **GameFeed** (additif) : `play.decision.{reception, coverer, bust, busts}`, `roster[].player_iq`. **Site** : sur le
  terrain, le défenseur responsable colle le receveur sur un ballon disputé (et c'est bien lui sur la fiche), personne
  n'est près de la réception sur un coverage bust ; play-by-play « · contested catch », « · caught in traffic »,
  « · X in coverage », « · coverage bust (X) » ; stats d'équipe « Contested catches », « Coverage busts allowed » ;
  fiche « Receiver intelligence » / « Coverage intelligence » ; commentaire écrit (« Broken up by X! », « Coverage
  bust! … », contested catch). Commentaire enregistré : pas de nouvelle prise (appels génériques, déjà couverts).
- **Tests** : 22 tests du bloc C (`moteur/tests/test_bloc_c.py`, en distribution) dont **deux défenseurs de notes
  différentes face à la même situation** (man IQ / reaction en homme, zone IQ en zone, discipline et play recognition
  -> coverage busts, play action, screen, soupape), le niveau compté une seule fois, route IQ, release, reconnaissance,
  réception, yards après la réception, déterminisme, bloc B intact sans attributs ; 65 tests en < 10 s.

**Rapport de calibration** (12.3, 1 008 matchs, mêmes graines ; `outils/moteur/rapport_v24_bloc_c.json`) :

| Mesure | V21 | V23 (safety + bloc B) | V24 (bloc C) | Tolérance |
|---|---|---|---|---|
| Complétion | 65,4 % | 65,3 % | 65,1 % | ± 2 points |
| Sacks / dropback | 8,1 % | 8,3 % | 8,0 % | ± 1 point |
| INT / tentative | 2,4 % | 2,4 % | 2,5 % | ± 0,5 point |
| Yards / tentative | 7,67 | 7,54 | 7,62 | ± 0,3 |
| Yards nets / dropback | 6,62 | 6,53 | 6,62 | ± 0,3 |
| Yards / course | 5,64 | 5,67 | 5,67 | ± 0,2 |
| Pertes de balle / match | 3,61 | 3,66 | 3,72 | ± 0,3 |
| Points / match | 51,8 | 51,8 | 52,1 | ± 2 |
| Drives / match | 21,0 | 21,1 | 21,1 | ± 1 |
| Premiers downs / match | 42,7 | 43,0 | 43,4 | ± 2 |
| Actions / match | 126,5 | 127,3 | 127,4 | ± 5 |
| Part de dropbacks | 59,0 % | 58,9 % | 59,0 % | ± 2 points |
| Victoires CTX · VEC · AEG · MNL | 48,5 · 48,8 · 47,0 · 55,7 % | 57,6 · 45,0 · 53,3 · 44,0 % | 52,4 · 49,6 · 54,0 · 44,0 % | chacune 40-60 % |
| Temps par match | 128-140 ms | 162 ms* | 165 ms* (× 1,02) | ≤ × 2 |

\* mesurés sur la machine de cette session, chargée par d'autres calculs (le rapport compare à la référence V21 :
× 1,18) ; V23 et V24 mesurés dans les mêmes conditions.

Bloc C (V24) : ballons **open** 48,4 % des lancers (complétion 82,3 %, INT 0,9 %), **in traffic** 43,0 % (60,2 %,
3,3 %), **contested** 8,6 % (37,2 %, 8,3 %) ; **coverage bust** sur la cible 2,1 % des lancers (≈ 2,9 par match, toutes
lectures comprises). 1re lecture 47,2 %, QB pressé 22,8 %, lancer à 2,14 s (bloc B inchangé).
Cotes : **13.2** passe (biais −1,0 % pour ±4,5 % tolérés ; Brier 0,2437 contre 0,2585 pour la formule de notes ;
spread 50,4 %, total 49,7 %) ; **13.4** passe sans recalibrage (écart moyen 0,010, extrêmes ±0,019, outsiders
−13,1 %). Notebook complet sans semaine : 1 213 s ; **semaine du 12/10** produite par `generer_semaine.py` (notebook
complet, décisions des blocs A-B-C) en 1 911 s — machine chargée par deux autres exécutions du notebook en parallèle
(V23 : 1 591 s seule) ; `audit_moteur.py` : **0 anomalie bloquante, 0 alerte** (39 matchs, 5 442 actions, 3 049
passes décidées au bloc C : 1 320 open, 1 133 in traffic, 222 contested, 43 coverage busts sur la cible ; `player_iq`
dans les rosters) ; le serveur la charge et la sert. Site : exhibition rejouée dans Chromium sans erreur JS
(play-by-play, stats, fiches, terrain) ; test du commentaire enregistré : couverture complète (20 806 moments).

**Choix faits pendant le calibrage** (à relire) :
- **Première version écartée** : les attributs bruts (écart à 80) recomptaient le niveau des joueurs, déjà dans le
  duel de notes du bloc A. Mesuré : MNL (DB et WR les plus faibles de la ligue) tombait à 35-41 % au test 12.3 quel
  que soit le poids (0,3 à 0,55), VEC montait à 56-61 % ; un témoin aux attributs neutres restait à 43-47 %. Compenser
  par l'échelle du duel (30 au lieu de 20) ne suffisait pas (MNL 36-41 %). D'où le **profil** (écart au niveau du
  joueur, `POIDS_NIVEAU = 0`) : MNL 44,0 %, sans toucher à l'échelle du duel (20).
- `POIDS = 0,45` (comme au bloc B). À 0,7 : CTX 49,4 · VEC 49,2 · AEG 57,0 · MNL 44,3 % (AEG trop près de 60).
- Coverage bust : base 0,8 % par receveur (× 2,2 sur play action, × 1,5 sur double move) -> 2,1 % des cibles ; à
  1,2 % : 2,9-3,6 % des cibles, plus de gros jeux (points / match +2,4 avant recalibrage). Sans busts, l'équilibre ne
  bouge pas (mesuré) : ils ne sont pas en cause dans l'écart de MNL.
- Bruit générique de la séparation 0,65 au bloc C (0,9 avant) : l'écart de route (0,30-0,85 selon le route IQ) prend
  le reste ; neutre pour l'équilibre (mesuré : MNL 45,2 % avec les attributs neutres).
- Profils d'identité : VEC release / separation +1 (+3 au départ : l'avantage s'ajoutait à ses notes, déjà les
  meilleures), MNL man IQ +4 et reaction +2 (défense physique), AEG zone IQ +4 et discipline +6, VEC discipline −6.
- Normalisation propre au bloc C : `CALIBRATION_C` (int 1,166 · sack 1,241 · inc 0,921 · yards 0,423) ; contrairement
  aux blocs A-B, le facteur « yards » du bloc C est bien appliqué aux yards de la passe (au bloc B, `CALIBRATION_B`
  « yards » n'est pas utilisé : c'est celui du bloc A — sans conséquence mesurée, laissé tel quel pour ne pas changer V23).

**À surveiller (bloc C)** :
- MNL 44,0 % (comme en V23) : sa défense de passe concède le plus de receveurs libres (≈ 49 % des dropbacks adverses
  contre 36-44 % ; autant avec le bloc C neutralisé) — ce sont ses notes de DB (duel du bloc A). Le bloc D (plan de jeu : courir plus contre une défense qui couvre bien)
  peut l'aider ; si une franchise approche 40 / 60 %, baisser `intelligence_joueurs.POIDS` ou revoir `PROFILS`.
- Test du commentaire enregistré (`outils/audio/test_commentaire_v02.js`) sur la semaine du 12/10 : « pas deux fois
  la même prise de suite » échoue (6 cas) — sans lien avec le bloc C (même résultat avec la page d'avant) : les cues
  d'ajustement en direct ADJ_SHELVE_FORM et ADJ_D_NOBLITZ n'ont qu'**une** prise et reviennent deux fois dans un même
  match (les semaines précédentes n'avaient pas d'ajustements V21). Ajouter des prises (workflow « Commentaire audio »).
- Les effets du profil sont modestes par construction (écarts de ± 1 à 4 points effectifs) : ils se voient surtout
  dans les duels extrêmes (contested catches de MNL, busts de VEC, zones d'AEG).

**Exhibition** (site, onglet « Exhibition ») : MNL @ VEC V24 (`exh-v24-mnl-vec`, 35-40, graine
9 400 014) remplace VEC @ CTX V23 — choisi parmi 40 candidats pour ce qu'il montre du bloc C : 2 contested catches,
5 passes défendues par le défenseur responsable, 2 coverage busts (concédés par la défense de MNL), avec les blocs A-B
(33 lancers au-delà de la 1re lecture, 11 sous pression, 4 scrambles, 5 throwaways, 5 sacks « ballon gardé »), 1 safety
et 11 ajustements en direct (7 types). `simuler_exhibition.py` note ces duels dans l'index (`contested`, `broken_up`,
`busts`) et la carte du site les affiche.

**Reste hors dépôt** : fiche technique du notebook (V22 / V22.1 / V23 / V24 : cellules 12.2 quinquies, sexies,
septies, safety).

## Bloc D — ✅ terminé le 05/10/2026 (notebook V25, allumé)

**Adaptation en match et plan de jeu** — cellule **12.2 octies**, module `moteur/plan_de_jeu.py` (+ `decider_passe`,
`reaction_defensive`, `resolution`), interrupteur `GAMEPLAN_ENABLED` (`GC_BLOC_D=0` : moteur V24) :
- **Plan de jeu par adversaire** (avant le match, sans hasard) : fréquence de blitz du coordinateur adverse -> part du
  jeu rapide (quick game, screens, draws) ; couvertures préférées (part d'homme) -> concepts contre l'homme (mesh,
  croisements, slants) ou contre la zone (curl, stick, dagger, sail, champ) ; duels en homme (Cover 1) -> **cible
  favorite** (meilleur mismatch, lue en premier une fois sur trois quand elle dépasse le 2e duel de 3 points ; flux à
  part « plan-de-jeu ») ; receveurs extérieurs contre safeties -> part des passes profondes ; écart des notes d'unité
  -> probabilité de passer ± 0,05 au plus ; en défense, la **menace** de l'attaque adverse (meilleur receveur) est
  brackétée un peu plus souvent (+ 8 points). Résumé lisible : « quick game vs the blitz, beat man coverage, take shots
  deep, target Zane Montague » / « bracket Nico Saint-Clair ».
- **Mémoire de tendances** (`MemoireTendances`, fenêtre de 8 à 10 dropbacks selon l'équipe) : ce que chaque camp a vu
  de l'autre — cibles du QB (réussite, yards), blitz sur 3e essai et sur les dropbacks, sacks / lancers pressés sur
  blitz, doubles par receveur, jeu rapide réussi contre le blitz.
- **AdaptiveGameplanEngine** (déterministe ; chaque ajustement dure `tenue` snaps et dit sa **raison**) :
  attaque **o_quick** (blitz répétés -> quick pass / screen / draw, surtout sur 3e essai ; passes profondes moins
  appelées) · **o_protect** (3 sacks / lancers pressés sur blitz -> un RB reste protéger : poche + 0,20 s, 5e rusher
  ramassé en partie, une route de moins) · **o_away** (un receveur doublé 3-4 fois -> la progression l'évite, bascule
  vers WR2 / TE / RB) ; défense **d_bracket** (receveur ≥ 40-50 % des cibles récentes et productif -> double sur lui) ·
  **d_rotate** (contre-ajustement : l'attaque a basculé -> le bracket suit la nouvelle cible) · **d_disguise**
  (contre-ajustement : le jeu rapide a puni le blitz -> moins de blitz sur 3e essai, Cover 2 / 4). Profils : CTX vite
  (2 blitz sur 3e essai suffisent, bracket 50 %), AEG lent et long (tenue 14 snaps), VEC garde son style (ne protège
  pas, tourne peu, déguise peu), MNL têtu (seuils les plus hauts). Affichage : une fois par équipe et par type (rotation :
  deux).
- **Effets sur la passe** (`moteur.decider_passe(..., plan=...)`) : bracket (le double va sur le receveur choisi, même
  tirage consommé qu'au bloc A ; jamais en Cover 0), protection, progression réordonnée. Sans plan : bloc C à
  l'identique (testé). Branchements du notebook : feuille d'appel (`pb_play_weight`), probabilité de passer, appel
  défensif (pression déguisée), passe décidée (12.2 quinquies).
- **GameFeed** (additif) : `play.adjust[].reason`, kinds `plan_o` / `plan_d` / `o_quick` / `o_protect` / `o_away` /
  `d_bracket` / `d_rotate` / `d_disguise`, `game.gameplan`, `play.decision.plan`. **Site** : raison dans le
  play-by-play ; onglet **« Game plan »** du Match centre (plan des deux équipes + ajustements faits jusqu'à l'action
  affichée, sans spoiler) ; « · into the bracket », « · game-plan read » ; commentaire écrit des 8 nouveaux types ;
  carte d'exhibition. Corrigé au passage : « holds it too long… sacked » ne s'affichait plus depuis le bloc C (test
  `bloc==='B'`). Commentaire enregistré : 7 cues ajoutées au catalogue (`ADJ_GAMEPLAN`, `ADJ_O_QUICK`, `ADJ_O_PROTECT`,
  `ADJ_O_AWAY`, `ADJ_D_BRACKET`, `ADJ_D_ROTATE`, `ADJ_D_DISGUISE`, 3 prises chacune) — **à générer** (workflow
  « Commentaire audio »). `audit_moteur.py` : ajustement mal formé (bloquant), ajustement du bloc D sans raison (alerte),
  `game.gameplan` mal formé (bloquant).
- **Tests** : 32 tests du bloc D (`moteur/tests/test_bloc_d.py`) — détection de tendance, ajustement offensif,
  ajustement défensif (dont le bracket en distribution), **contre-ajustement** (bracket -> l'attaque lit ailleurs -> le
  bracket tourne vers le TE -> l'évitement expire), plan de jeu, progression, chaîne (sans plan = bloc C, déterminisme,
  le bracket détourne les lancers, flux séparé) ; 97 tests en ≈ 11 s.

**Rapport de calibration** (12.3, 1 008 matchs, mêmes graines ; `outils/moteur/rapport_v25_bloc_d.json`) :

| Mesure | V21 | V24 (bloc C) | V25 (bloc D) | Tolérance |
|---|---|---|---|---|
| Complétion | 65,4 % | 65,1 % | 65,4 % | ± 2 points |
| Sacks / dropback | 8,1 % | 8,0 % | 8,3 % | ± 1 point |
| INT / tentative | 2,4 % | 2,5 % | 2,4 % | ± 0,5 point |
| Yards / tentative | 7,67 | 7,62 | 7,62 | ± 0,3 |
| Yards nets / dropback | 6,62 | 6,62 | 6,61 | ± 0,3 |
| Yards / course | 5,64 | 5,67 | 5,70 | ± 0,2 |
| Pertes de balle / match | 3,61 | 3,72 | 3,66 | ± 0,3 |
| Points / match | 51,8 | 52,1 | 52,7 | ± 2 |
| Drives / match | 21,0 | 21,1 | 21,0 | ± 1 |
| Premiers downs / match | 42,7 | 43,4 | 43,4 | ± 2 |
| Actions / match | 126,5 | 127,4 | 127,1 | ± 5 |
| Part de dropbacks | 59,0 % | 59,0 % | 58,6 % | ± 2 points |
| Victoires CTX · VEC · AEG · MNL | 48,5 · 48,8 · 47,0 · 55,7 % | 52,4 · 49,6 · 54,0 · 44,0 % | **52,3 · 46,6 · 52,3 · 48,8 %** | chacune 40-60 % |
| Temps par match | 128-140 ms | 165 ms* | 149 ms* (× 1,06 sur la référence) | ≤ × 2 |

\* machine de cette session, chargée par d'autres calculs.

Bloc D (V25) : par match, ≈ 1,9 bracket, 1,5 rotation du bracket, 1,6 bascule hors du double, 0,6 quick game contre le
blitz, 0,4 protection, 0,14 pression déguisée (+ les 2 plans de jeu de chaque équipe, dits à leur première action) ; les
ajustements V21 ne changent pas (≈ 11 par match). **Cibles : WR1 40,1 % -> 33,8 %, WR2 25,0 -> 28,1 %, TE 15,1 -> 16,7 %,
WR3 5,4 -> 6,1 %** — l'attaque bascule quand son WR1 est brackété ; 32 % des dropbacks voient un double réel, et le QB
ne lance dans le bracket que 1,5 % du temps. Par équipe : CTX tourne son bracket 462 fois sur 504 matchs, VEC 47 ;
VEC ne protège jamais et subit le plus de pressions déguisées adverses (105). MNL remonte de 44,0 % à 48,8 %.

**Choix faits pendant le calibrage** (à relire) :
- Mesuré composant par composant (1 008 matchs chacun) : la **protection** (+ 0,35 s au départ) ajoutait ≈ 0,7 point
  par match et faisait tomber VEC (l'équipe qui blitze le plus, et qui par identité ne protège pas) à 42,6 % ; les
  **brackets** ajoutent ≈ 0,9 point (le safety qui aide laisse de la place aux autres receveurs, règle du bloc A) ;
  les concepts du plan et le déplacement course / passe ne changent presque rien aux points. Retenu : protection
  + 0,20 s / 5e rusher 0,10, seuil de pression 3 pour CTX et AEG (réglage B parmi trois essayés : VEC 46,0 · 46,5 · 43,8 %).
- Normalisation propre au bloc D : `CALIBRATION_D` (int 1,092 · sack 1,376 · inc 0,914 · yards 0,361), partie de
  `CALIBRATION_C` (`calibrer_bloc_a.py --bloc D`).
- Bascule hors du double : 3 doubles (CTX, AEG) ou 4 (VEC, MNL) dans la fenêtre ; à 2, elle se déclenchait presque à
  chaque match (les doubles naturels du bloc A sur le WR1 en Cover 2 / 4 sont fréquents).
- Le bracket du plan (menace adverse, + 8 points) est présent sur toutes les passes ; le site ne dit « into the bracket »
  que si le double a vraiment eu lieu sur la cible.
- Aucun ajustement ne dépend du score (seulement de ce qui a été vu) : les cotes en direct ne bougent pas — 13.2 et
  13.4 passent sans recalibrage dans le notebook complet (ci-dessous).

**Semaine du 12/10** produite par `generer_semaine.py` (notebook complet, blocs A-B-C-D, 13.2 et 13.4 passés) en
2 340 s, seule sur la machine de cette session (V24 : 1 911 s sur machine chargée ; V21 : 1 733 s ici -> × 1,35, budget
× 2) ; `audit_moteur.py` : **0 anomalie bloquante, 0 alerte** (39 matchs, 5 374 actions, un plan de jeu dans chaque
match, 3 018 passes jouées sous un plan dont 1 000 avec un double réel ; 73 brackets, 71 rotations, 63 bascules hors du
double, 25 quick game contre le blitz, 20 protections, 8 pressions déguisées). Semaine non versée au dépôt : c'est le
calcul du samedi qui la produit.

**Exhibition** (site, onglet « Exhibition ») : CTX @ VEC V25 (`exh-v25-ctx-vec`, 37-45, graine 9 400 013) remplace
MNL @ VEC V24 — choisi parmi 40 candidats pour ce qu'il montre du bloc D : les deux plans de jeu (CTX : « quick game vs
the blitz, beat man coverage, take shots deep, target Zane Montague » ; VEC : bracket de Rafe Ellison), CTX qui répond
au blitz de VEC par le quick game et un RB en protection, VEC qui bascule hors du double sur Nico Saint-Clair, deux
brackets suivis chacun d'une rotation (contre-ajustements), 1 lancer dans un bracket ; avec les blocs A-C (59 lancers
au-delà de la 1re lecture, 26 sous pression, 4 contested catches, 6 ballons défendus, 1 coverage bust), 1 safety et 27
ajustements en direct (16 types). Rejoué dans Chromium (bureau et mobile 390 px) : onglet « Game plan », raisons dans
le play-by-play, commentaire écrit, aucune erreur JS. `simuler_exhibition.py` note les ajustements du plan de jeu, les
contre-ajustements et les lancers dans un bracket (`gameplan_adjust`, `counters`, `bracket_throws`).

**À surveiller (bloc D)** :
- VEC 46,6 % (le plus bas) : l'équipe qui blitze le plus subit le quick game et la protection adverses, et ne protège
  pas elle-même (identité). Si elle approche 40 %, baisser `PROTECTION` ou `PLAN["quick"]`, ou laisser VEC protéger
  rarement.
- Beaucoup de lignes d'ajustement par match (≈ 11 du bloc D, plans compris, + ≈ 11 de V21) : réduire `MONTRER` si le
  play-by-play paraît chargé.
- AEG tourne souvent son bracket (552 fois sur 504 matchs) malgré son identité « lente » : sa tenue est longue (14
  snaps) mais son seuil de rotation est celui de CTX (3) — à monter à 4 si Guillaume veut une AEG plus têtue.
- Le commentaire enregistré des 7 cues du bloc D reste à générer (d'ici là : sous-titre et voix de l'appareil ; le test
  `test_commentaire_v02.js` les comptera comme manquantes).
- Tests du serveur hors dépôt (`tserver.py`, `tavance.py`, `taccounts.py`, `tparis2.py`, `tsearch.py`, `tadjust.py`) :
  pas dans le dépôt, non relancés dans cette session (le serveur n'a pas changé ; le site a été vérifié dans Chromium).

**Reste hors dépôt** : fiche technique du notebook (V22 → V25 : cellules 12.2 quinquies, sexies, septies, octies, safety).

## Bloc E — ✅ terminé le 05/10/2026 (notebook V26, allumé)

**Décisions de Guillaume** (début du bloc, 05/10) : une saison = une semaine, **une « année » = 4 semaines** (l'âge
augmente d'un an toutes les 4 semaines) ; les **vraies notes** évoluent (notes d'unité, OVR et cotes suivent) ;
anti-inflation **« ligue + écart d'équipe borné »** ; **forme figée pour la semaine** (tout se met à jour entre deux
semaines : les cotes calculées avant la semaine restent justes).

**Progression des joueurs** — cellule **12.2 nonies**, module `moteur/developpement.py` (`PlayerDevelopmentEngine` du
programme), interrupteur `PROGRESSION_ENABLED` (`GC_BLOC_E=0` : rosters de base chaque semaine, moteur V25) :
- **Notes séparées** : base (roster 12.1), actuelle (développée), **forme** (± 3 points sur toutes les notes de la
  semaine, tirée des performances de la semaine jouée — mesurées dans le groupe de poste — et du bilan de l'équipe),
  **potentiel** (marge au-dessus de la base, plus grande chez les jeunes), rythme de **développement** (slow · normal
  · fast · star), **âge** et **expérience** (déterministes : hash de l'id). Notes jouées = arrondi(actuelle + forme).
- **Évolution par attribut** : physique (vitesse, accélération, puissance, force, mobilité, bras, jambe, esquive) —
  pic à 29 ans (RB : 27) puis régression rapide ; technique (précision, routes, réception, blocs, pass rush,
  couverture, plaquage) — pic à 31 ans, régression lente ; mental (decision_making) — progresse avec les années
  jouées, pic à 34 ans. Jouer fait progresser (temps de jeu : RB2 selon ses courses).
- **Expérience** -> bonus (relatif à la ligue, somme nulle, ± 4 au plus) sur les attributs d'intelligence des blocs B
  et C : lecture, processing, anticipation du QB ; route IQ et reconnaissance des receveurs ; reconnaissance du jeu,
  zone / man IQ, awareness et discipline des défenseurs.
- **Anti-inflation** : (1) moyenne de chaque note par unité (RB1 et RB2 à part) ramenée sur sa valeur de départ ;
  (2) plafonds (potentiel, 99) ; (3) **écart d'équipe borné** : **force** (moyenne des 4 notes d'unité) à **± 0,2**
  point de sa base, par un **décalage commun** des notes de l'équipe (ses joueurs gardent leurs écarts entre eux : le
  jeune monte, le vétéran baisse), et chaque **note d'unité** à **± 0,75** (réduction des écarts du côté concerné).
- **Persistance** : `week.json -> players_next_week` (état complet) et `progression` (dérive de la ligue, écarts
  d'unité, force, corrections, plus fortes hausses / baisses), repris par 15.1 ; semaine précédente sans état (avant
  V26) : **amorce** depuis ses stats. Le serveur ne publie pas ces champs (pas de spoiler).
- **Hasard** : flux `progression|<semaine>|<id>` (garde-fou 2). Au départ (aucune semaine jouée), notes = roster : le
  moteur joue exactement comme V25 (contrôlé dans la cellule et au test d'équilibre : mêmes chiffres qu'en V25).
- **GameFeed** (additif) : `roster[].progression` (`age`, `ovr`, `ovr_base`, `potential`, `form`, `dev`,
  `experience`, `iq_bonus`, `base`, `delta`, `history`). **Site** (et cellule 427) : fiche joueur — âge et potentiel
  sous la note, écart à la base sur chaque attribut (▲ / ▼), section **« Development »** et **courbe de la note par
  semaine** (base en pointillés). Commentaire : rien de nouveau (la progression se passe entre deux semaines).
- **Audit** (`audit_moteur.py`) : notes = base + écart, 40-99, forme ± 3, **notes figées pendant la semaine**,
  `players_next_week` contrôlé, force ± 0,2 et unités ± 0,75 — bloquant ; dérive de la ligue > 0,5 — alerte.
- **Tests** : 32 tests du bloc E (`moteur/tests/test_bloc_e.py`) — progression, régression, potentiel, forme,
  évolution par attribut, expérience, déterminisme, anti-inflation (ligue, RB à part, force et unités dans un cas
  extrême, sans effacer les écarts entre joueurs), persistance JSON, roster complété, courbe ; 128 tests en ≈ 25 s.

**Rapport de calibration** (12.3, 1 008 matchs, mêmes graines, après N semaines de progression jouées —
`rapport_calibration.py --semaines N --graine-trajectoire G` ; `outils/moteur/rapport_v26_bloc_e.json`) :

| Mesure | V21 | V25 / V26 au départ | 8 sem. | 16 sem. | 24 sem. | 32 sem. | Tolérance |
|---|---|---|---|---|---|---|---|
| Complétion | 65,4 % | 65,4 % | 65,3 % | 65,2 % | 65,4 % | 65,9 % | ± 2 points |
| Sacks / dropback | 8,1 % | 8,3 % | 8,2 % | 8,2 % | 8,2 % | 8,1 % | ± 1 point |
| INT / tentative | 2,4 % | 2,4 % | 2,3 % | 2,2 % | 2,4 % | 2,4 % | ± 0,5 point |
| Yards / tentative | 7,67 | 7,62 | 7,60 | 7,57 | 7,59 | 7,69 | ± 0,3 |
| Yards / course | 5,64 | 5,70 | 5,75 | 5,74 | 5,80 | 5,71 | ± 0,2 |
| Pertes de balle / match | 3,61 | 3,66 | 3,61 | 3,56 | 3,70 | 3,68 | ± 0,3 |
| Points / match | 51,8 | 52,7 | 52,4 | 51,9 | 52,6 | 52,7 | ± 2 |
| Victoires CTX · VEC · AEG · MNL | 48,5 · 48,8 · 47,0 · 55,7 % | 52,3 · 46,6 · 52,3 · 48,8 % | 55,6 · 43,6 · 51,7 · 49,2 % | 52,1 · 47,1 · 51,7 · 49,1 % | 53,3 · 41,0 · 55,6 · 50,2 % | 51,6 · 46,7 · 55,2 · 46,5 % | chacune 40-60 % |

Toutes les autres mesures (drives, premiers downs, actions, part de dropbacks, yards nets) restent dans leurs
tolérances ; temps par match × 1,2 à × 1,3 sur la référence (machine chargée). Une semaine de progression coûte
≈ 1 s (mise à jour + garde-fou) ; la cellule 12.2 nonies ≈ 20 s (trois semaines d'essai).

**Choix faits pendant le calibrage** (à relire) :
- **La borne d'équipe proposée au départ (± 3 par unité) ne protégeait pas l'équilibre** : mesuré, VEC 72 % et MNL
  24 % après 8 semaines ; ± 1 : MNL 34-36 % ; ± 1,5 : MNL 35 %. Le moteur est très sensible : ≈ 15 points de % de
  victoires par point de force (et les notes individuelles jouent aussi : duels receveur / défenseur, QB). D'où une
  borne de **force** (moyenne des 4 unités) à ± 0,2, plus une borne par unité à ± 0,75 (à ± 1 et force ± 0,25, MNL
  tombait à 40,1 % sur une trajectoire : course − 1,0, passe − 0,9). Le principe choisi (écart d'équipe borné) est
  gardé ; seule la valeur a changé.
- **Décalage commun plutôt que réduction** pour la force : réduire tous les écarts d'une équipe (λ) effaçait, chez une
  équipe âgée comme MNL, à la fois le déclin de ses vétérans et la progression de ses jeunes ; le décalage commun ne
  retire que la dérive de l'équipe entière.
- **RB1 et RB2 à part** dans la moyenne de la ligue : sur les 8 RB ensemble, les yards par course montaient (jusqu'à
  + 0,20) quand les RB1, plus jeunes, progressaient aux dépens des RB2.
- Forme : 0,35 × forme d'avant + 1,6 × performance (écarts-types dans le groupe de poste) + bruit 0,5, ± 3 ; bilan de
  l'équipe ± 0,5. Croissance 4 points / an à 21 ans → 0,4 à 29 ; régression physique − 0,9 / an au pic, + 0,7 par an.
- Âges de départ tirés du hash de l'id (22-31 ans, QB 24-33, K / P 24-35, remplaçants plus jeunes) : MNL a les
  titulaires les plus âgés (27,2 ans de moyenne), VEC son WR1 (Nico Saint-Clair, 31 ans, rythme lent).

**Semaine du 12/10** produite par `generer_semaine.py` (notebook complet, blocs A-E ; amorce depuis les stats de la
semaine du 05/10) en 2 036 s — machine de cette session, chargée en partie par trois rapports de calibration en parallèle (V25 : 2 340 s seule ; V21 : 1 733 s -> × 1,17, budget × 2) ; `audit_moteur.py` : **0 anomalie bloquante, 0 alerte** (39 matchs, 5 348 actions ; notes figées pendant la semaine, notes = base + écart dans chaque GameFeed, `players_next_week` contrôlé). Semaine 3 ; 12.2 nonies, 12.3, 13.2 et 13.4 passés dans le notebook complet. Progression pour la semaine du 19/10 : dérive de la ligue 0,16, force CTX −0,15 · VEC +0,20 · AEG −0,17 · MNL +0,07 ; hausses Adrien Pellegrini (MNL CB, 26 ans) +3, Lazlo Hargrove (AEG CB, 24 ans) +2 ; baisses Bastien Kincaid (VEC WR, 22 ans) −4, Lazlo Coventry (VEC EDGE, 31 ans) −2. Site : fiche joueur rejouée dans Chromium (bureau et mobile 390 px) — section « Development », courbe W2 -> W3, écarts ▲ / ▼, aucune erreur JS, pas de défilement horizontal. Semaine non versée au
dépôt : c'est le calcul du samedi qui la produit.

**À surveiller (bloc E)** :
- **VEC** : 41-47 % selon la trajectoire (départ 46,6 %) — son jeu de passe passe par un WR1 de 31 ans qui décline ;
  la force moyenne ne voit pas cet effet « joueur clé ». Si VEC approche 40 %, baisser `FORCE_EQUIPE_MAX` (0,15) ou
  pondérer la force par le jeu de l'équipe (part de passes, cible principale).
- **Retraites et recrues** : avec une année = 4 semaines, les titulaires les plus âgés passent 35 ans en quelques mois
  (fortes baisses individuelles : − 10 à − 16 d'OVR après 26 semaines pour les plus vieux). À décider avec l'étape 6
  (plus de franchises) ; `developpement.completer` accueille déjà des joueurs nouveaux ou partis.
- Le bonus d'expérience est relatif à la ligue (pas à l'équipe) : une équipe jeune gagne un peu d'intelligence ; effet
  modeste (± 4 points d'attribut au plus, POIDS 0,45), à surveiller avec l'équilibre.
- Tests du serveur hors dépôt (`tserver.py`…) : non relancés (le serveur n'a changé que pour son crochet de test).

**Reste hors dépôt** : fiche technique du notebook (V22 → V26 : cellules 12.2 quinquies à nonies, safety).

## Fin de programme — validation complète ✅ (06/10/2026)

Outil : `outils/moteur/validation_complete.py` (≈ 30 min sur 3 cœurs ; `--rapide` ≈ 6 min) — rapport
`outils/moteur/rapport_validation_complete.json` ; workflow manuel « Validation complète » (GitHub, `rapide` / `complet`).
Chaque étage du moteur joue les 1 008 matchs du test d'équilibre (12.3, mêmes graines) dans son propre processus.

| Contrôle | Résultat |
|---|---|
| Tests unitaires (5 modules de tests, blocs A → E) | ✅ 129 tests en 21 s (A 23 · B 20 · C 22 · D 32 · E 32) |
| Intégration : V21, A, A-B, A-C, A-D, A-E, puis A-E après 8, 16, 32 et 52 semaines (10 × 1 008 matchs) | ✅ GameFeed exporté et `validate_gamefeed` : 0 problème ; `audit_moteur.check_game` action par action : 0 anomalie bloquante, 0 alerte (hors deux artefacts d'un match joué hors semaine : pas de cotes, courbe vide) ; **stats joueurs = stats d'équipe** (passes, complétions, yards, TD, INT, courses, réceptions ; INT et sacks crédités à la défense adverse) : 0 écart sur 28 224 identités par étage ; champs de chaque bloc présents exactement quand le bloc est allumé |
| Déterminisme | ✅ 720 matchs rejoués (dans l'ordre et à l'envers) identiques ; trajectoire de progression rejouée : même état ; **autre processus** (`PYTHONHASHSEED` différent) : 96 matchs identiques — après correction (ci-dessous) |
| Non-régression | ✅ chaque étage redonne **à l'identique** (toutes les mesures) son rapport publié : V23 bloc A + safety, V23, V24, V25, V26 au départ, et les 4 trajectoires du rapport V26 (8, 16, 24, 32 semaines) ; bloc E au départ = V25 **match par match** |
| Calibration contre V21 (tolérances de la PR #12) | ✅ tous les étages ; après 16, 32 et 52 semaines ✅ ; **après 8 semaines (trajectoire neuve 660 000) : yards / course 5,90 pour 5,64 ± 0,2 ❌** (voir « À décider ») |
| Semaine réelle (notebook complet, cotes 13.2 / 13.4 comprises) | ✅ semaine du 12/10 reproduite (`generer_semaine.py`, 1 780 s, machine chargée par la validation) : 0 anomalie, 0 alerte, 39 matchs, **5 348 actions et force des équipes identiques au bloc E** ; ✅ **semaine du 19/10 enchaînée** (reprend `players_next_week` du 12/10) : 0 anomalie, 0 alerte, 5 357 actions, courbe des joueurs W2 → W3 → W4 |

**Correction faite** (déterminisme) : 12.2 quater (V21) parcourait les ajustements défensifs d'une action dans un
`set` ; quand deux arrivaient ensemble (« Defense rolls to deep shells » et « Defense backs off the blitz »), leur
**ordre d'affichage** dépendait du hachage de Python (4 matchs sur 36 touchés). Rien ne changeait au jeu (mêmes mesures
partout), mais le GameFeed n'était pas reproductible octet par octet. `dict.fromkeys(hurt)` : ordre d'apparition.

**Stats joueurs / équipes, Next Gen Stats** (repères, par équipe et par match ; V21 → A-E au départ → A-E après 52 semaines) :

| | V21 | A-E | A-E, 52 sem. |
|---|---|---|---|
| Points · yards | 25,9 · 396 | 26,3 · 398 | 25,8 · 394 |
| Yards à la passe · à la course | 263 · 146 | 254 · 158 | 251 · 157 |
| INT · sacks subis · fumbles perdus | 0,8 · 2,9 · 1,0 | 0,8 · 3,0 · 1,0 | 0,8 · 3,0 · 1,0 |
| 3e essais convertis · passes de 20+ · courses de 10+ | 46,9 % · 8,7 % · 20,5 % | 47,5 % · 8,3 % · 21,7 % | 46,6 % · 8,2 % · 21,8 % |
| Yards à la réception WR1 · WR2 · WR3 · TE · RB | 53 · 13 · 14 · 15 · 6 % | 36 · 30 · 6 · 18 · 10 % | 33 · 32 · 7 · 18 · 10 % |
| Défense créditée : plaquages · sacks · INT · passes défendues | 44,3 · 2,9 · 0,84 · 3,8 | 44,7 · 3,0 · 0,79 · 3,1 | — |
| Lancer · QB pressé · 1re lecture | — | 2,12 s · 21,9 % · 47,1 % | 2,12 s · 22,6 % · 46,7 % |
| Ballons open · in traffic · contested (complétion) | — | 50 % (82 %) · 42 % (60 %) · 8 % (37 %) | — |

Leaders par match (A-E) : Dax Holloway 385 yards à la passe, Titus Okafor 146 à la course, Nico Saint-Clair 155 à la
réception (V21 : 217 — l'attaque ne passe plus tout par le WR1). Le passage aux décisions déplace ≈ 10 yards de la
passe vers la course (scrambles, comptés comme des courses depuis le bloc A).

**Semaines enchaînées** (trajectoire neuve 660 000) : force de chaque franchise toujours à ± 0,2, dérive de la ligue
≤ 0,48, garde-fou d'équipe actif presque chaque semaine, `controler` sans problème ; écart d'OVR à la base de − 16 à
+ 8 (vétérans / jeunes) ; victoires 43-57 % (VEC le plus bas : 43,4 % à 32 semaines, 43,9 % à 52).

**À décider (Guillaume) — yards par course après quelques semaines de progression.** Sur une trajectoire, les semaines 6
à 10 donnent 5,81 · 5,87 · 5,90 · 5,77 · 5,70 yards / course (V21 5,64, départ 5,70 ; tolérance ± 0,2) ; les rapports
V26 avaient déjà + 0,05 à + 0,16. Ce n'est **pas** la forme (semaine 8 sans forme : 5,90 aussi) : ce sont les notes
développées. Hypothèse, non démontrée : la moyenne de la ligue est recentrée sans tenir compte du temps de jeu ; si le RB
de l'équipe qui court le plus (MNL) progresse pendant que d'autres déclinent, la moyenne ne bouge pas mais les yards de la
ligue montent. Points par match : la valeur d'une seule semaine varie d'environ ± 0,6 (forme) — mesuré 54,1 une fois après 52
semaines (hors tolérance), 52,9 · 53,5 · 52,9 · 53,5 sur les semaines 50 à 53 : léger glissement (+ 0,5 sur le départ),
dans la tolérance. Options : (a) accepter (la tolérance s'applique à la moyenne de quelques semaines, pas à un seul état
hebdomadaire) et surveiller ; (b) recentrer la ligue en pondérant par le temps de jeu (RB, puis tous les postes) ;
(c) ramener la tolérance « yards / course » du bloc E à ± 0,3. (b) change les trajectoires : nouveau rapport V26.1 et
semaine re-produite.

**À surveiller** : VEC 43-48 % sur les trajectoires longues (comme au bloc E) ; la cue `SAFETY` et les 7 cues du bloc D
restent à générer (workflow « Commentaire audio ») ; tests du serveur hors dépôt (`tserver.py`…) non relancés (serveur
inchangé).

**Action « GameFeeds d'exhibition »** (`.github/workflows/gamefeeds.yml`, `outils/exhibition/gamefeeds.py`) : reprise de
la branche du bloc C (jamais fusionnée) et passée au moteur V26 (blocs A-E, notes et staffs de la dernière semaine de
`data/weeks`) — 12 GameFeeds (une par affiche) dans l'artefact « gamefeeds-v26 », à charger sur le site (« Load
GameFeed »). Le bouton « Run workflow » n'apparaît qu'une fois le fichier dans `main`.

## Pour la conversation suivante
1. Lire ce fichier, `gamecenter_serveur (1)/moteur/README.md` et les sections 15-22 du README du serveur.
2. **À décider (Guillaume)** : yards par course après quelques semaines de progression (fin de programme, options a / b / c)
   — si (b) : recentrage pondéré par le temps de jeu, rapport V26.1, `validation_complete.py` relancé.
3. **Étape 6 : plus de franchises / divisions**, avec les systèmes de l'étape 5 (aucune logique codée pour les 4 équipes de
   test) ; décider en même temps des **retraites et recrues** (bloc E : avec une année = 4 semaines, les plus âgés passent
   35 ans en quelques mois). Relancer `validation_complete.py` à la fin (les tolérances, l'équilibre 40-60 % et le temps
   par match restent les garde-fous).
4. Générer le commentaire enregistré des 7 cues du bloc D et de `SAFETY` (workflow « Commentaire audio », mode `generer`).


## Extension du playbook V0.1 — ✅ branchée le 06/10/2026 (notebook V27, cellule 12.2 decies)
`programme/GRIDIRON_SIM_PLAYBOOK_EXPANSION_DATABASE_V0.1.md` : à la demande de Guillaume, **tout ce qui n'était pas
encore dans le notebook est branché** avant l'étape 6 (pendant la validation du programme) ; les formations et concepts
déjà présents ne sont pas recopiés (alias). Détail : README du serveur, section 21, et `moteur/README.md`.
- Catalogue `moteur/playbook_expansion.py` (tests `test_expansion.py`) : 22 formations, 144 plays, 41 concepts (dont
  6 options et 6 RPO), 9 routes, motions / shifts, protections, enchaînements ; défense : 33 paquets, 11 fronts, jeux
  de rush, mouvements ; `ALIAS` (131 noms déjà portés par le moteur), `RESERVE` (5, avec la raison).
- Crochets : `simulate_drive_franchise` (après l'appel défensif : `_XP_SNAP_HOOK`), `_decision_pass_hook`
  (`_dec_expansion` -> `moteur.decider_passe(..., appel=...)`). Interrupteur `EXPANSION_ENABLED` / `GC_EXPANSION`.
- Mesuré : rapport de calibration dans les tolérances (points 52,7 -> 51,7, victoires 46,6-54,7 %), semaine du 12/10
  produite et auditée (0 anomalie, 0 alerte), exhibition V27 CTX @ MNL.

**À surveiller (extension)** :
- **Temps du calcul du samedi** : ≈ ×1,3 par match (230 contre 175 ms) ; semaine d'essai 49 min sur une machine chargée
  (limite du job : 75 min). Si le samedi dépasse 60 min, réduire le nombre de plays candidats ou mettre en cache les
  enveloppes de la feuille d'appel (V21 / bloc D).
- **MNL 46,6 %** (VEC 48,0 %) : dans 40-60 %, mais MNL perd 2 points ; à suivre sur les semaines réelles.
- Réserve à compléter par Guillaume : définition de **SALEM** et de **SPILL_PROTECTION** ; formations **10 personnel**
  (4 WR) dès que les rosters de l'étape 6 en auront.
- Commentaire enregistré : aucune cue nouvelle (motion, RPO, option, paquet déguisé : sous-titres seulement).

## Fin de période : field goal ou continuer — ✅ 06/10/2026 (notebook V28, cellule 12.2 undecies)
Demande de Guillaume avant l'étape 6 : en fin de Q2 / Q4, une équipe à portée jouait presque toujours une action au lieu
de tirer (4 field goals sur 166 dernières actions à portée). Cause : field goal regardé au 4e essai seulement. Module
`moteur/fin_de_periode.py` : comparaison « field goal / continuer » (points attendus au Q2, probabilité de victoire au Q4)
à chaque snap des 45 dernières secondes. Après : 39 / 145 (les autres : match déjà gagné, touchdown nécessaire, touchdown
plus rentable près de la ligne de but). Calibration dans les tolérances (+1,5 point par match). Détail : README section 22.
**À surveiller / plus tard** : poser le genou quand on mène ; temps morts et horloge entre les actions (le moteur n'en a
pas : à décider avec l'étape 6 si on veut une gestion de l'horloge plus réaliste).

## À surveiller (repris de l'étape 4)
- **MNL 55,7 %** au test d'équilibre (dans 40-60 %, au-dessus des autres) : la baisse des fumbles profite surtout à
  l'équipe qui court le plus ; à suivre sur les semaines réelles.
- Cotes en direct recalibrées pour V21 (13.4 : outsiders −0,3 %) ; à re-vérifier si l'adaptation change.

## Pièges connus
- Bloc E : `reset_franchises()` remet les rosters ET l'état de progression à la base (12.3, 14.2 l'appellent) ; les
  notes d'une vraie semaine viennent de `progression_reprendre(prev)` (15.1, exhibition). Les caches d'intelligence
  des blocs B / C (`QB_IQ`, `PLAYER_IQ`) sont vidés à chaque changement de notes (`appliquer_progression`).
- La page du site a un **espace de noms JavaScript unique** : vérifier qu'un nom est libre avant de l'ajouter
  (`AC` = contexte audio ; un second `let AC` avait cassé la page).
- Une IA qui change de plan selon le score **fausse le modèle de cotes en direct** → refaire 13.4 après tout changement.
- La cellule 427 (site embarqué dans le notebook) doit suivre les changements de rendu du site (`outils/regen427.py`).
- Le site lit la musique et les sons dans `audio/manifest.json` : `generer_audio.py` et `composer_musique.py` préservent
  les catégories qu'ils ne gèrent pas ; ne pas éditer le manifeste à la main.
- Exhibition : `outils/exhibition/simuler_exhibition.py --home X --away Y` rejoue le notebook (≈ 20 min) sans produire
  de semaine — pratique pour montrer un nouveau bloc avant qu'il n'arrive dans une vraie semaine.
