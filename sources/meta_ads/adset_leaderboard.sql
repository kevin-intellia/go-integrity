with by_adset as (
    select
        adset_name as audience,
        sum(spend) as spend,
        round(sum(conversion_1), 0) as meta_leads,
        round(sum(spend) / nullif(sum(conversion_1), 0), 2) as cpl_meta
    from daily_adset_insights
    group by 1
    having sum(spend) > 0
)
select
    audience,
    round(spend, 2) as spend,
    meta_leads,
    cpl_meta
from by_adset
order by cpl_meta asc
limit 1
