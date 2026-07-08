---
title: Campaign Analytics
sidebar: never
hide_breadcrumbs: true
hide_toc: false
---

<p class="text-sm text-base-content-muted mb-4">
    Internal campaign analytics across all channels. Meta spend and CRM leads use matching dates wherever CPL is calculated. Use the date range filter to explore different periods.
</p>

```sql meta_data_freshness
select
    max(date_start) as latest_meta_spend_date,
    max(lead_date) as latest_crm_lead_date
from meta_ads.daily_campaign_insights
cross join (
    select max(lead_date) as lead_date from ghl._lead_records
) crm
```

<p class="text-xs text-base-content-muted mb-4">
    Data freshness: Meta spend through {meta_data_freshness[0].latest_meta_spend_date}; CRM leads through {meta_data_freshness[0].latest_crm_lead_date}. CPL metrics only count leads on dates with synced Meta spend.
</p>

<RefreshDataButton />

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

## Overview

### Lead totals

```sql crm_totals
select
    count(*) as total_leads,
    sum(case when lr.channel = 'Facebook Ads' then 1 else 0 end) as facebook_ad_leads,
    sum(
        case when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1 else 0 end
    ) as appointments_scheduled
from ghl._lead_records lr
join ghl.opportunities o on o.id = lr.opportunity_id
join ghl.contacts c on c.id = lr.contact_id
where lr.lead_date >= '${inputs.date_range.start}'
  and lr.lead_date <= '${inputs.date_range.end}'
```

<CrmMetricBlocks data={crm_totals} />

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

### Lead volume by channel

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

### Leads over time

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

### Channel performance

Channel mix, appointment rates, and lead volume. The chart shows totals; the table adds showings.

```sql lead_breakdown_channel
with base as (
    select
        lr.channel,
        count(*) as leads,
        sum(
            case when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1 else 0 end
        ) as appointments
    from ghl._lead_records lr
    join ghl.opportunities o on o.id = lr.opportunity_id
    where lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
    group by 1
),
channel_rows as (
    select
        channel,
        leads,
        round(100.0 * leads / nullif(sum(leads) over (), 0), 2) as share_pct,
        appointments,
        round(100.0 * appointments / nullif(leads, 0), 2) as appointment_rate_pct,
        0 as sort_order
    from base
),
total_row as (
    select
        'Total' as channel,
        sum(leads) as leads,
        100.0 as share_pct,
        sum(appointments) as appointments,
        round(100.0 * sum(appointments) / nullif(sum(leads), 0), 2) as appointment_rate_pct,
        1 as sort_order
    from base
)
select channel, leads, share_pct, appointments, appointment_rate_pct
from (
    select * from channel_rows
    union all
    select * from total_row
) combined
order by sort_order, leads desc, channel
```

<DataTable data={lead_breakdown_channel} search=true title="Leads by channel" subtitle="Lead volume, share, and appointment rate for each marketing channel in the CRM.">
    <Column id="channel" title="Channel" description="Marketing channel attributed to the lead." />
    <Column id="leads" title="Leads" fmt='#,##0' description="Total leads from this channel in the CRM." />
    <Column id="share_pct" title="Share" fmt='0.0"%"' description="Percent of all leads from this channel." />
    <Column id="appointments" title="Appointments" fmt='#,##0' description="Leads moved to the appointment stage in the CRM." />
    <Column id="appointment_rate_pct" title="Appt. %" fmt='0.0"%"' description="Appointments as a percent of leads from this channel." />
</DataTable>

### Mobile vs non-mobile leads

Leads classified from first-touch user agent in GoHighLevel. **Mobile** = iOS, Android, or other mobile browsers. **Non-mobile** = desktop. **Unknown** = no user agent (often manually entered in the CRM).

```sql mobile_lead_breakdown
with labeled as (
    select
        case
            when c.device_type in ('ios', 'android', 'mobile_other') then 'Mobile'
            when c.device_type = 'desktop' then 'Non-mobile'
            else 'Unknown'
        end as device_group,
        case
            when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1
            else 0
        end as is_appointment
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    join ghl.opportunities o on o.id = lr.opportunity_id
    where lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
),
group_rows as (
    select
        device_group,
        count(*) as leads,
        round(100.0 * count(*) / nullif(sum(count(*)) over (), 0), 2) as share_pct,
        sum(is_appointment) as appointments,
        round(100.0 * sum(is_appointment) / nullif(count(*), 0), 2) as appointment_rate_pct,
        0 as sort_order
    from labeled
    group by 1
),
total_row as (
    select
        'Total' as device_group,
        count(*) as leads,
        100.0 as share_pct,
        sum(is_appointment) as appointments,
        round(100.0 * sum(is_appointment) / nullif(count(*), 0), 2) as appointment_rate_pct,
        1 as sort_order
    from labeled
)
select device_group, leads, share_pct, appointments, appointment_rate_pct
from (
    select * from group_rows
    union all
    select * from total_row
) combined
order by sort_order,
    case device_group
        when 'Mobile' then 1
        when 'Non-mobile' then 2
        when 'Unknown' then 3
        else 4
    end
```

<DataTable data={mobile_lead_breakdown} search=true title="Device summary" subtitle="All CRM leads grouped by mobile, non-mobile (desktop), or unknown device type.">
    <Column id="device_group" title="Device" description="Mobile, non-mobile (desktop), or unknown." />
    <Column id="leads" title="Leads" fmt='#,##0' description="Total CRM leads on this device type." />
    <Column id="share_pct" title="Share" fmt='0.0"%"' description="Percent of all leads on this device type." />
    <Column id="appointments" title="Appointments" fmt='#,##0' description="Leads moved to the appointment stage." />
    <Column id="appointment_rate_pct" title="Appt. %" fmt='0.0"%"' description="Appointments as a percent of leads." />
</DataTable>

```sql mobile_leads_by_channel
with labeled as (
    select
        lr.channel,
        case
            when c.device_type in ('ios', 'android', 'mobile_other') then 'Mobile'
            when c.device_type = 'desktop' then 'Non-mobile'
            else 'Unknown'
        end as device_group
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    where lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
)
select
    channel,
    sum(case when device_group = 'Mobile' then 1 else 0 end) as mobile_leads,
    sum(case when device_group = 'Non-mobile' then 1 else 0 end) as non_mobile_leads,
    sum(case when device_group = 'Unknown' then 1 else 0 end) as unknown_leads,
    count(*) as total_leads,
    round(100.0 * sum(case when device_group = 'Mobile' then 1 else 0 end) / nullif(count(*), 0), 2) as mobile_pct
from labeled
group by 1
order by total_leads desc, channel
```

<DataTable data={mobile_leads_by_channel} search=true title="Mobile vs non-mobile by channel" subtitle="How each channel splits between mobile and desktop leads.">
    <Column id="channel" title="Channel" description="Marketing channel attributed to the lead." />
    <Column id="mobile_leads" title="Mobile" fmt='#,##0' description="Leads from mobile devices." />
    <Column id="non_mobile_leads" title="Non-mobile" fmt='#,##0' description="Leads from desktop browsers." />
    <Column id="unknown_leads" title="Unknown" fmt='#,##0' description="Leads without device attribution." />
    <Column id="total_leads" title="Total" fmt='#,##0' />
    <Column id="mobile_pct" title="Mobile %" fmt='0.0"%"' description="Mobile leads as a percent of channel total." />
</DataTable>

### Key trends

```sql daily_leads_by_channel
with classified as (
    select lead_date, channel
    from ghl._lead_records
    where lead_date >= '${inputs.date_range.start}'
      and lead_date <= '${inputs.date_range.end}'
),
daily as (
    select lead_date, channel, count(*) as daily_leads
    from classified
    group by 1, 2
),
channels as (
    select distinct channel from classified
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
        c.channel,
        coalesce(daily.daily_leads, 0) as daily_leads
    from date_span d
    cross join channels c
    left join daily
        on d.lead_date = daily.lead_date
       and c.channel = daily.channel
)
select
    lead_date,
    strftime(lead_date, '%b %d') as lead_date_label,
    channel,
    daily_leads
from filled
where daily_leads > 0
order by lead_date, channel
```

<LineChart
    data={daily_leads_by_channel}
    title="Daily leads by channel"
    x=lead_date_label
    y=daily_leads
    series=channel
    sort=false
/>



```sql mobile_pct_over_time
with daily as (
    select
        lr.lead_date,
        count(*) as total_leads,
        sum(
            case when c.device_type in ('ios', 'android', 'mobile_other') then 1 else 0 end
        ) as mobile_leads
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
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
        coalesce(daily.total_leads, 0) as total_leads,
        coalesce(daily.mobile_leads, 0) as mobile_leads
    from date_span d
    left join daily on d.lead_date = daily.lead_date
)
select
    lead_date,
    strftime(lead_date, '%b %d') as lead_date_label,
    round(100.0 * mobile_leads / nullif(total_leads, 0), 2) as mobile_pct
from filled
where total_leads > 0
order by lead_date
```

<LineChart
    data={mobile_pct_over_time}
    title="Mobile share of leads over time"
    x=lead_date_label
    y=mobile_pct
    sort=false
    yFmt='0.0"%"'
/>

```sql leads_by_day_of_week
select
    case dayofweek(lead_date)
        when 0 then 'Sunday'
        when 1 then 'Monday'
        when 2 then 'Tuesday'
        when 3 then 'Wednesday'
        when 4 then 'Thursday'
        when 5 then 'Friday'
        when 6 then 'Saturday'
    end as day_name,
    dayofweek(lead_date) as day_order,
    count(*) as leads
from ghl._lead_records
where lead_date >= '${inputs.date_range.start}'
  and lead_date <= '${inputs.date_range.end}'
group by 1, 2
order by day_order
```

<BarChart
    data={leads_by_day_of_week}
    title="Leads by day of week"
    x=day_name
    y=leads
/>

```sql channel_mix_weekly
select
    date_trunc('week', lead_date)::date as week_start,
    strftime(date_trunc('week', lead_date)::date, '%b %d') as week_label,
    channel,
    count(*) as leads
from ghl._lead_records
where lead_date >= '${inputs.date_range.start}'
  and lead_date <= '${inputs.date_range.end}'
group by 1, 2, 3
order by week_start, channel
```

<AreaChart
    data={channel_mix_weekly}
    title="Channel mix over time (weekly)"
    x=week_label
    y=leads
    series=channel
    type=stacked
    sort=false
/>

### All appointments

Every lead in the CRM who requested or booked a showing.

```sql all_appointments
select *
from ghl.all_appointments
where lead_date >= '${inputs.date_range.start}'
  and lead_date <= '${inputs.date_range.end}'
```

<DataTable data={all_appointments} search=true rows=25 title="All appointments detail" subtitle="Full contact and opportunity fields for each showing request.">
    <Column id="contact_name" title="Name" description="Contact name from GoHighLevel." />
    <Column id="showing_status" title="Status" description="Showing requested or booked via private showing form." />
    <Column id="lead_date" title="Lead date" description="Date the lead entered the CRM." />
    <Column id="channel" title="Channel" description="Marketing channel attributed to this lead." />
    <Column id="audience" title="Audience" description="Ad audience mapped from UTM term." />
    <Column id="email" title="Email" description="Contact email from GoHighLevel." />
    <Column id="phone" title="Phone" description="Contact phone from GoHighLevel." />
    <Column id="first_name" title="First name" description="Contact first name." />
    <Column id="last_name" title="Last name" description="Contact last name." />
    <Column id="contact_source" title="Contact source" description="Form or source recorded on the contact." />
    <Column id="contact_type" title="Contact type" description="Contact type in GoHighLevel." />
    <Column id="contact_date_added" title="Contact added" description="When the contact was created in GoHighLevel." />
    <Column id="contact_date_updated" title="Contact updated" description="When the contact was last updated." />
    <Column id="tags" title="Tags" description="Tags applied to the contact." />
    <Column id="utm_source" title="UTM source" description="UTM source from first-touch attribution." />
    <Column id="utm_medium" title="UTM medium" description="UTM medium from first-touch attribution." />
    <Column id="utm_campaign" title="UTM campaign" description="UTM campaign from first-touch attribution." />
    <Column id="utm_content" title="UTM content" description="UTM content from first-touch attribution." />
    <Column id="utm_term" title="UTM term" description="UTM term used to map ad audience." />
    <Column id="utm_keyword" title="UTM keyword" description="UTM keyword from first-touch attribution." />
    <Column id="device_type" title="Device" description="Device type from first-touch attribution." />
    <Column id="session_source" title="Session source" description="Session source when no UTM tags are present." />
    <Column id="referrer" title="Referrer" description="Referring URL from first-touch attribution." />
    <Column id="page_url" title="Page URL" description="Landing page URL from first-touch attribution." />
    <Column id="user_agent" title="User agent" description="Browser user agent from first-touch attribution." />
    <Column id="opportunity_name" title="Opportunity" description="Opportunity name in GoHighLevel." />
    <Column id="opportunity_status" title="Opp. status" description="Opportunity status in GoHighLevel." />
    <Column id="opportunity_source" title="Opp. source" description="Source recorded on the opportunity." />
    <Column id="monetary_value" title="Value" fmt='$#,##0.00' description="Monetary value on the opportunity." />
    <Column id="opportunity_created" title="Opp. created" description="When the opportunity was created." />
    <Column id="opportunity_updated" title="Opp. updated" description="When the opportunity was last updated." />
    <Column id="last_status_change" title="Last status change" description="When the opportunity status last changed." />
    <Column id="pipeline_id" title="Pipeline ID" description="GoHighLevel pipeline identifier." />
    <Column id="pipeline_stage_id" title="Stage ID" description="GoHighLevel pipeline stage identifier." />
    <Column id="opp_utm_source" title="Opp. UTM source" description="UTM source stored on the opportunity." />
    <Column id="opp_utm_medium" title="Opp. UTM medium" description="UTM medium stored on the opportunity." />
    <Column id="opp_utm_campaign" title="Opp. UTM campaign" description="UTM campaign stored on the opportunity." />
    <Column id="opp_utm_content" title="Opp. UTM content" description="UTM content stored on the opportunity." />
    <Column id="opp_utm_term" title="Opp. UTM term" description="UTM term stored on the opportunity." />
    <Column id="opp_utm_keyword" title="Opp. UTM keyword" description="UTM keyword stored on the opportunity." />
    <Column id="opportunity_id" title="Opportunity ID" description="GoHighLevel opportunity identifier." />
    <Column id="contact_id" title="Contact ID" description="GoHighLevel contact identifier." />
</DataTable>

---

## Facebook Ads

Paid Meta campaigns attributed in the CRM via `utm_source=facebook` and `utm_medium=cpc`. Read top-to-bottom: spend & efficiency → funnel → creative type → audiences → device → spend trends → lead roster.

### Spend and efficiency

CRM leads are counted only on dates with synced Meta spend so CPL isn't diluted by leads on days without ad data.

```sql spend_totals
with meta as (
    select
        round(sum(spend), 2) as spend,
        sum(impressions) as impressions,
        sum(link_clicks) as link_clicks,
        round(100.0 * sum(link_clicks) / nullif(sum(impressions), 0), 2) as ctr,
        round(sum(spend) / nullif(sum(link_clicks), 0), 2) as cpc,
        round(1000.0 * sum(spend) / nullif(sum(impressions), 0), 2) as cpm,
        min(date_start) as spend_start,
        max(date_start) as spend_end
    from meta_ads.daily_campaign_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
crm as (
    select
        count(*) as facebook_ad_leads,
        sum(
            case when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1 else 0 end
        ) as showing_requests
    from ghl._lead_records lr
    join ghl.opportunities o on o.id = lr.opportunity_id
    cross join meta m
    where lr.channel = 'Facebook Ads'
      and lr.lead_date >= greatest(m.spend_start, cast('${inputs.date_range.start}' as date))
      and lr.lead_date <= least(m.spend_end, cast('${inputs.date_range.end}' as date))
)
select
    m.spend,
    m.impressions,
    m.link_clicks,
    c.facebook_ad_leads as meta_leads,
    c.showing_requests,
    m.ctr,
    m.cpc,
    m.cpm,
    round(m.spend / nullif(c.facebook_ad_leads, 0), 2) as cpl_meta,
    round(m.spend / nullif(c.showing_requests, 0), 2) as cost_per_showing
from meta m
cross join crm c
```

<SpendMetricBlocks data={spend_totals} />

```sql daily_cpl
with daily_spend as (
    select
        date_start as report_date,
        round(sum(spend), 2) as spend
    from meta_ads.daily_campaign_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1
),
spend_bounds as (
    select
        min(report_date) as min_date,
        max(report_date) as max_date
    from daily_spend
),
daily_leads as (
    select
        lr.lead_date as report_date,
        count(*) as leads
    from ghl._lead_records lr
    cross join spend_bounds b
    where lr.channel = 'Facebook Ads'
      and lr.lead_date >= greatest(b.min_date, cast('${inputs.date_range.start}' as date))
      and lr.lead_date <= least(b.max_date, cast('${inputs.date_range.end}' as date))
    group by 1
),
date_span as (
    select unnest(
        generate_series(
            (select min_date from spend_bounds),
            (select max_date from spend_bounds),
            interval 1 day
        )
    )::date as report_date
),
filled as (
    select
        d.report_date,
        coalesce(s.spend, 0) as daily_spend,
        coalesce(l.leads, 0) as daily_leads
    from date_span d
    left join daily_spend s on d.report_date = s.report_date
    left join daily_leads l on d.report_date = l.report_date
)
select
    report_date,
    strftime(report_date, '%b %d') as report_date_label,
    sum(daily_spend) over (
        order by report_date
        rows between unbounded preceding and current row
    ) as cumulative_spend,
    sum(daily_leads) over (
        order by report_date
        rows between unbounded preceding and current row
    ) as cumulative_leads,
    round(
        sum(daily_spend) over (
            order by report_date
            rows between unbounded preceding and current row
        ) / nullif(
            sum(daily_leads) over (
                order by report_date
                rows between unbounded preceding and current row
            ),
            0
        ),
        2
    ) as cpl
from filled
order by report_date
```

<LineChart
    data={daily_cpl}
    title="CPL over time"
    subtitle="Cumulative ad spend divided by cumulative Facebook ad leads in the CRM."
    x=report_date_label
    y=cpl
    sort=false
    yFmt=usd
/>

```sql facebook_funnel_chart
with spend_bounds as (
    select
        min(date_start) as spend_start,
        max(date_start) as spend_end
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
meta as (
    select
        sum(impressions) as impressions,
        sum(link_clicks) as page_visits
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
crm as (
    select
        count(*) as facebook_leads,
        sum(
            case when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1 else 0 end
        ) as showings
    from ghl._lead_records lr
    join ghl.opportunities o on o.id = lr.opportunity_id
    cross join spend_bounds b
    where lr.channel = 'Facebook Ads'
      and lr.lead_date >= greatest(b.spend_start, cast('${inputs.date_range.start}' as date))
      and lr.lead_date <= least(b.spend_end, cast('${inputs.date_range.end}' as date))
)
select stage_name, stage_order, value
from (
    select 'Impressions' as stage_name, 1 as stage_order, m.impressions as value from meta m
    union all
    select 'Page visits', 2, m.page_visits from meta m
    union all
    select 'CRM leads', 3, c.facebook_leads from crm c
    union all
    select 'Showings', 4, c.showings from crm c
) stages
order by stage_order
```

<FunnelChart
    data={facebook_funnel_chart}
    title="Facebook funnel"
    nameCol=stage_name
    valueCol=value
/>

### Static vs dynamic creative

Compares **Static** (Geo Targeting - Non-Dynamic Creative) against **Dynamic** (Geo Targeting - Dynamic Creative and Multi-Geo Targeting - Dynamic Creative). Meta metrics come from campaign names; CRM leads are classified from `utm_campaign`.

```sql creative_type_comparison
with spend_bounds as (
    select
        min(date_start) as spend_start,
        max(date_start) as spend_end
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
meta as (
    select
        case
            when lower(campaign_name) like '%non%dynamic%' then 'Static'
            when lower(campaign_name) like '%dynamic creative%' then 'Dynamic'
            else 'Other'
        end as creative_type,
        sum(spend) as spend,
        sum(impressions) as impressions,
        sum(link_clicks) as link_clicks
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1
),
crm as (
    select
        case
            when lower(c.utm_campaign) like '%non%dynamic%' then 'Static'
            when lower(c.utm_campaign) like '%dynamic creative%' then 'Dynamic'
            else 'Other'
        end as creative_type,
        count(*) as facebook_leads,
        sum(
            case when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1 else 0 end
        ) as showings
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    join ghl.opportunities o on o.id = lr.opportunity_id
    cross join spend_bounds b
    where lr.channel = 'Facebook Ads'
      and lr.lead_date >= greatest(b.spend_start, cast('${inputs.date_range.start}' as date))
      and lr.lead_date <= least(b.spend_end, cast('${inputs.date_range.end}' as date))
    group by 1
),
joined as (
    select
        t.creative_type,
        round(coalesce(m.spend, 0), 2) as spend,
        round(100.0 * coalesce(m.spend, 0) / nullif(sum(coalesce(m.spend, 0)) over (), 0), 2) as spend_share_pct,
        coalesce(m.impressions, 0) as impressions,
        coalesce(m.link_clicks, 0) as page_visits,
        round(100.0 * coalesce(m.link_clicks, 0) / nullif(coalesce(m.impressions, 0), 0), 2) as link_ctr,
        round(coalesce(m.spend, 0) / nullif(coalesce(m.link_clicks, 0), 0), 2) as cpc,
        coalesce(c.facebook_leads, 0) as facebook_leads,
        round(100.0 * coalesce(c.facebook_leads, 0) / nullif(sum(coalesce(c.facebook_leads, 0)) over (), 0), 2) as lead_share_pct,
        coalesce(c.showings, 0) as showings,
        round(coalesce(m.spend, 0) / nullif(coalesce(c.facebook_leads, 0), 0), 2) as cpl,
        round(100.0 * coalesce(c.showings, 0) / nullif(coalesce(c.facebook_leads, 0), 0), 2) as showing_rate_pct
    from (values ('Static'), ('Dynamic'), ('Other')) as t(creative_type)
    left join meta m on m.creative_type = t.creative_type
    left join crm c on c.creative_type = t.creative_type
    where t.creative_type in ('Static', 'Dynamic')
       or coalesce(m.spend, 0) > 0
       or coalesce(c.facebook_leads, 0) > 0
),
type_rows as (
    select *, 0 as sort_order from joined
),
total_row as (
    select
        'Total' as creative_type,
        round(sum(spend), 2) as spend,
        100.0 as spend_share_pct,
        sum(impressions) as impressions,
        sum(page_visits) as page_visits,
        round(100.0 * sum(page_visits) / nullif(sum(impressions), 0), 2) as link_ctr,
        round(sum(spend) / nullif(sum(page_visits), 0), 2) as cpc,
        sum(facebook_leads) as facebook_leads,
        100.0 as lead_share_pct,
        sum(showings) as showings,
        round(sum(spend) / nullif(sum(facebook_leads), 0), 2) as cpl,
        round(100.0 * sum(showings) / nullif(sum(facebook_leads), 0), 2) as showing_rate_pct,
        1 as sort_order
    from joined
)
select
    creative_type,
    spend,
    spend_share_pct,
    impressions,
    page_visits,
    link_ctr,
    cpc,
    facebook_leads,
    lead_share_pct,
    showings,
    cpl,
    showing_rate_pct
from (
    select * from type_rows
    union all
    select * from total_row
) combined
order by sort_order, spend desc, creative_type
```

<DataTable data={creative_type_comparison} search=true title="Static vs dynamic comparison" subtitle="Meta delivery and CRM outcomes for static and dynamic creative campaigns.">
    <Column id="creative_type" title="Creative type" description="Static = fixed creative assets. Dynamic = Meta dynamic creative optimization." />
    <Column id="spend" title="Spend" fmt='$#,##0.00' description="Ad spend from Meta." />
    <Column id="spend_share_pct" title="Spend %" fmt='0.0"%"' description="Share of total Facebook ad spend." />
    <Column id="impressions" title="Impressions" fmt='#,##0' description="Times ads appeared on screen (Meta)." />
    <Column id="page_visits" title="Page visits" fmt='#,##0' description="Landing page link clicks (Meta)." />
    <Column id="link_ctr" title="Link CTR" fmt='0.0"%"' description="Link clicks divided by impressions." />
    <Column id="cpc" title="CPC" fmt='$#,##0.00' description="Cost per link click." />
    <Column id="facebook_leads" title="CRM leads" fmt='#,##0' description="Facebook ad leads in the CRM." />
    <Column id="lead_share_pct" title="Lead %" fmt='0.0"%"' description="Share of Facebook ad leads in the CRM." />
    <Column id="showings" title="Showings" fmt='#,##0' description="Leads moved to appointment stage." />
    <Column id="cpl" title="CPL" fmt='$#,##0.00' description="Spend divided by CRM leads." />
    <Column id="showing_rate_pct" title="Showing %" fmt='0.0"%"' description="Showings as a percent of CRM leads." />
</DataTable>

<Grid cols=2>
    <BarChart
        data={creative_type_comparison}
        title="Spend by creative type"
        x=creative_type
        y=spend
        where="creative_type != 'Total'"
        yFmt=usd
    />
    <BarChart
        data={creative_type_comparison}
        title="CRM leads by creative type"
        x=creative_type
        y=facebook_leads
        where="creative_type != 'Total'"
    />
</Grid>

```sql creative_type_daily_spend
with daily as (
    select
        date_start as report_date,
        case
            when lower(campaign_name) like '%non%dynamic%' then 'Static'
            when lower(campaign_name) like '%dynamic creative%' then 'Dynamic'
            else 'Other'
        end as creative_type,
        round(sum(spend), 2) as spend
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1, 2
),
date_span as (
    select unnest(
        generate_series(
            cast('${inputs.date_range.start}' as date),
            cast('${inputs.date_range.end}' as date),
            interval 1 day
        )
    )::date as report_date
),
types as (
    select 'Static' as creative_type
    union all
    select 'Dynamic'
)
select
    d.report_date,
    strftime(d.report_date, '%b %d') as report_date_label,
    t.creative_type,
    coalesce(daily.spend, 0) as spend
from date_span d
cross join types t
left join daily
    on d.report_date = daily.report_date
   and t.creative_type = daily.creative_type
order by d.report_date, t.creative_type
```

<LineChart
    data={creative_type_daily_spend}
    title="Daily spend by creative type"
    x=report_date_label
    y=spend
    series=creative_type
    sort=false
    yFmt=usd
/>

```sql creative_type_by_audience
with spend_bounds as (
    select
        min(date_start) as spend_start,
        max(date_start) as spend_end
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
meta as (
    select
        adset_name as audience,
        case
            when lower(campaign_name) like '%non%dynamic%' then 'Static'
            when lower(campaign_name) like '%dynamic creative%' then 'Dynamic'
            else 'Other'
        end as creative_type,
        sum(spend) as spend,
        sum(link_clicks) as link_clicks
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1, 2
),
crm as (
    select
        case c.utm_term
            when '120250101870600306' then 'VT & NH'
            when '120250101883590306' then 'VT & NH'
            when '120250093236920306' then 'NYC 15 Miles'
            when '120250091197620306' then 'NYC 15 Miles'
            when '120250093748420306' then 'Westchester / Hudson Valley'
            when '120250091788420306' then 'Westchester / Hudson Valley'
            when '120250091674470306' then 'Long Island Gold Coast/Hamptons'
            when '120250093766560306' then 'Long Island Gold Coast/Hamptons'
            when '120250093727620306' then 'NJ Shore'
            when '120250091847730306' then 'NJ Shore'
            when '120250091623250306' then 'Connecticut Gold Coast'
            when '120250093630920306' then 'Connecticut Gold Coast'
            else 'Unattributed'
        end as audience,
        case
            when lower(c.utm_campaign) like '%non%dynamic%' then 'Static'
            when lower(c.utm_campaign) like '%dynamic creative%' then 'Dynamic'
            else 'Other'
        end as creative_type,
        count(*) as facebook_leads
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    cross join spend_bounds b
    where lr.channel = 'Facebook Ads'
      and lr.lead_date >= greatest(b.spend_start, cast('${inputs.date_range.start}' as date))
      and lr.lead_date <= least(b.spend_end, cast('${inputs.date_range.end}' as date))
    group by 1, 2
),
joined as (
    select
        m.audience,
        m.creative_type,
        round(m.spend, 2) as spend,
        m.link_clicks as page_visits,
        coalesce(c.facebook_leads, 0) as facebook_leads,
        round(m.spend / nullif(coalesce(c.facebook_leads, 0), 0), 2) as cpl
    from meta m
    left join crm c
        on c.audience = m.audience
       and c.creative_type = m.creative_type
    where m.creative_type in ('Static', 'Dynamic')
    and (coalesce(c.facebook_leads, 0) > 0 or m.spend >= 50)
)
select audience, creative_type, spend, page_visits, facebook_leads, cpl
from joined
order by creative_type, spend desc, audience
```

<DataTable data={creative_type_by_audience} search=true title="Performance by audience and creative type" subtitle="Audiences with meaningful spend or CRM leads. National campaign geos without UTM-matched leads are hidden.">
    <Column id="audience" title="Audience" description="Geographic ad audience from Meta." />
    <Column id="creative_type" title="Creative type" description="Static or dynamic creative campaign." />
    <Column id="spend" title="Spend" fmt='$#,##0.00' />
    <Column id="page_visits" title="Page visits" fmt='#,##0' />
    <Column id="facebook_leads" title="CRM leads" fmt='#,##0' />
    <Column id="cpl" title="CPL" fmt='$#,##0.00' />
</DataTable>

### Audience breakdown

Spend, delivery metrics, and CRM outcomes for each geographic ad audience.

```sql adset_efficiency
with spend_bounds as (
    select
        min(date_start) as spend_start,
        max(date_start) as spend_end
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
by_adset as (
    select
        adset_name,
        sum(spend) as spend,
        sum(impressions) as impressions,
        sum(link_clicks) as link_clicks
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1
),
crm_leads as (
    select
        case c.utm_term
            when '120250101870600306' then 'VT & NH'
            when '120250101883590306' then 'VT & NH'
            when '120250093236920306' then 'NYC 15 Miles'
            when '120250091197620306' then 'NYC 15 Miles'
            when '120250093748420306' then 'Westchester / Hudson Valley'
            when '120250091788420306' then 'Westchester / Hudson Valley'
            when '120250091674470306' then 'Long Island Gold Coast/Hamptons'
            when '120250093766560306' then 'Long Island Gold Coast/Hamptons'
            when '120250093727620306' then 'NJ Shore'
            when '120250091847730306' then 'NJ Shore'
            when '120250091623250306' then 'Connecticut Gold Coast'
            when '120250093630920306' then 'Connecticut Gold Coast'
            else 'Unattributed'
        end as audience,
        count(*) as facebook_leads
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    cross join spend_bounds b
    where lr.channel = 'Facebook Ads'
      and lr.lead_date >= greatest(b.spend_start, cast('${inputs.date_range.start}' as date))
      and lr.lead_date <= least(b.spend_end, cast('${inputs.date_range.end}' as date))
    group by 1
),
crm_showings as (
    select
        case c.utm_term
            when '120250101870600306' then 'VT & NH'
            when '120250101883590306' then 'VT & NH'
            when '120250093236920306' then 'NYC 15 Miles'
            when '120250091197620306' then 'NYC 15 Miles'
            when '120250093748420306' then 'Westchester / Hudson Valley'
            when '120250091788420306' then 'Westchester / Hudson Valley'
            when '120250091674470306' then 'Long Island Gold Coast/Hamptons'
            when '120250093766560306' then 'Long Island Gold Coast/Hamptons'
            when '120250093727620306' then 'NJ Shore'
            when '120250091847730306' then 'NJ Shore'
            when '120250091623250306' then 'Connecticut Gold Coast'
            when '120250093630920306' then 'Connecticut Gold Coast'
            else 'Unattributed'
        end as audience,
        count(*) as showing_requests
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    join ghl.opportunities o on o.id = lr.opportunity_id
    cross join spend_bounds b
    where lr.channel = 'Facebook Ads'
      and o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c'
      and lr.lead_date >= greatest(b.spend_start, cast('${inputs.date_range.start}' as date))
      and lr.lead_date <= least(b.spend_end, cast('${inputs.date_range.end}' as date))
    group by 1
),
joined as (
    select
        a.adset_name,
        a.spend,
        a.impressions,
        a.link_clicks,
        coalesce(l.facebook_leads, 0) as facebook_leads,
        coalesce(s.showing_requests, 0) as showing_requests
    from by_adset a
    left join crm_leads l on l.audience = a.adset_name
    left join crm_showings s on s.audience = a.adset_name
),
audience_rows as (
    select
        adset_name,
        round(spend, 2) as spend,
        round(100.0 * spend / nullif(sum(spend) over (), 0), 2) as spend_share_pct,
        impressions,
        link_clicks as page_visits,
        round(100.0 * link_clicks / nullif(impressions, 0), 2) as ctr,
        round(spend / nullif(link_clicks, 0), 2) as cpc,
        round(1000.0 * spend / nullif(impressions, 0), 2) as cpm,
        facebook_leads,
        round(spend / nullif(facebook_leads, 0), 2) as cpl,
        showing_requests,
        round(spend / nullif(showing_requests, 0), 2) as cost_per_showing,
        0 as sort_order
    from joined
),
total_row as (
    select
        'Total' as adset_name,
        round(sum(spend), 2) as spend,
        100.0 as spend_share_pct,
        sum(impressions) as impressions,
        sum(link_clicks) as page_visits,
        round(100.0 * sum(link_clicks) / nullif(sum(impressions), 0), 2) as ctr,
        round(sum(spend) / nullif(sum(link_clicks), 0), 2) as cpc,
        round(1000.0 * sum(spend) / nullif(sum(impressions), 0), 2) as cpm,
        sum(facebook_leads) as facebook_leads,
        round(sum(spend) / nullif(sum(facebook_leads), 0), 2) as cpl,
        sum(showing_requests) as showing_requests,
        round(sum(spend) / nullif(sum(showing_requests), 0), 2) as cost_per_showing,
        1 as sort_order
    from joined
)
select
    adset_name,
    spend,
    spend_share_pct,
    impressions,
    page_visits,
    ctr,
    cpc,
    cpm,
    facebook_leads,
    cpl,
    showing_requests,
    cost_per_showing
from (
    select * from audience_rows
    union all
    select * from total_row
) combined
order by sort_order, spend desc
```

<DataTable data={adset_efficiency} search=true rows=20 title="Audience efficiency" subtitle="Spend, delivery, and CRM outcomes for each geographic ad audience.">
    <Column id="adset_name" title="Audience" description="Geographic ad audience from Meta." />
    <Column id="spend" title="Spend" fmt='$#,##0.00' description="Total ad spend from Meta in the selected period." />
    <Column id="spend_share_pct" title="Spend %" fmt='0.0"%"' description="This audience's share of total spend." />
    <Column id="impressions" title="Impressions" fmt='#,##0' description="Times ads appeared on screen (Meta)." />
    <Column id="page_visits" title="Page visits" fmt='#,##0' description="Clicks to the landing page (Meta link clicks)." />
    <Column id="ctr" title="Link CTR" fmt='0.0"%"' description="Link clicks divided by impressions (not Meta all-clicks CTR) (Meta)." />
    <Column id="cpc" title="CPC" fmt='$#,##0.00' description="Cost per click: spend divided by page visits (Meta)." />
    <Column id="cpm" title="CPM" fmt='$#,##0.00' description="Cost per 1,000 impressions (Meta)." />
    <Column id="facebook_leads" title="Leads" fmt='#,##0' description="Facebook ad leads recorded in the CRM." />
    <Column id="cpl" title="CPL" fmt='$#,##0.00' description="Cost per lead: spend divided by CRM leads." />
    <Column id="showing_requests" title="Showings" fmt='#,##0' description="Leads moved to showing-requested stage in the CRM." />
    <Column id="cost_per_showing" title="Cost per showing" fmt='$#,##0.00' description="Spend divided by showings requested in the CRM." />
</DataTable>

### Audience funnel

Conversion rates from impressions through showings for each audience.

```sql adset_funnel
with spend_bounds as (
    select
        min(date_start) as spend_start,
        max(date_start) as spend_end
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
by_audience as (
    select
        adset_name as audience,
        sum(impressions) as impressions,
        sum(link_clicks) as landing_page_clicks
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1
),
crm_leads as (
    select
        case c.utm_term
            when '120250101870600306' then 'VT & NH'
            when '120250101883590306' then 'VT & NH'
            when '120250093236920306' then 'NYC 15 Miles'
            when '120250091197620306' then 'NYC 15 Miles'
            when '120250093748420306' then 'Westchester / Hudson Valley'
            when '120250091788420306' then 'Westchester / Hudson Valley'
            when '120250091674470306' then 'Long Island Gold Coast/Hamptons'
            when '120250093766560306' then 'Long Island Gold Coast/Hamptons'
            when '120250093727620306' then 'NJ Shore'
            when '120250091847730306' then 'NJ Shore'
            when '120250091623250306' then 'Connecticut Gold Coast'
            when '120250093630920306' then 'Connecticut Gold Coast'
            else 'Unattributed'
        end as audience,
        count(*) as facebook_leads
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    cross join spend_bounds b
    where lr.channel = 'Facebook Ads'
      and lr.lead_date >= greatest(b.spend_start, cast('${inputs.date_range.start}' as date))
      and lr.lead_date <= least(b.spend_end, cast('${inputs.date_range.end}' as date))
    group by 1
),
crm_showings as (
    select
        case c.utm_term
            when '120250101870600306' then 'VT & NH'
            when '120250101883590306' then 'VT & NH'
            when '120250093236920306' then 'NYC 15 Miles'
            when '120250091197620306' then 'NYC 15 Miles'
            when '120250093748420306' then 'Westchester / Hudson Valley'
            when '120250091788420306' then 'Westchester / Hudson Valley'
            when '120250091674470306' then 'Long Island Gold Coast/Hamptons'
            when '120250093766560306' then 'Long Island Gold Coast/Hamptons'
            when '120250093727620306' then 'NJ Shore'
            when '120250091847730306' then 'NJ Shore'
            when '120250091623250306' then 'Connecticut Gold Coast'
            when '120250093630920306' then 'Connecticut Gold Coast'
            else 'Unattributed'
        end as audience,
        count(*) as showing_requests
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    join ghl.opportunities o on o.id = lr.opportunity_id
    cross join spend_bounds b
    where lr.channel = 'Facebook Ads'
      and o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c'
      and lr.lead_date >= greatest(b.spend_start, cast('${inputs.date_range.start}' as date))
      and lr.lead_date <= least(b.spend_end, cast('${inputs.date_range.end}' as date))
    group by 1
),
joined as (
    select
        a.audience,
        a.impressions,
        a.landing_page_clicks,
        coalesce(l.facebook_leads, 0) as facebook_leads,
        coalesce(s.showing_requests, 0) as showing_requests
    from by_audience a
    left join crm_leads l on l.audience = a.audience
    left join crm_showings s on s.audience = a.audience
),
audience_rows as (
    select
        audience,
        impressions,
        landing_page_clicks,
        facebook_leads,
        showing_requests,
        round(100.0 * impressions / nullif(sum(impressions) over (), 0), 2) as impressions_share_pct,
        round(100.0 * landing_page_clicks / nullif(impressions, 0), 2) as landing_page_clicks_pct,
        round(100.0 * facebook_leads / nullif(landing_page_clicks, 0), 2) as facebook_leads_pct,
        round(100.0 * showing_requests / nullif(facebook_leads, 0), 2) as showing_requests_pct,
        0 as sort_order
    from joined
),
total_row as (
    select
        'Total' as audience,
        sum(impressions) as impressions,
        sum(landing_page_clicks) as landing_page_clicks,
        sum(facebook_leads) as facebook_leads,
        sum(showing_requests) as showing_requests,
        100.0 as impressions_share_pct,
        round(100.0 * sum(landing_page_clicks) / nullif(sum(impressions), 0), 2) as landing_page_clicks_pct,
        round(100.0 * sum(facebook_leads) / nullif(sum(landing_page_clicks), 0), 2) as facebook_leads_pct,
        round(100.0 * sum(showing_requests) / nullif(sum(facebook_leads), 0), 2) as showing_requests_pct,
        1 as sort_order
    from joined
)
select
    audience,
    impressions,
    impressions_share_pct,
    landing_page_clicks,
    landing_page_clicks_pct,
    facebook_leads,
    facebook_leads_pct,
    showing_requests,
    showing_requests_pct
from (
    select * from audience_rows
    union all
    select * from total_row
) combined
order by sort_order, audience
```

<DataTable data={adset_funnel} search=true title="Audience funnel" subtitle="Impressions through showings for each audience — where prospects drop off.">
    <Column id="audience" title="Audience" description="Geographic ad audience from Meta." />
    <Column id="impressions" title="Impressions" fmt='#,##0' description="Times ads appeared on screen (Meta)." />
    <Column id="impressions_share_pct" title="Impr. %" fmt='0.0"%"' description="Share of total impressions for this audience." />
    <Column id="landing_page_clicks" title="Page Visits" fmt='#,##0' description="Clicks to the landing page (Meta link clicks)." />
    <Column id="landing_page_clicks_pct" title="Visit %" fmt='0.0"%"' description="Page visits as a percent of impressions." />
    <Column id="facebook_leads" title="Leads (CRM)" fmt='#,##0' description="Facebook ad leads recorded in the CRM." />
    <Column id="facebook_leads_pct" title="Lead %" fmt='0.0"%"' description="CRM leads as a percent of page visits." />
    <Column id="showing_requests" title="Showings" fmt='#,##0' description="Leads moved to showing-requested stage in the CRM." />
    <Column id="showing_requests_pct" title="Showing %" fmt='0.0"%"' description="Showings as a percent of CRM leads." />
</DataTable>

### Device breakdown

How mobile and desktop perform across Meta delivery and CRM leads. Meta device comes from impression delivery; CRM device comes from landing-page user agent — they measure different things.

```sql device_breakdown
with spend_bounds as (
    select
        min(date_start) as spend_start,
        max(date_start) as spend_end
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
meta_by_device as (
    select
        case lower(impression_device)
            when 'desktop' then 'Desktop'
            when 'mobile' then 'Mobile'
            when 'mobile_app' then 'Mobile'
            when 'mobile_web' then 'Mobile'
            else 'Unknown'
        end as device,
        sum(impressions) as impressions,
        sum(link_clicks) as page_visits
    from meta_ads.daily_adset_insights_by_device
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1
),
crm_leads_by_device as (
    select
        case c.device_type
            when 'desktop' then 'Desktop'
            when 'ios' then 'Mobile'
            when 'android' then 'Mobile'
            when 'mobile_other' then 'Mobile'
            else 'Unknown'
        end as device,
        count(*) as facebook_leads
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    cross join spend_bounds b
    where lr.channel = 'Facebook Ads'
      and lr.lead_date >= greatest(b.spend_start, cast('${inputs.date_range.start}' as date))
      and lr.lead_date <= least(b.spend_end, cast('${inputs.date_range.end}' as date))
    group by 1
),
crm_showings_by_device as (
    select
        case c.device_type
            when 'desktop' then 'Desktop'
            when 'ios' then 'Mobile'
            when 'android' then 'Mobile'
            when 'mobile_other' then 'Mobile'
            else 'Unknown'
        end as device,
        count(*) as showings
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    join ghl.opportunities o on o.id = lr.opportunity_id
    cross join spend_bounds b
    where lr.channel = 'Facebook Ads'
      and o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c'
      and lr.lead_date >= greatest(b.spend_start, cast('${inputs.date_range.start}' as date))
      and lr.lead_date <= least(b.spend_end, cast('${inputs.date_range.end}' as date))
    group by 1
),
all_leads_by_device as (
    select
        case c.device_type
            when 'desktop' then 'Desktop'
            when 'ios' then 'Mobile'
            when 'android' then 'Mobile'
            when 'mobile_other' then 'Mobile'
            else 'Unknown'
        end as device,
        count(*) as total_leads
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    where lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
    group by 1
),
joined as (
    select
        d.device,
        coalesce(m.impressions, 0) as impressions,
        coalesce(m.page_visits, 0) as page_visits,
        coalesce(al.total_leads, 0) as total_leads,
        coalesce(l.facebook_leads, 0) as facebook_leads,
        coalesce(s.showings, 0) as showings
    from (values ('Desktop'), ('Mobile'), ('Unknown')) as d(device)
    left join meta_by_device m on m.device = d.device
    left join all_leads_by_device al on al.device = d.device
    left join crm_leads_by_device l on l.device = d.device
    left join crm_showings_by_device s on s.device = d.device
),
device_rows as (
    select
        device,
        impressions,
        round(100.0 * impressions / nullif(sum(impressions) over (), 0), 2) as impressions_share_pct,
        page_visits,
        round(100.0 * page_visits / nullif(impressions, 0), 2) as visit_rate_pct,
        total_leads,
        facebook_leads,
        round(100.0 * facebook_leads / nullif(page_visits, 0), 2) as lead_rate_pct,
        showings,
        round(100.0 * showings / nullif(facebook_leads, 0), 2) as showing_rate_pct,
        0 as sort_order
    from joined
),
total_row as (
    select
        'Total' as device,
        sum(impressions) as impressions,
        100.0 as impressions_share_pct,
        sum(page_visits) as page_visits,
        round(100.0 * sum(page_visits) / nullif(sum(impressions), 0), 2) as visit_rate_pct,
        sum(total_leads) as total_leads,
        sum(facebook_leads) as facebook_leads,
        round(100.0 * sum(facebook_leads) / nullif(sum(page_visits), 0), 2) as lead_rate_pct,
        sum(showings) as showings,
        round(100.0 * sum(showings) / nullif(sum(facebook_leads), 0), 2) as showing_rate_pct,
        1 as sort_order
    from joined
)
select
    device,
    impressions,
    impressions_share_pct,
    page_visits,
    visit_rate_pct,
    total_leads,
    facebook_leads,
    lead_rate_pct,
    showings,
    showing_rate_pct
from (
    select * from device_rows
    union all
    select * from total_row
) combined
order by sort_order, device
```

<DataTable data={device_breakdown} search=true title="Device breakdown" subtitle="Meta delivery and CRM leads by device type.">
    <Column id="device" title="Device" description="Desktop, Mobile, or Unknown. Meta uses impression device; CRM uses first-touch user agent." />
    <Column id="impressions" title="Impressions" fmt='#,##0' description="Ad impressions by device (Meta)." />
    <Column id="impressions_share_pct" title="Impr. %" fmt='0.0"%"' description="Share of total impressions on this device." />
    <Column id="page_visits" title="Page Visits" fmt='#,##0' description="Landing page link clicks by device (Meta)." />
    <Column id="visit_rate_pct" title="Visit %" fmt='0.0"%"' description="Page visits as a percent of impressions." />
    <Column id="total_leads" title="All Leads" fmt='#,##0' description="CRM leads from any channel on this device." />
    <Column id="facebook_leads" title="FB Leads" fmt='#,##0' description="Facebook ad leads in the CRM on this device." />
    <Column id="lead_rate_pct" title="Lead %" fmt='0.0"%"' description="Facebook leads as a percent of page visits." />
    <Column id="showings" title="Showings" fmt='#,##0' description="Showing requests in the CRM on this device." />
    <Column id="showing_rate_pct" title="Showing %" fmt='0.0"%"' description="Showings as a percent of Facebook leads." />
</DataTable>

<BarChart
    data={device_breakdown}
    title="Facebook leads by device"
    x=device
    y=facebook_leads
    where="device != 'Total'"
    swapXY=true
/>

### Daily spend

Ad spend over time — total, by campaign group, and by audience.

```sql daily_spend_total
with daily as (
    select
        date_start as report_date,
        round(sum(spend), 2) as spend
    from meta_ads.daily_campaign_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1
),
date_span as (
    select unnest(
        generate_series(
            cast('${inputs.date_range.start}' as date),
            cast('${inputs.date_range.end}' as date),
            interval 1 day
        )
    )::date as report_date
)
select
    d.report_date,
    strftime(d.report_date, '%b %d') as report_date_label,
    coalesce(daily.spend, 0) as spend
from date_span d
left join daily on d.report_date = daily.report_date
order by d.report_date
```

<LineChart
    data={daily_spend_total}
    title="Daily spend"
    x=report_date_label
    y=spend
    sort=false
    yFmt=usd
/>

```sql daily_spend_by_group
with daily as (
    select
        date_start as report_date,
        case
            when campaign_name in (
                'Geo Targeting - Dynamic Creative',
                'Geo Targeting - Non-Dynamic Creative'
            ) then 'Northeast'
            when campaign_name = 'Multi-Geo Targeting - Dynamic Creative' then 'National'
            else campaign_name
        end as campaign_group,
        round(sum(spend), 2) as spend
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1, 2
),
date_span as (
    select unnest(
        generate_series(
            cast('${inputs.date_range.start}' as date),
            cast('${inputs.date_range.end}' as date),
            interval 1 day
        )
    )::date as report_date
),
groups as (
    select 'Northeast' as campaign_group
    union all
    select 'National'
)
select
    d.report_date,
    strftime(d.report_date, '%b %d') as report_date_label,
    g.campaign_group,
    coalesce(daily.spend, 0) as spend
from date_span d
cross join groups g
left join daily
    on d.report_date = daily.report_date
   and g.campaign_group = daily.campaign_group
order by d.report_date, g.campaign_group
```

<LineChart
    data={daily_spend_by_group}
    title="Daily spend by campaign group"
    x=report_date_label
    y=spend
    series=campaign_group
    sort=false
    yFmt=usd
/>

```sql daily_spend
select
    date_start,
    adset_name as audience,
    round(sum(spend), 2) as spend
from meta_ads.daily_adset_insights
where date_start >= '${inputs.date_range.start}'
  and date_start <= '${inputs.date_range.end}'
group by 1, 2
order by date_start, audience
```

<LineChart
    data={daily_spend}
    title="Daily spend by audience"
    x=date_start
    y=spend
    series=audience
    yFmt=usd
/>


### Trends & diagnostics

Additional CPL, delivery, and device mix charts.

```sql cpl_by_audience_weekly
with spend_bounds as (
    select
        min(date_start) as spend_start,
        max(date_start) as spend_end
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
weekly_meta as (
    select
        date_trunc('week', date_start)::date as week_start,
        adset_name as audience,
        sum(spend) as spend
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1, 2
),
weekly_crm as (
    select
        date_trunc('week', lr.lead_date)::date as week_start,
        case c.utm_term
            when '120250101870600306' then 'VT & NH'
            when '120250101883590306' then 'VT & NH'
            when '120250093236920306' then 'NYC 15 Miles'
            when '120250091197620306' then 'NYC 15 Miles'
            when '120250093748420306' then 'Westchester / Hudson Valley'
            when '120250091788420306' then 'Westchester / Hudson Valley'
            when '120250091674470306' then 'Long Island Gold Coast/Hamptons'
            when '120250093766560306' then 'Long Island Gold Coast/Hamptons'
            when '120250093727620306' then 'NJ Shore'
            when '120250091847730306' then 'NJ Shore'
            when '120250091623250306' then 'Connecticut Gold Coast'
            when '120250093630920306' then 'Connecticut Gold Coast'
            else 'Unattributed'
        end as audience,
        count(*) as facebook_leads
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    cross join spend_bounds b
    where lr.channel = 'Facebook Ads'
      and lr.lead_date >= greatest(b.spend_start, cast('${inputs.date_range.start}' as date))
      and lr.lead_date <= least(b.spend_end, cast('${inputs.date_range.end}' as date))
    group by 1, 2
),
joined as (
    select
        coalesce(m.week_start, c.week_start) as week_start,
        coalesce(m.audience, c.audience) as audience,
        coalesce(m.spend, 0) as spend,
        coalesce(c.facebook_leads, 0) as facebook_leads
    from weekly_meta m
    full outer join weekly_crm c
        on m.week_start = c.week_start
       and m.audience = c.audience
)
select
    week_start,
    strftime(week_start, '%b %d') as week_label,
    audience,
    round(spend / nullif(facebook_leads, 0), 2) as cpl
from joined
where audience != 'Unattributed'
  and (spend > 0 or facebook_leads > 0)
order by week_start, audience
```

<LineChart
    data={cpl_by_audience_weekly}
    title="CPL by audience (weekly)"
    x=week_label
    y=cpl
    series=audience
    sort=false
    yFmt=usd
/>

```sql creative_type_cpl_weekly
with spend_bounds as (
    select
        min(date_start) as spend_start,
        max(date_start) as spend_end
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
weekly_meta as (
    select
        date_trunc('week', date_start)::date as week_start,
        case
            when lower(campaign_name) like '%non%dynamic%' then 'Static'
            when lower(campaign_name) like '%dynamic creative%' then 'Dynamic'
            else 'Other'
        end as creative_type,
        sum(spend) as spend
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1, 2
),
weekly_crm as (
    select
        date_trunc('week', lr.lead_date)::date as week_start,
        case
            when lower(c.utm_campaign) like '%non%dynamic%' then 'Static'
            when lower(c.utm_campaign) like '%dynamic creative%' then 'Dynamic'
            else 'Other'
        end as creative_type,
        count(*) as facebook_leads
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    cross join spend_bounds b
    where lr.channel = 'Facebook Ads'
      and lr.lead_date >= greatest(b.spend_start, cast('${inputs.date_range.start}' as date))
      and lr.lead_date <= least(b.spend_end, cast('${inputs.date_range.end}' as date))
    group by 1, 2
),
joined as (
    select
        coalesce(m.week_start, c.week_start) as week_start,
        coalesce(m.creative_type, c.creative_type) as creative_type,
        coalesce(m.spend, 0) as spend,
        coalesce(c.facebook_leads, 0) as facebook_leads
    from weekly_meta m
    full outer join weekly_crm c
        on m.week_start = c.week_start
       and m.creative_type = c.creative_type
)
select
    week_start,
    strftime(week_start, '%b %d') as week_label,
    creative_type,
    round(spend / nullif(facebook_leads, 0), 2) as cpl
from joined
where creative_type in ('Static', 'Dynamic')
  and (spend > 0 or facebook_leads > 0)
order by week_start, creative_type
```

<LineChart
    data={creative_type_cpl_weekly}
    title="CPL by creative type (weekly)"
    x=week_label
    y=cpl
    series=creative_type
    sort=false
    yFmt=usd
/>


```sql audience_spend_leads_scatter
with spend_bounds as (
    select
        min(date_start) as spend_start,
        max(date_start) as spend_end
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
by_audience as (
    select
        adset_name as audience,
        sum(spend) as spend,
        sum(link_clicks) as page_visits
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1
),
crm as (
    select
        case c.utm_term
            when '120250101870600306' then 'VT & NH'
            when '120250101883590306' then 'VT & NH'
            when '120250093236920306' then 'NYC 15 Miles'
            when '120250091197620306' then 'NYC 15 Miles'
            when '120250093748420306' then 'Westchester / Hudson Valley'
            when '120250091788420306' then 'Westchester / Hudson Valley'
            when '120250091674470306' then 'Long Island Gold Coast/Hamptons'
            when '120250093766560306' then 'Long Island Gold Coast/Hamptons'
            when '120250093727620306' then 'NJ Shore'
            when '120250091847730306' then 'NJ Shore'
            when '120250091623250306' then 'Connecticut Gold Coast'
            when '120250093630920306' then 'Connecticut Gold Coast'
            else 'Unattributed'
        end as audience,
        count(*) as facebook_leads
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    cross join spend_bounds b
    where lr.channel = 'Facebook Ads'
      and lr.lead_date >= greatest(b.spend_start, cast('${inputs.date_range.start}' as date))
      and lr.lead_date <= least(b.spend_end, cast('${inputs.date_range.end}' as date))
    group by 1
)
select
    a.audience,
    round(a.spend, 2) as spend,
    coalesce(c.facebook_leads, 0) as facebook_leads,
    a.page_visits
from by_audience a
left join crm c on c.audience = a.audience
where a.audience is not null
order by spend desc
```

<ScatterPlot
    data={audience_spend_leads_scatter}
    title="Spend vs CRM leads by audience"
    x=spend
    y=facebook_leads
    series=audience
    xFmt=usd
    sort=false
/>

```sql spend_efficiency_weekly
with spend_bounds as (
    select
        min(date_start) as spend_start,
        max(date_start) as spend_end
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
weekly_meta as (
    select
        date_trunc('week', date_start)::date as week_start,
        adset_name as audience,
        sum(spend) as spend
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1, 2
),
weekly_crm as (
    select
        date_trunc('week', lr.lead_date)::date as week_start,
        case c.utm_term
            when '120250101870600306' then 'VT & NH'
            when '120250101883590306' then 'VT & NH'
            when '120250093236920306' then 'NYC 15 Miles'
            when '120250091197620306' then 'NYC 15 Miles'
            when '120250093748420306' then 'Westchester / Hudson Valley'
            when '120250091788420306' then 'Westchester / Hudson Valley'
            when '120250091674470306' then 'Long Island Gold Coast/Hamptons'
            when '120250093766560306' then 'Long Island Gold Coast/Hamptons'
            when '120250093727620306' then 'NJ Shore'
            when '120250091847730306' then 'NJ Shore'
            when '120250091623250306' then 'Connecticut Gold Coast'
            when '120250093630920306' then 'Connecticut Gold Coast'
            else 'Unattributed'
        end as audience,
        count(*) as facebook_leads
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    cross join spend_bounds b
    where lr.channel = 'Facebook Ads'
      and lr.lead_date >= greatest(b.spend_start, cast('${inputs.date_range.start}' as date))
      and lr.lead_date <= least(b.spend_end, cast('${inputs.date_range.end}' as date))
    group by 1, 2
),
joined as (
    select
        coalesce(m.week_start, c.week_start) as week_start,
        coalesce(m.audience, c.audience) as audience,
        coalesce(m.spend, 0) as spend,
        coalesce(c.facebook_leads, 0) as facebook_leads
    from weekly_meta m
    full outer join weekly_crm c
        on m.week_start = c.week_start
       and m.audience = c.audience
)
select
    week_start,
    strftime(week_start, '%b %d') as week_label,
    audience,
    round(1000.0 * facebook_leads / nullif(spend, 0), 2) as leads_per_1k_spend
from joined
where audience != 'Unattributed'
  and spend > 0
order by week_start, audience
```

<LineChart
    data={spend_efficiency_weekly}
    title="Lead efficiency by audience (leads per $1k spend, weekly)"
    x=week_label
    y=leads_per_1k_spend
    series=audience
    sort=false
/>

```sql meta_delivery_over_time
with daily as (
    select
        date_start as report_date,
        sum(impressions) as impressions,
        sum(link_clicks) as page_visits,
        sum(clicks) as all_clicks
    from meta_ads.daily_campaign_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1
),
date_span as (
    select unnest(
        generate_series(
            cast('${inputs.date_range.start}' as date),
            cast('${inputs.date_range.end}' as date),
            interval 1 day
        )
    )::date as report_date
)
select
    d.report_date,
    strftime(d.report_date, '%b %d') as report_date_label,
    coalesce(daily.impressions, 0) as impressions,
    coalesce(daily.page_visits, 0) as page_visits
from date_span d
left join daily on d.report_date = daily.report_date
order by d.report_date
```

<LineChart
    data={meta_delivery_over_time}
    title="Impressions and page visits over time"
    x=report_date_label
    y=impressions
    y2=page_visits
    sort=false
    yFmt='#,##0'
    y2Fmt='#,##0'
/>

```sql ctr_comparison_over_time
with daily as (
    select
        date_start as report_date,
        sum(impressions) as impressions,
        sum(clicks) as all_clicks,
        sum(link_clicks) as link_clicks
    from meta_ads.daily_campaign_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1
),
date_span as (
    select unnest(
        generate_series(
            cast('${inputs.date_range.start}' as date),
            cast('${inputs.date_range.end}' as date),
            interval 1 day
        )
    )::date as report_date
),
filled as (
    select
        d.report_date,
        coalesce(daily.impressions, 0) as impressions,
        coalesce(daily.all_clicks, 0) as all_clicks,
        coalesce(daily.link_clicks, 0) as link_clicks
    from date_span d
    left join daily on d.report_date = daily.report_date
)
select
    report_date,
    strftime(report_date, '%b %d') as report_date_label,
    round(100.0 * all_clicks / nullif(impressions, 0), 2) as meta_ctr,
    round(100.0 * link_clicks / nullif(impressions, 0), 2) as link_ctr
from filled
where impressions > 0
order by report_date
```

<LineChart
    data={ctr_comparison_over_time}
    title="Meta CTR vs link CTR over time"
    subtitle="Meta CTR = all clicks ÷ impressions. Link CTR = landing page clicks ÷ impressions."
    x=report_date_label
    y=meta_ctr
    y2=link_ctr
    sort=false
    yFmt='0.0"%"'
    y2Fmt='0.0"%"'
/>

```sql device_funnel_over_time
with spend_bounds as (
    select
        min(date_start) as spend_start,
        max(date_start) as spend_end
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
meta_daily as (
    select
        date_start as report_date,
        case lower(impression_device)
            when 'desktop' then 'Non-mobile'
            when 'mobile' then 'Mobile'
            when 'mobile_app' then 'Mobile'
            when 'mobile_web' then 'Mobile'
            else 'Unknown'
        end as device_group,
        sum(impressions) as impressions
    from meta_ads.daily_adset_insights_by_device
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1, 2
),
crm_daily as (
    select
        lr.lead_date as report_date,
        case
            when c.device_type in ('ios', 'android', 'mobile_other') then 'Mobile'
            when c.device_type = 'desktop' then 'Non-mobile'
            else 'Unknown'
        end as device_group,
        count(*) as facebook_leads
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    cross join spend_bounds b
    where lr.channel = 'Facebook Ads'
      and lr.lead_date >= greatest(b.spend_start, cast('${inputs.date_range.start}' as date))
      and lr.lead_date <= least(b.spend_end, cast('${inputs.date_range.end}' as date))
    group by 1, 2
),
meta_labeled as (
    select
        report_date,
        strftime(report_date, '%b %d') as report_date_label,
        'Meta impressions — ' || device_group as series,
        impressions as value
    from meta_daily
    where device_group in ('Mobile', 'Non-mobile')
),
crm_labeled as (
    select
        report_date,
        strftime(report_date, '%b %d') as report_date_label,
        'CRM leads — ' || device_group as series,
        facebook_leads as value
    from crm_daily
    where device_group in ('Mobile', 'Non-mobile')
)
select * from meta_labeled
union all
select * from crm_labeled
order by report_date, series
```

<LineChart
    data={device_funnel_over_time}
    title="Mobile vs non-mobile: Meta impressions and CRM leads over time"
    x=report_date_label
    y=value
    series=series
    sort=false
    yFmt='#,##0'
/>

#### Facebook lead roster

Searchable list of every Facebook ad lead in the CRM for the selected date range.

```sql facebook_lead_roster
select
    coalesce(nullif(trim(c.contact_name), ''), 'Unknown') as contact_name,
    lr.lead_date,
    case c.utm_term
        when '120250101870600306' then 'VT & NH'
        when '120250101883590306' then 'VT & NH'
        when '120250093236920306' then 'NYC 15 Miles'
        when '120250091197620306' then 'NYC 15 Miles'
        when '120250093748420306' then 'Westchester / Hudson Valley'
        when '120250091788420306' then 'Westchester / Hudson Valley'
        when '120250091674470306' then 'Long Island Gold Coast/Hamptons'
        when '120250093766560306' then 'Long Island Gold Coast/Hamptons'
        when '120250093727620306' then 'NJ Shore'
        when '120250091847730306' then 'NJ Shore'
        when '120250091623250306' then 'Connecticut Gold Coast'
        when '120250093630920306' then 'Connecticut Gold Coast'
        else 'Unattributed'
    end as audience,
    case
        when lower(c.utm_campaign) like '%multi-geo%' then 'National'
        when lower(c.utm_campaign) like '%geo targeting%' then 'Northeast'
        else 'Other'
    end as campaign_group,
    case c.device_type
        when 'desktop' then 'Desktop'
        when 'ios' then 'Mobile'
        when 'android' then 'Mobile'
        when 'mobile_other' then 'Mobile'
        else 'Unknown'
    end as device,
    case
        when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 'Appointment'
        else 'New Lead'
    end as pipeline_stage,
    coalesce(nullif(trim(c.utm_campaign), ''), lr.opportunity_source, lr.contact_source) as source_detail,
    c.email,
    c.phone
from ghl._lead_records lr
join ghl.contacts c on c.id = lr.contact_id
join ghl.opportunities o on o.id = lr.opportunity_id
where lr.channel = 'Facebook Ads'
  and lr.lead_date >= '${inputs.date_range.start}'
  and lr.lead_date <= '${inputs.date_range.end}'
order by lr.lead_date desc, contact_name
```

<DataTable data={facebook_lead_roster} search=true rows=25 title="Facebook lead roster" subtitle="Every Facebook ad lead in the CRM for the selected date range.">
    <Column id="contact_name" title="Name" description="Contact name from GoHighLevel." />
    <Column id="lead_date" title="Lead date" description="Date the lead entered the CRM." />
    <Column id="audience" title="Audience" description="Ad audience mapped from UTM term." />
    <Column id="campaign_group" title="Campaign" description="Northeast or National campaign group." />
    <Column id="device" title="Device" description="Device from first-touch user agent." />
    <Column id="pipeline_stage" title="Stage" description="Current pipeline stage in the CRM." />
    <Column id="source_detail" title="Source detail" description="UTM campaign or opportunity source." />
    <Column id="email" title="Email" description="Contact email." />
    <Column id="phone" title="Phone" description="Contact phone." />
</DataTable>


### Performance highlights

```sql performance_highlights
select * from meta_ads.client_performance_highlights
```

<p class="text-sm text-base-content-muted mb-4">
    The 3% real-estate CTR benchmark is a rough industry reference, not a guaranteed target.
</p>

<PerformanceHighlights data={performance_highlights} />

---

## Email

Leads from email campaigns and newsletters, attributed via `utm_medium=email` or email-related UTM sources in GoHighLevel.

```sql email_channel_totals
with filtered as (
    select
        case
            when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1
            else 0
        end as is_appointment
    from ghl._lead_records lr
    join ghl.opportunities o on o.id = lr.opportunity_id
    where lr.channel = 'Email'
      and lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
),
totals as (
    select count(*) as total_leads
    from ghl._lead_records
    where lead_date >= '${inputs.date_range.start}'
      and lead_date <= '${inputs.date_range.end}'
)
select
    count(*) as leads,
    sum(is_appointment) as appointments,
    round(100.0 * sum(is_appointment) / nullif(count(*), 0), 2) as appointment_rate_pct,
    round(100.0 * count(*) / nullif((select total_leads from totals), 0), 2) as share_pct
from filtered
```

<ChannelMetricBlocks data={email_channel_totals} />

```sql email_source_breakdown
with labeled as (
    select
        lower(trim(coalesce(
            nullif(c.utm_campaign, ''),
            nullif(lr.opportunity_source, ''),
            nullif(c.source, ''),
            'unknown'
        ))) as source_key,
        coalesce(
            nullif(trim(c.utm_campaign), ''),
            nullif(trim(lr.opportunity_source), ''),
            nullif(trim(c.source), ''),
            'Unknown'
        ) as source,
        case
            when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1
            else 0
        end as is_appointment
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    join ghl.opportunities o on o.id = lr.opportunity_id
    where lr.channel = 'Email'
      and lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
)
select
    any_value(source) as source,
    count(*) as leads,
    round(100.0 * count(*) / nullif(sum(count(*)) over (), 0), 2) as share_pct,
    sum(is_appointment) as appointments,
    round(100.0 * sum(is_appointment) / nullif(count(*), 0), 2) as appointment_rate_pct
from labeled
group by source_key
order by leads desc, source
```

<DataTable data={email_source_breakdown} search=true title="Email campaigns" subtitle="Leads and appointments attributed to each email campaign or source tag.">
    <Column id="source" title="Campaign / source" description="Email campaign or source tag from UTMs or opportunity source." />
    <Column id="leads" title="Leads" fmt='#,##0' />
    <Column id="share_pct" title="Share" fmt='0.0"%"' description="Percent of email leads from this source." />
    <Column id="appointments" title="Appointments" fmt='#,##0' />
    <Column id="appointment_rate_pct" title="Appt. %" fmt='0.0"%"' />
</DataTable>

```sql email_device_breakdown
with labeled as (
    select
        case c.device_type
            when 'desktop' then 'Desktop'
            when 'ios' then 'Mobile'
            when 'android' then 'Mobile'
            when 'mobile_other' then 'Mobile'
            else 'Unknown'
        end as device,
        case
            when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1
            else 0
        end as is_appointment
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    join ghl.opportunities o on o.id = lr.opportunity_id
    where lr.channel = 'Email'
      and lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
)
select
    device,
    count(*) as leads,
    sum(is_appointment) as appointments,
    round(100.0 * sum(is_appointment) / nullif(count(*), 0), 2) as appointment_rate_pct
from labeled
group by 1
order by leads desc, device
```

<DataTable data={email_device_breakdown} search=true title="Email leads by device" subtitle="Device mix for email-sourced leads from first-touch user agent.">
    <Column id="device" title="Device" description="Device from first-touch user agent." />
    <Column id="leads" title="Leads" fmt='#,##0' />
    <Column id="appointments" title="Appointments" fmt='#,##0' />
    <Column id="appointment_rate_pct" title="Appt. %" fmt='0.0"%"' />
</DataTable>

```sql email_leads_cumulative
with daily as (
    select lead_date, count(*) as daily_leads
    from ghl._lead_records
    where channel = 'Email'
      and lead_date >= '${inputs.date_range.start}'
      and lead_date <= '${inputs.date_range.end}'
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
    data={email_leads_cumulative}
    title="Cumulative email leads"
    x=lead_date_label
    y=cumulative_leads
    sort=false
/>

```sql email_lead_roster
select
    coalesce(nullif(trim(c.contact_name), ''), 'Unknown') as contact_name,
    lr.lead_date,
    coalesce(nullif(trim(c.utm_campaign), ''), lr.opportunity_source, lr.contact_source) as source_detail,
    case c.device_type
        when 'desktop' then 'Desktop'
        when 'ios' then 'Mobile'
        when 'android' then 'Mobile'
        when 'mobile_other' then 'Mobile'
        else 'Unknown'
    end as device,
    case
        when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 'Appointment'
        else 'New Lead'
    end as pipeline_stage,
    c.email,
    c.phone
from ghl._lead_records lr
join ghl.contacts c on c.id = lr.contact_id
join ghl.opportunities o on o.id = lr.opportunity_id
where lr.channel = 'Email'
  and lr.lead_date >= '${inputs.date_range.start}'
  and lr.lead_date <= '${inputs.date_range.end}'
order by lr.lead_date desc, contact_name
```

<DataTable data={email_lead_roster} search=true rows=25 title="Email lead roster" subtitle="Every email lead in the CRM for the selected date range.">
    <Column id="contact_name" title="Name" />
    <Column id="lead_date" title="Lead date" />
    <Column id="source_detail" title="Campaign / source" />
    <Column id="device" title="Device" />
    <Column id="pipeline_stage" title="Stage" />
    <Column id="email" title="Email" />
    <Column id="phone" title="Phone" />
</DataTable>

---

## Print

Leads from print placements, attributed via `utm_medium=print` in GoHighLevel.

```sql print_channel_totals
with filtered as (
    select
        case
            when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1
            else 0
        end as is_appointment
    from ghl._lead_records lr
    join ghl.opportunities o on o.id = lr.opportunity_id
    where lr.channel = 'Print'
      and lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
),
totals as (
    select count(*) as total_leads
    from ghl._lead_records
    where lead_date >= '${inputs.date_range.start}'
      and lead_date <= '${inputs.date_range.end}'
)
select
    count(*) as leads,
    sum(is_appointment) as appointments,
    round(100.0 * sum(is_appointment) / nullif(count(*), 0), 2) as appointment_rate_pct,
    round(100.0 * count(*) / nullif((select total_leads from totals), 0), 2) as share_pct
from filtered
```

<ChannelMetricBlocks data={print_channel_totals} />


```sql print_leads_cumulative
with daily as (
    select lead_date, count(*) as daily_leads
    from ghl._lead_records
    where channel = 'Print'
      and lead_date >= '${inputs.date_range.start}'
      and lead_date <= '${inputs.date_range.end}'
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
    data={print_leads_cumulative}
    title="Cumulative print leads"
    x=lead_date_label
    y=cumulative_leads
    sort=false
/>

```sql print_source_breakdown
with labeled as (
    select
        lower(trim(coalesce(
            nullif(c.utm_campaign, ''),
            nullif(lr.opportunity_source, ''),
            nullif(c.source, ''),
            'unknown'
        ))) as source_key,
        coalesce(
            nullif(trim(c.utm_campaign), ''),
            nullif(trim(lr.opportunity_source), ''),
            nullif(trim(c.source), ''),
            'Unknown'
        ) as source,
        case
            when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1
            else 0
        end as is_appointment
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    join ghl.opportunities o on o.id = lr.opportunity_id
    where lr.channel = 'Print'
      and lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
)
select
    any_value(source) as source,
    count(*) as leads,
    round(100.0 * count(*) / nullif(sum(count(*)) over (), 0), 2) as share_pct,
    sum(is_appointment) as appointments
from labeled
group by source_key
order by leads desc, source
```

<DataTable data={print_source_breakdown} search=true title="Print publications" subtitle="Leads attributed to each print campaign or publication.">
    <Column id="source" title="Publication / source" description="Print campaign or publication from UTMs." />
    <Column id="leads" title="Leads" fmt='#,##0' />
    <Column id="share_pct" title="Share" fmt='0.0"%"' />
    <Column id="appointments" title="Appointments" fmt='#,##0' />
</DataTable>

```sql print_lead_roster
select
    coalesce(nullif(trim(c.contact_name), ''), 'Unknown') as contact_name,
    lr.lead_date,
    coalesce(nullif(trim(c.utm_campaign), ''), lr.opportunity_source, lr.contact_source) as source_detail,
    case
        when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 'Appointment'
        else 'New Lead'
    end as pipeline_stage,
    c.email,
    c.phone
from ghl._lead_records lr
join ghl.contacts c on c.id = lr.contact_id
join ghl.opportunities o on o.id = lr.opportunity_id
where lr.channel = 'Print'
  and lr.lead_date >= '${inputs.date_range.start}'
  and lr.lead_date <= '${inputs.date_range.end}'
order by lr.lead_date desc, contact_name
```

<DataTable data={print_lead_roster} search=true rows=25 title="Print lead roster" subtitle="Every print lead in the CRM for the selected date range.">
    <Column id="contact_name" title="Name" />
    <Column id="lead_date" title="Lead date" />
    <Column id="source_detail" title="Publication / source" />
    <Column id="pipeline_stage" title="Stage" />
    <Column id="email" title="Email" />
    <Column id="phone" title="Phone" />
</DataTable>

---

## Social

Organic social and untagged form submissions grouped as Social in the CRM — typically `session_source = Social media` or social-related contact sources without paid ad UTMs.

```sql social_channel_totals
with filtered as (
    select
        case
            when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1
            else 0
        end as is_appointment
    from ghl._lead_records lr
    join ghl.opportunities o on o.id = lr.opportunity_id
    where lr.channel = 'Social'
      and lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
),
totals as (
    select count(*) as total_leads
    from ghl._lead_records
    where lead_date >= '${inputs.date_range.start}'
      and lead_date <= '${inputs.date_range.end}'
)
select
    count(*) as leads,
    sum(is_appointment) as appointments,
    round(100.0 * sum(is_appointment) / nullif(count(*), 0), 2) as appointment_rate_pct,
    round(100.0 * count(*) / nullif((select total_leads from totals), 0), 2) as share_pct
from filtered
```

<ChannelMetricBlocks data={social_channel_totals} />


```sql social_leads_cumulative
with daily as (
    select lead_date, count(*) as daily_leads
    from ghl._lead_records
    where channel = 'Social'
      and lead_date >= '${inputs.date_range.start}'
      and lead_date <= '${inputs.date_range.end}'
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
    data={social_leads_cumulative}
    title="Cumulative social leads"
    x=lead_date_label
    y=cumulative_leads
    sort=false
/>

```sql social_source_breakdown
with labeled as (
    select
        coalesce(
            nullif(trim(c.source), ''),
            nullif(trim(lr.opportunity_source), ''),
            nullif(trim(c.session_source), ''),
            'Unknown'
        ) as source,
        case
            when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1
            else 0
        end as is_appointment
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    join ghl.opportunities o on o.id = lr.opportunity_id
    where lr.channel = 'Social'
      and lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
)
select
    source,
    count(*) as leads,
    round(100.0 * count(*) / nullif(sum(count(*)) over (), 0), 2) as share_pct,
    sum(is_appointment) as appointments
from labeled
group by 1
order by leads desc, source
```

<DataTable data={social_source_breakdown} search=true title="Social sources" subtitle="Leads from organic social and untagged form fills, by source.">
    <Column id="source" title="Form / source" description="Contact source or session source for social leads." />
    <Column id="leads" title="Leads" fmt='#,##0' />
    <Column id="share_pct" title="Share" fmt='0.0"%"' />
    <Column id="appointments" title="Appointments" fmt='#,##0' />
</DataTable>

```sql social_lead_roster
select
    coalesce(nullif(trim(c.contact_name), ''), 'Unknown') as contact_name,
    lr.lead_date,
    coalesce(nullif(trim(c.source), ''), lr.opportunity_source, c.session_source) as source_detail,
    c.referrer,
    case
        when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 'Appointment'
        else 'New Lead'
    end as pipeline_stage,
    c.email,
    c.phone
from ghl._lead_records lr
join ghl.contacts c on c.id = lr.contact_id
join ghl.opportunities o on o.id = lr.opportunity_id
where lr.channel = 'Social'
  and lr.lead_date >= '${inputs.date_range.start}'
  and lr.lead_date <= '${inputs.date_range.end}'
order by lr.lead_date desc, contact_name
```

<DataTable data={social_lead_roster} search=true rows=25 title="Social lead roster" subtitle="Every social lead in the CRM for the selected date range.">
    <Column id="contact_name" title="Name" />
    <Column id="lead_date" title="Lead date" />
    <Column id="source_detail" title="Form / source" />
    <Column id="referrer" title="Referrer" />
    <Column id="pipeline_stage" title="Stage" />
    <Column id="email" title="Email" />
    <Column id="phone" title="Phone" />
</DataTable>

---

## No campaign tag

Direct traffic and form fills that arrived without UTM parameters — often organic visits or links missing campaign tags.

```sql no_tag_channel_totals
with filtered as (
    select
        case
            when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1
            else 0
        end as is_appointment
    from ghl._lead_records lr
    join ghl.opportunities o on o.id = lr.opportunity_id
    where lr.channel = 'No Campaign Tag'
      and lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
),
totals as (
    select count(*) as total_leads
    from ghl._lead_records
    where lead_date >= '${inputs.date_range.start}'
      and lead_date <= '${inputs.date_range.end}'
)
select
    count(*) as leads,
    sum(is_appointment) as appointments,
    round(100.0 * sum(is_appointment) / nullif(count(*), 0), 2) as appointment_rate_pct,
    round(100.0 * count(*) / nullif((select total_leads from totals), 0), 2) as share_pct
from filtered
```

<ChannelMetricBlocks data={no_tag_channel_totals} />

```sql no_tag_source_breakdown
with labeled as (
    select
        coalesce(
            nullif(trim(c.source), ''),
            nullif(trim(lr.opportunity_source), ''),
            nullif(trim(c.session_source), ''),
            'Unknown'
        ) as source,
        case
            when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1
            else 0
        end as is_appointment
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    join ghl.opportunities o on o.id = lr.opportunity_id
    where lr.channel = 'No Campaign Tag'
      and lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
)
select
    source,
    count(*) as leads,
    sum(is_appointment) as appointments
from labeled
group by 1
order by leads desc, source
```

<DataTable data={no_tag_source_breakdown} search=true title="Untagged lead sources" subtitle="Form and session sources for leads without UTM parameters.">
    <Column id="source" title="Form / session source" description="Contact source or session source when UTMs are missing." />
    <Column id="leads" title="Leads" fmt='#,##0' />
    <Column id="appointments" title="Appointments" fmt='#,##0' />
</DataTable>

```sql no_tag_lead_roster
select
    coalesce(nullif(trim(c.contact_name), ''), 'Unknown') as contact_name,
    lr.lead_date,
    coalesce(nullif(trim(c.source), ''), lr.opportunity_source, c.session_source) as source_detail,
    c.referrer,
    c.page_url,
    case
        when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 'Appointment'
        else 'New Lead'
    end as pipeline_stage,
    c.email,
    c.phone
from ghl._lead_records lr
join ghl.contacts c on c.id = lr.contact_id
join ghl.opportunities o on o.id = lr.opportunity_id
where lr.channel = 'No Campaign Tag'
  and lr.lead_date >= '${inputs.date_range.start}'
  and lr.lead_date <= '${inputs.date_range.end}'
order by lr.lead_date desc, contact_name
```

<DataTable data={no_tag_lead_roster} search=true rows=25 title="Untagged lead roster" subtitle="Leads without campaign tags in the CRM for the selected date range.">
    <Column id="contact_name" title="Name" />
    <Column id="lead_date" title="Lead date" />
    <Column id="source_detail" title="Form / session source" />
    <Column id="referrer" title="Referrer" />
    <Column id="page_url" title="Landing page" />
    <Column id="pipeline_stage" title="Stage" />
    <Column id="email" title="Email" />
    <Column id="phone" title="Phone" />
</DataTable>

---

## Other channels

Referrals, website inquiries, marketplace posts, and other smaller sources not covered above.

```sql other_channel_breakdown
with labeled as (
    select
        lr.channel,
        case
            when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1
            else 0
        end as is_appointment
    from ghl._lead_records lr
    join ghl.opportunities o on o.id = lr.opportunity_id
    where lr.channel not in (
        'Facebook Ads', 'Email', 'Print', 'Social', 'No Campaign Tag'
    )
      and lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
)
select
    channel,
    count(*) as leads,
    sum(is_appointment) as appointments,
    round(100.0 * sum(is_appointment) / nullif(count(*), 0), 2) as appointment_rate_pct
from labeled
group by 1
order by leads desc, channel
```

<DataTable data={other_channel_breakdown} search=true title="Other channels" subtitle="Referrals, website inquiries, marketplace, and other smaller sources.">
    <Column id="channel" title="Channel" description="CRM channel classification." />
    <Column id="leads" title="Leads" fmt='#,##0' />
    <Column id="appointments" title="Appointments" fmt='#,##0' />
    <Column id="appointment_rate_pct" title="Appt. %" fmt='0.0"%"' />
</DataTable>

```sql other_lead_roster
select
    coalesce(nullif(trim(c.contact_name), ''), 'Unknown') as contact_name,
    lr.lead_date,
    lr.channel,
    coalesce(nullif(trim(c.utm_campaign), ''), lr.opportunity_source, lr.contact_source, c.session_source) as source_detail,
    case
        when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 'Appointment'
        else 'New Lead'
    end as pipeline_stage,
    c.email,
    c.phone
from ghl._lead_records lr
join ghl.contacts c on c.id = lr.contact_id
join ghl.opportunities o on o.id = lr.opportunity_id
where lr.channel not in (
    'Facebook Ads', 'Email', 'Print', 'Social', 'No Campaign Tag'
)
  and lr.lead_date >= '${inputs.date_range.start}'
  and lr.lead_date <= '${inputs.date_range.end}'
order by lr.lead_date desc, contact_name
```

<DataTable data={other_lead_roster} search=true rows=25 title="Other channel lead roster" subtitle="Leads from smaller channels not covered above.">
    <Column id="contact_name" title="Name" />
    <Column id="lead_date" title="Lead date" />
    <Column id="channel" title="Channel" />
    <Column id="source_detail" title="Source detail" />
    <Column id="pipeline_stage" title="Stage" />
    <Column id="email" title="Email" />
    <Column id="phone" title="Phone" />
</DataTable>

---

