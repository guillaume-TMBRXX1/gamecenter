# Next Gen Stats — statistiques de suivi dans Insights (Pro) : plan de mise en place

Plan préparé le 18/11/2026 à la demande de Guillaume (« attaquer le plan du next gen stats, à intégrer dans les
Insights, probablement en pro »). **Une conversation par étape**, comme pour le reste de la feuille de route : en début de
conversation, lire ce fichier, `programme/Feuille_de_route.md` et le `README.md` du serveur (sections 78, 82, 89 pour
Insights et l'empreinte ; 94-104 pour ce que le moteur exporte sur le terrain).

## L'idée

Les statistiques de suivi de la NFL (temps avant le lancer, séparation, CPOE, yards au-delà de l'attendu…) mesurent ce
qui se passe **entre** le snap et le résultat. Snapline a un avantage : le moteur **décide** ces moments (bloc A : la
lecture du QB ; causal léger, blocs 1-4 : course après contact, après réception, couverture, poche) et les **exporte déjà**
dans chaque GameFeed depuis le 05-07/11 (`play.decision`, `play.geo`, `play.pocket`, `play.run`). On n'a rien à simuler
de plus : il suffit de **compter**. Les Next Gen Stats sont donc un module de lecture, côté serveur, comme Insights.

- **Aucun changement du moteur** : ni recalibrage, ni cotes refaites, ni semaine re-produite, ni cellule 427 touchée.
- **Matchs terminés seulement** (même règle qu'Insights et l'empreinte : jamais une action avant l'heure).
- **Textes en anglais**, comme le site.

## Ce qui existe déjà (vérifié dans le code et sur la semaine du 16/11, 279 matchs)

| Source dans le GameFeed | Contenu utile | Présent sur |
|---|---|---|
| `play.decision` | `action` (LANCER / THROWAWAY / SACK / SCRAMBLE), `throw_time`, `time_to_pressure`, `pressure`, `hurried`, `read` / `reads` (1re lecture ?), `misread`, `blitz`, `rushers`, `coverage`, `family`, `reception` (open / traffic / contested), `coverer` (défenseur responsable), `intended` et `target`, `qb` | 22 788 passes décidées |
| `play.geo` (k = pass) | `tt`, `ttp`, `tgt`, `rec` = `[rôle, séparation (yd), statut L/S/C/D, défenseur, bust]` pour **chaque** receveur ; `cov` (trace des duels) | idem |
| `play.call.route` | `name`, `depth` (profondeur de la route → **air yards**), `side` | idem |
| `play.geo` (k = run) | `cls`, `side`, `hole`, `read`, `ch` (non bloqués), `ct` (niveau du 1er contact), `tkl`, `duels` (bloqueur, défenseur, marge), `sim` (porteur et défenseurs après le contact, plaquages tentés `[t, id, 1 réussi / 0 manqué]`) | 11 909 courses |
| `play.run` | `box` (défenseurs dans la boîte), `contact`, `key_block` | idem |
| `play.pocket` | chaque duel de protection : rusher, bloqueur, `margin`, `t` (instant où il cède), `free`, `double` ; `shape` | 80 % des actions de passe |
| `play.players` | porteur, passeur, défenseur crédité (TACKLE…) | toutes |
| `game.home/away.roster` | identifiants, postes, notes : pour relier un nom à sa franchise et son poste | tous les matchs |

**Mesuré sur la semaine du 16/11** (essai jetable, `ngs_probe.py`, 4,6 s pour les 279 matchs ; l'outil n'est pas dans le dépôt) :
- Temps avant le lancer : moyenne 2,19 s (10e centile 1,05, 90e 3,21) ; **par QB de 1,98 à 2,52 s** (26 QB à 150 passes ou plus).
- Complétion selon le statut de la cible : libre court 86 %, serré court 67 %, couvert court 48 %, couvert profond
  sous pression 30 % → un **modèle de complétion attendue** se lit directement dans ces cases.
- aDOT (profondeur moyenne de la cible) 10,2 yd ; séparation moyenne à la cible **par receveur de 2,33 à 3,43 yd**
  (100 receveurs à 60 cibles ou plus).
- Taux de pression subie **par équipe de 25 % (MNL) à 48 % (GRZ)** ; taux de victoire au rush **par rusher de 2 % à 14 %**
  (136 rushers à 300 duels ou plus).
- Courses : 1er contact au 2e rideau 71 %, sur la ligne 16 %, au 3e rideau 13 % ; yards après contact 2,3 en moyenne ;
  0,32 plaquage manqué par course.

Les écarts entre joueurs sont nets : les classements auront du sens.

**Deux réserves à traiter en NGS-1** :
1. La **séparation** `rec` est celle du moteur, convertie en yards et **bornée par le statut** (libre 3-7, serré 1,6-2,9,
   couvert 0,4-1,5, doublé 0,8 ; README section 94). Elle ne correspond pas à la distance finale de la trace `geo.cov`
   (vérifié sur w8-r05 : 2,5 yd contre 2,1 ; 0,8 contre 11,6…). **On s'appuie sur `rec`** (c'est elle qui décide du
   résultat) ; la trace sert au dessin. Écrire la définition en clair dans l'aide.
2. **Air yards** = profondeur de la route appelée, pas le point exact de réception ; YAC = gain − profondeur (2,3 yd en
   moyenne, plutôt bas). À vérifier sur quelques actions avant de l'afficher ; sinon renommer la statistique.

Couverture dans le temps : `play.geo` existe à partir de la semaine du 09/11 (les trajectoires datent du 05/11) ; les
semaines d'avant n'ont que `decision` et `pocket`. Insights portant sur **la semaine en cours**, ce n'est pas gênant.

## Le catalogue proposé

Noms anglais affichés ; une ligne d'aide par statistique (« How it's measured »). Seuils d'affichage dans un classement
entre parenthèses (à confirmer en NGS-1 d'après la distribution de fin de semaine et de milieu de semaine).

**Passeurs (QB)** (≥ 100 passes décidées)
- **Time to throw** — `throw_time` moyen des lancers.
- **aDOT** — profondeur moyenne des cibles ; **Air yards share** de l'équipe.
- **CPOE** — complétion réelle moins complétion attendue (modèle `xComp`, NGS-2).
- **Aggressiveness** — part des lancers vers une cible couverte ou doublée (statut C / D), la « fenêtre serrée ».
- **First-read rate** — part des lancers sur la 1re lecture ; **Misreads** ; **Throwaways**.
- **Under pressure** — part des dropbacks sous pression, complétion et yards par tentative sous pression.
- **Time to pressure** subi (moyenne), **Sack rate**, **Scramble rate**.

**Receveurs (WR, TE, RB)** (≥ 30 cibles)
- **Avg separation** à la cible ; **Open rate** (part des routes où il est libre, ciblé ou non : `rec` le donne pour
  chaque receveur, même non ciblé — une vraie statistique « de suivi »).
- **Catch rate over expected** (avec `xComp`) ; **Contested catch rate** (`reception = contested`).
- **YAC** et **YAC over expected** (modèle `xYAC`, NGS-2) ; **aDOT** du receveur ; **Target share**.

**Porteurs (RB, QB qui court)** (≥ 50 courses)
- **RYOE** — yards au-delà de l'attendu (modèle `xRush` : boîte, classe de course, côté, down et distance — seulement ce
  qui est connu avant le snap) et **RYOE / carry**.
- **Yards before / after contact** (point du 1er contact = 1re position de `geo.sim.c`).
- **Missed tackles forced** (plaquages manqués de `geo.sim.ev`) ; **8+ box rate** ; **Stuff rate** (≤ 0 yard).

**Défense**
- Rushers (≥ 150 duels) : **Pass rush win rate** (duel gagné avant le lancer : `t ≤ throw_time`), **Pressures**,
  **Double-teamed rate**, **Unblocked**.
- Couverture (≥ 20 cibles comme défenseur responsable, `decision.coverer`) : **Targets**, **Completion allowed**,
  **Catch rate allowed over expected**, **Separation allowed**, **Passer rating allowed**.
- Plaqueurs : **Missed tackle rate** (`geo.sim.ev`), plaquages.

**Lignes offensives** (≥ 150 duels de passe) : **Pass block win rate** par joueur (marge des duels de `pocket`) et par
équipe ; **Run block win rate** (duels de `geo.duels`).

**Équipes** : blitz (part, et yards par passe concédés avec / sans blitz), temps avant le lancer, pression subie /
infligée, RYOE de l'attaque, séparation moyenne concédée.

## Gratuit ou Pro (proposition, à décider par Guillaume)

Le cadenas existe déjà : `insights_pro(p)` dans `serveur.py` (pseudos de `GC_INSIGHTS_USERS`, jamais un invité ; bouton
« Unlock · €4.99 » inactif, « Coming soon »). Même règle que l'empreinte : **le teaser est vrai, le détail est Pro**.

- **Gratuit** : un « Next Gen stat of the day » dans Day recap (une seule statistique, vraie, ex. « Fastest release:
  Theo Marchand, 1.98 s ») et, sur la fiche d'un joueur, **une** statistique de suivi phare de son poste.
- **Pro** : tous les classements, les statistiques expliquées, les comparaisons à la moyenne de la ligue, la fiche
  complète du joueur et de l'équipe. Sans compte Pro : aperçu flouté dessiné avec des **chiffres factices** — l'API
  n'envoie rien d'autre que le teaser (comme `/api/insights`).

## Le nom (point à décider)

« **Next Gen Stats** » est une marque de la NFL : ne pas l'afficher sur le site. Noms neutres proposés pour l'onglet :
**« Tracking »** (recommandé : court, dit ce que c'est), « Field data », « Deep stats ». « Next Gen Stats » reste le nom
interne du chantier (fichiers `ngs`).

## Le chemin des données

```
data/weeks/<semaine>/games/*.json  (GameFeeds, déjà produits le samedi)
        │  matchs terminés à l'heure du serveur
        ▼
moteur/ngs.py ── compter(match, feed) ──> comptes d'un match (en cache, calculés une fois)
        │        agreger(comptes, modeles) ──> joueurs / équipes / ligue
        │        modèles xComp, xYAC, xRush : moteur/ngs_modeles.json (tables, versées au dépôt)
        ▼
serveur.py ── /api/tracking?view=leaders|player|team ── insights_pro ? tout : teaser
        ▼
site : Insights › Tracking (classements) · fiche joueur · fiche équipe · Day recap (stat du jour)
```

## Les étapes

### NGS-0 — Plan *(ce fichier)* — ✅ 18/11
Catalogue, sources vérifiées, mesures de faisabilité, découpage. Points à décider ci-dessous.

### NGS-1 — Module de comptage *(module seul, sans serveur ni site)*
- `moteur/ngs.py` : `compter(match, feed)` → comptes bruts par joueur (identifiant, poste, franchise) et par équipe pour
  un match ; `agreger(liste de comptes, modeles=None)` → statistiques finales, seuils d'échantillon, moyenne de ligue,
  rang. Statistiques sans modèle d'abord (temps de lancer, aDOT, séparation, open rate, pression, win rates, yards
  après contact, plaquages manqués…).
- Exclusions explicites : genou, spike, pénalités sans action, 2 points, actions sans `decision` / `geo` (comptées à part).
- Lever les deux réserves (séparation, air yards) sur des actions relues à la main.
- **Tests** `moteur/tests/test_ngs.py` : un petit GameFeed fabriqué (chaque statistique vérifiée à la main),
  déterminisme, un match sans `geo` (semaine ancienne) ne plante pas.
- Outil `outils/moteur/ngs_rapport.py` : distributions et classements d'une semaine entière (pour fixer les seuils).

### NGS-2 — Modèles « attendus » *(module + outil)*
- `xComp` : complétion attendue par case (statut de la cible × profondeur × pression × temps de lancer), lissée vers la
  case parente quand elle a peu d'actions. `xYAC` : YAC attendu (statut, profondeur, réception). `xRush` : yards attendus
  d'une course d'après ce qui est connu **avant le snap** (boîte, classe, côté, down, distance, position).
- Tables apprises sur les **semaines précédentes** (pas sur la semaine en cours : stables, et pas de fuite), écrites dans
  `moteur/ngs_modeles.json` par `outils/moteur/ngs_modeles.py --semaines …`. Au départ, à la main ; plus tard,
  rafraîchies par le calcul du samedi si utile.
- **Contrôle** : sur une semaine entière, somme attendue ≈ somme réelle (CPOE de la ligue ≈ 0, RYOE ≈ 0) ; écarts par
  joueur et stabilité d'une moitié de semaine à l'autre (si un CPOE ne se répète pas, ne pas l'afficher en tête).

### NGS-3 — Serveur *(serveur)*
- `/api/tracking?view=leaders&group=qb|wr|rb|def|ol|team`, `view=player&id=`, `view=team&team=` ; matchs terminés
  seulement, comptes d'un match en cache, agrégat en cache par nombre de matchs finis (comme `insights_data`).
- Accès : `insights_pro` → tout ; sinon le teaser seulement (statistique du jour, la stat phare d'un joueur) ; invité :
  idem. Interrupteur `GC_TRACKING=off` (ni API ni onglet : le site d'avant).
- Tests `moteur/tests/test_tracking_serveur.py` (sur une copie des données, jamais `data/` du dépôt) : matchs finis
  seulement, rien de Pro dans la réponse d'un compte hors liste, interrupteur, temps de réponse.

### NGS-4 — Site : Insights › Tracking *(site)*
- Nouveau sous-onglet dans Insights : groupes (Passing, Receiving, Rushing, Pass rush, Coverage, Blocking, Teams),
  classements triables, une ligne d'aide par statistique, moyenne de la ligue, seuil d'échantillon affiché.
- Aperçu flouté verrouillé (chiffres factices) pour les comptes non Pro, bouton « Unlock » existant.
- Statistique du jour dans Day recap (gratuit).
- Tests navigateur `outils/site/test_tracking.js` : invité, compte hors liste, compte Pro, téléphone 390 px, iPad,
  mode sombre, interrupteur. Charger la skill `dataviz` avant le premier graphique.

### NGS-5 — Fiches et match *(site + serveur)*
- Fiche joueur : bloc « Tracking » (la stat phare en clair, le reste Pro, rang dans la ligue).
- Fiche équipe (Teams, My team) et Head-to-head : profil de suivi des deux équipes côte à côte (Pro).
- Match terminé : « Tracking » dans le récap du match (temps de lancer, pression, séparation de chaque équipe).

### NGS-6 — Plus tard (si l'audience suit)
- Graphiques : carte des passes (profondeur × côté), carte des courses (trou × yards) d'un joueur.
- Historique d'une semaine à l'autre (une semaine = une saison) : carrière de suivi d'un joueur.
- Promotion : carton « Tracking stat of the week » pour les vidéos (étape 8), sans mot de paris.
- Récompenses de la semaine (« Fastest release », « Most separation »…).

## Points à décider (Guillaume)

1. **Gratuit / Pro** : d'accord avec « stat du jour + une stat par fiche joueur gratuites, tout le reste Pro » ?
2. **Nom affiché** : « Tracking » (recommandé), « Field data », « Deep stats », autre ?
3. **Catalogue** : tout d'un coup en NGS-4, ou d'abord Passing / Receiving / Rushing, puis défense et lignes ?
4. **Modèles attendus** (CPOE, RYOE, YAC over expected) : les veut-on dès la 1re mise en ligne, ou après (NGS-2 peut
   passer après NGS-4) ?
5. **Fenêtre** : la semaine en cours seulement (comme Insights), ou aussi « depuis la semaine X » (comme History) ?

## Garde-fous (définition de fini de chaque étape)

- Matchs terminés seulement ; aucun chiffre Pro dans une réponse non Pro.
- Moteur, notebook, calcul du samedi et cellule 427 inchangés (vérifié : `git diff` sans ces fichiers).
- Tests locaux avant de pousser : `python -m unittest discover -s moteur/tests -t .`, `python audit_moteur.py data/weeks`,
  `bash outils/site/tests_navigateur.sh --semaines 1` ; PR aux trois contrôles verts.
- Section du README du serveur pour chaque étape mise en ligne ; ligne « NGS » de la feuille de route mise à jour.
