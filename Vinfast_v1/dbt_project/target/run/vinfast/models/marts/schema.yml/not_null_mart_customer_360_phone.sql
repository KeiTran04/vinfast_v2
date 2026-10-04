
    
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select phone
from `vinfast`.`mart_customer_360`
where phone is null



  
  
    ) dbt_internal_test