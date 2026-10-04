



select
    1
from `vinfast`.`mart_charging_analytics`

where not(ended_at > started_at)

