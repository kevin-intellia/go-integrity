select
    o.id as opportunity_id,
    o.contact_id,
    case
        when c.first_name is not null
            and c.last_name is not null
            and lower(trim(c.first_name)) = lower(trim(c.last_name))
            then trim(c.first_name)
        when nullif(trim(concat(coalesce(c.first_name, ''), ' ', coalesce(c.last_name, ''))), '') is not null
            then trim(concat(coalesce(c.first_name, ''), ' ', coalesce(c.last_name, '')))
        else coalesce(c.contact_name, 'Unknown')
    end as contact_name,
    c.first_name,
    c.last_name,
    c.email,
    c.phone,
    cast(coalesce(c.date_added, o.created_at) as date) as lead_date,
    lr.channel,
    case c.utm_term
        when '120250101870600306' then 'VT & NH'
        when '120250101883590306' then 'VT & NH'
        when '120250093236920306' then 'NYC 15 Miles'
        when '120250091197620306' then 'NYC 15 Miles'
        when '120250093748420306' then 'Westchester / Hudson Valley'
        when '120250091788420306' then 'Westchester / Hudson Valley'
        when '120250091674470306' then 'Long Island Gold Coast/Hamptons'
        when '120250093766560306' then 'Long Island Gold Coast/Hamptons'
        when '120250093727620306' then 'NJ Shore'
        when '120250091847730306' then 'NJ Shore'
        when '120250091623250306' then 'Connecticut Gold Coast'
        when '120250093630920306' then 'Connecticut Gold Coast'
        else 'Unattributed'
    end as audience,
    case
        when c.source ilike '%Private Showing%' then 'Showing Booked'
        else 'Showing Requested'
    end as showing_status,
    case
        when c.source ilike '%Private Showing%' then 'Private Showing form'
        when c.source ilike '%Optin%' or c.source ilike '%optin%' then 'Learn More form'
        else coalesce(c.source, 'Unknown form')
    end as entry_point,
    c.source as contact_source,
    c.type as contact_type,
    cast(c.date_added as date) as contact_date_added,
    cast(c.date_updated as date) as contact_date_updated,
    c.tags,
    c.utm_source,
    c.utm_medium,
    c.utm_campaign,
    c.utm_content,
    c.utm_term,
    c.utm_keyword,
    c.device_type,
    c.session_source,
    c.referrer,
    c.page_url,
    c.user_agent,
    o.name as opportunity_name,
    o.status as opportunity_status,
    o.source as opportunity_source,
    o.monetary_value,
    cast(o.created_at as date) as opportunity_created,
    cast(o.updated_at as date) as opportunity_updated,
    cast(o.last_status_change_at as date) as last_status_change,
    o.pipeline_id,
    o.pipeline_stage_id,
    o.utm_source as opp_utm_source,
    o.utm_medium as opp_utm_medium,
    o.utm_campaign as opp_utm_campaign,
    o.utm_content as opp_utm_content,
    o.utm_term as opp_utm_term,
    o.utm_keyword as opp_utm_keyword
from ghl.opportunities o
join ghl.contacts c on c.id = o.contact_id
join lead_records lr on lr.opportunity_id = o.id
where o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c'
order by
    case when c.source ilike '%Private Showing%' then 0 else 1 end,
    lead_date desc
