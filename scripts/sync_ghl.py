#!/usr/bin/env python3
"""Pull GoHighLevel contacts and opportunities into DuckDB for Evidence dashboards."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import duckdb
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "sources" / "ghl" / "ghl.duckdb"
SNAPSHOT_PATH = ROOT / "sources" / "ghl" / "ghl.snapshot.duckdb"
BASE_URL = "https://services.leadconnectorhq.com"
API_VERSION = "2021-07-28"
PAGE_SIZE = 100

CONTACTS_DDL = """
    id VARCHAR,
    location_id VARCHAR,
    contact_name VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    email VARCHAR,
    phone VARCHAR,
    source VARCHAR,
    type VARCHAR,
    date_added TIMESTAMP,
    date_updated TIMESTAMP,
    utm_source VARCHAR,
    utm_medium VARCHAR,
    utm_campaign VARCHAR,
    utm_content VARCHAR,
    utm_term VARCHAR,
    utm_keyword VARCHAR,
    device_type VARCHAR,
    user_agent VARCHAR,
    referrer VARCHAR,
    page_url VARCHAR,
    session_source VARCHAR,
    tags VARCHAR
"""

OPPORTUNITIES_DDL = """
    id VARCHAR,
    location_id VARCHAR,
    name VARCHAR,
    contact_id VARCHAR,
    pipeline_id VARCHAR,
    pipeline_stage_id VARCHAR,
    status VARCHAR,
    source VARCHAR,
    monetary_value DOUBLE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_status_change_at TIMESTAMP,
    utm_source VARCHAR,
    utm_medium VARCHAR,
    utm_campaign VARCHAR,
    utm_content VARCHAR,
    utm_term VARCHAR,
    utm_keyword VARCHAR
"""


def load_config() -> tuple[str | None, str | None]:
    load_dotenv(ROOT / ".env")
    token = os.getenv("GHL_PRIVATE_INTEGRATION_TOKEN")
    location_id = os.getenv("GHL_LOCATION_ID", "").strip()
    return token, location_id or None


def api_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Version": API_VERSION,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def first_attribution(record: dict) -> dict:
    attributions = record.get("attributions") or []
    return attributions[0] if attributions else {}


def device_type_from_user_agent(user_agent: str | None) -> str:
    if not user_agent:
        return "unknown"

    ua = user_agent.lower()
    if "iphone" in ua or "ipad" in ua:
        return "ios"
    if "android" in ua:
        return "android"
    if "mobile" in ua:
        return "mobile_other"
    return "desktop"


def attribution_fields(record: dict) -> dict[str, str | None]:
    attr = first_attribution(record)
    user_agent = attr.get("userAgent")
    page_url = attr.get("pageUrl") or attr.get("url")

    return {
        "utm_source": attr.get("utmSource"),
        "utm_medium": attr.get("utmMedium"),
        "utm_campaign": attr.get("utmCampaign"),
        "utm_content": attr.get("utmContent"),
        "utm_term": attr.get("utmTerm"),
        "utm_keyword": attr.get("utmKeyword"),
        "device_type": device_type_from_user_agent(user_agent),
        "user_agent": user_agent,
        "referrer": attr.get("referrer"),
        "page_url": page_url,
        "session_source": attr.get("utmSessionSource"),
    }


def fetch_contacts(token: str, location_id: str) -> list[dict]:
    headers = api_headers(token)
    params: dict[str, str | int] = {
        "locationId": location_id,
        "limit": PAGE_SIZE,
    }
    rows: list[dict] = []

    while True:
        response = requests.get(
            f"{BASE_URL}/contacts/",
            headers=headers,
            params=params,
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        contacts = payload.get("contacts") or []

        for contact in contacts:
            utm = attribution_fields(contact)
            rows.append(
                {
                    "id": contact.get("id"),
                    "location_id": contact.get("locationId"),
                    "contact_name": contact.get("contactName"),
                    "first_name": contact.get("firstName"),
                    "last_name": contact.get("lastName"),
                    "email": contact.get("email"),
                    "phone": contact.get("phone"),
                    "source": contact.get("source"),
                    "type": contact.get("type"),
                    "date_added": contact.get("dateAdded"),
                    "date_updated": contact.get("dateUpdated"),
                    "tags": ",".join(contact.get("tags") or []),
                    **utm,
                }
            )

        meta = payload.get("meta") or {}
        if not meta.get("nextPageUrl"):
            break

        params = {
            "locationId": location_id,
            "limit": PAGE_SIZE,
            "startAfter": meta["startAfter"],
            "startAfterId": meta["startAfterId"],
        }

    return rows


def fetch_opportunities(token: str, location_id: str) -> list[dict]:
    headers = api_headers(token)
    rows: list[dict] = []
    page = 1

    while True:
        response = requests.post(
            f"{BASE_URL}/opportunities/search",
            headers=headers,
            json={"locationId": location_id, "limit": PAGE_SIZE, "page": page},
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        opportunities = payload.get("opportunities") or []
        total = int(payload.get("total") or 0)

        for opp in opportunities:
            utm = attribution_fields(opp)
            rows.append(
                {
                    "id": opp.get("id"),
                    "location_id": opp.get("locationId"),
                    "name": opp.get("name"),
                    "contact_id": opp.get("contactId"),
                    "pipeline_id": opp.get("pipelineId"),
                    "pipeline_stage_id": opp.get("pipelineStageId"),
                    "status": opp.get("status"),
                    "source": opp.get("source"),
                    "monetary_value": float(opp.get("monetaryValue") or 0),
                    "created_at": opp.get("createdAt"),
                    "updated_at": opp.get("updatedAt"),
                    "last_status_change_at": opp.get("lastStatusChangeAt"),
                    **utm,
                }
            )

        if not opportunities or page * PAGE_SIZE >= total:
            break
        page += 1

    return rows


def write_table(table: str, ddl: str, rows: list[dict], columns: list[str]) -> int:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    placeholders = ", ".join(["?"] * len(columns))
    insert_sql = f"INSERT INTO {table} VALUES ({placeholders})"

    con = duckdb.connect(str(DB_PATH))
    con.execute(f"DROP TABLE IF EXISTS {table}")
    con.execute(f"CREATE TABLE {table} ({ddl})")
    if rows:
        con.executemany(insert_sql, [tuple(row[col] for col in columns) for row in rows])
    con.close()

    print(f"Synced {len(rows)} rows to {table}")
    return len(rows)


def save_snapshot() -> None:
    if DB_PATH.exists():
        shutil.copy2(DB_PATH, SNAPSHOT_PATH)
        print(f"Updated GHL snapshot at {SNAPSHOT_PATH}")


def keep_or_fail(reason: str) -> int:
    if DB_PATH.exists():
        print(f"{reason} — keeping existing GHL data.", file=sys.stderr)
        return 0
    if SNAPSHOT_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SNAPSHOT_PATH, DB_PATH)
        print(f"{reason} — restored GHL data from snapshot.", file=sys.stderr)
        return 0
    print(f"{reason} — no cached GHL data available.", file=sys.stderr)
    return 1


def main() -> int:
    token, location_id = load_config()

    if not token or token in {"REPLACE_WITH_YOUR_TOKEN", "your_token_here"}:
        print("No GHL_PRIVATE_INTEGRATION_TOKEN found — skipping GHL sync.")
        return 0

    if not location_id:
        print("Missing GHL_LOCATION_ID in .env", file=sys.stderr)
        return 1

    print(f"Fetching GHL data for location {location_id}...")
    try:
        contacts = fetch_contacts(token, location_id)
        opportunities = fetch_opportunities(token, location_id)
    except requests.RequestException as error:
        print(f"GHL sync failed: {error}", file=sys.stderr)
        return keep_or_fail("GHL sync failed")

    contact_columns = [
        "id",
        "location_id",
        "contact_name",
        "first_name",
        "last_name",
        "email",
        "phone",
        "source",
        "type",
        "date_added",
        "date_updated",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
        "utm_keyword",
        "device_type",
        "user_agent",
        "referrer",
        "page_url",
        "session_source",
        "tags",
    ]
    opportunity_columns = [
        "id",
        "location_id",
        "name",
        "contact_id",
        "pipeline_id",
        "pipeline_stage_id",
        "status",
        "source",
        "monetary_value",
        "created_at",
        "updated_at",
        "last_status_change_at",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
        "utm_keyword",
    ]

    write_table("contacts", CONTACTS_DDL, contacts, contact_columns)
    write_table("opportunities", OPPORTUNITIES_DDL, opportunities, opportunity_columns)
    save_snapshot()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
