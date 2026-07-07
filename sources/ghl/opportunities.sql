select
    id,
    name,
    contact_id,
    pipeline_stage_id,
    status,
    source,
    monetary_value,
    created_at,
    updated_at,
    utm_source,
    utm_medium,
    utm_campaign,
    utm_content,
    utm_term
from opportunities
order by created_at desc
