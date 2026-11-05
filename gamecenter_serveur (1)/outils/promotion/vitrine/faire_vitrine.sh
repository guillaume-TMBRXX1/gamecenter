#!/usr/bin/env bash
# Vidéo « vitrine » de Snapline (promotion, 04/11/2026) : démo du site façon « UI showcase » (zooms et panoramiques de
# caméra, transitions floues, curseur qui clique), en 16:9 (1920×1080) et 9:16 (1080×1920), ≈ 15 s, 30 images/s.
# Depuis « gamecenter_serveur (1) » :   bash outils/promotion/vitrine/faire_vitrine.sh [dossier de sortie]
# Il faut Python avec fastapi/uvicorn, Node + Playwright (Chromium), ffmpeg, numpy et Pillow. ≈ 20 min (le site est
# filmé image par image, ≈ 1 s par image, les deux formats en parallèle).
# Variables : VITRINE_AT (heure du site au début du tournage ; défaut : un match « Prime Time » serré en fin de 4e
# quart-temps de la semaine du 02/11), VITRINE_MUSIQUE (musique originale du site, défaut final_drive), VITRINE_PORT.
# Écrit <sortie>/snapline_vitrine_16x9.mp4 et <sortie>/snapline_vitrine_9x16.mp4 (non versionnés : à publier à la main).
# Jamais de paris à l'image (programme/Promotion.md) : solde, ticket, cotes et marchés sont masqués pendant le tournage.
set -euo pipefail
ICI="$(cd "$(dirname "$0")" && pwd)"
RACINE="$(cd "$ICI/../.." && pwd)"
SORTIE="$(mkdir -p "${1:-$RACINE/videos}" && cd "${1:-$RACINE/videos}" && pwd)"
PORT="${VITRINE_PORT:-8170}"
AT="${VITRINE_AT:-2026-11-04T15:15:30+01:00}"
MUSIQUE="${VITRINE_MUSIQUE:-$(ls "$RACINE"/audio/music/final_drive.*.mp3 | head -1)}"
TRAVAIL="$(mktemp -d)"
trap 'kill "${SRV:-0}" 2>/dev/null || true; rm -rf "$TRAVAIL"' EXIT

mkdir -p "$TRAVAIL/data"; cp -r "$RACINE/data/weeks" "$TRAVAIL/data/"
( cd "$RACINE" && GC_DATA="$TRAVAIL/data" GC_TEST_HOOK=1 GC_PUSH_LOOP=0 GC_DEMO_AT="$AT" \
    exec python3 -m uvicorn serveur:app --port "$PORT" > "$TRAVAIL/serveur.log" 2>&1 ) & SRV=$!
for _ in $(seq 120); do curl -sf "http://localhost:$PORT/api/time" > /dev/null && break; sleep 1; done
curl -sf "http://localhost:$PORT/" > /dev/null   # 1re page d'un serveur neuf : lente (semaines à lire)
URL="http://localhost:$PORT/"

node "$ICI/tourner.js" L "$TRAVAIL/L" "$URL" & A=$!
node "$ICI/tourner.js" P "$TRAVAIL/P" "$URL" & B=$!
wait $A; wait $B
node "$ICI/carton.js" L "$TRAVAIL/fin_L" "$URL"
node "$ICI/carton.js" P "$TRAVAIL/fin_P" "$URL"
python3 "$ICI/monter.py" L "$TRAVAIL/L" "$TRAVAIL/fin_L" "$MUSIQUE" "$SORTIE/snapline_vitrine_16x9.mp4"
python3 "$ICI/monter.py" P "$TRAVAIL/P" "$TRAVAIL/fin_P" "$MUSIQUE" "$SORTIE/snapline_vitrine_9x16.mp4"
echo "Vidéos : $SORTIE/snapline_vitrine_16x9.mp4 · $SORTIE/snapline_vitrine_9x16.mp4"
