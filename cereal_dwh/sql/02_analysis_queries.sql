-- =====================================================================
-- EXAMPLE ANALYSIS QUERIES  (PostgreSQL / DuckDB)
-- Each one answers a business question a data analyst would get.
-- =====================================================================

-- Q1. Market share by brand and year (value and volume)
SELECT
    d.year,
    b.brand_name,
    SUM(s.revenue_eur)                                             AS revenue_eur,
    ROUND(100.0 * SUM(s.revenue_eur)
          / SUM(SUM(s.revenue_eur)) OVER (PARTITION BY d.year), 1) AS value_share_pct,
    ROUND(100.0 * SUM(s.units_sold)
          / SUM(SUM(s.units_sold))  OVER (PARTITION BY d.year), 1) AS volume_share_pct
FROM fact_sales s
JOIN dim_date    d ON d.date_key   = s.week_date_key
JOIN dim_product p ON p.product_id = s.product_id
JOIN dim_brand   b ON b.brand_id   = p.brand_id
GROUP BY d.year, b.brand_name
ORDER BY d.year, revenue_eur DESC;


-- Q2. Share of Voice (SOV) vs Share of Market (SOM) in 2025
--     Brands with SOV > SOM are usually investing to grow.
WITH spend AS (
    SELECT i.brand_id, SUM(i.spend_eur) AS spend
    FROM fact_ad_investment i
    JOIN dim_date d ON d.date_key = i.week_date_key
    WHERE d.year = 2025
    GROUP BY i.brand_id
), sales AS (
    SELECT p.brand_id, SUM(s.revenue_eur) AS revenue
    FROM fact_sales s
    JOIN dim_date d    ON d.date_key   = s.week_date_key
    JOIN dim_product p ON p.product_id = s.product_id
    WHERE d.year = 2025
    GROUP BY p.brand_id
)
SELECT
    b.brand_name,
    ROUND(100.0 * sp.spend   / SUM(sp.spend)   OVER (), 1) AS sov_pct,
    ROUND(100.0 * sa.revenue / SUM(sa.revenue) OVER (), 1) AS som_pct,
    ROUND(100.0 * sp.spend   / SUM(sp.spend)   OVER ()
        - 100.0 * sa.revenue / SUM(sa.revenue) OVER (), 1) AS excess_sov_pts
FROM spend sp
JOIN sales sa  USING (brand_id)
JOIN dim_brand b USING (brand_id)
ORDER BY excess_sov_pts DESC;


-- Q3. Media mix: how each brand splits its budget across media
SELECT
    b.brand_name,
    m.media_type,
    SUM(i.spend_eur) AS spend_eur,
    ROUND(100.0 * SUM(i.spend_eur)
          / SUM(SUM(i.spend_eur)) OVER (PARTITION BY b.brand_name), 1) AS pct_of_brand
FROM fact_ad_investment i
JOIN dim_brand      b ON b.brand_id      = i.brand_id
JOIN dim_media_type m ON m.media_type_id = i.media_type_id
GROUP BY b.brand_name, m.media_type
ORDER BY b.brand_name, spend_eur DESC;


-- Q4. TV efficiency: cost per GRP and cost per thousand (CPM) by channel
SELECT
    c.channel_name,
    c.channel_type,
    COUNT(*)                                             AS spots,
    ROUND(SUM(t.grp), 0)                                 AS total_grps,
    ROUND(SUM(t.spot_cost_eur) / SUM(t.grp), 0)          AS cost_per_grp_eur,
    ROUND(SUM(t.spot_cost_eur) / SUM(t.impressions_000), 2) AS cpm_eur
FROM fact_tv_audience t
JOIN dim_tv_channel c ON c.channel_id = t.channel_id
GROUP BY c.channel_name, c.channel_type
ORDER BY cpm_eur;


-- Q5. Best dayparts for kids brands (GRPs delivered per spot)
SELECT
    dp.daypart_name,
    COUNT(*)                     AS spots,
    ROUND(AVG(t.grp), 2)         AS avg_grp_per_spot,
    ROUND(AVG(t.spot_cost_eur))  AS avg_spot_cost_eur
FROM fact_tv_audience t
JOIN dim_brand   b  ON b.brand_id   = t.brand_id
JOIN dim_daypart dp ON dp.daypart_id = t.daypart_id
WHERE b.segment = 'Kids'
GROUP BY dp.daypart_name, dp.daypart_id
ORDER BY dp.daypart_id;


-- Q6. Weekly TV pressure vs sales: one row per brand-week.
--     Export this to Python / Power BI to chart or model ad effects.
WITH tv AS (
    SELECT t.brand_id, d.week_start, SUM(t.grp) AS grps, SUM(t.spot_cost_eur) AS tv_spend
    FROM fact_tv_audience t
    JOIN dim_date d ON d.date_key = t.date_key
    GROUP BY t.brand_id, d.week_start
), sales AS (
    SELECT p.brand_id, d.full_date AS week_start,
           SUM(s.units_sold) AS units, SUM(s.revenue_eur) AS revenue
    FROM fact_sales s
    JOIN dim_date d    ON d.date_key   = s.week_date_key
    JOIN dim_product p ON p.product_id = s.product_id
    GROUP BY p.brand_id, d.full_date
)
SELECT b.brand_name, sa.week_start,
       COALESCE(tv.grps, 0)     AS tv_grps,
       COALESCE(tv.tv_spend, 0) AS tv_spend_eur,
       sa.units, sa.revenue
FROM sales sa
JOIN dim_brand b USING (brand_id)
LEFT JOIN tv ON tv.brand_id = sa.brand_id AND tv.week_start = sa.week_start
ORDER BY b.brand_name, sa.week_start;
