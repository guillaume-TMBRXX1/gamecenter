# Feuille de route — GridironSim (mise à jour le 04/10/2026, bloc B et safety terminés)

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
| **5** | **ENGINE INTELLIGENCE** — un vrai système décisionnel (programme ci-dessous, blocs A → E) | **en cours** — ✅ bloc A allumé (notebook V22.1, PR #12 + #13) ; ✅ safety + bloc B allumés (notebook V23) ; **prochain : bloc C** | notebook (+ modules Python) + site + serveur |
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

**Reste hors dépôt** : fiche technique du notebook (V22 / V22.1 / V23 : cellules 12.2 quinquies, 12.2 sexies, safety).

## Pour la conversation suivante
1. Lire ce fichier, `gamecenter_serveur (1)/moteur/README.md` et les sections 15-16 du README du serveur.
2. **Bloc C** — intelligence des joueurs (receveurs : route IQ, release, séparation, zone / homme, réception sous
   pression, contested catch ; défenseurs : play recognition, zone / man IQ, awareness, réaction, discipline, pursuit),
   notebook V24 : mêmes garde-fous, rapport `outils/moteur/rapport_calibration.py --reference
   outils/moteur/reference_v21.json`. Même approche que le bloc B pour l'équilibre : attributs hors OVR, poids réglable.

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
