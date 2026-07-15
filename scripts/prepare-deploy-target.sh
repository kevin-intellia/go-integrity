#!/usr/bin/env bash
# Remove pages that should not ship on each Cloudflare target.
set -euo pipefail

TARGET="${1:?Usage: prepare-deploy-target.sh client|internal}"
REDIRECTS="static/_redirects"

case "$TARGET" in
	client)
		for page in meta-ads.md home-ab-test.md; do
			if [ -f "pages/$page" ]; then
				rm -f "pages/$page"
				echo "Excluded internal page: pages/$page"
			fi
		done
		rm -f static/home-ab-test.html reports/home-ab-test.html
		echo "Excluded internal A/B report assets"
		cat > "$REDIRECTS" <<'EOF'
/ /client-report/ 302
/index /client-report/ 302
/index/ /client-report/ 302
EOF
		echo "Wrote client redirects"
		;;
	internal)
		for page in client-report.md meta-ads.md; do
			if [ -f "pages/$page" ]; then
				rm -f "pages/$page"
				echo "Excluded page: pages/$page"
			fi
		done
		rm -f "$REDIRECTS"
		echo "Internal home is index.md — no root redirects"
		;;
	*)
		echo "ERROR: TARGET must be 'client' or 'internal', got: $TARGET"
		exit 1
		;;
esac
