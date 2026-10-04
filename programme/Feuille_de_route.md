# Feuille de route — GridironSim (mise à jour le 04/10/2026)

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
| **5** | **ENGINE INTELLIGENCE** — un vrai système décisionnel (programme ci-dessous, blocs A → E) | **à faire — prochaine étape** | notebook (+ modules Python) + site + serveur |
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

## Pour démarrer la conversation du bloc A
1. Lire ce fichier, le README du serveur (sections 9 à 14) et la fiche technique du notebook (+ notes V19, V20, V21).
2. Mesurer l'existant sur V21 (≈ 1 000 matchs) : stats de passe et de course, pertes de balle, points, équilibre, temps
   par match et temps d'une semaine → référence du rapport de calibration.
3. Fixer les tolérances du rapport (proposer, faire valider par Guillaume).
4. Créer le dossier des modules Python (proposition : `gamecenter_serveur (1)/moteur/`) et le branchement dans le notebook
   derrière `DECISIONS_ENABLED`.

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
