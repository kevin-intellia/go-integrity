#!/usr/bin/env bash
set -euo pipefail

echo "Installing Python dependencies..."
python3 -m pip install --user -r requirements.txt

echo "Syncing Meta ads..."
python3 scripts/sync_meta_ads.py

echo "Syncing GHL CRM..."
python3 scripts/sync_ghl.py

echo "Building Evidence sources..."
npm run sources

echo "Building static site..."
npm run build
