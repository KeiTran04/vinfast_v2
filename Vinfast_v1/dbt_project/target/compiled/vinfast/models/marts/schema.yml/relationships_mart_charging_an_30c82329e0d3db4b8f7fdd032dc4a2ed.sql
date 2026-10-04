
    
    

with child as (
    select vehicle_id as from_field
    from `vinfast`.`mart_charging_analytics`
    where vehicle_id is not null
),

parent as (
    select vehicle_id as to_field
    from `vinfast`.`mart_vehicle_360`
)

select
    from_field

from child
left join parent
    on child.from_field = parent.to_field

where parent.to_field is null
-- end_of_sql
settings join_use_nulls = 1


