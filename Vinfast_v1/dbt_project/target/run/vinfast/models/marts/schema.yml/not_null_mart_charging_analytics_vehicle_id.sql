
    
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select vehicle_id
from `vinfast`.`mart_charging_analytics`
where vehicle_id is null



  
  
    ) dbt_internal_test