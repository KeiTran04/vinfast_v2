
    
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

select
    dealer_id as unique_field,
    count(*) as n_records

from `vinfast`.`mart_sales_pipeline`
where dealer_id is not null
group by dealer_id
having count(*) > 1



  
  
    ) dbt_internal_test