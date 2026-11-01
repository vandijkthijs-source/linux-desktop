#!/usr/bin/env bash
# Fetch the UNMODIFIED original VS Code Pets dog GIFs into this project.
set -euo pipefail
cd "$(dirname "$0")"
color="${1:-brown}"
case "$color" in brown|black|white|red|akita) ;; *) echo "Choose brown, black, white, red or akita" >&2; exit 2;; esac
command -v curl >/dev/null || { echo 'Please install curl: sudo apt install curl' >&2; exit 2; }
mkdir -p assets
base='https://raw.githubusercontent.com/tonybaloney/vscode-pets/main/media/dog'
for anim in idle walk run lie swipe; do
  file="${color}_${anim}_8fps.gif"
  echo "Fetching $file"
  curl --fail --location --retry 3 --silent --show-error "$base/$file" -o "assets/$file.part"
  if [[ $(head -c 3 "assets/$file.part") != 'GIF' ]]; then
    rm -f "assets/$file.part"
    echo "Invalid GIF download" >&2; exit 1
  fi
  mv "assets/$file.part" "assets/$file"
done
curl --fail --location --retry 3 --silent --show-error "$base/license.txt" -o assets/ARTWORK_LICENSE.txt
printf '\nSprites downloaded. They are licensed CC BY-ND 4.0 by their rights holders.\n'
printf 'Artwork attribution: NVPH Studio, via tonybaloney/vscode-pets.\n'
printf 'Start with: python3 panel_pup.py --check && python3 panel_pup.py\n'
