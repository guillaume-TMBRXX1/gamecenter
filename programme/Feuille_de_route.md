# Feuille de route — GridironSim / Snapline (mise à jour le 21/10/2026 : moteur plus intelligent, étape 6)

Ordre choisi par Guillaume. **Une conversation par étape (ou par bloc)** : en début de conversation, lire ce fichier,
puis `programme/Mise_en_ligne.md`, `programme/Bilan_prototype.md` et `notebook/NFL_Sim_fiche_technique.md`
(fichiers du projet Claude, hors dépôt) et le `README.md` du serveur (`gamecenter_serveur (1)/README.md`).
**Cette version, dans le dépôt, remplace celle du 03/10** (l'étape 5 « plus de franchises » est remplacée par le
programme ENGINE INTELLIGENCE ; l'extension des franchises vient après, en étape 6).

Le site se met à jour par le dépôt GitHub privé `guillaume-TMBRXX1/gamecenter` (sous-dossier `gamecenter_serveur (1)/`) :
tout changement fusionné dans `main` est redéployé par Railway. Toujours tester en local avant de pousser, depuis
`gamecenter_serveur (1)` : `python -m unittest discover -s moteur/tests -t .` (moteur, serveur, pauses, alerte ; fastapi
requis pour les tests serveur), `python audit_moteur.py data/weeks`, `bash outils/site/tests_navigateur.sh --semaines 1`
(site, audio, recherche, cellule 427, parité). Chaque PR vers `main` repasse les mêmes tests sur GitHub (« Contrôle des
PR », README section 38). Ne jamais relancer `--premiere` (la semaine 1 existe). Ne pas fusionner pendant un calcul
« Semaine suivante » (samedi 01:05 UTC, dimanche en secours).

## Tableau

| # | Étape | État | Touche |
|---|---|---|---|
| 0 | Valider la règle de départage | ✅ validée le 03/10/2026 | — |
| 1 | Comptes joueurs + classement multi-semaines | ✅ en ligne le 03/10 (`5366e55`) | serveur + site |
| 2 | Paris plus riches (combinés, cash-out, historique) | ✅ en ligne le 03/10 (`baab4d3`) | serveur + site |
| 3 | Playbooks plus variés (V19) · 3 bis recherche · 3 ter « Roman 2014 » (V20) | ✅ en ligne le 03/10 | notebook + site |
| 4 | IA adaptatives en direct (notebook V21) | ✅ poussé le 03/10 (`9c610ab`), semaines à partir du 12/10 | notebook + site |
| — | Hors feuille de route, 03-04/10 : fluidité mobile / iPad, Audio System V0.1 → V0.4 (commentaire, foule, effets ElevenLabs hors ligne ; musique originale CC0), accueil économe et sans spoiler (aperçus, teasers), Exhibition (match V21 hors calendrier) | ✅ en ligne (PR #1 → #10) | site + serveur |
| **5** | **ENGINE INTELLIGENCE** — un vrai système décisionnel (programme ci-dessous, blocs A → E) | ✅ **terminé** — ✅ bloc A allumé (notebook V22.1, PR #12 + #13) ; ✅ safety + bloc B allumés (notebook V23) ; ✅ bloc C allumé (notebook V24) ; ✅ bloc D allumé (notebook V25) ; ✅ bloc E allumé (notebook V26) ; ✅ **validation complète** (06/10, un point à décider : yards / course après plusieurs semaines) ; étape 6 lancée | notebook (+ modules Python) + site + serveur |
| 5 bis | Extension du playbook V0.1 (base de connaissances football) branchée au moteur (notebook V27) | ✅ 06/10, notebook V27 | notebook (+ module) + site |
| 5 ter | Décisions de fin de Q2 / Q4 : field goal ou continuer (notebook V28) | ✅ 06/10 | notebook (+ module) + site |
| **6** | **Plus de franchises / divisions** — par paliers (bible des identités) | **en cours** — ✅ palier 1 : 8 franchises (05-08), retraites et recrues (notebook V29, noms validés) · site : My team, fiches joueurs, plein écran agrandi · ✅ palier 2 : 12 franchises (09-12, notebook V30) · ✅ palier 3 : 16 franchises (13-16, notebook V31) · ✅ palier 4 : 20 franchises (17-20, notebook V32) · ✅ franchises 21-24 (hors bible, notebook V33) · ✅ divisions, calibrage, contrôles à 24 (notebook V34) · noms, identités, couleurs et divisions validés (08/10) | notebook (+ modules) + site + serveur |
| — | Hors feuille de route, 09-10/10 : progression rééquilibrée, interface des matchs, iPad / Safari (page allégée), calendrier toutes les 30 min, « Grand Final », pauses de retransmission, audit à bornes par semaine | ✅ en ligne (PR #40 → #48) | notebook + site + serveur |
| **B1** | **Fiabilité** (avant les publicités) : alerte et relance du calcul du samedi, temps du calcul mesuré, contrôle automatique des PR, tests serveur et cellule 427 rapatriés | ✅ **terminé le 11/10** (PR #49, #52 → #55 ; étape 2 : mesure seule) | workflows + tests + notebook (cellule 427) |
| **B2** | **Produit et visibilité** : domaine snapline.live et nom Snapline, scores du bandeau (« Hide scores »), transformation après touchdown, coup d'envoi avec retour, histoire / records / carrières, rappels Web Push, ligues privées, vidéos verticales et référencement | ✅ **terminé le 12/10** (PR #57 → #64) | notebook (+ modules) + site + serveur + workflows |
| 7 | Publicités | **prête (13/10)**, en attente du compte AdSense de Guillaume — README section 47 | site + serveur — voir `Publicites_plan.md` |
| **8** | **Promotion du site** : TikTok, puis Instagram Reels et YouTube Shorts, à partir des vidéos du bloc 2 | **en cours** — plan validé le 13/10 (`programme/Promotion.md`) ; ✅ 8.1 plan et photo de profil · ✅ 8.2 action du jour pour TikTok, « Best play so far » · ✅ 8.3 qualité (image par image, 60 i/s), résumé court, « What is Snapline? » · 8.4 lien compté `/tt` (en attente : 1 000 abonnés) · ✅ 8.4 bis adresse visible, commentaire épinglé · ✅ 8.6 a joueur de la semaine, champion · ✅ 8.6 b match hors norme, franchise · 8.5 Reels et Shorts | contenu + outils vidéo + serveur |
| 9 | **Moteur plus intelligent** — idées 1 et 2 (14/10) : horloge réelle (temps entre les actions, temps morts, genou, spike) et valeur des décisions (4e essai par probabilité de victoire) | ✅ **allumé** (12.2 quaterdecies ; décision de Guillaume du 14/10 : quarts de 15 min, ≈ 18 min de retransmission, 4e essai réaliste selon la situation) — 13.4 recalibré, semaine du 19/10 produite et auditée (README section 53) ; ✅ idée 3 bloc F, course (README 54) · ✅ idée 4 checks avant le snap (README 58) · hors feuille de route : 4e essai plus prudent (59), fumbles disputés (60), « Bigger field » (61), noms des joueurs sur le terrain (62) · ✅ **idée 5** : appel de jeu qui apprend (12.2 vicies semel, README 63) · ✅ **idée 6** : mémoire d'une semaine à l'autre, le film de scouting (12.2 vicies bis, README 65, fusionnée) · hors feuille de route : résultats du jour en cours seulement (README 66, fusionnée) · ✅ **étape 7.1** : la poche et la ligne offensive (12.2 vicies ter, README 67, fusionnée) · ✅ **étape 7.2** : les pénalités pendant l'action (12.2 vicies quater, README 68, fusionnée) · ✅ **étape 7.3** : le banc, les packages, la fatigue et les rotations (12.2 vicies quinquies, README 69 ; PR à fusionner par Guillaume) · 7.4 blessures à venir | notebook (+ modules) + site |

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
   13.1 / `outils/moteur/fit_live.py` si besoin, outil créé le 21/10). Leçon de l'étape 4 : l'adaptation avait poussé 13.4 à « outsiders +24 % ».
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
  workflow GitHub « Tests moteur » (remplacé le 11/10 par « Contrôle des PR »).
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

## 09-10/10/2026 — hors feuille de route (✅ en ligne, PR #40 → #48)
- 09/10 : validation complète avec les références régénérées (#40) ; progression rééquilibrée, interface des matchs
  (#41) ; bannière TD / FG allégée pour Safari, relance du son, journal de diagnostic (#42) ; iPad : page allégée,
  replay repris à la bonne action après un rechargement (#43, #44). README sections 31-34.
- 10/10 : audit à bornes par semaine (chaque semaine contrôlée avec les bornes du garde-fou de sa production, #45) ;
  calendrier du lundi au vendredi, un coup d'envoi toutes les 30 min de 10:00 à 22:00 ; « AI Bowl » renommé
  **« Grand Final »** (clé interne `ai_bowl` conservée : phase, marché des futures, paris enregistrés) ; **pauses de
  retransmission** (fin de Q1 / Q3 10 s, mi-temps 40 s, écran final ; temps de présentation seulement, serveur et site
  sur la même ligne de temps) (#46) ; exhibition BST @ ZPH pour voir les pauses (#47) ; « Semaine suivante » reprend
  `main` avant de pousser (#48). README sections 35-36.

## Bloc 1 — Fiabilité ✅ (11/10/2026)
Une étape = une PR, testée en local, fusionnée par Guillaume.
1. **Alerte et relance du calcul du samedi** (PR #49, README section 37). L'échec du 10/10 venait du **push** (main avait
   avancé pendant le calcul), pas de l'audit. Job « suivi » de `semaine.yml` : issue « calcul-semaine » (étape fautive, fin
   du log de l'étape, mention), fermée au prochain calcul réussi ; push refusé → semaine repoussée depuis un artefact,
   sans recalcul ; panne de machine → une seule relance ; tests / calcul / audit / dépassement → alerte seule.
   Essais réels sur la branche (`test_echec` = audit, push, machine) : issues #50 et #51.
2. **Temps du calcul : mesure seule, aucun changement** (décision du 11/10). ≈ 46 min sur GitHub (étape « Calculer »),
   ≈ 47 min le job, sur 75. Cellule 15.1 ≈ 38 min, dont **91 % pour les cotes d'avant-match** (276 affiches × 50
   simulations + demi-finales à 300, ≈ 14 400 matchs à ≈ 0,18 s) ; préambule (cellules 0 → 14.2) ≈ 5 min sur un seul cœur
   (contrôles et démonstrations : 12.2 nonies 127 s, 12.2 undecies 59 s…). Machine GitHub d'un dépôt privé : sans doute
   2 cœurs. Le calcul local reproduit GitHub (mêmes données JSON ; seul l'ordre des clés des stats joueurs varie d'un
   processus à l'autre). Options écartées : mesure dans le log, parallélisation du reste en série (≈ 1,5 min), contrôles
   sautés le samedi (≈ 5-6 min), cotes réparties sur plusieurs jobs (≈ 15 min). **Plafond réel : 3 600 s par cellule**
   (`generer_semaine.py`, `timeout=3600`) : la 15.1 n'a donc que ≈ 22 min de marge, avant les 75 min du job.
3. **Contrôle des PR** (PR #52, README section 38) : `controle.yml` — Python (unittest, audit), Navigateur (site) et
   Navigateur (parité) en parallèle, ≈ 6 min ; remplace « Tests moteur ». `outils/site/tests_navigateur.sh` : la même
   commande en local. Tests audio réparés (`test_parite_v01`, `test_commentaire_v02`, `test_stade_v03` envoyaient tout
   `data/weeks` à la page) ; parité identique sans sons enregistrés (377 924 décisions). Puis (PR #53) : deux variantes
   pour les 5 cues d'ajustement à une seule prise, générées le 11/10 (catalogue 198 prises).
4. **Tests serveur et cellule 427.** `tserver.py`, `tavance.py`, `taccounts.py`, `tparis2.py`, `tsearch.py`, `tadjust.py`
   et `regen427.py` étaient **perdus** (jamais dans le dépôt) : réécrits. PR #54 : `moteur/tests/test_serveur.py` (17
   tests : direct sans fuite, playoffs, paris, comptes, classements, horloge, semaines enchaînées) et
   `outils/site/test_recherche.js`. PR #55 : `outils/regen427.py` (report bloc par bloc des changements du site ; 12
   synchronisations passées sur 17 reproduites à l'identique) ; cellule 427 synchronisée avec le site du 10/10 **sans
   écrans de pause** (choix du 11/10 : le replay du notebook n'a pas la mécanique du site ; `BRK_SEC={q:0,half:RP_HALF}`
   garde les pauses d'avant) ; `outils/site/test_cellule427.js`.
5. Cette mise à jour de la feuille de route.

**Ruleset de `main` : à décider par Guillaume.** Le 11/10, la PR #53 restait fusionnable pendant ses contrôles, et la
PR #56 (`.md` seul, aucun contrôle) l'était aussi : les contrôles ne sont **pas obligatoires** aujourd'hui. Les rendre
obligatoires a deux effets de bord : (1) « Semaine suivante » pousse **directement** sur `main` (sans PR, avec le jeton
du workflow) — une règle « Require status checks to pass » sur `main` refuserait ce push et la semaine ne paraîtrait
pas (l'alerte de l'étape 1 se déclencherait), sauf à exempter ce push (*Bypass list*) ; (2) une PR qui ne change que
des `.md` ou `programme/` ne lance aucun contrôle (`paths-ignore`) et attendrait indéfiniment. Recommandation :
**laisser les contrôles facultatifs** et ne fusionner qu'une PR aux trois coches vertes.

## Bloc 2 — Produit et visibilité ✅ (11-12/10/2026)
Ordre choisi par Guillaume le 11/10 ; une étape = une PR, testée en local, fusionnée par Guillaume ; avant chaque
étape, état des lieux et choix validés. **Hors bloc** (décision du 11/10) : publicités (reportées à l'étape 7) et paris
sur les joueurs.
1. **Domaine et nom** (PR #57, README 39). Le projet s'appelle **Snapline** ; le site garde « GameCenter ».
   `snapline.live` (Cloudflare, `CNAME @` vers Railway en « DNS only ») est le domaine du service Railway ;
   `www` redirigé par une règle Cloudflare ; `GC_DOMAINE=snapline.live` redirige l'ancienne adresse `*.up.railway.app`
   (308). Les noms internes (fichiers, notebook, projet Railway « NFL Sim ») ne changent pas.
2. **Scores des matchs terminés dans le bandeau** (PR #58, README 40). Affichés par défaut ; Réglages → Display →
   « Hide scores » remet la protection anti-spoiler (fonction unique `seen(id)`).
3. **Transformation après un touchdown** (PR #59, README 41 ; `moteur/transformation.py`, notebook 12.2 duodecies) :
   touchdown à 6 points, puis point après touchdown (≈ 94 %) ou 2 points (≈ 47 %), choix selon le tableau de Vermeil et
   l'agressivité du coordinateur. Interrupteur `GC_TRANSFORMATION=0`. 16 prises de commentaire générées.
4. **Coup d'envoi après chaque score, avec retour** (PR #60, README 42 ; `moteur/coup_envoi.py`, 12.2 terdecies) :
   touchback ≈ 42 %, retour ≈ 25 yards, touchdown sur retour rare (≈ 0,4 %). Interrupteur `GC_COUP_ENVOI=0`. Prises
   générées. Les transformations et les retours arrivent dans les vraies semaines à partir de **celle du 19/10**.
5. **Histoire, records, carrières** (PR #61, README 43 ; `moteur/histoire.py`) : onglet **History** (saisons,
   franchises, records d'un match / d'une saison / de carrière) et section **Career** de la fiche joueur. Calculé par le
   serveur depuis les semaines enregistrées ; rien ne change dans le calcul du samedi.
6. **Rappel « ton équipe joue dans 10 min »** (PR #62, README 44) : Web Push (service worker, manifeste, icônes),
   équipe favorite + cloche sur n'importe quel match, lien `/?watch=<match>`. iPhone : seulement si Snapline est sur
   l'écran d'accueil. Clés `GC_VAPID_PUBLIC` / `GC_VAPID_PRIVATE` / `GC_VAPID_SUBJECT` posées sur Railway le 12/10.
7. **Ligues privées** (PR #63, README 45) : onglet **Leagues**, code de 6 caractères ou lien `/?join=CODE`, classement de
   la semaine et de la saison ; 50 membres par ligue, 10 ligues par compte ; comptes seulement.
8. **Visibilité** (PR #64, README 46) :
   - **Vidéos verticales 1080×1920** (`outils/video/`) : l'**action du jour** (note : bascule de probabilité, touchdown,
     perte de balle, gros gain, « décision folle » au 4e essai, 2 points, long field goal, fin de match) avec ralenti, et
     le **résumé** du plus beau match de la semaine (≈ 2 min 15). Le vrai site est filmé par Chromium ; son du stade
     seulement (la musique se met sur le réseau). Workflow **« Vidéos »** : action du jour tous les soirs (22 h 30 UTC),
     résumé le dimanche, à la demande aussi ; vidéos et légendes dans les *Artifacts* (30 jours), **publiées à la main**
     (aucun connecteur TikTok).
   - **Référencement** : titre, description, adresse canonique, Open Graph / Twitter (`/og.png`), JSON-LD, `/robots.txt`,
     `/sitemap.xml`, texte « What is Snapline? », bouton **Share** au grand écran. Google Search Console : propriété
     « Domaine » validée par Guillaume (TXT dans Cloudflare), sitemap envoyé le 12/10
     (`https://snapline.live/sitemap.xml`), indexation demandée. Pas d'autre outil de mesure (choix du 12/10).
   - Le même jour : un seul match d'exhibition gardé (ZPH–BST, V34) ; GLT–AXM retiré.

## Étape 8 — Promotion (en cours, depuis le 13/10/2026)
Plan complet, validé par Guillaume le 13/10 : **`programme/Promotion.md`** (compte, rythme, heures, formats, hashtags,
musique, premiers posts, mesure, tableau du bilan du lundi). Une étape = une PR, testée en local, fusionnée par Guillaume.
- **Décisions du 13/10** : compte TikTok **personnel** (sons tendance), `@snapline.live`, « Snapline · AI Football »,
  photo de profil = le logo du site (`gamecenter_serveur (1)/outils/promotion/photo_profil.png`, refaite par
  `faire_profil.js`) ; **jamais de paris** sur les réseaux ; une action par jour, le résumé le lundi, publication
  programmée (TikTok Studio), deux créneaux testés 2 semaines (19:00 et 01:00 à Bruxelles).
- **Constat sur les vidéos du 12/10** (action du 9/10 filmée en local) : ouverture sur 2,6 s de carton fixe (pas
  d'accroche), enjeu (score, temps, probabilité) peu visible, texte de l'action sous la légende de TikTok (à partir de
  1 550 px sur 1 920), haut sous les onglets, terrain sur 61 % de la hauteur, résumé de 2 min 15 long pour TikTok.
- 8.1 ✅ plan et photo de profil (PR #67) · 8.2 ✅ action du jour au format TikTok (ouverture sur l'action, enjeu, bascule
  de probabilité au ralenti, zones sûres, terrain resserré à 46 yards, légendes TikTok / Instagram / YouTube sans mot de
  paris) et « Best play so far » (matchs terminés seulement ; README 46 ; PR #68) · 8.3 ✅ qualité : les vidéos étaient
  filmées en 432×768 agrandi et le site baissait la résolution du terrain en cours de tournage ; désormais tournage
  image par image (horloge pilotée), 1080×1920 natif, 60 images/s ; résumé court ≈ 60 s (le long seulement à la demande
  : que des formats courts sur les réseaux, choix du 13/10) ; « What is Snapline? » (PR #69) · 8.4 lien compté `/tt`
  (TikTok seulement) **en attente** : pas de lien cliquable avant 1 000 abonnés · 8.4 bis ✅ adresse visible dans les
  vidéos, carton « Type it in your browser », commentaire à épingler ; pistes sans lien : `Promotion.md` section 8 · 8.5
  Instagram Reels, YouTube Shorts et bilan · 8.6 a ✅ carton de statistiques animé, joueur de la semaine (score
  fantasy) et champion de la Grand Final, produits le dimanche · 8.6 b ✅ match hors norme (record battu ou 100 points
  cumulés, le mercredi) et franchise de la semaine (ordre fixe, le vendredi ; `Promotion.md` section 7). Plus tard, à décider : commentaire et sous-titres
  incrustés, image de couverture.

## 9 — Moteur plus intelligent (14/10/2026)

Idées proposées le 14/10 (dans l'ordre recommandé) : (1) modèle de valeur commun (points attendus, probabilité de
victoire) pour les décisions ; (2) horloge réelle ; (3) bloc F, intelligence du jeu de course ; (4) checks avant le snap
(audibles) ; (5) appel de jeu qui apprend et reste imprévisible ; (6) mémoire d'une semaine à l'autre (scouting depuis les
GameFeeds) ; (7) pénalités, rotations, blessures, décisions d'équipes spéciales. **Guillaume : « commence par 1 et 2 »**,
en voyant ensemble la durée des matchs.

**Fait (PR « Horloge réelle et valeur des décisions »)** : `moteur/horloge.py`, `moteur/valeur.py`, cellule 12.2
quaterdecies, notes du play-by-play — interrupteurs **coupés** (le samedi ne change pas). Mesures : README du serveur,
section 53. Avec des quarts-temps de 15 min et un huddle de 36 s, la retransmission moyenne reste à ≈ 18 min
(18,4 contre 18,1) ; le huddle règle la durée (28 s : 20,9 min · 46 s : 15,8 min) ; l'horloge dans des quarts de 3 min
réduirait tout de 40 % (11,5 min, 31 points).

**Décision de Guillaume (14/10)** : quarts-temps de 15 min, retransmission ≈ 18 min ; 4e essai gardé tel quel, mais
réaliste selon la situation (menée / large avance, quart-temps, temps restant, identité). Fait : grille situationnelle
(menée : la prudence s'efface au fil du dernier quart-temps ; gagné : règle d'avant ; dernières secondes, menée : fin de
période ; correctif du « jouer » systématique de la fin de période pour l'équipe qui mène ; pas de genou au 4e essai) ;
interrupteurs **allumés** ; cotes en direct ré-ajustées (13.1) et 13.4 ✅ ; semaine du 19/10 produite (29,5 min) et
auditée (0 anomalie bloquante). **À surveiller le 17/10** : premier samedi avec l'horloge réelle (temps du calcul,
audit, durée des retransmissions sur le site, commentaire : aucune cue pour genou / spike / temps mort, sous-titres
seulement).

**Idée 3 — bloc F, intelligence du jeu de course** (« passe à l'étape 3 », 14/10) : ✅ codé et allumé
(`moteur/course.py`, cellule 12.2 quindecies, README section 54) — boîte, côté choisi, duels de ligne, trou, lecture
du porteur, plaqueur ; calibration et 13.4 ✅ ; équilibre 39,8 – 59,8 % ; semaine du 19/10 produite (30,4 min) et
auditée. PR séparée, après la fusion de celle de l'horloge. Suite : idée 4.

**Idée 4 — checks avant le snap** (16/10) : ✅ codé et allumé (`moteur/presnap.py`, cellule 12.2 novodecies, README
section 58). **Décisions de Guillaume (16/10)** : allumé par défaut ; fréquence des audibles = identité de la franchise
(`LIBERTE` : de MNL / FRG « on joue notre jeu » à PLS, CTD, APX), 4-8 par match ; check du QB et motion visibles sur le
terrain (« CHECK · RUN / PASS », motion tracée, roll / lock / bump). Mesuré : 6,0 audibles par match (83 % vers la
passe), 0,65 trompés, part des passes + 3,1 points (effet voulu) ; 13.4 ✅ sans recalibrage ; équilibre 39,7 – 59,5 % ;
semaine du 19/10 produite en 32,8 min, auditée (0 anomalie). Exhibition `exh-v40-gmb-mnl`.

**Hors feuille de route, après l'idée 4 (17-19/10)** :
- **4e essai plus prudent** (17/10, README 59) : `valeur-2` (biais d'identité −5 ; +0,5, prudence dans son camp 3
  points) : 35 % -> **≈ 16-17 %** des 4es essais joués (GRZ 2 % à GMB 68 %) ; équilibre 37,2 – 59,8 % ; semaine du 19/10
  régénérée (33,7 min). GameFeeds d'exhibition au moteur complet (jusqu'à la dernière cellule 12.2).
- **Fumbles disputés** (19/10, README 60, cellule 12.2 vicies, `GC_FUMBLE`) : la défense récupère 1 fois sur 2 ;
  fumbles perdus 1,78 -> 0,96 par match ; équilibre **39,4 % (SPK) – 60,9 % (CPH)** ; 13.4 ✅ ; semaine du 26/10 en
  41,9 min.
- **« Bigger field »** (19/10, README 61) : le match en plein écran (téléphone tourné ou paysage), commandes au toucher.
- **Noms des joueurs sur le terrain** (19/10, README 62) : receveurs et porteur avant le snap, porteur pendant l'action,
  auteur de l'action défensive à la fin.

**Idée 5 — l'appel de jeu qui apprend et reste imprévisible** (19-20/10) : ✅ codé et allumé (README du serveur,
section 63) ; plan validé par Guillaume le 19/10, rendus validés sur captures le 19/10.
- Module `moteur/scouting.py`, cellule **12.2 vicies semel** (juste avant 12.3), interrupteur `GC_SCOUTING`, flux
  `scouting-def` / `scouting-att`.
- **Défense** : compte ce que l'attaque montre (course / passe et famille du jeu) par down & distance, formation,
  personnel, zone du terrain et down & distance × formation, avec oubli ; a priori de la ligue ; tendance **nette** =
  assez d'observations, prédiction ≥ 72 % et écart ≥ 15 points à l'a priori ; elle s'y engage selon son profil
  (« KEY ») : petit effet d'anticipation si elle devine juste, punie si elle se trompe (play action contre une défense
  engagée sur la course, boîte allégée contre une défense engagée sur la passe).
- **Attaque** (self-scout) : se sait lue (sa tendance est nette et la défense a montré qu'elle lit) et casse sa
  tendance (« BREAK ») : play action après une série de courses, passe sur un down de course, même formation pour le jeu
  opposé ; plafond par match, jamais en hurry-up / horloge, toujours dans son playbook.
- **Profils** dérivés de 12.2 quater / bloc D / `LIBERTE`, plus `SCOUT` (engagement, bluff) : MNL, FRG, GRZ jouent leur
  jeu ; CTX, MRG, LTC, PRM, CTD, GMB jouent aux échecs ; ONX, BST lisent et attaquent le ballon ; GLT, SPK parient trop.
- Mémoire remise à zéro à chaque match (d'une semaine à l'autre : idée 6).
- Écart au plan : tendance nette à **66 % et 10 points** (au lieu de 72 % / 15 : trop peu de lectures par match).
- **Mesuré** : 6-7 lectures par match (≈ 62 % justes), ≈ 2,3 tendances cassées ; points attendus par action : défense
  juste −0,22, trompée +0,25, cassure +0,10 ; site : « KEY · RUN / PASS », « BREAK », puce « READ / BURNED / BROKE
  TENDENCY », play-by-play et commentateur (sous-titres). Équilibre 12.3 **39,9 – 63,0 %** (BST : lit sans parier,
  engagement 0,60) ; 13.2 / 13.4 ✅ sans recalibrage ; calibration dans les tolérances ; semaine du 26/10 en 32 min,
  auditée (0 anomalie, 0 alerte). Exhibition `exh-v41-ltc-mnl`.
- **À surveiller** : BST (déjà ≥ 60 % coupé) au test d'équilibre ; peu de cassures en play action (0,06 par match : la
  ligue passe beaucoup, les tendances nettes sont surtout des tendances passe). Les deux défauts vus sur les captures
  (nom du porteur d'un jet sweep, « On air » sur la puce du résultat au téléphone) sont corrigés (20/10, README 64).
- **Suite** : idée 6, ci-dessous.

**Idée 6 — la mémoire d'une semaine à l'autre** (20-21/10) : ✅ codé et allumé (README du serveur, section 65) ; plan
validé par Guillaume le 20/10, rendus validés sur captures le 21/10.
- Module `moteur/scouting.py` (fin du module), cellule **12.2 vicies bis** (juste après 12.2 vicies semel), interrupteur
  `GC_MEMOIRE` (coupé ou film vide : idée 5 à l'identique, contrôlé) ; aucun hasard nouveau.
- **Le film** : les appels joués (situation vue avant le snap -> course / passe, famille) de tous les matchs de chaque
  attaque ; fin de semaine : film × 0,5 + la semaine (≈ 2 semaines au plus), `week_<lundi>/scouting_next_week.json`
  (compact, ≈ 0,85 Mo ; `week.json` n'en garde qu'un renvoi) ; repris par 15.1 ; **amorce** depuis les GameFeeds des 4
  dernières semaines quand la semaine précédente n'en a pas (cas du premier samedi). Figé pendant la semaine (cotes).
- **Défense** : commence avec le film de l'adversaire, formation par formation, ses propres matchs × 1,5, plafonné
  (poids du coordinateur 0,6 – 1,4) ; a priori < film < match (le film s'efface : demi-vie 24 snaps) ; confiance du film
  ≤ 0,80. **Attaque** : sait ce qu'elle a montré (match OU film) ; une défense réputée lectrice compte comme « elle lit ».
- **Écarts au plan** (mesures) : situations générales (down & distance, zone, personnel) laissées au match (sinon 4,9
  lectures au lieu de 5,9) ; self-scout « match OU film » (sinon 1,6 cassure au lieu de 2,0) ; poids de ses propres
  matchs sur la formation seulement (taille du film).
- **Mesuré** (2 208 matchs, mêmes graines) : lectures 5,9 -> 7,1 par match (3,0 sur le film), justes 64 -> 76 %, 1er
  quart-temps ≈ 1,6 -> 3,1 ; cassures 2,0 -> 2,2 (0,3 « on tape ») ; points 53,6 -> 53,7 ; victoires 40,0 – 60,9 % ; 8
  semaines enchaînées stables (38,9 – 59,8 % en moyenne). Site : « KEY » + « SCOUTED · 44 GAMES », « BREAK » + « ON
  TAPE », play-by-play « film: … , 44 games incl. 2 of their own », « Scouting report » dans Game plan, commentateur
  (sous-titres). Semaine du 26/10 produite en 28,8 min, auditée (0 anomalie, 0 alerte).
- **Contrôles** (exécution complète, 56,5 min, aucun échec) : 12.3 **41,0 % (NVA) – 61,1 % (FRG)** ; 13.2 ✅ ; **13.4**
  ❌ avec les paramètres d'avant (extrêmes ± 0,042, outsiders − 28,7 % : les avances tiennent mieux) -> `LIVE_*`
  ré-ajustés pour la mémoire (nouvel outil `outils/moteur/fit_live.py`) -> ✅ ± 0,022, écart moyen 0,019, outsiders
  − 8,2 % ; calibration de la ligue dans les tolérances ; 412 tests unitaires ; tests navigateur ✅.
- **À surveiller** : le premier samedi avec la mémoire (amorce depuis les GameFeeds, temps du calcul, audit, taille de
  `scouting_next_week.json`) ; les points par match (51,9 sur la semaine du 26/10 contre 54,0 avec l'idée 5 — de l'ordre
  du bruit, à confirmer sur les vraies semaines) ; la réputation des défenses n'existe qu'à partir des semaines jouées
  avec l'idée 5 (`play.scout`), donc les cassures « on tape » montent après le premier samedi.
- **Suite** : étape 7, ci-dessous.

**Étape 7** (plan revu avec Guillaume le 21/10) : 7.1 la poche et la ligne offensive · 7.2 pénalités pendant l'action
seulement (holding, roughing the passer, interférences, illegal contact ; ≈ 8 par match ; accepter / refuser, effet sur
le jeu, audit, site, GameFeed, retransmission) · 7.3 banc (11 remplaçants par franchise, noms jamais déjà portés dans la
ligue ; les doublons existants restent) et rotations / fatigue · 7.4 blessures (pendant le match, absences d'une ou
plusieurs semaines publiées avant les cotes). Les équipes spéciales ne changent pas.

**7.1 — la poche et la ligne offensive** : ✅ codé et allumé (README du serveur, section 67 ; module `moteur/poche.py`,
cellule 12.2 vicies ter, `GC_POCHE`) ; rendus validés sur vidéos le 21/10 (pas de mise en évidence du duel perdu ; pas
de semaine à produire, les tests suffisent). Duels de protection, duel perdu au temps avant la pression, poche pliée par
les bords / enfoncée / effondrée ; le QB monte, glisse ou sort et lance en courant ; sack crédité au vainqueur du duel ;
site : fer à cheval, rushers qui contournent ou poussent, QB qui bouge, play-by-play, stats (lancers en courant, duels
de protection, pressions), commentateur.
Contrôles en local : notebook complet, rapport de calibration (dans les tolérances), tests unitaires et navigateur ✅.

**7.2 — les pénalités pendant l'action** : ✅ codé et allumé (README du serveur, section 68 ; module
`moteur/penalites.py`, cellule 12.2 vicies quater, `GC_PENALITES`) ; plan, 8 drapeaux par match et choix selon la
probabilité de victoire validés le 21/10, rendus validés. Holding (attaque, défense), illegal contact, interférences
(défense, attaque), roughing the passer ; qui la commet selon son profil ; acceptée, l'action est annulée ; site :
drapeau jaune au moment de la faute, appel de l'arbitre, play-by-play, stats, commentateur ; audit.
Contrôles en local : notebook complet, audit d'une semaine de 279 matchs (0 anomalie), rapport de calibration (dans les tolérances), tests unitaires et navigateur ✅.

**7.3 — le banc, les packages, la fatigue et les rotations** : ✅ codé et allumé (README du serveur, section 69 ; module
`moteur/rotations.py`, cellule 12.2 vicies quinquies, `GC_BANC`) ; plan et choix validés le 21/10, rendus validés sur
captures. 11 remplaçants par franchise (vétéran / jeune / spécialiste, ≈ 7 points sous le titulaire, 264 noms jamais
portés dans la ligue), dans l'état du bloc E ; le personnel de l'appel et le paquet défensif font entrer les joueurs (2e
TE, fullback, WR4, CB3, S3, LB4, 6e OL) ; énergie par joueur, rotations du coordinateur (DT ≈ 67 %, EDGE ≈ 72 %, RB1 ≈ 63 %),
hurry-up de PLS ; garbage time (> 98 % dans les 8 dernières minutes, 17 points d'écart : QB2 compris) ; calibration du
banc (+ 1,2 / + 2,0 aux notes d'unité défensives jouées) ; site : bons joueurs action par action, snaps, fiche, tableau de
profondeur, play-by-play et commentateur pour les changements marquants ; audit. Prépare 7.4 : un remplaçant par place.
Contrôles en local : notebook complet, audit d'une semaine de 279 matchs (0 anomalie), rapport de calibration (dans les
tolérances), tests unitaires et navigateur ✅.

**Hors feuille de route, 21/10 — résultats du jour en cours seulement** (README 66) : le calendrier a un onglet par jour,
aujourd'hui ouvert et les autres fermés ; tableau Live, compteur « Results », bandeau et Big plays ne montrent que les
matchs du jour (le matin : « Today's results appear here · first kickoff 10:00 »). Test `test_jour.js`.

## Pour la conversation suivante
1. Lire ce fichier, puis les sections 35-46 du README du serveur (et 15-22 pour le moteur).
2. **Étape 7 — Publicités** : le code est en place (README section 47) ; rien ne s'affiche tant que
   `GC_ADSENSE_CLIENT` n'est pas posé sur Railway. Reste à Guillaume : compte AdSense, message de consentement, blocage
   des jeux d'argent, 3 blocs d'annonces ; puis poser les variables (`GC_ADSENSE_CLIENT`, `GC_ADSENSE_SLOTS`,
   `GC_EDITEUR`, `GC_EDITEUR_ADRESSE`, `GC_CONTACT`). Revenus réalistes : quelques centimes à quelques euros pour 1 000
   pages vues ; les sponsors directs (une marque par franchise, « présenté par » sur la Grand Final) restent une piste.
3. **Étape 8 — Promotion** : en cours (section « Étape 8 » ci-dessus, `programme/Promotion.md`) ; prochaine étape 8.5 (8.4 en attente des 1 000 abonnés).
4. Ne fusionner qu'une PR aux trois contrôles verts (ils restent facultatifs : voir « Ruleset de `main` », bloc 1).
5. Après chaque samedi : la semaine suivante est dans le dépôt (commit « Nouvelle semaine … ») et aucune issue
   « calcul-semaine » n'est ouverte. **Le 17/10 en particulier** : premier calcul avec transformations et retours.
6. ~~Yards par course~~ (décidé le 06/10) · ~~étape 6~~ (terminée le 08/10) · ~~commentaire des cues du bloc D~~ (généré)
   · ~~bloc 2~~ (terminé le 12/10).


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

## Étape 6, palier 1 — ✅ 8 franchises (06/10/2026, notebook V29)

Bible : `GridironSim_Franchise_Identity_Bible_V1_1.md` (fournie par Guillaume ; 20 franchises conçues, 24 visées en
2 conférences × 2 divisions × 6). **Décisions de Guillaume (06/10)** : par paliers (05-08 d'abord) ; Claude propose noms,
codes et couleurs, Guillaume valide ; moins de matchs par équipe ; retraite + recrue générée. Détail : README du serveur,
section 23, et `moteur/README.md` (« Étape 6 », « Retraites et recrues »).

- **Franchises proposées** (à valider : tout est dans `FRANCHISE_SPECS` et `FRANCHISE_COLORS`, 12.1, et les tables de
  profils ; renommer = changer le nom et les mentions du site) : **AXM Axiom Falcons** (05 Precision, vert), **GLT Glitch
  Hornets** (06 Blitz, violet), **CPH Cipher Lynx** (07 Option, orange), **NVA Nova Raptors** (08 Vertical, magenta) ;
  coordinateurs Lena Strand / Owen Achterberg, Rhys Calloway / Vera Kovac, Mateo Quill / Selene Arkwright, Jasper Holt /
  Ines Marchetti.
- **Mêmes systèmes**, aucune logique propre à une équipe : rosters, coordinateurs, playbooks, adaptation V21 et profils
  des blocs B-D / de l'extension dans les tables existantes. Identités mesurées au 12.3 (contrôles automatiques).
- **Semaine** : aller-retour, 56 matchs en 14 créneaux de 4, playoffs inchangés ; cotes à 150 simulations par affiche,
  en parallèle ; feuille d'appel accélérée (× 1,5, matchs identiques). `GC_FRANCHISES=4` = V28 à l'identique (vérifié).
- **Retraites et recrues** (bloc E) : retraite à 35 ans (QB 38, K / P 40) ou déclin marqué après 32 ans ; recrue de
  22 ans à la même place, base du poste gardée, notes en dessous, grand potentiel.
- **Mesures** : rapport de calibration dans les tolérances (points 53,7 : +1,95 pour ± 2 ; yards / course 5,81 : +0,17
  pour ± 0,2) ; victoires 44,8-59,7 % (1 008 matchs), 43,1-54,4 % (3 024) ; semaine du 12/10 produite en 35,5 min
  (2 processus ; ≈ 50 min estimées sur GitHub, limite 75) : 0 anomalie, 0 alerte ; site vérifié dans Chromium.

**Décisions de Guillaume (06/10, après le palier 1)** :
1. Noms, codes, couleurs (et coordinateurs) des 4 franchises **validés**.
2. **Yards par course** (question ouverte de l'étape 5) : **on laisse comme ça** — les équipes s'adaptent par leur
   coordinateur offensif (ajustement hebdomadaire 12.3, réglages en match V21). Option (a) de la fin de programme.
3. **Budget** : le calcul du samedi doit **toujours rester sous les 75 min** de GitHub, quitte à réduire les
   simulations par affiche. Appliqué : `SEASON_ODDS_BUDGET` (13.1) — le total des simulations de la saison régulière
   reste celui de la ligue de 8 (≈ 8 400) : 150 par affiche à 8 équipes, 64 à 12, plancher 60. À mesurer à chaque palier
   (`generer_semaine.py`, 2 processus) ; si besoin : 12.3 et 13.4 en parallèle, moins de matchs au test d'équilibre.
4. Site (avant le palier 2) : rubrique **My team**, **fiches joueurs** depuis les rosters, **plein écran agrandi** du
   match — README du serveur, section 24.

**Mise en ligne** : la fusion fait passer la semaine du samedi à 8 équipes (la semaine en cours reste à 4).

**À surveiller (palier 1)** :
- **AEG** 59,7 % au test officiel de 12.3 (54,4 % sur 3 024 matchs : échantillon haut) et **MNL / VEC** autour de
  43-48 % : MNL souffre face aux attaques de passe (sa couverture est la plus faible de la ligue).
- **Points** +1,95 et **yards / course** +0,17 : près des bornes (l'option de CPH et les boîtes allégées de NVA font
  monter la course) — à recalibrer si un palier les fait sortir.
- **Temps du samedi** : ≈ 50 min estimées sur GitHub. Palier 2 (12 équipes, 132 affiches) : il faudra réduire encore
  (moins de simulations par affiche, 12.3 et 13.4 en parallèle, ou cotes partielles).
- Pas de cue enregistrée pour les nouveaux noms (le commentaire écrit et la voix de l'appareil les lisent).

**Prochain** : palier 2 (franchises 09-12 : No-Huddle, Ball Hawk, Trench Warfare, Field Position), puis 13-16, 17-20 ;
divisions et conférences quand les 24 seront conçues (bible, section 14).

## Étape 6, palier 2 — ✅ 12 franchises (07/10/2026, notebook V30)

**Décision de Guillaume (07/10)** : passer au palier 2 sans audit ni tests lourds ; les contrôles (équilibre,
calibration, audit, tests) seront exécutés une fois les 24 franchises créées.

- **Franchises proposées** (à valider) : **PLS Pulse Jackals** (09 Tempo, bleu ciel), **ONX Onyx Hawks** (10 Ball Hawk,
  ardoise), **FRG Forge Bison** (11 Trench Warfare, brun), **MRD Meridian Owls** (12 Territory, olive) ; coordinateurs
  Kade Ferris / Mira Solberg, Lucien Abara / Saskia Delmont, Harlan Brody / Tamsin Okeke, Ansel Whitford / Priya
  Lindgren. Mêmes tables que le palier 1 (README du serveur, section 25).
- **Semaine à 12** : aller simple (66 matchs, 11 par équipe, 11 créneaux de 6, lundi-jeudi) ; cotes à 64 simulations
  par affiche (budget de 8 400 inchangé).
- **Contrôles allégés à 12** : 12.3 signale une franchise hors de 40-60 % sans bloquer et n'impose plus l'ordre des
  identités. Une exécution complète du calcul du samedi a servi de seule vérification (durée : voir la PR).

**À faire à 24 franchises** : calibrage des forces (équilibre 40-60 %), contrôles d'identité de 12.3 pour toutes,
rapport de calibration, audit, tests ; divisions et conférences (bible, section 14).

## Étape 6, palier 3 — ✅ 16 franchises (07/10/2026, notebook V31)

- **Franchises proposées** (à valider) : **APX Apex Vipers** (13 Red Zone, rouge), **LTC Lattice Wolves** (14 RPO /
  Spread, indigo), **ZPH Zephyr Condors** (15 Air Raid, jaune), **BST Bastion Panthers** (16 Lockdown, prune) ;
  coordinateurs Dario Vance / Noor Halvorsen, Ilya Brandt / Freya Lund, Bo Kittredge / Celia Moreau, Gideon Pryce /
  Annika Strauss. Détail : README du serveur, section 26.
- **Semaine à 16** : aller simple (120 matchs, 15 par équipe, 15 créneaux de 8, lundi-vendredi) ; cotes à 35
  simulations par affiche (plancher abaissé pour tenir le budget de 8 400 et les 75 min).
- Contrôles allégés comme au palier 2 ; une exécution complète du calcul du samedi comme seule vérification.

## Étape 6, palier 4 — ✅ 20 franchises (07/10/2026, notebook V32)

- **Franchises proposées** (à valider) : **GRZ Granite Grizzlies** (17 Run Defense, gris acier), **MRG Mirage Cobras**
  (18 Play-Action, corail), **GMB Gambit Stallions** (19 Fourth Down, turquoise), **PRM Prism Chameleons** (20
  Positionless, vert lime) ; coordinateurs Silas Brennan / Hanna Kowalczyk, Lionel Duquesne / Ingrid Halloran, Rocco
  Valente / Delphine Ashworth, Matthias Ekwueme / Sabine Rourke. Détail : README du serveur, section 27.
- **Semaine à 20** : aller simple (190 matchs, 19 par équipe, 19 créneaux de 10, lundi-vendredi) ; cotes à 22
  simulations par affiche (budget de 8 400 tenu).

## Étape 6 — ✅ franchises 21-24, ligue de 24 (07/10/2026, notebook V33)

- La bible en décrit 20 : **identités proposées par Claude** (à valider) : **SPK Spark Kestrels** (jeunesse, « Grow »,
  orange), **CTD Citadel Rams** (vétérans, « Endure », bleu pétrole), **TDL Tidal Herons** (zone large / bootleg,
  « Flow », violet), **CMT Comet Stingrays** (équipes spéciales, « Ignite », rose). SPK et CTD utilisent le bloc E
  (`developpement.AGE_EQUIPE`). Détail : README du serveur, section 28.
- **Semaine à 24** : aller simple (276 matchs, 23 par équipe, 23 créneaux de 12) ; cotes à 15 simulations par affiche.

**Prochain** (décision de Guillaume : contrôles à 24) : divisions et conférences (bible, section 14), calibrage des
forces (équilibre 40-60 %), contrôles d'identité de 12.3, rapport de calibration, audit, tests — et le temps du samedi,
proche de la limite (voir la PR).

## Étape 6 — ✅ divisions, calibrage, audit et tests à 24 (08/10/2026, notebook V34)

- **Divisions** (bible, section 14 ; à valider) : Nexus (Circuit : CTX, PRM, BST, FRG, CMT, PLS · Grid : AEG, NVA, GLT,
  TDL, GMB, SPK) et Frontier (Horizon : MNL, ZPH, ONX, MRG, CTD, AXM · Summit : VEC, CPH, LTC, GRZ, MRD, APX). Playoffs :
  champions de division, finales de conférence, AI Bowl. Site : classement par division.
- **Calcul du samedi** : contrôles lourds sautés (`CONTROLES`), 50 simulations par affiche, 32 min en local (≈ 45 sur
  GitHub). Les contrôles tournent en exécution complète.
- **Calibrage** : 43-58 % de victoires sur 4 416 matchs ; points +2,5 (composition de la ligue), yards / course +0,2
  (décision du 06/10). Détail : README du serveur, section 29.

**Validé par Guillaume (08/10)** : noms, codes, identités et couleurs des 24 franchises ; répartition en conférences et
divisions. Ajout : bilan et rang de la ligue sous le code des équipes dans le tableau de score.

**Étape 6 terminée.** Prochain : la suite du programme (à définir avec Guillaume).

## À surveiller (repris de l'étape 4)
- **MNL 55,7 %** au test d'équilibre (dans 40-60 %, au-dessus des autres) : la baisse des fumbles profite surtout à
  l'équipe qui court le plus ; à suivre sur les semaines réelles.
- Cotes en direct recalibrées pour V21 (13.4 : outsiders −0,3 %) ; à re-vérifier si l'adaptation change.
- **Temps du calcul du samedi** (≈ 46 min sur 75 ; la cellule 15.1 seule ≈ 38 min sur 60 permises par cellule) : toute
  hausse des simulations de cotes ou du nombre d'équipes le rapproche du plafond. Mesures et options : bloc 1, étape 2.
- **`data/weeks` grossit d'≈ 64 Mo par semaine** (dépôt, déploiement Railway, tests qui rejouent toutes les semaines :
  le contrôle des PR n'en rejoue qu'une).
- **Semaine du 19/10** (calcul du samedi 17/10) : première avec transformations et retours — temps du calcul, audit,
  points par match ; le replay et les records (History) doivent les montrer.
- **Google Search Console** : le sitemap passe de « Impossible de récupérer » à « Opération effectuée » en quelques jours
  (le 12/10, Railway a bien servi `/sitemap.xml`) ; sinon, regarder.
- **Workflow « Vidéos »** : une exécution par soir (≈ 5 min ; le dimanche ≈ 10 min avec le résumé). Une exécution rouge
  = pas de vidéo ce jour-là, rien d'autre n'est touché.

## Pièges connus
- **Mémoire de la machine** : l'exécution complète du notebook avec ses contrôles monte à ≈ 12,5 Go ; ne rien lancer de
  lourd en même temps (le 21/10, notebook + `rapport_calibration.py` en parallèle : noyau tué pendant 13.2, manque de
  mémoire). Le calcul du samedi saute ces contrôles.
- **Idée 6** : le film d'une semaine est à part (`week_<lundi>/scouting_next_week.json`) ; un changement du moteur qui
  modifie le déroulé des matchs peut demander de refaire `outils/moteur/fit_live.py` (13.4).
- Bloc E : `reset_franchises()` remet les rosters ET l'état de progression à la base (12.3, 14.2 l'appellent) ; les
  notes d'une vraie semaine viennent de `progression_reprendre(prev)` (15.1, exhibition). Les caches d'intelligence
  des blocs B / C (`QB_IQ`, `PLAYER_IQ`) sont vidés à chaque changement de notes (`appliquer_progression`).
- La page du site a un **espace de noms JavaScript unique** : vérifier qu'un nom est libre avant de l'ajouter
  (`AC` = contexte audio ; un second `let AC` avait cassé la page ; `HIST` = historique des paris, d'où `LGH` pour
  l'histoire de la ligue). Même chose pour les **classes CSS** (`.tot` existait déjà : `car-tot` pour la carrière ; les
  vidéos préfixent les leurs en `v…`).
- **Clés VAPID** (`GC_VAPID_*` sur Railway) : ne jamais les changer — tous les abonnements aux rappels seraient perdus.
- **Vidéos** : `outils/video/filmer.js` filme en temps réel (le résumé prend ≈ 2 min 15 de tournage) ; il lui faut le
  crochet de test (`GC_TEST_HOOK=1`, `rpSeek` exposé) et un serveur local sur une copie des données.
- Une IA qui change de plan selon le score **fausse le modèle de cotes en direct** → refaire 13.4 après tout changement.
- La cellule 427 (site embarqué dans le notebook) doit suivre les changements de rendu du site :
  `python3 outils/regen427.py` (essai), `--ecrire`, puis `node outils/site/test_cellule427.js`. Les blocs refusés « à
  reporter à la main » sont à examiner un par un (le 11/10 : écrans de pause, volontairement non reportés).
- Tests serveur (`moteur/tests/test_serveur.py`) : ils tournent sur une copie des données (dossier temporaire) ; ne jamais
  importer `serveur` avec `GC_DATA` sur `data/` du dépôt (la base des paris y serait écrite).
- Parité audio (`test_parite_v01.js`) : serveur **sans** sons enregistrés (`GC_AUDIO_DIR` vide) ; avec les packs foule /
  effets, l'Audio System s'écarte de l'ancien code, comme prévu.
- Le site lit la musique et les sons dans `audio/manifest.json` : `generer_audio.py` et `composer_musique.py` préservent
  les catégories qu'ils ne gèrent pas ; ne pas éditer le manifeste à la main.
- Exhibition : `outils/exhibition/simuler_exhibition.py --home X --away Y` rejoue le notebook (≈ 20 min) sans produire
  de semaine — pratique pour montrer un nouveau bloc avant qu'il n'arrive dans une vraie semaine.
