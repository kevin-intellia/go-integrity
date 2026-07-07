---
title: Meta Ads — Internal Analytics
sidebar_link: false
---

<p class="text-sm text-base-content-muted mb-2">INTERNAL ONLY — last 30 days</p>

<RefreshDataButton />

## Account Spend & Efficiency

```sql spend_totals
select * from meta_ads.spend_totals
```

<SpendMetricBlocks data={spend_totals} />

```sql spend_crm_efficiency
select
    round(s.spend / nullif(c.total_leads, 0), 2) as cpl_crm,
    round(s.spend / nullif(c.appointments_scheduled, 0), 2) as cpa_crm
from meta_ads.spend_totals s
cross join ghl.client_crm_totals c
```

<Grid cols=2>
    <BigValue data={spend_crm_efficiency} value=cpl_crm title="CPL — CRM" fmt=usd />
    <BigValue data={spend_crm_efficiency} value=cpa_crm title="CPA — CRM (showings requested)" fmt=usd />
</Grid>

```sql crm_totals
select * from ghl.client_crm_totals
```

<CrmMetricBlocks data={crm_totals} />

## Performance Highlights

```sql performance_highlights
select * from meta_ads.client_performance_highlights
```

<PerformanceHighlights data={performance_highlights} />

## Ad Set Rankings

```sql adset_leaderboard
select * from meta_ads.adset_leaderboard
```

```sql adset_efficiency
select * from meta_ads.adset_efficiency
```

<DataTable data={adset_efficiency} search=true rows=20>
    <Column id="adset_name" title="Audience" />
    <Column id="spend" title="Spend" fmt=usd />
    <Column id="spend_share_pct" title="Spend %" fmt='0.0"%"' />
    <Column id="impressions" title="Impressions" fmt='#,##0' />
    <Column id="ctr" title="CTR" fmt='0.0"%"' />
    <Column id="cpc" title="CPC" fmt=usd />
    <Column id="cpm" title="CPM" fmt=usd />
    <Column id="meta_leads" title="Meta Leads" fmt='#,##0' />
    <Column id="cpl_meta" title="CPL — Meta" fmt=usd />
    <Column id="showing_requests" title="Showings (Meta)" fmt='#,##0' />
    <Column id="cost_per_showing" title="Cost / Showing" fmt=usd />
</DataTable>

<Grid cols=2>
    <BarChart
        data={adset_efficiency}
        title="Spend by audience"
        x=adset_name
        y=spend
        yFmt=usd
        swapXY=true
    />
    <BarChart
        data={adset_efficiency}
        title="CPL by audience (Meta)"
        x=adset_name
        y=cpl_meta
        yFmt=usd
        swapXY=true
    />
</Grid>

```sql daily_spend
select * from meta_ads.daily_spend
```

<LineChart
    data={daily_spend}
    title="Daily spend by audience"
    x=date_start
    y=spend
    series=audience
    yFmt=usd
/>

## Ad Set Funnel

```sql adset_funnel
select * from meta_ads.adset_funnel
```

<DataTable data={adset_funnel} search=true>
    <Column id="audience" title="Audience" />
    <Column id="impressions" title="Impressions" fmt='#,##0' />
    <Column id="impressions_share_pct" title="Impr. %" fmt='0.0"%"' />
    <Column id="landing_page_clicks" title="Page Visits" fmt='#,##0' />
    <Column id="landing_page_clicks_pct" title="Visit %" fmt='0.0"%"' />
    <Column id="learn_more_forms" title="Lead Forms" fmt='#,##0' />
    <Column id="learn_more_forms_pct" title="Form %" fmt='0.0"%"' />
    <Column id="showing_requests" title="Showings" fmt='#,##0' />
    <Column id="showing_requests_pct" title="Showing %" fmt='0.0"%"' />
</DataTable>

## CRM Showings by Audience

```sql adset_appointments
select * from ghl.adset_appointments
```

<DataTable data={adset_appointments} search=true>
    <Column id="audience" title="Audience" />
    <Column id="crm_appointments" title="Showings requested" fmt='#,##0' />
</DataTable>

## Account Funnel

```sql funnel_totals
select
    m.impressions,
    m.landing_page_clicks,
    m.learn_more_forms,
    m.showing_requests as appointments_booked
from meta_ads.funnel_totals m
```

<FunnelMetricBlocks data={funnel_totals} description="Paid Meta ad funnel — impressions through CRM lead forms." />
