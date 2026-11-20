# Badges — fidélité, supporters, pronostics, communauté : plan de mise en place

Plan préparé le 20/11/2026 à la demande de Guillaume (« s'intéresser aux badges de manière générale et à ceux de
fidélité »). **Une conversation par étape**, comme pour le reste de la feuille de route : en début de conversation,
lire ce fichier, `programme/Feuille_de_route.md` et le `README.md` du serveur.

Rappel : le 07-09/11, le Front office avait écarté « tout système de points » et laissé « rapports et badges » pour
plus tard. Ce plan rouvre les badges, **sans points ni monnaie** : un badge se gagne par ce qu'on fait sur le site, il ne
s'achète pas et ne donne aucun avantage de jeu (pas plus de poids dans les votes, pas de mise en plus).

## Les principes proposés

1. **Fidélité à l'échelle de la semaine, pas du jour.** Une semaine = une saison, les matchs vont du lundi au vendredi
   et le week-end est une émission : une série de jours consécutifs punirait le visiteur qui ne vient pas le samedi. La
   fidélité se compte en **semaines actives** (au moins une visite connectée dans la semaine) et en **séries de
   semaines** consécutives ; les jours servent seulement à un badge « présent plusieurs jours de la même semaine ».
2. **Rien qui pousse à miser plus.** L'argent est fictif, mais le site doit rester loin des jeux d'argent (AdSense :
   catégorie bloquée ; 18+). Aucun badge pour le volume de mises, les pertes, les recharges ou le solde. Les badges de
   paris récompensent la **lecture du jeu** (une surprise vue venir, une journée parfaite), à mise libre.
3. **Comptes seulement.** Un invité n'est qu'une clé dans un navigateur : ses badges se perdraient. Il voit les badges
   (et sa progression) avec « Create an account to keep them ». À la création du compte, ce qu'il a déjà fait compte.
4. **Rétroactifs.** Au lancement, les badges se calculent sur l'historique déjà en base (paris, votes, ligues, franchise
   favorite) : les premiers fidèles les ont tout de suite. La fidélité (jours de visite) ne commence, elle, qu'au
   lancement — sauf « Founding fan », qui se lit sur la date de création du compte.
5. **Discrets et lisibles.** Une page « Badges » (gagnés, à gagner avec la progression), un toast quand on en gagne un,
   et **un badge mis en avant** (choisi par le joueur) à côté de son pseudo dans les classements et les ligues.

## Ce qui existe déjà (vérifié dans le code le 20/11)

| Donnée | Où | Sert à |
|---|---|---|
| Comptes : `players.login`, `acct_at`, `created` | `serveur.py`, table `players` | comptes seulement, « Founding fan », ancienneté |
| Franchise favorite : `fav_team`, `fav_team_at` | `players` | supporter fidèle (même franchise depuis N semaines) |
| Paris : `bets` (semaine, cote, mise, combinés `legs`, cash-out) ; règlement par le résultat du match | `bets`, calendrier de chaque semaine | surprise vue venir, journée parfaite, combiné gagné |
| Classement de la saison (`season_rows`) et ligues privées (`leagues`, `league_members`) | `serveur.py` | top de la saison, fondateur de ligue, vainqueur de ligue |
| Votes des supporters : `fan_votes` (semaine, levier, choix) ; draft (mêmes votes, levier de la draft) | `fan_votes` | voter chaque semaine, la draft |
| Réponses aux questions des articles : `news_votes` | `news_votes` | lecteur de News |
| Rappels Web Push : `push_subs`, `push_bells` | | rien (pas de badge pour s'abonner) ; notifier un badge gagné |
| Ouverture du site par un joueur connu : `/api/me` (appelé au chargement de la page) | `serveur.py` | **le point où noter la visite du jour** |
| Visites : seulement des totaux par jour (`stats_day`) | | **manque** : les jours de visite de chaque compte |

**À ajouter** : une table `player_days(player, day)` (une ligne par compte et par jour de Bruxelles, écrite par
`/api/me` au plus une fois par jour) et une table `player_badges(player, badge, tier, at, week)`.

## Le catalogue proposé (noms anglais affichés, comme le site)

Paliers bronze / argent / or quand un badge se répète. Entre parenthèses : la règle.

**Fidélité**
- **Founding fan** — compte créé avant la date fixée par Guillaume (unique, jamais plus attribuable ensuite).
- **Season ticket** — semaines actives : 4 (bronze), 12 (argent), 24 (or), 52 (« Legend »).
- **On a streak** — semaines actives consécutives : 3, 8, 16.
- **Every day this week** — présent 5 jours sur les 7 d'une même semaine.
- **Opening day** — présent le lundi d'ouverture de la semaine ; **Grand Final night** — présent le soir de la Grand Final.

**Supporter**
- **True fan** — la même franchise favorite depuis 4, 12, 24 semaines.
- **Front office regular** — a voté au vote des supporters 4, 12, 24 semaines.
- **Draft day** — a voté à une draft ; **Scout's pick** — le prospect qu'il a choisi a été drafté.
- **Called the vote** — son choix a été celui de la majorité des supporters, 5 fois.

**Lecture du jeu** (paris en argent fictif, sans regard sur la mise)
- **Upset caller** — a gagné un pari « vainqueur » à +200 ou plus.
- **Perfect day** — tous ses paris d'une journée gagnés, 3 au moins.
- **Combo** — un combiné de 3 sélections ou plus gagné.
- **Top of the league** — premier de sa ligue privée à la fin d'une semaine (3 membres au moins).
- **Top 10** — dans les 10 premiers du classement de la saison à la fin d'une semaine.

**Communauté**
- **League founder** — a créé une ligue qui compte 3 membres ou plus ; **Recruiter** — 5 membres arrivés dans ses ligues.
- **Newsroom** — a répondu à 10, 50, 150 questions d'articles.

**Plus tard (à décider)** : *Watched it live* (un match regardé en direct jusqu'au coup de sifflet final : demande que le
site le signale au serveur), badges liés à « Read the AI » ou « Play of the week » si ces idées sont faites, un badge
**Insights Pro** (« Supporter ») si le paiement unique est un jour branché.

## Le chemin des données

```
site ── /api/me (chargement de la page) ──> serveur : player_days (une ligne par compte et par jour)
                                              │
moteur/badges.py ── evaluer(compte, données lues en base, semaines) ──> badges dus (et progression)
                                              │  au chargement (/api/badges) et le lundi (révélation)
                                              ▼
                                   player_badges (gagnés une fois, datés) ── toast « Badge unlocked »
                                              │
site : My account › Badges · badge mis en avant à côté du pseudo (classements, ligues) · Web Push (facultatif)
```

`moteur/badges.py` reste **pur** (des listes en entrée, des badges en sortie) : testable sans serveur, comme
`moteur/insights.py` et `moteur/ngs.py`. Un badge gagné ne se retire jamais (même si la franchise favorite change).

## Les étapes

### BD-0 — Plan *(ce fichier)* — ✅ 20/11
Catalogue, principes, données existantes, découpage. Points à décider ci-dessous.

### BD-1 — Module des règles + jours de visite *(module + serveur, sans site)* — ✅ 20/11 (README section 130)
- `moteur/badges.py` : le catalogue (clé, nom, description, paliers, catégorie) et `evaluer(...)` → badges dus et
  progression vers le palier suivant ; tests `moteur/tests/test_badges.py` (chaque règle, paliers, séries de semaines
  avec trous, rien pour un invité, rien pour la mise ou les recharges).
- Serveur : table `player_days`, écrite par `/api/me` une fois par jour (comptes seulement) ; table `player_badges`.
- Outil `outils/badges_rapport.py` : sur une copie de la base de production (lecture seule), combien de comptes
  auraient chaque badge au lancement (pour régler les seuils avant d'afficher quoi que ce soit).

### BD-2 — Serveur : attribution et API *(serveur)*
- `/api/badges?token=` : badges gagnés (datés), à gagner (progression), badge mis en avant ; `POST /api/badges/featured`.
- Attribution au chargement (`/api/badges`) et à la révélation du lundi ; rétroactive au premier calcul d'un compte.
- Le badge mis en avant renvoyé avec les lignes du classement de la saison et des ligues.
- Interrupteur `GC_BADGES=off` (ni API ni affichage). Tests serveur sur une copie des données.

### BD-2 bis — Créer un compte et choisir sa franchise *(site + serveur)*
- Une entrée visible pour un invité : bouton « Create account » dans la barre du haut (à la place du solde avant le
  premier pari, voir section 127) et invitations au bon moment (après un premier pari gagné, au vote des supporters,
  sur la page Badges : « Create an account to keep them »).
- Un parcours court en deux écrans : pseudo + mot de passe (la clé d'invité devient le compte : ses paris, ses jours et
  sa progression restent), puis **le choix de la franchise favorite** (grille des 24 logos, « Skip » possible), qui
  ouvre My team, le vote des supporters et True fan.
- Settings garde la gestion du compte (changer de franchise, se déconnecter) ; le formulaire du bas de Settings disparaît.
- À plan validé par Guillaume (écrans sur le vrai site, comme pour le Front office) avant de coder.

### BD-3 — Site *(site)*
- My account › **Badges** : grille des badges (gagnés en couleur, à gagner en gris avec la progression « 7 / 12 weeks »),
  choix du badge mis en avant ; toast « Badge unlocked » au moment où il est gagné ; le badge mis en avant à côté du
  pseudo dans Standings › Season, les ligues privées (et le chat si Guillaume le veut).
- Invité : la page avec la progression et « Create an account to keep them ».
- Icônes : un pictogramme par catégorie + la couleur du palier (pas d'image par badge au départ).
- Tests navigateur, captures, téléphone 390 px, mode sombre.

### BD-4 — Plus tard
- Web Push « You unlocked Season ticket · Silver » (abonnés seulement) ; récapitulatif du lundi (« New this week »).
- Badges des idées d'engagement si elles sont faites ; badge Insights Pro si le paiement est branché.

## Points décidés (Guillaume, 20/11/2026)

1. **Comptes seulement** : oui (les invités voient leur progression ; leurs jours de visite sont notés et comptent s'ils
   créent un compte).
2. **Badges de paris** : tous ceux du plan (Upset caller, Perfect day, Combo, Top of the league, Top 10), toujours sans
   rien sur la mise ni le volume. Garde-fou ajouté en BD-1 : Top 10 seulement une semaine où 30 comptes au moins sont
   classés (avec trois classés, tout le monde est « top 10 »).
3. **Founding fan** : compte créé au plus tard le **31/12/2026**.
4. **Badge mis en avant** : pas tranché ; par défaut, classements et ligues seulement (pas le chat).
5. **Badge Insights Pro** : oui.

**Remarque de Guillaume (20/11) — la création de compte.** Aujourd'hui, créer un compte demande d'aller tout en bas de
Settings, et le choix de la franchise favorite n'est pas mis en avant. Les badges ne valent que pour les comptes : il
faut donc une vraie entrée. Étape **BD-2 bis** ci-dessous, avant le site des badges.

## Garde-fous (définition de fini de chaque étape)

- Aucun badge pour la mise, le volume de paris, les pertes, les recharges ou le solde ; aucun avantage de jeu.
- Un badge ne se perd pas ; les règles sont déterministes (mêmes données, mêmes badges).
- Moteur, notebook et calcul du samedi inchangés.
- Tests locaux avant de pousser : `python -m unittest discover -s moteur/tests -t .`, tests navigateur du site ; PR aux
  contrôles verts. Section du README du serveur pour chaque étape mise en ligne ; ligne « Badges » de la feuille de route.
