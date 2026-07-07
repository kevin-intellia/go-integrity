select
    (select count(*) from lead_records) as total_leads,
    (
        select count(*)
        from lead_records
        where channel = 'Facebook Ads'
    ) as facebook_ad_leads,
    sum(
        case when o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c' then 1 else 0 end
    ) as appointments_scheduled,
    sum(
        case when c.source ilike '%Private Showing%' then 1 else 0 end
    ) as showings_booked
from opportunities o
join contacts c on c.id = o.contact_id
