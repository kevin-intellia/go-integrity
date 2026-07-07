select
    id,
    contact_name,
    email,
    phone,
    source,
    type,
    date_added,
    utm_source,
    utm_medium,
    utm_campaign,
    utm_content,
    utm_term,
    device_type,
    referrer,
    page_url,
    session_source,
    tags
from contacts
order by date_added desc
