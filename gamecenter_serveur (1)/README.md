# GameCenter — serveur de direct

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

Chaque **samedi vers 3 h** (Bruxelles), GitHub exécute le notebook et produit la semaine suivante (~20 min),
en reprenant les staffs ajustés de la semaine jouée. Il l'ajoute au dépôt ; Railway voit la mise à jour et
redémarre le site (≈ 1 min, en pleine nuit, aucun match en cours). Le dimanche à la même heure, un second
passage rattrape un échec éventuel (sinon il ne fait rien). Le lundi 00 h, le site passe à la nouvelle semaine.
GitHub envoie un e-mail si un calcul échoue.

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
  `GC_TEST_HOOK=1 uvicorn serveur:app --port 8103` puis `node outils/audio/test_parite_v01.js data/weeks 8103` (Playwright).

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
`GC_ADMIN_KEY` (sauvegardes) · `GC_DEMO_AT` (ISO ou `auto` : décale l'horloge, pour une démonstration) · `PORT`.

## Test

`python3 tserver.py data gamecenter_source.html` — démarre le serveur à plusieurs moments de la semaine du
2026-10-05 et vérifie : aucune fuite, actions à l'heure, paris acceptés/refusés, règlement serveur = moteur = page,
classement, nom, playoffs révélés au bon moment.

## Limites (prototype)

Un seul processus ; SQLite ; pas de vrais comptes (effacer les données du site perd l'accès) ; pas de limite de
requêtes ; un pari en direct est pris au prix de la dernière action **jouée** (le bulletin propose alors la nouvelle cote).
