with daily as (
    select
        cast(date_added as date) as lead_date,
        count(*) as daily_leads
    from contacts
    where utm_source = 'facebook' and utm_medium = 'cpc'
    group by 1
),
date_span as (
    select unnest(
        generate_series(
            (select min(lead_date) from daily),
            (select max(lead_date) from daily),
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
