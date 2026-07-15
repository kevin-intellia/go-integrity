#!/usr/bin/env bash
# Remove the other dashboard page before build so it is not published at all.
set -euo pipefail

TARGET="${1:?Usage: prepare-deploy-target.sh client|internal}"
REDIRECTS="static/_redirects"

case "$TARGET" in
	client)
		if [ -f pages/meta-ads.md ]; then
			rm -f pages/meta-ads.md
			echo "Excluded internal page: pages/meta-ads.md"
		fi
		cat > "$REDIRECTS" <<'EOF'
/ /client-report/ 302
/index /client-report/ 302
/index/ /client-report/ 302
EOF
		echo "Wrote client redirects"
		;;
	internal)
		if [ -f pages/client-report.md ]; then
			rm -f pages/client-report.md
			echo "Excluded client page: pages/client-report.md"
		fi
		cat > "$REDIRECTS" <<'EOF'
/ /meta-ads/ 302
/index /meta-ads/ 302
/index/ /meta-ads/ 302
EOF
		echo "Wrote internal redirects"
		;;
	*)
		echo "ERROR: TARGET must be 'client' or 'internal', got: $TARGET"
		exit 1
		;;
esac
