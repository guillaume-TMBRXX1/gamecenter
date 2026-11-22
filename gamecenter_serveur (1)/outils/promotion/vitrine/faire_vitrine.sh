#!/usr/bin/env bash
# Vidéo « vitrine » de Snapline (promotion ; v1 04/11/2026, v2 21/11/2026 pour Reddit) : démo du site façon « UI
# showcase » (zooms et panoramiques de caméra, transitions floues, curseur qui clique), en 16:9 (1920×1080) et 9:16
# (1080×1920), ≈ 60 s, 30 images/s, des plans de 5 à 11 s pour avoir le temps de lire.
# Depuis « gamecenter_serveur (1) » :   bash outils/promotion/vitrine/faire_vitrine.sh [dossier de sortie]
# Il faut Python avec fastapi/uvicorn, Node + Playwright (Chromium), ffmpeg, numpy et Pillow. ≈ 1 h (le site est filmé
# image par image, ≈ 1 à 2 s par image, les deux formats en parallèle).
# Le match filmé (v2) : vendredi 20/11, GRZ @ MRD, Q4 1:06, GRZ mené 13-15 — le coach IA tente le 4e essai (52 % contre
# 43 % pour le field goal), touchdown, puis « Goes for two » manqué. VITRINE_T0 = heure du site au début du premier
# plan (ms) : la carte « AI coach » apparaît 1,6 s après l'ouverture du grand écran (mesuré : 17:16:44,6). Pour un
# autre match, changer VITRINE_DEMO_AT et VITRINE_T0 (et la semaine doit être dans data/weeks).
# Le compte filmé (compte_demo.py) : « Snapfan », Insights Pro (GC_INSIGHTS_USERS), 8 badges de fidélité et de supporter.
# Écrit <sortie>/snapline_vitrine_16x9.mp4 et <sortie>/snapline_vitrine_9x16.mp4 (non versionnés : à publier à la main).
# Jamais de paris à l'image (programme/Promotion.md) : solde, ticket, cotes, marchés, onglet « This week » d'Insights,
# badges « Reading the game » et phrases qui parlent de paris sont masqués ou retirés pendant le tournage.
set -euo pipefail
ICI="$(cd "$(dirname "$0")" && pwd)"
RACINE="$(cd "$ICI/../.." && pwd)"
SORTIE="$(mkdir -p "${1:-$RACINE/videos}" && cd "${1:-$RACINE/videos}" && pwd)"
PORT="${VITRINE_PORT:-8170}"
DEMO_AT="${VITRINE_DEMO_AT:-2026-11-20T17:16:15+01:00}"
export VITRINE_T0="${VITRINE_T0:-1795191395630}"          # 2026-11-20T17:16:35.630+01:00
# musique originale du site (CC0) : plusieurs pistes de 17,5 s enchaînées en fondu, jusqu'à « victory » sur le carton
MUSIQUE="${VITRINE_MUSIQUE:-$(for m in pregame red_zone close_game final_drive victory; do ls "$RACINE"/audio/music/$m.*.mp3 | head -1; done | paste -sd,)}"
PSEUDO="Snapfan"
TRAVAIL="$(mktemp -d)"
trap 'kill "${SRV:-0}" 2>/dev/null || true; rm -rf "$TRAVAIL"' EXIT

mkdir -p "$TRAVAIL/data/weeks"
for w in "$RACINE"/data/weeks/week_*; do ln -s "$w" "$TRAVAIL/data/weeks/"; done
( cd "$RACINE" && GC_DATA="$TRAVAIL/data" GC_TEST_HOOK=1 GC_PUSH_LOOP=0 GC_DEMO_AT="$DEMO_AT" GC_INSIGHTS_USERS="$PSEUDO" \
    exec python3 -m uvicorn serveur:app --port "$PORT" > "$TRAVAIL/serveur.log" 2>&1 ) & SRV=$!
for _ in $(seq 120); do curl -sf "http://localhost:$PORT/api/time" > /dev/null && break; sleep 1; done
URL="http://localhost:$PORT/"
python3 "$ICI/compte_demo.py" "$URL" "$TRAVAIL/data/gamecenter.db" "$PSEUDO" > "$TRAVAIL/compte.json"
export VITRINE_COMPTE="$TRAVAIL/compte.json"
curl -sf "${URL}api/tracking?token=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["token"])' "$VITRINE_COMPTE")" > /dev/null   # 1er calcul Tracking (≈ 5 s)
curl -sf "$URL" > /dev/null   # 1re page d'un serveur neuf : lente (semaines à lire)

node "$ICI/tourner.js" L "$TRAVAIL/L" "$URL" & A=$!
node "$ICI/tourner.js" P "$TRAVAIL/P" "$URL" & B=$!
wait $A; wait $B
node "$ICI/carton.js" L "$TRAVAIL/fin_L" "$URL"
node "$ICI/carton.js" P "$TRAVAIL/fin_P" "$URL"
python3 "$ICI/monter.py" L "$TRAVAIL/L" "$TRAVAIL/fin_L" "$MUSIQUE" "$SORTIE/snapline_vitrine_16x9.mp4"
python3 "$ICI/monter.py" P "$TRAVAIL/P" "$TRAVAIL/fin_P" "$MUSIQUE" "$SORTIE/snapline_vitrine_9x16.mp4"
echo "Vidéos : $SORTIE/snapline_vitrine_16x9.mp4 · $SORTIE/snapline_vitrine_9x16.mp4"
