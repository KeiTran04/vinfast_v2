
    
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  



select
    1
from `vinfast`.`mart_charging_analytics`

where not(end_soc_pct >= start_soc_pct)


  
  
    ) dbt_internal_test