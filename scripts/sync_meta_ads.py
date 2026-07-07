#!/usr/bin/env python3
"""Pull Meta Ads insights into DuckDB for Evidence dashboards."""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "sources" / "meta_ads" / "meta_ads.duckdb"
SNAPSHOT_PATH = ROOT / "sources" / "meta_ads" / "meta_ads.snapshot.duckdb"
GRAPH_API_VERSION = "v22.0"

# Conversion 1: submitted a form to learn more
CONVERSION_1_TYPES = {"lead"}

# Conversion 2: reached out to schedule a private showing (custom pixel event)
CONVERSION_2_TYPES = {"offsite_conversion.fb_pixel_custom"}

INSIGHTS_DDL = """
    date_start DATE,
    date_stop DATE,
    campaign_id VARCHAR,
    campaign_name VARCHAR,
    adset_id VARCHAR,
    adset_name VARCHAR,
    ad_id VARCHAR,
    ad_name VARCHAR,
    impressions BIGINT,
    clicks BIGINT,
    link_clicks BIGINT,
    spend DOUBLE,
    reach BIGINT,
    cpc DOUBLE,
    cpm DOUBLE,
    ctr DOUBLE,
    conversion_1 DOUBLE,
    conversion_2 DOUBLE,
    conversion_3 DOUBLE,
    conversion_4 DOUBLE,
    conversions DOUBLE
"""

INSIGHTS_INSERT = """
    INSERT INTO {table} VALUES
    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

INSIGHT_FIELDS = [
    "campaign_id",
    "campaign_name",
    "adset_id",
    "adset_name",
    "ad_id",
    "ad_name",
    "impressions",
    "clicks",
    "inline_link_clicks",
    "spend",
    "reach",
    "cpc",
    "cpm",
    "ctr",
    "actions",
    "date_start",
    "date_stop",
]


def load_config() -> tuple[str | None, str | None]:
    load_dotenv(ROOT / ".env")
    token = os.getenv("META_ACCESS_TOKEN")
    account_id = os.getenv("META_AD_ACCOUNT_ID", "").strip()
    if account_id and not account_id.startswith("act_"):
        account_id = f"act_{account_id}"
    return token, account_id or None


def fetch_insights(
    token: str,
    account_id: str,
    *,
    level: str,
    days: int = 30,
) -> list[dict]:
    since = (date.today() - timedelta(days=days)).isoformat()
    until = date.today().isoformat()

    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{account_id}/insights"
    params = {
        "access_token": token,
        "level": level,
        "fields": ",".join(INSIGHT_FIELDS),
        "time_range": json.dumps({"since": since, "until": until}),
        "time_increment": 1,
        "limit": 500,
    }

    rows: list[dict] = []
    while url:
        response = requests.get(url, params=params, timeout=120)
        if not response.ok:
            try:
                error_body = response.json()
            except ValueError:
                error_body = response.text
            print(f"Meta API error ({response.status_code}): {error_body}", file=sys.stderr)
        response.raise_for_status()
        payload = response.json()

        if "error" in payload:
            raise RuntimeError(payload["error"].get("message", payload["error"]))

        rows.extend(payload.get("data", []))
        url = payload.get("paging", {}).get("next")
        params = None

    return rows


def action_count(actions: list[dict], action_types: set[str]) -> float:
    total = 0.0
    for action in actions:
        if action.get("action_type") in action_types:
            total += float(action.get("value") or 0)
    return total


def normalize_row(row: dict) -> dict:
    actions = row.get("actions") or []
    conversion_1 = action_count(actions, CONVERSION_1_TYPES)
    conversion_2 = action_count(actions, CONVERSION_2_TYPES)
    # Placeholders until GHL / CRM data is connected
    conversion_3 = 0.0
    conversion_4 = 0.0

    return {
        "date_start": row.get("date_start"),
        "date_stop": row.get("date_stop"),
        "campaign_id": row.get("campaign_id"),
        "campaign_name": row.get("campaign_name"),
        "adset_id": row.get("adset_id"),
        "adset_name": row.get("adset_name"),
        "ad_id": row.get("ad_id"),
        "ad_name": row.get("ad_name"),
        "impressions": int(row.get("impressions") or 0),
        "clicks": int(row.get("clicks") or 0),
        "link_clicks": int(row.get("inline_link_clicks") or 0),
        "spend": float(row.get("spend") or 0),
        "reach": int(row.get("reach") or 0),
        "cpc": float(row.get("cpc") or 0),
        "cpm": float(row.get("cpm") or 0),
        "ctr": float(row.get("ctr") or 0),
        "conversion_1": conversion_1,
        "conversion_2": conversion_2,
        "conversion_3": conversion_3,
        "conversion_4": conversion_4,
        "conversions": conversion_1 + conversion_2,
    }


def write_insights_table(table: str, rows: list[dict]) -> int:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    normalized = [normalize_row(row) for row in rows]

    con = duckdb.connect(str(DB_PATH))
    con.execute(f"DROP TABLE IF EXISTS {table}")
    con.execute(f"CREATE TABLE {table} ({INSIGHTS_DDL})")
    if normalized:
        con.executemany(
            INSIGHTS_INSERT.format(table=table),
            [
                (
                    r["date_start"],
                    r["date_stop"],
                    r["campaign_id"],
                    r["campaign_name"],
                    r["adset_id"],
                    r["adset_name"],
                    r["ad_id"],
                    r["ad_name"],
                    r["impressions"],
                    r["clicks"],
                    r["link_clicks"],
                    r["spend"],
                    r["reach"],
                    r["cpc"],
                    r["cpm"],
                    r["ctr"],
                    r["conversion_1"],
                    r["conversion_2"],
                    r["conversion_3"],
                    r["conversion_4"],
                    r["conversions"],
                )
                for r in normalized
            ],
        )
    con.close()
    print(f"Synced {len(normalized)} rows to {table}")
    return len(normalized)


def save_snapshot() -> None:
    if DB_PATH.exists():
        shutil.copy2(DB_PATH, SNAPSHOT_PATH)
        print(f"Updated Meta snapshot at {SNAPSHOT_PATH}")


def keep_or_fail(reason: str) -> int:
    if DB_PATH.exists():
        print(f"{reason} — keeping existing Meta data.", file=sys.stderr)
        return 0
    if SNAPSHOT_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SNAPSHOT_PATH, DB_PATH)
        print(f"{reason} — restored Meta data from snapshot.", file=sys.stderr)
        return 0
    print(f"{reason} — no cached Meta data available.", file=sys.stderr)
    return 1


def main() -> int:
    token, account_id = load_config()

    if not token or token == "your_access_token_here":
        print("No META_ACCESS_TOKEN found.", file=sys.stderr)
        print("Copy .env.example to .env and add your Meta credentials when ready.", file=sys.stderr)
        return keep_or_fail("Missing Meta token")

    if not account_id:
        print("Missing META_AD_ACCOUNT_ID in .env", file=sys.stderr)
        return 1

    print(f"Fetching insights for {account_id}...")
    try:
        campaign_rows = fetch_insights(token, account_id, level="campaign", days=30)
        adset_rows = fetch_insights(token, account_id, level="adset", days=30)
        write_insights_table("daily_campaign_insights", campaign_rows)
        write_insights_table("daily_adset_insights", adset_rows)
        save_snapshot()
        return 0
    except requests.RequestException as error:
        print(f"Meta sync failed: {error}", file=sys.stderr)
        return keep_or_fail("Meta sync failed")


if __name__ == "__main__":
    raise SystemExit(main())
