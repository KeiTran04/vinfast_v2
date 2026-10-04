
    
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select dealer_id
from `vinfast`.`mart_sales_pipeline`
where dealer_id is null



  
  
    ) dbt_internal_test