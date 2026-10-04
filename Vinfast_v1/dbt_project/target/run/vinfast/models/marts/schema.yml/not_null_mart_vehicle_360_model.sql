
    
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select model
from `vinfast`.`mart_vehicle_360`
where model is null



  
  
    ) dbt_internal_test