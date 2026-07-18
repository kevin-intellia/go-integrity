create or replace view lead_records as
select
    o.id as opportunity_id,
    o.contact_id,
    cast(coalesce(c.date_added, o.created_at) as date) as lead_date,
    o.source as opportunity_source,
    c.source as contact_source,
    c.utm_source,
    c.utm_medium,
    c.session_source,
    case
        when lower(coalesce(c.utm_source, '')) in ('facebook', 'fb') then 'Facebook'
        when c.session_source = 'Paid Social' then 'Facebook'
        when c.utm_medium = 'email'
            or lower(coalesce(c.utm_source, '')) ilike '%email%'
            or lower(coalesce(c.utm_source, '')) in ('sevendays', 'seven days email newsletters') then 'Email'
        when c.utm_medium = 'print'
            or lower(coalesce(c.utm_source, '')) in (
                'robb_report', 'stowereporter', 'propertyblast', 'wsj', 'print'
            ) then 'Print'
        when o.source in ('Integrity Website Inquires', 'Integrity Website Inquiries') then 'Integrity Website'
        when o.source = 'Listing Realtor Referral Leads' then 'Realtor Referral'
        when o.source in ('Realtors', 'Realors') then 'Realtors'
        when o.source = 'FB Community/Marketplace Ad' then 'Facebook Marketplace'
        when c.utm_source is null or trim(c.utm_source) = '' then
            case
                when c.session_source = 'Direct traffic' then 'No Campaign Tag'
                when c.session_source = 'Social media' then 'Social'
                when c.session_source = 'Organic Search' then 'Organic Search'
                when c.session_source = 'Referral' then 'Referral'
                when c.session_source = 'Paid Social' then 'Facebook'
                when coalesce(c.source, o.source) ilike '%optin%'
                    or coalesce(c.source, o.source) ilike '%funnel leads%' then
                    case c.session_source
                        when 'Paid Social' then 'Facebook'
                        when 'Social media' then 'Social'
                        when 'Organic Search' then 'Organic Search'
                        when 'Referral' then 'Referral'
                        when 'Direct traffic' then 'No Campaign Tag'
                        else 'Website'
                    end
                when o.source is not null
                    and trim(o.source) != ''
                    and o.source not ilike '%optin%'
                    and o.source not ilike '%funnel leads%' then o.source
                else 'Untracked (no UTM)'
            end
        else 'Other campaigns'
    end as channel,
    case
        when coalesce(nullif(trim(c.source), ''), nullif(trim(o.source), '')) ilike '%website lead%'
            or o.source in ('Integrity Website Inquires', 'Integrity Website Inquiries')
            or coalesce(c.source, o.source) ilike '%website%inquir%'
            then 'Website'
        when coalesce(c.source, o.source) ilike '%funnel%'
            or coalesce(c.source, o.source) ilike '%optin%'
            or coalesce(c.source, o.source) ilike '%private showing%'
            or coalesce(c.source, o.source) ilike '%call request%'
            then 'Funnel'
        else null
    end as lead_form
from opportunities o
join contacts c on c.id = o.contact_id
where not (
    lower(coalesce(c.email, '')) in ('test@test.com', 'test@gmail.com')
    or lower(coalesce(c.email, '')) like '%intelliadigital.com'
    or lower(trim(coalesce(c.first_name, ''))) in ('test', 'test 1')
    or lower(trim(coalesce(c.last_name, ''))) = 'test'
)
