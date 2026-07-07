---
title: Campaign Performance
description: Overall lead activity and Facebook ad performance for the last 30 days.
sidebar: never
hide_breadcrumbs: true
---

<CampaignSummary />

## Overall Lead Activity

All leads and outcomes across every channel.

```sql crm_totals
select * from ghl.client_crm_totals
```

<CrmMetricBlocks data={crm_totals} showShowingsBooked={false} />

## Lead Sources

All campaigns and channels driving leads into the CRM.

```sql lead_channels
select channel, leads from ghl.client_lead_channels
```

<BarChart
    data={lead_channels}
    title="Leads by channel"
    x=channel
    y=leads
    swapXY=true
/>

## Facebook Ad Funnel

```sql funnel_totals
select
    m.impressions,
    m.landing_page_clicks,
    c.facebook_ad_leads as learn_more_forms,
    (
        select count(*)
        from ghl.client_appointments
        where channel = 'Facebook Ad'
    ) as appointments_booked
from meta_ads.funnel_totals m
cross join ghl.client_crm_totals c
```

<FunnelMetricBlocks data={funnel_totals} />

```sql lead_cumulative
select lead_date_label, cumulative_leads
from ghl.client_lead_cumulative
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

## Showings

Leads who requested a showing or booked a private viewing.

```sql appointments
select
    name,
    channel,
    audience
from ghl.client_appointments
```

<DataTable data={appointments} search=true>
    <Column id="name" title="Name" />
    <Column id="channel" title="Lead source" />
    <Column id="audience" title="Ad audience" />
</DataTable>
