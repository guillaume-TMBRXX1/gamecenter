# moteur/ — ENGINE INTELLIGENCE

Modules de décision du moteur GridironSim (`programme/Feuille_de_route.md`, étape 5). Python pur (bibliothèque
standard seulement), indépendants du notebook : on échange des `dict` simples (`{"id", "name", "ratings"}`).
Le notebook `NFL_Sim_GameCenter.ipynb` les importe (cellule **12.2 quinquies**) et les appelle depuis
`simulate_drive_franchise` (12.2) derrière l'interrupteur `DECISIONS_ENABLED` (allumé depuis V22.1).

## Bloc A — état post-snap, progression du QB, cible réelle (notebook V22, allumé en V22.1)

```
appel du coordinateur (play + couverture)
   │ progressions.progression(concept, formation)        primaire · secondaire · tertiaire · checkdown (+ routes)
   ▼
DefensiveReactionEngine.react(...)  ->  PostSnapState   couverture réelle (homme / zone, Cover 0-4), rushers,
   │                                                     receveur LIBRE / SERRE / COUVERT / DOUBLE, temps avant pression
   ▼
QBDecisionEngine.decide(...)        ->  QBDecision      LANCER (cible réelle, n° de lecture) · THROWAWAY · SCRAMBLE · SACK
   ▼
resolution.probabilites_ajustees(...)                   probabilités du tirage historique ajustées selon la décision
```

| Fichier | Rôle |
|---|---|
| `progressions.py` | progression de lecture de chaque concept de passe (18 concepts + défaut), routes et instant où le QB peut lancer ; HEAVY : WR1 inéligible |
| `reaction_defensive.py` | séparation = écart de notes (route vs couverture, 20 points de note par « pas ») + avantage de la route contre la couverture + bruit ; double couverture (bracket) sur la meilleure menace ; chrono de poche selon le niveau de pression (03E) et les rushers |
| `decision_qb.py` | lecture dans l'ordre ; lancer selon le statut ; sous pression : meilleure lecture vue, sinon scramble (mobility) / throwaway (decision_making) / passe forcée / sack |
| `resolution.py` | multiplicateurs (libre, serré, couvert, double, pression) + `CALIBRATION` (facteurs qui ramènent les moyennes de la ligue sur V21) ; yards selon la profondeur de la cible réelle ; yards de scramble |
| `stats.py` | statistiques des décisions : par cible réelle, par statut, par couverture, taux de première lecture, pression, scramble, throwaway |
| `aleatoire.py` | flux aléatoire dédié : `random.Random("decision-passe|<graine du match>|<n° d'action>")` — le hasard du moteur n'est jamais consommé par une décision |

## Tests (quelques secondes)

```bash
cd "gamecenter_serveur (1)"
python3 -m unittest discover -s moteur/tests -t .
```

Primaire libre · primaire couvert / secondaire libre · tout couvert (checkdown, throwaway, sack) · double
couverture · blitz (moins de temps, plus de rushers, route « hot ») · Cover 4 (fond fermé, court ouvert) ·
QB mobile (plus de scrambles) · pression précoce · déterminisme (même graine = même décision, flux indépendant
du hasard global) · probabilités valides · agrégation des stats.

## Calibration (garde-fou 3)

```bash
python3 outils/moteur/rapport_calibration.py --decisions off --sortie /tmp/v21.json          # référence V21
python3 outils/moteur/rapport_calibration.py --decisions on --reference /tmp/v21.json         # verdict (code 1 si hors tolérance)
python3 outils/moteur/calibrer_bloc_a.py --reference /tmp/v21.json                            # recalcule CALIBRATION
```

Le rapport charge le notebook sans Jupyter (cellules jusqu'à 12.2 quinquies) et joue le test d'équilibre de 12.3
(1 008 matchs, mêmes graines). Tolérances : `TOLERANCES` dans `rapport_calibration.py`.

## Colab

Le notebook cherche `moteur/` dans `GC_MOTEUR_DIR`, le dossier courant, `./gamecenter_serveur (1)` et
`/content/gamecenter/gamecenter_serveur (1)`. Sur Colab, avant d'exécuter le notebook :

```python
!git clone https://<jeton GitHub>@github.com/guillaume-TMBRXX1/gamecenter.git /content/gamecenter
```

(dépôt privé : jeton « fine-grained » en lecture seule). Sans le dossier, le notebook tourne en V21 (interrupteur
forcé à coupé, message dans 12.2 quinquies) — sauf si `GC_MOTEUR_DIR` est donné ou `GC_DECISIONS=1` : il s'arrête alors.
`GC_DECISIONS=0` coupe l'interrupteur pour toute l'exécution.
