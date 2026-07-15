#!/usr/bin/env python3
"""Before/after split-test report using Meta + GHL contact APIs (synced to DuckDB).

Lead = CRM form submit: new contact with email on the split-test page URL.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "split_tests.json"
GHL_DB = ROOT / "sources" / "ghl" / "ghl.duckdb"
GHL_SNAPSHOT = ROOT / "sources" / "ghl" / "ghl.snapshot.duckdb"
META_DB = ROOT / "sources" / "meta_ads" / "meta_ads.duckdb"
META_SNAPSHOT = ROOT / "sources" / "meta_ads" / "meta_ads.snapshot.duckdb"

FORM_FILTER = """
    coalesce(email, '') != ''
    and coalesce(source, '') not in ('', '-')
"""


def parse_ts(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def pick_db(primary: Path, snapshot: Path) -> Path:
    if primary.exists():
        return primary
    if snapshot.exists():
        return snapshot
    raise FileNotFoundError(f"Missing data: {primary} and {snapshot}")


def count_forms(
    con: duckdb.DuckDBPyConnection,
    *,
    url_pattern: str,
    start: datetime,
    end: datetime | None,
    facebook_only: bool,
) -> dict:
    end_sql = "current_timestamp" if end is None else f"timestamp '{end.isoformat()}'"
    fb_filter = "and utm_source = 'facebook' and utm_medium = 'cpc'" if facebook_only else ""

    row = con.execute(
        f"""
        select
            count(*) as leads,
            sum(case when utm_source = 'facebook' and utm_medium = 'cpc' then 1 else 0 end) as fb_leads
        from ghl.contacts
        where date_added >= timestamp '{start.isoformat()}'
          and date_added < {end_sql}
          and {FORM_FILTER}
          and page_url ilike '{url_pattern}'
          {fb_filter}
        """
    ).fetchone()

    return {"leads": int(row[0] or 0), "fb_leads": int(row[1] or 0)}


def load_config(test_id: str) -> dict:
    config = json.loads(CONFIG_PATH.read_text())
    if test_id not in config:
        available = ", ".join(config)
        raise SystemExit(f"Unknown test '{test_id}'. Available: {available}")
    return config[test_id]


def main() -> int:
    parser = argparse.ArgumentParser(description="Split-test before/after report")
    parser.add_argument("test_id", nargs="?", default="home_page_1")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--facebook-only", action="store_true")
    args = parser.parse_args()

    if args.refresh:
        import subprocess

        for script in ("scripts/sync_meta_ads.py", "scripts/sync_ghl.py"):
            print(f"Running {script}...", file=sys.stderr)
            subprocess.run(
                [str(ROOT / ".venv/bin/python"), str(ROOT / script)],
                cwd=ROOT,
                check=True,
            )

    cfg = load_config(args.test_id)
    test_start = parse_ts(cfg["test_started_at"])
    baseline_start = parse_ts(f"{cfg['baseline_start']}T00:00:00+00:00")
    control_pat = cfg["control_url_pattern"]
    variation_pat = cfg["variation_url_pattern"]
    legacy_patterns = cfg.get("legacy_baseline_url_patterns", [])

    con = duckdb.connect()
    con.execute(f"ATTACH '{pick_db(GHL_DB, GHL_SNAPSHOT)}' AS ghl (READ_ONLY)")

    lead_key = "fb_leads" if args.facebook_only else "leads"

    before_legacy = None
    if legacy_patterns:
        clauses = " or ".join(f"page_url ilike '{p}'" for p in legacy_patterns)
        end_sql = f"timestamp '{test_start.isoformat()}'"
        fb_filter = "and utm_source = 'facebook' and utm_medium = 'cpc'" if args.facebook_only else ""
        n = con.execute(
            f"""
            select count(*) from ghl.contacts
            where date_added >= timestamp '{baseline_start.isoformat()}'
              and date_added < {end_sql}
              and {FORM_FILTER}
              and ({clauses})
              {fb_filter}
            """
        ).fetchone()[0]
        before_legacy = int(n)

    before_control = count_forms(
        con, url_pattern=control_pat, start=baseline_start, end=test_start, facebook_only=args.facebook_only
    )
    after_control = count_forms(
        con, url_pattern=control_pat, start=test_start, end=None, facebook_only=args.facebook_only
    )
    after_variation = count_forms(
        con, url_pattern=variation_pat, start=test_start, end=None, facebook_only=args.facebook_only
    )

    print()
    print(cfg["label"])
    print("=" * len(cfg["label"]))
    print(f"Test started (UTC): {test_start.isoformat()}")
    print("Lead = CRM form submit (contact with email) on page_url")
    print(f"Control URL:   ...{control_pat.strip('%')}")
    print(f"Variation URL: ...{variation_pat.strip('%')}")
    print()

    if before_legacy is not None:
        print(f"Before test (legacy home/root URLs):  {before_legacy:>4} form submits")

    print(f"Before test (control URL):            {before_control[lead_key]:>4} form submits")
    print(f"After test  (control URL):            {after_control[lead_key]:>4} form submits")
    print(f"After test  (variation URL):          {after_variation[lead_key]:>4} form submits")
    print(f"After test  (both URLs combined):       {after_control[lead_key] + after_variation[lead_key]:>4} form submits")
    print()

    if cfg.get("notes"):
        print(cfg["notes"])
    print()

    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
