select
    sum(impressions) as impressions,
    sum(link_clicks) as landing_page_clicks,
    round(sum(conversion_1), 0) as learn_more_forms,
    round(sum(conversion_2), 0) as showing_requests
from daily_campaign_insights
