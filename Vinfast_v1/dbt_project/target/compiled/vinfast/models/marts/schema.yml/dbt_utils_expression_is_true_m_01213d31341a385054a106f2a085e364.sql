



select
    1
from `vinfast`.`mart_charging_analytics`

where not(end_soc_pct >= start_soc_pct)

