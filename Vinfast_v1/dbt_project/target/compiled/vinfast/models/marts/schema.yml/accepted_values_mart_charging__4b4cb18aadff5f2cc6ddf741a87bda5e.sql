
    
    

with all_values as (

    select
        charger_type as value_field,
        count(*) as n_records

    from `vinfast`.`mart_charging_analytics`
    group by charger_type

)

select *
from all_values
where value_field not in (
    'AC_TYPE2','CCS2_DC'
)


