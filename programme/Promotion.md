# Promotion de Snapline — étape 8 (TikTok, puis Instagram Reels et YouTube Shorts)

Plan validé par Guillaume le 13/10/2026. Une étape = une PR, testée en local, fusionnée par Guillaume.
Matière première : le workflow **« Vidéos »** (README du serveur, section 46) — l'action du jour chaque soir, le résumé
du plus beau match le dimanche, avec leurs légendes anglaises, dans les *Artifacts* de l'exécution (30 jours) ;
publication **à la main** (aucun connecteur TikTok).

| # | Étape | État |
|---|---|---|
| 8.1 | Ce plan, photo de profil (`outils/promotion/`) | ✅ 13/10 (cette PR) |
| 8.2 | Générateur — action du jour pour TikTok : accroche, enjeu, zones sûres, terrain agrandi, appel à l'action, légendes par réseau ; « Best play so far » (post épinglé n° 2) | ✅ 13/10 |
| 8.3 | Qualité (tournage image par image, 1080×1920 natif, 60 images/s) ; résumé court ≈ 60 s (« Game in 60 seconds », post épinglé n° 3 ; le long seulement à la demande) ; « What is Snapline? » (post épinglé n° 1) | ✅ 13/10 |
| 8.4 | Mesure — lien `snapline.live/tt` compté par le serveur (TikTok seulement, choix du 13/10) | **en attente** : pas de lien cliquable avant 1 000 abonnés (section 8) |
| 8.4 bis | Adresse visible dans les vidéos (badge « snapline.live », carton « Type it in your browser ») et commentaire à épingler dans le `.txt` | ✅ 13/10 |
| 8.5 | Instagram Reels et YouTube Shorts ; bilan après 2 semaines | à faire |
| 8.6 | Autres formats (demande de Guillaume, 13/10) : voir section 7 | à faire |
| — | Plus tard (à décider) : voix du commentaire du site + sous-titres incrustés (revient sur le choix du 12/10 « son du stade seulement ») ; image de couverture `.jpg` | — |

## 1. Le compte

- **Type : compte personnel** (choix du 13/10) : il peut utiliser les sons tendance ; un compte « Entreprise » n'a
  droit qu'à la bibliothèque de musique commerciale. Le lien cliquable dans la bio n'arrive qu'avec assez d'abonnés
  (seuil à vérifier dans l'appli, il change) : d'ici là, « snapline.live » est écrit dans la bio et sur chaque vidéo.
- **Nom d'utilisateur** : `@snapline.live` (sinon `@snaplinefootball`). **Nom affiché** : « Snapline · AI Football ».
  Le même partout (Instagram, YouTube) dès le début, pour réserver le nom.
- **Photo de profil** : le logo du site (ballon blanc sur le dégradé cyan → violet → rose de l'en-tête et de `/og.png`),
  `gamecenter_serveur (1)/outils/promotion/photo_profil.png` (1080×1080 ; le réseau l'affiche en rond, le ballon reste
  dans le cercle). Refaite par `node outils/promotion/faire_profil.js` si le logo change.
- **Bio** (80 caractères au plus) : `24 teams. 24 AI coaches. Every game simulated live 👇 snapline.live`
- Les vidéos ne montrent pas les paris : pas besoin du réglage « contrôle de l'audience » (vidéos réservées aux adultes,
  qui réduit la portée) ; la mention 18+ est sur le site. Dans les réglages : compte public, commentaires ouverts, téléchargements des vidéos autorisés
  (le partage aide la portée).
- **Ne jamais parler des paris sur les réseaux** (ni bio, ni légende, ni texte à l'écran, ni réponse aux
  commentaires) : TikTok restreint les contenus liés aux jeux d'argent, même en argent fictif. On montre les matchs, les
  IA, les records ; le site fait le reste. Pas de « NFL » à l'image ni rien qui laisse croire à un lien officiel.

## 2. Rythme et heures

- **Chaque jour : l'action du jour** (au moins 4 semaines sans trou — la régularité compte plus que le volume).
  **Le lundi : le résumé court** (≈ 60 s) du match de la semaine. **Que des formats courts** sur les réseaux (choix du
  13/10) : ils donnent envie d'aller sur le site, où les replays montrent les matchs entiers.
- **Publication programmée** depuis l'ordinateur : TikTok Studio (tiktok.com → *Upload* → *Schedule*). La vidéo arrive
  vers 23 h (Bruxelles) dans les *Artifacts* ; le matin, la télécharger et la programmer (≈ 5 min).
- **Deux créneaux testés pendant 2 semaines**, puis on garde le meilleur (statistiques, section 5) :
  **19:00 à Bruxelles** (soirée européenne, midi aux États-Unis) un jour sur deux, **01:00 à Bruxelles** (19:00 sur
  la côte Est) l'autre jour. Changements d'heure : 25/10 en Europe, 01/11 aux États-Unis (une semaine à 5 h d'écart
  au lieu de 6).
- Répondre aux commentaires dans l'heure qui suit la publication quand c'est possible (la réponse en vidéo est un
  format à part entière).

## 3. Formats qui marchent (sport et simulations)

1. **La série numérotée** : « Day 12 of an AI-only football league » — on suit un feuilleton.
2. **La décision de l'IA** — notre angle unique : « The AI coach went for it on 4th & 9 from his own 30 » (les
   « décisions folles » de `choisir.py`).
3. **La bascule** : « 12% → 91% in one play » (probabilité de victoire avant / après).
4. **« Who wins tomorrow? »** : l'affiche du lendemain, réponse dans la vidéo suivante — des commentaires, et une
   raison d'aller voir le match en direct.
5. **Records et carrières** (onglet History) : « New single-season rushing record », le joueur d'une franchise.
6. **Rivalités et identités** des franchises (bible des identités) : les mêmes équipes reviennent, on s'y attache.

Texte à l'écran dès la 1re seconde, une seule idée par vidéo, la fin qui renvoie au début (la boucle allonge le temps
regardé), une question en légende.

## 4. Légende, hashtags, musique

- **Légende** : une phrase d'accroche + une question (« Would you go for it? ») + `snapline.live`. 3 à 5 hashtags au
  plus : `#americanfootball #football #simulation #ai #playoftheday` (`#nfl` possible pendant la saison, pour être
  trouvé). Depuis l'étape 8.2, le `.txt` de chaque vidéo a trois blocs prêts à copier : TikTok, Instagram, YouTube
  Shorts.
- **Musique** : le son du stade reste le son original de la vidéo (d'autres peuvent le réutiliser). Option : un son
  tendance à **5-10 %** du volume, ajouté dans l'éditeur de TikTok au moment de publier.
- **Couverture** : choisir l'image de l'action (pas un carton vide).

## 5. Premiers posts (semaine de lancement)

Avant le premier post : compte créé, photo, bio, nom réservé sur Instagram et YouTube. Puis 3 à 5 vidéos la première
semaine, **les trois premières épinglées** :
1. **« What is Snapline? »** (≈ 20 s) : 3 actions à la suite avec le texte « 24 teams · 24 AI coaches · every game
   simulated live » : Actions → « Vidéos » → *Run workflow* → type `presentation`.
2. **La plus belle action** jusqu'ici (un game-winner) : Actions → « Vidéos » → *Run workflow* → type `meilleure`.
3. **Le résumé court** du dernier grand match : type `resume` (le dimanche, il est produit tout seul).
Ensuite, le rythme de la section 2.

## 6. Mesurer ce qui marche

- **TikTok Studio → Analytics** (gratuit, activé d'office) — pour chaque vidéo : vues, **durée moyenne regardée**,
  **% regardé en entier**, **courbe de rétention** (part qui part dans les 2 premières secondes), part des vues venant
  de « Pour toi », partages, commentaires, abonnés gagnés, visites du profil ; pour le compte : heures où les abonnés
  sont là, pays.
- **Visites du site venues des réseaux** (étape 8.4) : `snapline.live/tt`, `/ig`, `/yt` redirigent vers l'accueil et
  sont comptés par le serveur (sans cookie). Search Console ne voit que Google (recherches, impressions, pages
  indexées) : il ne compte pas les visites venues de TikTok.
- **Bilan du lundi** (≈ 10 min), tableau ci-dessous : on garde le créneau, le format et la longueur qui gardent le plus
  de monde, on abandonne ce qui ne marche pas après 2 semaines.

| Semaine | Vidéos | Vues | Durée moy. / % en entier | Abonnés | Clics `/tt` | Comptes créés | Remarque |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## 7. Autres formats à produire (demande du 13/10, étape 8.6)
En plus de l'action du jour et du résumé, des posts tirés des données du site (semaines, onglet History, fiches) :
- **Joueur de la semaine** : les statistiques du meilleur joueur de la semaine (carte + ses plus belles actions).
- **Champion** : la victoire d'une équipe en **Grand Final**, avec ses plus belles actions de la semaine.
- **Match hors norme** : les chiffres d'un match (par exemple 102 points cumulés), avec les actions qui les ont faits.
- **Histoire d'une franchise** : titres, records, joueurs marquants (bible des identités, onglet History).
- Records battus, séries (victoires, défaites), « Who wins tomorrow? » (affiche du lendemain).
Le détail (lesquels, dans quel ordre, cartes fixes ou action filmée) se décide au début de l'étape 8.6.

## 8. Amener les gens sur le site sans lien cliquable (13/10)
Un compte TikTok **personnel** n'a pas de lien cliquable avant **1 000 abonnés**. En attendant :
1. **Essayer le compte Entreprise** (réversible) : Paramètres → Compte → *Passer à un compte Entreprise* (catégorie
   Divertissement ou Sport) → *Modifier le profil* : si le champ **Site web** apparaît, y mettre
   `https://snapline.live` (avec `https://`, sinon le lien reste du texte). Selon les guides, un compte Entreprise a ce
   champ sans minimum d'abonnés (non confirmé par TikTok) ; on perd les sons tendance, mais nos vidéos ont leur propre
   son de stade. Si le champ n'apparaît pas : revenir au compte personnel.
2. **Instagram** : TikTok → *Modifier le profil* → *Liens* → Instagram (sans minimum) ; dans la bio Instagram, le lien
   `https://snapline.live` est cliquable tout de suite ; une Story par jour avec l'autocollant **lien** (« match en
   direct maintenant »). Avance l'étape 8.5.
3. **L'adresse partout** : nom d'utilisateur `@snapline.live` (c'est l'adresse), nom affiché avec « snapline.live »,
   **commentaire épinglé** sous chaque vidéo (bloc « Pinned comment » du `.txt`), badge et carton final dans la vidéo
   (étape 8.4 bis), format « Who wins tomorrow? » (le match se regarde sur le site).
4. **Liens cliquables ailleurs**, une publication soignée chacun : Reddit (r/SideProject, r/WebGames,
   r/InternetIsBeautiful, communautés de football américain et de simulation — lire leurs règles), Hacker News
   « Show HN », Product Hunt, X / Bluesky.
5. Plus tard, payant : TikTok **Promote** avec l'objectif « visites du site web », quand on sait quelles vidéos
   accrochent.
