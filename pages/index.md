---
title: All
sidebar: never
hide_breadcrumbs: true
hide_toc: true
---

<p class="text-sm text-base-content-muted mb-2">
    <strong>All</strong> · <a href="/facebook/">Facebook</a>
</p>

<p class="text-sm text-base-content-muted mb-4">
    CRM leads and showings across every channel — Facebook, email, print, social, and more.
</p>

```sql report_dates
select lead_date as report_date from ghl._lead_records
union all
select date_start as report_date from meta_ads.daily_campaign_insights
```

```sql data_freshness
select max(lead_date) as latest_crm_lead_date from ghl._lead_records
```

<p class="text-xs text-base-content-muted mb-4">
    CRM leads fresh through {data_freshness[0].latest_crm_lead_date}.
</p>

<DateRange
    name=date_range
    data={report_dates}
    dates=report_date
    title="Date range"
    presetRanges={['Last 7 Days', 'Last 30 Days', 'All Time']}
    defaultValue="All Time"
/>

## Lead totals

```sql crm_totals
select
    count(*) as total_leads,
    sum(
        case when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1 else 0 end
    ) as showings_requested,
    sum(case when lr.channel = 'Facebook' then 1 else 0 end) as facebook_ad_leads
from ghl._lead_records lr
join ghl.opportunities o on o.id = lr.opportunity_id
where lr.lead_date >= '${inputs.date_range.start}'
  and lr.lead_date <= '${inputs.date_range.end}'
```

<CrmMetricBlocks data={crm_totals} />

## Showings over time

```sql appointments_total_over_time
with daily as (
    select
        lr.lead_date,
        sum(
            case when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1 else 0 end
        ) as daily_appointments
    from ghl._lead_records lr
    join ghl.opportunities o on o.id = lr.opportunity_id
    where lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
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
filled as (
    select
        d.lead_date,
        coalesce(daily.daily_appointments, 0) as daily_appointments
    from date_span d
    left join daily on d.lead_date = daily.lead_date
)
select
    lead_date,
    strftime(lead_date, '%b %d') as lead_date_label,
    sum(daily_appointments) over (
        order by lead_date
        rows between unbounded preceding and current row
    ) as cumulative_appointments
from filled
order by lead_date
```

<LineChart
    data={appointments_total_over_time}
    title="Cumulative showings requested (all channels)"
    x=lead_date_label
    y=cumulative_appointments
    sort=false
/>

## Leads over time

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
    select lead_date, channel, count(*) as daily_leads
    from classified
    group by 1, 2
),
daily_total as (
    select lead_date, count(*) as daily_leads
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
    select d.lead_date, c.channel
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

## Leads by channel

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

## Channel performance

```sql channel_performance
with base as (
    select
        lr.channel,
        count(*) as leads,
        sum(
            case when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1 else 0 end
        ) as showings
    from ghl._lead_records lr
    join ghl.opportunities o on o.id = lr.opportunity_id
    where lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
    group by 1
)
select
    channel,
    leads,
    round(100.0 * leads / nullif(sum(leads) over (), 0), 1) as lead_share_pct,
    showings,
    round(100.0 * showings / nullif(leads, 0), 1) as showing_rate_pct
from base
order by leads desc
```

<DataTable data={channel_performance} search=true rows=20 title="Channel performance">
    <Column id="channel" title="Channel" />
    <Column id="leads" title="Leads" fmt='#,##0' />
    <Column id="lead_share_pct" title="Lead %" fmt='0.0"%"' />
    <Column id="showings" title="Showings" fmt='#,##0' />
    <Column id="showing_rate_pct" title="Showing %" fmt='0.0"%"' />
</DataTable>

## CRM roster

Searchable lead and showing detail for the selected date range.

```sql all_leads_roster
select *
from ghl.all_leads
where lead_date >= '${inputs.date_range.start}'
  and lead_date <= '${inputs.date_range.end}'
order by lead_date desc, contact_name
```

```sql all_appointments
select *
from ghl.all_appointments
where lead_date >= '${inputs.date_range.start}'
  and lead_date <= '${inputs.date_range.end}'
order by lead_date desc, contact_name
```

<LeadShowingsRosterTabs leadsData={all_leads_roster} showingsData={all_appointments} />
