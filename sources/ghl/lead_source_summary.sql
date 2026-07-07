select
    coalesce(nullif(trim(source), ''), '-') as source,
    count(*) as total_leads,
    sum(case when lower(status) = 'open' then 1 else 0 end) as open_count,
    sum(case when lower(status) = 'won' then 1 else 0 end) as won_count,
    sum(case when lower(status) = 'lost' then 1 else 0 end) as lost_count,
    sum(case when lower(status) = 'abandoned' then 1 else 0 end) as abandoned_count,
    round(
        100.0 * sum(case when lower(status) = 'won' then 1 else 0 end) / nullif(count(*), 0),
        2
    ) as win_pct
from opportunities
group by 1
order by total_leads desc
