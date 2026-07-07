select
    date_start,
    adset_name as audience,
    round(sum(spend), 2) as spend,
    round(sum(conversion_1), 0) as meta_leads
from daily_adset_insights
group by 1, 2
order by date_start, audience
