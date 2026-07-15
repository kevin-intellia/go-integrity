---
title: Facebook
sidebar: never
hide_breadcrumbs: true
hide_toc: true
---

<p class="text-sm text-base-content-muted mb-2">
    <a href="/">All</a> · <strong>Facebook</strong> · <a href="/home-ab-test/">Page 1 A/B</a>
</p>

<p class="text-sm text-base-content-muted mb-4">
    Meta spend, landing page visits, and Facebook-attributed CRM outcomes.
</p>

```sql report_dates
select lead_date as report_date from ghl._lead_records
union all
select date_start as report_date from meta_ads.daily_campaign_insights
```

```sql data_freshness
select
    max(date_start) as latest_meta_spend_date,
    max(lead_date) as latest_crm_lead_date
from meta_ads.daily_campaign_insights
cross join (
    select max(lead_date) as lead_date from ghl._lead_records
) crm
```

<p class="text-xs text-base-content-muted mb-4">
    Data freshness: Meta spend through {data_freshness[0].latest_meta_spend_date}; CRM leads through {data_freshness[0].latest_crm_lead_date}.
</p>

<DateRange
    name=date_range
    data={report_dates}
    dates=report_date
    title="Date range"
    presetRanges={['Last 7 Days', 'Last 30 Days', 'All Time']}
    defaultValue="All Time"
/>

## Overview

```sql overview_totals
select
    round(coalesce(m.spend, 0), 2) as total_spend,
    coalesce(m.landing_page_visits, 0) as landing_page_visits,
    coalesce(c.facebook_leads, 0) as facebook_leads,
    coalesce(c.showings_requested, 0) as showings_requested
from (
    select
        sum(spend) as spend,
        sum(link_clicks) as landing_page_visits
    from meta_ads.daily_campaign_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
) m
cross join (
    select
        count(*) as facebook_leads,
        sum(
            case when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1 else 0 end
        ) as showings_requested
    from ghl._lead_records lr
    join ghl.opportunities o on o.id = lr.opportunity_id
    where lr.channel = 'Facebook'
      and lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
) c
```

```sql daily_spend_by_campaign_group
with classified as (
    select
        date_start as report_date,
        case
            when lower(campaign_name) like '%ski targeting%' then 'Ski'
            when lower(campaign_name) like '%multi-geo targeting%' then 'National'
            when lower(campaign_name) like '%geo targeting%' then 'Northeast'
            else 'Other'
        end as campaign_group,
        case
            when lower(campaign_name) like '%- website%' then 'website'
            else 'funnel'
        end as website_variant,
        spend
    from meta_ads.daily_campaign_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
daily as (
    select
        report_date,
        campaign_group,
        website_variant,
        round(sum(spend), 2) as daily_spend
    from classified
    where campaign_group != 'Other'
    group by 1, 2, 3
),
combinations as (
    select distinct campaign_group, website_variant from daily
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
        c.campaign_group,
        c.website_variant,
        coalesce(daily.daily_spend, 0) as daily_spend
    from date_span d
    cross join combinations c
    left join daily
        on d.report_date = daily.report_date
       and c.campaign_group = daily.campaign_group
       and c.website_variant = daily.website_variant
)
select
    report_date,
    strftime(report_date, '%b %d') as report_date_label,
    campaign_group,
    website_variant,
    daily_spend
from filled
order by
    case campaign_group
        when 'Northeast' then 1
        when 'National' then 2
        when 'Ski' then 3
        else 4
    end,
    case website_variant
        when 'funnel' then 1
        when 'website' then 2
        else 3
    end,
    report_date
```

```sql daily_cost_efficiency
with classified_meta as (
    select
        date_start as report_date,
        case
            when lower(campaign_name) like '%ski targeting%' then 'Ski'
            when lower(campaign_name) like '%multi-geo targeting%' then 'National'
            when lower(campaign_name) like '%geo targeting%' then 'Northeast'
            else 'Other'
        end as campaign_group,
        case
            when lower(campaign_name) like '%- website%' then 'website'
            else 'funnel'
        end as website_variant,
        case
            when lower(campaign_name) like '%non-dynamic%' then 'Static'
            when lower(campaign_name) like '%dynamic%' then 'Dynamic'
            else 'Other'
        end as creative_type,
        spend
    from meta_ads.daily_campaign_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
daily_meta as (
    select
        report_date,
        campaign_group,
        website_variant,
        creative_type,
        round(sum(spend), 2) as daily_spend
    from classified_meta
    where campaign_group != 'Other'
      and creative_type != 'Other'
    group by 1, 2, 3, 4
),
adset_dims as (
    select distinct
        adset_id,
        case
            when lower(campaign_name) like '%ski targeting%' then 'Ski'
            when lower(campaign_name) like '%multi-geo targeting%' then 'National'
            when lower(campaign_name) like '%geo targeting%' then 'Northeast'
            else 'Other'
        end as campaign_group,
        case
            when lower(campaign_name) like '%- website%' then 'website'
            else 'funnel'
        end as website_variant,
        case
            when lower(campaign_name) like '%non-dynamic%' then 'Static'
            when lower(campaign_name) like '%dynamic%' then 'Dynamic'
            else 'Other'
        end as creative_type
    from meta_ads.daily_adset_insights
),
daily_crm as (
    select
        lr.lead_date as report_date,
        coalesce(
            ad.campaign_group,
            case
                when lower(c.utm_campaign) like '%ski targeting%' then 'Ski'
                when lower(c.utm_campaign) like '%multi-geo targeting%' then 'National'
                when lower(c.utm_campaign) like '%geo targeting%' then 'Northeast'
                else 'Other'
            end
        ) as campaign_group,
        coalesce(ad.website_variant, 'funnel') as website_variant,
        coalesce(
            ad.creative_type,
            case
                when lower(c.utm_campaign) like '%non-dynamic%' then 'Static'
                when lower(c.utm_campaign) like '%dynamic%' then 'Dynamic'
                else 'Other'
            end
        ) as creative_type,
        count(*) as daily_leads,
        sum(
            case when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1 else 0 end
        ) as daily_showings
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    join ghl.opportunities o on o.id = lr.opportunity_id
    left join adset_dims ad on ad.adset_id = c.utm_term
    where lr.channel = 'Facebook'
      and lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
    group by 1, 2, 3, 4
),
combinations as (
    select distinct campaign_group, website_variant, creative_type
    from daily_meta
    union
    select distinct campaign_group, website_variant, creative_type
    from daily_crm
    where campaign_group != 'Other'
      and creative_type != 'Other'
),
date_span as (
    select report_date
    from (
        select unnest(
            generate_series(
                cast('${inputs.date_range.start}' as date),
                cast('${inputs.date_range.end}' as date),
                interval 1 day
            )
        )::date as report_date
    )
    where report_date != date '2026-07-03'
),
filled as (
    select
        d.report_date,
        c.campaign_group,
        c.website_variant,
        c.creative_type,
        coalesce(m.daily_spend, 0) as daily_spend,
        coalesce(cr.daily_leads, 0) as daily_leads,
        coalesce(cr.daily_showings, 0) as daily_showings
    from date_span d
    cross join combinations c
    left join daily_meta m
        on d.report_date = m.report_date
       and c.campaign_group = m.campaign_group
       and c.website_variant = m.website_variant
       and c.creative_type = m.creative_type
    left join daily_crm cr
        on d.report_date = cr.report_date
       and c.campaign_group = cr.campaign_group
       and c.website_variant = cr.website_variant
       and c.creative_type = cr.creative_type
    where c.campaign_group != 'Other'
      and c.creative_type != 'Other'
)
select
    report_date,
    strftime(report_date, '%b %d') as report_date_label,
    campaign_group,
    website_variant,
    creative_type,
    daily_spend,
    daily_leads,
    daily_showings
from filled
order by
    case campaign_group
        when 'Northeast' then 1
        when 'National' then 2
        when 'Ski' then 3
        else 4
    end,
    case website_variant
        when 'funnel' then 1
        when 'website' then 2
        else 3
    end,
    case creative_type
        when 'Dynamic' then 1
        when 'Static' then 2
        else 3
    end,
    report_date
```

<FacebookOverview overview={overview_totals} />

## Ad spend

<DailySpendByCampaignGroupChart data={daily_spend_by_campaign_group} />

<DailyCostEfficiencyChart data={daily_cost_efficiency} />

## Landing page performance

```sql campaign_groups
with classified as (
    select
        case
            when lower(campaign_name) like '%ski targeting%' then 'Ski'
            when lower(campaign_name) like '%multi-geo targeting%' then 'National'
            when lower(campaign_name) like '%geo targeting%' then 'Northeast'
            else 'Other'
        end as campaign_group,
        case
            when lower(campaign_name) like '%- website%' then 'website'
            else 'funnel'
        end as website_variant,
        spend,
        impressions,
        link_clicks
    from meta_ads.daily_campaign_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
meta as (
    select
        campaign_group,
        website_variant,
        sum(spend) as spend,
        sum(impressions) as impressions,
        sum(link_clicks) as landing_page_visits
    from classified
    where campaign_group != 'Other'
    group by 1, 2
),
adset_campaign as (
    select distinct
        adset_id,
        case
            when lower(campaign_name) like '%ski targeting%' then 'Ski'
            when lower(campaign_name) like '%multi-geo targeting%' then 'National'
            when lower(campaign_name) like '%geo targeting%' then 'Northeast'
            else 'Other'
        end as campaign_group,
        case
            when lower(campaign_name) like '%- website%' then 'website'
            else 'funnel'
        end as website_variant
    from meta_ads.daily_adset_insights
),
crm_classified as (
    select
        coalesce(
            ac.campaign_group,
            case
                when lower(c.utm_campaign) like '%ski targeting%' then 'Ski'
                when lower(c.utm_campaign) like '%multi-geo targeting%' then 'National'
                when lower(c.utm_campaign) like '%geo targeting%' then 'Northeast'
                else 'Other'
            end
        ) as campaign_group,
        coalesce(ac.website_variant, 'funnel') as website_variant,
        lr.opportunity_id,
        o.pipeline_stage_id
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    join ghl.opportunities o on o.id = lr.opportunity_id
    left join adset_campaign ac on ac.adset_id = c.utm_term
    where lr.channel = 'Facebook'
      and lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
),
crm as (
    select
        campaign_group,
        website_variant,
        count(*) as facebook_leads,
        sum(
            case when pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1 else 0 end
        ) as showings
    from crm_classified
    where campaign_group != 'Other'
    group by 1, 2
),
joined as (
    select
        m.campaign_group,
        m.website_variant,
        m.spend,
        m.impressions,
        m.landing_page_visits,
        coalesce(c.facebook_leads, 0) as facebook_leads,
        coalesce(c.showings, 0) as showings
    from meta m
    left join crm c
        on c.campaign_group = m.campaign_group
       and c.website_variant = m.website_variant
)
select
    campaign_group,
    website_variant,
    round(spend, 2) as spend,
    impressions,
    landing_page_visits,
    facebook_leads,
    showings
from joined
order by
    case campaign_group
        when 'Northeast' then 1
        when 'National' then 2
        when 'Ski' then 3
        else 4
    end,
    case website_variant
        when 'funnel' then 1
        when 'website' then 2
        else 3
    end
```

```sql audiences
with classified as (
    select
        adset_name,
        case
            when lower(campaign_name) like '%ski targeting%' then 'Ski'
            when lower(campaign_name) like '%multi-geo targeting%' then 'National'
            when lower(campaign_name) like '%geo targeting%' then 'Northeast'
            else 'Other'
        end as campaign_group,
        case
            when lower(campaign_name) like '%- website%' then 'website'
            else 'funnel'
        end as website_variant,
        spend,
        impressions,
        link_clicks
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
meta as (
    select
        campaign_group,
        website_variant,
        adset_name as audience,
        sum(spend) as spend,
        sum(impressions) as impressions,
        sum(link_clicks) as landing_page_visits
    from classified
    where campaign_group != 'Other'
    group by 1, 2, 3
),
adset_campaign as (
    select distinct
        adset_id,
        adset_name,
        case
            when lower(campaign_name) like '%ski targeting%' then 'Ski'
            when lower(campaign_name) like '%multi-geo targeting%' then 'National'
            when lower(campaign_name) like '%geo targeting%' then 'Northeast'
            else 'Other'
        end as campaign_group,
        case
            when lower(campaign_name) like '%- website%' then 'website'
            else 'funnel'
        end as website_variant
    from meta_ads.daily_adset_insights
),
crm_classified as (
    select
        coalesce(
            ac.campaign_group,
            case
                when lower(c.utm_campaign) like '%ski targeting%' then 'Ski'
                when lower(c.utm_campaign) like '%multi-geo targeting%' then 'National'
                when lower(c.utm_campaign) like '%geo targeting%' then 'Northeast'
                else 'Other'
            end
        ) as campaign_group,
        coalesce(ac.website_variant, 'funnel') as website_variant,
        coalesce(ac.adset_name, 'Unattributed') as audience,
        lr.opportunity_id,
        o.pipeline_stage_id
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    join ghl.opportunities o on o.id = lr.opportunity_id
    left join adset_campaign ac on ac.adset_id = c.utm_term
    where lr.channel = 'Facebook'
      and lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
),
crm as (
    select
        campaign_group,
        website_variant,
        audience,
        count(*) as facebook_leads,
        sum(
            case when pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1 else 0 end
        ) as showings
    from crm_classified
    where campaign_group != 'Other'
      and audience != 'Unattributed'
    group by 1, 2, 3
),
joined as (
    select
        m.campaign_group,
        m.website_variant,
        m.audience,
        m.spend,
        m.impressions,
        m.landing_page_visits,
        coalesce(c.facebook_leads, 0) as facebook_leads,
        coalesce(c.showings, 0) as showings
    from meta m
    left join crm c
        on c.campaign_group = m.campaign_group
       and c.website_variant = m.website_variant
       and c.audience = m.audience
)
select
    campaign_group,
    website_variant,
    audience,
    round(spend, 2) as spend,
    impressions,
    landing_page_visits,
    facebook_leads,
    showings
from joined
where spend >= 100
order by
    case campaign_group
        when 'Northeast' then 1
        when 'National' then 2
        when 'Ski' then 3
        else 4
    end,
    case website_variant
        when 'funnel' then 1
        when 'website' then 2
        else 3
    end,
    spend desc
```

<CampaignGroupsTable data={campaign_groups} audiences={audiences} />

## Ad performance

```sql creative_comparison
with classified as (
    select
        case
            when lower(campaign_name) like '%non-dynamic%' then 'Non-dynamic'
            when lower(campaign_name) like '%dynamic%' then 'Dynamic'
        end as creative_type,
        spend,
        impressions,
        link_clicks
    from meta_ads.daily_campaign_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
),
meta as (
    select
        creative_type,
        round(sum(spend), 2) as spend,
        sum(impressions) as impressions,
        sum(link_clicks) as landing_page_visits
    from classified
    where creative_type is not null
    group by 1
),
adset_campaign as (
    select distinct
        adset_id,
        case
            when lower(campaign_name) like '%non-dynamic%' then 'Non-dynamic'
            when lower(campaign_name) like '%dynamic%' then 'Dynamic'
        end as creative_type
    from meta_ads.daily_adset_insights
    where case
            when lower(campaign_name) like '%non-dynamic%' then 'Non-dynamic'
            when lower(campaign_name) like '%dynamic%' then 'Dynamic'
        end is not null
),
crm as (
    select
        ac.creative_type,
        count(*) as facebook_leads,
        sum(
            case when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1 else 0 end
        ) as showings
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    join ghl.opportunities o on o.id = lr.opportunity_id
    join adset_campaign ac on ac.adset_id = c.utm_term
    where lr.channel = 'Facebook'
      and lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
    group by 1
),
joined as (
    select
        m.creative_type,
        m.spend,
        m.impressions,
        m.landing_page_visits,
        coalesce(c.facebook_leads, 0) as facebook_leads,
        coalesce(c.showings, 0) as showings
    from meta m
    left join crm c on c.creative_type = m.creative_type
)
select
    creative_type,
    spend,
    round(100.0 * landing_page_visits / nullif(impressions, 0), 2) as link_ctr,
    round(spend / nullif(landing_page_visits, 0), 2) as cpc,
    landing_page_visits,
    facebook_leads,
    round(spend / nullif(facebook_leads, 0), 2) as cpl,
    showings,
    round(spend / nullif(showings, 0), 2) as cost_per_showing
from joined
order by
    case creative_type
        when 'Non-dynamic' then 1
        when 'Dynamic' then 2
        else 3
    end
```

```sql ad_creatives
with crm_detail as (
    select
        trim(c.utm_content) as ad_name,
        c.utm_term as adset_id,
        case
            when lower(max(c.utm_campaign)) like '%non-dynamic%' then 'Non-dynamic'
            when lower(max(c.utm_campaign)) like '%dynamic%' then 'Dynamic'
        end as creative_type,
        count(*) as facebook_leads,
        sum(
            case when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1 else 0 end
        ) as showings
    from ghl._lead_records lr
    join ghl.contacts c on c.id = lr.contact_id
    join ghl.opportunities o on o.id = lr.opportunity_id
    where lr.channel = 'Facebook'
      and lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
      and c.utm_content is not null
      and trim(c.utm_content) != ''
      and c.utm_content != '{{ad.name}}'
    group by 1, 2
),
adset_lead_totals as (
    select
        adset_id,
        sum(facebook_leads) as adset_leads
    from crm_detail
    group by 1
),
meta_adset as (
    select
        adset_id,
        sum(spend) as spend,
        sum(impressions) as impressions,
        sum(link_clicks) as landing_page_visits
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1
),
creative_meta as (
    select
        case
            when lower(campaign_name) like '%non-dynamic%' then 'Non-dynamic'
            when lower(campaign_name) like '%dynamic%' then 'Dynamic'
        end as creative_type,
        sum(spend) as spend,
        sum(impressions) as impressions,
        sum(link_clicks) as landing_page_visits
    from meta_ads.daily_adset_insights
    where date_start >= '${inputs.date_range.start}'
      and date_start <= '${inputs.date_range.end}'
    group by 1
),
creative_lead_totals as (
    select
        creative_type,
        sum(facebook_leads) as creative_leads
    from crm_detail
    group by 1
),
allocated as (
    select
        cd.ad_name,
        cd.creative_type,
        cd.facebook_leads,
        cd.showings,
        coalesce(
            mas.spend * cd.facebook_leads::double / nullif(alt.adset_leads, 0),
            cm.spend * cd.facebook_leads::double / nullif(clt.creative_leads, 0),
            0
        ) as spend,
        coalesce(
            mas.impressions * cd.facebook_leads::double / nullif(alt.adset_leads, 0),
            cm.impressions * cd.facebook_leads::double / nullif(clt.creative_leads, 0),
            0
        ) as impressions,
        coalesce(
            mas.landing_page_visits * cd.facebook_leads::double / nullif(alt.adset_leads, 0),
            cm.landing_page_visits * cd.facebook_leads::double / nullif(clt.creative_leads, 0),
            0
        ) as landing_page_visits
    from crm_detail cd
    left join adset_lead_totals alt on alt.adset_id = cd.adset_id
    left join meta_adset mas on mas.adset_id = cd.adset_id
    left join creative_lead_totals clt on clt.creative_type = cd.creative_type
    left join creative_meta cm on cm.creative_type = cd.creative_type
),
rolled as (
    select
        ad_name,
        max(creative_type) as creative_type,
        sum(facebook_leads) as facebook_leads,
        sum(showings) as showings,
        round(sum(spend), 2) as spend,
        sum(impressions) as impressions,
        sum(landing_page_visits) as landing_page_visits
    from allocated
    group by 1
),
joined as (
    select
        ad_name,
        creative_type,
        spend,
        impressions,
        landing_page_visits,
        facebook_leads,
        showings
    from rolled
    where facebook_leads > 0
)
select
    'crm:' || ad_name as ad_id,
    ad_name,
    creative_type,
    spend,
    facebook_leads,
    round(spend / nullif(facebook_leads, 0), 2) as cpl,
    round(100.0 * landing_page_visits / nullif(impressions, 0), 2) as link_ctr,
    round(spend / nullif(landing_page_visits, 0), 2) as cpc,
    landing_page_visits,
    showings,
    round(spend / nullif(showings, 0), 2) as cost_per_showing
from joined
order by
    facebook_leads desc,
    cpl nulls last,
    spend desc,
    ad_name
```

<CreativeComparisonTable data={creative_comparison} />

<AdCreativesTable data={ad_creatives} />

## Device breakdown

```sql device_breakdown
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
    where lr.channel = 'Facebook'
      and lr.lead_date >= '${inputs.date_range.start}'
      and lr.lead_date <= '${inputs.date_range.end}'
),
grouped as (
    select
        device_group,
        count(*) as leads,
        sum(is_appointment) as appointments
    from labeled
    group by 1
),
group_rows as (
    select
        device_group,
        leads,
        round(100.0 * leads / nullif(sum(leads) over (), 0), 2) as lead_share_pct,
        appointments,
        round(100.0 * appointments / nullif(sum(appointments) over (), 0), 2) as appointment_share_pct,
        0 as sort_order
    from grouped
),
total_row as (
    select
        'Total' as device_group,
        sum(leads) as leads,
        100.0 as lead_share_pct,
        sum(appointments) as appointments,
        100.0 as appointment_share_pct,
        1 as sort_order
    from grouped
)
select device_group, leads, lead_share_pct, appointments, appointment_share_pct
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

<DataTable data={device_breakdown} search=true title="Device summary" subtitle="Facebook CRM leads grouped by mobile, non-mobile (desktop), or unknown device type. Share columns are each a percent of the column total.">
    <Column id="device_group" title="Device" description="Mobile, non-mobile (desktop), or unknown." />
    <Column id="leads" title="Leads" fmt='#,##0' description="Facebook CRM leads on this device type." />
    <Column id="lead_share_pct" title="Lead share" fmt='0.0"%"' description="Share of all Facebook leads on this device type." />
    <Column id="appointments" title="Appointments" fmt='#,##0' description="Leads moved to the appointment stage." />
    <Column id="appointment_share_pct" title="Appt. share" fmt='0.0"%"' description="Share of all appointments on this device type." />
</DataTable>
