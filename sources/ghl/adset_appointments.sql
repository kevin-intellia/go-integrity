with mapped as (
    select
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
        end as audience
    from opportunities o
    join contacts c on c.id = o.contact_id
    where o.pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c'
),
audience_rows as (
    select audience, count(*) as crm_appointments, 0 as sort_order
    from mapped
    where audience != 'Unattributed'
    group by 1
),
total_row as (
    select 'Total' as audience, count(*) as crm_appointments, 1 as sort_order
    from opportunities
    where pipeline_stage_id = 'e76ef02c-d363-4233-a669-9d6a9468990c'
)
select audience, crm_appointments
from (
    select * from audience_rows
    union all
    select * from total_row
) combined
order by sort_order, audience
