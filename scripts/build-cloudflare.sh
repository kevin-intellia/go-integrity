#!/usr/bin/env bash
set -euo pipefail

# client = client report only; internal = All + Facebook + A/B (no Campaign Analytics)
resolve_deploy_target() {
	if [ -n "${CLOUDFLARE_DEPLOY_TARGET:-}" ]; then
		echo "$CLOUDFLARE_DEPLOY_TARGET"
		return
	fi
	if [ -n "${1:-}" ]; then
		echo "$1"
		return
	fi
	if [[ "${CF_PAGES_PROJECT_NAME:-}" == *internal* ]]; then
		echo internal
		return
	fi
	echo client
}

DEPLOY_TARGET="$(resolve_deploy_target "${1:-}")"
echo "Cloudflare deploy target: $DEPLOY_TARGET (project: ${CF_PAGES_PROJECT_NAME:-local})"

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

echo "Preparing deploy target: $DEPLOY_TARGET"
bash scripts/prepare-deploy-target.sh "$DEPLOY_TARGET"

if [ "$DEPLOY_TARGET" = "internal" ]; then
	echo "Copying GHL split stats and form submissions for A/B test..."
	cp config/ghl_split_stats_home_ab.json static/ghl_split_stats_home_ab.json
	cp config/form_submissions_home_ab.json static/form_submissions_home_ab.json
	echo "Building Page 1 A/B test report (internal only)..."
	python3 scripts/build_ab_test_viz.py
fi

echo "Building static site ($DEPLOY_TARGET)..."
rm -rf build
PUBLIC_DEPLOY_TARGET="$DEPLOY_TARGET" npm run build

echo "Checking build output file sizes..."
oversized="$(find build -type f -size +25M 2>/dev/null || true)"
if [ -n "$oversized" ]; then
	echo "ERROR: Cloudflare Pages rejects files over 25 MiB:"
	echo "$oversized"
	exit 1
fi
