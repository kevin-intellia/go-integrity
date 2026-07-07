with by_adset as (
    select
        adset_name,
        sum(spend) as spend,
        sum(impressions) as impressions,
        sum(link_clicks) as link_clicks,
        round(sum(conversion_1), 0) as meta_leads,
        round(sum(conversion_2), 0) as showing_requests
    from daily_adset_insights
    group by 1
)
select
    adset_name,
    round(spend, 2) as spend,
    round(100.0 * spend / nullif(sum(spend) over (), 0), 2) as spend_share_pct,
    impressions,
    round(100.0 * link_clicks / nullif(impressions, 0), 2) as ctr,
    round(spend / nullif(link_clicks, 0), 2) as cpc,
    round(1000.0 * spend / nullif(impressions, 0), 2) as cpm,
    meta_leads,
    round(spend / nullif(meta_leads, 0), 2) as cpl_meta,
    showing_requests,
    round(spend / nullif(showing_requests, 0), 2) as cost_per_showing
from by_adset
order by spend desc
