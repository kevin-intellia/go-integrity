with by_audience as (
    select
        adset_name as audience,
        sum(impressions) as impressions,
        sum(link_clicks) as landing_page_clicks,
        round(sum(conversion_1), 0) as learn_more_forms,
        round(sum(conversion_2), 0) as showing_requests
    from daily_adset_insights
    group by 1
),
audience_rows as (
    select
        audience,
        impressions,
        landing_page_clicks,
        learn_more_forms,
        showing_requests,
        round(100.0 * impressions / nullif(sum(impressions) over (), 0), 2) as impressions_share_pct,
        round(100.0 * landing_page_clicks / nullif(impressions, 0), 2) as landing_page_clicks_pct,
        round(100.0 * learn_more_forms / nullif(landing_page_clicks, 0), 2) as learn_more_forms_pct,
        round(100.0 * showing_requests / nullif(learn_more_forms, 0), 2) as showing_requests_pct,
        0 as sort_order
    from by_audience
),
total_row as (
    select
        'Total' as audience,
        sum(impressions) as impressions,
        sum(landing_page_clicks) as landing_page_clicks,
        sum(learn_more_forms) as learn_more_forms,
        sum(showing_requests) as showing_requests,
        100.0 as impressions_share_pct,
        round(100.0 * sum(landing_page_clicks) / nullif(sum(impressions), 0), 2) as landing_page_clicks_pct,
        round(100.0 * sum(learn_more_forms) / nullif(sum(landing_page_clicks), 0), 2) as learn_more_forms_pct,
        round(100.0 * sum(showing_requests) / nullif(sum(learn_more_forms), 0), 2) as showing_requests_pct,
        1 as sort_order
    from by_audience
)
select
    audience,
    impressions,
    impressions_share_pct,
    landing_page_clicks,
    landing_page_clicks_pct,
    learn_more_forms,
    learn_more_forms_pct,
    showing_requests,
    showing_requests_pct
from (
    select * from audience_rows
    union all
    select * from total_row
) combined
order by sort_order, audience
