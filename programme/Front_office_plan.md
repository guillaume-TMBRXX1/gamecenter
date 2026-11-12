# Front office — vote des supporters et draft : plan de mise en place

Plan préparé le 09/11/2026, après validation par Guillaume des écrans montrés sur le vrai site (captures iPad du 07/11).
**Une conversation par étape**, comme pour le reste de la feuille de route : en début de conversation, lire ce fichier,
`programme/Feuille_de_route.md` et le `README.md` du serveur.

## Décisions de Guillaume (07-09/11/2026)

- **Gardé** : (1) My team › Front office, le vote de la semaine ; (2) My team › Draft, avec un décompte avant
  l'ouverture puis le choix entre trois prospects ; (4) le lundi, le résultat des votes et la fiche du rookie.
- **Pas pour l'instant** : le Draft board (pronostics de toute la ligue) et **tout système de points**.
- **La draft reste rare** : un événement, seulement quand un joueur part à la retraite, annoncé avec un décompte.
- **Gratuit** : une voix par compte, la même pour tous ; rien de payant ne donne plus de poids (le payant éventuel :
  rapports et badges, plus tard).
- Votent les **comptes dont c'est la franchise favorite** (My team). Pourcentages **cachés jusqu'à la fermeture**.
  Moins de **5 votes** (ou égalité) : le coordinateur décide (« the coordinator kept his plan »).
- ~~Premier levier : le 4e essai~~ → **décision du 09/11 : plusieurs questions dès le départ, qui alternent** d'une
  semaine à l'autre. La même question pour toutes les franchises une semaine donnée, rotation fixe par index de semaine :
  4e essai → course / passe → blitz → couverture → profondeur des passes (le 4e essai la semaine du 16/11). Trois
  réponses : un côté, « Coordinator's call » (aucun changement), l'autre côté. Bornes des leviers 4-5, ligne du 4e essai
  (± 8 yd) et intitulés anglais validés le 09/11 (FO-1, README du serveur section 105).

## Le rythme d'une semaine

| Moment | Vote de la semaine | Draft (quand une retraite est annoncée) |
|---|---|---|
| Lundi 00:00 | la question de la semaine s'ouvre (pour la semaine suivante) ; le résultat du vote précédent est affiché et appliqué | la « dernière saison » du joueur est annoncée, décompte jusqu'à l'ouverture |
| Lun → ven | on regarde, on vote, on peut changer son vote | décompte (onglet Draft « 1 d 16 h ») ; prospects verrouillés, seul leur profil est connu |
| Vendredi 12:00 | — | **la draft s'ouvre** : noms et notes des prospects, vote (rappel Web Push aux supporters abonnés) |
| Vendredi 23:30 | **fermeture** (le verrou du classement, `standings_locked_at`) | fermeture |
| Nuit de vendredi à samedi | le calcul de la semaine suivante applique les choix ; **les cotes sont calculées avec** | le prospect choisi remplace le retraité |
| Lundi suivant | révélation (écran 4), « Fans' plan » sur les matchs | le rookie arrive, « Drafted by the fans · W… » |

## Ce qui existe déjà et sur quoi on s'appuie (vérifié dans le code le 09/11)

- **4e essai** : l'agressivité vient des réglages du coordinateur offensif, `go_max_to_go` et `go_min_yard_line`
  (`moteur/transformation.py`, `agressivite`), utilisée par `moteur/valeur.py` (`quatrieme_essai`, `BIAIS`).
- **Bornes d'identité** : chaque coordinateur a des `bands` (notebook, cellule des staffs : par exemple
  `"go_max_to_go": (1, 3)`, `"pass_shift": (-0.08, 0.08)`) ; l'ajustement hebdomadaire des staffs reste déjà dedans.
  **Le choix des supporters se place dans ces bornes** : c'est ce qui le garde « dans l'identité de l'équipe ».
- **Reprise des staffs** : `staffs_next_week` → `apply_staff_snapshots` (notebook, section serveur) ; les cotes
  d'avant-match sont calculées ensuite par le même moteur.
- **Retraites** : `moteur/developpement.py` — `doit_partir`, `recrue`, `retraites`, appelées par `semaine_suivante`
  (mesuré : 2 retraites dans toute la ligue les semaines du 19/10 et du 26/10, aucune celle du 02/11 — d'où la draft rare).
- **Serveur** : comptes et `fav_team` (`/api/account/team`), clé `GC_ADMIN_KEY`, Web Push (rappels My team),
  verrou du vendredi lu dans `week.json`.
- **Calcul du samedi** : `.github/workflows/semaine.yml` → `generer_semaine.py` (variables d'environnement passées au
  notebook : `GC_WEEK_START`, `GC_PREV_WEEK`, `GC_OUT`, `GC_MOTEUR_DIR`).

## Le chemin des données

```
site (My team) ──vote──> serveur Railway (SQLite : fan_votes)
                              │  vendredi 23:30 : fermeture, résultat figé
                              ▼
GitHub Actions (samedi) ── GET /api/admin/fans (GC_ADMIN_KEY) ──> data/fans/fans_<lundi>.json (versé au dépôt)
                              │
                              ▼
generer_semaine.py ── GC_FANS=<fichier> ──> notebook : choix appliqués dans les bornes, cotes calculées avec
                              │
                              ▼
week.json : fans.applied (ce qui a été appliqué) · fan_vote (question suivante) · draft (annonce, prospects)
GameFeed : game.fans_plan ── serveur ──> site : révélation du lundi, « Fans' plan », rookie
```

Si le serveur ne répond pas le samedi, **le calcul ne s'arrête pas** : les coordinateurs décident, une alerte
(annotation du workflow) le signale, et `fans.applied` l'indique (`source: "coordinators"`).

## Les étapes

Chaque étape : tests unitaires et navigateur, `audit_moteur.py`, une section du README, la feuille de route à jour,
une PR. Interrupteur par étape (coupé = le site et le moteur d'avant, à l'identique).

### FO-1 — Moteur : les leviers des supporters, en rotation *(notebook + module)* — ✅ 09/11 (README section 105)

- `moteur/supporters.py` : catalogue des cinq leviers (id, intitulés anglais, options, réglage, côté), rotation
  (`levier_de_semaine(index)`), placement au bas ou en haut des bornes du coordinateur (bands du notebook pour le 4e
  essai, course / passe et blitz ; tables d'identité pour la couverture et la profondeur), format et validation du
  fichier `GC_FANS`. **Seulement pour la semaine** : restauré avant l'ajustement hebdomadaire (`staffs_next_week`).
- Notebook : cellule 12.2 quinquatricies ; 15.1 lit `GC_FANS` et applique après `apply_staff_snapshots`, avant les
  cotes ; `week.json → fans` et `fan_vote`, `game.fans_plan`. Interrupteur `GC_SUPPORTERS`.
- Mesures (`outils/moteur/banc_supporters.py`, graines du 12.3) : effet de chaque option visible sur une semaine ;
  « coordinateur » partout = matchs identiques ; choix au hasard sans levier gagnant à lui seul ; 13.2 / 13.4 ;
  déterminisme. **Constat** : l'équilibre de 12.3 est déjà hors de 40-60 % avant FO-1 (34,8 % à 70,4 %), à traiter à
  part.
- Tests : `moteur/tests/test_supporters.py` ; `audit_moteur.py` contrôle `fans.applied` (bornes, rotation, rien de reporté).

### FO-2 — Serveur : les votes *(serveur)* — ✅ 10/11 (README section 107)

- Tables `fan_votes(player, week, team, lever, choice, at)` (une ligne par joueur, semaine et levier) ; colonne
  `fav_team_at` dans `players`.
- **Règles** : compte seulement ; vote pour sa franchise favorite seulement ; vote modifiable jusqu'au verrou ;
  changer de franchise pendant la semaine retire le vote de la semaine (le vote compte pour l'équipe tenue depuis le
  lundi) ; limite de requêtes comme pour les ligues.
- API : `GET /api/fans` (question de ma franchise, mon vote, heure de fermeture ; résultat seulement après le verrou),
  `POST /api/fans/vote`, `GET /api/fans/results?team=` (après le verrou, pour toutes les franchises : page Teams),
  `GET /api/admin/fans?key=…&week=…` (export pour le calcul, seulement après le verrou). Interrupteur `GC_FRONT_OFFICE`
  (et non `GC_FANS`, déjà la variable du notebook pour le fichier des choix).
- Tests : `moteur/tests/test_supporters_serveur.py` (règles, verrou, pourcentages cachés, export, changement de
  franchise, minimum de 5 votes, égalité).

### FO-3 — Calcul du samedi : du serveur au moteur *(workflow + generer_semaine)* — ✅ 11/11 (README section 110)

- `semaine.yml` : une étape « Récupérer les votes des supporters » avant le calcul → `data/fans/fans_<lundi>.json`,
  versé au dépôt avec la semaine (archive et rejouabilité). Secrets GitHub à ajouter par Guillaume :
  `GC_ADMIN_KEY` (la même que sur Railway) et `GC_SITE_URL` (`https://snapline.live`).
- `generer_semaine.py` : passe `GC_FANS` au notebook quand le fichier existe.
- `audit_moteur.py` : ce qui est appliqué (`fans.applied`) correspond au fichier, et reste dans les bornes.
- Échec de la récupération : calcul normal avec les coordinateurs, annotation d'alerte (pas d'échec du workflow).

### FO-4 — Site : Front office et révélation du lundi *(site)* — ✅ 11/11 (README section 111)

- My team : sélecteur **Overview / Front office** (Draft viendra en FO-6). Front office = l'écran 1 validé : question,
  trois options, chiffres de la semaine de l'équipe, compte à rebours, « Cast my vote » / « Change vote », comment ça
  marche, le choix en vigueur cette semaine. Refait le 11/11 d'après les captures iPad (projection par option, tuiles
  Faced / Went for it / Converted / League avg, titre avec le nom du coordinateur, « In effect this week »).
- Le lundi : l'écran 4 (sans la partie draft) — résultat et pourcentages, « Your vote », le prochain match avec
  « Fans' plan », la nouvelle question.
- Match centre : la ligne du levier de la semaine (« 4th downs », part des courses, blitz…) avec la puce « Fans' plan » ; page Teams : le choix des supporters de chaque
  franchise, en lecture seule.
- Invités et comptes sans franchise : une invitation à créer un compte / choisir son équipe. Téléphone 390 px.
  Marge en bas pour le bouton « Bet slip ».
- Tests : `outils/site/test_front_office.js` (jeudi, lundi et après le verrou, invité, compte d'une autre franchise,
  téléphone, interrupteur).

**À la fin de FO-4, le vote fonctionne de bout en bout** : première semaine utilisable par le public.

### FO-5 — Moteur : la draft *(notebook + module)* — ✅ 12/11 (README section 113)

- **Annonce** : au calcul de la semaine N, les joueurs qui partiront à la fin de N sont annoncés
  (`week.json → draft`). Au calcul de N+1, **exactement les annoncés partent** (une promesse faite aux supporters ne
  change pas). Conséquence assumée : une retraite arrive une semaine après le moment où elle arrive aujourd'hui.
- **Prospects** : trois par départ, tirés dans leur propre flux (`prospect|<semaine>|<id>|k`), avec la base du poste
  gardée (garde-fou d'équipe) et trois profils : « prêt tout de suite » (notes plus proches de la base, potentiel
  modeste), « gros potentiel » (plus jeune, en dessous, potentiel haut, croissance rapide), « intelligence de jeu »
  (mental haut, physique plus bas).
- Au calcul de N+1 : le prospect choisi par les supporters devient la recrue (`recrue.drafted_by_fans`). Sans choix
  valable : le choix du coordinateur, tiré de façon déterministe.
- Mesures : force des franchises et garde-fou inchangés sur plusieurs semaines enchaînées ; nombre de retraites par
  semaine inchangé en moyenne ; progression des trois profils (le « gros potentiel » doit rattraper en 6 à 8 semaines).
- Tests : `moteur/tests/test_draft.py`.
- **Décisions du 11/11** : titulaires seulement (le banc garde la recrue d'aujourd'hui) ; réglages des trois profils
  validés ; coordinateur selon l'identité (SPK gros potentiel, CTD et QB prêt, sinon 50 / 30 / 20). Annonce : le
  départ a lieu au même moment qu'aujourd'hui (le calcul de N simule toute la semaine N) ; la place est tenue par le
  prospect du coordinateur dans `players_next_week`, échangée la semaine suivante si les supporters en choisissent un
  autre. Fichier `GC_FANS` : bloc `draft` (`{id: {choice, votes, counts}}`), à produire par le serveur en FO-6.

### FO-6 — Serveur et site : la draft *(serveur + site)* — ✅ 12/11 (README section 114)

- Fenêtre lue dans `week.json` (proposition : **vendredi 12:00 → 23:30**) ; votes dans `fan_votes` (levier `draft`).
- Onglet **Draft** dans My team, seulement quand une retraite de la franchise est annoncée : décompte (écran 2),
  puis les trois prospects (écran 3) ; « Remind me when it opens » (Web Push existant).
- Lundi : fiche du rookie dans la révélation, badge « Drafted by the fans · W… » sur la fiche joueur et le roster.
- Tests serveur et navigateur.

- **Décisions du 12/11** : fenêtre vendredi 12:00 → 23:30 (profils seulement avant) ; Football IQ calculé pour tous
  les postes (décision du QB, sinon OVR + 3 × bonus d'expérience) ; plusieurs départs : drafts l'une sous l'autre.

### FO-7 — Plus tard

- Rubrique « Fans' call » dans Week in review.
- Autres leviers : titulaire disputé (la rotation des cinq premiers leviers est faite en FO-1).
- Draft board et points : seulement si Guillaume le décide.

## Points à confirmer au fil des étapes

1. La fenêtre de la draft : vendredi 12:00 → 23:30 (proposé), ou ouverte plus tôt dans la semaine.
2. ~~FO-1 : la même question chaque semaine~~ — tranché le 09/11 : cinq questions en rotation.
3. FO-3 : ajouter les deux secrets GitHub `GC_ADMIN_KEY` et `GC_SITE_URL` — action de Guillaume (sans eux, le calcul
   continue avec les coordinateurs et une alerte).
4. FO-5 : accepter le décalage d'une semaine des retraites (nécessaire pour annoncer la dernière saison).
