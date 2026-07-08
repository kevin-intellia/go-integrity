#!/usr/bin/env python3
"""Clip Facebook CRM lead dates to synced Meta spend bounds in pages/meta-ads.md."""

from __future__ import annotations

import re
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "pages" / "meta-ads.md"

BOUNDS = """spend_bounds as (
    select
        min(date_start) as spend_start,
        max(date_start) as spend_end
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),"""

QUERIES = [
    "creative_type_comparison",
    "creative_type_by_audience",
    "adset_efficiency",
    "adset_funnel",
    "facebook_funnel_chart",
    "cpl_by_audience_weekly",
    "creative_type_cpl_weekly",
    "audience_spend_leads_scatter",
    "spend_efficiency_weekly",
    "device_breakdown",
    "device_funnel_over_time",
]

PLAIN_WHERE = (
    "    where lr.channel = 'Facebook Ads'\n"
    "      and lr.lead_date >= '${inputs.date_range.start}'\n"
    "      and lr.lead_date <= '${inputs.date_range.end}'"
)
ALIGNED_WHERE = (
    "    cross join spend_bounds b\n"
    "    where lr.channel = 'Facebook Ads'\n"
    "      and lr.lead_date >= greatest(b.spend_start, cast('${inputs.date_range.start}' as date))\n"
    "      and lr.lead_date <= least(b.spend_end, cast('${inputs.date_range.end}' as date))"
)

PIPELINE_WHERE = (
    "    where lr.channel = 'Facebook Ads'\n"
    "      and o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c'\n"
    "      and lr.lead_date >= '${inputs.date_range.start}'\n"
    "      and lr.lead_date <= '${inputs.date_range.end}'"
)
PIPELINE_ALIGNED = (
    "    cross join spend_bounds b\n"
    "    where lr.channel = 'Facebook Ads'\n"
    "      and o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c'\n"
    "      and lr.lead_date >= greatest(b.spend_start, cast('${inputs.date_range.start}' as date))\n"
    "      and lr.lead_date <= least(b.spend_end, cast('${inputs.date_range.end}' as date))"
)


def patch_block(block: str) -> str:
    if "lr.channel = 'Facebook Ads'" not in block:
        return block
    if "spend_bounds as (" not in block:
        block = block.replace("with ", f"with {BOUNDS}\n", 1)
    block = block.replace(PIPELINE_WHERE, PIPELINE_ALIGNED)
    block = block.replace(PLAIN_WHERE, ALIGNED_WHERE)
    return block


def main() -> None:
    text = PATH.read_text()
    for name in QUERIES:
        marker = f"```sql {name}\n"
        start = text.find(marker)
        if start == -1:
            continue
        end = text.find("\n```", start + len(marker))
        if end == -1:
            continue
        block = text[start : end + 4]
        text = text[:start] + patch_block(block) + text[end + 4 :]

    PATH.write_text(text)
    print(f"Patched {len(QUERIES)} query blocks in {PATH}")


if __name__ == "__main__":
    main()
