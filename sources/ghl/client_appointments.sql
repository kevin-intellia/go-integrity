select
    case
        when c.first_name is not null
            and c.last_name is not null
            and lower(trim(c.first_name)) = lower(trim(c.last_name))
            then trim(c.first_name)
        when nullif(trim(concat(coalesce(c.first_name, ''), ' ', coalesce(c.last_name, ''))), '') is not null
            then trim(concat(coalesce(c.first_name, ''), ' ', coalesce(c.last_name, '')))
        else coalesce(c.contact_name, 'Unknown')
    end as name,
    case
        when c.utm_source = 'facebook' and c.utm_medium = 'cpc' then 'Facebook Ad'
        when c.utm_source ilike '%facebook%' then 'Facebook'
        when c.utm_source ilike '%email%' or c.session_source ilike '%email%' then 'Email'
        when c.utm_source is null and c.utm_medium is null then 'Other'
        else coalesce(c.utm_source, 'Other')
    end as channel,
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
        else 'Requested'
    end as status,
    case
        when c.source ilike '%Private Showing%' then 'Private Showing form'
        when c.source ilike '%Optin%' or c.source ilike '%optin%' then 'Learn More form'
        else coalesce(c.source, 'Unknown form')
    end as entry_point,
    cast(c.date_added as date) as date_added
from opportunities o
join contacts c on c.id = o.contact_id
where o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c'
order by
    case when c.source ilike '%Private Showing%' then 0 else 1 end,
    c.date_added desc
