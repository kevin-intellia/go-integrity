with totals as (
    select
        round(100.0 * sum(link_clicks) / nullif(sum(impressions), 0), 2) as overall_ctr
    from daily_campaign_insights
),
by_audience as (
    select
        adset_name as audience,
        round(100.0 * sum(link_clicks) / nullif(sum(impressions), 0), 2) as ctr
    from daily_adset_insights
    group by 1
),
best as (
    select audience, ctr
    from by_audience
    order by ctr desc
    limit 1
)
select
    t.overall_ctr,
    b.audience as top_audience,
    b.ctr as top_audience_ctr,
    3.0 as industry_ctr_avg,
    round(b.ctr / 3.0, 1) as top_audience_vs_benchmark
from totals t
cross join best b
