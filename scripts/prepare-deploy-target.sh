#!/usr/bin/env bash
# Remove the other dashboard page before build so it is not published at all.
set -euo pipefail

TARGET="${1:?Usage: prepare-deploy-target.sh client|internal}"

case "$TARGET" in
	client)
		if [ -f pages/meta-ads.md ]; then
			rm -f pages/meta-ads.md
			echo "Excluded internal page: pages/meta-ads.md"
		fi
		;;
	internal)
		if [ -f pages/client-report.md ]; then
			rm -f pages/client-report.md
			echo "Excluded client page: pages/client-report.md"
		fi
		;;
	*)
		echo "ERROR: TARGET must be 'client' or 'internal', got: $TARGET"
		exit 1
		;;
esac
