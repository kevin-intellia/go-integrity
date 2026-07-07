select
    device_type,
    case
        when utm_campaign is not null and utm_campaign != '' then 'has utm'
        else 'no utm'
    end as utm_status,
    session_source,
    case
        when referrer ilike '%m.facebook.com%' then 'facebook_mobile'
        when referrer ilike '%facebook.com%' or referrer ilike '%l.facebook.com%' then 'facebook'
        when referrer ilike '%instagram.com%' then 'instagram'
        when referrer is null or referrer = '' then '(none)'
        else 'other'
    end as referrer_group,
    count(*) as leads
from contacts
group by 1, 2, 3, 4
order by leads desc
