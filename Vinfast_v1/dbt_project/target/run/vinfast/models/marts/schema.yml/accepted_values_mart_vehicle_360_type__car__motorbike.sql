
    
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

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



  
  
    ) dbt_internal_test