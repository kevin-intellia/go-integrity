#!/usr/bin/env python3
"""One-off reorganizer for pages/meta-ads.md — run from repo root."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "pages" / "meta-ads.md"


def extract_block(text: str, start_pattern: str, end_pattern: str | None) -> tuple[str, str, str]:
    m = re.search(start_pattern, text, re.MULTILINE)
    if not m:
        raise ValueError(f"Start not found: {start_pattern}")
    start = m.start()
    if end_pattern:
        pat = end_pattern if end_pattern != "$" else r"\Z"
        em = re.search(pat, text[m.end() :], re.MULTILINE)
        if not em:
            raise ValueError(f"End not found after {start_pattern}: {end_pattern}")
        end = m.end() + em.start()
    else:
        end = len(text)
    return text[:start], text[start:end], text[end:]


def remove_block(text: str, start_pattern: str, end_pattern: str) -> str:
    before, block, after = extract_block(text, start_pattern, end_pattern)
    return before + after


def move_block(text: str, start_pattern: str, end_pattern: str, insert_before: str) -> str:
    before, block, after = extract_block(text, start_pattern, end_pattern)
    rest = before + after
    idx = rest.index(insert_before)
    return rest[:idx] + block + rest[idx:]


def strip_duplicate_h4_before_datatables(text: str) -> str:
    return re.sub(
        r"\n#### [^\n]+\n\n[^\n<`][^\n]*\n\n(?=<DataTable)",
        "\n",
        text,
    )


def main() -> None:
    text = PATH.read_text()

    # --- terminology & labels ---
    text = text.replace("then 'national'", "then 'National'")
    text = text.replace("like '%multi-geo%' then 'national'", "like '%multi-geo%' then 'National'")
    text = text.replace("'national'", "'National'")
    text = text.replace('title="CTR"', 'title="Link CTR"')
    text = text.replace(
        "Click-through rate: page visits divided by impressions",
        "Link clicks divided by impressions (not Meta all-clicks CTR)",
    )
    text = text.replace("fmt=usd description", "fmt='$#,##0.00' description")
    text = text.replace("fmt=usd />", "fmt='$#,##0.00' />")
    text = text.replace("fmt=usd\n", "fmt='$#,##0.00'\n")
    text = text.replace("learn_more_forms", "facebook_leads")
    text = text.replace("Lead Forms", "Leads (CRM)")
    text = text.replace("Form %", "Lead %")
    text = text.replace("Lead forms as a percent", "CRM leads as a percent")
    text = text.replace("Cost / Showing", "Cost per showing")
    text = text.replace(
        'Campaign" description="Northeast or national',
        'Campaign" description="Northeast or National',
    )
    text = text.replace("Northeast or national campaign", "Northeast or National campaign")
    text = text.replace("('Northeast', 'national')", "('Northeast', 'National')")

    # intro + data freshness
    text = text.replace(
        "<p class=\"text-sm text-base-content-muted mb-4\">\n"
        "    Full lead activity across every channel. The overview summarizes all sources; "
        "each channel section below breaks down performance, sources, and individual leads.\n"
        "</p>",
        "<p class=\"text-sm text-base-content-muted mb-4\">\n"
        "    Internal campaign analytics across all channels. Meta spend and CRM leads use matching dates "
        "wherever CPL is calculated. Use the date range filter to explore different periods.\n"
        "</p>\n\n"
        "```sql meta_data_freshness\n"
        "select\n"
        "    max(date_start) as latest_meta_spend_date,\n"
        "    max(lead_date) as latest_crm_lead_date\n"
        "from meta_ads.daily_campaign_insights\n"
        "cross join (\n"
        "    select max(lead_date) as lead_date from ghl._lead_records\n"
        ") crm\n"
        "```\n\n"
        "<p class=\"text-xs text-base-content-muted mb-4\">\n"
        "    Data freshness: Meta spend through {meta_data_freshness[0].latest_meta_spend_date}; "
        "CRM leads through {meta_data_freshness[0].latest_crm_lead_date}. "
        "CPL metrics only count leads on dates with synced Meta spend.\n"
        "</p>",
    )

    # Remove redundant facebook lead breakdown block (stop before roster)
    text = remove_block(
        text,
        r"```sql facebook_lead_breakdown\n",
        r"\n#### Facebook lead roster\n",
    )

    # Remove showings by audience section
    text = remove_block(
        text,
        r"### Showings by audience\n",
        r"\n### Facebook charts\n",
    )

    # Slim overview charts: remove redundant blocks
    for start, end in [
        (r"```sql daily_leads_total\n", r"\n```sql appointments_over_time\n"),
        (r"```sql appointments_over_time\n", r"\n```sql appointments_total_over_time\n"),
        (r"<BarChart\n    data=\{lead_breakdown_channel\}\n", r"\n```sql mobile_pct_over_time\n"),
        (r"```sql referrer_breakdown\n", r"\n---\n\n## Facebook Ads\n"),
    ]:
        try:
            text = remove_block(text, start, end)
        except ValueError:
            pass

    text = text.replace("### Charts & trends", "### Key trends")

    # Remove fb_channel_totals block at facebook start (redundant with spend cards)
    try:
        text = remove_block(
            text,
            r"```sql fb_channel_totals\n",
            r"\n#### Facebook lead roster\n",
        )
    except ValueError:
        try:
            text = remove_block(
                text,
                r"```sql fb_channel_totals\n",
                r"\n### Spend and efficiency\n",
            )
        except ValueError:
            pass

    # Remove duplicate adset efficiency bar charts (keep table only)
    try:
        text = remove_block(
            text,
            r"\n<Grid cols=2>\n    <BarChart\n        data=\{adset_efficiency\}\n",
            r"\n</Grid>\n\n### Audience funnel\n",
        )
    except ValueError:
        pass

    # Remove campaign_group_performance grid from facebook charts
    try:
        text = remove_block(
            text,
            r"```sql campaign_group_performance\n",
            r"\n```sql audience_spend_leads_scatter\n",
        )
    except ValueError:
        pass

    # Move spend section to top of Facebook (right after ## Facebook Ads intro)
    fb_intro_end = (
        "Read top-to-bottom: spend & efficiency → funnel → creative type → "
        "audiences → device → spend trends → lead roster.\n\n"
    )
    if "### Spend and efficiency" in text.split("## Facebook Ads")[1][:12000]:
        before_fb, fb_rest = text.split("## Facebook Ads", 1)
        fb_rest = "## Facebook Ads" + fb_rest
        _, spend_block, _ = extract_block(
            fb_rest,
            r"### Spend and efficiency\n",
            r"\n### Static vs dynamic creative\n",
        )
        fb_rest = remove_block(
            fb_rest,
            r"### Spend and efficiency\n",
            r"\n### Static vs dynamic creative\n",
        )
        # Update intro before inserting spend
        fb_rest = fb_rest.replace(
            "Paid Meta campaigns tracked in Ads Manager and attributed in the CRM via "
            "`utm_source=facebook` and `utm_medium=cpc`. Includes ad delivery, spend efficiency, "
            "and audience performance.\n\n",
            "Paid Meta campaigns attributed in the CRM via `utm_source=facebook` and "
            "`utm_medium=cpc`. "
            + fb_intro_end,
        )
        insert_at = fb_rest.index(fb_intro_end) + len(fb_intro_end)
        fb_rest = fb_rest[:insert_at] + spend_block + fb_rest[insert_at:]
        text = before_fb + fb_rest

    # Move facebook lead roster to before Performance highlights
    perf_marker = "\n### Performance highlights\n"
    for end_pat in (r"\n### Static vs dynamic creative\n", perf_marker):
        try:
            text = move_block(
                text,
                r"#### Facebook lead roster\n",
                end_pat,
                perf_marker,
            )
            break
        except ValueError:
            continue

    # Move all appointments section before Facebook (section lives at end of file)
    appts_marker = "\n---\n\n## Facebook Ads\n"
    if appts_marker not in text:
        appts_marker = "\n## Facebook Ads\n"
    try:
        text = move_block(
            text,
            r"### All appointments\n",
            r"$",
            appts_marker,
        )
    except ValueError:
        pass

    # Move appointments total chart up in overview (after lead totals)
    try:
        text = move_block(
            text,
            r"```sql appointments_total_over_time\n",
            r"\n<BarChart\n    data=\{lead_breakdown_channel\}\n",
            r"<CrmMetricBlocks data={crm_totals} />\n\n",
        )
    except ValueError:
        pass

    # Move funnel chart SQL + component before static vs dynamic (after daily_cpl chart)
    try:
        before, funnel_sql, after = extract_block(
            text,
            r"```sql facebook_funnel_chart\n",
            r"\n```sql cpl_by_audience_weekly\n",
        )
        if "<FunnelChart" in after:
            chart_block, after = extract_block(after, r"<FunnelChart\n", r"\n```sql cpl_by_audience_weekly\n")
            funnel_block = funnel_sql + chart_block
            text = before + after
            insert_marker = r"\n### Static vs dynamic creative\n"
            idx = text.index(insert_marker)
            text = text[:idx] + funnel_block + text[idx:]
        else:
            text = move_block(
                text,
                r"```sql facebook_funnel_chart\n",
                r"\n```sql cpl_by_audience_weekly\n",
                r"\n### Static vs dynamic creative\n",
            )
    except ValueError:
        pass

    # Rename Facebook charts section
    text = text.replace(
        "### Facebook charts\n\nTrends and comparisons",
        "### Trends & diagnostics\n\nAdditional",
    )

    # Performance highlights caveat
    text = text.replace(
        "<PerformanceHighlights data={performance_highlights} />",
        "<p class=\"text-sm text-base-content-muted mb-4\">\n"
        "    The 3% real-estate CTR benchmark is a rough industry reference, not a guaranteed target.\n"
        "</p>\n\n"
        "<PerformanceHighlights data={performance_highlights} />",
    )

    # Device breakdown disclaimer
    text = text.replace(
        "How mobile and desktop perform across Meta delivery and CRM leads.\n\n```sql device_breakdown",
        "How mobile and desktop perform across Meta delivery and CRM leads. "
        "Meta device comes from impression delivery; CRM device comes from landing-page user agent — "
        "they measure different things.\n\n"
        "```sql device_breakdown",
    )

    # creative_type_by_audience filter + subtitle
    text = text.replace(
        "where m.creative_type in ('Static', 'Dynamic')\n)\nselect audience",
        "where m.creative_type in ('Static', 'Dynamic')\n"
        "    and (coalesce(c.facebook_leads, 0) > 0 or m.spend >= 50)\n"
        ")\nselect audience",
    )
    text = text.replace(
        'subtitle="Spend, page visits, CRM leads, and CPL for each audience within static or dynamic campaigns."',
        'subtitle="Audiences with meaningful spend or CRM leads. National campaign geos without UTM-matched leads are hidden."',
    )

    # Overview channel section copy
    text = text.replace(
        "### Channel summary\n\nLeads, appointments, and conversion rates across all marketing channels.",
        "### Channel performance\n\nChannel mix, appointment rates, and lead volume. The chart shows totals; the table adds showings.",
    )
    text = re.sub(
        r"### Leads by channel\n\n```sql lead_channels",
        "### Lead volume by channel\n\n```sql lead_channels",
        text,
        count=1,
    )

    # Remove mobile bar chart in overview
    try:
        text = remove_block(
            text,
            r"\n<BarChart\n    data=\{mobile_lead_breakdown\}\n",
            r"\n```sql mobile_leads_by_channel\n",
        )
    except ValueError:
        pass

    # Strip duplicate h4 before DataTables
    text = strip_duplicate_h4_before_datatables(text)

    PATH.write_text(text)
    print(f"Wrote {PATH}")


if __name__ == "__main__":
    main()
