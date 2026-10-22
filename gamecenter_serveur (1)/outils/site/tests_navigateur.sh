#!/usr/bin/env bash
# Tests navigateur du site (Playwright, serveurs réels avec le crochet de test) — en local comme sur GitHub
# (workflow « Contrôle des PR », README section 38). Depuis « gamecenter_serveur (1) » :
#
#   bash outils/site/tests_navigateur.sh [--semaines N] [--groupe site|parite]
#
# Il faut Python avec fastapi / uvicorn (requirements.txt), Node avec Playwright (Chromium) et ffmpeg (sons de test).
# --semaines N : commentaire et parité audio ne rejouent que les N dernières semaines (défaut : toutes ; la parité
#                prend ≈ 6 min par semaine). --groupe : « site » (tout sauf la parité) ou « parite » (défaut : les deux).
# Le dépôt n'est pas modifié : chaque serveur tourne sur une copie de data/ (paris, comptes) dans un dossier temporaire.
#   8103 : sans sons enregistrés (parité avec l'ancien code) · 8104 : sons de test (--placeholder) · 8108 : sons du dépôt
# Tous les tests tournent, même après un échec ; le script échoue si l'un d'eux échoue.
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1
SEMAINES=0; GROUPE=tous
while [ $# -gt 0 ]; do
  case "$1" in
    --semaines) SEMAINES="${2:-0}"; shift 2;;
    --groupe) GROUPE="${2:-tous}"; shift 2;;
    *) echo "option inconnue : $1"; exit 2;;
  esac
done
SITE=0; PAR=0
case "$GROUPE" in tous) SITE=1; PAR=1;; site) SITE=1;; parite) PAR=1;; *) echo "groupe inconnu : $GROUPE"; exit 2;; esac
TMP=$(mktemp -d)
PIDS=()
arreter() { for p in "${PIDS[@]}"; do kill "$p" 2>/dev/null; done; wait 2>/dev/null; rm -rf "$TMP"; }
trap arreter EXIT

if [ $SITE = 1 ]; then
  echo "== sons de test (bips, sans ElevenLabs)"
  python3 outils/audio/generer_audio.py --placeholder --audio-dir "$TMP/sons" > "$TMP/sons.log" 2>&1 \
    && python3 outils/audio/generer_audio.py --placeholder --cat stade --audio-dir "$TMP/sons" >> "$TMP/sons.log" 2>&1 \
    || { cat "$TMP/sons.log"; echo "échec : sons de test"; exit 1; }
fi
mkdir -p "$TMP/sans-sons"

serveur() {   # port, dossier audio (vide = celui du dépôt)
  cp -r data "$TMP/data$1"
  if [ -n "$2" ]; then
    GC_DATA="$TMP/data$1" GC_TEST_HOOK=1 GC_AUDIO_DIR="$2" python3 -m uvicorn serveur:app --port "$1" > "$TMP/serveur$1.log" 2>&1 &
  else
    GC_DATA="$TMP/data$1" GC_TEST_HOOK=1 python3 -m uvicorn serveur:app --port "$1" > "$TMP/serveur$1.log" 2>&1 &
  fi
  PIDS+=($!)
}
PORTS=()
if [ $PAR = 1 ]; then serveur 8103 "$TMP/sans-sons"; PORTS+=(8103); fi
if [ $SITE = 1 ]; then serveur 8104 "$TMP/sons"; serveur 8108 ""; PORTS+=(8104 8108); fi
for port in "${PORTS[@]}"; do
  for _ in $(seq 120); do curl -sf "http://localhost:$port/api/health" | grep -q '"ok":true' && break; sleep 1; done
  curl -sf "http://localhost:$port/api/health" | grep -q '"ok":true' || { cat "$TMP/serveur$port.log"; echo "échec : serveur $port"; exit 1; }
done

ECHECS=()
RESUME="| Test | Résultat | Durée |\n|---|---|---|\n"
lancer() {   # nom, commande…
  local nom=$1; shift
  echo; echo "== $nom"
  local t0=$SECONDS
  if "$@"; then local r="✅"; else local r="❌"; ECHECS+=("$nom"); fi
  echo "-- $nom : $r ($((SECONDS - t0)) s)"
  RESUME+="| $nom | $r | $((SECONDS - t0)) s |\n"
}
SEM=(); [ "$SEMAINES" != 0 ] && SEM=(--semaines "$SEMAINES")
if [ $SITE = 1 ]; then
  lancer "Audio : AudioEventMapper" node outils/audio/test_mapper_v01.js data/weeks
  lancer "Site : pauses de retransmission" node outils/site/test_pauses.js
  lancer "Site : fin de match dans le grand écran" node outils/site/test_fin_de_match.js
  lancer "Site : recherche" node outils/site/test_recherche.js data/weeks 8108
  lancer "Site : scores des matchs terminés" node outils/site/test_bandeau.js
  lancer "Site : résultats du jour en cours seulement (onglets des jours)" node outils/site/test_jour.js
  lancer "Site : transformations après un touchdown" node outils/site/test_transformation.js
  lancer "Site : coups d'envoi et retours" node outils/site/test_retours.js
  lancer "Site : punts et retours" node outils/site/test_punts.js
  lancer "Site : jeu de course dessiné (bloc F)" node outils/site/test_courses.js
  lancer "Site : horloge continue, chrono des 40 s, temps morts" node outils/site/test_horloge.js
  lancer "Site : checks avant le snap (audible, motion, défense qui se décale)" node outils/site/test_audibles.js
  lancer "Site : la poche et la ligne offensive (fer à cheval, step up, sortie, sack)" node outils/site/test_poche.js
  lancer "Site : pénalités pendant l'action (drapeau, appel de l'arbitre, stats)" node outils/site/test_penalites.js
  lancer "Site : le banc, les packages et les rotations (bons joueurs, snaps, profondeur)" node outils/site/test_banc.js
  lancer "Site : fumbles gardés par l.attaque" node outils/site/test_fumbles.js
  lancer "Site : appel de jeu qui apprend (KEY, BREAK, READ / BURNED)" node outils/site/test_scouting.js
  lancer "Site : mémoire d.une semaine à l.autre (SCOUTED, ON TAPE, Scouting report)" node outils/site/test_memoire.js
  lancer "Site : Bigger field en plein écran (ordinateur, téléphone)" node outils/site/test_plein_ecran.js
  lancer "Site : noms des joueurs sur le terrain" node outils/site/test_noms.js
  lancer "Site : histoire, records, carrières" node outils/site/test_histoire.js
  lancer "Site : classement des joueurs (Ranking)" node outils/site/test_classement.js
  lancer "Site : rappels avant le coup d.envoi" node outils/site/test_rappels.js
  lancer "Site : ligues privées" node outils/site/test_ligues.js
  lancer "Site : visibilité (référencement, partage)" node outils/site/test_visibilite.js
  lancer "Site : publicités, mentions, page légale" node outils/site/test_publicites.js
  lancer "Notebook : Game Center (cellule 427)" node outils/site/test_cellule427.js
  lancer "Audio : musique" node outils/audio/test_musique_v04.js 8108
  lancer "Audio : commentaire enregistré" node outils/audio/test_commentaire_v02.js data/weeks 8104 "${SEM[@]}"
  lancer "Audio : foule et effets" node outils/audio/test_stade_v03.js data/weeks 8104
fi
if [ $PAR = 1 ]; then
  lancer "Audio : parité avec l'ancien code" node outils/audio/test_parite_v01.js data/weeks 8103 "${SEM[@]}"
fi

echo; printf "%b" "$RESUME"
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then printf "### Tests navigateur (%s)\n\n%b" "$GROUPE" "$RESUME" >> "$GITHUB_STEP_SUMMARY"; fi
if [ ${#ECHECS[@]} -gt 0 ]; then echo "ÉCHEC : ${ECHECS[*]}"; exit 1; fi
echo "TOUS LES TESTS NAVIGATEUR PASSENT"
