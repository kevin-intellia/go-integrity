select stage, leads
from (
    select
        case o.pipeline_stage_id
            when '3a5e7711-ba66-41bd-9ba7-eb3bdcb35efe' then 'New Lead'
            when 'e76ef02c-d363-4233-a669-9d6a9468990c' then 'Appointment Scheduled'
            when '108fe0e2-80bd-4c0b-85a0-1e8a0603b52c' then 'Registered for Auction'
            else 'Other'
        end as stage,
        count(*) as leads
    from opportunities o
    group by 1
) t
order by
    case stage
        when 'New Lead' then 1
        when 'Appointment Scheduled' then 2
        when 'Registered for Auction' then 3
        else 4
    end
