select
    round(sum(spend), 2) as spend,
    sum(impressions) as impressions,
    sum(link_clicks) as link_clicks,
    round(sum(conversion_1), 0) as meta_leads,
    round(sum(conversion_2), 0) as showing_requests,
    round(100.0 * sum(link_clicks) / nullif(sum(impressions), 0), 2) as ctr,
    round(sum(spend) / nullif(sum(link_clicks), 0), 2) as cpc,
    round(1000.0 * sum(spend) / nullif(sum(impressions), 0), 2) as cpm,
    round(sum(spend) / nullif(sum(conversion_1), 0), 2) as cpl_meta,
    round(sum(spend) / nullif(sum(conversion_2), 0), 2) as cost_per_showing
from daily_campaign_insights
