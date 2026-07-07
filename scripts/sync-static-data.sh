#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/.evidence/template/static/data"
DEST="$ROOT/static/data"

if [ ! -d "$SRC" ]; then
	echo "No generated data at $SRC — run npm run sources first."
	exit 1
fi

mkdir -p "$DEST"
rsync -a --delete "$SRC/" "$DEST/"
echo "Synced Evidence data to static/data"
