# Lancement de Snapline dans les communautés — étape 9.4

Préparé le 29/10/2026 (plan validé le 28/10, `Promotion.md` section 9). **Guillaume publie à la main**, une communauté tous
les 2 ou 3 jours. Claude a préparé les textes (en anglais) et relevé les règles. Les textes sont à copier tels quels ou à
retoucher : ils sont écrits à la première personne, c'est Guillaume qui parle.

## 1. Règles communes (à relire avant chaque publication)

- **Une seule fois par communauté.** On ne republie pas le même lien si ça ne prend pas. On n'ouvre pas non plus un
  second compte.
- **Ne jamais parler de paris**, même en argent fictif : ni dans le titre, ni dans le texte, ni dans les réponses. Rien
  qui laisse croire à un lien avec la NFL. Si quelqu'un pose la question, voir la réponse préparée n° 4 (section 4).
- **Ne jamais demander de votes** (upvote, « like », « support us »), ni en public ni en message privé. On ne demande
  pas non plus à des amis de voter. C'est interdit sur Hacker News, Reddit et Product Hunt, et ça peut faire supprimer le
  post ou bannir le compte.
- **Être là pendant les 3 heures qui suivent** pour répondre aux commentaires : c'est ce qui fait monter un post. Il faut
  répondre aux critiques avec calme, sur le fond, et remercier.
- **Rester honnête** sur ce que font les « IA » (section 4, réponse n° 1) : ce ne sont pas des modèles de langage.
- **Publier quand des matchs sont en direct** : du lundi au vendredi, de 10:00 à 22:00 (heure de Bruxelles), un match
  commence toutes les 30 minutes. Le créneau conseillé est **15:00 à Bruxelles** (14:00 UTC en hiver, 10:00 à New York),
  du mardi au jeudi. Les visiteurs tombent alors sur « Watch live now ».
- **Compter les visites** : `snapline.live/admin/stats` → « D'où viennent les visites » et « Liens courts ». Chaque
  publication a son lien `/r/<source>` (section 3). Sur Hacker News, on met l'adresse simple : le site d'origine
  (« hackernews ») est reconnu tout seul.

## 2. Calendrier proposé

| Jour | Où | Lien à publier | Pourquoi dans cet ordre |
|---|---|---|---|
| J0 (mar. ou mer.) | Hacker News, « Show HN » | `https://snapline.live` | Le public le plus large ; aime les projets techniques à essayer sans inscription |
| J+2 | Reddit r/SideProject | `https://snapline.live/r/reddit-sideproject` | Fait pour montrer un projet et recevoir des retours |
| J+4 | Reddit r/InternetIsBeautiful | `https://snapline.live/r/reddit-iib` | Grand public ; seulement si le compte Reddit respecte la règle des 90/10 (section 3) |
| J+6 | Communautés de simulation de football (après accord des modérateurs) | `/r/reddit-simfootball`, `/r/reddit-footballgm`, `/r/fofc` | Le public le plus proche, mais les règles sont à confirmer |
| J+9 | Product Hunt | `https://snapline.live/r/ph` | À préparer (images, premier commentaire) ; mieux après quelques retours |
| Au fil de l'eau | Indie Hackers, AlternativeTo, X / Bluesky | `/r/ih`, `/r/alternativeto`, `/r/x`, `/r/bluesky` | Liens entrants durables (référencement) |

Après chaque publication : noter la date, le lien et le résultat (votes, commentaires, visites de `/admin/stats`) dans la
colonne « Décision » du bilan du lundi (`Promotion.md`, section 9).

## 3. Les publications, une par une

### 3.1 Hacker News — Show HN

**Règles relevées** (page officielle [showhn.html](https://news.ycombinator.com/showhn.html), lue au travers de copies
et de guides : la session de Claude n'a pas accès au site lui-même) :
- un Show HN, c'est quelque chose que l'on a fait soi-même et que les autres peuvent **essayer tout de suite**, de
  préférence **sans inscription ni e-mail** → Snapline se regarde sans compte ✅ ;
- pas de page d'attente, pas de levée de fonds, pas de simple article ;
- il faut être là pour en discuter ;
- titre qui commence par « Show HN: », 80 caractères au plus, sans langage publicitaire (pas de « revolutionary »,
  « the best »…).

**À vérifier par Guillaume** : relire la page [showhn.html](https://news.ycombinator.com/showhn.html) et les
[guidelines](https://news.ycombinator.com/newsguidelines.html) le jour même. Le compte HN doit avoir un peu d'historique :
un compte tout neuf voit souvent ses posts bloqués.

**Comment publier** : news.ycombinator.com → *submit* → titre, URL `https://snapline.live`, puis le texte ci-dessous
**en premier commentaire** (c'est l'usage quand on met une URL).

**Titre** (78 caractères) :

```
Show HN: Snapline – AI coaches play a full American football season every week
```

**Premier commentaire** :

```
Hi HN! Snapline is a simulated American football league you can watch live in the browser, no sign-up.

24 fictional teams play a full season every week: a regular season Monday to Friday (a game kicks off every 30 minutes
from 10:00 to 22:00 Brussels time), two semifinals on Saturday and a Grand Final on Sunday. Every game is simulated snap
by snap and shown in real time on a 2D field, with play-by-play, win probability and the box score.

"AI coach" doesn't mean an LLM here. Each team has an offensive and a defensive coordinator, and they make the decisions
a real staff makes:

- 4th down: go for it, punt or kick, by comparing the win probability of each option;
- play calling that adapts to what works during the game, and a scouting file on every opponent (tendencies by down
  and distance, formation and field zone). Defenses key on those tendencies, and offenses notice when they're being
  read and break them;
- pre-snap reads and audibles, QB progressions under pressure, fatigue and rotations, injuries and penalties.

The engine is written in Python and runs once a week on GitHub Actions to produce the whole week of games. The site is
FastAPI + SQLite, with a single-page canvas front end. Games are computed ahead, but the server only reveals each play
when it happens on the clock, so a live game really is live for the viewer.

I'd love feedback on two things: does the play-by-play feel like football, and is it clear what the AI decided and why?
```

### 3.2 Reddit — r/SideProject

**Règles relevées** (sources secondaires : Claude n'a pas pu ouvrir Reddit) : la communauté sert à montrer un projet et
à **recevoir des retours** ; l'autopromotion est tolérée si l'on participe aussi (répondre, commenter les projets des
autres). Une communauté voisine, r/sideprojects (avec un « s »), a ses propres règles.

**À vérifier par Guillaume** : la barre latérale et les règles du jour (onglet *About*), et s'il faut un « flair ».
Commenter 2 ou 3 autres projets le jour même.

**Type** : publication texte. **Titre** :

```
I built a live American football league where AI coaches call every play
```

**Texte** :

```
Hi r/SideProject! For the past few weeks I've been building Snapline: https://snapline.live/r/reddit-sideproject

It's a simulated American football league you can watch live in the browser (free, no sign-up). 24 fictional teams play
a full season every week, and every game is simulated snap by snap and shown in real time on a 2D field.

Each team is run by AI coordinators (decision models, not chatbots): they decide 4th downs from win probability, adapt
their play calling during the game, keep a scouting file on each opponent, and try to break their own tendencies when
the defense starts reading them.

Stack: a Python simulation engine that runs once a week on GitHub Actions, a FastAPI + SQLite server, and a single-page
canvas front end.

What I'd like to know:
1. Is it clear in the first 5 seconds what the site is?
2. Would you come back to watch a game, and what would make you come back?

Thanks for any feedback, good or bad!
```

### 3.3 Reddit — r/InternetIsBeautiful

**Règles relevées** (copie de la barre latérale par un site miroir, peut-être ancienne) : règle des **90/10**, c'est-à-dire
que l'essentiel de l'activité du compte doit porter sur autre chose que ses propres sites. Pas de sites qui regroupent
le contenu d'autres sites, pas d'articles, vidéos ou images seuls.

**À vérifier par Guillaume** : les règles complètes (onglet *About*). **Ne publier que si le compte Reddit a déjà une
vraie activité ailleurs** ; sinon, sauter cette communauté. Il faut un lien direct vers le site, sans texte de pub.

**Type** : lien. **Titre** :

```
A football league where every game is played live by AI coaches, snap by snap
```

**Lien** : `https://snapline.live/r/reddit-iib`

### 3.4 Communautés de simulation de football

Le public le plus proche, mais **aucune règle d'autopromotion n'a pu être confirmée**. Il faut donc **écrire d'abord aux
modérateurs** (modmail sur Reddit, message privé sur le forum) avec le texte court ci-dessous, et ne publier qu'avec leur
accord.

- **r/Football_GM** (environ 8 000 membres, autour du jeu Football GM) : lien `/r/reddit-footballgm`.
- **r/SimulationFootball** (autour de la ligue ISFL) : lien `/r/reddit-simfootball`.
- **Front Office Football Central** (forum d'Operation Sports, partie « autres simulations textuelles ») : lien `/r/fofc`.

**Message aux modérateurs** :

```
Hi! I've built a free browser-based American football simulation where AI coordinators call every play and every game
is shown live, snap by snap (24 fictional teams, a full season every week). Would it be OK to share it once with your
community and ask for feedback? Totally fine if not. Thanks!
```

**Publication (une fois l'accord obtenu)**. Titre :

```
I made a sim league where AI coordinators call every play — 24 teams, a full season every week, watch it live
```

Texte :

```
Hi all, long-time fan of football sims here. I built Snapline: https://snapline.live/r/<lien de la communauté>

What might interest this community: the coordinators are decision models. They pick 4th-down calls from win probability,
self-scout and break tendencies, defenses key on what they've seen, and QBs go through progressions under pressure.
Fatigue, rotations, injuries and penalties are in. Every game is simulated play by play and shown live on a 2D field
with the box score; History keeps records and player careers across seasons.

I'd really value the opinion of people who know sims: what feels off, what's missing, what would you want to see?
```

### 3.5 Product Hunt (vers J+9)

**Règles relevées** (guides de 2026, pas la page officielle) : interdit de demander des votes, même en message privé ;
les votes de comptes très récents ou suspects sont retirés ; les commentaires comptent plus que le nombre de votes ; on
peut programmer le lancement jusqu'à un mois à l'avance.

**À préparer** :
- nom « Snapline », accroche de 60 caractères au plus : `AI coaches play a full American football season, live` ;
- 4 images 1270×760 : le terrain en direct, le journal de l'IA (un carton des vidéos), l'onglet History, le téléphone.
  Claude peut les produire sur demande ;
- premier commentaire du créateur : reprendre le texte de la section 3.1, en plus court.

**À vérifier par Guillaume** : les règles officielles le jour même (help.producthunt.com).

### 3.6 Liens durables (au fil de l'eau)

- **Indie Hackers** (indiehackers.com, publication « Show IH ») : reprendre le texte de r/SideProject, avec le lien `/r/ih`.
- **AlternativeTo** (alternativeto.net) : fiche de Snapline (application web gratuite, catégorie jeux de sport), proposée
  comme alternative à Football GM et Front Office Football. Lien `/r/alternativeto`.
- **X et Bluesky** : un compte `@snapline.live`, les vidéos du jour, le lien `/r/x` ou `/r/bluesky` dans la bio.

## 4. Réponses préparées (en anglais)

1. **« Is it ChatGPT / an LLM? »**

   ```
   No LLM. The coordinators are decision models: win probability for 4th downs, a scouting model of each opponent's
   tendencies, adaptive play calling, and QB reads with timing and pressure. Every decision is logged in the game feed,
   so the site can show what was decided and why.
   ```

2. **« Are the results decided in advance? »**

   ```
   Each week is simulated ahead of time (on Saturday, for the following week), but the server only reveals each play
   when it happens on the clock, so nobody watching can see how a game ends before it's played.
   ```

3. **« Why fictional teams? »**

   ```
   On purpose: no real league, team or player. Everything is invented, so the teams can build their own history.
   ```

4. **Une question sur les cotes ou l'argent visibles sur le site** → **à valider par Guillaume** (section 5, point 1).

5. **« Is it open source? / Can I coach a team? »** → **réponses à donner par Guillaume** (section 5, point 2). Pour
   l'instant, on peut suivre une équipe et recevoir un rappel avant ses matchs.

6. **Une critique** (lent, confus, moche…) :

   ```
   Thanks, that's really useful. [Ce que je vais changer, ou pourquoi c'est ainsi.]
   ```

   Puis noter la critique pour le bilan du lundi.

## 5. Décisions à prendre par Guillaume avant J0

1. **Les cotes à l'écran.** Les visiteurs des communautés verront les cotes et le solde en argent fictif, et quelqu'un
   demandera ce que c'est. Notre règle interdit d'en parler sur les réseaux. Deux options :
   - **A (conseillée)** : une réponse courte et honnête, sans le mot « paris » : *« There's an optional play-money mode
     (no real money, nothing can be bought or won, 18+). Snapline is about watching the AI coaches: you can ignore
     it. »* ;
   - **B** : ne pas répondre à cette question.
2. **Code source et participation** : le dépôt est public sur GitHub. Le dire, ou non ? Et peut-on « coacher » une
   équipe un jour, ou non ?
3. **Le compte** : Guillaume a-t-il des comptes HN et Reddit avec un peu d'historique ? Sinon, les créer dès
   maintenant et participer normalement quelques jours avant J0.
4. **L'aide d'une IA pour le code** : la mentionner ou non dans le texte de HN ? Le public de HN pose souvent la
   question, et y répondre franchement est mieux reçu.
