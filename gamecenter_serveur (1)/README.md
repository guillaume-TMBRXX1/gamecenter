# GameCenter — serveur de direct

> **Feuille de route du projet** : `programme/Feuille_de_route.md` à la racine du dépôt (mise à jour le 04/10/2026 —
> étape en cours : ENGINE INTELLIGENCE, blocs A → E ; blocs A, B et C allumés dans le notebook V24, prochain : bloc D).

La page servie est `gamecenter_source.html` au **design officiel « Glass éditorial »** (clair par défaut, sombre
selon l'appareil ou au choix). Le serveur garde les semaines produites par le moteur et n'envoie au public
**que ce qui s'est déjà passé** : les résultats, les scores et les affiches des playoffs ne peuvent pas fuiter.

---

## Mettre le site en ligne — version gratuite (GitHub calcule, Railway affiche)

Le calcul d'une semaine demande ≈ 3 Go de mémoire pendant ~16 min : trop pour une offre gratuite.
On le confie donc à **GitHub Actions** (gratuit : 2 000 min/mois pour un dépôt privé, il en faut ~70),
et **Railway** ne fait que servir le site (≈ 110 Mo de mémoire) : l'essai Railway (5 $ offerts, 30 jours) suffit.
Après l'essai : forfait Hobby à 5 $/mois, sans rien changer d'autre.

### 1. Préparer le dossier

Rien à faire si tu as `gamecenter_serveur.zip` : dézippe-le, c'est le dossier à envoyer.
(Pour le refaire soi-même : `pip install -r requirements.txt -r requirements-semaine.txt` puis `python3 assembler.py`.)

### 2. Dépôt GitHub privé

1. github.com → **New repository** → nom `gamecenter` → **Private** (obligatoire : les fichiers contiennent les
   résultats des matchs à venir) → *Create repository*.
2. Sur la page du dépôt vide : **uploading an existing file** → glisse **tout le contenu** du dossier dézippé,
   **y compris le dossier caché `.github`** → *Commit changes*.
   - Mac : dans le Finder, `Cmd + Maj + .` affiche les fichiers cachés ; puis `Cmd + A` et glisser.
   - Windows : le dossier `.github` est visible normalement.
3. Contrôle : onglet **Actions** du dépôt → le calcul « Semaine suivante » doit apparaître.
   S'il n'y est pas : *Add file → Create new file*, nom `.github/workflows/semaine.yml`, coller le contenu
   donné en annexe ci-dessous, *Commit*.

### 3. Railway

1. railway.com → *Login* avec GitHub → l'essai démarre (une carte peut être demandée ; rien n'est prélevé pendant l'essai).
2. **New Project → Deploy from GitHub repo** → `gamecenter` (autoriser Railway à lire ce dépôt). Il trouve le `Dockerfile`.
3. **Disque** : clic droit sur le service → **Attach volume** → chemin **`/data`**.
4. **Variables** : `GC_ADMIN_KEY` = une longue phrase secrète (20 caractères ou plus) ; `TZ` = `Europe/Brussels`.
5. **Adresse** : *Settings → Networking → Generate Domain*.

### 4. Vérifier

| Ouvrir | Attendu |
|---|---|
| `https://<adresse>/api/health` | `"ok": true`, `"weeks": ["2026-10-05"]` |
| `https://<adresse>/` | le Game Center (design Glass) |
| un pari d'avant-match, puis *My bets* | le pari, solde 990 $ ; *Leaderboard* te montre |
| le site sur le téléphone en 4G | même chose |
| GitHub → *Actions* → *Semaine suivante* → **Run workflow** | ✅ vert en ~1 min, « Rien à faire » (la semaine suivante n'est produite qu'à partir du samedi) |

### 5. Les semaines suivantes (automatique)

Chaque **samedi vers 3 h** (Bruxelles), GitHub exécute le notebook et produit la semaine suivante (≈ 45 min),
en reprenant les staffs ajustés de la semaine jouée. Il l'ajoute au dépôt ; Railway voit la mise à jour et
redémarre le site (≈ 1 min, en pleine nuit, aucun match en cours). Le dimanche à la même heure, un second
passage rattrape un échec éventuel (sinon il ne fait rien). Le lundi 00 h, le site passe à la nouvelle semaine.
En cas d'échec, une issue « calcul-semaine » est ouverte dans le dépôt (section 37).

Contrôle du samedi matin : `/api/health` liste deux semaines ; le dépôt a un commit « Nouvelle semaine … ».

**Changer de moteur** : remplacer `NFL_Sim_GameCenter.ipynb` dans le dépôt (*Add file → Upload files*, même nom).
Les semaines suivantes utiliseront le nouveau notebook. Nouveau design : remplacer `gamecenter_source.html`.

### 6. À surveiller

- **Coûts** : Railway → *Usage* (l'essai affiche ce qu'il reste). Avant la fin des 30 jours : passer en Hobby
  (5 $/mois), sinon le site s'arrête (les données du disque sont conservées un temps). GitHub : *Settings → Billing*
  → minutes Actions utilisées (~70 sur 2 000).
- **Sauvegardes** : les semaines sont déjà archivées dans GitHub. Pour les paris, une fois par semaine :
  `https://<adresse>/api/backup?key=<GC_ADMIN_KEY>` → un .zip à garder.
- **Sécurité** : dépôt privé ; ne jamais publier `GC_ADMIN_KEY` ; pas de vrais comptes ; pas de limite de requêtes
  (à ajouter avant une grosse audience) ; argent fictif uniquement (de l'argent réel demanderait une licence de la
  Commission des jeux de hasard).

### 7. Comptes joueurs (depuis le 03/10/2026)

- **Facultatifs** : on parie en invité comme avant (clé gardée dans le navigateur). *Settings → Account* :
  **Create account** (pseudo 3-24 caractères + mot de passe de 8 caractères ou plus) pose le compte sur la clé
  du navigateur — les paris déjà faits suivent. **Sign in** sur un autre appareil redonne le même portefeuille
  (les paris faits en invité sur cet appareil passent sur le compte pour chaque semaine où le compte n'a encore rien joué).
- Mots de passe hachés (scrypt) ; 8 erreurs sur un pseudo (ou 30 depuis une même adresse) en 15 min → pause de 15 min.
  Changer de mot de passe déconnecte les autres appareils.
- **Mot de passe oublié** (pas d'e-mail) : toi seul peux le réinitialiser, avec `GC_ADMIN_KEY` :
  ```
  curl -X POST https://gridironsim.up.railway.app/api/admin/password \
       -H 'Content-Type: application/json' \
       -d '{"key":"<GC_ADMIN_KEY>","pseudo":"Pseudo du joueur","password":"nouveau-mot-de-passe"}'
  ```
- **Classement de la saison** (*My bets → Leaderboard → Season*) : comptes seulement, somme des gains nets de chaque
  semaine (retour − mise des paris réglés ; un pari compte quand il est réglé). Toutes les semaines du serveur comptent ;
  pour repartir d'une date : variable Railway `GC_SEASON_START=2026-10-05` (par exemple).

### 8. Paris plus riches (depuis le 03/10/2026)

- **Combinés** : 2 à 6 sélections, une par match, pas de futures, une seule mise (bulletin → *Combo*). Perdu dès qu'une
  sélection perd ; gagné au produit des cotes des sélections gagnées (une sélection remboursée compte 1).
- **Cash-out** (*Open bets* ou *My bets*, deux clics) : valeur juste − 5 % = mise × Π (cote prise ÷ cote du moment) × 0,95
  (sélection déjà gagnée : sa cote). Indisponible si la ligne d'un spread / total a bougé, ou sur un future pendant les matchs.
  Le serveur recalcule ; si la valeur a bougé, il renvoie la nouvelle et la page redemande confirmation. `POST /api/cashout`.
- **Historique** : *My bets* → onglets de semaine (semaines où le joueur a parié). `GET /api/history?token=…[&week=…]`.

### 9. Playbooks des franchises et recherche (depuis le 03/10/2026)

- **Notebook V19** (`NFL_Sim_GameCenter.ipynb`) : cellule 12.2 bis — 45 plays, 8 formations (TRIPS, ACE, JUMBO en plus),
  un playbook par franchise, feuille d'appel selon la situation, anti-répétition, COVER_3 et formations défensives selon la distance.
  Les semaines produites à partir du 12/10 l'utilisent ; celles du 28/09 et du 05/10 restent telles quelles.
- **Notebook V20** : cellule 12.2 ter — playbook « Roman 2014 » (49ers) : 92 plays, 11 formations (BUNCH, HEAVY, PONY en plus),
  Stick, Curl/Chuck, Champ, Dagger, Sail, Mesh, Boot/Naked, Pop, Trap, Read option, Z-Sweep, répartis selon l'identité de chaque franchise.
  La **semaine du 05/10 a été re-produite avec V20** le 03/10 (numéro 2, staffs repris du 28/09 ; aucun pari n'existait sur elle).
- **Recherche** (barre du haut, touche `/`) : équipes, joueurs, coordinateurs, matchs, pages ; ↑ ↓ Entrée, Échap.

### 10. Coordinateurs adaptatifs en direct (notebook V21, depuis le 03/10/2026)

- **Notebook V21** (`NFL_Sim_GameCenter.ipynb`) : cellule 12.2 quater — les coordinateurs s'ajustent pendant le match
  (concept ou formation mis de côté après des échecs répétés, retour à ce qui marche, hurry-up quand on est mené tard,
  course pour tuer l'horloge quand on mène, défense qui change de couverture / blitz face à ce qui fait mal), chacun
  selon son identité (CTX très adaptatif, AEG prudent et lent, VEC agressif qui force, MNL têtu sur la course mais
  hurry-up s'il est mené tard). Pertes de balle ≈ 3,6 par match (5,4 avant), Q2 / Q4 commencent à 180 s.
  Cotes en direct recalibrées (13.1 / 13.4). Utilisé à partir de la semaine du 12/10 (calcul du samedi 10/10).
- **Site** : chaque ajustement est une ligne en italique du play-by-play (« Goes hurry-up », « Shelves the Dagger »,
  « Defense rolls to deep shells »…) et le commentateur le dit au snap (`play.adjust` du GameFeed). Les semaines
  produites avant V21 n'en ont pas : rien ne change pour elles.

### 11. Audio System (V0.1, depuis le 03/10/2026)

- **Architecture** : moteur (GameFeed) → page (rejoue, écrit les phrases) → `AudioEventMapper` (événements + contexte,
  point de vue HOME = le stade) → `AudioManager` → `AudioMixer` (MASTER · COMMENTARY · CROWD · SFX · MUSIC) → Web Audio.
  Modules dans `static/audio/`, assemblés et versionnés par le serveur (`/static/audio/gc-audio.js?v=…`, cache 1 an).
- **V0.1 = même son qu'avant** : sons procéduraux et voix du navigateur déplacés tels quels (parité vérifiée sur les
  10 476 actions des semaines : 46 461 décisions identiques). Nouveau : *Settings → Sound → Mixer* (niveau par catégorie,
  muet pour la voix et la musique), enregistré dans le navigateur.
- **Retour arrière immédiat** : ajouter `?audio=legacy` à l'adresse (ou si `gc-audio.js` ne se charge pas) → l'ancien code.
- **Fichiers sons** : `audio/manifest.json` + `audio/{commentary,crowd,sfx,music}/` (vides en V0.1). Ils seront pré-générés
  hors ligne (ElevenLabs) : **aucun appel ElevenLabs pendant un match, aucune clé sur Railway ni dans le navigateur**
  (clé seulement dans un `.env` local, ignoré par Git, ou un secret GitHub).
- **Tests** : `node outils/audio/test_mapper_v01.js` (sans navigateur) ;
  `GC_TEST_HOOK=1 GC_AUDIO_DIR=<dossier vide> uvicorn serveur:app --port 8103` puis
  `node outils/audio/test_parite_v01.js data/weeks 8103` (Playwright). Sans sons enregistrés : avec les packs foule /
  effets (V0.3), l'Audio System s'écarte de l'ancien code, comme prévu. Tous les tests navigateur : section 38.

### 12. Commentaire enregistré (Audio System V0.2)

- **Principe** : le commentateur dit des appels génériques enregistrés (163 phrases en anglais, sans nom de joueur :
  `outils/audio/catalogue/commentary.json`) ; les sous-titres gardent la phrase complète (noms, yards, score).
  Ton choisi selon l'importance du moment (calme / excité / énorme : un TD ordinaire n'est pas un TD décisif à 0:30),
  variante choisie de façon contrôlée (même prise pour tous les spectateurs, jamais deux fois de suite).
  Prise absente ou trop lente (> 350 ms) → la voix de l'appareil dit la phrase complète. *Settings → Sound → Commentator voice*
  permet de garder la voix de l'appareil. iOS : le son passe même en mode silencieux quand Safari le permet.
- **Tant qu'aucune prise n'est générée, rien ne change** (le site garde la voix de l'appareil).
- **Générer les prises — tout depuis le navigateur, rien à installer** (GitHub calcule, comme pour les semaines) :
  1. Une seule fois, GitHub → dépôt → *Settings → Secrets and variables → Actions* :
     - onglet *Secrets* → *New repository secret* : nom `ELEVENLABS_API_KEY`, valeur = la clé ElevenLabs
       (chiffrée par GitHub, jamais affichée ni commitée, jamais sur Railway) ;
     - onglet *Variables* → *New repository variable* : nom `ELEVENLABS_VOICE_ID`, valeur = l'ID de la voix.
  2. *Actions → Commentaire audio → Run workflow* (mode `essai` d'abord si tu veux voir ce qui sera généré, ≈ 4 600 caractères).
     Mode `generer` : ≈ 3-5 min, les prises sont ajoutées au dépôt, Railway met le site à jour tout seul.
  3. Écouter sur `https://<site>/audio/ecoute` (téléphone ou ordinateur). Cocher les prises ratées, copier la liste,
     relancer le workflow avec le champ *Prises à refaire* : seules celles-là sont refaites.
  4. Changer de voix ou de réglages (`outils/audio/catalogue/voix.json`) → le prochain passage refait les prises concernées.
- **Tests** : `node outils/audio/test_commentaire_v02.js data/weeks 8104` avec des bips de test
  (`generer_audio.py --placeholder --audio-dir /tmp/gc-audio` et `GC_AUDIO_DIR=/tmp/gc-audio` pour le serveur).

### 13. Foule et effets enregistrés (Audio System V0.3)

- **Foule** (`outils/audio/catalogue/stade.json`, ElevenLabs Sound Effects) : fond de stade en boucle (enchaîné en fondu,
  sans couture audible), fond d'anticipation sur 3e / 4e down, zone rouge à domicile et fin de match serrée ; réactions
  (petite / moyenne / énorme acclamation, huées, déception, TD, interception, victoire). **Point de vue HOME** : un TD
  à domicile fait exploser le stade, un TD des visiteurs est hué ; taille selon l'importance du moment (un premier
  down = applaudissements polis, une course ordinaire = rien). 2 réactions au plus à la fois.
- **Effets** : snap, plaquage, impact, réception, ballon au sol, sifflet (long en fin de quart-temps), coup de pied,
  field goal, ballon perdu, changement de possession, corne de stade. Variation légère de hauteur et de niveau,
  6 effets au plus à la fois, réglages de niveau dans le catalogue (`gain`). Ambiance broadcast, pas d'arcade.
- **Secours** : tout son enregistré absent ou pas encore décodé → le son synthétisé d'avant. Sans pack « stade », rien ne change.
- **Générer** : GitHub → *Actions → Commentaire audio → Run workflow*, catégorie `stade` (42 sons, ≈ 2 min de son au
  total ; mode `essai` d'abord). Les prises de commentaire existantes ne sont pas refaites. Écoute : `/audio/ecoute`.
- **Tests** : `node outils/audio/test_stade_v03.js data/weeks 8106` (sons de test : `generer_audio.py --placeholder --cat stade`).

### 14. Musique et réglage de la foule (Audio System V0.4)

- **Musique originale, libre de droits** : 8 pièces composées par `outils/audio/composer_musique.py` (synthèse pure, aucun
  échantillon ni morceau existant → domaine public, CC0), ré mineur, 120 BPM, habillage sportif TV :
  boucles *pregame, gameplay, close_game, red_zone, final_drive, overtime* (16 s, bouclage parfait) et jingles *victory, defeat*.
  1,6 Mo au total, déjà dans `audio/music/`. Pour remplacer une pièce par un autre morceau libre de droits : même `state` dans le manifeste.
- **États** (décidés à chaque action du match à l'antenne) : avant le match et à la mi-temps → pregame ; prolongation → overtime ;
  fin de Q4 serrée → final_drive si l'attaque est menée, close_game sinon ; zone rouge → red_zone ; serré en 2e mi-temps →
  close_game ; sinon gameplay ; coup de sifflet final → jingle victory / defeat (point de vue HOME), puis silence.
  Fondus à puissance constante de 3 s ; la tension monte tout de suite mais ne redescend qu'après 20 s (pas de va-et-vient) ;
  jamais plus de 2 pièces à la fois. Musique sous la voix et la foule, baissée quand le commentateur parle ;
  coupée sur les connexions « économie de données ». *Settings → Sound → Mixer → Music* (niveau, muet).
  Niveau mesuré en replay (04/10) : musique ≈ −25 dB, au-dessus du fond de foule (−28), sous la voix ; pièces « m3 » enrichies
  en médiums pour rester audibles sur un haut-parleur de tablette ou de téléphone.
- **Foule plus présente** (mesures : fonds −28 LUFS, réactions −23 LUFS, voix ≈ −17 LUFS) : les réactions ne sont plus
  baissées sous la voix (comme à la télé, la clameur monte sous l'appel), +6 à 7 dB sur fonds et réactions, baisse sous la
  voix allégée ; limiteur de sécurité sur la sortie (jamais de saturation). Aucun son régénéré.
- **Tests** : `node outils/audio/test_musique_v04.js 8108`.

### 15. ENGINE INTELLIGENCE — bloc A (notebook V22.1, 04/10/2026, allumé)

- **Modules Python du dépôt** : `moteur/` (voir `moteur/README.md`) — progression du playbook (primaire, secondaire,
  tertiaire, checkdown), `DefensiveReactionEngine` (état post-snap : couverture homme / zone Cover 0-4, rushers,
  receveur libre / serré / couvert / double, temps avant la pression), `QBDecisionEngine` (lecture dans l'ordre ->
  cible réelle, throwaway, scramble ou sack), résolution **ajustée** (les probabilités du tirage historique sont
  modulées par la décision, puis normalisées pour garder les moyennes de V21). Flux aléatoire dédié par action.
- **Notebook V22.1** : cellule 12.2 quinquies, interrupteur `DECISIONS_ENABLED` **allumé par défaut** ; `GC_DECISIONS=0`
  le coupe (moteur de V21). `generer_semaine.py` indique au notebook où est `moteur/` (`GC_MOTEUR_DIR`) : s'il manque,
  le calcul s'arrête (jamais de semaine V21 en silence). Colab sans le dossier : décisions coupées, avec un message ;
  cloner le dépôt avant d'exécuter (en-tête de 12.2 quinquies).
- **Corrections de V22.1** : 13.2 contrôle les cotes réellement publiées (300 simulations) avec une tolérance de biais
  statistique (2,5 écarts-types, au moins 3 %) ; le porteur n'est plus jamais arrêté derrière son en-but (le moteur
  n'avait pas de safety : arrêt sur la ligne des 1 — règle du safety ajoutée en V23, section 16) ; le cache des cotes distingue décisions allumées / coupées.
- **Rapport de calibration** (1 008 matchs, mêmes graines que 12.3) : `python3 outils/moteur/rapport_calibration.py`
  (`--decisions off --sortie ref.json`, puis `--decisions on --reference ref.json` -> verdict, code 1 hors tolérance) ;
  `outils/moteur/calibrer_bloc_a.py` recalcule les facteurs de normalisation.
- **GameFeed** (additif) : `play.decision` = `{action, intended, target, read, reads, status, pressure, forced,
  throw_time, time_to_pressure, coverage, family, rushers, blitz}` ; `call.route` = route de la **cible réelle** ;
  texte « Pass thrown away », « X scramble, +7 ». **Site** : la route animée suit le receveur choisi ; « · off his
  first read » dans le play-by-play quand le QB a lancé au-delà de sa première lecture. Rien ne change pour les
  semaines produites avant (sans `play.decision`).
- **Exhibition** : `outils/exhibition/simuler_exhibition.py` joue avec les décisions (`--sans-decisions` : moteur V21).
  Depuis V25 : CTX @ VEC (`exh-v25-ctx-vec`, remplace MNL @ VEC V24), choisi parmi 40 candidats pour ses plans de
  jeu et ses ajustements du bloc D (quick game et protection contre le blitz, bascule hors du double, brackets et leurs
  rotations), avec les duels receveur / défenseur et les décisions du QB ; `--remplace <id>` retire l'ancienne exhibition.
- **Tests** : `python3 -m unittest discover -s moteur/tests -t .` (quelques secondes) — lancés par GitHub avant chaque
  calcul du samedi et par le workflow « Contrôle des PR » sur chaque PR (section 38).

### 16. Safety et ENGINE INTELLIGENCE — bloc B (notebook V23, 04/10/2026, allumés)

- **Safety** (règle NFL) : porteur, receveur ou QB sacké arrêté dans son propre en-but -> **2 points pour la défense**,
  puis free kick de l'équipe qui a concédé depuis sa ligne des 20 (distance tirée dans un flux dédié : le hasard du
  moteur n'est pas consommé) ; en prolongation, un safety termine le match. Fumble perdu dans son en-but : ballon sur
  la ligne des 1 (comme V22.1). ≈ 9-11 % des matchs en ont un (NFL ≈ 7 %). Interrupteur `SAFETY_ENABLED` (11.6).
  GameFeed : `result: "safety"`, `possession_change: "safety"`, `safety_via` (`run` / `complete` / `sack` : ce que le
  site anime), `highlight: "SAFETY"` ; le coup de pied suivant est un `kickoff` au texte « Free kick, N yds ».
  `audit_moteur.py` vérifie que le safety donne exactement 2 points à la défense.
- **Bloc B — intelligence du QB, poche et pression** (cellule 12.2 sexies, modules `moteur/intelligence_qb.py` et
  `moteur/decision_qb.py`, voir `moteur/README.md`) : 8 attributs (awareness, processing, coverage reading, decision
  making, pocket awareness, pressure response, anticipation, aggressiveness), dérivés des notes du QB et de l'identité
  de sa franchise, **hors OVR** (notes d'unité et cotes d'avant-match inchangées). Chrono de poche, statut **perçu**
  (erreurs de lecture), style, fin de poche : sacks et interceptions deviennent en partie la conséquence de mauvaises
  décisions. Interrupteur `QB_IQ_ENABLED` (allumé ; `GC_BLOC_B=0` : décisions du bloc A). Exhibition : `--sans-bloc-b`.
- **GameFeed** (additif) : `play.decision.{bloc, qb, perceived, misread, hurried, pocket_time}` ; `roster[].qb_iq` pour
  le QB. **Site** : scramble animé (le QB recule, la poche se referme, il s'échappe), « · under pressure » dans le
  play-by-play, stats d'équipe « Avg. time to throw », « Pressured dropbacks », « QB scrambles », fiche du QB avec
  ses 8 attributs, safety (puce, éclair, play-by-play, stats, commentaire écrit, foule et effets).
- **Commentaire enregistré** : cue `SAFETY` (4 prises dans `outils/audio/catalogue/commentary.json`) — à générer avec
  le workflow « Commentaire audio » (mode `generer`, `seulement` = `SAFETY`) ; d'ici là, sous-titre et voix de
  l'appareil.
- **Rapport de calibration** : charge jusqu'à 12.2 sexies ; `--bloc-b off` pour les décisions du bloc A ; mesure aussi
  les safeties et, bloc B, les erreurs de lecture et les stats par QB. `calibrer_bloc_a.py --bloc B` recalcule
  `CALIBRATION_B`.

### 17. ENGINE INTELLIGENCE — bloc C : intelligence des joueurs (notebook V24, 04/10/2026, allumé)

- **Receveurs et défenseurs** (cellule 12.2 septies, module `moteur/intelligence_joueurs.py`, voir `moteur/README.md`) :
  6 attributs de receveur (route IQ, release, separation, reconnaissance zone / homme, catch in traffic, contested
  catch) et 7 de défenseur (play recognition, zone IQ, man IQ, awareness, reaction, discipline, pursuit), dérivés des
  notes du roster et de l'identité de la franchise, **hors OVR** (notes d'unité et cotes d'avant-match inchangées).
  Ce qui pèse, c'est le **profil** (l'écart d'un attribut au niveau des notes du joueur, déjà dans le duel du bloc A).
- **Abstraction statistique** : chaque receveur fait face au défenseur **responsable** (homme : son vis-à-vis ; zone :
  un défenseur de la tranche attaquée). Les attributs déplacent sa séparation avant la lecture du QB (release, cassure,
  lecture de la couverture, soupape, screen), l'écart entre la route dessinée et la route courue est tiré selon le
  route IQ, et un défenseur peu discipliné laisse parfois un receveur seul (**coverage bust**, surtout sur play action
  et double move). Puis la **réception** : libre (open), serrée (catch in traffic), couverte ou doublée (contested
  catch ; un défenseur attentif intercepte plus) et les **yards après la réception** (separation contre pursuit). Le
  défenseur responsable est crédité de l'interception et de la passe défendue sur un ballon disputé. Flux aléatoire à
  part. Interrupteur `PLAYER_IQ_ENABLED` (allumé ; `GC_BLOC_C=0` : moteur V23). Exhibition : `--sans-bloc-c`.
- **GameFeed** (additif) : `play.decision.{reception, coverer, bust, busts}` ; `roster[].player_iq` (WR, TE, RB, CB,
  S, LB). **Site** : sur le terrain, le défenseur responsable colle le receveur sur un ballon disputé et personne
  n'est près de la réception sur un coverage bust ; play-by-play « · contested catch », « · caught in traffic »,
  « · X in coverage », « · coverage bust (X) » ; stats d'équipe « Contested catches » et « Coverage busts allowed » ;
  fiche joueur « Receiver intelligence » / « Coverage intelligence » ; commentaire écrit (« Broken up by X! »,
  « Coverage bust! … », contested catch). Le commentaire enregistré n'a pas de nouvelle prise (appels génériques).
- **Rapport de calibration** : charge jusqu'à 12.2 septies ; `--bloc-c off` pour le moteur V23 ; mesure aussi les
  réceptions par type et les coverage busts. `calibrer_bloc_a.py --bloc C` recalcule `CALIBRATION_C`.

### 18. ENGINE INTELLIGENCE — bloc D : adaptation en match et plan de jeu (notebook V25, 05/10/2026, allumé)

- **Plan de jeu par adversaire** (cellule 12.2 octies, module `moteur/plan_de_jeu.py`, voir `moteur/README.md`) : avant
  le match, chaque coordinateur fait le scouting de l'adversaire, sans hasard — fréquence de blitz -> part du jeu
  rapide (quick game, screens, draws) ; couvertures préférées -> concepts contre l'homme (mesh, croisements, slants) ou
  contre la zone (curl, stick, dagger, sail, champ) ; duels en homme -> **cible favorite** (meilleur mismatch, lue en
  premier une fois sur trois) ; receveurs contre safeties -> passes profondes ; notes d'unité -> léger déplacement
  course / passe. En défense : la menace principale de l'attaque adverse est brackétée plus souvent.
- **Mémoire de tendances et ajustements** (prolonge V21, section 10) : chaque camp retient ce qu'il a vu (cibles du QB,
  blitz sur 3e essai, pression, doubles, jeu rapide contre le blitz). Attaque : **quick game** contre les blitz
  répétés, un **RB qui reste protéger** (poche plus longue, une route de moins ; VEC, qui force, ne le fait pas),
  **bascule hors du double** vers WR2 / TE / RB. Défense : **bracket** sur un receveur trop ciblé et productif,
  **contre-ajustements** — le bracket suit la nouvelle cible quand l'attaque bascule, pression déguisée (deux safeties
  profonds, moins de blitz sur 3e essai) quand le jeu rapide punit le blitz. Profils : CTX réagit vite, AEG lentement et
  longtemps, VEC garde son style, MNL têtu. Interrupteur `GAMEPLAN_ENABLED` (allumé ; `GC_BLOC_D=0` : moteur V24).
  Normalisation `CALIBRATION_D` (passes jouées sous un plan de jeu). Exhibition : `--sans-bloc-d`.
- **GameFeed** (additif) : `play.adjust[].reason` (« 5 of the last 8 targets »), nouveaux `kind` (`plan_o`, `plan_d`,
  `o_quick`, `o_protect`, `o_away`, `d_bracket`, `d_rotate`, `d_disguise`), `game.gameplan` (`{home|away: {offense:
  {summary, focus, …}, defense: {summary, bracket}}}`), `play.decision.plan` (`bracket`, `bracketed`, `protection`,
  `away`, `focus`). **Site** : la raison de chaque ajustement dans le play-by-play ; onglet **« Game plan »** du Match
  centre (plan de chaque équipe, ajustements faits jusqu'à l'action affichée — pas de spoiler) ; « · into the
  bracket », « · game-plan read » ; commentaire écrit (plans, quick game, protection, bracket, rotation, pression
  déguisée) ; carte d'exhibition (ajustements du plan de jeu, contre-ajustements). Corrigé au passage : « holds it too
  long… sacked » ne s'affichait plus depuis le bloc C.
- **Commentaire enregistré** : 7 nouvelles cues (`ADJ_GAMEPLAN`, `ADJ_O_QUICK`, `ADJ_O_PROTECT`, `ADJ_O_AWAY`,
  `ADJ_D_BRACKET`, `ADJ_D_ROTATE`, `ADJ_D_DISGUISE`, 3 prises chacune dans `outils/audio/catalogue/commentary.json`) —
  à générer avec le workflow « Commentaire audio » (mode `generer`) ; d'ici là, sous-titre et voix de l'appareil.
- **Rapport de calibration** : charge jusqu'à 12.2 octies ; `--bloc-d off` pour le moteur V24 ; mesure aussi les
  ajustements par match et les passes jouées sous un plan (bracket, protection, cible évitée, cible favorite).
  `calibrer_bloc_a.py --bloc D` recalcule `CALIBRATION_D`.

### 19. ENGINE INTELLIGENCE — bloc E : progression des joueurs (notebook V26, 05/10/2026, allumé)

- **Décisions de Guillaume** (début du bloc) : une saison = une semaine, **une « année » = 4 semaines** (l'âge augmente
  d'un an toutes les 4 semaines) ; les **vraies notes** évoluent (notes d'unité, OVR et cotes suivent) ; anti-inflation
  « ligue + écart d'équipe borné » ; tout est **figé pendant la semaine** (forme comprise) : les cotes calculées avant
  la semaine restent justes.
- **Chaque joueur des franchises** (cellule 12.2 nonies, module `moteur/developpement.py`, voir `moteur/README.md`) :
  notes de **base** (roster), **actuelles** (développées), **forme** (± 3 points sur toutes ses notes, tirée de ses
  performances de la semaine jouée et du bilan de l'équipe), **potentiel**, rythme de **développement** (slow · normal ·
  fast · star), **âge**, **expérience**. Évolution **par attribut** : physique (pic vers 27-29 ans, puis régression
  rapide), technique (pic plus tard, régression lente), mental (decision_making : progresse avec l'expérience). Jouer
  fait progresser ; l'expérience donne un bonus — relatif à la ligue — aux attributs d'intelligence des blocs B et C
  (lecture du QB, route IQ, reconnaissance, zone / man IQ, discipline).
- **Anti-inflation** : (1) moyenne de chaque note, par unité, ramenée sur sa valeur de départ ; (2) plafonds (potentiel,
  99) ; (3) **écart d'équipe borné** — la **force** d'une franchise (moyenne de ses 4 notes d'unité) reste à ± 0,2 point
  de sa base par un décalage commun de ses notes (ses joueurs gardent leurs écarts entre eux), chaque note d'unité à
  ± 0,75. Bornes fixées après mesure : le moteur est très sensible (≈ 15 points de % de victoires par point de force ; à
  ± 3 par unité, la valeur proposée au départ, VEC montait à 72 % et MNL tombait à 24 % après 8 semaines).
- **Persistance** (comme `staffs_next_week`) : `week.json -> players_next_week` (état complet) et `progression`
  (dérive de la ligue, écarts d'unité, force, corrections du garde-fou, plus fortes hausses / baisses) ; la semaine
  suivante les reprend (15.1). Semaine précédente produite avant V26 : **amorce** depuis ses stats. Non publiés par
  l'API (le serveur ne sert que les champs publics de `week.json`). Interrupteur `PROGRESSION_ENABLED` (allumé ;
  `GC_BLOC_E=0` : rosters de base chaque semaine, moteur V25). Au départ, notes = roster : le moteur joue comme V25.
- **GameFeed** (additif) : `roster[].progression` (`age`, `ovr`, `ovr_base`, `potential`, `form`, `dev`, `experience`,
  `iq_bonus`, `base`, `delta`, `history` : un point par semaine). **Site** : fiche joueur — âge et potentiel sous la
  note, écart à la base sur chaque attribut (▲ / ▼), section « Development » (âge · expérience, forme, note · base ·
  potentiel, rythme, expérience sur les lectures) et **courbe de la note par semaine** (base en pointillés).
- **Audit** (`audit_moteur.py`) : notes = base + écart, 40-99, forme ± 3, **notes figées pendant la semaine** (même
  joueur, mêmes notes dans tous les matchs), `players_next_week` contrôlé (bornes, plafonds, joueurs du roster), force
  ± 0,2 et unités ± 0,75 au plus — bloquant ; dérive de la ligue > 0,5 — alerte.
- **Rapport de calibration** : charge jusqu'à 12.2 nonies ; `--semaines N` joue N semaines de progression (36 matchs
  chacune) avant le test d'équilibre, `--graine-trajectoire` change de trajectoire ; `--bloc-e off` : moteur V25.
  Exhibition : `simuler_exhibition.py` reprend aussi les notes des joueurs de la dernière semaine.
- **À décider plus tard** : retraites et recrues (avec une année = 4 semaines, les titulaires les plus âgés passent
  35 ans en quelques mois ; à traiter avec l'étape 6, plus de franchises — `developpement.completer` accueille déjà
  des joueurs nouveaux ou partis).

### 20. ENGINE INTELLIGENCE — validation complète (06/10/2026)

- `python3 outils/moteur/validation_complete.py` (≈ 30 min ; `--rapide` ≈ 6 min ; workflow manuel « Validation
  complète ») : tests unitaires, intégration (GameFeed validé et audité action par action, stats joueurs = stats
  d'équipe) pour chaque étage du moteur et après 8 à 52 semaines de progression, déterminisme (rejeu, autre processus),
  non-régression (rapports publiés à l'identique), calibration contre V21. Résultats : `programme/Feuille_de_route.md`
  (« Fin de programme ») et `outils/moteur/rapport_validation_complete.json`.
- Corrigé : l'ordre d'affichage de deux ajustements défensifs V21 simultanés dépendait du hachage de Python (GameFeed
  non reproductible octet par octet ; jeu inchangé).
- Action « GameFeeds d'exhibition » (`outils/exhibition/gamefeeds.py`) : 12 GameFeeds du moteur V26 (notes et staffs de
  la dernière semaine) dans un artefact, à charger sur le site (« Load GameFeed »).

### 21. Extension du playbook V0.1 (notebook V27, 06/10/2026, allumée)

- **Source** : `programme/GRIDIRON_SIM_PLAYBOOK_EXPANSION_DATABASE_V0.1.md` (base de connaissances football de
  Guillaume). Tout ce qu'elle apporte et que le moteur n'avait pas est branché (cellule **12.2 decies**, module
  `moteur/playbook_expansion.py`, voir `moteur/README.md`) ; **aucun doublon** : ce que le moteur avait déjà, même sous un
  autre nom, est rangé en alias (131) ; sans définition sûre, en réserve (SALEM, SPILL_PROTECTION ; personnel 10 bloqué
  par la compatibilité avec des rosters à 3 WR ; équipes spéciales, hors playbook).
- **Attaque** : 22 formations (avec leur personnel 11 / 12 / 21 / 22 et leurs modificateurs : tight, Y-off, wing, stack,
  quads, trips open / tight, flex, bunch, deuce, wing pair, nasty, strong / weak, full house, wildcat…), 144 plays,
  23 concepts de course (wham, power toss, pin & pull, buck sweep, counter sweep, jet action, end around, reverses,
  QB draw / sweep, 6 options, 6 RPO), 18 concepts de passe (hitch, choice, écrans WR, mesh wheel, pivot, spot, levels,
  Y-cross, dart, double dig, flood, deep cross, double post, divide, switch verticals, PA slide / flood), 9 routes,
  motions (jet, orbit, across, return, trade) et shifts, protections (5 / 6 / 7, slides, man, chip, scat),
  enchaînements entre concepts. Méthode « Roman 2014 » : chaque nouveau concept prend une part du budget d'un concept
  existant (identités et mélange course / passe conservés) ; MNL garde ses courses à ses RB, VEC n'a ni option ni
  wildcat.
- **Défense** : 33 paquets joués à l'intérieur de l'appel du coordinateur (press / off man, robber, Cover 2 man, banjo,
  Tampa 2, Cover 2 sink, Cover 3 sky / buzz / match, match quarters, palms, Cover 6 / 8 ; pression **présentée** sans
  être jouée : sim pressure, creeper, mug drop, exchange ; vraie pression : fire zone, Cover 2 fire, 7 rushers, mug,
  overload, A / B gap, edge, corner, safety, nickel, cross dog), jeux de rush à 4, 11 fronts (4-3 over / under / even,
  bear, tite, hybrid, mint, stack, short yardage, nascar, empty) et mouvements de front.
- **Interaction** : RPO lu après l'appel défensif (boîte chargée -> le QB lance, et le jeu devient une passe décidée) ;
  option lue sur le bord (le QB garde plus quand il ferme) ; le QB se trompe plus contre une coquille déguisée, moins
  après une motion qui révèle l'homme ; un blitzeur laisse son receveur ; front, motion, shift et mouvement pèsent sur
  les courses. Chaque système tire dans son flux (`xp-…|graine|n° d'action`).
- **Mesures** (1 008 matchs, `rapport_calibration.py --reference` V26) : toutes dans les tolérances — complétion 65,4 ->
  64,1 %, sacks 8,3 -> 8,7 %, YPA 7,62 -> 7,46, yards / course 5,70 -> 5,78, points 52,7 -> 51,7, pertes de balle
  3,66 -> 3,58, passes 58,6 -> 59,7 % ; victoires CTX 54,7 · VEC 48,0 · AEG 50,7 · MNL 46,6 %. Temps : 230 ms par match
  contre 175 sans l'extension (feuille d'appel mise en cache). Semaine du 12/10 produite avec le notebook complet
  (12.3, 13.x passés) : `audit_moteur.py` 0 anomalie, 0 alerte (39 matchs, 5 415 actions) ; 49 min sur la machine de la
  session, chargée en même temps par l'exhibition (budget du job : 75 min — à surveiller au prochain samedi).
- **GameFeed** (additif) : `play.call.{personnel, motion, shift_from, protection, rpo, option, sequence}`,
  `play.call.defense.{package, presented, front, rush, movement}`. **Site** : les 22 formations dessinées (wildcat :
  snap direct au RB, QB écarté), nouvelles routes et concepts, courses du QB / receveur / TE, rôles (H-back, wing,
  fullback…), personnel et paquet réel dans la ligne de l'action, « jet motion », « RPO, pulled and thrown », « QB keeps »,
  « Fire Zone (showed mug) » dans le play-by-play (même code dans la cellule 427).
- Interrupteur `EXPANSION_ENABLED` (allumé ; `GC_EXPANSION=0` : moteur V26 à l'identique, contrôlé dans la cellule).
  Rapport : `--expansion off`. Exhibition V27 : CTX @ MNL (`exh-v27-ctx-mnl`, remplace `exh-v25-ctx-vec`) ;
  `simuler_exhibition.py --sans-expansion`.

### 22. Fin de période : field goal ou continuer (notebook V28, 06/10/2026, allumée)

- **Constat** (Guillaume, puis mesuré sur 240 matchs V27) : dans les dernières secondes du Q2 et du Q4, une équipe à
  portée de field goal jouait presque toujours une course ou une passe (dernière action du quart-temps : 4 field goals
  sur 166), même menée de 2 ou 3 points. **Cause** : `simulate_drive_franchise` (12.2) ne regardait le field goal qu'au
  4e essai, jamais l'horloge ; une action arrêtée quand l'horloge tombe à zéro ne rapporte rien.
- **Correction** (cellule **12.2 undecies**, module `moteur/fin_de_periode.py`) : dans les 45 dernières secondes du Q2 et
  du Q4, à chaque snap, le moteur **compare** « field goal maintenant » et « continuer » avec un modèle du reste de la
  période — temps d'une action (mesuré), essai et distance, touchdown / perte de balle / arrêt / gain par zone (mesurés,
  × écart des unités attaque - défense), probabilité du kicker (distance + équipes spéciales, barème du moteur),
  possibilité de tirer plus tard — et prend la meilleure valeur : **points attendus** au Q2, **probabilité de victoire**
  au Q4. Pas de règle fixe : à 40 s à la ligne des 30, on joue ; à 3 s, on tire ; mené de 2 ou 3, les 3 points
  (égalité ou victoire) ; mené de 4 et plus, il faut un touchdown ; près de la ligne de but, le touchdown peut valoir plus
  (le moteur marque plus de la moitié des actions à moins de 5 yards). Au 4e essai dans la fenêtre, la même comparaison
  remplace « go for it / field goal ». Temps morts : le moteur n'écoule pas l'horloge entre deux actions, ils ne
  changeraient rien aujourd'hui (paramètre prévu pour un futur modèle d'horloge). Déterministe.
- **Corrigé au passage** : un drive qui commençait par un field goal (possible désormais au 1er essai) plantait
  (`termination_cause` non défini).
- **Mesures** : 240 matchs — dernière action à portée : field goal 39 fois sur 145 (V27 : 4 sur 166) ; les autres :
  équipe qui a déjà gagné (68), menée de 4 et plus (13), touchdown plus rentable près de la ligne de but (25) ; 149
  field goals avant le 4e essai (135 réussis). Rapport de calibration (1 008 matchs, référence V27) : tout dans les
  tolérances — points 51,7 -> 53,2 (les 3 points ramassés), victoires CTX 50,0 · VEC 49,0 · AEG 53,0 · MNL 48,0 %,
  temps × 1,08.
- **GameFeed** (additif) : `play.clock_decision = {choice, fg, play, p_fg, distance, objective, reason, down}`.
  **Site** : « takes the points on 2nd down », « needs a touchdown » dans le play-by-play (même code dans la cellule 427).
- Interrupteur `FIN_PERIODE_ENABLED` (allumé ; `GC_FIN_PERIODE=0` : moteur V27 à l'identique). Rapport :
  `--fin-periode off`. Hors sujet, noté pour plus tard : une équipe qui mène dans les dernières secondes ne pose pas
  encore le genou (elle joue l'appel du coordinateur).

### 23. Étape 6, palier 1 : 8 franchises, retraites et recrues (notebook V29, 06/10/2026)

**Décisions de Guillaume (06/10)** : par paliers (franchises 05-08 de la bible des identités d'abord) ; noms, codes et
couleurs proposés par Claude — **validés par Guillaume le 06/10** ; moins de matchs par équipe ; **retraite + recrue générée**.

| Code | Franchise | Bible | Couleur | Coordinateurs (att. · déf.) | Ce qui se mesure (12.3) |
|---|---|---|---|---|---|
| AXM | Axiom Falcons | 05 Precision / West Coast — *Execute* | vert `#2E8A5E` | Lena Strand · Owen Achterberg | meilleure complétion de la ligue (≈ 70 %), jeu court de timing, peu d'INT |
| GLT | Glitch Hornets | 06 Blitz / Chaos — *Disrupt* | violet `#6B4FA8` | Rhys Calloway · Vera Kovac | blitz le plus fréquent (≈ 40 % des snaps), le plus de sacks, presse |
| CPH | Cipher Lynx | 07 Mobile / Option — *Deceive* | orange `#C4672B` | Mateo Quill · Selene Arkwright | le QB court (≈ 40 yds / match : read option, RPO, QB draw / sweep) |
| NVA | Nova Raptors | 08 Vertical / Big Play — *Explode* | magenta `#B03A78` | Jasper Holt · Ines Marchetti | 2e attaque la plus explosive (yards / réception, passes de 20+), défense à 2 safeties |

- **Aucun système parallèle** : chaque franchise est décrite dans les tables qui décrivent déjà les 4 de départ —
  12.1 `FRANCHISE_SPECS` (roster de 25 joueurs, bases d'unité, bonus d'attributs, coordinateurs et leurs plages), 12.2 bis
  `FRANCHISE_PLAYBOOK_STYLE`, 12.2 ter `ROMAN_SHARES` / `ROMAN_EXCLUDE`, 12.2 quater profils d'adaptation, et dans
  `moteur/` les `PROFILS` du QB, des joueurs et du plan de jeu, les tables de l'extension du playbook. Les faiblesses de la
  bible se voient dans le face-à-face : GLT punit VEC (qui ne protège pas), AXM et CPH punissent GLT (jeu rapide, QB
  mobile), MNL bat GLT et VEC.
- **Calibrage** : à notes égales, les schémas des nouvelles franchises (option, West Coast…) rapportent plus ; leurs
  notes ont été réglées sur 3 024 matchs (tolérances du programme ENGINE INTELLIGENCE, équilibre 40-60 %), forces un peu
  sous celles des 4 de départ. La défense d'AXM est « dominable physiquement » et celle de NVA « accepte les gains
  courts », comme le dit la bible (sinon MNL tombait sous 40 %).
- **Ligue de 8** : `LEAGUE_TEAMS`, `league_rounds` (12.1) ; semaine **aller-retour** : 56 matchs en **14 créneaux de 4**
  (lundi → jeudi 13 h · 18 h · 22 h, vendredi 18 h · 22 h), 14 matchs par équipe, playoffs inchangés (les 4 premiers).
  **`GC_FRANCHISES=4`** : la ligue de départ, **V28 à l'identique** (vérifié : toutes les mesures égales au notebook V28).
- **Cotes** : 150 simulations par affiche en saison régulière (56 affiches), 300 en playoffs ; calculées **en parallèle**
  (`engine_pregame_odds_many`, `GC_PROCS`, mêmes graines : cotes identiques au calcul en série). 13.2 : le contrôle Brier
  tolère le bruit des simulations et 2 écarts-types (18 matchs par affiche).
- **Feuille d'appel accélérée** (fin de 12.2 undecies) : poids des plays candidats calculés d'un coup par snap ; ≈ × 1,5
  par match, **matchs identiques** (contrôlé dans la cellule ; `GC_PB_RAPIDE=0` : les couches d'origine).
- **Retraites et recrues** (bloc E, `moteur/developpement.py`, `tests/test_retraites.py`) : voir `moteur/README.md`.
  `progression.retirements` dans week.json, `roster[].progression.rookie` (fiche joueur : « Rookie · replaced X »).
- **Site** (et cellule 427) : couleurs des 4 franchises (clair et sombre), styles, « N slots », 4 matchs en direct sur
  l'accueil (2 sur mobile, fluidité), tableau des futures transposé au-delà de 4 équipes. Serveur et audit : nombre de
  créneaux et d'affiches lus dans la semaine (4 ou 8 équipes).
- **Mesures** — rapport de calibration (1 008 matchs, graines de 12.3 ; `outils/moteur/rapport_v29_etape6.json`) : tout
  dans les tolérances contre V21 — complétion 64,2 %, sacks 8,8 %, INT 2,4 %, YPA 7,50, yards / course 5,81 (+0,17 pour
  ± 0,2), points 53,7 (+1,95 pour ± 2), actions 129,7 ; victoires CTX 50,0 · VEC 44,8 · AEG 59,7 · MNL 48,0 · AXM 46,2 ·
  GLT 50,0 · CPH 51,6 · NVA 49,6 % (sur 3 024 matchs : 43,1 à 54,4 %) ; temps × 1,11. **Semaine du 12/10 produite**
  (`generer_semaine.py`, notebook complet, 2 processus) en 35,5 min : `audit_moteur.py` **0 anomalie, 0 alerte** (59 matchs,
  8 279 actions) ; site rejoué dans Chromium (bureau et 390 px), aucune erreur.

### 24. Site : My team, fiches joueurs depuis les rosters, plein écran agrandi (06/10/2026)

Demandes de Guillaume (06/10, avant le palier 2 de l'étape 6) :
- **My team** (barre latérale, et « My team » dans la recherche sur mobile) : un compte choisit son **équipe favorite**
  (gardée sur le serveur : colonne `players.fav_team`, `POST /api/account/team {token, team}` — comptes seulement, équipe
  connue d'une semaine ; `fav_team` dans `/api/me` et les réponses de connexion). La page montre le bilan (W-L, rang,
  points marqués / encaissés, yards à la passe / à la course, sacks, interceptions, domicile / extérieur, série, 5
  derniers), les matchs **joués** (replay) et **à jouer** (direct, cotes), l'**historique de la Grand Final** (titres,
  finales, bilan et rang de chaque semaine terminée : `GET /api/teams/history`, jamais une semaine en cours — pas de
  spoiler), les coordinateurs, les unités et le roster. Sans compte : invitation à en créer un (Settings).
- **Fiche joueur depuis un roster** (Teams et My team) : un clic (ou Entrée) sur un joueur ouvre la **même tuile**
  qu'en match — attributs, intelligence (QB, receveur, défenseur : lue dans les GameFeed de la semaine), développement
  (âge, potentiel, courbe, recrue), stats de la semaine et rang. Code commun : `playerBodyHTML` / `showCardEl`.
- **Plein écran agrandi** (bouton dans l'en-tête du match, retenu sur l'appareil) : terrain plus grand avec le score,
  la ligne des jeux appelés et le commentaire (play-by-play) en haut ; probabilité de victoire, cotes et statistiques
  descendent en bas. Mobile : tout en une colonne, terrain plus haut.
- Au passage : raccourcis d'horloge selon le nombre de créneaux (« Midweek », dernier créneau), « N franchises » sur
  la page Teams.
- Vérifié dans Chromium (bureau 1440 px et mobile 390 px) : aucune erreur JS, pas de défilement horizontal ; API :
  refus sans compte (401) et équipe inconnue (400).

### 25. Étape 6, palier 2 : 12 franchises (notebook V30, 07/10/2026)

Franchises 09-12 de la bible des identités, dans les **mêmes tables** que le palier 1 (aucune logique propre à une
équipe). Noms, codes, couleurs et coordinateurs **proposés par Claude, à valider par Guillaume** :

| Code | Franchise | Bible | Couleur | Coordinateurs (att. · déf.) | Identité dans le moteur |
|---|---|---|---|---|---|
| PLS | Pulse Jackals | 09 No-Huddle / Tempo | `#1C8FC0` | Kade Ferris · Mira Solberg | tempo −3 s par action, hurry-up tôt, jeu rapide (écrans, Stick, Mesh, RPO), défense simple (Cover 3, Quarters) |
| ONX | Onyx Hawks | 10 Turnover / Ball Hawk | `#3E4A59` | Lucien Abara · Saskia Delmont | DB et LB lecteurs (zone_iq, awareness, réaction), appâts et rotations (Robber, Cover 3 Match, Mug drop, Palms), attaque prudente |
| FRG | Forge Bison | 11 Trench Warfare | `#7A4E2D` | Harlan Brody · Tamsin Okeke | OL / DL dominantes, Power / Counter / Duo et play action de poche (≈ 55 / 45), pression à quatre (interior collapse), 4e essais |
| MRD | Meridian Owls | 12 Field Position / Territory | `#6E7F2A` | Ansel Whitford · Priya Lindgren | K / P à 91, field goals longs, 4e essais rares, jeu court sûr, Cover 2 / Cover 3, horloge tuée tôt |

- **Calendrier** : à 12, **aller simple** (11 rondes, 66 matchs, 11 par équipe — 5 ou 6 à domicile), 11 créneaux de 6
  matchs du lundi au jeudi (13:00, 18:00, 22:00 ; jeudi 18:00 et 22:00) ; verrou du classement vendredi 23:30, playoffs
  inchangés. `league_rounds` (12.1) : aller-retour à 8, aller simple à partir de 12.
- **Cotes** : budget inchangé (`SEASON_ODDS_BUDGET` = 8 400 simulations) : 64 par affiche à 12 équipes.
- **Contrôles** (décision de Guillaume, 07/10 : pas d'audit ni de tests lourds avant les 24 franchises) : à 12, le test
  d'équilibre de 12.3 **signale** (⚠️) une franchise hors de 40-60 % au lieu de bloquer, et affiche les identités
  sans les contrôler ; calibrage, rapport de calibration, audit et tests repris à 24 franchises. `GC_FRANCHISES=4` /
  `8` gardent les ligues précédentes et leurs contrôles.
- Site : couleurs `--t-pls`, `--t-onx`, `--t-frg`, `--t-mrd` (thèmes clair / sombre), styles en anglais (Teams).

### 26. Étape 6, palier 3 : 16 franchises (notebook V31, 07/10/2026)

Franchises 13-16 de la bible, dans les mêmes tables (aucune logique propre à une équipe). Noms, codes, couleurs et
coordinateurs **proposés par Claude, à valider par Guillaume** :

| Code | Franchise | Bible | Couleur | Coordinateurs (att. · déf.) | Identité dans le moteur |
|---|---|---|---|---|---|
| APX | Apex Vipers | 13 Red Zone Specialist | `#D63A3A` | Dario Vance · Noor Halvorsen | feuille d'appel situationnelle renforcée, Bunch / Stack, Power / Counter, Boot / Pop, défense homme et paquets de ligne de but |
| LTC | Lattice Wolves | 14 RPO / Spread | `#4049A8` | Ilya Brandt · Freya Lund | RPO (zone intérieure / extérieure), écrans, Stick / Mesh, shotgun 3x1 / 2x2, QB qui lit vite ; défense à rotations tardives |
| ZPH | Zephyr Condors | 15 Air Raid | `#C9A21B` | Bo Kittredge · Celia Moreau | attaque la plus portée sur la passe (≈ +0,20), Empty / 4-5 WR, Mesh, Y-Cross, verticales ; QB distributeur ; couvertures multiples |
| BST | Bastion Panthers | 16 Lockdown Coverage | `#5B2C6F` | Gideon Pryce · Annika Strauss | secondaire à 90, presse et couvertures « match », brackets / doubles (plan de jeu), pression à quatre ; attaque prudente |

- **Calendrier** : à 16, aller simple : 15 rondes, 120 matchs (15 par équipe), 15 créneaux de 8 du lundi au vendredi
  (13:00, 18:00, 22:00) ; verrou vendredi 23:30, playoffs inchangés.
- **Cotes** : budget tenu à 8 400 simulations : **35 par affiche** à 16 équipes (240 affiches ; plancher abaissé de 60 à
  35 — décision de Guillaume : rester sous 75 min, quitte à réduire les simulations par affiche).
- **Contrôles** : comme au palier 2 (signalés sans bloquer, repris à 24 franchises).

### 27. Étape 6, palier 4 : 20 franchises (notebook V32, 07/10/2026)

Franchises 17-20 de la bible (les dernières qu'elle décrit), dans les mêmes tables. Noms, codes, couleurs et
coordinateurs **proposés par Claude, à valider par Guillaume** :

| Code | Franchise | Bible | Couleur | Coordinateurs (att. · déf.) | Identité dans le moteur |
|---|---|---|---|---|---|
| GRZ | Granite Grizzlies | 17 Run Defense | `#7D838F` | Silas Brennan · Hanna Kowalczyk | DL / LB qui plaquent et poursuivent, défense « contre la course » (run_focus 0,40), boîtes chargées ; attaque play action derrière les LB |
| MRG | Mirage Cobras | 18 Play-Action / Misdirection | `#E2667A` | Lionel Duquesne · Ingrid Halloran | play action, Boot, Counter, reverse, end around, jet ; QB qui lit les réactions ; défense de discipline des yeux |
| GMB | Gambit Stallions | 19 Fourth Down / Risk | `#0FA3A3` | Rocco Valente · Delphine Ashworth | 4e essais jusqu'à 5 yards dès sa ligne de 30, field goals plus courts, hurry-up tôt ; pressions choisies et presse |
| PRM | Prism Chameleons | 20 Positionless / Matchup | `#7DB82E` | Matthias Ekwueme · Sabine Rourke | formations très variées, motions, ajustements rapides en match (adaptive 0,14) ; défense hybride à toutes les couvertures |

- **Calendrier** : à 20, aller simple : 19 rondes, 190 matchs (19 par équipe), 19 créneaux de 10 : lundi-jeudi à
  11:00, 14:30, 18:00, 21:30 ; vendredi 13:00, 17:30, 22:00 ; verrou vendredi 23:30, playoffs inchangés.
- **Cotes** : budget de 8 400 tenu : **22 simulations par affiche** (380 affiches ; plancher 22 à 20 équipes).
- **Contrôles** : comme aux paliers 2 et 3. La bible décrit 20 franchises : les 21-24 restent à concevoir.

### 28. Étape 6 : franchises 21-24, ligue de 24 (notebook V33, 07/10/2026)

La bible décrit 20 franchises : les 21-24 sont **proposées par Claude** pour compléter les identités existantes (à
valider par Guillaume — noms, codes, couleurs, coordinateurs **et identités**). Deux d'entre elles s'appuient sur le
bloc E (progression) : `developpement.AGE_EQUIPE` décale l'âge tiré des joueurs d'une franchise (0 pour les autres :
leurs tirages ne changent pas).

| Code | Franchise | Identité | Couleur | Coordinateurs (att. · déf.) | Dans le moteur |
|---|---|---|---|---|---|
| SPK | Spark Kestrels | 21 Youth — « Grow » | `#FF8A3D` | Tessa Lindqvist · Oscar Bellweather | joueurs ≈ 3,5 ans plus jeunes (potentiel élevé : progresse au fil des semaines), notes de départ plus basses, vitesse ; audacieuse, presse et blitz |
| CTD | Citadel Rams | 22 Veterans — « Endure » | `#264653` | Bernard Okonkwo · Margot Delacourt | joueurs ≈ 3,5 ans plus âgés (notes hautes, déclin et retraites plus tôt), QB vétéran de poche, lecture ; zones disciplinées |
| TDL | Tidal Herons | 23 Wide Zone / Bootleg — « Flow » | `#9B5DE5` | Callum Fairweather · Petra Lindahl | zone extérieure (65 % des courses), toss, sweeps, play action en mouvement, crossers |
| CMT | Comet Stingrays | 24 Special Teams — « Ignite » | `#F15BB5` | Nadia Petrov-Lane · Gareth Mwangi | K / P à 93, field goals jusqu'à 60 yards, vitesse (retours, écrans, jet, end around) |

- **Calendrier** : à 24, aller simple : 23 rondes, 276 matchs (23 par équipe), 23 créneaux de 12 : lundi-jeudi à
  10:00, 13:00, 16:00, 19:00, 22:00 ; vendredi 13:00, 17:30, 22:00 ; verrou vendredi 23:30, playoffs inchangés.
  (Depuis le 10/10 : matchs étalés de 10:00 à 22:00, un coup d'envoi toutes les 30 min — section 35.)
- **Cotes** : budget de 8 400 tenu : 15 simulations par affiche (552 affiches).
- **Prochain** (décision de Guillaume, 07/10) : divisions / conférences (bible, section 14), calibrage des forces,
  contrôles d'identité, rapport de calibration, audit et tests — maintenant que les 24 franchises existent.

### 29. Étape 6 : divisions, calibrage, contrôles à 24 franchises (notebook V34, 08/10/2026)

Décision de Guillaume (07/10) : audits et tests repris une fois les 24 franchises créées.

**Divisions et conférences** (bible, section 14 ; répartition proposée par Claude, validée par Guillaume le 08/10) — `LEAGUE_STRUCTURE`
(12.1), une des 4 franchises de départ par division, un mélange d'identités dans chacune :

| Conférence | Division | Franchises |
|---|---|---|
| Nexus | Circuit | CTX, PRM, BST, FRG, CMT, PLS |
| Nexus | Grid | AEG, NVA, GLT, TDL, GMB, SPK |
| Frontier | Horizon | MNL, ZPH, ONX, MRG, CTD, AXM |
| Frontier | Summit | VEC, CPH, LTC, GRZ, MRD, APX |

- Calendrier inchangé (aller simple : chaque équipe rencontre les 23 autres). Playoffs : les **4 champions de division** ;
  demi-finales = **finales de conférence** ; Grand Final entre les champions de conférence (`playoff_order`, 14.1 : seeds[0]
  = meilleur bilan, seeds[3] = l'autre champion de sa conférence). Futures alignés (« Grand Final berth » = champion de
  conférence). Export : `week.league` et `conference` / `division` par équipe (le serveur les transmet tels quels).
- Site : classement par conférence et division (# = rang de la ligue) puis tableau de la ligue ; « Conference final ».
- Audit (`audit_moteur.py`) : les finales de conférence opposent les champions de division.

**Calcul du samedi** (mesuré cellule par cellule à 24 : 44 min avant, dont ≈ 15 min de contrôles et de démonstrations) :
`CONTROLES` (12.1) — avec `GC_WEEK_START` (calcul hebdomadaire) ou `GC_LEGER=1` (exhibition), le test d'équilibre
(12.3), la calibration (13.2), le match 13.3, la vérification 13.4 et la semaine d'exemple (14.2) sont sautés ; seules
les 276 affiches de la semaine sont simulées, à **50 simulations par affiche** (au lieu de 15). Mesuré : **32 min** en
local (≈ 45 min estimées sur GitHub, limite 75). Les contrôles tournent dans une exécution complète du notebook (sans
`GC_WEEK_START`), dans `outils/moteur/validation_complete.py`, ou avec `GC_CONTROLES=1`.

**Calibrage** (banc de réglage, 4 416 matchs, 8 par affiche et par terrain) : forces et tempos des 20 nouvelles
franchises (les 4 de départ inchangées : `GC_FRANCHISES=4` reste identique à V28). Défenses renforcées, tempos extrêmes
ramenés (PLS −1 ; LTC, ZPH, SPK, GMB 0), passe un peu moins dominante (ZPH 0,14), FRG / CPH / APX / CTD un peu moins
forts, MRD / PRM / SPK / GMB / CMT relevées. Résultat : **43,3 à 57,9 % de victoires** ; mesures de la ligue dans les
tolérances de la référence V21 sauf **points +2,5** (± 2 : composition de la ligue — VEC, ZPH, PLS, MRG marquent
beaucoup par identité) et **yards / course +0,2** (décision de Guillaume du 06/10 : on laisse).

**Contrôles stricts à 24** (exécution complète) : 12.3 — équilibre 40-60 % élargi d'un écart-type du bruit (184 matchs
par franchise) et identités nettes (passe ZPH / VEC, MNL min ; blitz GLT / VEC ; sacks GLT ; 4e essais GMB ; gros gains
VEC / ZPH ; course MNL ; course du QB CPH ; complétion AXM dans les 3 premiers ; défense AEG ou BST) ; 13.2, 13.4 et
14.2 bloquants comme à 4 et 8 équipes. **Exécution complète du 08/10 (43 min) : tout passe** — 12.3 : 40,2-59,5 % sur
2 208 matchs, identités nettes ; 13.2 : Brier 0,2495 (formule de notes 0,2605), z² 0,96, biais +1,2 %, spread 51,6 %,
over 50,9 %, marge −3,5 % ; 13.4 : extrêmes ±0,023, écart moyen 0,021, outsiders +4,9 % ; 14.2 : semaine validée
(279 GameFeed). Audit d'une semaine à 24 (`audit_moteur.py`) : 0 anomalie bloquante, 2 alertes (un score très élevé, un
match très long). Mémoire : 12.3 ne garde que équipes et scores après ses contrôles (2 208 matchs complets ≈ 7 Go).

**Ligue de 4 (`validation_complete.py`, 08/10)** : le jeu à 4 équipes est **identique** avant l'étape 6 (b56f600) et
maintenant (étage ABCDE, 2 graines : toutes les mesures égales, seul le temps change — 0,12 s par match contre 0,18).
**Références régénérées (08/10)** avec `validation_complete.py --regenerer-references` (moteur actuel, V27 extension du
playbook et V28 fin de période comprises) : `reference_v21.json`, `rapport_v23_safety_bloc_a.json`,
`rapport_v23_bloc_b.json`, `rapport_v24_bloc_c.json`, `rapport_v25_bloc_d.json`, `rapport_v26_bloc_e.json` (départ et
trajectoires 8 / 16 / 24 / 32 semaines) — champ `regenere` dans chaque fichier, chiffres d'origine dans l'historique git.
Le contrôle 12.2 decies (« MNL : courses toujours à ses RB ») ne compte plus les scrambles du QB sur une passe (étage AB).
Résultat : non-régression et intégration de tous les étages ✅, déterminisme ✅, calibration ✅ sauf **2 contrôles
bloquants restants, de jeu (pas des références)**, déjà présents avant l'étape 6 : E8 (trajectoire neuve de 8 semaines)
VEC 39,5 % de victoires (plage 40-60 %) ; E52 dérive de ligue 0,56 (plafond 0,5) — corrigés le 09/10 (section 31).

### 30. Validations de Guillaume et bilan dans le tableau de score (08/10/2026)

- **Validés par Guillaume (08/10)** : noms, codes, identités et couleurs des franchises 05-24, et la répartition en
  conférences et divisions (section 29).
- **Tableau de score des matchs** (tuiles de l'accueil, fenêtre du match, plein écran) : sous le code de chaque équipe,
  en petit, son **bilan et son rang dans la ligue au coup d'envoi** (« 6-8-2 · #14 » ; bilan seul avant le premier
  créneau). Calculé dans le site depuis `standings_by_slot` (`recRank`) — rien à ajouter côté serveur ni notebook.

### 31. Progression rééquilibrée et audit de l'interface des matchs (09/10/2026)

**Progression des joueurs (bloc E)** — les deux contrôles bloquants restants de la validation complète :
- *Dérive de la ligue (E52 : 0,56 pour un plafond de 0,5)* : elle venait de la **forme**, pas des notes. Recentrée une
  seule fois puis bornée à ± 3, sa moyenne restait jusqu'à ± 0,5 dans un petit groupe (4 à 8 TE ou QB). Elle est
  maintenant recentrée en plusieurs passes, et de nouveau après le garde-fou d'équipe (qui réduit aussi la forme).
  Dérive maximale mesurée : 0,19 sur 52 semaines.
- *VEC à 39,5 % après 8 semaines (plage 40-60 %)* : la moyenne des 4 unités prédit mal un match (VEC remis entièrement à
  sa base gagnait encore 43,8 % : ses adversaires avaient progressé là où VEC est faible). Bornes du garde-fou
  resserrées : **force ± 0,15** (0,2) et **unités ± 0,5** (0,75). Mesuré sur la trajectoire neuve : 46-56 % pour les 4
  franchises après 8, 16, 32 et 52 semaines (41-45 % pour VEC avec les anciennes bornes).
- Trajectoires de référence du bloc E (`rapport_v26_bloc_e.json`) régénérées avec ces bornes.
- **Validation complète (09/10, 33 min) : ✅ réussie, 0 contrôle bloquant** — E8 / E16 / E32 / E52 : 45,4-56,4 % de
  victoires, dérive ≤ 0,19, force ≤ 0,15.

**Interface des matchs (direct et replay)** — audit dans le navigateur (serveur local, horloge simulée) :
- *Fenêtre du match figée ou faux replay pendant un TD / FG* : à chaque fin de match d'un créneau, le tableau de
  l'accueil était reconstruit, y compris sous un match ouvert. La fenêtre gardait une copie orpheline du match (terrain
  figé) pendant que la nouvelle copie écrivait score, bannières et puces dedans ; si c'était le dernier match du
  créneau, elle affichait « 0-0 REPLAY » et les bannières d'un replay. Le tableau attend maintenant la fermeture.
- *Actions sautées en direct* : une action dure 6 à 7,5 s à l'écran, le serveur en révèle une toutes les 6,5 s ; à 2
  actions de retard le site sautait (≈ 1 action sur 3 jamais montrée, bannière TD / FG coupée ou restée sur l'action
  suivante). Il rattrape maintenant en accélérant un peu (jusqu'à × 2,5 selon le retard) et ne saute qu'au-delà de 8.
- *Bannière TD / FG tronquée* (« TOUCHI ») : le dégradé du texte ne couvrait pas tout le mot (CSS `repeat-x`). Durée
  de la bannière divisée par la vitesse du replay (2×, 4×) ; un saut (barre, précédent, suivant) coupe la bannière.
- *Page qui se recharge pendant un match* : (1) au passage à la nouvelle semaine, le rechargement attend que la
  fenêtre du match soit fermée ; (2) la page (53 Mo) et l'interrogation du serveur toutes les 3 s (9 Mo, dont 8,8 Mo de
  rosters inutiles) poussaient les téléphones à tuer ou recharger l'onglet : réponses compressées (gzip : page ≈ 5,6
  Mo) et rosters des 276 matchs de saison régulière retirés de `/api/delta` ; requête abandonnée après 15 s (une
  requête bloquée figeait le direct) ; (3) le match regardé est mémorisé pour l'onglet et rouvert après un rechargement.
- Aussi : classement, bilans du tableau de score et cotes des futures figés après le 18e créneau (23 à 24 équipes) ;
  une sélection de texte glissée jusqu'au fond fermait le match ; Échap ferme d'abord la fiche joueur ; le cercle rouge
  clignote aussi pendant la pause après l'action.

### 32. Bannière TD / FG en plein écran sous Safari (09/10/2026)

Signalé par Guillaume (Safari 18, Mac) : en replay, plein écran, à chaque touchdown ou field goal le son se coupe et
l'écran rétrécit. Non reproduit dans Chromium (taille du terrain, mémoire et son stables pendant la bannière, aussi avec
un écran Retina et un processeur ralenti ×6) ; les journaux du serveur montrent que la page n'est pas rechargée (le
direct continue d'interroger le serveur) mais qu'aucun commentaire n'est plus joué après le field goal.
- **Bannière allégée** : texte blanc et `text-shadow` au lieu de `background-clip:text` + 3 filtres `drop-shadow` sur tout
  le terrain, animation sur `transform` / `opacity` seulement (plus d'espacement des lettres ni de reflet animés) — Safari
  redessinait toute la bannière filtrée à chaque image.
- **Son** : si Safari met le contexte audio en pause (« interrupted » / « suspended »), il est relancé aussitôt, sinon au
  prochain clic ou à la prochaine touche.
- **Journal de diagnostic** (`/api/diag`, lignes « DIAG » des journaux Railway) : pendant un match ouvert, bannières (et
  1,5 s / 4 s après), taille de la fenêtre et du terrain, zoom, plein écran, état du son, baisse de qualité d'affichage,
  erreurs JavaScript. Rien de personnel ni stocké ; 60 envois par page au plus.

### 33. iPad : onglet rechargé en plein replay (09/10/2026)

Journal de diagnostic (section 32) de Guillaume sur iPad, Safari, Bigger field : le replay avance normalement (bannières
TD / FG correctes), puis après ≈ 9 minutes la page est rechargée sans événement de fermeture et le match repart de la
1re action — iOS tue l'onglet faute de mémoire et le recharge (pas de fuite mesurée : mémoire JavaScript stable sur tout
un replay). Le poids venait de la page (texte de la semaine ≈ 52 Mo : 32 000 actions, rosters répétés dans chaque match).
- Le texte de la semaine est libéré dès qu'il est lu ; le roster d'une équipe n'est gardé qu'une fois (558 → 24).
- En Bigger field, le site derrière le match n'est plus dessiné (`body.gc-match`) : mémoire graphique des terrains de
  l'accueil libérée.
- Sons en mémoire : budget réduit sur iPad (48 Mo au lieu de 96).
- Si l'onglet est quand même rechargé, le replay **reprend à l'action où il était** (position notée à chaque action).

### 34. iPad : page allégée (matchs terminés sans le détail des actions) (09/10/2026)

Après la section 33, l'onglet était toujours rechargé (14h50, ≈ 10 min de replay, 4 s après un touchdown) et le replay
ouvert depuis le calendrier n'était pas rouvert. Mesures (Chromium) : sans fuite JavaScript ni audio (nœuds Web Audio
créés = débranchés), la page reste lourde.
- **Page allégée** : les matchs terminés, sauf les 12 plus récents (ceux de l'accueil), n'emportent plus que ce que
  l'accueil, les classements, les stats de la saison et les moments forts lisent (résultat, yards, joueurs, texte, score,
  type d'appel) ; le détail (appel complet, décision du QB, ajustements, cotes action par action) arrive avec
  `/api/feed/{id}` à l'ouverture du replay (« Loading the replay… »). Rosters écrits une fois par équipe (`rosters`).
  Page : 53 → 20 Mo (jeudi soir ; moins encore en fin de semaine) ; mémoire JavaScript 64 → 22 Mo ; stats de la saison
  identiques (432 joueurs, 228 matchs comparés).
- **Reprise après rechargement** pour tous les replays (accueil, calendrier, recherche, moments) : à la bonne action,
  après le chargement du détail si besoin.
- Sons générés (sifflet, corne, impacts) : nœuds débranchés à la fin de chaque effet ; canevas vidés quand un terrain
  est fermé (Safari iOS ne rend leur mémoire qu'ainsi).

### 35. Calendrier : un coup d'envoi toutes les 30 min ; « AI Bowl » devient la « Grand Final » (10/10/2026)

- **Calendrier** (notebook 14.1, `season_kickoffs`) : du lundi au vendredi, coups d'envoi de 10:00 à 22:00, toutes les
  30 min (25 heures par jour, aucune vide). Volume de chaque jour inchangé : 60 matchs du lundi au jeudi (5 rondes,
  2 ou 3 matchs par heure), 36 le vendredi (3 rondes, 1 ou 2 par heure). Une ronde (`slot` : chaque équipe joue une
  fois) occupe un bloc d'heures consécutives — 10:00-12:00, 12:30-14:30, 15:00-17:00, 17:30-19:30, 20:00-22:00 ;
  vendredi 10:00-13:30, 14:00-17:30, 18:00-22:00 — et se termine avant la suivante : classement et futures après
  chaque ronde inchangés, aucun résultat connu avant la mise à jour des futures. Dans une ronde, les équipes qui ont
  joué le plus tôt jouent les premières : ≈ 2 h 40 de repos en moyenne entre deux matchs d'un jour (2 h au moins).
  Un match dure ≈ 15 min en direct (≈ 140 actions × 6,5 s) : deux heures voisines ne se chevauchent pas.
  Inchangés : verrou vendredi 23:30, finales de conférence samedi 16:00 et 20:00, finale dimanche 22:00.
- **Grand Final** : nouveau nom affiché de la finale (site, notebook, audit, GameFeeds des semaines 1 et 2). La clé
  interne `ai_bowl` (phase du match, marché des futures, paris enregistrés) ne change pas.
- Site : « a kickoff every 30 min, 10:00–22:00 », « rounds » au lieu de « slots », raccourcis d'horloge calculés
  depuis le premier coup d'envoi.

### 36. Pauses de retransmission : fin de Q1 / Q3, mi-temps, écran final (10/10/2026)

- **Temps de présentation séparé du temps de simulation** : les actions du moteur ne changent pas (aucune action
  ajoutée, rejouée ou recalculée). Une pause suit l'action qui termine la période, repérée sur cette action seule
  (`after.status` = `half` ; horloge à 0, match en cours = fin de Q1 / Q3, ou du temps réglementaire avant une
  prolongation). Durées : **10 s** (fin de quart-temps), **40 s** (mi-temps) — `BREAK_SEC` (serveur.py), `BRK_SEC`
  (site, reçu du serveur dans `#gf-server`).
- **Ligne de temps du direct** (serveur et site, même règle) : l'action k commence à `ko + k·6,5 s + les pauses après
  les actions 0..k-1`. Le serveur révèle les actions, fixe les cotes en direct, la fin des matchs (`end`, +60 s par
  match) et le règlement des paris sur cette ligne de temps ; pendant une pause, rien de nouveau n'est révélé et les
  cotes restent celles de la fin de la période. Un tableau en direct entre dans la pause quand il y arrive et en sort à
  l'heure (sans accélérer ensuite) ; une page ouverte pendant une pause l'affiche avec le temps restant.
- **Écrans** (sur le terrain seulement : Match centre, cotes et coupon restent utilisables) :
  - fin de Q1 / Q3 : score agrandi, équipes, « 2nd quarter next », compte à rebours, sortie animée avant la reprise ;
  - mi-temps : score central, situation (« CTX lead by 3 at the half »), 3 cartes par équipe de part et d'autre
    (classement provisoire), compte à rebours ;
  - fin du match : vainqueur, score, joueur du match, 3 meilleures performances par équipe (classement définitif) ;
    l'écran reste, « Show the field » le masque (onglet « Final screen » pour le rouvrir). Le replay s'arrête dessus
    au lieu de reboucler.
  - replay : « Resume now » passe la pause ; un saut (barre, précédent / suivant) l'annule. Petits terrains : score seul.
- **Cartes** : stats du Match centre (`computeStats`, action par action, jusqu'à l'action à l'écran) selon le poste —
  QB C/ATT, YDS, TD, INT (+ temps moyen avant la passe, décisions du moteur, quand le flux les a) ; RB CAR, YDS, TD ;
  WR / TE REC, YDS, TD ; défense TKL, SCK, INT, PD ; K FG réussis / tentés, points des FG (le PAT n'est pas une action
  du flux : il n'est pas compté). Une ligne résume le reste (« 2 rec, 21 yds »). Ordre : pondération type fantasy
  (classement seulement, jamais affichée). `computeStats` compte maintenant les field goals par kicker (aussi dans
  l'onglet Players : « Kicking ») et le temps avant la passe par passeur.
- **Publicité (plus tard)** : `BRK_SLOT.half = g => html` ajoute un bloc à l'écran de mi-temps, sans toucher à l'écran.
- **Tests** : `moteur/tests/test_pauses.py` (pauses repérées sur 318 matchs, durées, ligne de temps du serveur,
  actions inchangées, même ligne de temps calculée par le site dans Node) ; `node outils/site/test_pauses.js`
  (Playwright, serveur réel : replay complet pas à pas, durées, reprise, cartes = Match centre, défense = `player_stats`
  du moteur, écran final, « Resume now », direct ouvert pendant la mi-temps).
- Déploiement : un match **en cours** au moment du déploiement recule de quelques actions (sa fin est décalée de ses
  pauses déjà passées) ; déployer hors des heures de match.

### 37. Alerte et relance du calcul du samedi (11/10/2026)

- **Job « suivi »** de `semaine.yml`, après le job « produire », qu'il ait réussi ou non (`outils/ci/alerte_semaine.py`,
  Python seul, jeton de l'exécution). En cas d'échec, il ouvre l'issue **« Semaine suivante : échec du calcul du
  samedi »** (étiquette `calcul-semaine`) ou la commente si elle est déjà ouverte : exécution, étape fautive, fin du
  log (60 lignes), relance tentée ou non, mention du propriétaire du dépôt (notification GitHub).
- **Relance unique** selon l'étape fautive :

  | Étape fautive | Relance |
  |---|---|
  | Ajouter la semaine au dépôt (push) | la semaine calculée (artefact `semaine-calculee`, 7 jours) est repoussée par « suivi » sur `main` à jour, **sans recalcul** ; l'issue est alors fermée aussitôt |
  | machine GitHub : checkout, installation, aucune étape en échec (machine perdue) | nouvelle exécution du workflow (`relance=oui`), en file derrière l'exécution en cours |
  | tests du moteur, calcul, audit ; job annulé (dépassement des 75 min, annulation à la main) | aucune : le même calcul redonnerait le même résultat |

  Jamais de relance du workflow depuis une exécution déjà relancée ni depuis une 2e tentative (pas de boucle).
- **Fermeture** : le prochain calcul réussi (relance, secours du dimanche, lancement à la main, même « Rien à faire »)
  commente et ferme l'issue ouverte.
- **Essai** (Actions → « Semaine suivante » → Run workflow, `test_echec` = `machine`, `audit` ou `push`) : échec simulé
  à cette étape, ≈ 2 min si aucune semaine n'est à produire ; l'issue le signale comme essai. En `push`, une fausse
  semaine `week_test-alerte` est commitée sur la machine puis « repoussée » en `--dry-run` : rien n'arrive dans le dépôt.
- Tests : `moteur/tests/test_alerte_semaine.py` (classement des étapes, relance unique, commandes contre une fausse API
  GitHub locale).

### 38. Contrôle des PR (11/10/2026)

- **Workflow « Contrôle des PR »** (`.github/workflows/controle.yml`) : sur chaque PR vers `main` (sauf celles qui ne
  touchent que des `.md` ou `programme/`), trois jobs en parallèle, en lecture seule :
  - **Python** (≈ 2 min) : tests du moteur et du serveur (`unittest`, fastapi installé : les tests serveur des pauses
    et `test_serveur.py` tournent aussi), audit de toutes les semaines (`audit_moteur.py`) ;
  - **Navigateur (site)** (≈ 6 min) : AudioEventMapper, pauses de retransmission, recherche, scores des matchs terminés, transformations, coups d'envoi et retours, Game Center du notebook
    (cellule 427), musique, commentaire enregistré (dernière
    semaine), foule et effets ;
  - **Navigateur (parité)** (≈ 8 min) : parité Audio System / ancien code sur la dernière semaine.
  Un nouveau push annule le contrôle en cours de la même PR. À la main (*Actions → Contrôle des PR → Run workflow*) :
  champ `semaines` (0 = toutes, ≈ 6 min de parité par semaine). Il remplace le workflow « Tests moteur ».
- **En local, la même commande** (depuis `gamecenter_serveur (1)`, Python avec `requirements.txt`, Node + Playwright, ffmpeg) :
  `bash outils/site/tests_navigateur.sh [--semaines N] [--groupe site|parite]`. Le script fabrique les sons de test,
  lance les serveurs (crochet de test) sur des copies de `data/` (le dépôt n'est pas modifié), lance tous les tests même
  après un échec et résume les résultats.
- **Tests réparés** (ils plantaient : tout `data/weeks`, ≈ 130 Mo, envoyé d'un coup à la page) : `test_parite_v01.js`,
  `test_commentaire_v02.js`, `test_stade_v03.js` envoient les matchs par lots (`outils/audio/commun.js`) et attendent le
  crochet de test au lieu d'un délai fixe (la page met ≈ 4 s à démarrer) ; `--semaines N` pour les N dernières semaines.
  Commentaire : « jamais deux fois de suite la même prise » ne vaut que pour les cues à plusieurs prises — les cues à
  une seule prise (`ADJ_SHELVE_FORM`, `ADJ_D_NOBLITZ`, `ADJ_D_PRESS`, `ADJ_D_PREVENT`, `ADJ_D_HEAT`) se répètent
  forcément et sont listées « à enrichir » (workflow « Commentaire audio » pour leur ajouter des prises) ; le test du
  repli fait taire le match à l'antenne pendant la mesure (sa phrase passait aussi par la voix de l'appareil).
- **Cellule 427 du notebook** (Game Center du notebook, `NGS_TEMPLATE` : copie allégée du site, sans serveur, recherche,
  paris en ligne ni exhibitions). Après un changement de rendu de `gamecenter_source.html` : `python3 outils/regen427.py`
  (essai) puis `--ecrire`. L'outil reporte les changements du site depuis le commit noté dans la cellule
  (« Synchronisé avec gamecenter_source.html @ … »), bloc par bloc, là où il retrouve leur code une seule fois ; il liste
  les blocs refusés (partie du site seulement, ou à reporter à la main). `--historique` rejoue les synchronisations
  passées : 12 sur 17 reproduites à l'identique (les autres avaient des reports à la main). Recréé le 11/10/2026 (l'ancien
  outil, hors dépôt, est perdu). Vérifier ensuite : `node outils/site/test_cellule427.js` (replay complet dans Chromium).
  Synchronisée le 11/10 avec le site du 10/10 (stats du Match centre : coups de pied, temps avant la passe,
  bannière TD allégée pour Safari) ; **pas d'écran de pause dans le notebook** (choix du 11/10 : le replay du notebook
  n'a pas la mécanique du site) — `BRK_SEC={q:0,half:RP_HALF}` y garde les pauses d'avant (mi-temps 4 s).
- **Rendre le contrôle obligatoire** (facultatif) : GitHub → *Settings → Branches → Add branch ruleset* (ou *Add rule*)
  sur `main` → *Require status checks to pass* → cocher « Python (tests, audit) », « Navigateur (site) » et
  « Navigateur (parite) ». **Attention** : « Semaine suivante » pousse directement sur `main` ; cette règle refuserait
  son push (à exempter dans la *Bypass list*), et une PR ne touchant que des `.md` / `programme/` (aucun contrôle lancé)
  resterait bloquée. Recommandation du 11/10 : les laisser facultatifs.

### 39. Domaine snapline.live et nom « Snapline » (bloc 2, étape 1 — 11/10/2026)
- **Nom** : le site garde « GameCenter » ; « Snapline » remplace « NFL SIM » au-dessus du logo (titre de l'onglet
  « Snapline GameCenter », description sans « NFL ») ; l'étiquette du bandeau devient « Live ». Les noms internes
  (fichiers, notebook, projet Railway « NFL Sim », clés `gc-…` du navigateur) ne changent pas. Cellule 427 : même surtitre.
- **Domaine** : `snapline.live` (acheté le 11/10) est le domaine personnalisé du service Railway « gamecenter »
  (port 8080). L'offre Railway n'en permet qu'**un** par service : `www.snapline.live` est redirigé par Cloudflare
  (règle de redirection), pas par Railway.
- **DNS chez Cloudflare** : `CNAME @ → y2ud8d0o.up.railway.app` (nuage gris, « DNS only » : Railway délivre lui-même le
  certificat HTTPS) et `TXT _railway-verify → railway-verify=…` (valeur donnée par Railway, *Settings → Networking*).
  `www` : enregistrement proxifié (nuage orange) + *Rules → Redirect Rules* → `https://snapline.live${chemin}`, 301.
- **Ancienne adresse** : avec la variable Railway `GC_DOMAINE=snapline.live`, `serveur.py` redirige toute requête vers
  `*.up.railway.app` sur `https://snapline.live` (308 : chemin, paramètres et méthode gardés). Sans la variable (local,
  tests) : aucune redirection. À ne poser qu'une fois `https://snapline.live` en service (certificat délivré), sinon
  l'ancienne adresse renverrait vers une page morte. Les données du navigateur (`gc-…`) sont liées à l'adresse : un
  invité de l'ancienne adresse repart de zéro sur la nouvelle (accepté le 11/10 : pas encore de visiteurs).

### 40. Scores des matchs terminés, réglage « Hide scores » (bloc 2, étape 2 — 11/10/2026)
- **Par défaut, les scores s'affichent** : bandeau du haut (8 derniers matchs terminés, score et « FINAL »), tuiles des
  matchs terminés du tableau Live (image finale avec le score, puce « Final »), Big plays de tous les matchs terminés.
- **Réglages → Display → « Hide scores »** (désactivé par défaut, gardé dans le navigateur, `gc-settings-v1.spoil`) :
  la protection d'avant, partout — un match terminé non regardé ici n'a pas de score (« − ») dans le bandeau ni sur sa
  tuile (teaser des grosses actions, cotes d'avant-match), et ses grosses actions ne sont pas dans les Big plays. Le
  changement s'applique tout de suite (tableau, bandeau, Big plays redessinés). Une seule fonction décide : `seen(id)`.
- Calendrier, classements et fiches d'équipe montraient déjà les scores : inchangés.
- Test : `outils/site/test_bandeau.js` (groupe site de `tests_navigateur.sh`) — serveur sur une copie des données, horloge
  2 h après le premier coup d'envoi de la dernière semaine ; scores du bandeau = scores du moteur ; réglage activé,
  gardé au rechargement, désactivé.

### 41. Transformation après un touchdown : point après touchdown ou 2 points (bloc 2, étape 3 — 12/10/2026)
- **Moteur** (module `moteur/transformation.py`, tests `moteur/tests/test_transformation.py`, notebook 12.2 duodecies) :
  le touchdown vaut 6 points ; l'attaque tente ensuite une **transformation**, action à part sans temps de jeu.
  Point après touchdown : coup de pied de la ligne des 15, ≈ 94 % (± 0,4 point par point de précision du kicker).
  2 points : course (45 %) ou passe (55 %) de la ligne des 2, ≈ 47 % (± 1 point par point d'écart attaque − défense).
  Choix : tableau de Vermeil sur l'écart APRÈS le touchdown (mené de 2, 5, 9, 12 ; devant de 1, 4, 5, 12) au 4e
  quart-temps et en prolongation, dès le 3e pour un coordinateur agressif (réglages du 4e essai) ; ailleurs le point, sauf
  parfois un coordinateur agressif (5 % × agressivité). Touchdown gagnant sur la dernière action : pas de transformation.
  Non modélisés (choix du 11/10) : coup de pied contré, transformation ramenée par la défense. Tirages dans un flux dédié.
  Interrupteur `GC_TRANSFORMATION=0` : touchdown à 7 points comme avant (contrôlé dans le notebook). LEAGUE inchangé.
- **GameFeed** (additif) : résultats `pat_good`, `pat_missed`, `two_point_good`, `two_point_failed` ; appel
  `extra_point` / `two_point` ; `play.conversion = {choice, reason, play, good, points, p}` ; `try_follows` sur le
  touchdown suivi d'une transformation : **pas de pause** de fin de quart-temps entre les deux (serveur `break_kind` et site
  `brkKind`, même règle). Les anciens matchs (touchdown à 7) restent lisibles.
- **Site** : le point après touchdown est dessiné comme un field goal, les 2 points comme une course ou une passe depuis la
  ligne des 2 ; bannière (« EXTRA POINT · GOOD », « 2-PT CONVERSION »…), « EXTRA POINT » / « 2-PT TRY » à la place de
  l'essai, Match centre : lignes « Extra points » et « 2-pt conversions », kicker FG / XP / PTS. Cellule 427 : même rendu.
- **Audio** : événements `EXTRA_POINT_GOOD/MISS`, `TWO_POINT_GOOD/FAIL` (foule, effets) ; 4 répliques enregistrées à
  générer (`PAT_GOOD`, `PAT_MISS`, `TWO_POINT_GOOD`, `TWO_POINT_FAIL`, 16 prises, 2 par niveau d'intensité : workflow « Commentaire audio », mode
  `generer`) ; d'ici là, sous-titre et voix de l'appareil.
- **Audit** : saut de 1 point seulement sur `pat_good`, transformation juste après un touchdown de la même équipe, sans
  temps de jeu, touchdown à 6 points quand une transformation suit.
- **Tests** : `moteur/tests/test_transformation.py` (choix, taux, flux dédié), `test_pauses.py` (pas de pause entre le
  touchdown et la transformation), `outils/site/test_transformation.js` (groupe site : replay d'un match avec
  transformations — réel, ou complété tant que les semaines n'en ont pas — bannières, score, Match centre).

### 42. Coup d'envoi après chaque score, avec retour (bloc 2, étape 4 — 12/10/2026)
- **Moteur** (module `moteur/coup_envoi.py`, tests `moteur/tests/test_coup_envoi.py`, notebook 12.2 terdecies) : coup
  d'envoi de la ligne des 35 après chaque touchdown (après la transformation) et chaque field goal réussi — sauf quand la
  mi-temps ou la fin du match arrive, et en prolongation (départ aux 25 comme avant). Longueur selon la puissance du
  kicker ; **touchback** (≈ 42 %, départ aux 25) ou **retour** du receveur (le plus rapide des WR2, WR3, RB2 : vitesse +
  agilité, contre les équipes spéciales adverses), ≈ 25 yards en moyenne, parfois une grande chevauchée ; **touchdown sur
  retour** (≈ 0,4 % des coups d'envoi après un score) : 6 points, transformation, puis coup d'envoi en sens inverse.
  Départ moyen ≈ 25,7 (avant : 25). Les coups d'envoi du début de match, de la mi-temps et de la prolongation ont aussi un
  retour (sans touchdown possible). Pas de temps de jeu (comme avant). Non modélisés (choix du 12/10) : onside kick,
  fumble sur retour. Flux dédié ; `GC_COUP_ENVOI=0` : moteur d'avant à l'identique (contrôlé). LEAGUE inchangé.
- **GameFeed** (additif) : `play.kick_return = {kick, landing, touchback, return, td}`, porteur = le receveur, texte
  « Kickoff 66 yds · X returns 24 » / « touchback » ; touchdown sur retour = `result: touchdown` sur un appel `kickoff`
  (`try_follows`, puis transformation). `highlight: BIG` à partir de 40 yards.
- **Site** : le ballon tombe là où le receveur l'attrape, puis il remonte le terrain (genou à terre sur un touchback) ;
  bannières « TOUCHBACK », « KICKOFF · RETURN n YDS », « BIG RETURN » ; Match centre : « Kick return yards », tableau
  « Kick returns » ; commentaire. Cellule 427 : même rendu.
- **Audio** : événements `TOUCHBACK`, `KICK_RETURN_BIG`, `KICK_RETURN_TD` ; 3 répliques, **10 prises à générer**
  (workflow « Commentaire audio », mode `generer`).
- **Audit** : un coup d'envoi après chaque score (feeds avec retours), touchback = départ aux 25, touchdown sur retour
  suivi de sa transformation.
- **Tests** : `outils/site/test_retours.js` (groupe site : replay d'un match avec retours — réel, ou complété tant que les
  semaines n'en ont pas — bannières, textes, score, Match centre).

### 43. Histoire de la ligue, records et stats de carrière (bloc 2, étape 5 — 12/10/2026)
**Décisions de Guillaume (12/10)** : onglet « History » à part ; la semaine en cours compte match par match (« Hide
scores » : seulement les semaines terminées) ; la semaine 1 (4 franchises) est incluse ; transformations et retours
comptent depuis qu'ils existent (semaine du 19/10), sans revenir sur les saisons précédentes.
- **Rien ne change dans le moteur ni dans le calcul du samedi** : tout se calcule sur le serveur à partir des semaines déjà
  enregistrées (`moteur/histoire.py`, bibliothèque standard ; l'image Docker copie maintenant `moteur/`). Chaque semaine
  est une saison. Feuille de match par joueur depuis les GameFeed (mêmes règles que le Match centre) : les totaux de
  saison sont **égaux aux statistiques du notebook** (`week.json`, contrôlé par les tests) — sauf les fumbles provoqués,
  absents des GameFeed (non affichés).
- **API** : `GET /api/league/history` (saisons : champion, score de la Grand Final, finaliste, meilleur bilan, leaders ;
  franchises : titres, finales, demi-finales, bilan de toujours ; records d'un match, d'une saison, top 10 de carrière) et
  `GET /api/league/career/{id}` (les carrières d'une place de roster). Matchs **terminés** seulement (rien d'un match pas
  encore joué) ; `?finished_weeks=1` : semaines dont la Grand Final est jouée. Calculé une fois par match, mis en cache
  tant qu'aucun match ne se termine (≈ 0,1 s par recalcul).
- **Carrière** = identifiant + nom : une recrue reprend la place (l'identifiant) d'un retraité, mais commence sa propre
  carrière ; la fiche dit qui tenait la place avant.
- **Site** : onglet **History** (barre latérale ; « History » dans la recherche sur mobile) — Seasons, Franchises,
  Records (Single game · Single season · Career) ; un record de la semaine en cours a son lien « Replay ». Fiche joueur
  (Teams, My team) : section **Career** — une ligne par semaine, total, rang de toujours dans la statistique du poste.
- **Tests** : `moteur/tests/test_histoire.py` (feuille de match, recrue, saison en cours, records ; totaux = `week.json`),
  `outils/site/test_histoire.js` (groupe site : API, onglet, fiche joueur, « Hide scores », mobile 390 px).

### 44. Rappel « ton équipe joue dans 10 min » (bloc 2, étape 6 — 12/10/2026)
**Décisions de Guillaume (12/10)** : tous les matchs de l'équipe favorite (playoffs compris) + une cloche sur n'importe
quel match du calendrier ; cloches aussi pour les invités (l'équipe favorite demande un compte, comme avant) ; clés
générées et posées sur Railway par Claude ; icône tirée du logo.
- **Web Push** (standard des navigateurs) : la notification arrive même site fermé — ordinateur et Android ; **iPhone /
  iPad : seulement si Snapline est ajouté à l'écran d'accueil** (iOS 16.4+ ; Partager → « Sur l'écran d'accueil »).
  D'où le manifeste (`static/manifest.webmanifest`), les icônes (`static/icons/`) et le service worker (`static/sw.js`,
  servi à la racine : `/sw.js`) — aucun cache hors ligne.
- **Serveur** (`serveur.py`) : tables `push_subs` (un abonnement par appareil), `push_bells` (cloches d'un joueur),
  `push_sent` (envois faits : aucun doublon, même après un redémarrage). Boucle toutes les 30 s (`rappels_dus`,
  `push_tour`) : un match est dû entre 10 min avant son coup d'envoi et le coup d'envoi, quand ses équipes sont connues
  (playoffs). Un abonnement refusé (404 / 410) est oublié. Texte : équipes, phase et heure — **jamais de score**. Lien :
  `/?watch=<match>` (le match s'ouvre sur le grand écran : tout de suite s'il est en direct ou terminé, au coup d'envoi
  sinon). Dépendance : `pywebpush`.
- **API** : `GET /api/push/key`, `POST /api/push/subscribe` (`fav` : « My team's games »), `POST /api/push/unsubscribe`,
  `POST /api/push/test` (« Send a test », une fois par 10 s), `GET /api/push/bells`, `POST /api/push/bell`.
- **Variables Railway** (posées le 12/10, **ne jamais les changer** : cela couperait tous les abonnements) :
  `GC_VAPID_PUBLIC`, `GC_VAPID_PRIVATE`, `GC_VAPID_SUBJECT`. Sans elles : pas de rappel (Réglages le dit).
  Tests : `GC_PUSH_FAKE=1` (envois notés, rien ne part), `GC_PUSH_LOOP=0` (boucle arrêtée), `GC_PUSH_TICK` (secondes).
- **Site** : Réglages → **Notifications** (activer sur cet appareil, « My team's games », « Send a test », explication
  iPhone) ; cloche 🔔 sur chaque match à venir du calendrier. La demande d'autorisation ne vient qu'après un geste. À la
  connexion à un compte, l'appareil le suit ; à la déconnexion, ses rappels s'arrêtent.
- **Tests** : `moteur/tests/test_rappels.py` (fenêtre, équipe favorite, cloches, playoffs, doublons, abonnement refusé,
  texte), `outils/site/test_rappels.js` (groupe site : fichiers de l'application, Réglages, cloche, rappels envoyés par le
  serveur, `?watch=`, mobile 390 px). La réception réelle se vérifie sur un appareil avec « Send a test ».

### 45. Ligues privées entre amis (bloc 2, étape 7 — 12/10/2026)
**Décisions de Guillaume (12/10)** : comptes seulement ; classement de la semaine et de la saison (les mêmes mesures que
le classement général) ; un onglet **Leagues** à part dans la barre de gauche ; 50 membres par ligue, 10 ligues par compte.
- **Serveur** (`serveur.py`) : tables `leagues` (nom, code, créateur) et `league_members`. Un compte crée une ligue et
  reçoit un **code** de 6 caractères (sans 0/O ni 1/I) ; on rejoint avec le code ou le lien `/?join=CODE`. Le créateur
  renomme, retire un membre, change le code (l'ancien lien ne marche plus) et supprime ; tout membre peut partir (le
  créateur parti, la ligue passe au membre le plus ancien ; vide, elle disparaît). Codes faux en série refusés (10 par
  joueur, 40 par adresse en 15 min). Classement : solde de la semaine / gains nets de la saison, tous les membres (ceux
  qui n'ont pas parié viennent après, sans rang) ; réservé aux membres.
- **API** : `GET /api/leagues`, `POST /api/leagues/create`, `GET /api/leagues/preview` (le lien d'invitation, sans compte
  aussi), `POST /api/leagues/join`, `…/leave`, `…/rename`, `…/code`, `…/kick`, `…/delete`, `GET /api/leagues/{id}/standings`.
- **Site** : onglet **Leagues** (« Leagues » dans la recherche sur mobile) — mes ligues, créer, rejoindre avec un code,
  code et lien à partager (partage du téléphone ou copie), classement Week / Season, gestion (créateur) ou départ (avec
  confirmation). Le lien `?join=CODE` ouvre l'invitation ; sans compte, on crée son compte et on rejoint tout de suite.
- **Tests** : `moteur/tests/test_ligues.py`, `outils/site/test_ligues.js` (groupe site).

### 46. Visibilité : vidéos pour les réseaux et référencement (bloc 2, étape 8 — 12/10/2026)
**Décisions de Guillaume (12/10)** : l'action du jour (la plus belle, une décision folle, une action incroyable) et le
résumé d'un match en 2 à 3 minutes ; le son du stade seulement (la musique se met sur le réseau) ; automatique pour
l'action du jour et pour le plus beau match de la semaine, à la demande aussi ; pas d'outil de mesure ajouté (Google
Search Console suffit).
- **Choix** (`outils/video/choisir.py`, bibliothèque standard, rien d'aléatoire) : chaque action est notée — bascule de
  la probabilité de victoire, touchdown (sur retour : plus), perte de balle, gain ou retour de 40 yards et plus,
  **« décision folle »** (4e essai tenté et réussi dans son camp ou avec 4 yards et plus à faire), 2 points réussis,
  field goal de 55 yards et plus ; ×1,5 dans les 2 dernières minutes et en prolongation (« game-winning » si elle fait
  basculer le match). **Action du jour** : la mieux notée des matchs du jour (heure de Bruxelles). **Plus beau match** :
  bascules cumulées, écart final serré, prolongation, remontée, playoffs. **Résumé** : tous les scores, les pertes de
  balle et la dernière action, complétés par les plus grosses bascules jusqu'à ≈ 2 min 30 (19 actions environ).
- **Rendu** (`outils/video/faire_video.py` + `filmer.js`) : le vrai site tourne en local (crochet de test) ; Chromium
  filme le grand terrain du replay en **1080×1920** (vertical : TikTok, Reels, Shorts), avec un bandeau en haut (match),
  un en bas (essai, horloge, texte de l'action) et des cartons (ouverture, fin de quart-temps, score final,
  snapline.live). L'action du jour passe à vitesse normale puis au **ralenti**. Son : les sons du stade du site
  (`audio/manifest.json` : ambiance, snap, coup de pied, réactions selon l'action, sifflet, klaxon), calés sur le snap
  et le résultat filmés, mixés par ffmpeg (−16 LUFS, 48 kHz). Sortie : `videos/<nom>.mp4`, `.txt` (légende anglaise
  avec mots-dièse, prête à coller) et `.json` (ce qui a été choisi).
  ```
  python outils/video/faire_video.py action [--jour AAAA-MM-JJ]       # action du jour (défaut : la journée qui finit)
  python outils/video/faire_video.py resume [--match w3-r91]          # résumé court ≈ 60 s (défaut : le plus beau match)
  python outils/video/faire_video.py resume --long [--match w3-r91]   # résumé long, 2 à 3 min (à la demande seulement)
  python outils/video/faire_video.py action --meilleure               # la plus belle action jusqu'ici (matchs terminés)
  python outils/video/faire_video.py presentation                     # « What is Snapline? » (≈ 20 s, 3 actions)
  python outils/video/faire_video.py joueur [--semaine data/weeks/…]  # le joueur de la semaine (≈ 22 s)
  python outils/video/faire_video.py champion [--semaine …]            # le champion de la Grand Final (≈ 28 s)
  ```
  Il faut Python (fastapi, uvicorn), Node + Playwright avec Chromium, et ffmpeg. Tournage en local (4 cœurs) : ≈ 4 min
  pour une action, ≈ 12-15 min pour un résumé court (sur GitHub, à 2 cœurs : compter ≈ 1,5×).
- **Format TikTok (étape 8.2, 13/10)** : l'action du jour **s'ouvre sur l'action** (plus de carton fixe ; la 1re image,
  qui sert de couverture, montre déjà le terrain), avec l'**enjeu** en grand en haut (`choisir.enjeu` : « Tied 31–31 ·
  0:14 left », « AXM down 28–31 · 1:02 left », « Overtime · … », « 4th & 6 · own 35 », sinon score et horloge ; rien
  sur le résultat) ; au ralenti, la **bascule** de probabilité de victoire (`choisir.bascule` : « AEG win probability ·
  26% → 81% ») ; carton final de 2 s « Watch the next game live · snapline.live ». ≈ 20 s. **Zones sûres** : rien
  d'important dans les ≈ 215 px du haut, les ≈ 400 px du bas et les ≈ 140 px de droite (interface de TikTok, Reels,
  Shorts) ; terrain de 500 à 1 575 px, **resserré à 46 yards** (70 sur le site : joueurs ≈ 1,5× plus gros), tableau de
  score du site masqué (le résumé affiche le score en haut, action par action). **Légende** (`.txt`) : trois blocs à
  copier — TikTok, Instagram, YouTube Shorts (titre de 100 caractères au plus avec `#Shorts`) —, l'accroche en 1re
  ligne, une question selon l'action, 4-5 mots-dièse ; **aucun mot de paris** (« gamble » devient « go-for-it » ; un
  test le vérifie). **« Best play so far »** : `faire_video.py action --meilleure` — la plus belle action de toutes les
  semaines, **parmi les matchs terminés** (coup d'envoi + 2 h : la semaine en cours est calculée d'avance) ; dans le
  workflow, type `meilleure`.
- **Qualité (étape 8.3, 13/10)** : avant, le navigateur était filmé en temps réel par son « screencast », en **432×768**
  agrandi à 1080×1920, et le site baissait de lui-même la résolution du terrain (qualité adaptative : 2× → 1,5× → 1×)
  parce que la machine sans carte graphique « ramait ». Désormais : **tournage image par image** — l'horloge de la page
  est pilotée (`page.clock`, Playwright), elle avance de **1/60 s** entre deux images, quelle que soit la vitesse de la
  machine (mouvement régulier, son calé à l'image près) ; Chromium dessine **nativement à × 2,5**
  (`--force-device-scale-factor`) : images **1080×1920** sans agrandissement ; terrain dessiné à × 2,5 avec ses halos,
  sans qualité adaptative (crochet de test `__gc.fx`, dans `serveur.py` : seulement avec `GC_TEST_HOOK=1`, le site
  public ne change pas). Encodage H.264 High 4.2, **60 images/s**, `crf 17`, `preset slow`, `tune animation`.
- **Résumé court (étape 8.3)** : `faire_video.py resume` (le défaut ; post épinglé n° 3) — « Game in 60 seconds » :
  chaque touchdown (y compris sur retour), chaque perte de balle, les field goals des 2 dernières minutes et de la
  prolongation, la dernière action ; d'abord les scores, au plus ≈ 55 s d'actions (10 actions), 6 au moins
  (`choisir.resume_court`) ; s'ouvre sur la 1re action, le score en haut, sans carton de quart-temps ; carton final
  « Final … » + snapline.live. Le **résumé long** (2 à 3 min) ne se fait plus qu'à la demande (`--long`, type `long`) :
  les replays du site sont faits pour ça, les réseaux ne reçoivent que des formats courts (choix du 13/10).
- **« What is Snapline? » (étape 8.3)** : `faire_video.py presentation` (post épinglé n° 1, ≈ 20 s) — trois actions de
  trois matchs terminés (`choisir.trois_actions` : le plus beau touchdown, la plus belle perte de balle, le plus beau
  4e essai tenté), une phrase en haut de chacune (« 24 teams. 24 AI coaches. », « Every game simulated live », « A full
  season every week »), puis « Free to watch · snapline.live ».
- **Adresse visible (étape 8.4 bis, 13/10)** : sans lien cliquable sur TikTok avant 1 000 abonnés, l'adresse doit se
  lire : badge « snapline.live » (logo du site) au-dessus du texte de l'action pendant toute la vidéo (le bas de
  l'écran est sous la légende du réseau), « SNAPLINE.LIVE » sous le texte des cartons, carton final « Type it in your
  browser » ; le `.txt` a un bloc **Pinned comment (TikTok)** : le commentaire à épingler sous chaque vidéo.
- **Joueur de la semaine et champion (étape 8.6 a, 13/10)** : carton de **statistiques** aux couleurs de l'équipe
  (couleurs du site, `--t-<équipe>`), gros chiffres qui montent de 0 à leur valeur en 0,8 s (horloge pilotée : même
  rendu à chaque tournage). `faire_video.py joueur` (≈ 22 s) — le meilleur joueur de la semaine (une semaine = une
  saison) au **score fantasy** (`choisir.score_fantasy` : passe yards / 25 + 4 par TD − 2 par interception ; course et
  réception yards / 10 + 6 par TD + 0,5 par réception ; défense plaquage 1, sack 4, interception 6 ; field goal 3),
  matchs terminés seulement ; 4 chiffres selon le poste, puis ses 3 plus belles actions (touchdown ou gain de 15 yards
  qu'il porte ou lance, interception / sack / fumble en défense). `faire_video.py champion` (≈ 28 s) — après la Grand
  Final seulement : score de la finale, bilan de la saison régulière, titres de tous les temps, puis ses 4 plus belles
  actions des demi-finales et de la finale. Un match est « terminé » 1 h après son coup d'envoi (avant : 2 h ; la
  Grand Final du dimanche 22 h doit être finie au tournage de 22 h 30 UTC, même l'hiver).
- **Automatique** : `.github/workflows/videos.yml` (« Vidéos ») tous les soirs à 22 h 30 UTC — l'action du jour ; le
  dimanche, en plus, le **résumé court** du plus beau match de la semaine, le **champion** et le **joueur de la
  semaine** (limite du job : 90 min). Les vidéos ne vont
  **pas** dans le dépôt : onglet Actions → l'exécution → **Artifacts** → `videos-<jour>` (zip, gardé 30 jours), puis
  publication à la main. À la demande : Actions → « Vidéos » → *Run workflow* (type `action`, `resume`, `long`,
  `meilleure`, `presentation`, `joueur` ou `champion` ; jour, match).
- **Référencement** : titre et description en anglais, adresse canonique `https://snapline.live/`, Open Graph et Twitter
  (aperçu des liens partagés, image `/og.png` 1200×630 faite par `outils/site/faire_og.js`), JSON-LD `WebSite`,
  `/robots.txt` (tout sauf `/api/`) et `/sitemap.xml`. Texte **« What is Snapline? »** en bas de l'accueil (lisible par
  les moteurs). Bouton **Share** sur le grand écran d'un match de la saison : feuille de partage du téléphone, sinon le
  lien `/?watch=<match>` est copié (il rouvre ce match).
- **Google Search Console** (à faire une fois, par Guillaume) :
  1. search.google.com/search-console → *Ajouter une propriété* → **Domaine** → `snapline.live` ; Google donne un
     enregistrement `google-site-verification=…`.
  2. Cloudflare → `snapline.live` → **DNS** → *Add record* : type **TXT**, nom `@`, contenu = la valeur donnée par
     Google → *Save* ; puis *Valider* dans Search Console (quelques minutes, parfois plus).
  3. Search Console → **Sitemaps** → `sitemap.xml` → *Envoyer*. Puis *Inspection de l'URL* → `https://snapline.live/`
     → *Demander l'indexation*.
  Variante sans DNS : propriété **Préfixe d'URL** + méthode « balise HTML » : mettre la valeur `content` de la balise dans
  la variable Railway `GC_GOOGLE_VERIFY` (le serveur l'ajoute à la page).
- **Tests** : `moteur/tests/test_videos.py` (notes, décision folle, fin de match, bandeaux, sons ; action du jour, plus
  beau match et résumé sur la dernière semaine ; étape 8.2 : enjeu, bascule, légendes, aucun mot de paris, « Best play
  so far » sans match à venir ; étape 8.3 : résumé court, « What is Snapline? » ; étape 8.6 a : score fantasy, joueur
  de la semaine, champion après la finale seulement, titres), `outils/site/test_visibilite.js` (groupe site : balises, robots, plan
  du site, image, texte d'accueil, Share sur téléphone et ordinateur, lien `?watch=`).

### 47. Publicités : Google AdSense, consentement, mentions et page légale (étape 7 — 13/10/2026)
**Décisions de Guillaume (13/10)** : régie **Google AdSense** ; emplacements **mi-temps du grand écran, accueil, bas des
onglets** ; consentement par l'**outil gratuit de Google** (Confidentialité et messages, certifié IAB TCF v2.2) ; page
**Privacy** et **`/ads.txt`**. Repris du plan du 03/10 (`Publicites_plan.md`) : mention permanente « argent fictif ·
aucun gain réel · 18+ », page de règles, mentions légales, blocage des publicités pour les jeux d'argent (interdites en
Belgique depuis le 01/07/2023), emplacements de taille fixe, jamais sur le terrain ni sur les cotes.
- **Rien ne change tant que `GC_ADSENSE_CLIENT` n'est pas posé** : aucun script de régie, aucun emplacement,
  `/ads.txt` absent (404). La mention et la page légale, elles, sont là tout de suite.
- **Variables Railway** : `GC_ADSENSE_CLIENT` (identifiant d'éditeur, `ca-pub-` + 16 chiffres : balise
  `google-adsense-account` et script AdSense dans le `<head>`, `/ads.txt` = `google.com, pub-…, DIRECT,
  f08c47fec0942fa0`) ; `GC_ADSENSE_SLOTS` (blocs d'annonces « display » créés dans AdSense, un par emplacement :
  `half=…,home=…,page=…`) — un emplacement sans bloc n'affiche rien. Mentions légales : `GC_EDITEUR` (nom),
  `GC_EDITEUR_ADRESSE` (adresse), `GC_CONTACT` (e-mail) ; sans elles, la page dit « not set ».
- **Emplacements** (site, `adShow` / `adHTML` / `adPush`) : **accueil** (sous Power rankings / Top agents, au-dessus de
  « What is Snapline? »), **bas des onglets** Schedule, Standings, Teams, History (un seul bloc, `page`) ; **mi-temps**
  du grand écran (`BRK_SLOT.half`, écran complet seulement : ni les tuiles, ni les fins de quart-temps, ni le terrain
  pendant le jeu). Taille fixe : 728×90 si la place le permet, sinon 320×100 (mobile, mi-temps) ; la place est réservée
  avant l'arrivée de l'annonce (rien ne bouge pendant le direct). Libellé « Advertisement ». Aucun bloc dans Live
  board pendant un match, le bulletin, My bets, Leagues, Settings. Un bloc n'est demandé qu'une fois par page (en
  changeant d'onglet, il reste) ; la mi-temps en demande un à chaque écran de mi-temps.
- **Mention et pages** : pied de page sur tous les onglets « **Play money · No real winnings · 18+** », lien « Rules,
  privacy & legal », bouton « **Privacy choices** » (rouvre le message de consentement de Google ; seulement avec
  AdSense) ; phrase 18+ et lien dans « What is Snapline? ». Page **`/legal`** (`static/legal.html`, anglais, thème clair
  / sombre) : règles (argent fictif, 18+, aide : aideauxjoueurs.be / gokhulp.be), politique de confidentialité (ce que
  le serveur garde : clé de joueur, compte et mot de passe haché scrypt, paris, équipe favorite, ligues, rappels,
  journaux ; le stockage du navigateur ; publicité et consentement ; droits RGPD, APD), mentions légales (éditeur des
  variables, hébergeur Railway). Ajoutée au plan du site.
- **À faire par Guillaume dans AdSense** (une fois le compte ouvert) : ajouter le site `snapline.live` ; **Confidentialité
  et messages → RGPD** : créer et publier le message de consentement (EEE, Royaume-Uni, Suisse) ; **Contrôle des
  annonces → Catégories sensibles** : bloquer « Jeux d'argent et paris » (et, au choix, les autres catégories
  sensibles) ; créer 3 blocs d'annonces « Display » à taille fixe (noms : `half`, `home`, `page`) et donner leurs
  numéros (`data-ad-slot`). Google examine le site (de quelques jours à quelques semaines) ; le contenu « paris en argent
  fictif » peut être refusé — la page `/legal` et la mention 18+ répondent aux questions habituelles.
- **Tests** : `moteur/tests/test_publicites.py` (variables, `/ads.txt`, `/legal` échappée, plan du site),
  `outils/site/test_publicites.js` (groupe site : deux serveurs, sans et avec AdSense ; script de Google remplacé par un
  bouchon local ; emplacements par onglet, tailles, place réservée, mi-temps, mobile, mode sombre, `/legal`).

### 48. Promotion sur les réseaux (étape 8 — 13/10/2026)
Plan (compte, rythme, formats, mesure) : `programme/Promotion.md` à la racine du dépôt. Les vidéos viennent du workflow
« Vidéos » (section 46) et se publient à la main.
- **Photo de profil** : `outils/promotion/photo_profil.png` (1080×1080, le logo du site sur son dégradé ; le réseau
  l'affiche en rond). À refaire seulement si le logo change : `node outils/promotion/faire_profil.js` (Playwright).

### Annexe — `.github/workflows/semaine.yml`

```yaml
# Calcule la semaine suivante de NFL Sim GameCenter, gratuitement, sur les machines de GitHub.
# Samedi 3 h (heure de Bruxelles, ≈ 1 h UTC) ; dimanche même heure en secours si samedi a échoué.
# Le script ne fait rien si la semaine suivante existe déjà ou n'est pas encore à produire.
# La nouvelle semaine est ajoutée au dépôt → Railway remet le site à jour tout seul.
name: Semaine suivante

on:
  schedule:
    - cron: "5 1 * * 6"
    - cron: "5 1 * * 0"
  workflow_dispatch: {}

permissions:
  contents: write

concurrency:
  group: semaine
  cancel-in-progress: false

jobs:
  produire:
    runs-on: ubuntu-latest
    timeout-minutes: 75
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Installer le moteur
        run: |
          pip install -r requirements-semaine.txt
          python -m ipykernel install --user
      - name: Calculer la semaine (≈ 15-20 min si elle est à produire)
        run: python generer_semaine.py --suivante --data data --notebook NFL_Sim_GameCenter.ipynb
      - name: Ajouter la semaine au dépôt
        run: |
          git config user.name "gamecenter-bot"
          git config user.email "gamecenter-bot@users.noreply.github.com"
          git add data/weeks
          if git diff --cached --quiet; then
            echo "Aucune nouvelle semaine."
          else
            git commit -m "Nouvelle semaine $(ls data/weeks | tail -1)"
            git push origin HEAD
          fi
```

---

## Lancer en local

```bash
pip install -r requirements.txt -r requirements-semaine.txt
python3 assembler.py
uvicorn serveur:app --port 8000                       # http://localhost:8000
GC_DEMO_AT=auto uvicorn serveur:app --port 8000       # démo : l'horloge part du lundi 12:45 de la dernière semaine
```

Produire une semaine à la main : `python3 generer_semaine.py --lundi 2026-10-12` (reprend la semaine précédente
si elle est dans `data/weeks`), ou `--premiere` pour repartir des staffs de départ.

## Docker (autre hébergeur : VPS Hetzner, Fly.io…)

```bash
cd a_envoyer
docker build -t gamecenter .
docker run -d --restart unless-stopped -p 8000:8000 -v gamecenter-data:/data -e GC_ADMIN_KEY=… gamecenter
```

Tout hébergeur qui lance un conteneur Docker **avec un disque persistant monté sur `/data`** convient
(≈ 110 Mo de mémoire : l'image ne contient que le serveur, les semaines viennent du dépôt GitHub).
Sans GitHub Actions, il faut produire les semaines sur la machine (`pip install -r requirements-semaine.txt`,
`GC_AUTOGEN=1`, ≥ 4 Go de mémoire). Le HTTPS est fourni par l'hébergeur ou un proxy (Caddy, nginx).

## Ce qu'il fait

| | |
|---|---|
| **Direct** | Chaque match démarre à son heure (Bruxelles). Une action toutes les 6,5 s, envoyée **après** avoir été jouée. Le navigateur interroge `/api/delta` toutes les 3 s. |
| **Rien ne fuit** | Pas de résultat avant la fin d'un match, pas d'affiche des playoffs avant son heure, pas de classement final, de champion ni de stats avant qu'ils soient connus, pas de graines des matchs. |
| **Paris** | Pris par le serveur (`/api/bets`) : cote vérifiée (dernière action jouée ou avant-match), marché ouvert, solde. Réglés par le serveur avec les mêmes règles que le site. 1 000 $ par semaine, remis à zéro le lundi 00 h. |
| **Joueurs** | Pas de compte : au premier pari, le serveur donne une **clé de joueur** gardée dans le navigateur. Nom modifiable dans Settings. |
| **Classement** | Commun à tous les joueurs de la semaine (My bets → Leaderboard). |
| **Semaine suivante** | Calculée par GitHub Actions le samedi (`generer_semaine.py --suivante`). Sur un serveur avec ≥ 4 Go de mémoire, `GC_AUTOGEN=1` le fait dans le serveur à la place. |

## API

| Méthode | Chemin | Rôle |
|---|---|---|
| GET | `/` | la page, avec la semaine publique à l'instant présent |
| GET | `/api/delta?have=id:n,…` | état public + actions nouvelles |
| POST | `/api/players` | nouvelle clé de joueur `{token, name}` |
| POST | `/api/players/me` | changer de nom `{token, name}` |
| GET | `/api/me?token=` | paris de la semaine et solde |
| POST | `/api/bets` | `{token, picks:[{key, price_dec, line, stake, title, sub}]}` → acceptés / refusés (et pourquoi) |
| GET | `/api/leaderboard` | classement de la semaine |
| GET | `/api/backup?key=` | sauvegarde .zip (base + semaines), si `GC_ADMIN_KEY` est définie |
| GET | `/api/health`, `/api/time`, `/api/docs` | état, heure du serveur, documentation |

## Variables

`GC_DATA` (données, défaut `./data`) · `GC_SITE` (source du site) · `GC_NOTEBOOK` (notebook) · `GC_AUTOGEN=1` ·
`GC_ADMIN_KEY` (sauvegardes) · `GC_DEMO_AT` (ISO ou `auto` : décale l'horloge, pour une démonstration) · `PORT` ·
`GC_MOTEUR_DIR` (dossier qui contient `moteur/`, mis par `generer_semaine.py`) · `GC_DECISIONS=0` (notebook : décisions
de passe du bloc A coupées, moteur V21 ; allumées par défaut) · `GC_BLOC_B=0` (intelligence du QB coupée : bloc A) ·
`GC_BLOC_C=0` (intelligence des receveurs et des défenseurs coupée : moteur V23) · `GC_BLOC_D=0` (plan de jeu et adaptation
en match du bloc D coupés : moteur V24) · `GC_BLOC_E=0` (progression des joueurs coupée : rosters de base chaque semaine,
moteur V25) · `GC_DOMAINE` (domaine du site, ex. `snapline.live` : l'adresse `*.up.railway.app` y est redirigée,
README section 39) · `GC_GOOGLE_VERIFY` (balise de vérification Google Search Console, facultative,
README section 46) · `GC_ADSENSE_CLIENT`, `GC_ADSENSE_SLOTS` (publicités) · `GC_EDITEUR`,
`GC_EDITEUR_ADRESSE`, `GC_CONTACT` (mentions légales de `/legal`), README section 47.

## Test

`python3 -m unittest discover -s moteur/tests -t .` (≈ 1 min) — modules ENGINE INTELLIGENCE, pauses, alerte du calcul
du samedi et **serveur** (`moteur/tests/test_serveur.py`, fastapi requis : sinon sautés). Le serveur tourne sur une copie
des données, horloge déplacée à des moments choisis de la semaine la plus récente : aucune fuite (actions à l'heure,
pauses comprises ; ni score ni action future dans `/api/delta`, `/api/feed`, la page), résultat = score du moteur,
playoffs et champion révélés au bon moment, paris (simple, combiné, refus, règlement, cash-out, historique, semaine
fermée), comptes (inscription, connexion, limite d'essais, paris d'invité repris, mot de passe, admin, équipe favorite),
classements semaine / saison, `GC_DEMO_AT`, semaines enchaînées (staffs de départ = staffs ajustés de la semaine d'avant).
Ils remplacent les tests hors dépôt `tserver.py`, `tavance.py`, `taccounts.py`, `tparis2.py`, `tsearch.py`, `tadjust.py`,
perdus (11/10/2026) ; la recherche du site est testée dans le navigateur (`outils/site/test_recherche.js`).

Tests navigateur (site, audio, recherche, pauses) : `bash outils/site/tests_navigateur.sh` (section 38).

## Limites (prototype)

Un seul processus ; SQLite ; pas de vrais comptes (effacer les données du site perd l'accès) ; pas de limite de
requêtes ; un pari en direct est pris au prix de la dernière action **jouée** (le bulletin propose alors la nouvelle cote).
