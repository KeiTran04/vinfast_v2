
    
    

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


