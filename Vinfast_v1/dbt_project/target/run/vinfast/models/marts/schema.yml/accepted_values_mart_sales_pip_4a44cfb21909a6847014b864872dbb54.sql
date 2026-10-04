
    
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        city_code as value_field,
        count(*) as n_records

    from `vinfast`.`mart_sales_pipeline`
    group by city_code

)

select *
from all_values
where value_field not in (
    'HN','SG','DN','TH','TN','NA','HT','QN'
)



  
  
    ) dbt_internal_test