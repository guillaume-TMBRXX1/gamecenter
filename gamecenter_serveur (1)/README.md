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
- **Exhibition** (retirée le 28/10/2026, section 78) : `outils/exhibition/simuler_exhibition.py` jouait avec les décisions (`--sans-decisions` : moteur V21).
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
- Action « GameFeeds d'exhibition » (`outils/exhibition/gamefeeds.py`, retirée le 28/10/2026, section 78) : GameFeeds du moteur complet (notes et staffs de
  la dernière semaine ; depuis le 17/10/2026 jusqu'à la dernière cellule 12.2, voir section 59) dans un artefact, à
  charger sur le site (« Load GameFeed »).

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
  paris en ligne ni Insights). Après un changement de rendu de `gamecenter_source.html` : `python3 outils/regen427.py`
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
scores » : seulement les semaines terminées) ; la semaine 1 (4 franchises) est incluse (**changé le 14/10 : History
part de la semaine 2, section 52**) ; transformations et retours
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
  python outils/video/faire_video.py chiffres [--semaine …]            # le match hors norme de la semaine (≈ 40 s)
  python outils/video/faire_video.py franchise [--semaine …]           # la franchise de la semaine (≈ 25 s)
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
- **Match hors norme et franchise (étape 8.6 b, 13/10)** : `faire_video.py chiffres` (≈ 40 s) — le match de la semaine
  (matchs terminés) qui bat un **record de tous les temps** au moment où il est joué (total des deux équipes, puis
  points d'une équipe, puis écart ; égaler ne suffit pas), sinon le plus gros total s'il atteint **100 points**
  (`choisir.match_hors_norme`, depuis les résultats du calendrier) ; carton du chiffre et du record d'avant, puis les
  actions du score en rafale (touchdowns d'abord, 8 au plus), puis le score final. Pas de match hors norme : pas de
  vidéo, sortie normale. `faire_video.py franchise` (≈ 25 s) — la franchise de la semaine, **ordre fixe** : les 24
  équipes par abréviation, une par semaine depuis la première semaine enregistrée (`choisir.franchise_de_la_semaine`) ;
  carton palmarès (saisons, bilan, titres, Grand Finals ; conférence, division, coordinateurs IA — le style et
  l'identité de la bible sont en français, la vidéo en anglais ne les montre pas), carton du **joueur légendaire**
  (meilleur score fantasy sur ses saisons avec elle, `moteur/histoire.py`), ses 2 plus belles actions de tous les
  temps.
- **Habillage « AI vs AI » (20/10/2026)** — **Décisions de Guillaume (20/10)** : refaire les vidéos (terrain tourné et
  rogné avec « Bigger field », qualité pas assez propre), plus dynamiques, plus « UGC » à la façon des médias sportifs,
  centrées sur les **agents IA qui jouent les matchs**, aux couleurs du site ; style validé sur un prototype de l'action
  du jour, puis appliqué à tous les formats.
  - **Cause du défaut** : sur un téléphone en portrait, « Bigger field » fait pivoter le match ; la vidéo le cliquait.
    Désormais la vue normale est forcée (`gc-theater-v1 = 0`, bouton relâché s'il est enfoncé) et un **garde-fou**
    arrête le tournage si le terrain est tourné, plus haut que large ou déplacé (`verifier`, à chaque match ouvert).
  - **Look du site** : thème sombre, fond en halos, polices Big Shoulders Display / Manrope / Azeret Mono, couleurs
    des équipes (`--t-<équipe>`), dégradé de la marque (cyan → violet → rose), panneaux en verre ; en haut un kicker
    « AI vs AI · … » à point rouge, le titre qui apparaît mot par mot ; **score bug** aux couleurs des deux équipes
    au-dessus du terrain (le titre du résumé et du match hors norme devient l'affiche : le score est dans le bug).
  - **Le journal de l'IA** (panneau sous le terrain, dans la zone sûre) : « AI OC <coordinateur> » de l'attaque, puis
    jusqu'à 3 lignes tapées à la machine avec curseur, tirées du GameFeed — 4e essai (probabilité de victoire en
    tentant / en bottant), lecture de la boîte et audible, « DEF AI keyed on the run (…) » et tendance cassée (étape
    5), l'appel (concept, formation, couverture) ; la **lecture du QB** (cible n° x, couverture, temps de lancer,
    pression) ne s'écrit qu'au snap ; chaque ligne tient sur une ligne (la police rétrécit, polices chargées avant
    la mesure) ; barre de probabilité de victoire qui bascule au résultat, score du bug qui saute quand il change.
  - **Dynamique** : le mot du résultat en gros (« TOUCHDOWN », « PICKED OFF », « +34 », « CONVERTED »…) avec flash,
    zoom et secousse du terrain et un impact sonore (`hit`) ; au ralenti (0,5×), l'avant-snap est sauté ; cartons
    animés (entrée, chiffres qui montent). Animations sur `requestAnimationFrame` sous horloge pilotée (même rendu à
    chaque tournage).
  - **Qualité** : `crf 14`, débit max 24 Mbit/s, image clé toutes les secondes (≈ 4 Mbit/s au lieu de 0,7) ; action
    du jour ≈ 21 s (33 avant), tournage ≈ 2 min (8 avant). **Couverture** : `videos/<nom>-cover.jpg` (image à 1,2 s :
    titre posé, terrain visible), à choisir comme couverture sur TikTok.
  - **Textes** : kickers « AI vs AI · play of the day / best play so far / game in 60 seconds / player of the week /
    road to the title / franchise story », « every call made by an AI coach », présentation « No human calls a single
    play », carton final « 24 AI coaches · 1 league · live » ; toujours **aucun mot de paris** (test).
- **Automatique** : `.github/workflows/videos.yml` (« Vidéos ») tous les soirs à 22 h 30 UTC — l'action du jour ; le
  dimanche, en plus, le **résumé court** du plus beau match de la semaine, le **champion** et le **joueur de la
  semaine** ; le mercredi, le **match hors norme** (s'il y en a un) ; le vendredi, la **franchise** (limite du job :
  90 min). Les vidéos ne vont
  **pas** dans le dépôt : onglet Actions → l'exécution → **Artifacts** → `videos-<jour>` (zip, gardé 30 jours), puis
  publication à la main. À la demande : Actions → « Vidéos » → *Run workflow* (type `action`, `resume`, `long`,
  `meilleure`, `presentation`, `joueur`, `champion`, `chiffres` ou `franchise` ; jour, match).
- **Référencement** : titre et description en anglais, adresse canonique `https://snapline.live/`, Open Graph et Twitter
  (aperçu des liens partagés, image `/og.png` 1200×630 faite par `outils/site/faire_og.js`), JSON-LD `WebSite`,
  `/robots.txt` (tout sauf `/api/`) et `/sitemap.xml`. Texte **« What is Snapline? »** en bas de l'accueil (lisible par
  les moteurs). Bouton **Share** sur le grand écran d'un match de la saison : feuille de partage du téléphone, sinon le
  lien `/?watch=<match>` est copié (il rouvre ce match).
- **Icône de l'onglet et de Google (favicon, 14/10)** : le logo sur son **dégradé** (celui de l'en-tête, de `/og.png`
  et de TikTok), déclaré dans la page d'accueil et `/legal` (`<link rel="icon">` : `/favicon.ico` 16-32-48,
  `/icons/favicon.svg`, `/icons/favicon-192.png`), fait par `node outils/site/faire_favicon.js` (à relancer seulement
  si le logo change). L'icône de l'**écran d'accueil** du téléphone (`icon-180/192/512`, manifeste) reste **bleu-vert**
  (choix du 14/10). Google remplace son globe après un nouveau passage : Search Console → *Inspection de l'URL* →
  `https://snapline.live/` → *Demander l'indexation* (quelques jours, parfois quelques semaines). Test :
  `moteur/tests/test_favicon.py`.
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
  de la semaine, champion après la finale seulement, titres ; étape 8.6 b : record battu ou 100 points, franchise de la
  semaine, joueur légendaire), `outils/site/test_visibilite.js` (groupe site : balises, robots, plan
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

### 49. Fin de match dans le grand écran (14/10/2026)
**Demande de Guillaume (14/10)** : une fois un match terminé dans le grand écran, en direct ou en replay, laisser le
résultat et les statistiques jusqu'à ce que l'on quitte le grand écran ; ne pas relancer le replay.
- **Constat** : le direct et les replays ouverts depuis le calendrier restaient déjà sur l'écran final (vérifié :
  3 min en direct ; `test_pauses.js`). Seul le match **« Prime Time » de l'accueil** (replay en boucle sur sa tuile)
  recommençait à zéro 12 s après le coup de sifflet final (`RP_FINAL`) quand il était ouvert en grand écran.
- **Correctif** (`stepReplay`) : dans le grand écran, un match terminé reste sur son écran final (résultat, joueur du
  match, statistiques), le replay s'arrête ; à la fermeture du grand écran (`closeModal`), la tuile Prime Time reprend
  sa boucle au début. Le bouton lecture de l'écran final relance toujours le replay si on le demande. La cellule 427 du
  notebook n'a pas de grand écran : rien n'y change.
- **Test** : `outils/site/test_fin_de_match.js` (groupe site de `tests_navigateur.sh`).

### 50. Statistiques d'audience : Cloudflare Web Analytics (14/10/2026)
Pour mesurer l'audience réelle (visiteurs uniques, pays, pages, sources) avant de décider des offres payantes.
Cloudflare Web Analytics ne pose **aucun cookie** et n'identifie pas les visiteurs : pas de consentement à demander.
- **Rien ne change tant que `GC_CF_ANALYTICS` n'est pas posé.** Avec lui, le script
  `static.cloudflareinsights.com/beacon.min.js` est ajouté dans le `<head>` de `/` et de `/legal`.
- **Obtenir le jeton** : dash.cloudflare.com → *Analytics & Logs* → *Web Analytics* → *Add a site* → `snapline.live` →
  choisir l'installation par **JS snippet** (pas l'injection automatique, pour ne pas compter deux fois) → copier la
  valeur `token` (32 caractères hexadécimaux) → variable Railway `GC_CF_ANALYTICS`. Un jeton mal formé est ignoré.
- La page `/legal` décrit ces statistiques (section *Audience statistics* et *Services we use*).
- Tests : `moteur/tests/test_publicites.py` (`test_statistiques_cloudflare`).

### 51. Onglet « Ranking » : classement des joueurs de la semaine, poste par poste (14/10/2026)
Demande de Guillaume (14/10) : le classement de la fiche joueur (« Season rank ») pour tous les postes, sur la semaine en
cours seulement (History › Records garde toutes les semaines).
- **Site** : bouton **Ranking** dans la barre latérale (sous Standings ; « Ranking » dans la recherche sur mobile). Un
  onglet par poste — QB, RB, WR, TE, EDGE, DT, LB, CB, S, K — classé dans la statistique du poste : yards à la passe (QB),
  à la course (RB), en réception (WR, TE), sacks (EDGE, DT), plaquages (LB, CB, S), field goals réussis (K). Colonnes
  utiles du poste ; un joueur qui a joué sans rien dans la statistique clé est en bas, sans rang (« — »). Un clic sur
  une ligne ouvre la fiche joueur.
- **Mise à jour** : match par match, dès qu'un match se termine (pas seulement à 22h15) ; calcul dans la page, depuis
  les GameFeed déjà chargés (`seasonAgg`, comme « Season leaders »), rien de nouveau côté serveur.
- **Fiche joueur** : « Season rank » compte maintenant **parmi les joueurs du même poste** (avant : tous postes
  confondus, p. ex. des QB et des WR dans les yards à la course), pour donner le même rang que l'onglet ; les kickers ont
  aussi le leur (field goals).
- **Tests** : `outils/site/test_classement.js` (groupe site : barre latérale, onglets, rangs et stat clé décroissante,
  meilleur QB = leader de History calculé par le serveur, fiche joueur au même rang, recherche, mobile 390 px).

### 52. History part de la semaine 2 (14/10/2026)
Demande de Guillaume (14/10) : la semaine 1 n'avait que 4 franchises, qui ont donc joué une saison de plus que les 20
autres — titres, bilans de franchise, records et carrières en étaient faussés.
- **Serveur** : `league_history` (`serveur.py`) ne prend que les semaines d'index ≥ `HIST_DEPUIS` (variable
  `GC_HIST_DEPUIS`, **défaut 2** ; `1` pour tout reprendre). Tout ce qui est calculé à partir de plusieurs semaines suit :
  Seasons, Franchises (titres, finales, bilans de toujours), Records (un match, une saison, carrière) et la section
  Career de la fiche joueur (lignes, total, rang de toujours). `/api/league/history` renvoie `since_week`.
- Rien n'est supprimé : `data/weeks/week_2026-09-28` reste sur le disque, la semaine 1 n'est simplement plus comptée.
- Ranking, Season leaders et « Season rank » de la fiche joueur ne portaient déjà que sur la semaine en cours.
- **Site** : l'en-tête de History dit « counted from week 2 (week 1 had only 4 franchises) » ; les notes « All weeks »
  deviennent « From week 2 ».
- **Tests** : `outils/site/test_histoire.js` (une saison par semaine à partir de la 2, aucun record, titre ni ligne de
  carrière de la semaine 1, en-tête).

### 53. Horloge réelle et valeur des décisions (notebook 12.2 quaterdecies, 14/10/2026 — allumées)
Feuille de route : « moteur plus intelligent », idées 1 et 2. Modules `moteur/horloge.py` et `moteur/valeur.py` (tests
`test_horloge.py`, `test_valeur.py`), cellule **12.2 quaterdecies** du notebook. **Décision de Guillaume (14/10)** :
quarts-temps de 15 min, retransmission ≈ 18 min, 4e essai tel quel mais réaliste selon la situation du match.
**Allumés** ; `GC_HORLOGE=0` / `GC_VALEUR=0` : moteur d'avant à l'identique (contrôlé) ; `GC_QUART` : longueur du
quart-temps (900).
- **Horloge réelle** : l'horloge tourne entre les actions (huddle 36 s, hurry-up 16 s, tuer l'horloge 40 s, ± le tempo du
  coordinateur) ; elle s'arrête sur une passe incomplète, un changement de possession, une sortie du terrain dans les
  2 dernières minutes du Q2 et les 5 dernières du Q4, l'avertissement des 2 minutes, un temps mort ; temps morts (3 par
  mi-temps) de l'équipe menée et de l'attaque en fin de Q2 ; genou (victory formation, fin de Q2 dans son camp) ; spike ;
  « fire drill » (l'unité de field goal entre en courant). Le temps entre deux actions est compté dans la durée de
  l'action qui précède : le GameFeed garde une horloge continue (audit inchangé).
- **Valeur des décisions** : points attendus et probabilité de victoire mesurés sur 597 matchs du moteur ; 4e essai
  (jouer / field goal / punt) partout sur le terrain, au meilleur choix à un biais d'identité près (agressivité du
  coordinateur, prudence dans son camp). **Situation du match** : menée, l'équipe perd sa prudence au fil du dernier
  quart-temps (en prolongation, aucune) ; l'équipe qui a déjà gagné garde la règle d'avant (garbage time) ; dans les
  dernières secondes, l'équipe menée suit la fin de période (section 22, action par action : « il faut un touchdown ») ;
  un field goal choisi par la fin de période est gardé. Correctif : la fin de période jouait tous les 4e essais d'une
  équipe qui mène (elle ne voit pas le ballon rendu) — c'est maintenant la valeur qui décide.
- **GameFeed** (additif) : `play.clock` (`runoff`, `stop`, `timeout`, `oob`, `timeouts`), `play.fourth_down` (`choice`,
  `model`, `wp`, `conversion`, `bias`, `reason`), `call.play_id` `KNEEL` / `SPIKE`, `game.clock_model`. **Site** :
  « goes for it on 4th (…) », « timeout VEC », « two-minute warning » dans le play-by-play (`rpClockNote`, cellule 427
  comprise). Le site lit déjà la longueur du quart-temps dans le GameFeed (`quarter_seconds`).
- **Mesures** (552 à 1 104 matchs, 24 franchises ; retransmission = actions × 6,5 s + pauses) :

  | | Moteur actuel (quarts de 3 min) | Horloge réelle + valeur (quarts de 15 min) |
  |---|---|---|
  | Actions offensives · points · drives | 130,6 · 54,2 · 22,6 | 134,2 · 54,9 · 23,1 |
  | Retransmission moyenne (5 % – 95 %) | 18,1 min (15,6 – 20,7) | 18,4 min (15,9 – 21,4) |
  | Genoux · spikes · temps morts / match | 0 · 0 · 0 | 1,9 · 0,5 · 6,5 |
  | Q4, attaque qui tue l'horloge : passes | 44 % | 38 % |
  | 4e et 1 entre ses 30 et le milieu : joués | 42 % | 44 % (AEG 6 % … GMB 100 % sur 4e et 1-3) |
  | 4e et 4-6 entre les 35 et les 10 adverses : joués | 18 % | 47 % |
  | Dernière action d'un Q2 / Q4 à portée : field goal | 75 / 266 | 75 / 239 |
  | Calcul | 229 ms / match | 251 ms / match (+ 10 %) |

  Calibration (1 104 matchs, tolérances de `rapport_calibration.py`) contre le moteur actuel : tout dans les tolérances
  sauf yards / course − 0,22 (± 0,2) — les genoux comptent comme des courses de − 1 yard ; hors genoux − 0,02.
  Molette de la durée : huddle 28 s -> 154 actions, 20,9 min, 59 points ; 36 s -> 18,4 min ; 46 s -> 114 actions,
  15,8 min, 44 points. Variante écartée : l'horloge réelle dans des quarts de 3 min (× 0,2) -> 80 actions, 11,5 min,
  31 points (toutes les stats et les records d'un match baissent de 40 %).
- **Cotes en direct (13.4, garde-fou 4)** : avec les paramètres V21, la fin de match gérée faisait mentir le modèle
  (extrêmes ± 0,071, outsiders en direct + 31 %). Même modèle, paramètres `LIVE_*` ré-ajustés quand l'horloge est
  allumée (13.1 ; maximum de vraisemblance sur 1 433 matchs, graines 3 100 000 +) : 13.4 (graines 4 000 000 +, 50
  simulations par affiche) ✅ extrêmes ± 0,023, écart moyen 0,028, outsiders + 1,2 % (90 % : − 8,7 % à + 12,1 %).
- **Semaine du 19/10 produite** (`generer_semaine.py`, notebook complet, sur une copie de `data/`) en **29,5 min** (machine
  de 4 cœurs ; étape 6 : 32 min) ; `audit_moteur.py` : **0 anomalie bloquante** (alertes : seulement celles, déjà connues,
  de la semaine 1). 279 matchs, quarts de 15 min, retransmission 18,7 min en moyenne (14,8 – 23,8), 57,1 points ;
  par match : 1,8 genou, 0,6 spike, 6,2 temps morts, 4e essais 3,5 joués / 1,8 field goal / 5,0 punts.

### 54. Bloc F — intelligence du jeu de course (notebook 12.2 quindecies, 14/10/2026 — allumé)
Feuille de route : « moteur plus intelligent », idée 3. Module `moteur/course.py` (tests `test_course.py`), cellule
**12.2 quindecies** ; interrupteur `GC_BLOC_F=0` : moteur d'avant à l'identique (contrôlé).
- **Constat** (552 matchs, 28 711 courses, horloge réelle) : la course était résolue au niveau de l'équipe ; contre
  BOX_STACK 2,5 yards et 33 % de courses bloquées, contre tout le reste ≈ 6,7 yards (± 2 yards de l'intention
  défensive) ; inside 5,3 · gap 5,7 · outside 5,4 ; un WR sur jet sweep courait comme le RB1 ; ni les lignes au point
  d'attaque, ni le profil du porteur ne pesaient.
- **Ce que fait le bloc F** : boîte (5-9 défenseurs : formation, appel, paquet, front) ; côté choisi par l'attaque (le
  meilleur duel, 65 %) ; duels de ligne au point d'attaque par rapport à la moyenne de chaque ligne ; front contre la
  classe de course ; trou ouvert / étroit / fermé ; lecture du porteur (cutback, rebond, bloqué) ; contact (plaqueur
  crédité = défenseur au contact, yards après contact) ; RB2 contre RB1. **Profils, jamais niveaux** : le niveau est dans
  les notes d'unité du tirage du moteur (une première version comptait la puissance et le tackling en absolu : MNL
  montait à 76 % de victoires).
- **Mesures** (mêmes graines) : contre BOX_STACK 2,5 → 4,1 yards, contre Cover 3 6,7 → 5,9 ; boîte de 6 → 8 :
  6,6 → 4,6 ; 3e et 11+ : 7,3 → 5,9 ; courses bloquées 16 % → 15 %, 10+ 20 % → 19 % ; trou ouvert 6,9 · fermé 4,5
  (cutback 6,6 · bloqué 2,8). Calibration (1 104 matchs, contre le moteur sans bloc F) : tout dans les tolérances
  (yards / course + 0,04, points + 0,02). Équilibre (4 416 matchs) : 39,8 – 59,8 % (sans : 40,1 – 56,4 %).
  Calcul : + 5 % par match.
- **Cotes en direct** : 13.4 trouvait les outsiders trop payés (− 15 %, extrêmes ± 0,037 : moins de retournements) ;
  `LIVE_*` ré-ajustés pour « horloge + bloc F » (13.1) : ✅ extrêmes ± 0,023, écart moyen 0,011, outsiders − 4,6 %.
- **Semaine du 19/10 produite** (notebook complet, copie de `data/`) : 30,4 min ; audit : 0 anomalie bloquante ;
  retransmission 18,6 min ; 5,71 yards / course ; 18 % de courses bloquées, 7,6 % de cutbacks.
- **GameFeed** (additif) : `play.run` = {box, side, hole, read, contact, tackler, front, key_block}. **Site** :
  « 8 in the box », « cutback », « bounced outside », « stuffed at the line », « breaks a tackle at the line » dans le play-by-play (cellule 427 comprise) — la lecture affichée est réconciliée avec le gain final (une course « bloquée » qui gagne 4 yards ou plus a cassé un plaquage ; 2-3 yards : course « designed » ; un cutback ou rebond à moins de 2 yards : « designed »).

### 55. Punts avec retour, course dessinée, horloge continue, fin de match (14-15/10/2026)
Retours de Guillaume sur l'exhibition GMB–MNL du 14/10 : retours de punt absents, course pas dessinée, horloge illisible
(« on ne s'y retrouve pas »), field goals de 63-64 yards à la suite en fin de match.
- **Punt avec retour** (module `moteur/punt.py`, tests `test_punt.py`, notebook **12.2 sexdecies**, `GC_PUNT=0` : moteur
  d'avant) : longueur selon le punter (≈ 46,5 yards bruts, ≈ 42 nets) ; près du terrain adverse, punt de précision vers la
  ligne des 10 ; touchback, fair catch, ballon arrêté par la couverture, sortie, ou retour du retourneur (le plus rapide
  des WR2, WR3, RB2) contre les équipes spéciales ; touchdown sur retour (6 points, transformation du receveur, puis son
  coup d'envoi). 400 matchs : 2 010 punts — retours 40 %, fair catches 32 %, arrêtés 13 %, sorties 10 %, touchbacks 5 %,
  3 touchdowns. `valeur.PUNT_NET` (4e essai) mesuré sur ce punt. 11.1 garde `points_against` / `same_offense_next`.
  GameFeed : `play.punt_return = {kick, landing, result, return, td, catch, pinned, returner}` ; touchdown sur retour :
  résultat `punt`, 6 points au receveur, `try_follows`. Site : animation (le retourneur attrape et remonte, fair catch,
  rebond et gunner), bannières, Match centre (« Punt return yards », tableau « Punt returns »), commentaire, sons. Audit et
  vidéos : touchdown sur retour de punt.
- **Course dessinée** (bloc F) : le placement latéral (11.6) suit le côté du bloc F (cutback : de l'autre côté ; rebond :
  près de la touche) ; le site place au snap autant de défenseurs dans la boîte que le moteur, ouvre ou ferme le trou,
  dessine la lecture du porteur (cutback, rebond, bloqué, plaquage cassé) et met l'anneau rouge sur le plaqueur du bon
  niveau (ligne, linebackers, secondaire).
- **Horloge continue** (module `moteur/ecran.py`, tests `test_ecran.py`, notebook **12.2 octodecies**, `GC_ECRAN=0`) :
  chaque action a son temps d'écran — avant le snap, le chrono des 40 s utilisé, accéléré 26 fois (l'horloge du match
  tourne avec lui si elle tournait) ; l'action (animations × 0,8) ; l'après. ≈ 15 min par match, pauses comprises (avant
  ≈ 18,5). GameFeed : `play.show = {sec, pre, act, post, c0, pt, pc, to}`, `game.broadcast`. Serveur (`play_sec`) et site
  (`psec`, `tlOf`) révèlent chaque action à la fin de son temps d'écran ; sans `play.show` : 6,5 s comme avant. Site :
  horloge qui s'écoule en continu (arrêtée sur incomplète, sortie, changement de possession, temps mort), **chrono des
  40 s** à côté (25 après un temps mort, un changement de possession ou un quart-temps ; rouge sous 5 s : ce qu'il reste au
  snap dit si l'équipe a pressé ou tué le temps), **temps morts restants** sous chaque équipe, bannière TIMEOUT.
- **Fin de match** : `moteur/field_goal.py` (partagé par le moteur des franchises — 12.2 septendecies —, `fin_de_periode`
  et `valeur`) : jusqu'à 60 yards inchangé ; au-delà 40 % à 61 yards puis − 6 points par yard, 2 % après 67 (avant : 45 %
  jusqu'à 70 yards) ; `horloge.genou` : à égalité au Q4, dans son camp, moins de 20 s : genou.
- **FRG** (décision de Guillaume du 15/10) : lignes offensive et défensive 87 → 86 (59,6 % de victoires sur 736 matchs →
  58,4 %).
- **Tests 12.3 / 13.2** : chaque affiche a ses propres graines (`_balance_seed`) — les 4 mêmes graines pour les 552
  affiches valaient 4 tirages (une même graine donne des matchs semblables quelle que soit l'affiche : 64,8 points par
  match pour la graine 50 003, 52,5 pour la 50 000) ; sur main, 13.2 échouait (over 57,1 %).
- **Cotes en direct** (13.1) : `LIVE_HOME` (1 point d'avantage du terrain qui s'efface avec le temps : la valeur de la
  possession pesait d'emblée contre le domicile, qui ne reçoit pas le coup d'envoi) et `LIVE_*` ré-ajustés sur 1 433
  matchs : 13.4 passe (écart moyen 0,035 → 0,020 sur son échantillon).
- **Tests navigateur** : `test_punts.js`, `test_courses.js`, `test_horloge.js` (groupe site).

### 56. Match en temps réel : quarts-temps de 4 min, chrono de 10 s, temps morts de 15 s (15/10/2026)
Retour de Guillaume sur l'exhibition GMB–MNL (section 55) : « les actions vont trop vite. L'horloge doit s'écouler
normalement et en temps réel » — 4 quarts-temps de 4 min, délai d'avant-snap de 10 s au plus, 3 temps morts de 15 s par
équipe et par mi-temps, moins de 30 min par match ; l'horloge s'arrête sur une passe incomplète, une sortie du terrain,
un temps mort, un changement de phase et les cas particuliers, et tourne sinon ; les receveurs ne sortaient jamais du
terrain (« il retourne toujours vers l'intérieur »). Choix de Guillaume : moins d'actions (≈ 100 au lieu de ≈ 160) et
moins de points, pauses de 10 s entre les quarts-temps et de 40 s à la mi-temps (inchangées).
- **Format** : quarts-temps de **240 s** (`GC_QUART`, 12.2 quaterdecies ; 900 avant). Le **changement de format** se voit
  dans les chiffres de la ligue : ≈ 114 actions par match (coups d’envoi et transformations compris ; ≈ 160 avant),
  ≈ 40 points (≈ 55 avant), ≈ 11 sorties du terrain et ≈ 5 temps morts par match. Les cotes (13.1-13.4), l'équilibre
  (12.3) et les contrôles passent sans réglage : ils se calibrent sur les matchs du moteur. Exécution complète du
  notebook (15/10) : équilibre 39,1 – 58,2 % de victoires sur 2 208 matchs ; 13.4 : écart moyen 0,018 sur 929 matchs ;
  12.2 octodecies (96 matchs) : 25,2 min à l'écran en moyenne (22,6 – 28,0), 115 actions, chrono à 3,4 s au snap en
  moyenne, 4,5 temps morts par match ; semaine 1 exportée et validée (279 GameFeed).
- **Moteur** (`moteur/horloge.py`, format temps réel dès qu'un quart-temps fait 300 s ou moins) : entre deux actions,
  l'horloge tourne de **9 s** en rythme normal, **4 s** en hurry-up, **10 s** pour tuer l'horloge (et au genou) — jamais
  plus que le chrono de 10 s ; une **sortie du terrain arrête toujours l'horloge** (avant : seulement dans les 2
  dernières minutes du Q2 et les 5 dernières du Q4) ; receveurs et porteurs cherchent davantage la touche (24 % des
  passes complétées, 10 % des courses ; 16 % / 8 % avant). Avertissement des 2 minutes à 32 s du terme (à l'échelle),
  fire drill, genou, spike : inchangés.
- **Retransmission** (`moteur/ecran.py` **ecran-2**, 12.2 octodecies) : **une seconde d'écran = une seconde de match**.
  Avant le snap, l'horloge (si elle tournait) et le chrono des 10 s descendent ensemble ; horloge arrêtée : le chrono
  seul, au rythme de l'attaque (5 s utilisées en rythme normal, 3 pressée, 8 qui tue le temps) ; temps mort : **15 s de
  décompte**, puis le chrono ; pendant l'action, l'horloge s'écoule du temps de jeu du moteur, au rythme réel (si
  l'action dure plus que l'animation, elle continue juste après) ; pause après l'action seulement horloge arrêtée (3 s
  après un score ou une perte de balle). **Durée garantie ≤ 28 min**, pauses comprises (≈ 25 min en moyenne, de 22 à
  28) : au-delà, seuls les temps horloge arrêtée qui ne sont pas fixés par la règle (chrono utilisé, pauses, mise en
  place des coups de pied) sont raccourcis ; l'horloge et les temps morts restent en temps réel. Les coups d'envoi
  restent espacés de 30 min. GameFeed : `play.show` gagne `tw` (secondes de temps mort) et `rt` (temps réel).
- **Sortie du terrain** : l'action finit **sur la touche** (12.2 octodecies : `end_y` à 0,6 yard de la ligne, mêmes
  tirages du placement latéral ; le ballon suivant part de la hash mark de ce côté). Site : le porteur ou le receveur file
  vers la touche et la franchit, bannière « +7 PASS · OUT OF BOUNDS » ; dans le terrain, le receveur ne revient plus vers
  l'intérieur que d'un yard (plus sur une longue course après la réception).
- **Site** : horloge et chrono à 1 s par seconde, « TO :15 » à la place du chrono pendant un temps mort (jaune), chrono en
  rouge sous 3 s. Test navigateur `test_horloge.js` : horloge à 1 s par seconde quand elle tourne, chrono de 10 s,
  décompte de temps mort, sorties sur la touche, match rejoué en moins de 30 min.
- **Exhibition** `exh-v38-gmb-mnl` (remplace `exh-v37`) : MNL 22 @ GMB 19, 121 actions, 11 sorties du terrain, 2 temps
  morts, 2 genoux, 6 4es essais joués ; 25 min à l'écran (pauses comprises).

### 57. Rythme rapide : chrono d'avant-snap 7 / 8-10 / 0-1 s, sorties vers l'extérieur, ≈ 20 min (16/10/2026)
Retour de Guillaume sur l'exhibition en temps réel (section 56) : « les actions sont trop lentes ». Pas besoin de temps
réel : une dynamique rapide et nerveuse (le rythme des matchs de la semaine), ≈ 20 min par match et jamais plus de 25 ;
on garde le chrono d'avant-snap, les temps morts et l'horloge qui tourne sauf cas particuliers, sans qu'elle accélère
trop. Chrono au snap : ≈ 7 s restantes en situation classique, 8, 9 ou 10 en hurry-up (no huddle), 1 ou 0 pour tuer
l'horloge. Sorties du terrain : seulement quand le QB lance vers un receveur extérieur (ou près de la touche) — dans
l'exhibition, un receveur attrapait le ballon au milieu du terrain et piquait à 90° vers la touche.
- **Moteur** (`moteur/horloge.py`, quarts-temps de 240 s inchangés) : secondes de chrono utilisées entre deux actions,
  tirées dans le flux « chrono » : **2-4** en situation classique (≈ 7 restantes), **0-2** en hurry-up, **9-10** pour
  tuer l'horloge, 10 au genou ; l'horloge du match tourne d'autant. **Sortie du terrain** (`horloge.vers_la_touche`) :
  passe vers un receveur extérieur (WR1 / WR2) sur une route qui ne rentre pas, route vers l'extérieur (out, corner,
  flag, flat…), course vers l'extérieur (sweep, toss, outside zone, rebond du bloc F) — 40 % de ces passes complétées
  et 30 % de ces courses sortent ; jamais un slant, un drag, un receveur du slot au milieu, une course intérieure.
  ≈ 153 actions et ≈ 54 points par match (≈ 140 actions, quarts de 3 min, pour les matchs de la semaine du 12/10 ;
  ≈ 115 et ≈ 42 en temps réel), ≈ 7 sorties du terrain et ≈ 4 temps morts par match.
- **Retransmission** (`moteur/ecran.py` **ecran-3**) : avant le snap, le chrono (et l'horloge du match quand elle
  tourne) descend **1,1 fois plus vite** que le temps réel, au moins 1,2 s ; horloge arrêtée : le chrono seul, au rythme
  de l'équipe (1, 3 ou 9 s utilisées) ; temps mort : décompte de **15 s montré en 4 s** ; l'action (≈ 3,3 s une course,
  3,8 une passe, ± 10-15 % selon son temps de jeu) écoule le temps de jeu — en médiane l'horloge perd ≈ 1,2 s par
  seconde d'écran quand elle tourne ; 0,8 s après l'action, 2 s après un score ou une perte de balle. **≈ 20 min par
  match** (120 matchs : 20,0 en moyenne, de 16,9 à 24,5), **plafond 24 min 30** pauses comprises (au-delà, seuls les
  temps horloge arrêtée sont raccourcis). GameFeed : `play.show` = `{sec, pre, act, post, c0, pt, pc, to, tw, tl}`
  (`tl` : secondes de temps mort affichées).
- **Site** : décompte du temps mort lu dans `show.tl` ; `test_horloge.js` (ecran-3) : l'horloge n'accélère pas trop
  (médiane ≤ 2,2 s de match par seconde, aucun pas au-delà de 3,2), chrono de 10 s, « TO :15 », sorties sur la touche,
  match rejoué en moins de 25 min.
- **Exhibition** `exh-v39-gmb-mnl` (remplace `exh-v38`) : MNL 27 @ GMB 27, 159 actions, 8 sorties du terrain, 6 temps
  morts ; 20 min à l'écran (pauses comprises).

### 58. Checks avant le snap : le QB lit la défense, la défense répond aux motions (notebook 12.2 novodecies, 16/10/2026 — allumés)
Feuille de route : « moteur plus intelligent », étape 4. Module `moteur/presnap.py` (tests `test_presnap.py`), cellule
**12.2 novodecies** (avant la retransmission 12.2 octodecies) ; interrupteur `GC_PRESNAP=0` : moteur d'avant à
l'identique (contrôlé). **Décisions de Guillaume (16/10)** : allumé par défaut ; la fréquence des audibles est d'abord
l'identité de la franchise (haute pour certaines, basse pour celles qui jouent leur jeu), 4-8 par match comme socle ; le
check du QB et la motion doivent se voir sur le terrain.
- **Avant** : le jeu appelé dans le huddle était joué quoi que montre la défense ; les déguisements de l'extension
  (`presente`, `deguisement`, 12.2 decies) ne trompaient que la lecture du QB après le snap ; une motion n'appelait
  aucune réponse.
- **Réponse à la motion** (profil défensif, flux `presnap-def`) : **roll** (un safety tourne vers la motion : un défenseur
  de plus dans la boîte de la course, la coquille se dévoile), **lock** (homme : le défenseur suit, le QB sait que c'est
  de l'homme), **bump** (zone : on se passe le joueur, la motion ne dévoile plus rien et donne moitié moins de
  séparation en homme).
- **Lecture du QB** : la défense montre une boîte et une coquille ; un paquet déguisé ment (« 2-high rotating » : un
  défenseur de moins, le safety descend au snap ; « mug » : un ou deux de plus, ils reculent au snap). Le QB voit au
  travers selon son **awareness** et sa **lecture de couverture** (bloc B), moins le déguisement (réduit par la motion et
  le shift) ; roll / lock lui dévoilent tout. Vu au travers : moitié moins d'erreurs de lecture dues au déguisement
  après le snap.
- **Audible** (flux `presnap`, `presnap-jeu`) : course contre une boîte lue de 8 ou plus → passe rapide ; passe contre
  une boîte lue de 6 ou moins, à 6 yards ou moins → course intérieure ; même formation dans 97 % des cas. Jamais en
  tuant l'horloge (course → passe), en hurry-up (passe → course), sur 3e / 4e et 1 ou à la goal line, dans les 15
  dernières secondes, sur un RPO ou une option. **Fréquence** = liberté laissée au QB par l'identité (`LIBERTE` : de
  MNL / FRG « on joue notre jeu » à PLS, AXM, CTD, ZPH, APX) × penchant (course / passe) × awareness du QB.
  **Trompé** : il a lu la boîte montrée — mauvais audible (`wrong_check`) ou audible manqué (`missed_check`).
  **Aucun yard ajouté** : un bon audible paie par le moteur (bloc F : une course contre 8-9 rapporte 3,9-5,2 yards,
  contre 5-6 7,0-7,2 ; une passe ≈ 6,3 quelle que soit la boîte), un mauvais coûte de même.
- **Chrono** : un audible coûte **2 s** du chrono d'avant-snap (**+1** si la défense a répondu à une motion) ; l'horloge
  du match tourne d'autant quand elle tournait (le temps est compté dans l'action précédente : horloge continue) ; il
  reste toujours 1 s au snap ; une attaque qui tue l'horloge ne paie rien ; jamais à travers l'avertissement des 2
  minutes. Retransmission (`ecran.py`) : horloge arrêtée, les secondes s'ajoutent au chrono utilisé ; un avant-snap qui
  montre quelque chose (motion, audible, défense qui se décale) dure au moins 2,6 s à l'écran.
- **GameFeed** (additif) : `play.presnap = {look, box_shown, box_real, box_read, shell_shown, shell_real, read, audible,
  from, to, same_formation, fooled, motion, motion_response, sec, clock, qb}` (seulement quand il y a quelque chose à
  raconter) ; `game.presnap_model`. **Site** : sur le terrain, la défense montre sa boîte et sa coquille puis se décale
  jusqu'à la vraie au snap ; le joueur en motion traverse la formation (trace pointillée), un défenseur le suit (lock),
  la zone se décale (bump), un safety tourne (roll) ; « CHECK · RUN / PASS » au-dessus du QB quand il change le jeu.
  Play-by-play : « audible: … sees 8 in the box and checks to a pass », « — fooled: the defense showed 9 and played 7 »,
  « disguised: the defense showed 7 in the box and played 8 », « … rolls a safety with the jet motion ». Test
  navigateur `test_audibles.js` (groupe site) ; cellule 427 synchronisée.
- **Sortie du terrain d'une course** (point en suspens) : une course bloquée à la ligne ou à 1-2 yards « sortait » 25
  yards plus loin (le porteur partait du trou, au centre, et filait vers la touche). `horloge.vers_la_touche` : une course
  ne sort qu'avec 3 yards de gain (rebond : 2), jamais sur un cutback ; site : une course qui sort part vers la touche dès
  le trou, remonte le long de la ligne et la franchit.
- **Mesures** (552 matchs, mêmes graines, check coupé → allumé) : points 56,4 → 56,5, actions 126,3 → 126,1 (aucune force
  ajoutée) ; **6,0 audibles par match** (83 % vers la passe, 97 % dans la même formation) ; trompés 0,65 par match
  (mauvais audible 0,27, audible manqué 0,38) ; réponses aux motions 2,7 par match (roll 1,0, bump 1,1, lock 0,5) ;
  yards par course 5,89 → 6,08 (+ 0,19, tolérance ± 0,2) et **part des passes 60,5 → 63,6 %** (+ 3,1 points, au-delà de
  la tolérance indicative de ± 2) : c'est l'effet voulu — des courses appelées contre une boîte chargée deviennent des
  passes ; à rééquilibrer (plus d'audibles vers la course) si Guillaume le souhaite. Calcul : ≈ + 3 % par match pour le
  check lui-même (les passes en plus coûtent davantage).
- **Semaine du 19/10 produite** (notebook complet, copie de `data/`) en **32,8 min** (bloc F : 30,4 ; limite GitHub 75) ;
  `audit_moteur.py` : **0 anomalie bloquante, 0 alerte** (279 matchs, 57,1 points, 154 actions) ; **5,75 audibles par
  match** (de 0 à 20), de 0,8 % des snaps (MNL) et 1,0 % (FRG) à 7,7 % (PLS, CTD) et 9,2 % (APX) ; retransmission 20,4 min
  (17,1 – 24,5) ; 6,8 sorties du terrain par match.
- **Contrôles** (exécution complète avec contrôles, 75 min sur 4 cœurs, aucun échec) : équilibre 12.3 sur 2 208 matchs
  **39,7 % (CMT) – 59,5 % (BST)** (bloc F : 39,8 – 59,8) ; 13.2 ✅ (Brier 0,2466, biais − 0,8 %) ; **13.4 ✅ sans
  recalibrage** (extrêmes ± 0,022, écart moyen 0,015, outsiders − 11,9 %).
- **Exhibition** `exh-v40-gmb-mnl` (remplace `exh-v39`) : MNL 31 @ GMB 37, 164 actions, **9 audibles** (dont un passe →
  course : EMPTY_SHORT_OUT → EMPTY_QB_DRAW contre une boîte de 6), 10 motions et 3 réponses (roll, lock, bump), 11 sorties
  du terrain ; 21,8 min à l'écran (pauses comprises).

### 59. 4e essai plus prudent ; GameFeeds d'exhibition au moteur complet (17/10/2026)
**Demande de Guillaume (17/10)** : les franchises tentent trop souvent le 4e essai au lieu de punter — « les équipes
doivent être vraiment plus prudentes, on doit largement baisser ces pourcentages » ; réglage à appliquer avant de
régénérer la semaine du 19/10.
- **Constat** (semaine du 19/10, valeur-1) : **35 %** des 4es essais joués (3,3 par match) — dans son camp 24 %, du
  milieu aux 35 adverses 44 %, des 35 aux 20 45 %, zone rouge 58 % ; 4e et 1 80 %, 4e et 4-6 44 % ; équipes de BST 7 %
  à GMB 73 %. La conversion mesurée suit bien la table `CONVERSION` (le moteur convertit vraiment ≈ 55 % des 4e et
  4-6) : la prudence doit venir du coordinateur, pas du calcul.
- **Réglage** (`moteur/valeur.py`, `valeur-2`) : biais d'identité `BIAIS` (−2,5 ; +0,5) -> **(−5 ; +0,5)** points
  (prudent -> agressif) et `PRUDENCE_CAMP` 1,5 -> **3** points. L'agressif garde son audace (GMB joue toujours 2 4es
  essais sur 3), le coordinateur moyen punte le 4e et 1 dans son camp et prend les 3 points près de l'en-but ; menée en
  fin de match, la prudence s'efface toujours (test `test_prudence`). Essais (200 matchs, puis le test d'équilibre 12.3
  rejoué avec ses graines, 2 208 matchs) :

  | Réglage (BIAIS ; camp) | 4es joués | 12.3 : min – max |
  |---|---|---|
  | (−2,5 ; +0,5) ; 1,5 — avant | 35 % | — |
  | (−4 ; −0,5) ; 2,5 | 16 % | **35,9 % SPK** – 60,9 % CTD ❌ |
  | (−4 ; 0) ; 3 | 18 % | 36,4 % SPK – 60,3 % CTD |
  | (−6 ; +0,5) ; 2,5 | 15 % | **34,8 % SPK** – 59,0 % CTD ❌ |
  | **(−5 ; +0,5) ; 3 — retenu** | **17 %** | **37,2 % SPK – 59,8 % CTD** |

  Écarté : une audace des outsiders (l'équipe aux unités plus faibles retrouve jusqu'à 2-4 points) — elle n'aide pas
  SPK (34,8 – 40,2 %) et fait remonter les 4es essais (22-27 %) et BST (63-65 %). SPK (jeune, notes de départ plus
  basses) est la franchise que la prudence de toute la ligue coûte le plus : 45 % -> 37 % en 12.3 (sa progression du
  bloc E la fait remonter au fil des semaines).
- **Semaine du 19/10 régénérée** (`generer_semaine.py --lundi 2026-10-19`, notebook complet, sur une copie de `data/`)
  en 33,7 min ; `audit_moteur.py` : 0 anomalie bloquante (alertes déjà connues). 279 matchs : **16 % des 4es essais
  joués** (1,5 par match, avant 3,3), field goals 2,4 par match (1,7), punts 5,5 (4,4) ; 53,5 points par match (57,1) ;
  équipes de GRZ 2 % à GMB 68 %.
- **Contrôles** (exécution complète avec contrôles, 61 min sur 4 cœurs, aucun échec) : équilibre 12.3 sur 2 208 matchs
  **37,2 % (SPK) – 59,8 % (CTD)** (avant : 39,7 – 59,5) ; 13.2 ✅ (Brier 0,2464) ; **13.4 ✅ sans recalibrage** (extrêmes
  ± 0,010, écart moyen 0,016, outsiders − 12,0 %) ; 377 tests unitaires.
- **GameFeeds d'exhibition** (`outils/exhibition/gamefeeds.py`, action « GameFeeds d'exhibition ») : le chargement
  s'arrêtait à 12.2 undecies — les feeds n'avaient ni l'horloge réelle, ni le bloc F, ni les punts avec retour, ni la
  fin de match, ni les checks avant le snap, ni la retransmission (`play.show`). Il va maintenant jusqu'à la dernière
  cellule 12.2 avant 12.3 (aujourd'hui 12.2 octodecies, trouvée toute seule : une nouvelle cellule du moteur sera
  prise sans retoucher le script). Les feeds partent des notes et staffs de la dernière semaine de `data/weeks` : ce
  sont des matchs du moteur à jour, hors calendrier. Action GitHub : 552 affiches en ≈ 13 min, artefact
  « gamefeeds-exhibition ».

### 60. Fumbles disputés : l'attaque garde le ballon une fois sur deux (notebook 12.2 vicies, 19/10/2026 — allumé)
**Demande de Guillaume (19/10)** : « l'équipe adverse ne doit pas toujours récupérer le ballon » — 50/50 : la moitié
du temps la défense récupère et prend la possession ; sinon l'équipe qui a perdu le ballon le récupère et on passe au
down suivant là où il a été récupéré.
- **Avant** : un fumble resté en jeu (12.2 quater en efface 30 %, `ADAPT_TURNOVER_KEEP`) était toujours perdu.
- **Maintenant** (cellule **12.2 vicies**, juste avant 12.3) : chaque fumble est disputé — la défense le récupère 1 fois
  sur 2 (`FUMBLE_RECUP_DEFENSE`), perte de balle comme avant ; sinon l'attaque le garde, par le porteur lui-même 4 fois
  sur 10 (`FUMBLE_RECUP_SOI`). L'action redevient une course, un sack ou une passe complétée arrêtée sur place : down
  suivant (au 4e essai raté, ballon rendu sur downs ; récupéré dans son propre en-but : safety, règle NFL). Tirage dans
  un flux dédié (« fumble-recuperation ») : le hasard du moteur n'est pas consommé. Interrupteur `GC_FUMBLE=0` : moteur
  d'avant à l'identique (contrôlé). Non modélisé : le fumble provoqué n'est crédité au défenseur que si la défense
  récupère (comme avant).
- **GameFeed** (additif) : `play.fumble` = {`lost`: false, `by`, `recovered_by` : `self` | `team`, `team`}, texte de
  l'action « Malachi Reed fumble, recovered, +3 » (40 caractères au plus) ; `game.fumble_model`. Les fumbles perdus
  restent `fumble_lost`. **Site** (cellule 427 comprise) : le ballon échappe au porteur, puis il retombe dessus ou le
  coéquipier le plus proche le récupère ; puce « FUMBLE · RECOVERED » ; play-by-play « · recovered by VEC » / « · he
  recovers it himself » ; le commentateur le raconte. Test navigateur `outils/site/test_fumbles.js`.
- **Mesures** — semaine du 26/10 produite sur une copie de `data/` (`generer_semaine.py`, 279 matchs, 41,9 min en
  parallèle d'une exécution complète ; `audit_moteur.py` : 0 anomalie bloquante) comparée à la semaine du 19/10 :
  **fumbles perdus 1,78 -> 0,96 par match** (NFL ≈ 1,1), 0,90 gardés (dont 0,35 par le porteur) ; interceptions 1,68 ->
  1,59 ; pertes de balle 3,47 -> 2,54 ; 53,5 -> 54,2 points par match.
- **Contrôles** (exécution complète avec contrôles, 74,6 min sur 4 cœurs en parallèle de la semaine, aucun échec) :
  12.2 vicies ✅ (25 matchs : défense 53 %) ; équilibre 12.3 **39,4 % (SPK) – 60,9 % (CPH)** ; 13.2 ✅ (Brier 0,2442) ;
  **13.4 ✅ sans recalibrage** (extrêmes ± 0,026, écart moyen 0,029, outsiders − 20,4 %) ; 377 tests unitaires.

### 61. « Bigger field » : le match en plein écran (19/10/2026)
**Demande de Guillaume (19/10)**, rendus validés sur captures avant la modification : « Bigger field » ne doit pas
juste agrandir un peu le terrain mais mettre le match en plein écran — on ne voit que le déroulé du match, sans le
play-by-play ; même chose sur mobile, à l'horizontale. Les commandes du replay apparaissent au toucher ; le bandeau du
3e / 4e essai se range sous « On air ».
- **Avant** : un terrain plus grand, le play-by-play à droite, probabilité de victoire, cotes et stats en dessous.
- **Maintenant** : le terrain prend tout l'écran (fond sombre, plus de titre, de play-by-play, de panneaux ni de stats).
  Restent sur le terrain : le tableau de score (scores, temps morts, quart, horloge, chrono d'avant-snap, ballon, down &
  distance), l'indicateur LIVE / REPLAY, « On air » et le commentaire écrit (déplacé dans le match), l'encadré rouge et
  le bandeau du 3e / 4e essai (sous « On air »), la puce de l'action, TOUCHDOWN / INTERCEPTION, l'écran final.
  Le bouton de sortie (en haut à gauche) et, sur un replay, les commandes (en bas à droite, jamais sur le tableau de
  score) apparaissent au toucher ou à la souris et s'effacent après 2,5 s. Le vrai plein écran du navigateur est
  demandé (Échap ou le geste du système : retour à la vue normale) et, sur Android, l'écran est verrouillé en paysage.
  **Téléphone tenu droit** (iPhone : pas de plein écran ni de verrouillage dans Safari) : le match est tourné d'un
  quart de tour et remplit l'écran ; un toucher sur un joueur est ramené dans le repère du match (`fsTurned`,
  `pickPlayer`) et ouvre toujours sa fiche. Le choix reste mémorisé sur l'appareil (`gc-theater-v1`).
- Site seulement (le notebook n'a pas de « Bigger field » ; cellule 427 : la sélection d'un joueur suit le site).
  Test navigateur `outils/site/test_plein_ecran.js` (groupe site) : ordinateur 1440 × 900, téléphone tenu droit
  390 × 844 et en paysage 844 × 390.

### 62. Noms des joueurs sur le terrain (19/10/2026)
**Demande de Guillaume (19/10)**, validée sur captures : voir sur l'écran du match qui est qui, sans lire le play-by-play —
les receveurs et le porteur, et en défense l'auteur d'une interception ou d'un plaquage, sans gêner le reste. Trois
moments (validés), sans le QB.
- **Avant le snap** : une fois la formation en place, numéro et nom de famille sous les WR, le TE et le RB (jamais le
  QB ni la ligne) pendant 1,8 s au plus, en fondu, effacés avant le snap ; sous les pions (la bulle « CHECK » du QB est
  au-dessus) et jamais l'un sur l'autre.
- **Pendant l'action** : le nom suit le porteur du ballon dès la remise ou la réception (couleur de l'équipe).
- **À la fin** : le porteur avec son gain (« +26 Quarles », « TD ») et, en rose, le défenseur auteur de l'action :
  « TACKLE », « SACK », « INT », « PASS DEFENDED », « FORCED FUMBLE » (interception, passe défendue et sack dès l'action,
  plaquage à la fin) ; effacés avec l'action suivante.
- Grand écran seulement (vue normale et « Bigger field ») ; ni sur les tuiles de l'accueil, ni sur les coups de pied,
  ni sur les transformations à 2 points. Les noms viennent de `slotMap` (le pion = le joueur de la fiche) et du
  GameFeed (`play.players`). `nameTags` / `drawNameTags` ; cellule 427 synchronisée (sans grand écran : rien n'y est
  dessiné). Corrigé au passage : en « Bigger field », la puce du résultat est décalée à droite du bouton de sortie.
  Test navigateur `outils/site/test_noms.js` (groupe site).

### 63. L'appel de jeu qui apprend et reste imprévisible (notebook 12.2 vicies semel, 19-20/10/2026 — allumé)
Feuille de route : « moteur plus intelligent », étape 5. Module `moteur/scouting.py` (tests `test_scouting.py`), cellule
**12.2 vicies semel** (juste avant 12.3) ; interrupteur `GC_SCOUTING=0` : moteur d'avant à l'identique (contrôlé sur 4
matchs, référence calculée avant tout chargement de module) ; flux de hasard dédiés `scouting-def` / `scouting-att` (le
hasard du moteur n'est pas consommé). **Décisions de Guillaume (19/10)** : plan validé ; rendus validés sur captures
avant d'être codés.
- **Avant** : les coordinateurs s'adaptaient à ce qui marche (12.2 quater, bloc D) mais l'appel restait lisible — une
  attaque pouvait répéter ses tendances sans que la défense en profite, et rien ne poussait une attaque à les casser.
- **Ce que la défense mesure** : un carnet par attaque adverse, situation par situation — down & distance (1st, 2nd /
  3rd long, moyen, court, 4th), formation, personnel, zone du terrain (son camp, milieu, territoire adverse, zone rouge,
  goal-to-go) et down & distance × formation : courses / passes et famille du jeu (course intérieure, extérieure,
  screen / draw ; passe rapide, moyenne, profonde, play action). Les comptes s'oublient (demi-vie en snaps de cette
  attaque). Elle voit la formation et le personnel avant le snap, jamais l'appel.
- **Tendance nette** : la part de passes de chaque situation part de l'a priori de la ligue (`A_PRIORI`, par down &
  distance) ; les situations du snap sont mélangées, la plus précise pèse le plus. Nette = assez d'actions vues (`n_min`
  du profil), **≥ 66 %** d'un côté et **≥ 10 points** d'écart à l'a priori (passer sur un 3e et 9 n'est pas une
  tendance). Écart au plan (72 % / 15 points) : à ce seuil, une défense ne voyait que ≈ 2 tendances nettes par match.
- **La défense s'engage (« KEY »)** selon son profil × la confiance : priorité course ou passe, couverture contre la
  famille attendue. **Anticipation** (`ANTICIPATION`) — juste : un défenseur de plus dans le trou et −0,8 yard (la
  boîte du bloc F plafonne à 9), routes attendues couvertes de près (−0,7 pas de séparation) et poche plus courte
  (−0,3 s) ; trompée : boîte allégée et +1 yard, linebackers qui mordent (+0,9 pas, +1,3 sur un play action), poche plus
  longue (+0,25 s).
- **L'attaque se sait lue (self-scout)** quand sa tendance est nette dans la situation du snap et que la défense lui a
  montré qu'elle lit (une lecture juste dans les 6 derniers snaps, une réponse `d_run` / `d_press` de 12.2 quater, deux
  courses stoppées) ; elle **casse sa tendance (« BREAK »)** selon son bluff : play action après une série de courses,
  passe sur un down de course, course / draw sur un down de passe, même formation pour le jeu opposé (sinon : « contre
  sa tendance ») ; plafond par match ; jamais en hurry-up, en tuant l'horloge ni au 4e essai ; toujours dans son
  playbook (poids de la feuille d'appel, chemin accéléré `pb_play_weights` compris). Une cassure qui réussit sème le
  doute (la défense divise par deux ce qu'elle croyait savoir de la situation).
- **Profils, pas niveaux** : vitesse d'apprentissage (`n_min`, force de l'a priori) depuis `trigger` de 12.2 quater ;
  oubli depuis `fenetre` du bloc D ; vigilance de l'attaque depuis `learn` de 12.2 quater ; `SCOUT` (engagement, bluff,
  cassures au plus) : MNL, FRG, GRZ jouent leur jeu ; MRG, CTX, LTC, PRM, CTD, GMB jouent aux échecs ; ONX lit et
  attaque le ballon ; GLT, SPK parient. Réglage d'équilibre (20/10) : BST engagement 0,70 -> 0,60 (déjà la meilleure
  défense : lit sans parier), MNL bluff 0,05 -> 0,10.
- **Journal / GameFeed** (additif) : `play.scout = {version, def: {team, key, family, conf, why, right}, off: {team,
  tendency, played, broke, kind, same_formation, why}}` (seulement quand il y a quelque chose à raconter) ;
  `play.adjust` : `scout_key` (première lecture de chaque côté par défense) et `scout_break` (deux premières cassures
  par attaque), avec leur raison (« 21 of 24 runs on 1st down ») ; `game.scout_model`. Moteur : clé `anticipation` de
  l'appel (`reaction_defensive._effet_appel`, additive).
- **Site** (cellule 427 synchronisée) : « KEY · RUN / PASS » au-dessus du linebacker du milieu pendant l'avant-snap,
  « BREAK · PLAY ACTION / PASS / RUN / SAME LOOK » au-dessus du QB (le CHECK garde la priorité) ; puce du résultat
  « · READ » (défense juste, action stoppée), « · BURNED » (défense trompée, action réussie), « · BROKE TENDENCY » ;
  play-by-play « ONX keyed on the run (21 of 24 runs on 1st down) — read it » (« right guess, beaten anyway »,
  « burned », « wrong guess »), « MRG break their tendency (…) : play action » ; commentateur (sous-titres, aucune cue
  enregistrée). Test navigateur `outils/site/test_scouting.js` (groupe site, indépendant de l'heure).
- **Corrigé au passage** : la cellule rechargeait `moteur.reaction_defensive` et effaçait les couvertures ajoutées par
  l'extension du playbook — le moteur changeait interrupteur coupé ; trouvé par le test d'équilibre, corrigé avant les
  mesures ci-dessous. `gamefeeds.py` reconnaît une cellule au nom en deux mots.
- **Mesures** (192 matchs, mêmes graines, effet causal = anticipation allumée − coupée) : **6,0 lectures par match**
  (deux défenses), justes 61 % ; **2,2 tendances cassées par match**. Points attendus par action pour l'attaque :
  défense juste **−0,22** (passe −2,2 yards, réussite −9 points ; course −0,6 yard), défense trompée **+0,25** (course
  contre une défense engagée sur la passe +1,2 yard), tendance cassée **+0,10**. Sur un match, le pari est à peu près
  neutre : il récompense la bonne lecture et punit l'erreur.
- **Semaine du 26/10 produite** (`generer_semaine.py --lundi 2026-10-26`, notebook complet, sur une copie de `data/`) en
  **32 min**, en parallèle d'autres calculs (avant : 34-42 ; limite GitHub 75) ; `audit_moteur.py` : **0 anomalie
  bloquante, 0 alerte** (279 matchs, 54,0 points par match, 152 actions). **6,6 lectures par match** (justes 62 %, dont
  0,4 sur la course), **2,3 cassures** (contre la tendance 392, course sur un down de passe 121, même formation 113,
  play action 17). Identités — cassures par match : LTC 2,8, VEC 2,3, CTD 1,9, PRM 1,9, AXM 1,8 … GRZ 0,4, MNL 0,3,
  FRG 0,2 ; lectures en défense par match : GMB 5,7, GRZ 5,4, GLT 4,7 … MRD 1,9, AEG 1,6 (elles dépendent aussi de la
  prévisibilité de l'adversaire).
- **Équilibre 12.3** (graines officielles, 2 208 matchs) : **39,9 % (CTX, PLS) – 63,0 % (BST)** ✅ (plage 36-64 ; coupé :
  39,4 % SPK – 60,9 % CPH) ; sur 8 autres graines par affiche (4 416 matchs) : 39,8 % SPK – 56,7 % FRG (coupé : 39,4 % SPK
  – 60,3 % MNL). Les écarts par équipe changent de signe d'un échantillon à l'autre (bruit : ± 3,7 points sur 184
  matchs) ; BST, déjà au-dessus de 60 % coupé, reste la franchise à surveiller.
- **Calibration** (`rapport_calibration.py --jusqua "12.2 vicies semel"`, 1 104 matchs, contre la même cellule coupée) :
  toutes les mesures de la ligue dans les tolérances — points 53,5 -> 52,8, part des passes 63,3 -> 62,1 %, yards par
  course 6,04 -> 6,13, complétion 65,1 -> 64,8 %, sacks 9,5 -> 9,9 %, pertes de balle 2,37 -> 2,41 ; les victoires par
  équipe sortent de 40-60 % pour quelques franchises, coupé comme allumé (92 matchs par équipe : bruit ± 5 points).
- **Contrôles** (exécution complète avec contrôles, **77 min** sur 4 cœurs, seule, **aucun échec**) : 12.2 vicies semel ✅
  (coupé = identique sur 4 matchs, déterministe ; 49 matchs : 6,9 lectures, 2,3 cassures) ; 12.3 ✅ équilibre **39,9 %
  – 63,0 %**, identités nettes, ajustement hebdomadaire dans les plages ; 13.2 ✅ (Brier 0,2452, z² 0,94, biais −0,6 %) ;
  **13.4 ✅ sans recalibrage** (extrêmes ± 0,029, écart moyen 0,023, outsiders − 21,5 %) ; 14.2 ✅ ; **394 tests
  unitaires** ; tests navigateur `test_scouting.js` et `test_cellule427.js` ✅.

### 64. Nom du porteur sur une course, puce du résultat sous « On air » (20/10/2026)
Deux défauts vus sur les captures de l'étape 5 (section 63), corrigés avant l'étape 6 à la demande de Guillaume.
- **Nom du porteur d'une course** : `slotMap` mettait toujours le nom du porteur sur le pion du RB (slot 7), alors que le
  terrain fait porter le ballon par le receveur d'un jet / Z sweep (slots 8-10, TE 5) ou par le QB qui le garde (6) :
  sur un jet sweep, le nom du RB suivait le ballon (et celui du receveur restait sur le RB). `runSlot()` suit le dessin
  de `planScrimmage` (wildcat : le RB qui reçoit le snap direct).
- **« Bigger field »** : « On air » et le bandeau du 3e / 4e essai sont centrés en haut, la puce du résultat en haut à
  gauche ; sur un écran étroit (téléphone en paysage ou tourné) ou avec une puce longue (« +14 · 1ST DOWN · OUT OF
  BOUNDS · BURNED »), « On air » la recouvrait. `fsChipClear()` la descend juste sous eux quand ils la chevauchent, en
  coordonnées du match (téléphone tourné compris), à chaque légende, puce, bandeau et passage en plein écran ; vue
  normale inchangée.
- Tests : `test_noms.js` (pendant une course, le nom qui suit le ballon est celui du porteur ; le match choisi a une
  course portée par un receveur) et `test_plein_ecran.js` (puce jamais recouverte, dans les deux ordres d'apparition,
  ordinateur / téléphone tenu droit / paysage) — les deux échouent sur le site d'avant. Cellule 427 synchronisée (sans
  grand écran ni « Bigger field » : seul le nom du porteur la concerne).

### 65. La mémoire d'une semaine à l'autre : le film de scouting (notebook 12.2 vicies bis, 20-21/10/2026 — allumée)
Feuille de route : « moteur plus intelligent », étape 6. Module `moteur/scouting.py` (fin du module ; tests
`test_scouting.py`), cellule **12.2 vicies bis** (juste après 12.2 vicies semel) ; interrupteur `GC_MEMOIRE=0` : moteur de
l'idée 5 à l'identique (contrôlé sur 4 matchs, référence calculée avant tout branchement ; un film vide aussi) ; aucun
hasard nouveau (flux `scouting-def` / `scouting-att` de l'idée 5). **Décisions de Guillaume (20-21/10)** : plan validé ;
rendus validés sur captures avant d'être finalisés.
- **Avant** : le carnet de scouting de l'idée 5 (section 63) repartait de zéro à chaque match.
- **Le film** : pour chaque attaque, ce qu'une défense voit avant le snap (down & distance, formation, personnel, zone)
  et ce qui a été joué (course / passe, famille), sur tous ses matchs — les appels joués du journal, pas `play.scout`.
  Fin de semaine (14.1, `run_week`) : film de la semaine suivante = film × **0,5** + la semaine jouée (playoffs compris ;
  série bornée : ≈ 2 semaines au plus ; comptes de moins d'une demi-action oubliés), écrit **à part** par `export_week`
  dans `week_<lundi>/scouting_next_week.json` (compact, ≈ 0,85 Mo ; `week.json`, écrit indenté et relu par le serveur,
  n'en garde qu'un renvoi `{file, version, weeks, last}` ; non publié). La semaine suivante le reprend (15.1,
  `memoire_reprendre`) ; semaine précédente sans film : **amorce** depuis les GameFeeds des 4 dernières semaines de
  `data/weeks` (même film que depuis le journal : contrôlé). **Figé pendant la semaine** : les cotes sont calculées
  avant (le cache des cotes de 13.1 tient compte du film) et les paris ouverts dès la publication.
- **La défense** commence chaque match avec le film de l'attaque adverse — tous ses matchs, ceux qu'elle a joués
  elle-même contre elle pesant **1,5 fois** (au niveau de la formation) — étudié **formation par formation** (down &
  distance × formation, formation), plafonné en actions équivalentes (`FILM_MAX` × poids du coordinateur, 0,6 – 1,4 :
  fenêtre du bloc D ; AEG, CTD, MRD étudient le film, SPK y croit peu, MNL, FRG, GRZ restent sobres) : le film garde les
  proportions de l'attaque, pas sa masse. **A priori de la ligue < film < match** : le film s'efface pendant le match
  (demi-vie de 24 snaps de l'attaque) ; une tendance vue surtout sur le film est plafonnée à 0,80 de confiance.
- **Écarts au plan, après mesure** : (1) les situations générales (down & distance, zone, personnel) restent celles du
  match — sur le film elles ressemblent à la moyenne de la ligue et noyaient les séries du match (5,9 -> 4,9 lectures
  par match) ; (2) l'attaque se sait prévisible si le match **OU** son film le montre (mélangés, ses cassures tombaient
  de 2,0 à 1,6) ; (3) le poids de ses propres matchs ne porte que sur la formation (taille du film).
- **L'attaque** (self-scout) commence en sachant ce qu'elle a montré (son film à plein poids, down & distance et zone
  compris : elle se juge avant de choisir sa formation) ; une défense qui a la **réputation** de lire (≥ 3,5 lectures par
  match, ≥ 60 % justes, sur au moins 3 matchs du film) compte comme « elle lit » dès le premier snap. Plafonds de l'idée
  5 inchangés.
- **Anti-inflation** : oubli hebdomadaire (série bornée), plafonds par situation, confiance plafonnée, aucune force
  ajoutée (`ANTICIPATION` inchangée) ; audit : film dans ses bornes, `play.scout.def.film` cohérent (bloquant).
- **GameFeed** (additif) : `play.scout.version` « scouting-2 » ; `play.scout.def.film = {games, own, part}` (matchs sur
  le film, dont les siens, part du film dans la preuve) ; raison « film: 41 of 52 runs on 1st down from I-formation, 44
  games » ; `play.scout.off.on_tape` ; `game.scout_film = {home|away: {games, own, top: [{dd, formation, key, vu, sur,
  text}]}}` (ce que chaque défense apporte du film) ; `game.scout_memory = {film, weeks, source}` ; `game.scout_model`.
- **Site** (cellule 427 synchronisée ; rendus validés sur captures) : bulle « KEY · RUN / PASS » avec une seconde ligne
  « SCOUTED · 44 GAMES » quand la lecture vient surtout du film, « ON TAPE » sous « BREAK · … » ; play-by-play « TDL
  keyed on the pass (film: 154 of 166 passes on 2nd & long from Trips, 44 games incl. 2 of their own) — burned » ;
  onglet **Game plan** : « Scouting report » (matchs sur le film, deux tendances ; rien après le coup d'envoi : pas de
  spoiler) ; commentateur (sous-titres) : le rapport au coup d'envoi, « They've seen it on tape … ». Corrigé au passage :
  le play-by-play échappait deux fois la note de scouting (« 2nd &amp; long »). Test navigateur `outils/site/test_memoire.js`
  (groupe site, indépendant de l'heure).
- **Mesures** (2 208 matchs, mêmes graines, film reconstruit depuis les GameFeeds des 4 dernières semaines ; mémoire
  coupée -> allumée) : **lectures 5,9 -> 7,1 par match** (dont 3,0 sur le film, 79 % justes) ; **justes 64 % -> 76 %** ;
  lectures au 1er quart-temps ≈ 1,6 -> 3,1 ; cassures 2,0 -> 2,2 (dont 0,3 « on tape » ; 0,9 avec un film qui porte la
  réputation des défenses) ; points 53,6 -> 53,7 ; victoires 39,7 – 61,1 % -> 40,0 – 60,9 %. **8 semaines enchaînées**
  (le film de chaque semaine nourrit la suivante) : points ≈ 53,8, lectures ≈ 6,7 (76 % justes), cassures ≈ 2,3, taille
  du film bornée ; moyenne des 8 semaines 38,9 % (SPK) – 59,8 % (FRG). Un écart par équipe de ± 3 points n'est pas
  mesurable ici (bruit ≈ 5 points par équipe sur ces échantillons) : la plage de 12.3 fait foi. Calcul : + 10 % par match.
- **Semaine du 26/10 produite** (`generer_semaine.py --lundi 2026-10-26`, notebook complet, sur une copie de `data/`) en
  **28,8 min** (idée 5 : 32 ; limite GitHub 75) ; `audit_moteur.py` : **0 anomalie bloquante, 0 alerte** (279 matchs,
  51,9 points par match — 54,0 avec l'idée 5 sur la même semaine : écart de l'ordre du bruit sur 279 matchs) ; **7,8
  lectures par match** (78 % justes), dont 3,3 sur le film (80 % justes) ; 2,5 cassures (0,3 « on tape ») ; film de la
  semaine suivante 0,85 Mo.
- **Contrôles** (exécution complète avec contrôles, **56,5 min** sur 4 cœurs, seule, **aucun échec**) : 12.2 vicies bis ✅
  (coupé = idée 5 à l'identique sur 4 matchs, film vide aussi, film du journal = film des GameFeeds, déterministe ; film
  de contrôle : 49 matchs, 6,0 lectures, 2,8 cassures dont 0,9 « on tape ») ; 12.3 ✅ équilibre **41,0 % (NVA) – 61,1 %
  (FRG)** (idée 5 : 39,9 – 63,0), identités nettes, ajustement hebdomadaire dans les plages, 53,9 points par match ; 13.2
  ✅ (Brier 0,2478, z² 1,05, biais − 1,2 %) ; **13.4** : avec les paramètres d'avant, ❌ extrêmes ± 0,042, écart moyen
  0,033, outsiders − 28,7 % (les avances tiennent mieux) — paramètres `LIVE_*` ré-ajustés pour la mémoire (13.1, nouvel
  outil `outils/moteur/fit_live.py` : maximum de vraisemblance sur 1 500 matchs, graines 3 100 000 + ; `GC_MEMOIRE=0`
  garde ceux d'avant) -> ✅ extrêmes ± 0,022, écart moyen 0,019, outsiders − 8,2 % ; 14.2 ✅ ; **412 tests unitaires** ;
  tests navigateur complets ✅ (`test_memoire.js`, `test_scouting.js`, `test_cellule427.js` compris).
- **Calibration** (`rapport_calibration.py --jusqua "12.2 vicies bis"`, 1 104 matchs, contre `GC_MEMOIRE=0`) : toutes les
  mesures de la ligue dans les tolérances (points 52,77 -> 52,73, passes 62,1 -> 61,9 %, yards par course 6,13 -> 6,12,
  complétion 64,8 -> 64,8 %, pertes de balle 2,41 -> 2,36) ; victoires par équipe hors 40-60 % pour 2 franchises allumée
  (CPH 64 %, CMT 36 %) comme pour 3 coupée (MNL 66 %, CPH, AEG 63 %) : 92 matchs par équipe, bruit ± 5 points.

### 66. Résultats du jour en cours seulement (21/10/2026)
**Demande de Guillaume (21/10)** : n'afficher que les résultats de la journée en cours (le mercredi 21/10, ceux du jour et
plus ceux du lundi 19 ou du mardi 20), avec des onglets fermés ou en étant dirigé vers le bon jour.
- **Avant** : le mercredi à 07:30, le tableau Live montrait les matchs terminés de mardi soir, le bandeau leurs scores,
  « Results 120 » (toute la semaine), et le calendrier filtré sur « Results » commençait par le lundi 19 (deux journées
  de 60 matchs à faire défiler avant d'arriver au jour).
- **Maintenant** (jour = date à Bruxelles, `dayKey` / `isToday`) :
  - **calendrier** : un onglet par jour (`<details>`) — titre, « TODAY », résumé (« 60 games · 60 final », « 27 games ·
    3 live · 24 final », « No results yet · first kickoff 10:00 ») ; **aujourd'hui ouvert, les autres jours fermés**
    (avant la semaine ou un jour sans match : le prochain jour de matchs) ; un toucher ouvre un jour passé, le choix
    tient jusqu'à minuit (le lendemain, la veille se referme) ; filtres All games / Upcoming / Results inchangés ;
  - **tableau Live** : tuiles des matchs terminés, compteur « Results », bandeau du haut et Big plays : les matchs du jour
    seulement. Le matin, avant le premier coup d'envoi : les matchs du jour à venir, « Results 0 », et le bandeau dit
    « Today's results appear here · first kickoff 10:00 ».
  - Inchangés : classements, fiches d'équipe (« Results this week »), History, Ranking, paris.
- Site seulement (cellule 427 synchronisée : le notebook n'a ni tableau de saison ni calendrier). Test navigateur
  `outils/site/test_jour.js` (groupe site, indépendant de l'heure : le serveur est réglé sur le 3e jour de la dernière
  semaine, à 07:30 puis 2 h après le premier coup d'envoi) — il échoue sur le site d'avant.

### 67. La poche et la ligne offensive (notebook 12.2 vicies ter, 21/10/2026 — allumée)
Feuille de route : « moteur plus intelligent », étape 7.1. Module `moteur/poche.py` (tests `test_poche.py`), cellule
**12.2 vicies ter** (après 12.2 vicies bis) ; interrupteur `GC_POCHE=0` : moteur d'avant à l'identique (contrôlé sur 4
matchs, référence calculée avant tout branchement) ; flux de hasard dédié « poche ». **Décisions de Guillaume (21/10)** :
plan validé ; rendus validés sur vidéos au ralenti ; pas de mise en évidence du duel perdu ; pas de semaine à produire
(les tests suffisent).
- **Avant** : la poche était un chrono (un temps avant la pression par passe, 12.2 quinquies), puis lancer, pression,
  scramble ou sack (bloc B) ; personne ne gagnait de duel, la poche n'avait pas de forme et le QB ne bougeait pas ; sur
  le site, la ligne reculait en ligne droite et les rushers fonçaient tout droit.
- **Duels** : à chaque passe, chaque rusher face à son bloqueur — EDGE contre tackle (bord), DT contre guard
  (intérieur), le centre double le DT le plus dangereux ; les blitzeurs prennent le centre, puis le RB / TE qui restent
  protéger (protection de l'extension, plan de jeu du bloc D), sinon ils arrivent libres. Marge : pass_rush / strength
  contre pass_block / strength.
- **Pression** : le temps avant la pression ne change pas d'origine (il est calibré : unités, rushers, protection, jeu de
  rush) ; il dit QUAND un duel cède, les marges disent LEQUEL (un profil, pas un niveau ; les stunts et l'interior
  collapse de l'extension poussent à l'intérieur, l'edge rush au bord). Forme : **bords** (la poche se courbe en fer à
  cheval et se referme), **intérieur** (le DT enfonce le guard dans le QB), **effondrée** (un second duel cède dans la
  foulée), **propre** (le QB lance avant).
- **Réaction du QB** (pocket awareness, mobilité) : il **monte** dans la poche (pression des bords), **glisse** de l'autre
  côté (pression intérieure) ou **sort** du côté libre et **lance en courant** (précision moindre, routes courtes et
  moyennes) ou jette le ballon hors du terrain (légal hors de la poche) ; sinon scramble ou sack, crédité au **rusher qui
  a gagné son duel**. Calibration : la pression arrive 0,12 s plus tôt (`AVANCE`), le temps que le QB regagne en
  réagissant — sans elle, la poche ajoutait de la force à l'attaque (sacks 9,6 -> 8,2 %).
- **GameFeed** (additif) : `play.pocket = {version, ttp, shape, duels: [{rusher, blocker, side, type, margin, free,
  double, t}], beaten, reaction, side, on_run}` ; `game.pocket_model`.
- **Site** (cellule 427 synchronisée) : la ligne recule en fer à cheval (tackles profonds et écartés, guards, centre) ;
  les EDGE contournent les tackles en courbe, les DT poussent droit ; le duel perdu cède (au bord, le tackle pivote ; à
  l'intérieur, le guard est repoussé dans le QB ; effondrée : un second cède aussi) ; le QB monte, glisse ou sort et lance
  en courant (le ballon part après sa sortie ; réception très précoce : pas de mouvement) ; le sack est fait par le
  rusher du duel perdu. Play-by-play : « steps up in the pocket », « slides away from the rush », « flushed right, throws
  on the run », « Oyelaran beats Lachance off the edge », « the pocket collapses — X beats Y », « X comes in unblocked » ;
  stats d'équipe « Throws on the run » ; fiche joueur « Pass protection : 7/8 duels won », « Pass rush : 2 pressures
  won » ; commentateur (sous-titres). Les play actions en roulé (BOOT) gardent leur dessin. Test navigateur
  `outils/site/test_poche.js` (groupe site, indépendant de l'heure).
- **Mesures** (552 matchs, mêmes graines, poche coupée -> allumée) : sur ≈ 15 passes sous pression par match, poche pliée
  par les bords 45 %, enfoncée au centre 31 %, effondrée 24 % ; le QB monte 3,2 fois, glisse 1,7 fois, sort 4,2 fois par
  match ; ≈ 2 lancers en courant par match (complétion 51 %, 64 % dans la poche) ; sacks 9,55 -> 9,16 %, complétion
  65,2 -> 64,1 %, yards par passe 7,30 -> 7,21, points 53,8 -> 53,2.
- **Contrôles** (21/10, en local) : notebook complet ✅ (12.2 vicies ter sur 25 matchs : 2 lancers en courant par match,
  complétion 42 % en courant / 63,5 % dans la poche, sacks crédités au vainqueur du duel 100 % ; 12.3 : toutes les
  franchises entre 36 et 64 % ; 13.2 : Brier 0,2472 contre 0,2552 pour la formule de notes ; 13.4 : cotes en direct
  calibrées, pas de réajustement) ; rapport de calibration (1104 matchs, `GC_POCHE=0` -> `1`, `--jusqua "12.2 vicies
  ter"`) : toutes les statistiques dans les tolérances (complétion 64,8 -> 63,3 %, sacks 9,9 -> 9,8 %, yards par passe
  7,45 -> 7,37, points 52,7 -> 51,8, temps par match ×1,11) ; la plage 40-60 % par équipe du rapport sort pour quelques
  équipes des deux côtés (92 matchs par équipe, bruit ± 5 points, voir section 65) — l'équilibre est jugé par 12.3 ;
  427 tests unitaires, tests navigateur (dont `test_poche.js`) ✅.

### 68. Les pénalités pendant l'action (notebook 12.2 vicies quater, 21/10/2026 — allumées)
Feuille de route : « moteur plus intelligent », étape 7.2. Module `moteur/penalites.py` (tests `test_penalites.py`),
cellule **12.2 vicies quater** (après 12.2 vicies ter) ; interrupteur `GC_PENALITES=0` : moteur d'avant à l'identique
(contrôlé sur 4 matchs, référence calculée avant tout branchement) ; flux de hasard dédié « penalites ». **Décisions de
Guillaume (21/10)** : seulement les fautes pendant l'action (holding, roughing the passer, interférences, illegal
contact ; pas de false start, offside, delay of game, illegal formation) ; ≈ 8 drapeaux par match ; accepter / refuser
selon la probabilité de victoire ; rendus validés.
- **Avant** : aucune pénalité, ni dans le moteur ni sur le site.
- **Qui commet la faute** (un profil, pas un niveau) : holding offensif — le bloqueur qui perd son duel de protection
  (poche 7.1), à la course un bloqueur faible au bloc de course ; holding défensif et illegal contact — un défenseur en
  couverture, selon sa discipline (bloc C) ; interférence défensive — le défenseur responsable de la cible, sur un ballon
  disputé, plus souvent loin ; interférence offensive — la cible ; roughing — le rusher qui a gagné son duel, bien plus
  souvent sous pression. Une identité « discipline » (AEG, MRD, BST, GRZ) en commet moins. Un drapeau au plus par action.
- **Ce qu'elle coûte** (règles NFL, moitié de la distance près des en-buts) : 10 yards et essai rejoué (holding
  offensif, OPI) ; 5 yards et premier essai (holding défensif, illegal contact) ; ballon à l'endroit de la faute et
  premier essai (DPI ; aux 1 dans l'en-but) ; 15 yards et premier essai (roughing ; ajoutés à la fin d'une passe
  complétée). Acceptée, la faute **annule l'action** : ni yards ni stats (porteur, défenseur crédité, stats de saison
  14.1), le temps a passé. Pas de faute de la défense sur une interception, un fumble ou un safety, pas de roughing sur
  un touchdown (cas où la faute annulerait un changement de possession ou s'appliquerait au coup d'envoi). Non retenus
  (très rares) : le holding dans son en-but (safety) — moitié de la distance à la place —, l'essai sans temps après une
  faute de la défense quand la mi-temps se termine.
- **Accepter / refuser** : l'équipe qui subit la faute garde l'état qui lui donne la meilleure probabilité de victoire
  (`moteur/valeur.py` : même loi de la marge finale ; points attendus d'un essai selon down, distance et position).
- **GameFeed** (additif) : `play.penalty = {version, type, name, team, player {id, name, pos, number}, chooser, accepted,
  declined, wp {accept, decline}, yards, nullified, auto_first, replay_down, after {yl, down, togo}, play_before {result,
  gain, text}}` ; action annulée : `result` « penalty », `gain` = yards de la pénalité, l'action jouée dans `play_before` ;
  `game.penalty_model`.
- **Site** (cellule 427 synchronisée) : l'action annulée est dessinée comme elle a été jouée ; un drapeau jaune part au
  moment de la faute, sur le joueur qui l'a commise, et reste sur le terrain jusqu'à l'action suivante ; puce « FLAG »,
  puis l'appel (« FLAG · HOLDING · 10 YDS · REPEAT DOWN », « +15 ROUGHING THE PASSER », « FLAG DECLINED ») ;
  play-by-play « PENALTY on CTX: Holding, offense, #74 Lachance, 10 yards, repeat 3rd down — no play (Kian Morrow run,
  +6) », « Flag: Illegal contact, defense, #33 Sandoval — declined » ; stats d'équipe « Penalties (yards) », fiche
  joueur « Penalties » ; commentateur (sous-titres). Test navigateur `outils/site/test_penalites.js`.
- **Audit** (`audit_moteur.py`, `check_penalty`) : type dans la liste, équipe, joueur, accepté XOR refusé, choix conforme
  à la probabilité de victoire, action annulée ⇔ « penalty », pas de points sur une action annulée, down / distance
  après la pénalité, yards bornés ; repère « drapeaux_par_match » (alerte hors 4-12).
- **Mesures** (144 matchs) : 8,3 drapeaux par match (7,1 acceptés, 1,2 refusés, ≈ 71 yards acceptés) — holding offensif
  3,2, holding défensif 2,0, interférence défensive 1,4, illegal contact 0,6, roughing 0,55, interférence offensive 0,5.
- **Contrôles** (21/10, en local) : notebook complet ✅ (12.2 vicies quater sur 25 matchs : 8,1 drapeaux par match ;
  12.3 : toutes les franchises entre 36 et 64 % ; 13.2 : Brier moteur − formule −0,0078 ; 13.4 : cotes en direct
  calibrées, extrêmes ± 0,024, pas de réajustement) ; audit de la semaine exportée par 14.2 (279 matchs) : 0 anomalie,
  0 alerte, 7,96 drapeaux par match ; rapport de calibration (1104 matchs, `GC_PENALITES=0` -> `1`, `--jusqua "12.2
  vicies quater"`) : toutes les statistiques dans les tolérances (complétion 63,3 -> 63,1 %, yards par passe 7,37 ->
  7,27, points 51,8 -> 51,9, premiers essais 41,8 -> 43,5, drives 20,3 -> 19,8, temps ×1,05) ; la plage 40-60 % par
  équipe du rapport sort pour MNL, CPH, SPK (92 matchs par équipe, bruit ± 5 points ; 12.3 sur 2208 matchs : 51, 59,
  42 %) ; 443 tests unitaires, tests navigateur (dont `test_penalites.js`) ✅.

### 69. Le banc, les packages, la fatigue et les rotations (notebook 12.2 vicies quinquies, 21/10/2026 — allumés)
Feuille de route : « moteur plus intelligent », étape 7.3. Module `moteur/rotations.py` (tests `test_rotations.py`),
cellule **12.2 vicies quinquies** (après 12.2 vicies quater) ; interrupteur `GC_BANC=0` : moteur d'avant à l'identique
(contrôlé sur 4 matchs et sur un GameFeed, référence calculée avant tout branchement) ; flux de hasard dédié
« rotations ». **Décisions de Guillaume (21/10)** : plan validé, choix compris ; rendus validés sur captures.
- **Avant** : 25 joueurs par franchise, personne ne sortait jamais ; seule fatigue : le plafond de « touches » du porteur
  (≤ 3 yards) ; en nickel / dime pas de 3e CB, en 12 personnel pas de 2e TE (le site plaçait le LB3 en nickel back).
- **7.3.1 — le banc** (extension des rosters de 12.1 : `build_franchise` enveloppée) : 11 remplaçants par franchise (36
  joueurs, 264 dans la ligue) — QB2, RB3, WR4, TE2, OT (`<équipe>_RT2`), OG (`<équipe>_LG2`), EDGE3, DT3, LB4, CB3, S3 —
  dans `team.bench`, pas dans `team.roster` (le moteur ne les voit que quand ils entrent). Niveau 7,4 points sous le
  titulaire en moyenne (2,7 à 12,2 ; DT3 et EDGE3, qui jouent beaucoup, plus près) ; profils **vétéran** (29-33 ans,
  sans marge), **jeune à potentiel** (21-24 ans, potentiel 8-12, progresse avec ses snaps), **spécialiste** (proche du
  titulaire sur sa spécialité : slot corner, pass rush specialist, swing tackle…) — 96 / 96 / 72 ; SPK a 6 jeunes, CTD 6
  vétérans. Noms tirés des réservoirs des recrues (12.1) : aucun des 467 noms déjà portés (rosters, états des joueurs et
  retraités de toutes les semaines de `data/weeks`), aucun deux fois ; les doublons existants restent ; avec le banc, les
  recrues futures sont nommées sans doublon dans la ligue. Numéros uniques dans l'équipe et dans la plage du poste (les
  titulaires gardent les leurs). Bloc E : remplaçants dans l'état des joueurs (`banc`, profil de départ), groupes
  d'anti-inflation, de forme et d'expérience à part (les titulaires évoluent exactement comme sans banc : test), la
  recrue d'une place du banc est un jeune ; participation = 1,5 × part des snaps. Notes d'unité sur les titulaires.
- **7.3.2 — les packages** : chaque action a son alignement (11 places par unité, celles du site) ; le personnel de
  l'appel fait entrer les joueurs — 2e TE en 12 personnel (place du WR3), fullback (RB2) en 21 / 22, WR4 en 10 et en
  empty (passes), 6e OL en HEAVY ; le paquet défensif aussi — CB3 en nickel (place du LB3), CB3 et S3 en dime, LB4 en
  goal line. Le roster de l'action est l'unité alignée : cibles, couverture (le CB3 prend le slot en homme), duels de la
  poche, plaqueurs et pénalités portent le bon joueur ; rosters rendus à la fin du drive.
- **7.3.3 — fatigue et rotations** : énergie 0-100 par joueur ; un snap coûte selon le poste (DT 3,5, RB 3,1, EDGE 3,0,
  OL 1,6, QB 0,7 ; × 1,6 sur une action d'au moins 15 yards ou 7 s ; × 1,3 pour la défense face au hurry-up de PLS, qui
  ne peut pas faire tourner pendant le drive) ; 1,5 rendu par snap passé hors du terrain, 35 à la mi-temps. Effet :
  0,1 point de note par point d'énergie d'écart à 85 (− 5 au plus, + 1,5 frais), sauf notes mentales et de botté — un
  profil, pas un niveau. Rotations du coordinateur (part des snaps visée, retard sur la part + énergie, préférence pour
  le joueur déjà sur le terrain) : DT ≈ 67,5 %, EDGE ≈ 75 %, RB1 ≈ 62,5 %, modulés par l'identité (FRG et CTD gardent
  leurs lignes, GLT et SPK tournent plus, MNL / PLS / TDL font tourner les RB). **Garbage time** : probabilité de
  victoire > 98 % dans les 8 dernières minutes du 4e quart-temps **et** au moins 17 points d'écart (écart au plan,
  après mesure : à 98 % seul, QB2 entrait dans 3 matchs sur 4, dès qu'une équipe menait d'une possession à 2 minutes)
  — les remplaçants entrent, QB2 compris. La fatigue des touches reste et s'ajoute.
- **Calibration** (garde-fou 3, `rotations.CALIBRATION`) : sans correction, la ligue marquait ≈ 2,4 points de plus
  (DT3, EDGE3, CB3 jouent un tiers à la moitié des snaps ; les courses réparties réduisent la fatigue des touches) : + 0,3
  (passe) et + 1,8 (course) aux notes d'unité défensives **jouées** quand le banc est allumé (pas aux notes du roster).
  Un premier réglage (+ 1,2 / + 2,0) tenait la ligue mais sortait BST (défense d'élite) du test d'équilibre 12.3 (65,5 %) :
  la correction porte surtout sur la course, là où le banc coûte. **GLT** garde un spécialiste « interior pass rusher »
  comme DT3 (`SPECIALISTE_EQUIPE`) ; 12.3 demande GLT **dans les deux premiers** aux sacks (au lieu du premier — décision
  de Guillaume du 21/10 : GLT et VEC sont à 4,8-4,9 sacks par match, l'ordre se joue au bruit).
- **GameFeed** (additif) : `roster[]` = 25 titulaires puis 11 remplaçants, `depth` (1 / 2), `profile` (starter ·
  veteran · prospect · specialist), `slot`, `covers`, `specialty`, `snaps`, `snap_pct`, `energy` (fin de match) ;
  `play.subs = [{in, out, pos (place), reason: package | fatigue | garbage, side}]` seulement quand l'alignement change ;
  `play.players.passer` = le QB aligné ; `game.home/away.unit_snaps` ; `game.rotation_model`. Stats de saison (14.1) :
  `snaps`, `team_snaps`, `snap_pct` ; passes au QB aligné.
- **Audit** (`check_rotations`) : rosters de 36 (titulaires puis remplaçants), numéros uniques dans la plage du poste ;
  alignement de chaque action reconstitué depuis `play.subs` — 11 par côté, postes de l'unité, personne deux fois,
  joueurs du roster ; porteur et passeur sur le terrain (bloquant), défenseur crédité sur le terrain (alerte) ; snaps
  cohérents ; noms des remplaçants uniques dans la ligue (alerte).
- **Site** (cellule 427 synchronisée ; rendus validés sur captures) : les points du terrain suivent `play.subs` (le 2e
  TE, le CB3 « Nickel back », le QB2 portent leur nom et leur numéro action par action) ; fiche joueur « Depth :
  Starter / Backup · profil », « Snaps : 42 (68 %) », énergie au coup de sifflet final ; onglet Players : tableau des
  snaps ; tableau de profondeur (titulaires / remplaçants) dans My team et Teams, chaque nom ouvre sa fiche ;
  play-by-play « QB2 X comes in — the game is out of reach », « Goal-line package: X comes in » et commentateur
  (sous-titres) seulement pour ces changements marquants. Test navigateur `outils/site/test_banc.js` (groupe site,
  indépendant de l'heure).
- **Mesures** (25 matchs de contrôle de la cellule, semaine de 279 matchs) : ≈ 320 changements par match (packages
  185, rotations 140, garbage 6) ; parts des snaps : DT1 / DT2 67 %, DT3 66 %, EDGE1 / 2 71 %, EDGE3 57 %, RB1 63 %, CB3
  48 % (nickel / dime), TE2 14 %, WR4 8 %, LB4 13 %, OL et QB 97 % ; QB2 dans un match sur quatre environ, 2-4 % des
  snaps ; énergie minimale d'un match ≈ 40-65. Calcul : + 9 % par match.
- **Contrôles** (21/10, en local) : rapport de calibration (1 104 matchs, `GC_BANC=0` -> `1`, `--jusqua "12.2 vicies
  quinquies"`) : toutes les statistiques dans les tolérances (points 51,9 -> 53,2, yards par course 6,12 -> 6,16,
  complétion 63,1 -> 63,7 %, sacks 9,9 -> 9,3 %, pertes de balle 2,40 -> 2,34, premiers essais 43,5 -> 44,1, temps par
  match × 0,70) ; la plage 40-60 % par équipe sort pour FRG (64,7 %) et SPK (36,4 %) allumé (SPK 35,3 % coupé ; 92 matchs
  par équipe, bruit ≈ 5 % : c'est 12.3, 184 matchs par équipe, qui juge) ; 12.3 : toutes les franchises entre 36 et 64 %
  (BST 62,2 %, PRM 41,0 %), identités tenues, 52,5 points par match ; audit d'une
  semaine de 279 matchs produite avec le banc : 0 anomalie, 0 alerte (51,3 points, 8,1 drapeaux par match) ;
  notebook complet ✅ (13.2 : Brier 0,2485 contre 0,2557 pour la formule de notes, z² 0,98, biais + 0,9 % ; 13.4 : cotes
  en direct dans la tolérance sans recalage, extrêmes ± 0,014, écart moyen 0,021 ; 14.2 : semaine validée et exportée,
  279 GameFeed), puis audit de cette semaine : 0 anomalie, 0 alerte (53,0 points, 8,2 drapeaux par match). En local,
  12.3 a été exécuté à part (≈ 7 Go : 2 208 matchs complets gardés ensemble, mémoire que Python ne rend pas avant les
  processus de 13.2 — dans ce conteneur, le noyau meurt en 13.2), et le notebook complet avec, à sa place, les mêmes
  matchs (mêmes graines) réduits aux équipes et aux scores, ce dont 13.2 a besoin ; 464 tests unitaires, tests
  navigateur (dont `test_banc.js`, `test_cellule427.js`) ✅.

### 70. Les blessures (notebook 12.2 vicies sexies, 22-23/10/2026 — allumées)
Feuille de route : « moteur plus intelligent », étape 7.4, la dernière de l'étape 7. Module `moteur/blessures.py` (tests
`test_blessures.py`), indisponibles de `moteur/rotations.py`, cellule **12.2 vicies sexies** (après 12.2 vicies
quinquies) ; interrupteur `GC_BLESSURES=0` : moteur de 7.3 à l'identique (contrôlé sur 4 matchs et sur un GameFeed,
référence calculée avant tout branchement) ; flux de hasard dédié « blessures ». **Décisions de Guillaume (22/10)** :
ses recommandations — l'absence commence la semaine suivante (les cotes publiées le samedi restent justes toute la
semaine), ≈ une sortie tous les deux matchs et ≈ 2 absents par équipe, une partie du corps et une durée (rien de
choquant à l'image), un joueur libre quand l'effectif est à court ; « si je ne relance pas après 1 h, lance la suite ».
- **7.4.1 — la blessure pendant le match** : à chaque action de l'attaque (les équipes spéciales ne changent pas),
  chaque joueur sur le terrain a un risque selon son poste (RB, LB, DT, TE, EDGE plus que les WR, les CB et le QB),
  bien plus grand s'il prend le coup (porteur plaqué × 9, plaqueur × 5, QB sacké × 14 ; course lancée × 1,5), sa
  fatigue (énergie de 7.3 sous 70 : jusqu'à × 1,8) et son âge (+ 6 % par an après 29 ans) ; au plus un blessé par
  action. Gravité : légère 37 % (il revient après 2 à 10 snaps de son unité), match 37 %, semaines 26 % (1 : 18 %,
  2 : 5 %, 3 : 2 %, 4 : 1 %) ; partie du corps selon la gravité (cheville, épaule, ischios, genou, commotion — jamais
  légère —, côtes, main…). Le remplaçant de la place entre (`play.subs` « injury », « return » au retour) : la
  profondeur monte (le WR2 passe WR1, le WR4 entre), une place sans joueur à son poste est prise par une famille
  voisine (`URGENCE` : le S3 glisse en CB…), en dernier recours (essai à 30 fois le taux) un blessé joue blessé. Le
  dernier QB valide ne se blesse pas. L'horloge s'arrête (« blessure »), sauf dans les 2 dernières minutes d'une
  mi-temps (elle garde sa règle). Le tirage a lieu à la fin de l'action, avant l'horloge (`advance_game_clock`).
- **7.4.2 — l'infirmerie** : une blessure de « semaines » rend absent à partir de la semaine suivante. L'état des
  joueurs (bloc E, `players_next_week`) garde l'infirmerie (`infirmerie` : partie, semaines restantes, semaine de la
  blessure ; la plus longue l'emporte ; un retraité en sort) ; au début de la semaine (`progression_debut_semaine`,
  AVANT les cotes de `run_week`), les absents sortent : notes d'unité recalculées avec leurs remplaçants, rotations
  sans eux (1er snap : changement « absence »), clé du cache des cotes. Une famille de postes qui a plus d'absents que
  de remplaçants valides signe un joueur libre pour la semaine (`<équipe>_FA<n>`, profil `free_agent`, 10 points sous
  le titulaire, nom jamais porté ; pas dans l'état des joueurs). Un absent ne joue pas, donc ne progresse pas
  (participation nulle). Le rapport est publié dans week.json : `injuries` = absents (avec leur remplaçant),
  signatures, puis, en fin de semaine, les nouvelles absences (`export_week` l'écrit : une ligne ajoutée en 14.2).
- **Pendant la semaine** (décision de Guillaume du 23/10, avant la fusion) : un blessé de « semaines » ne rejoue pas
  les matchs suivants de la semaine en cours, playoffs compris — **sans changer les cotes** publiées le samedi : les
  simulations des cotes (graines ≥ `ENGINE_ODDS_SEED_BASE`, celles des playoffs aussi) ne voient que les absents
  d'avant la semaine (ni les blessés de la semaine, ni les joueurs libres signés pendant la semaine ; clé du cache
  inchangée). Une subtilité pour les parieurs : le site le montre une fois la blessure jouée. Sa durée part de la
  semaine suivante (la fin de la semaine en cours s'ajoute) ; au calcul du samedi suivant, les cotes en tiennent
  compte. Une équipe à court signe un joueur libre aussitôt (pas au roster des matchs d'avant sa signature, ni dans
  week.json). Rapport : `injuries.in_week` et `in_week_signings` (match, action) ; le serveur ne les publie qu'une fois
  l'action jouée ; GameFeed des matchs suivants : le blessé « out » (`absence.in_week`), changement « absence » au 1er
  snap. Site : « Hurt Tue · out this week + 1 wk » au rapport, « OUT » au tableau de profondeur, « Out: … » sur les
  tuiles des matchs à venir. Audit : un blessé de « semaines » est « out » dans tous les matchs suivants de son équipe
  (bloquant). Deux semaines enchaînées : 47 puis 35 blessés de « semaines », jamais alignés ensuite ; 12 et 13 joueurs
  libres signés pendant la semaine ; 47 absents avant les cotes de la semaine 2 (≈ 2 par équipe).
- **Audit, au passage** : un match de playoffs peut avoir plusieurs prolongations (règle 11.6) — le quart-temps 6 d'une
  double prolongation n'est plus « impossible » (l'audit aurait bloqué la publication du samedi).
- **GameFeed / week.json** (additifs) : `play.injury` {id, name, team, pos, part, severity: minor · game · weeks,
  weeks, returns}, `game.injuries`, `game.injury_model`, `roster[].injury` (blessure du match) ; `roster[].status`
  (active · out) et `roster[].absence` ; reasons de `play.subs` : `injury`, `return`, `absence`. **Serveur** : le site
  ne reçoit ni la blessure d'une action pas encore jouée (`game.injuries`, `roster[].injury` filtrés par les actions
  révélées), ni les nouvelles absences de la semaine (le rapport public : absents et signatures) — test `Blessures`
  de `test_serveur.py`.
- **Audit** : un absent n'est jamais aligné, un blessé (sauf blessure légère) ne revient pas, le blessé est sur le
  terrain à son action, blessures du match = actions avec une blessure ; rapport et rosters concordants (absents
  « out », joueurs libres au banc) ; d'une semaine à l'autre, les absents sont ceux de l'infirmerie publiée par la
  précédente (bloquant) ; plus de 4 absents par équipe : alerte. Rosters de 36 + joueurs libres acceptés.
- **Site** (cellule 427 synchronisée ; rendus montrés sur captures le 23/10) : après l'action, une croix médicale à
  côté du blessé et son étiquette « INJURED » ; play-by-play (« Injury: X (RB), ribs — will not return », puis « Y comes
  in for the injured X », « X returns ») et commentateur (commotion à part) ; fiche en match : bandeau « Injured ·
  ribs — will not return » ; Teams / My team : « Injury report · published before the odds » (joueur, blessure,
  « Out · 2 wks », remplaçant ; joueurs libres signés), tableau de profondeur (absent « OUT · knee », joueur libre
  « FA · Free agent »), fiche d'un absent ; tuiles : « Out: … » (titulaires absents). Test navigateur
  `outils/site/test_blessures.js` (groupe site, indépendant de l'heure).
- **Mesures** : 276 matchs (une semaine) : 0,51 blessure par match (légères 0,18, match 0,18, semaines 0,15 ; RB
  devant WR, OL, EDGE, S, LB ; 4 QB sur 141) ; 1,75 nouvel absent par équipe et par semaine (avant la retouche des
  longues : ≈ 1,5 attendu) ; deux semaines enchaînées (`run_week`) : 41 absents en semaine 2 (1,7 par équipe), 10
  joueurs libres, aucun absent aligné sur 42 000 actions, 54 absents annoncés pour la semaine 3 (2,25 par équipe).
- **Contrôles** (23/10, en local) : rapport de calibration (1 104 matchs, `GC_BLESSURES=0` -> `1`, `--jusqua "12.2
  vicies sexies"`) : toutes les statistiques dans les tolérances (points 53,2 -> 53,3, complétion 63,6 -> 63,7 %,
  sacks 9,3 -> 9,2 %, yards par course 6,16 -> 6,16, pertes de balle 2,35 -> 2,35) ; ONX et FRG hors de 40-60 %
  déjà blessures coupées (bruit, 12.3 juge) ; notebook complet ✅ (13.2 : Brier 0,2489 contre 0,2546 pour la formule
  de notes, z² 0,95, biais + 0,2 % ; 13.4 : cotes en direct dans la tolérance sans recalage, extrêmes ± 0,016, écart
  moyen 0,017 ; 14.2 : semaine validée et exportée, 279 GameFeed, 42 nouvelles absences au rapport) ; audit de cette
  semaine : 0 anomalie, 0 alerte ; 12.3 à part (même raison qu'en 7.3) : toutes les franchises entre 36 et 64 % (BST 61,7 %, ONX 40,5 %),
  identités tenues (sacks GLT, défense BST…), 52,6 points par match ; 479 tests unitaires (dont `test_blessures.py`, le
  test `Blessures` du serveur), tests navigateur (dont `test_blessures.js`, `test_banc.js`, `test_cellule427.js`) ✅.

### 71. Le chat — étape 1 : le serveur (26/10/2026)
Bloc 3 (espace de discussion). **Décisions de Guillaume (26/10)** : ses recommandations — salon General et un salon par
match (direct puis replay), ligues en V1.1, pas de messages privés ; lecture libre, écriture réservée aux comptes ;
messages gardés 30 jours, signalements et décisions 6 mois, masqué au 3e signalement ; pas de lien en V1 ; une PR pour
les étapes 1 et 2 (serveur, puis salon General dans la page), une pour l'étape 3 (salons de match et anti-spoiler).
**Étape 1 = serveur seul : rien ne change sur le site** (la page ne sait pas encore afficher le chat).
- **Interrupteur `GC_CHAT`** : `off` (défaut, et toute autre valeur) — routes du chat en 404, `/api/delta` identique
  à l'octet près à la version d'avant (contrôlé, horloge figée) ; `read` — lecture seule (incident) ; `on`.
  `GC_CHAT_DAYS` : durée de conservation des messages (défaut 30 jours).
- **Salons** : `general` ; `m:<semaine>:<id du match>` (ex. `m:2026-10-26:w5-r01`), ouvert à l'écriture 30 min avant
  le coup d'envoi (une affiche de playoffs encore cachée reste fermée), lisible ensuite jusqu'à la purge (replay).
- **Écrire** : comptes seulement (pas un invité) ; pas un compte de moins de 10 min ; pas un pseudo qui pourrait passer
  pour l'équipe (admin…, snapline, moderat…, ou les mots staff, support, official, system, team, modo — « supporter »,
  « Badminton » passent) ; pas un banni. Pseudo affiché = pseudo du compte au moment du message (unique), avec l'équipe
  favorite. Auteur public = identifiant opaque `a` (HMAC de l'id du joueur, clé tirée une fois et gardée dans la base) :
  **ni id interne, ni jeton, ni adresse IP, ni e-mail** dans une réponse ; l'adresse IP n'est jamais stockée.
- **Texte** : une ligne, 280 caractères ; caractères invisibles et de sens d'écriture retirés, un signe diacritique
  par lettre au plus. Filtre `static/chat_filtre.txt` (anglais, français, néerlandais ; relu tout seul quand il change ;
  jamais servi) : `[bloque]` refusé (`message_blocked`), `[masque]` en astérisques ; chiffres « leet » et sosies
  cyrilliques compris, « f u c k » lu comme un mot, sans faux positif sur « as », « assist », « Scunthorpe »,
  « niggling », « Niger », « Raccoon », « 3.5 yds » (testé). Liens refusés sauf snapline.live ; e-mails et numéros de
  téléphone refusés (`contact_not_allowed`). Le texte est rendu tel quel : la page devra l'afficher par `textContent`.
- **Débit** (en mémoire : un seul processus) : 1 message toutes les 3 s, 10 par minute, 300 par jour, pas deux fois le
  même en 2 min ; 30 par minute depuis une même adresse, tous comptes.
- **Temps réel** : interrogation courte. `/api/delta` porte `chat: {general: <dernier id>, rev}` (badge des non-lus,
  aucune requête de plus panneau fermé) ; le panneau ouvert lit `GET /api/chat?room=…&after=<id>&rev=<n>` toutes les
  3 s, servi par un tampon des 300 derniers messages de 32 salons au plus (pire cas mesuré ≈ 9 Mo ; 0,02 ms par appel).
  `gone` = messages retirés depuis `rev` (masqués, effacés) ; `reset` : trop de retraits manqués, recharger le salon.
- **Anti-spoiler, salon de match** : chaque message porte `at` = nombre d'actions que l'auteur avait vues, borné au
  direct (personne ne prétend avoir vu plus loin). Un score qui n'est pas celui de cette position (dans un sens ou dans
  l'autre), ou un mot de fin de match (won, final, overtime…), renvoie le message au point le plus loin connu.
  Lecture d'un replay : `upto=<position>` donne les messages déjà « vus » et, à part, `pending` (ceux d'après, que la
  page montrera quand le spectateur y arrivera ; `pend_more` : il y en a d'autres, relire plus loin) ; `far` =
  position du direct. **General** : chaque message porte les
  équipes citées (`teams` : abréviation en majuscules exactes, nom, ville ou surnom) et `sc: 1` s'il ressemble à un
  score ou à une fin de match — la page floutera (étape 3) ceux qui citent un match que le spectateur n'a pas fini.
- **Signaler** (comptes ; un par compte et par message ; 20 par heure) : spam, abuse, hate, spoiler, other. Au 3e
  signalement de comptes différents, le message est masqué en attendant l'administrateur. L'auteur **efface** son
  propre message (et ses signalements).
- **Administration** (`GC_ADMIN_KEY`, 10 essais faux par adresse en 15 min ; marche aussi chat coupé) :
  `POST /api/admin/chat` `{key, action, …}` — `reports` (messages signalés ou masqués à revoir, bannissements),
  `author {a}` (100 derniers messages d'un auteur), `hide {id, reason}`, `unhide {id}` (revu : ne sera plus masqué
  automatiquement), `ban {a, days, reason}` (`days` 0 = définitif ; masque aussi ses messages des dernières 24 h),
  `unban {a}`, `post {room, body}` (message « Snapline » avec badge), `purge`. Le motif est montré à l'auteur
  (`/api/chat/status` : `notices`, `ban` — exposé des motifs, DSA art. 17). Page `/admin/chat` : section 72 ; en ligne
  de commande :
  ```
  curl -X POST https://snapline.live/api/admin/chat -H 'Content-Type: application/json' \
       -d '{"key":"<GC_ADMIN_KEY>","action":"reports"}'
  curl -X POST https://snapline.live/api/admin/chat -H 'Content-Type: application/json' \
       -d '{"key":"<GC_ADMIN_KEY>","action":"ban","a":"8ba318ee9f","days":7,"reason":"Spam"}'
  ```
- **Conservation** : messages `GC_CHAT_DAYS` jours (30), 200 000 au plus (les plus anciens partent) ; signalements et
  décisions (avec le texte du message masqué) 6 mois ; bannissements temporaires finis retirés. Purge au plus une fois
  par heure, à la lecture (pas de fil de plus). ≈ 220 octets par message en base : 10 000 messages ≈ 2,2 Mo
  (volume de 500 Mo). Tout est dans `gamecenter.db`, donc dans `/api/backup`.
- **Sécurité** : écritures en JSON seulement (`Content-Type: application/json`, sinon 415 : un formulaire d'un autre
  site ne peut pas écrire à la place d'un joueur ; de toute façon le jeton n'est pas dans un cookie).
- **Routes** : `GET /api/chat?room=&after=&upto=&rev=` (lecture libre) · `POST /api/chat/status {token}` ·
  `POST /api/chat/post {token, room, body, at}` · `POST /api/chat/delete {token, id}` ·
  `POST /api/chat/report {token, id, reason}` · `POST /api/admin/chat`. Codes d'erreur (la page les traduira) :
  `chat_off`, `chat_read_only`, `account_required`, `account_too_new`, `pseudo_reserved`, `banned`, `room_not_found`,
  `room_closed`, `empty`, `too_long`, `message_blocked`, `links_not_allowed`, `contact_not_allowed`, `too_fast`,
  `too_many`, `duplicate`, `own_message`, `message_not_found`, `json_required`.
- **Tests** : `moteur/tests/test_chat.py` (18 tests, aucun ne lit l'horloge : instants tirés du calendrier de la
  semaine) — interrupteur, qui écrit, nettoyage, filtre (et ses faux positifs), liens, débit, signalements, effacement,
  administration, JSON obligatoire, purge, salon de match (position, ouverture, replay), équipes et spoilers, tampon et
  retraits. Essai de bout en bout avec uvicorn (HTTP réel) et mesure de mémoire faits en local.

### 72. Le chat — étape 2 : le salon General dans la page (26/10/2026)
Ce qu'on voit sur le site **une fois `GC_CHAT=on` posé sur Railway** (sans la variable : rien, la page, `/legal` et
`/api/delta` sont ceux d'avant ; `/admin/chat` répond 404).
- **Où** : bouton **Chat** dans la barre de gauche (entre Leagues et My bets) ; sur téléphone, où cette barre est
  cachée, une icône dans la barre du haut. Un point rose = nouveaux messages depuis la dernière lecture (le numéro du
  dernier message arrive avec `/api/delta`, aucune requête de plus). Tout est construit par le script seulement si le
  serveur annonce le chat (`#gf-server` porte `chat`) : chat coupé, le DOM est celui d'avant.
- **Le panneau** : à droite, par-dessus le bulletin, sans voile (le tableau reste utilisable) ; plein écran sur
  téléphone (la page dessous devient inerte). Ouvert : `/api/chat` toutes les 3 s, pas quand l'onglet est caché ; au
  plus 120 messages dans la page (iPad). Ouvrir un match (grand écran, « Bigger field ») ferme le panneau ; le chat
  dans un match et l'anti-spoiler viennent à l'étape 3. Pas de notification push pour le chat.
- **Lire et écrire** : un invité lit et voit « Read along, or create a free account to chat » (bouton vers Settings).
  Un compte écrit (« Message as <pseudo> », Entrée envoie), voit son message tout de suite (« you ») ; compteur à partir
  de 240 caractères, envoi bloqué au-delà de 280. Chaque refus du serveur a sa phrase (lien, coordonnées, haine,
  débit, compte trop récent, pseudo réservé, banni avec la date et le motif) ; le texte refusé reste dans le champ.
  Mots masqués : « Sent. Some words were hidden with *** ».
- **Sur un message** (bouton « … ») : **Report** (Spam, Abuse, Hate, Spoiler, Other ; comptes seulement), **Mute**
  (cet appareil seulement ; « Unmute all » en bas), **Delete** pour son propre message. Un message masqué par la
  modération : l'auteur le voit en haut du panneau avec le motif (« Dismiss »). Message de l'équipe : badge
  **Snapline**.
- **Accessibilité** : panneau `role="dialog"` nommé, Échap le ferme et rend le focus au bouton ; liste `role="log"`
  sans annonce à chaque message : « 3 new messages » au plus toutes les 10 s, seulement si le focus est dans le chat ;
  champ avec un libellé visible ; menus au clavier (`aria-expanded`) ; cibles de 44 px au doigt ; mouvement coupé avec
  « réduire les animations » ; thèmes clair et sombre.
- **Sécurité** : tout texte venu du serveur est posé avec `textContent` (jamais en HTML) — testé avec
  `<img onerror>` ; écritures en JSON ; jeton dans le corps, jamais dans l'adresse.
- **Modération : `/admin/chat`** (en français, non indexée, sans cache, pas dans une iframe). La clé est tapée dans la
  page et gardée dans l'onglet seulement (`sessionStorage`). « À revoir » : messages signalés ou masqués, avec les
  motifs ; **Masquer** (motif demandé, montré à l'auteur), **Laisser (revu)**, **Bannir 1 jour / 7 jours /
  définitif** (confirmation ; masque aussi ses messages des dernières 24 h), **Ses messages** ; liste des
  bannissements avec **Lever** ; **Message de l'équipe** publié dans General.
- **Page légale** (`/legal#chat`, seulement chat allumé, texte dans `static/legal_chat.html`) : règles du chat
  (respect, pas de spam ni de lien, données personnelles, usurpation, spoilers), signaler (bouton ou contact), ce que
  nous pouvons faire et comment la personne est prévenue (motif, demande de réexamen au contact — DSA art. 16-17),
  effacer ses messages, durée (`GC_CHAT_DAYS`) ; dans « What we keep » : messages, signalements, décisions, durées,
  aucune adresse IP avec un message. Pas de publicité dans le panneau.
- **Tests** : `outils/site/test_chat.js` (groupe site de `tests_navigateur.sh`, deux serveurs : chat allumé et coupé ;
  indépendant de l'heure : l'âge des comptes est reculé dans la base) — invité, deux comptes, `<img onerror>`, mot
  masqué, lien refusé, compteur, signaler, masquer, effacer, administration depuis la page, ouvrir un match, téléphone
  390 px, page légale, aucune erreur JS ; `moteur/tests/test_chat.py` (19 tests) : la page ne reçoit `chat` que chat
  allumé, page légale et `/admin/chat` selon l'interrupteur.

### 73. Le chat — étape 3 : un salon par match, sans spoiler (26/10/2026)
Toujours derrière `GC_CHAT` (coupé : ni bouton, ni réglage, rien de chargé). Le serveur était prêt depuis l'étape 1
(section 71 : position `at` bornée au direct, score ou fin de match renvoyés au point le plus loin connu).
- **Où** : dans le grand écran d'un match de la semaine (en direct, ou en replay depuis le tableau, le calendrier, une
  équipe…), bouton bulle **Match chat** dans l'en-tête, à côté de « Bigger field ». Pas de salon pour un match hors
  calendrier (exhibition, fichier GameFeed chargé). Le tiroir s'ouvre à droite du match ; plein écran sur téléphone en
  vue normale. En **« Bigger field »**, le bouton reste à côté du bouton de sortie (et s'efface avec lui) et le tiroir
  vit dans le panneau du match : sur un téléphone tenu droit, il suit le match tourné ;
  le tiroir en prend un peu moins de la moitié et le terrain reste visible. Fermer le match ferme son chat ; ouvrir le chat General ferme le match (étape 2).
- **Synchronisé à l'action** : la page compte les actions que le spectateur a vues (le score à l'écran est celui
  d'après ces actions). Au chargement, `/api/chat?upto=<position>` donne les messages écrits jusque-là et, à part, ceux
  d'après ; ceux-ci apparaissent quand l'écran y arrive (contrôle toutes les 0,5 s). Revenir en arrière dans un replay
  recharge le salon à la nouvelle position. En direct, tout le monde est au même point. Un message écrit porte la
  position de son auteur ; s'il parle d'un score qui n'est pas celui de ce moment (ou du résultat), le serveur le met
  à la fin et l'auteur lit « Sent. It talks about the score or the result, so people watching a replay see it once
  they reach the live point ». Ses propres messages s'affichent toujours tout de suite.
- **General, bouclier anti-spoiler** (Settings › **Chat spoiler shield**, allumé par défaut, à côté de « Hide scores ») :
  un message qui ressemble à un score ou à une fin de match (`sc`) et qui cite une équipe (`teams`) dont un match de la
  semaine a commencé sans avoir été regardé ici jusqu'au bout (mémoire « vu » du site) est replié : « Possible
  spoiler · CTX · tap to show ». Son texte n'est mis dans la page qu'au toucher. Ses propres messages et ceux de
  l'équipe ne sont jamais repliés.
- **Accessibilité** : tiroir `role="dialog"` nommé (« CTX @ CMT · chat »), Échap ferme d'abord le chat puis le match,
  le focus revient au bouton ; même liste, mêmes annonces groupées, mêmes menus que General ; le pli est un bouton
  qui dit l'équipe (« Possible spoiler about Cortex Foxes. Show the message »).
- **Le code de l'étape 2 est partagé** : General et un match utilisent les mêmes fonctions (liste, menu, signaler,
  masquer, effacer, pied avec le champ), chacun avec son état (`CH`, `MC`) ; masquer une personne vaut partout.
- **Tests** : `outils/site/test_chat_match.js` (groupe site ; horloge des serveurs posée par `GC_DEMO_AT` 3 h après le
  premier coup d'envoi de la dernière semaine, indépendant de l'heure) — pas de chat chat coupé ni hors calendrier ;
  replay à l'action 10, 45, 5 puis à la fin ; écrire depuis le replay (position, score renvoyé à la fin) ; Échap ;
  « Bigger field » sur ordinateur et sur un téléphone tenu droit ; bouclier (replié, montré au toucher, réglage, matchs
  vus) ; aucune erreur JS. `test_chat.js` (étape 2) passe toujours.

### 74. Refonte des playbooks — étape 1 : mesurer l'identité de jeu (27/10/2026)
Rien ne change dans le moteur ni dans le site : un outil de mesure, et des fiches à valider avant l'étape 2.
- **Outil** : `python3 outils/moteur/identite_playbooks.py` (dernière semaine ; `--semaines N`, 0 = toutes ;
  `--weeks` autre dossier ; `--md fichier` rapport Markdown ; `--json fichier`). ≈ 4 s par semaine. Lit les GameFeed
  des matchs et compte, par franchise, les appels de course ou de passe (genou et spike exclus ; un scramble compte
  comme la passe appelée) : familles (courtes, intermédiaires, profondes, écrans, play-action / bootleg, RPO, courses
  intérieures, en force, extérieures, option / QB), concepts, formations, personnel, plays, motion ; situations
  (1er & 10, 3e et long, courte distance, zone rouge, 4e tentés) ; défense de l'équipe qui défend (concepts, blitz,
  homme, paquets, fronts, stunts, ballons récupérés). Puis : signatures (concept ≥ 3 % et ≥ 1,5 fois la ligue), plays
  exclusifs, écart à la ligue et entre franchises (Jensen-Shannon sur les concepts).
- **Constat (semaine 2026-10-26)** : 248 plays différents dont 3 exclusifs, écart moyen 0,062, 14 paires sous 0,04
  (BST–MRD 0,019). Rapport : `programme/Refonte_playbooks_mesure_2026-10-26.md` ; fiches et cibles :
  `programme/Refonte_playbooks_fiches.md`.
- **Tests** : `moteur/tests/test_identite_playbooks.py` (deux matchs fabriqués : classement, situations, sens
  d'attaque, défense attribuée, exclusifs, signatures, écarts, rapport).

### 75. Refonte des playbooks — étape 2 : l'identité de jeu des franchises (27-28/10/2026)
Fiches validées par Guillaume le 27/10 (`programme/Refonte_playbooks_fiches.md`, avec les décisions). Cellule
**12.2 vicies septies** (après les blessures), module `moteur/identite_franchises.py`. Interrupteur `GC_IDENTITE`
(allumé ; `0` : moteur d'avant à l'identique, contrôlé par la cellule sur 3 matchs). Les semaines publiées ne changent
pas ; les équipes de LEAGUE non plus.
- **Correction** : les préférences de formation de l'extension (12.2 decies, 22 formations) n'étaient appliquées qu'à
  CTX, VEC, AEG et MNL ; elles le sont aux 24.
- **Playbook d'identité** (enveloppe de `franchise_playbook`) : multiplicateurs de concepts et de formations par
  franchise (`ATTAQUE`) ; le budget course / passe du coordinateur ne change pas. **Plays exclusifs** (`EXCLUSIFS`,
  110 : 4 à 6 par franchise) : combinaisons formation × concept existants créées pour une seule franchise, ou play de
  l'extension réservé à sa franchise ; les autres le perdent sans perte de poids pour le concept. **Feuille d'appel**
  de la franchise (`SITUATIONS` : zone rouge d'APX, court de GMB…), **menu** resserré de PLS (`MENU`), **motion**
  (`MOTION`, 8 franchises, flux « id-motion »), **ZPH en 10 personnel** sur ses formations spread (le WR4 du banc
  prend la place du TE), **défense** (`DEFENSE` : couvertures et blitz du coordinateur, paquets, rush, fronts).
- **Sortis de la réserve** de l'extension : `SALEM` (passe à trois niveaux, famille de SAIL ; GRZ, CTD) et
  `SPILL_PROTECTION` (pression à 5 contre la course, effet par classe de course `PAQUET_COURSE` ; GRZ, FRG). Le site
  dessine SALEM (tables `CONCEPT_ROUTE`, `PASS_ASSIGN`, `TARGET_DEFAULT`, cellule 427).
- **Systèmes réels** de référence (`SYSTEMES`) : Walsh (AXM), Leach (ZPH), Mike Shanahan (TDL), Kyle Shanahan / McVay
  (MRG), Air Coryell (NVA)…
- **Mesure** (semaine de test, 276 matchs, 3 graines) : écart moyen à la ligue 0,111-0,115 (avant 0,064), aucune paire
  sous 0,05 (avant 14 sous 0,04), 352 plays joués dont 121 par une seule franchise (avant 248 dont 4), 3 signatures ou
  plus pour toutes les franchises sauf CTX (« Adapt » : pas de dominante, par fiche) et parfois ONX. Points par match
  53,0 (avant 54,1) : à recaler avec le reste à l'étape 3 (calibration, cotes, audit, temps du samedi).
- **Étape 3 (28/10)** : `python3 outils/moteur/equilibre_identite.py` joue le test d'équilibre de 12.3 (2 208 matchs,
  mêmes graines) identité coupée puis allumée (`--coupe` réutilise un passage coupé, `--boucle` pour régler) :
  victoires de 0,421 à 0,576 (coupée : 0,405 à 0,617, BST hors limite), toutes les mesures de la ligue dans les
  tolérances de `rapport_calibration.TOLERANCES` (points 52,6 -> 53,6), 277 ms par match (coupée 274). Réglage : ZPH
  garde le 10 personnel hors du SHOTGUN de base, SPK moins de verticales et de jet sweeps, AXM un jeu court moins appuyé,
  BST moins de courses ; identités tenues (écart moyen 0,109, paire la plus proche 0,044).
- **Outils** : `python3 outils/moteur/semaine_identite.py` (semaine de test : moteur chargé une fois, ≈ 8 min, puis
  ≈ 30 s par semaine ; `--identite on/off`, `--graine`, `--garder` ; `--boucle dossier` pour régler le module sans
  recharger le notebook) ; `node outils/site/capture_identite.js <GameFeed> <sortie>` (captures : SALEM, ZPH en 10
  personnel, un exclusif).
- **Tests** : `moteur/tests/test_identite_franchises.py` (tables connues du moteur, exclusifs, playbook d'identité,
  feuille d'appel, motion déterministe, personnel, défense, SALEM et SPILL_PROTECTION) ; la cellule vérifie budgets,
  exclusifs jouables et réservés, déterminisme, GameFeed valides, interrupteur coupé.

### 76. Correctif : un drive n'est plus coupé à 20 actions (28/10/2026)
Trouvé par le calcul d'essai de la semaine du 02/11 (refonte des playbooks, étape 3) : un drive de GMB de 20 actions
finissait par 1er & but aux 8 (holding défensif accepté sur un 4e essai), puis le ballon passait à l'adversaire au même
endroit. `simulate_drive_franchise` (12.2) et ses enveloppes ont `max_plays = 20` par défaut ; la boucle qui s'arrête à
20 actions laisse le résultat par défaut, `TURNOVER_ON_DOWNS`. Rare (1 drive sur 1 155 matchs publiés), plus probable
avec les pénalités ; l'audit le classe bloquant (« après la pénalité ») et la semaine ne serait pas publiée.
- Cellule **12.2 vicies octies** (après l'identité) : le drive d'une franchise reçoit `max_plays = 60`
  (`DRIVE_MAX_ACTIONS`, jamais atteint). Les drives de moins de 20 actions ne changent pas (3 matchs de référence
  contrôlés), le hasard non plus. Interrupteur `GC_DRIVE_LONG` (`0` : coupure à 20 actions, à l'identique).
### 77. Mesure de l'audience : liens courts et tableau de bord (promotion, étape 9.1 — 28/10/2026)
**Décisions de Guillaume (28/10)** : plan de l'étape 9 validé (`programme/Promotion.md`, section 9) ; on commence par
mesurer. Le serveur compte lui-même ce que Cloudflare et Search Console ne voient pas : les clics sur les liens des
réseaux et les nouveaux joueurs. Reprend l'étape 8.4 (lien `/tt`), élargie à Instagram, YouTube et aux publications.
- **Rien ne change tant que `GC_MESURE=1` n'est pas posé** : rien n'est compté, `/tt`, `/ig`, `/yt`, `/r/…`,
  `/admin/stats` et `/api/admin/stats` répondent 404, `/legal` est inchangée. Le site lui-même ne change pas
  (`gamecenter_source.html` intact, cellule 427 inchangée).
- **Liens courts** : `snapline.live/tt`, `/ig`, `/yt` (bios TikTok, Instagram, YouTube) et `/r/<source>` (une
  publication : `/r/hn`, `/r/reddit-sideproject`, `/r/ph`… — minuscules, chiffres et tirets, 24 caractères au plus)
  renvoient à l'accueil (302, `noindex`) et comptent un clic (`lien:<source>`), sauf les robots et les aperçus de liens.
- **Visites** : chaque ouverture de l'accueil (`GET /`) compte `visite` et `visite:<source>` ; la source est le **nom**
  du site d'origine (en-tête `Referer`, `source_visite`) : `google`, `bing`, `duckduckgo`, `tiktok` (aussi l'application
  Android `com.zhiliaoapp.musically`), `instagram`, `facebook`, `youtube`, `reddit`, `hackernews`, `producthunt`, `x`,
  `bluesky`, `linkedin`, `operationsports`…, sinon `autre` ; `direct` sans en-tête (adresse tapée, favori, navigateur de
  TikTok qui ne dit rien) ; `site` depuis une page de Snapline. Les **robots** (moteurs, aperçus de liens, sondes,
  navigateurs sans écran comme celui du workflow « Vidéos », User-Agent vide) comptent `robot` à part ; les
  préchargements (`Sec-Purpose: prefetch`) et `HEAD` ne comptent pas. Ce sont des ouvertures de page, pas des
  visiteurs uniques (aucun identifiant).
- **RGPD** : rien que des totaux par jour (table `stats_day` : jour de Bruxelles, clé, nombre) ; ni cookie, ni adresse
  IP, ni identifiant, ni adresse complète du site d'origine : pas de consentement à demander. `/legal` le dit (phrase
  ajoutée sous *Audience statistics*, seulement avec `GC_MESURE=1`).
- **Tableau de bord** `/admin/stats` (en français, clé `GC_ADMIN_KEY` tapée dans la page, gardée dans l'onglet ; 10
  essais faux par adresse en 15 min ; `noindex`) : tuiles de la semaine en cours (visites, venues des réseaux, clics,
  nouveaux joueurs, comptes créés, joueurs actifs ; écart avec la semaine d'avant), **ligne du bilan du lundi** (la
  semaine finie, à coller dans `programme/Promotion.md`, bouton « Copier la ligne »), 12 semaines (visites, robots,
  réseaux, liens, joueurs, comptes, actifs, paris, ligues, adhésions, rappels, messages du chat), sources et liens
  courts sur 6 semaines. Semaines du lundi au dimanche, heure de Bruxelles. Les **joueurs** (clé créée au premier pari
  ou à la première cloche), **comptes**, **actifs** (au moins un pari ou un message du chat), paris, ligues, rappels et
  messages viennent de la base : ils sont comptés **depuis le début**, sans attendre la mesure. `GC_STATS_EXCLURE` :
  pseudos de comptes à ne pas compter (les siens), séparés par des virgules.
- **API** : `POST /api/admin/stats` `{key, semaines}` (1 à 52, 12 par défaut) → `{depuis, exclus, semaines: [{debut,
  visites, robots, sources, liens, joueurs, comptes, actifs, paris, ligues, adhesions, rappels, messages}], total}`.
- **Tests** : `moteur/tests/test_mesure.py` (interrupteur, sources, visites et robots, liens courts, clé et essais,
  semaines et changement d'heure, totaux tirés de la base et comptes exclus, page légale), `outils/site/test_mesure.js`
  (groupe site : deux serveurs, avec et sans `GC_MESURE` ; redirections, visite venue de TikTok, robot à part, tableau
  de bord, session, téléphone 390 px, mode sombre, page légale ; `SHOTS=<dossier>` pour les captures).

### 78. Onglet « Insights » et retrait d'Exhibition (28/10/2026)
**Insights** (barre latérale, avant « My bets ») : les statistiques de la semaine en cours pour parier plus
intelligemment, calculées par le serveur (`moteur/insights.py`, `/api/insights`) sur les **seuls matchs terminés** à
l'heure du serveur (jamais un résultat avant la fin du match). Gardées en mémoire et recalculées dès qu'un match se
termine (≈ 0,2 s pour 240 matchs) : le site redemande les chiffres à chaque match fini.
- **This week** : quatre chiffres de la ligue (points par match, victoires à domicile, des favoris, overs) ;
  **Betting angles** (six indices au plus, deux par genre, sur 8 matchs ou plus d'une équipe : contre le spread ≥ 70 %,
  over / under ≥ 70 %, chance ≥ 1,5 victoire) ; **Power table** (rating = marge moyenne corrigée du calendrier, SRS ;
  bilan, points marqués / encaissés, ATS, O-U, yards par action attaque · défense, Luck, 5 derniers matchs).
  Luck = victoires moins les victoires attendues par les cotes du moteur d'avant-match.
- **Head-to-head** : deux listes de franchises, un clic change l'équipe (autant de fois qu'on veut ; une équipe ne se
  choisit pas contre elle-même) ; 14 statistiques côte à côte, leur match de la semaine (résultat ou coup d'envoi,
  chance de victoire du moteur, spread, total) et quelques lectures.
- **Day recap** : un onglet par jour joué : matchs, points, surprises (plus grosses cotes d'abord), meilleure performance
  d'un match (passe, course, réception), match le plus prolifique et le plus serré, avec Replay.
- **Cadenas** : le Day recap est ouvert à tous (gratuit pour de bon). This week et Head-to-head sont réservés aux
  comptes listés dans `GC_INSIGHTS_USERS` (pseudos séparés par des virgules, sans tenir compte des majuscules ;
  un invité n'y a jamais accès). Les autres voient un aperçu flouté dessiné avec des **chiffres factices** : l'API ne
  leur envoie ni le tableau, ni les indices, ni les chiffres de la ligue. Le bouton « Unlock · €4.99 » est inactif
  (« Coming soon ») : paiement unique à brancher plus tard, quand l'audience sera là.
- Interrupteur `GC_INSIGHTS` (`off` : ni bouton, ni vue, ni API ; le site d'avant, sans Exhibition).
- Tests : `moteur/tests/test_insights.py` (calcul, matchs finis seulement, accès, interrupteur) et
  `outils/site/test_insights.js` (invité, compte hors liste, compte autorisé, téléphone 390 px, interrupteur).

**Exhibition retirée** : l'onglet, `/api/exhibitions`, `data/exhibitions`, `outils/exhibition/` et le workflow
« GameFeeds d'exhibition » (`.github/workflows/gamefeeds.yml`). Les deux matchs (`exh-v41`, `exh-v42`) ne sont plus
servis : ils restent des matchs de test des suites navigateur (`outils/site/matchs/`). Le bouton « Load GameFeed » du
replay reste.

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

### 79. AdSense refusé (« contenu à faible valeur ») : accueil sans valeurs de maquette et pages des franchises (29/10/2026)
**Constat** : Google AdSense a refusé `snapline.live` (« annonces sur des pages sans contenu d'éditeur », « contenu à
faible valeur informative »). Le site est une seule page dessinée en JavaScript : le plan du site ne comptait que `/` et
`/legal`, le HTML de l'accueil environ 260 mots (dont 120 de texte : « What is Snapline? ») et des valeurs de maquette
visibles avant le chargement du script. **Demande de Guillaume (29/10)** : d'abord retirer ces valeurs, puis les pages
des franchises.
- **Accueil** (`gamecenter_source.html`) : plus de valeurs inventées dans le HTML d'origine — solde `$4,280.50` →
  `$0.00`, `+$482` → `+$0`, `87 Bets` → `0`, `54%` → `—`, compteurs Live / Upcoming / Results vides, surtitre « Sunday
  night slate · 11.8K watching » → « Every game played by the engine », « Season IV · Week 12 » → « This week », « 5
  boards » retiré ; avatar factice « O1 / Operator One » supprimé de l'en-tête ; « Sim engine V3 · 4 franchises »
  (resté de la semaine 1) → nombre réel de franchises ; « Reconnecting to the GameCenter server… » → « Reconnecting
  to Snapline… ». Le script remplace toujours ces valeurs dès le chargement (rien ne change à l'écran ensuite). Liens
  vers `/teams` dans « What is Snapline? » et le pied de page.
- **Pages des franchises** (`pages_franchises.py`, rendues par le serveur, lisibles sans JavaScript, style de `/legal`,
  clair / sombre) : **`/teams`** (les 24 franchises par conférence et division, « How the league works ») et
  **`/teams/<nom>`** (`/teams/cortex-foxes` ; `/teams/ctx` y renvoie, 301). Chaque page : texte écrit pour la
  franchise (devise, trois paragraphes, points forts et faibles — `TEXTES`, en anglais, ≥ 120 mots), identité,
  coordinateurs, notes des unités, titulaires (effectif du début de semaine), histoire de la franchise (semaines
  **terminées** seulement : saisons, bilan, playoffs, finales, titres) et ses Grand Finals, rivaux de division, lien
  vers le direct. ≈ 600 mots par page. Ajoutées au plan du site (27 adresses). Pas de publicité sur ces pages pour
  l'instant.
- **À faire par Guillaume** : attendre que Google ait exploré les nouvelles pages (Search Console → Sitemaps →
  renvoyer `/sitemap.xml`, puis *Inspection de l'URL* sur `/teams`) avant de redemander l'examen AdSense. Suite
  prévue : comptes rendus écrits des matchs, récapitulatifs de semaine, guides.
- **Tests** : `moteur/tests/test_franchises.py` (un texte par franchise, pages, échappement, routes, plan du site).
  Cellule 427 : rien à reporter (partie du site seulement).

### 80. Comptes rendus écrits des matchs (AdSense, suite — 29/10/2026)
**Demande de Guillaume (29/10)** : après les pages des franchises (section 79), un compte rendu écrit pour chaque match.
- **Pages** (`comptes_rendus.py`, rendues par le serveur, lisibles sans JavaScript, style de `/legal`) :
  **`/games/<id>`** (compte rendu d'un match), **`/weeks/<n>`** (résultats d'une semaine par tour, playoffs, résumé de
  la saison quand elle est terminée : champion, meilleur bilan, leaders) et **`/games`** (derniers matchs, toutes les
  semaines). **Matchs terminés seulement** : un match à venir ou en cours répond 404 et n'est pas dans le plan du site.
- **Le compte rendu** (≈ 640 à 1 000 mots, 860 en moyenne sur les 1 155 matchs du dépôt) : tableau de marque par quart ;
  récit en six paragraphes — scénario (match nul, dernière seconde, remontée, large victoire, bataille défensive,
  festival offensif, match serré ; surprise ou favori d'après les cotes d'avant-match), déroulé (premiers points,
  mi-temps, dernier quart), action décisive (la plus grande hausse de probabilité de victoire en faveur du gagnant,
  hors fin du temps), joueur du match et autres performances, plan de jeu des deux staffs (et ce qu'a fait le joueur
  ciblé), conséquences (bilans de la semaine, qualification, titre ; quatrièmes tentés ; blessures sérieuses) — puis
  résumé des points, statistiques d'équipe (yards, troisièmes et quatrièmes, pertes de balle, sacks, possession) et
  feuilles individuelles. Les actions sont racontées d'après leurs champs (passeur, porteur, gain), pas le texte du
  direct (parfois coupé). Les tournures varient d'un match à l'autre, fixées par l'identifiant du match.
- **Liens** : « Latest games » (6 derniers comptes rendus) sur chaque page de franchise ; « Results & recaps » dans le
  pied de page du site, des pages franchises et « What is Snapline? ». Plan du site : `/games`, `/weeks/<n>`, et
  chaque match terminé (≈ 1 100 adresses avec les semaines du dépôt). Comptes rendus gardés en mémoire (64).
- **Tests** : `moteur/tests/test_comptes_rendus.py` (tous les matchs d'une semaine : points du résumé = score final,
  texte propre ; finale ; rien avant la fin d'un match ; page de semaine et index ; lien depuis la franchise).

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
| GET | `/api/chat?room=&after=&upto=&rev=` | chat : messages d'un salon (si `GC_CHAT` = `read` ou `on`, section 71) |
| POST | `/api/chat/status`, `/post`, `/delete`, `/report` | chat : état du joueur, écrire, effacer, signaler (section 71) |
| POST | `/api/admin/chat` | chat : modération avec `GC_ADMIN_KEY` (section 71) |
| GET | `/admin/chat` | chat : page de modération (si `GC_CHAT` = `read` ou `on`, section 72) |
| GET | `/teams`, `/teams/<nom>` | pages des franchises, lisibles sans JavaScript (section 79) |
| GET | `/games`, `/weeks/<n>`, `/games/<id>` | résultats et comptes rendus écrits des matchs terminés (section 80) |
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
README section 46) · `GC_ADSENSE_CLIENT`, `GC_ADSENSE_SLOTS` (publicités) · `GC_CF_ANALYTICS` (jeton Cloudflare Web Analytics,
statistiques d'audience, README section 50) · `GC_HIST_DEPUIS` (première semaine comptée dans History, défaut 2,
README section 52) · `GC_EDITEUR`,
`GC_EDITEUR_ADRESSE`, `GC_CONTACT` (mentions légales de `/legal`), README section 47 · `GC_CHAT` (`off` par défaut, `read`, `on` : le chat,
section 71) · `GC_CHAT_DAYS` (conservation des messages du chat, défaut 30 jours) · `GC_MESURE=1` (liens
courts `/tt` `/ig` `/yt` `/r/…`, visites comptées, tableau de bord `/admin/stats`, section 77) · `GC_STATS_EXCLURE`
(pseudos exclus du tableau de bord) · `GC_INSIGHTS` (`off` : pas d'onglet Insights), `GC_INSIGHTS_USERS` (pseudos qui
ont tout l'onglet), section 78.

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
