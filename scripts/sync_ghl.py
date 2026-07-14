#!/usr/bin/env python3
"""Pull GoHighLevel contacts and opportunities into DuckDB for Evidence dashboards."""

from __future__ import annotations

import os
import shutil
import sys
import time
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


RETRYABLE_STATUS_CODES = {400, 429, 500, 502, 503, 504}
RETRY_DELAYS_SECONDS = (1, 2, 4)


def request_with_retries(method: str, url: str, **kwargs) -> requests.Response:
    last_error: requests.RequestException | None = None

    for attempt, delay in enumerate((*RETRY_DELAYS_SECONDS, None)):
        try:
            response = requests.request(method, url, **kwargs)
            if response.status_code in RETRYABLE_STATUS_CODES and delay is not None:
                print(
                    f"GHL request retry {attempt + 1}/{len(RETRY_DELAYS_SECONDS)} "
                    f"after HTTP {response.status_code} for {url}",
                    file=sys.stderr,
                )
                time.sleep(delay)
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            last_error = error
            if delay is None:
                raise
            print(
                f"GHL request retry {attempt + 1}/{len(RETRY_DELAYS_SECONDS)} "
                f"after error: {error}",
                file=sys.stderr,
            )
            time.sleep(delay)

    if last_error:
        raise last_error
    raise RuntimeError(f"GHL request failed for {url}")


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
    expected_total: int | None = None

    while True:
        response = request_with_retries(
            "GET",
            f"{BASE_URL}/contacts/",
            headers=headers,
            params=params,
            timeout=120,
        )
        payload = response.json()
        contacts = payload.get("contacts") or []
        meta = payload.get("meta") or {}

        if expected_total is None:
            expected_total = int(meta.get("total") or 0) or None

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

        if expected_total is not None and len(rows) >= expected_total:
            break
        if not contacts or not meta.get("nextPageUrl"):
            break

        params = {
            "locationId": location_id,
            "limit": PAGE_SIZE,
            "startAfter": int(meta["startAfter"]),
            "startAfterId": meta["startAfterId"],
        }

    if expected_total is not None and len(rows) < expected_total:
        raise RuntimeError(
            f"GHL contacts sync incomplete: fetched {len(rows)} of {expected_total}"
        )

    return rows


def fetch_opportunities(token: str, location_id: str) -> list[dict]:
    headers = api_headers(token)
    rows: list[dict] = []
    page = 1

    expected_total: int | None = None

    while True:
        response = request_with_retries(
            "POST",
            f"{BASE_URL}/opportunities/search",
            headers=headers,
            json={"locationId": location_id, "limit": PAGE_SIZE, "page": page},
            timeout=120,
        )
        payload = response.json()
        opportunities = payload.get("opportunities") or []
        total = int(payload.get("total") or 0)
        if expected_total is None:
            expected_total = total or None

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

    if expected_total is not None and len(rows) < expected_total:
        raise RuntimeError(
            f"GHL opportunities sync incomplete: fetched {len(rows)} of {expected_total}"
        )

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


LEAD_RECORDS_VIEW = """
create or replace view lead_records as
select
    o.id as opportunity_id,
    o.contact_id,
    cast(coalesce(c.date_added, o.created_at) as date) as lead_date,
    o.source as opportunity_source,
    c.source as contact_source,
    c.utm_source,
    c.utm_medium,
    c.session_source,
    case
        when c.utm_source = 'facebook' and c.utm_medium = 'cpc' then 'Facebook'
        when c.utm_medium = 'email' or c.utm_source ilike '%email%' then 'Email'
        when c.utm_medium = 'print' then 'Print'
        when o.source in ('Integrity Website Inquires', 'Integrity Website Inquiries') then 'Integrity Website'
        when o.source = 'Listing Realtor Referral Leads' then 'Realtor Referral'
        when o.source in ('Realtors', 'Realors') then 'Realtors'
        when o.source = 'FB Community/Marketplace Ad' then 'Facebook Marketplace'
        when c.utm_source is null or trim(c.utm_source) = '' then
            case
                when c.session_source = 'Direct traffic' then 'No Campaign Tag'
                when c.session_source = 'Social media' then 'Social'
                when c.session_source = 'Organic Search' then 'Organic Search'
                when o.source is not null and trim(o.source) != '' then o.source
                when c.source is not null and trim(c.source) != '' then c.source
                else 'Untracked (no UTM)'
            end
        else coalesce(c.utm_source, 'Other')
    end as channel
from opportunities o
join contacts c on c.id = o.contact_id
where not (
    lower(coalesce(c.email, '')) in ('test@test.com', 'test@gmail.com')
    or lower(coalesce(c.email, '')) like '%intelliadigital.com'
    or lower(trim(coalesce(c.first_name, ''))) in ('test', 'test 1')
    or lower(trim(coalesce(c.last_name, ''))) = 'test'
)
"""


def ensure_lead_records_view() -> None:
    if not DB_PATH.exists():
        return
    con = duckdb.connect(str(DB_PATH))
    con.execute(LEAD_RECORDS_VIEW)
    con.close()


def save_snapshot() -> None:
    if DB_PATH.exists():
        shutil.copy2(DB_PATH, SNAPSHOT_PATH)
        print(f"Updated GHL snapshot at {SNAPSHOT_PATH}")


def keep_or_fail(reason: str) -> int:
    if DB_PATH.exists():
        print(f"{reason} — keeping existing GHL data.", file=sys.stderr)
        ensure_lead_records_view()
        return 0
    if SNAPSHOT_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SNAPSHOT_PATH, DB_PATH)
        print(f"{reason} — restored GHL data from snapshot.", file=sys.stderr)
        ensure_lead_records_view()
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
    ensure_lead_records_view()
    save_snapshot()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
