---
title: Campaign Performance
description: Overall lead activity and Facebook ad performance for the last 30 days.
sidebar: never
hide_breadcrumbs: true
---

<CampaignSummary />

```sql report_dates
select cast(date_added as date) as report_date from ghl.contacts
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
    sum(
        case when utm_source = 'facebook' and utm_medium = 'cpc' then 1 else 0 end
    ) as facebook_ad_leads
from ghl.contacts
where cast(date_added as date) >= '${inputs.date_range.start}'
  and cast(date_added as date) <= '${inputs.date_range.end}'
```

<CrmMetricBlocks data={crm_totals} showShowingsBooked={false} />

## Lead Sources

All campaigns and channels driving leads into the CRM.

```sql lead_channels
select
    case
        when utm_source = 'facebook' and utm_medium = 'cpc' then 'Facebook Ads'
        when utm_medium = 'email' or utm_source ilike '%email%' then 'Email'
        when utm_medium = 'print' then 'Print'
        when utm_source is null or trim(utm_source) = '' then
            case
                when session_source = 'Direct traffic' then 'No Campaign Tag'
                when session_source = 'Social media' then 'Social'
                when session_source = 'Organic Search' then 'Organic Search'
                else 'Untracked (no UTM)'
            end
        else coalesce(utm_source, 'Other')
    end as channel,
    count(*) as leads
from ghl.contacts
where cast(date_added as date) >= '${inputs.date_range.start}'
  and cast(date_added as date) <= '${inputs.date_range.end}'
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
    select
        cast(date_added as date) as lead_date,
        case
            when utm_source = 'facebook' and utm_medium = 'cpc' then 'Facebook Ads'
            when utm_medium = 'email' or utm_source ilike '%email%' then 'Email'
            when utm_medium = 'print' then 'Print'
            when utm_source is null or trim(utm_source) = '' then
                case
                    when session_source = 'Direct traffic' then 'No Campaign Tag'
                    when session_source = 'Social media' then 'Social'
                    when session_source = 'Organic Search' then 'Organic Search'
                    else 'Untracked (no UTM)'
                end
            else coalesce(utm_source, 'Other')
        end as channel
    from ghl.contacts
    where cast(date_added as date) >= '${inputs.date_range.start}'
      and cast(date_added as date) <= '${inputs.date_range.end}'
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
        sum(
            case when utm_source = 'facebook' and utm_medium = 'cpc' then 1 else 0 end
        ) as facebook_ad_leads
    from ghl.contacts
    where cast(date_added as date) >= '${inputs.date_range.start}'
      and cast(date_added as date) <= '${inputs.date_range.end}'
)
select
    m.impressions,
    m.landing_page_clicks,
    c.facebook_ad_leads as learn_more_forms
from meta m
cross join crm c
```

<FunnelMetricBlocks data={funnel_totals} showShowingsRequested={false} />

```sql lead_cumulative
with daily as (
    select
        cast(date_added as date) as lead_date,
        count(*) as daily_leads
    from ghl.contacts
    where utm_source = 'facebook' and utm_medium = 'cpc'
      and cast(date_added as date) >= '${inputs.date_range.start}'
      and cast(date_added as date) <= '${inputs.date_range.end}'
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
        coalesce(daily.daily_leads, 0) as daily_leads
    from date_span d
    left join daily on d.lead_date = daily.lead_date
)
select
    lead_date,
    strftime(lead_date, '%b %d') as lead_date_label,
    sum(daily_leads) over (
        order by lead_date
        rows between unbounded preceding and current row
    ) as cumulative_leads
from filled
order by lead_date
```

<LineChart
    data={lead_cumulative}
    title="Cumulative Facebook ad leads"
    x=lead_date_label
    y=cumulative_leads
    sort=false
    yFmt='#,##0'
/>
