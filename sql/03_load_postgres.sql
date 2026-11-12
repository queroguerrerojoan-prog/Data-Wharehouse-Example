-- Load the CSVs into PostgreSQL (run from the project root with psql):
--   createdb cereal_dwh
--   psql -d cereal_dwh -f sql/01_schema.sql
--   psql -d cereal_dwh -f sql/03_load_postgres.sql
-- Dimensions first, facts last, so foreign keys are satisfied.

\copy dim_date           FROM 'data/dim_date.csv'           CSV HEADER
\copy dim_manufacturer   FROM 'data/dim_manufacturer.csv'   CSV HEADER
\copy dim_brand          FROM 'data/dim_brand.csv'          CSV HEADER
\copy dim_product        FROM 'data/dim_product.csv'        CSV HEADER
\copy dim_retailer       FROM 'data/dim_retailer.csv'       CSV HEADER
\copy dim_region         FROM 'data/dim_region.csv'         CSV HEADER
\copy dim_tv_channel     FROM 'data/dim_tv_channel.csv'     CSV HEADER
\copy dim_daypart        FROM 'data/dim_daypart.csv'        CSV HEADER
\copy dim_target         FROM 'data/dim_target.csv'         CSV HEADER
\copy dim_media_type     FROM 'data/dim_media_type.csv'     CSV HEADER
\copy dim_campaign       FROM 'data/dim_campaign.csv'       CSV HEADER
\copy fact_tv_audience   FROM 'data/fact_tv_audience.csv'   CSV HEADER
\copy fact_ad_investment FROM 'data/fact_ad_investment.csv' CSV HEADER
\copy fact_sales         FROM 'data/fact_sales.csv'         CSV HEADER
