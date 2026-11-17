#!/usr/bin/env bash
# Refresh THE 53 rosters from nflverse and rebuild the site.
#   ./update_rosters.sh                         rebuild with no fixed web address
#   ./update_rosters.sh https://the53.pages.dev/ rebuild with your public address (makes share links and previews absolute)
# Run weekly during the season: it re-downloads this season's roster and keeps all older seasons cached.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p nfl
YEAR=$(date +%Y); MONTH=$(date +%m)
SEASON=$YEAR; if [ "$MONTH" -lt 3 ]; then SEASON=$((YEAR-1)); fi
BASE=https://github.com/nflverse/nflverse-data/releases/download
for y in $(seq 1920 "$SEASON"); do
  f=nfl/roster_$y.csv
  if [ ! -s "$f" ] || [ "$y" -ge $((SEASON-1)) ]; then curl -fsSL --retry 3 -o "$f" "$BASE/rosters/roster_$y.csv" || rm -f "$f"; fi
done
curl -fsSL --retry 3 -o nfl/draft_picks.csv "$BASE/draft_picks/draft_picks.csv"
python3 build_data.py nfl
python3 fetch_faces.py faces_cache
node split_data.js
node build.js "${1:-}"
echo "Done. Upload the dist/ folder."
