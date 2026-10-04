
    
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        charger_type as value_field,
        count(*) as n_records

    from `vinfast`.`mart_charging_revenue`
    group by charger_type

)

select *
from all_values
where value_field not in (
    'AC_TYPE2','CCS2_DC'
)



  
  
    ) dbt_internal_test