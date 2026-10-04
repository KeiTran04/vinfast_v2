
    
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  



select
    1
from `vinfast`.`mart_charging_analytics`

where not(ended_at > started_at)


  
  
    ) dbt_internal_test