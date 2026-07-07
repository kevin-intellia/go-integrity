select
    channel,
    count(*) as leads
from lead_records
group by 1
order by leads desc
