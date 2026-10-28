# Refonte des playbooks — les 24 fiches (validées le 27/10/2026)

27/10/2026. Étape 1 : ce document compare l'identité voulue (bible, feuille de route) à ce que les franchises jouent
vraiment, et propose des cibles. **Fiches validées par Guillaume le 27/10** ; l'étape 2 (moteur) les applique : voir
« Décisions » et « Étape 2 — ce qui est joué » à la fin.

- **Mesure** : `python3 outils/moteur/identite_playbooks.py` (README du serveur, section 74), semaine 2026-10-26,
  35 080 appels de course ou de passe. Rapport complet : `Refonte_playbooks_mesure_2026-10-26.md`. Sur deux semaines
  (69 833 appels) les chiffres bougent à peine (écart moyen 0,059 au lieu de 0,062) : la mesure est stable.
- **Lecture** : « familles » = types de jeu (passes courtes, intermédiaires, profondes, écrans, play-action / bootleg,
  RPO, courses intérieures, en force, extérieures, option / QB). « Signature » = concept joué ≥ 3 % et ≥ 1,5 fois plus
  que la ligue. « Écart » = distance de Jensen-Shannon entre deux répartitions de concepts (0 = identiques, 1 = rien
  en commun). Un scramble compte comme la passe appelée.

## Le constat

| | Aujourd'hui | Cible proposée |
|---|---|---|
| Écart moyen à la ligue | 0,062 | **≥ 0,10** |
| Paires presque identiques (écart < 0,04) | 14 sur 276 (BST–MRD 0,019, BST–ONX 0,021, LTC–PLS 0,024…) | **aucune** |
| Franchises sans signature | 2 (CTX, GMB) ; 5 autres n'en ont qu'une | **≥ 3 signatures chacune** (sauf CTX, voir sa fiche) |
| Plays exclusifs (une seule franchise) | 3 sur 248 | **4 à 6 par franchise** (≈ 100–140) |
| Formation n°1 | SHOTGUN partout (16–29 %) | SHOTGUN n°1 seulement pour les équipes spread |
| Personnel 11 | 46 à 89 % (ligue ≈ 74 %) | 35 à 90 % selon l'identité |
| Motion | 3 à 7 % partout | 15–30 % pour les équipes « motion » (AXM, CPH, MRG, PRM, TDL, APX) |
| RPO | 0 à 4 % (ligue 1 %) | LTC 15–20 %, CPH / APX / PLS 6–10 % |

Ce qui marche déjà : VEC (vertical), MNL (puissance), NVA (shots), ZPH (passes), CPH (option), FRG (puissance) et la
défense blitz de GLT / VEC / GMB se reconnaissent. Ce qui ne se voit pas : les équipes « équilibrées » ou dont
l'identité est défensive (BST, ONX, MRD, AEG, GRZ, CTX, PRM, GMB, GLT en attaque) jouent presque le même menu, et la
plupart des identités « de situation » (zone rouge APX, 4e essai GMB, tempo PLS) n'ont pas d'effet visible sur le
choix des jeux.

Forme des cibles : familles en % des appels (± 3 points de tolérance), signatures avec part visée, formations et
personnel dominants, 4 à 6 plays exclusifs écrits « FORMATION + CONCEPT » (uniquement des formations et concepts qui
existent déjà dans le moteur), défense. Les plays exclusifs sont des **combinaisons** nouvelles de pièces existantes,
pas de nouvelles mécaniques.

---

## 01 · CTX — Cortex Foxes · « Adapt »
- **Bible** : équilibrée, adaptative, lit l'adversaire et exploite sa faiblesse ; pas de dominante fixe.
- **Aujourd'hui** : la plus proche de la moyenne (écart 0,033), aucune signature. Seul trait visible : option / QB
  7 % et RPO 4 % (au-dessus de la ligue). Défense sans relief (blitz 12 %).
- **Cibles** : l'identité de CTX est de **changer d'un match à l'autre**, pas d'avoir un menu à elle. Proposition : son
  menu de la semaine se penche vers ce qui marche contre l'adversaire (plus de passes contre une défense faible contre
  la passe, etc.), avec une amplitude plus forte que les autres (V21 adaptation renforcée pour CTX seulement). Mesure
  de réussite : écart entre ses matchs (d'un adversaire à l'autre) ≥ 2 fois celui des autres franchises, plutôt
  qu'un écart à la ligue.
- **Exclusifs (4)** : GUN_FLEX + Y_CROSS, PISTOL_WING + RPO_PEEK, SINGLEBACK_BUNCH + LEVELS, GUN_TRIPS_OPEN + SPOT_SNAG.
- **Défense** : variée exprès (aucun appel > 15 %), déguisements (paquets SIM_PRESSURE, COVER_3_MATCH).
- **Décision** : l'adaptation renforcée touche la logique V21 (pas seulement des poids) — à confirmer.

## 02 · VEC — Vector Strikers · « Attack »
- **Bible** : pass-first, tempo rapide, explosif, défense agressive.
- **Aujourd'hui** : déjà la plus typée (écart 0,147) : 83 % de passes, profondes 37 %, DEEP_POST 10 %, CORNER 9 %,
  FOUR_VERTS 8 %, gros gains 8,7 % (ligue 4,9). Défense blitz 41 %.
- **Cibles** : garder. Se distinguer de NVA par le **volume spread** : TRIPS / EMPTY / GUN_QUADS ≥ 40 %, personnel 11
  ≈ 90 %, play-action ≤ 8 % (le play-action, c'est NVA). Profondes 32–36 %, intermédiaires 22–25 %.
- **Exclusifs (5)** : GUN_QUADS + SWITCH_VERTICALS, EMPTY + DIVIDE, TRIPS + DOUBLE_POST, GUN_TRIPS_OPEN + DEEP_CROSS,
  EMPTY + FOUR_VERTS.
- **Défense** : blitz 35–40 %, homme ~20 % (inchangé).

## 03 · AEG — Aegis Sentinels · « Control »
- **Bible** : défense d'abord, attaque méthodique, possession contrôlée, limiter les gros jeux.
- **Aujourd'hui** : très proche de MRD (0,035). Courses intérieures + force 37 %, TRAP 5 %, profondes 3 % seulement.
  Défense COVER_3 / COVER_4 / MATCH_QUARTERS, blitz 9 %, DIME 27 %.
- **Cibles** : attaque **12 personnel** (25–30 %, ACE / SINGLEBACK_TIGHT), INSIDE_RUN + TRAP 15 %, PA_SLIDE 4 %,
  CURL + LEVELS 8 %. Profondes ≤ 5 %. Plus de courses en 1er & 10 (≥ 50 %).
- **Exclusifs (4)** : ACE + PA_SLIDE, SINGLEBACK_TIGHT + TRAP, ACE + LEVELS, SINGLEBACK_DEUCE + INSIDE_RUN.
- **Défense** : quarters / Cover 3 match 50 % ou plus, blitz ≤ 8 %, homme ≤ 5 %, gros gains concédés les plus bas.

## 04 · MNL — Monolith Rhinos · « Impose »
- **Bible** : course d'abord, puissance, courte distance, ligne de but, gestion de l'horloge.
- **Aujourd'hui** : bien typée (0,119) : 43 % de passes, POWER 19 %, POWER_TOSS 3 %, 11 personnel 46 %. Mais
  SHOTGUN reste la formation n°1 (16 %) et la plus proche est FRG (0,035).
- **Cibles** : **gap / puissance sous le centre** : I_FORM + HEAVY + JUMBO + PISTOL_FULL_HOUSE ≥ 35 %, personnel
  21 / 22 ≥ 45 %, SHOTGUN ≤ 10 %. POWER + COUNTER + PIN_PULL + BUCK_SWEEP ≈ 35 %. Passes 38–42 %, presque toutes
  play-action ou courtes.
- **Exclusifs (5)** : JUMBO + POWER, I_FORM + BUCK_SWEEP, PISTOL_FULL_HOUSE + PIN_PULL, HEAVY + WHAM,
  I_FORM_WING + PLAY_ACTION.
- **Défense** : 4_3, BOX_STACK et front lourd contre la course (inchangé).
- **Distinction FRG** : MNL = sous le centre, gap / toss, 21–22 personnel ; FRG = zone intérieure / duo depuis
  SINGLEBACK / ACE en 12.

## 05 · AXM — Axiom Falcons · « Execute » (West Coast)
- **Bible** : précision, efficacité, timing, passes courtes, motion.
- **Aujourd'hui** : passes courtes 32 %, STICK / CURL / MESH / DAGGER en signatures. Motion 4 % seulement, plus proche
  ONX (0,032).
- **Cibles** : courtes 35 %, intermédiaires 18 %, **motion 20–25 %**, BUNCH + SINGLEBACK_BUNCH ≥ 12 %, SPOT_SNAG +
  PIVOT + CHOICE 8 %, écrans ~8 %, profondes ≤ 6 %.
- **Exclusifs (5)** : BUNCH + SPOT_SNAG, SINGLEBACK_BUNCH + DRAG, GUN_Y_OFF + PIVOT, BUNCH + CHOICE,
  SINGLEBACK_WING_PAIR + Y_CROSS.
- **Défense** : zone propre (COVER_3_MATCH), peu de blitz — inchangé.

## 06 · GLT — Glitch Hornets · « Disrupt » (Blitz / Chaos)
- **Bible** : défense agressive et imprévisible ; attaque : terrains courts, play-action, écrans, coups profonds de
  situation, profiter des pertes de balle.
- **Aujourd'hui** : défense très typée (blitz 44 %, PRESS_MAN, MUG_BLITZ). Attaque : DRAW 12 % (×1,8) et rien d'autre ;
  très proche de PRM (0,042).
- **Cibles** : attaque **écrans + play-action** : écrans 12–14 %, PA / BOOT 12 %, DRAW 10 %, profondes en
  situation (1er & 10 après une perte de balle adverse : profondes ≥ 25 %).
- **Exclusifs (4)** : GUN_TIGHT + WR_TUNNEL_SCREEN, PISTOL + QB_DRAW, SINGLEBACK + FL_SE_SCREEN, GUN_WING + PA_FLOOD.
- **Défense** : blitz 40–45 %, stunts ≥ 20 %, déguisements (paquets « presented » ≠ réels) — inchangé, plus de stunts.

## 07 · CPH — Cipher Lynx · « Deceive » (Mobile / Option)
- **Bible** : QB mobile, option, RPO, motions jet / orbit, Pistol.
- **Aujourd'hui** : option / QB 12 % (READ_OPTION, SHOVEL_OPTION), BOOT 5 %, Pistol 10 %. Motion 6 %, RPO 1 %.
- **Cibles** : option / QB 20–25 % (READ_OPTION, POWER_READ, INVERTED_VEER, MIDLINE_OPTION, SPEED_OPTION), RPO 6–8 %,
  **PISTOL + PISTOL_STRONG + PISTOL_WING ≥ 25 %**, motion 20 % (JET_ACTION, JET_SWEEP).
- **Exclusifs (6)** : PISTOL + INVERTED_VEER, PISTOL_WING + SPEED_OPTION, GUN_WING + MIDLINE_OPTION,
  PISTOL_STRONG + POWER_READ, PISTOL + TRIPLE_OPTION, WILDCAT + QB_SWEEP.
- **Défense** : blitz 18 % (inchangé).

## 08 · NVA — Nova Raptors · « Explode » (Vertical / Big Play)
- **Bible** : vertical, play-action, max protect ; défense qui empêche les gros jeux.
- **Aujourd'hui** : profondes 29 %, PA 14 %, 12 personnel 15 %, CHAMP / DIVIDE / DOUBLE_POST en signatures.
  Défense two-deep (COVER_2, TAMPA_2, COVER_6). Bien typée (0,122), plus proche VEC (0,066).
- **Cibles** : se distinguer de VEC par **les shots en play-action depuis 12 / 21** : personnel 12 + 21 ≥ 35 %,
  ACE / SINGLEBACK / I_FORM ≥ 25 %, play-action 18–20 %, max protect (protection 7–8) sur les shots.
- **Exclusifs (5)** : ACE + PLAY_ACTION (max protect), I_FORM + DOUBLE_POST, SINGLEBACK + PA_FLOOD,
  ACE + DEEP_POST, I_FORM_WING + CORNER.
- **Défense** : two-deep ≥ 45 % (COVER_2 + TAMPA_2 + COVER_4 + COVER_6), blitz ≤ 8 %.

## 09 · PLS — Pulse Jackals · « Speed » (No-Huddle / Tempo)
- **Bible** : tempo, sans regroupement, **petit menu de concepts** répétés vite.
- **Aujourd'hui** : passes courtes 33 %, écrans 11 %, STICK / SHORT_OUT / MESH. Mais 179 plays différents et quasi
  jumelle de LTC (0,024).
- **Cibles** : **menu resserré** : ≤ 110 plays différents par semaine, 8 concepts = 60 % des appels. SHOTGUN + TRIPS +
  EMPTY ≥ 55 %, personnel 11 ≈ 90 %, courtes 35 %, écrans 12 %, RPO 6 %.
- **Exclusifs (4)** : GUN_TRIPS_OPEN + HITCH, EMPTY + STICK, GUN_TRIPS_TIGHT + FL_SE_SCREEN, SHOTGUN + RPO_ALERT.
- **Défense** : inchangée.
- **Distinction LTC** : PLS = peu de jeux, très vite ; LTC = RPO et lecture.

## 10 · ONX — Onyx Hawks · « Hunt » (Turnover / Ball Hawk)
- **Bible** : défense chasseuse de ballons (robber, trap, déguisements) ; attaque qui protège le ballon.
- **Aujourd'hui** : invisible : ballons récupérés 1,35 / match (= ligue), jumelle de BST (0,021) et MRD (0,029).
  Attaque : STICK 6 %.
- **Cibles** : défense COVER_1_ROBBER + BOX_ROBBER + COVER_3_BUZZ ≥ 30 %, déguisements ≥ 25 %. Attaque **à faible
  risque** : courtes + écrans ≥ 38 %, profondes ≤ 6 %, interceptions lancées les plus basses.
- **Exclusifs (4)** : GUN_Y_OFF + SHORT_OUT, SINGLEBACK + HITCH, GUN_FLEX + WR_TUNNEL_SCREEN, PISTOL + DART_QUICK_DIG.
- **Décision** : les choix de jeu seuls ne feront pas monter les ballons récupérés ; il faudrait un effet moteur
  (chance d'interception un peu plus haute sur les paquets robber / trap d'ONX). À valider.

## 11 · FRG — Forge Bison · « Dominate » (Trench Warfare)
- **Bible** : les tranchées : zone intérieure, duo, power, counter ; pression intérieure en défense.
- **Aujourd'hui** : POWER 12 %, TRAP 5 %, HEAVY 10 %, 11 personnel 56 % ; stunts 22 % (le plus haut). Jumelle de MNL
  (0,035).
- **Cibles** : **zone intérieure / duo depuis SINGLEBACK / ACE en 12** : personnel 12 ≥ 30 %, INSIDE_RUN + TRAP + WHAM
  ≥ 20 %, POWER ≤ 8 % (le POWER, c'est MNL), PA depuis 12 (PA_SLIDE, BOOT) 10 %.
- **Exclusifs (4)** : SINGLEBACK_NASTY + INSIDE_RUN, ACE + WHAM, SINGLEBACK_TIGHT + PA_SLIDE, STRONG + TRAP.
- **Défense** : 4_3, stunts 25 %, pression à 4 (blitz ≤ 12 %).

## 12 · MRD — Meridian Owls · « Territory » (Field Position)
- **Bible** : terrain, efficacité, horloge, Cover 2 / 3 qui plie sans rompre.
- **Aujourd'hui** : SCREEN 8 %, CURL 6 %, INSIDE_RUN 7 % ; jumelle de BST (0,019) et ONX (0,029).
- **Cibles** : **horloge et écrans** : courses ≥ 45 % quand elle mène, écrans 12 %, CURL + HITCH + SHORT_OUT 12 %,
  PONY / PISTOL ≥ 15 %. 4e tentés ≤ 5 % (elle dégage). Profondes ≤ 6 %.
- **Exclusifs (4)** : PONY + SCREEN, PISTOL + CURL, PONY + INSIDE_RUN, SINGLEBACK_WING + HITCH.
- **Défense** : COVER_2 + COVER_3 ≥ 50 %, homme ≤ 4 %, blitz ≤ 8 %.

## 13 · APX — Apex Vipers · « Finish » (Red Zone)
- **Bible** : zone rouge : RPO, play-action, motion, picks en BUNCH / STACK, power, mouvement du QB.
- **Aujourd'hui** : BOOT 5 % seulement. En zone rouge : courtes 24 %, force 19 %, PA 12 % — rien de propre.
- **Cibles** : **un paquet zone rouge** (≤ 20 yards) à elle : BUNCH + GUN_STACK ≥ 30 % en zone rouge, MESH_WHEEL /
  SPOT_SNAG / DRAG (picks) 20 %, RPO 10 %, motion 25 % en zone rouge. Ailleurs, attaque équilibrée.
- **Exclusifs (5)** : GUN_STACK + MESH_WHEEL, BUNCH + SPOT_SNAG (zone rouge), GUN_STACK + RPO_POWER,
  PISTOL_STRONG + QB_DRAW, BUNCH + PA_FLOOD.
- **Défense** : homme 14 % / robber (inchangé).

## 14 · LTC — Lattice Wolves · « Stress » (RPO / Spread)
- **Bible** : RPO, zone intérieure / extérieure, bubble / tunnel, stick, mesh, 3×1 / 2×2 / empty.
- **Aujourd'hui** : RPO 3 % seulement ; STICK / MESH en signatures ; jumelle de PLS (0,024).
- **Cibles** : **RPO 15–20 %** (RPO_INSIDE_ZONE, RPO_OUTSIDE_ZONE, RPO_PEEK, RPO_READ), écrans bubble / tunnel 12 %
  (FL_SE_SCREEN, WR_TUNNEL_SCREEN), option 5 %. GUN_TRIPS_OPEN / GUN_FLEX / EMPTY ≥ 30 %.
- **Exclusifs (5)** : GUN_TRIPS_OPEN + RPO_INSIDE_ZONE, GUN_FLEX + RPO_PEEK, EMPTY + MESH, SHOTGUN + RPO_OUTSIDE_ZONE,
  GUN_TRIPS_OPEN + WR_TUNNEL_SCREEN.
- **Défense** : inchangée.

## 15 · ZPH — Zephyr Condors · « Overload » (Air Raid)
- **Bible** : 4–5 receveurs, mesh, four verts, Y-cross, stick, shallow, spacing, dagger.
- **Aujourd'hui** : 80 % de passes, FOUR_VERTS / MESH / SAIL ; courte distance en course 23 % seulement.
- **Cibles** : passes 80 %, **MESH + Y_CROSS + FOUR_VERTS + STICK + DAGGER ≥ 30 %**, EMPTY + GUN_QUADS ≥ 20 %.
- **Exclusifs (5)** : GUN_QUADS + MESH, EMPTY + Y_CROSS, GUN_QUADS + FOUR_VERTS, EMPTY + DAGGER, GUN_TRIPS_OPEN + DRAG.
- **Décision** : le vrai Air Raid est en **10 personnel (4 WR)**, aujourd'hui bloqué (effectifs à 3 WR). Ouvrir un 4e
  WR dans les effectifs de ZPH (et VEC ?) touche les effectifs, pas seulement les playbooks.

## 16 · BST — Bastion Panthers · « Deny » (Coverage / Lockdown)
- **Bible** : press man, Cover 1 / 2 / 6, brackets ; attaque qui protège le ballon, efficace.
- **Aujourd'hui** : homme 10 %, blitz 6 % (le plus bas), défense quarters / Cover 2 sans press. Attaque INSIDE_RUN
  10 %. Jumelle de MRD (0,019) et ONX (0,021).
- **Cibles** : **défense homme / press 25–30 %** (PRESS_MAN, MAN, COVER_1), COVER_6 10 %, blitz ≤ 6 %. Attaque
  courses intérieures + extérieures 30 %, passes courtes efficaces, profondes ≤ 6 %.
- **Exclusifs (4)** : SINGLEBACK + OUTSIDE_RUN, ACE + INSIDE_RUN, GUN_Y_OFF + SHORT_OUT, SINGLEBACK_WING_PAIR + STICK.
- **Défense** : c'est là que BST doit se voir.

## 17 · GRZ — Granite Grizzlies · « Erase » (Run Defense)
- **Bible** : défense contre la course ; attaque : play-action, bootlegs, passes intermédiaires, coutures du TE.
- **Aujourd'hui** : BOOT 7 %, SAIL 3 %, intermédiaires 21 % ; défense 4_3 40 %.
- **Cibles** : PA / BOOT 16 %, intermédiaires 22 % (SAIL, DEEP_CROSS, Y_CROSS pour le TE), personnel 12 + 22 ≥ 30 %.
- **Exclusifs (4)** : ACE + SAIL, HEAVY + BOOT, SINGLEBACK_DEUCE + Y_CROSS, I_FORM_SLOT + PA_SLIDE.
- **Défense** : BOX_STACK / 4_3 et front lourd sur 1er & 10 (≥ 40 %), courses concédées les plus basses.

## 18 · MRG — Mirage Cobras · « Manipulate » (Play-Action / Misdirection)
- **Bible** : boot, naked, counter, reverse, jet / orbit, split zone, crossers, max protect.
- **Aujourd'hui** : COUNTER 11 %, BOOT 7 %, POP 3 % ; motion 3 %.
- **Cibles** : PA / BOOT 18 %, misdirection (REVERSE, END_AROUND, COUNTER_SWEEP, JET_ACTION) 8 %, **motion 25 %**,
  COUNTER 10 %.
- **Exclusifs (5)** : I_FORM + DOUBLE_REVERSE, SINGLEBACK_WING + COUNTER_SWEEP, ACE + POP, PISTOL_WING + END_AROUND,
  WEAK + BOOT.
- **Défense** : inchangée.

## 19 · GMB — Gambit Stallions · « Risk » (4e essai)
- **Bible** : 4e essais : sneak, power, duo, RPO, mesh, slant, bunch.
- **Aujourd'hui** : 4e tentés 67 % (la seule vraie trace), aucun concept signature ; défense blitz 31 %.
- **Cibles** : un **paquet 3e / 4e et court** à elle (≤ 3 yards) : BUNCH + MESH, QUICK_SLANT, RPO_POWER, POWER
  ≥ 60 % de ces appels. Ailleurs : profondes 16 % (déjà), jeux à risque (gros gains) au-dessus de la ligue.
- **Exclusifs (4)** : BUNCH + QUICK_SLANT (4e), GUN_TIGHT + RPO_POWER, JUMBO + WHAM, BUNCH + MESH (4e).
- **Défense** : blitz 30 % (inchangé).

## 20 · PRM — Prism Chameleons · « Flex » (Positionless)
- **Bible** : motion, shifts, 11 / 12 / 21, empty, bunch, trips, compact, TE détaché.
- **Aujourd'hui** : la plus moyenne après CTX (0,020) : CHAMP 3 %, motion 5 %.
- **Cibles** : **motion 30 %**, formations « hybrides » ≥ 30 % (GUN_Y_OFF, GUN_FLEX, SINGLEBACK_BUNCH, GUN_WING),
  personnel 12 et 21 ≥ 30 % en passe, EMPTY depuis 12 / 21.
- **Exclusifs (5)** : GUN_FLEX + CHAMP, GUN_Y_OFF + LEVELS, SINGLEBACK_BUNCH + FLOOD, GUN_WING + CROSS,
  I_FORM_SLOT + CHOICE.
- **Défense** : inchangée.

## 21 · SPK — Spark Kestrels · « Grow » (jeunesse)
- **Feuille de route** : équipe jeune (bloc E, `AGE_EQUIPE`), énergie, progression.
- **Aujourd'hui** : profondes 17 %, FOUR_VERTS / DAGGER ; courte distance en course 34 % ; défense blitz 23 %, homme
  19 %. Plus proche CMT (0,032).
- **Cibles** : **jeune et vertical** : JET_SWEEP / JET_ACTION 5 %, profondes 18 %, rythme élevé (comme PLS mais menu
  large), erreurs de jeunesse déjà dans le bloc E. Défense homme / press 20 %.
- **Exclusifs (4)** : GUN_TRIPS_OPEN + FOUR_VERTS, SHOTGUN + JET_SWEEP, TRIPS + DAGGER, GUN_WING + SWITCH_VERTICALS.
- **Distinction VEC** : VEC = spread vertical complet ; SPK = verticales + sweeps rapides, moins de PA.

## 22 · CTD — Citadel Rams · « Endure » (vétérans)
- **Feuille de route** : vétérans (bloc E), expérience, sang-froid.
- **Aujourd'hui** : PLAY_ACTION 4 %, CURL 3 %, PA 11 % ; courte distance en course 38 %. Plus proche ONX (0,036).
- **Cibles** : **vétéran sous le centre** : play-action classique 14 %, SINGLEBACK / ACE / I_FORM ≥ 30 %, passes
  intermédiaires sur timing (CURL, LEVELS, DOUBLE_DIG) 12 %, 3e et long converti au-dessus de la ligue.
- **Exclusifs (4)** : I_FORM + PLAY_ACTION, ACE + DOUBLE_DIG, SINGLEBACK + LEVELS, STRONG + PA_FLOOD.
- **Défense** : zone patiente (COVER_2 + COVER_3 ≥ 40 %), inchangée sinon.

## 23 · TDL — Tidal Herons · « Flow » (zone large / bootleg)
- **Feuille de route** : zone large et bootleg (schéma Shanahan).
- **Aujourd'hui** : BOOT 6 %, DRAG 5 %, JET_SWEEP 4 % ; zone + boot ≈ 7 % seulement ; SHOTGUN n°1.
- **Cibles** : **OUTSIDE_RUN 12 %** + BOOT / PA 15 % sur la même allure, SINGLEBACK / SINGLEBACK_WING / PISTOL_WING
  ≥ 35 %, motion 25 % (JET_ACTION), 21 personnel 20 %.
- **Exclusifs (5)** : SINGLEBACK_WING + OUTSIDE_RUN, PISTOL_WING + BOOT, I_FORM_WING + JET_ACTION,
  SINGLEBACK + DEEP_CROSS, WEAK + OUTSIDE_RUN.
- **Défense** : inchangée.

## 24 · CMT — Comet Stingrays · « Ignite » (équipes spéciales)
- **Feuille de route** : identité d'équipes spéciales.
- **Aujourd'hui** : écart 0,037, MESH seule signature ; écrans 10 %, défense ballons récupérés 1,65 / match.
- **Cibles** : l'identité est surtout hors des appels de jeu (retours, coups de pied). Dans le playbook : **jeux de
  vitesse et trucs** — écrans 12 %, JET_SWEEP / REVERSE / END_AROUND 6 %, faux dégagements en 4e (si le moteur les
  gère, sinon plus tard).
- **Exclusifs (4)** : GUN_WING + REVERSE, TRIPS + FL_SE_SCREEN, SHOTGUN + END_AROUND, BUNCH + WR_TUNNEL_SCREEN.
- **Décision** : les vraies traces CMT (retours, coups de pied cachés, faux punts) sont des effets moteur d'équipes
  spéciales, pas des playbooks — à décider si on les fait à l'étape 2 ou plus tard.

---

## Garde-fous (pour l'étape 2)

- **Résultats** : chaque franchise reste entre 40 et 60 % de victoires à force égale ; totaux de la ligue (points,
  yards, passes / courses, pertes de balle) dans les tolérances de 12.3 ; calibrage 12.3 relancé.
- **Pas de piège tactique** : le moteur garde l'anti-répétition et l'adaptation V21 ; un play exclusif reste au plus
  ~3 % des appels de son équipe.
- **Temps de calcul du samedi** : ≤ 75 min (mesuré avant fusion).
- **Semaines publiées** : jamais recalculées ; la refonte vaut à partir de la semaine suivant la fusion.
- **Interrupteur** : les nouveaux poids derrière une variable (proposition : `GC_PLAYBOOK_IDENTITE=off` remet les
  poids actuels).
- **Mesure de réussite** : l'outil de l'étape 1 relancé sur une semaine de test donne écart moyen ≥ 0,10, aucune paire
  < 0,04, ≥ 3 signatures par franchise (CTX à part), 4–6 exclusifs chacune.

## Décisions (Guillaume, 27/10/2026)

1. **Les fiches** sont bonnes.
2. **ZPH joue avec un 4e receveur** (10 personnel) : le WR4 du banc (étape 7.3) entre à la place du TE sur ses
   formations spread (TRIPS, GUN_QUADS, GUN_TRIPS_OPEN, GUN_STACK ; pas le SHOTGUN de base, étape 3). VEC reste en 11.
3. **Plays exclusifs** : nouvelles combinaisons formation × concept, oui.
4. **Pas d'effet moteur** pour l'instant : on s'en tient à l'enrichissement des playbooks (choix des jeux).
5. **SALEM et SPILL_PROTECTION sortent de la réserve**, avec ces définitions (aucune définition publique fiable) :
   SALEM = passe à trois niveaux côté fort, famille de SAIL (go qui dégage le haut, dig à 12 yards du slot, flat de
   sortie) ; SPILL_PROTECTION = pression à 5 où les défenseurs du bord plongent à l'intérieur des blocs et renvoient la
   course vers la touche (fort contre power / counter et les scrambles, plus faible contre la passe rapide).
6. **Systèmes réels** comme repères (ci-dessous). À terme : que les coordinateurs imaginent leurs propres systèmes,
   cohérents avec leur identité.

## Étape 2 — ce qui est joué (moteur/identite_franchises.py, cellule 12.2 vicies septies)

Mesure sur une semaine de test (276 matchs, `outils/moteur/semaine_identite.py`, 3 graines) :

| | Avant | Après | Cible |
|---|---|---|---|
| Écart moyen à la ligue | 0,064 | 0,111 – 0,115 | ≥ 0,10 |
| Paire la plus proche | BST–MRD 0,019 (14 paires < 0,04) | BST–ONX 0,05 – 0,06 | aucune < 0,04 |
| Plays joués / par une seule franchise | 248 / 4 | 352 / 121 | 4 à 6 exclusifs chacune |
| Franchises avec moins de 3 signatures | 11 | CTX (par fiche), parfois ONX | aucune (sauf CTX) |
| Passes (ligue) | 63 % | 63-64 % | inchangé |
| Points par match | 54,1 | 53,0 | étape 3 (calibration) |

Quelques plays exclusifs ont changé par rapport aux fiches : une combinaison qui existait déjà dans le playbook de base,
12.2 bis ou Roman (EMPTY + FOUR_VERTS, JUMBO + POWER, ACE + PLAY_ACTION…) reste à tout le monde ; la fiche a pris une
combinaison voisine.

| Franchise | Système réel (repère) | Plays exclusifs |
|---|---|---|
| CTX | Patriots de Bill Belichick : un plan de jeu par adversaire, aucune dominante fixe | GUN_FLEX + Y_CROSS, PISTOL_WING + RPO_PEEK, SINGLEBACK_BUNCH + LEVELS, GUN_TRIPS_OPEN + SPOT_SNAG |
| VEC | Run and Shoot (Mouse Davis, June Jones) et « Greatest Show on Turf » de Mike Martz : spread vertical | GUN_QUADS + SWITCH_VERTICALS, EMPTY + DIVIDE, TRIPS + DOUBLE_POST, GUN_TRIPS_OPEN + DEEP_CROSS, GUN_STACK + FOUR_VERTS |
| AEG | Contrôle du ballon de Bill Parcells ; défense en match quarters de Nick Saban | ACE + PA_SLIDE, SINGLEBACK_TIGHT + TRAP, ACE + LEVELS, SINGLEBACK_DEUCE + INSIDE_RUN |
| MNL | Power-I de Nebraska et gap scheme de Greg Roman : sous le centre, 21 / 22 personnel | JUMBO + POWER_TOSS, I_FORM + BUCK_SWEEP, PISTOL_FULL_HOUSE + PIN_PULL, HEAVY + WHAM, I_FORM_WING + PLAY_ACTION |
| AXM | West Coast de Bill Walsh : timing, passes courtes, motion | BUNCH + SPOT_SNAG, SINGLEBACK_BUNCH + DRAG, GUN_Y_OFF + PIVOT, BUNCH + CHOICE, SINGLEBACK_WING_PAIR + Y_CROSS |
| GLT | Défense « 46 » de Buddy Ryan et blitz de Jim Johnson ; attaque d'écrans et de play-action | GUN_TIGHT + WR_TUNNEL_SCREEN, PISTOL + QB_DRAW, SINGLEBACK + FL_SE_SCREEN, GUN_WING + PA_FLOOD |
| CPH | Pistol de Chris Ault et spread option d'Urban Meyer | PISTOL + INVERTED_VEER, PISTOL_WING + SPEED_OPTION, GUN_WING + MIDLINE_OPTION, PISTOL_STRONG + POWER_READ, PISTOL + TRIPLE_OPTION, PISTOL_FULL_HOUSE + SPEED_OPTION |
| NVA | Air Coryell (Don Coryell) et Bruce Arians : shots en play-action, max protect | ACE + PA_FLOOD, I_FORM + DOUBLE_POST, SINGLEBACK + PA_FLOOD, ACE + DEEP_POST, I_FORM_WING + CORNER |
| PLS | Tempo de Chip Kelly (Oregon) : sans regroupement, petit menu répété vite | GUN_TRIPS_OPEN + HITCH, EMPTY + HITCH, GUN_TRIPS_TIGHT + FL_SE_SCREEN, SHOTGUN + RPO_ALERT |
| ONX | Tampa 2 de Tony Dungy et Monte Kiffin, Bears de Lovie Smith : défense qui chasse le ballon | GUN_Y_OFF + SHORT_OUT, SINGLEBACK + HITCH, GUN_FLEX + WR_TUNNEL_SCREEN, PISTOL + DART_QUICK_DIG |
| FRG | Wisconsin : zone intérieure, duo, play-action depuis 12 personnel, pression intérieure | SINGLEBACK_NASTY + INSIDE_RUN, ACE + WHAM, SINGLEBACK_TIGHT + PA_SLIDE, STRONG + TRAP |
| MRD | « Tresselball » de Jim Tressel : terrain, horloge, jeu sûr, Cover 2 / 3 qui plie | PONY + FL_SE_SCREEN, PISTOL + CURL, SINGLEBACK_WING + DRAW, SINGLEBACK_WING + HITCH |
| APX | Erhardt-Perkins en zone rouge (Patriots) : picks en bunch / stack, RPO, motion | GUN_STACK + MESH_WHEEL, GUN_STACK + SPOT_SNAG, GUN_STACK + RPO_POWER, PISTOL_STRONG + QB_DRAW, BUNCH + PA_FLOOD |
| LTC | RPO des Eagles 2017 (Doug Pederson, Frank Reich) : zone + lecture, bubble / tunnel | GUN_TRIPS_OPEN + RPO_INSIDE_ZONE, GUN_FLEX + RPO_PEEK, EMPTY + MESH, SHOTGUN + RPO_OUTSIDE_ZONE, GUN_TRIPS_OPEN + WR_TUNNEL_SCREEN |
| ZPH | Air Raid de Hal Mumme et Mike Leach : 4 receveurs, mesh, Y-cross, four verts | GUN_QUADS + MESH, EMPTY + Y_CROSS, GUN_QUADS + FOUR_VERTS, EMPTY + DAGGER, GUN_TRIPS_OPEN + DRAG |
| BST | Press man des Jets de Rex Ryan (Darrelle Revis) : homme, Cover 1 / 6, peu de blitz | SINGLEBACK_WING_PAIR + OUTSIDE_RUN, ACE + INSIDE_RUN, GUN_Y_OFF + HITCH, SINGLEBACK_WING_PAIR + STICK |
| GRZ | Défense des Ravens 2000 contre la course ; attaque à deux TE des Patriots 2011 (play-action, coutures) | ACE + SAIL, SINGLEBACK_DEUCE + BOOT, SINGLEBACK_DEUCE + Y_CROSS, I_FORM_SLOT + PA_SLIDE, ACE + SALEM |
| MRG | Kyle Shanahan et Sean McVay : boot, jet, reverse, feintes | I_FORM + DOUBLE_REVERSE, SINGLEBACK_WING + COUNTER_SWEEP, ACE + POP, PISTOL_WING + END_AROUND, WEAK + BOOT |
| GMB | Eagles 2017 et Lions de Dan Campbell : le 4e essai joué | BUNCH + QUICK_SLANT, GUN_TIGHT + RPO_POWER, JUMBO + WHAM, GUN_TRIPS_TIGHT + MESH |
| PRM | Chiefs d'Andy Reid : motions, shifts, formations hybrides | GUN_FLEX + CHAMP, GUN_Y_OFF + LEVELS, SINGLEBACK_BUNCH + FLOOD, GUN_WING + CROSS, I_FORM_SLOT + CHOICE |
| SPK | Oklahoma de Lincoln Riley : Air Raid jeune, verticales et jet sweeps | GUN_TRIPS_OPEN + FOUR_VERTS, SHOTGUN + JET_SWEEP, GUN_TRIPS_OPEN + DAGGER, GUN_WING + SWITCH_VERTICALS |
| CTD | Colts de Peyton Manning et Tom Moore : peu de formations, timing, play-action classique | I_FORM + PA_SLIDE, ACE + DOUBLE_DIG, SINGLEBACK + LEVELS, STRONG + PA_FLOOD, SINGLEBACK + SALEM |
| TDL | Broncos de Mike Shanahan : zone large et bootleg sur la même allure | SINGLEBACK_WING + OUTSIDE_RUN, PISTOL_WING + BOOT, I_FORM_WING + JET_ACTION, SINGLEBACK + DEEP_CROSS, WEAK + OUTSIDE_RUN |
| CMT | « Beamer Ball » de Frank Beamer (Virginia Tech) : vitesse, trucs, équipes spéciales | GUN_WING + REVERSE, TRIPS + FL_SE_SCREEN, SHOTGUN + END_AROUND, BUNCH + WR_TUNNEL_SCREEN |

Mesures par franchise après la refonte (graine 500 000) — passes, familles principales, motion, plays, écart :

| Franchise | Passes | Familles en tête | Motion | Personnel | Plays (exclusifs) | Écart | Signatures |
|---|---|---|---|---|---|---|---|
| AEG | 56 % | courtes 27 %, c. intérieures 24 %, intermédiaires 13 % | 6 % | 11 61 %, 12 25 % | 192 (4) | 0.113 | INSIDE_RUN, TRAP, CURL |
| APX | 67 % | courtes 23 %, c. en force 14 %, intermédiaires 11 % | 21 % | 11 71 %, 21 12 % | 196 (6) | 0.078 | SCREEN, BOOT, QUICK_SLANT, SPOT_SNAG, RPO_POWER |
| AXM | 73 % | courtes 37 %, intermédiaires 16 %, c. intérieures 12 % | 22 % | 11 81 %, 12 10 % | 191 (5) | 0.072 | STICK, CURL, DRAG, SPOT_SNAG |
| BST | 57 % | courtes 25 %, c. intérieures 18 %, intermédiaires 17 % | 3 % | 11 63 %, 12 20 % | 187 (4) | 0.077 | INSIDE_RUN, OUTSIDE_RUN, STICK, CURL, CROSS |
| CMT | 65 % | courtes 20 %, écrans 19 %, intermédiaires 12 % | 14 % | 11 81 %, 21 11 % | 186 (4) | 0.086 | SCREEN, JET_SWEEP, WR_TUNNEL_SCREEN, FL_SE_SCREEN |
| CPH | 55 % | option 19 %, courtes 16 %, PA / boot 12 % | 23 % | 11 69 %, 21 19 % | 185 (7) | 0.133 | READ_OPTION, BOOT, POWER_READ, INVERTED_VEER |
| CTD | 63 % | courtes 20 %, intermédiaires 19 %, c. intérieures 18 % | 4 % | 11 67 %, 12 14 % | 173 (5) | 0.084 | DRAW, CURL, PLAY_ACTION, LEVELS |
| CTX | 63 % | courtes 20 %, intermédiaires 16 %, profondes 12 % | 5 % | 11 74 %, 21 12 % | 220 (7) | 0.029 | READ_OPTION |
| FRG | 52 % | c. intérieures 22 %, c. en force 19 %, intermédiaires 16 % | 5 % | 11 46 %, 12 31 % | 171 (4) | 0.125 | INSIDE_RUN, BOOT, WHAM, TRAP |
| GLT | 68 % | écrans 19 %, PA / boot 14 %, c. intérieures 14 % | 4 % | 11 76 %, 21 11 % | 199 (4) | 0.068 | SCREEN, WR_TUNNEL_SCREEN, FL_SE_SCREEN, PLAY_ACTION |
| GMB | 63 % | courtes 24 %, c. en force 15 %, profondes 13 % | 8 % | 11 71 %, 21 12 % | 204 (5) | 0.074 | POWER, MESH, QUICK_SLANT, RPO_POWER |
| GRZ | 64 % | intermédiaires 22 %, c. en force 17 %, PA / boot 15 % | 6 % | 11 51 %, 12 31 % | 192 (5) | 0.090 | BOOT, Y_CROSS, SALEM |
| LTC | 68 % | courtes 25 %, écrans 15 %, RPO 15 % | 10 % | 11 93 %, 21 5 % | 159 (8) | 0.147 | WR_TUNNEL_SCREEN, STICK, MESH, READ_OPTION, FL_SE_SCREEN |
| MNL | 34 % | c. en force 45 %, PA / boot 16 %, c. intérieures 11 % | 4 % | 21 38 %, 22 27 % | 149 (5) | 0.248 | POWER, COUNTER, BOOT, POP, POWER_TOSS |
| MRD | 61 % | courtes 22 %, c. intérieures 21 %, écrans 17 % | 4 % | 11 63 %, 21 21 % | 177 (4) | 0.112 | SCREEN, INSIDE_RUN, CURL |
| MRG | 62 % | PA / boot 19 %, c. en force 16 %, intermédiaires 14 % | 21 % | 11 55 %, 21 21 % | 187 (6) | 0.082 | BOOT, COUNTER, POP, COUNTER_SWEEP |
| NVA | 67 % | profondes 23 %, PA / boot 21 %, intermédiaires 16 % | 7 % | 11 54 %, 12 23 % | 167 (5) | 0.159 | POWER, PLAY_ACTION, CORNER, BOOT, DEEP_POST |
| ONX | 61 % | courtes 31 %, c. intérieures 15 %, c. en force 13 % | 6 % | 11 76 %, 21 11 % | 196 (4) | 0.083 | SHORT_OUT, STICK, HITCH, DART_QUICK_DIG |
| PLS | 70 % | courtes 36 %, écrans 12 %, c. intérieures 12 % | 3 % | 11 95 %, 21 3 % | 88 (5) | 0.195 | DRAW, STICK, SCREEN, SHORT_OUT, DRAG |
| PRM | 68 % | intermédiaires 26 %, courtes 19 %, c. en force 13 % | 33 % | 11 73 %, 21 13 % | 199 (5) | 0.076 | CHAMP, CROSS, FLOOD |
| SPK | 67 % | profondes 24 %, courtes 18 %, intermédiaires 15 % | 12 % | 11 85 %, 21 7 % | 171 (4) | 0.095 | FOUR_VERTS, JET_SWEEP, QUICK_SLANT, DAGGER, DOUBLE_POST |
| TDL | 60 % | c. extérieures 16 %, PA / boot 15 %, intermédiaires 15 % | 20 % | 11 54 %, 12 27 % | 181 (5) | 0.100 | BOOT, OUTSIDE_RUN, JET_SWEEP, SAIL |
| VEC | 79 % | profondes 40 %, intermédiaires 22 %, c. intérieures 12 % | 4 % | 11 96 %, 12 2 % | 148 (5) | 0.190 | CORNER, DEEP_POST, FOUR_VERTS, DOUBLE_POST, SWITCH_VERTICALS |
| ZPH | 77 % | courtes 30 %, intermédiaires 19 %, profondes 18 % | 4 % | 10 63 %, 11 34 % | 133 (5) | 0.154 | MESH, DRAW, FOUR_VERTS, STICK, SAIL |

Garde-fous de l'étape 3 (avant fusion) : victoires 40-60 % à force égale sur beaucoup de matchs (une semaine de 23
matchs par équipe est trop bruitée : 0,28-0,72 avant comme après), totaux de la ligue dans les tolérances de 12.3,
cotes, audit, calcul du samedi ≤ 75 min.
