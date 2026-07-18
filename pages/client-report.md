---
title: Campaign Performance
description: Overall lead activity and Facebook ad performance for the last 30 days.
sidebar: never
hide_breadcrumbs: true
---

<CampaignSummary />

```sql report_dates
select lead_date as report_date from ghl._lead_records
union all
select date_start as report_date from meta_ads.daily_campaign_insights
```

<DateRange
    name=date_range
    data={report_dates}
    dates=report_date
    title="Date range"
    presetRanges={['Last 7 Days', 'Last 30 Days', 'Last 90 Days', 'All Time']}
    defaultValue="All Time"
/>

## Overall Lead Activity

All leads and outcomes across every channel.

```sql crm_totals
select
    count(*) as total_leads,
    sum(case when channel = 'Facebook' then 1 else 0 end) as facebook_ad_leads
from ghl._lead_records
where lead_date >= '${inputs.date_range.start}'
  and lead_date <= '${inputs.date_range.end}'
```

<CrmMetricBlocks data={crm_totals} showShowingsRequested={false} />

## Lead Sources

Marketing and referral sources — not individual forms.

```sql lead_channels
select
    channel,
    count(*) as leads
from ghl._lead_records
where lead_date >= '${inputs.date_range.start}'
  and lead_date <= '${inputs.date_range.end}'
group by 1
order by leads desc
```

<BarChart
    data={lead_channels}
    title="Leads by channel"
    x=channel
    y=leads
    swapXY=true
/>

## All Leads Over Time

Cumulative lead growth by channel — each line tracks one source; All is total leads across every channel.

```sql all_leads_cumulative
with classified as (
    select lead_date, channel
    from ghl._lead_records
    where lead_date >= '${inputs.date_range.start}'
      and lead_date <= '${inputs.date_range.end}'
),
channels as (
    select distinct channel from classified
),
daily as (
    select
        lead_date,
        channel,
        count(*) as daily_leads
    from classified
    group by 1, 2
),
daily_total as (
    select
        lead_date,
        count(*) as daily_leads
    from classified
    group by 1
),
date_span as (
    select unnest(
        generate_series(
            cast('${inputs.date_range.start}' as date),
            cast('${inputs.date_range.end}' as date),
            interval 1 day
        )
    )::date as lead_date
),
channel_dates as (
    select
        d.lead_date,
        c.channel
    from date_span d
    cross join channels c
),
filled as (
    select
        cd.lead_date,
        cd.channel,
        coalesce(daily.daily_leads, 0) as daily_leads
    from channel_dates cd
    left join daily
        on cd.lead_date = daily.lead_date
        and cd.channel = daily.channel
),
all_filled as (
    select
        d.lead_date,
        coalesce(daily_total.daily_leads, 0) as daily_leads
    from date_span d
    left join daily_total on d.lead_date = daily_total.lead_date
),
per_channel as (
    select
        lead_date,
        channel,
        strftime(lead_date, '%b %d') as lead_date_label,
        sum(daily_leads) over (
            partition by channel
            order by lead_date
            rows between unbounded preceding and current row
        ) as cumulative_leads
    from filled
),
all_series as (
    select
        lead_date,
        'All' as channel,
        strftime(lead_date, '%b %d') as lead_date_label,
        sum(daily_leads) over (
            order by lead_date
            rows between unbounded preceding and current row
        ) as cumulative_leads
    from all_filled
)
select * from per_channel
union all
select * from all_series
order by channel, lead_date
```

<CumulativeLeadsByChannelChart data={all_leads_cumulative} />

## Facebook Ads in Detail

Facebook is the largest lead source in this campaign. This section breaks out paid Meta ad performance — impressions, page visits, and lead forms — separately from email, print, and other channels above.

```sql funnel_totals
with meta as (
    select
        coalesce(sum(impressions), 0) as impressions,
        coalesce(sum(link_clicks), 0) as landing_page_clicks
    from meta_ads.daily_campaign_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
crm as (
    select
        sum(case when channel = 'Facebook' then 1 else 0 end) as facebook_ad_leads
    from ghl._lead_records
    where lead_date >= '${inputs.date_range.start}'
      and lead_date <= '${inputs.date_range.end}'
)
select
    m.impressions,
    m.landing_page_clicks,
    c.facebook_ad_leads as learn_more_forms
from meta m
cross join crm c
```

<FunnelMetricBlocks data={funnel_totals} showShowingsRequested={false} />

```sql lead_forms
select
    lead_form,
    count(*) as leads
from ghl._lead_records
where lead_date >= '${inputs.date_range.start}'
  and lead_date <= '${inputs.date_range.end}'
  and channel = 'Facebook'
  and lead_form is not null
group by 1
order by case lead_form when 'Website' then 1 when 'Funnel' then 2 else 3 end
```

<BarChart
    data={lead_forms}
    title="Leads by form"
    x=lead_form
    y=leads
    swapXY=true
/>

```sql facebook_leads_cumulative
with classified as (
    select lead_date, lead_form
    from ghl._lead_records
    where channel = 'Facebook'
      and lead_form is not null
      and lead_date >= '${inputs.date_range.start}'
      and lead_date <= '${inputs.date_range.end}'
),
forms as (
    select distinct lead_form from classified
),
daily as (
    select
        lead_date,
        lead_form,
        count(*) as daily_leads
    from classified
    group by 1, 2
),
daily_total as (
    select
        lead_date,
        count(*) as daily_leads
    from classified
    group by 1
),
date_span as (
    select unnest(
        generate_series(
            cast('${inputs.date_range.start}' as date),
            cast('${inputs.date_range.end}' as date),
            interval 1 day
        )
    )::date as lead_date
),
form_dates as (
    select
        d.lead_date,
        f.lead_form
    from date_span d
    cross join forms f
),
filled as (
    select
        fd.lead_date,
        fd.lead_form,
        coalesce(daily.daily_leads, 0) as daily_leads
    from form_dates fd
    left join daily
        on fd.lead_date = daily.lead_date
        and fd.lead_form = daily.lead_form
),
all_filled as (
    select
        d.lead_date,
        coalesce(daily_total.daily_leads, 0) as daily_leads
    from date_span d
    left join daily_total on d.lead_date = daily_total.lead_date
),
per_form as (
    select
        lead_date,
        lead_form as series,
        strftime(lead_date, '%b %d') as lead_date_label,
        sum(daily_leads) over (
            partition by lead_form
            order by lead_date
            rows between unbounded preceding and current row
        ) as cumulative_leads
    from filled
),
all_series as (
    select
        lead_date,
        'All' as series,
        strftime(lead_date, '%b %d') as lead_date_label,
        sum(daily_leads) over (
            order by lead_date
            rows between unbounded preceding and current row
        ) as cumulative_leads
    from all_filled
)
select * from per_form
union all
select * from all_series
order by series, lead_date
```

<LineChart
    data={facebook_leads_cumulative}
    title="Cumulative Facebook ad leads"
    x=lead_date_label
    y=cumulative_leads
    series=series
    seriesOrder={['All', 'Funnel', 'Website']}
    sort=false
    yFmt='#,##0'
/>
