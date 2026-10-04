
    
    

with all_values as (

    select
        lifecycle_stage as value_field,
        count(*) as n_records

    from `vinfast`.`mart_customer_360`
    group by lifecycle_stage

)

select *
from all_values
where value_field not in (
    'lead','prospect_warm','prospect_hot','customer'
)


