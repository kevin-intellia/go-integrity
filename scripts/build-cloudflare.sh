#!/usr/bin/env bash
set -euo pipefail

if [ -z "${GHL_PRIVATE_INTEGRATION_TOKEN:-}" ]; then
	echo "ERROR: GHL_PRIVATE_INTEGRATION_TOKEN is not set."
	echo "Add it in Cloudflare → Settings → Build → Variables and secrets"
	exit 1
fi

if [ -z "${GHL_LOCATION_ID:-}" ]; then
	echo "ERROR: GHL_LOCATION_ID is not set."
	echo "Add it in Cloudflare → Settings → Build → Variables and secrets"
	exit 1
fi

echo "Installing Python dependencies..."
python3 -m pip install --user -r requirements.txt

echo "Syncing Meta ads..."
python3 scripts/sync_meta_ads.py

echo "Syncing GHL CRM..."
python3 scripts/sync_ghl.py

echo "Building Evidence sources..."
npm run sources

echo "Patching Vite config for Cloudflare asset limits..."
node scripts/patch-vite-config.js

echo "Building static site..."
rm -rf build
npm run build

echo "Checking build output file sizes..."
oversized="$(find build -type f -size +25M 2>/dev/null || true)"
if [ -n "$oversized" ]; then
	echo "ERROR: Cloudflare Pages rejects files over 25 MiB:"
	echo "$oversized"
	exit 1
fi
