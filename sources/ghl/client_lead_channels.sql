select
    case
        when utm_source = 'facebook' and utm_medium = 'cpc' then 'Facebook Ads'
        when utm_medium = 'email' or utm_source ilike '%email%' then 'Email'
        when utm_medium = 'print' then 'Print'
        when utm_source is null or trim(utm_source) = '' then
            case
                when session_source = 'Direct traffic' then 'No Campaign Tag'
                when session_source = 'Social media' then 'Social'
                when session_source = 'Organic Search' then 'Organic Search'
                else 'Untracked (no UTM)'
            end
        else coalesce(utm_source, 'Other')
    end as channel,
    count(*) as leads
from contacts
group by 1
order by leads desc
