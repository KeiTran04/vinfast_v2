
    
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select session_id
from `vinfast`.`mart_charging_analytics`
where session_id is null



  
  
    ) dbt_internal_test