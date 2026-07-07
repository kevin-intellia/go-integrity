select
    count(*) as total_leads,
    sum(
        case when c.utm_source = 'facebook' and c.utm_medium = 'cpc' then 1 else 0 end
    ) as facebook_ad_leads,
    sum(
        case when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1 else 0 end
    ) as appointments_scheduled,
    sum(
        case when c.source ilike '%Private Showing%' then 1 else 0 end
    ) as showings_booked
from opportunities o
join contacts c on c.id = o.contact_id
