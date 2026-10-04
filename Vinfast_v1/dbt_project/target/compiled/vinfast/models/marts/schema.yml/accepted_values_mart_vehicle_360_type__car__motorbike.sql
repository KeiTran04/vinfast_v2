
    
    

with all_values as (

    select
        type as value_field,
        count(*) as n_records

    from `vinfast`.`mart_vehicle_360`
    group by type

)

select *
from all_values
where value_field not in (
    'car','motorbike'
)


