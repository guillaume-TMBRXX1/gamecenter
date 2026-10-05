# Feuille de route — GridironSim (mise à jour le 05/10/2026, bloc D terminé)

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
| **5** | **ENGINE INTELLIGENCE** — un vrai système décisionnel (programme ci-dessous, blocs A → E) | **en cours** — ✅ bloc A allumé (notebook V22.1, PR #12 + #13) ; ✅ safety + bloc B allumés (notebook V23) ; ✅ bloc C allumé (notebook V24) ; ✅ bloc D allumé (notebook V25) ; **prochain : bloc E** | notebook (+ modules Python) + site + serveur |
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

## Pour la conversation suivante
1. Lire ce fichier, `gamecenter_serveur (1)/moteur/README.md` et les sections 15-18 du README du serveur.
2. **Bloc E** — progression des joueurs (notes base / actuelle / forme / développement / potentiel, évolution par
   attribut, expérience, âge), notebook V26 : décider d'abord l'échelle de temps, la persistance d'une semaine à
   l'autre et le garde-fou anti-inflation ; mêmes garde-fous, rapport
   `outils/moteur/rapport_calibration.py --reference outils/moteur/reference_v21.json`. Les attributs des blocs B et C
   (dérivés des notes) sont la base naturelle de « l'évolution par attribut ».
3. Générer le commentaire enregistré des 7 cues du bloc D (workflow « Commentaire audio », mode `generer`).

## À surveiller (repris de l'étape 4)
- **MNL 55,7 %** au test d'équilibre (dans 40-60 %, au-dessus des autres) : la baisse des fumbles profite surtout à
  l'équipe qui court le plus ; à suivre sur les semaines réelles.
- Cotes en direct recalibrées pour V21 (13.4 : outsiders −0,3 %) ; à re-vérifier si l'adaptation change.

## Pièges connus
- La page du site a un **espace de noms JavaScript unique** : vérifier qu'un nom est libre avant de l'ajouter
  (`AC` = contexte audio ; un second `let AC` avait cassé la page).
- Une IA qui change de plan selon le score **fausse le modèle de cotes en direct** → refaire 13.4 après tout changement.
- La cellule 427 (site embarqué dans le notebook) doit suivre les changements de rendu du site (`outils/regen427.py`).
- Le site lit la musique et les sons dans `audio/manifest.json` : `generer_audio.py` et `composer_musique.py` préservent
  les catégories qu'ils ne gèrent pas ; ne pas éditer le manifeste à la main.
- Exhibition : `outils/exhibition/simuler_exhibition.py --home X --away Y` rejoue le notebook (≈ 20 min) sans produire
  de semaine — pratique pour montrer un nouveau bloc avant qu'il n'arrive dans une vraie semaine.
