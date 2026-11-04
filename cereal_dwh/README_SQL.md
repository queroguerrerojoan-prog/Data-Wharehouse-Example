# Cereal Category Data Warehouse

I built a data warehouse in **PostgreSQL** for a group of cereal brands. They wanted to combine data from different sources into a single source of truth for **sales, audiences and investment**. All brand names and figures are anonymized: the dataset is synthetic but reproduces realistic market behaviour.

| Source | Content |
|---|---|
| **TV audiences** | Every aired spot with channel, daypart, target, GRPs, impressions and cost |
| **Advertising investment** | Weekly spend by brand, campaign and media type (TV, digital video, social, OOH, radio) |
| **Sales** | Weekly retail sales by product, retailer and region, with price, promotions and distribution |

The data is internally consistent. TV investment equals the sum of spot costs. Sales respond to TV pressure (adstock with diminishing returns), seasonality, promotions and price. As a result, the analyses return realistic patterns.

## Brands

| Brand | Manufacturer | Segment | Price tier | Main TV target |
|---|---|---|---|---|
| Brand A | Manufacturer 1 | Kids | Mainstream | Kids 4-12 |
| Brand B | Manufacturer 2 | Family | Mainstream | Shoppers 25-54 |
| Brand C | Manufacturer 3 | Health | Premium | Adults 25-54 |
| Brand D | Manufacturer 1 | Kids | Value | Kids 4-12 |
| Brand E | Manufacturer 2 | Adult | Premium | Adults 35-64 |

## Data model

The warehouse is a **star schema**: 3 fact tables hold the measures and 11 dimension tables describe them. The data covers 1 January 2024 to 28 December 2025.

| Fact table | Grain | Rows |
|---|---|---|
| `fact_tv_audience` | One aired spot | ~28,000 |
| `fact_ad_investment` | Brand × campaign × media type × week | ~1,100 |
| `fact_sales` | Product × retailer × region × week | ~53,600 |

**Dimensions:** `dim_date`, `dim_brand`, `dim_manufacturer`, `dim_product`, `dim_retailer`, `dim_region`, `dim_campaign`, `dim_media_type`, `dim_tv_channel`, `dim_daypart`, `dim_target`.

### Join paths

```
fact_sales          week_date_key → dim_date
                    product_id    → dim_product → dim_brand → dim_manufacturer
                    retailer_id   → dim_retailer
                    region_id     → dim_region

fact_ad_investment  week_date_key → dim_date
                    brand_id      → dim_brand
                    campaign_id   → dim_campaign
                    media_type_id → dim_media_type

fact_tv_audience    date_key      → dim_date (daily)
                    brand_id      → dim_brand
                    campaign_id   → dim_campaign
                    channel_id    → dim_tv_channel
                    daypart_id    → dim_daypart
                    target_id     → dim_target
```

- `fact_sales` has no `brand_id`. To analyse sales by brand, always join through `dim_product`.
- `dim_brand` and `dim_date` are **conformed dimensions** shared by all three fact tables. They are what let you compare audiences, investment and sales side by side.
- Sales and investment are weekly, and `week_date_key` is always a Monday. TV is daily, so it rolls up to the weekly grain through `dim_date.week_start`.

## Project structure

```
cereal_dwh/
├── sql/
│   ├── 01_schema.sql            # DDL: creates the tables, keys and indexes
│   ├── 02_analysis_queries.sql  # 6 business questions answered in SQL
│   └── 03_load_postgres.sql     # \copy commands to load the CSVs
├── scripts/
│   └── generate_data.py         # Builds the synthetic data (seeded, reproducible)
└── data/
    └── *.csv                    # One file per table
```

## How to use it

### Option A: terminal (psql)

Run these from the `cereal_dwh` folder, because the load script uses paths relative to it (`data/*.csv`):

```bash
createdb cereal_dwh
psql -d cereal_dwh -f sql/01_schema.sql
psql -d cereal_dwh -f sql/03_load_postgres.sql
```

### Option B: pgAdmin

1. Create a database, then right-click it and choose **PSQL Tool**.
2. Move to the project folder and run the scripts:
   ```
   \cd '/path/to/cereal_dwh'
   \i sql/01_schema.sql
   \i sql/03_load_postgres.sql
   ```
3. Check the load. This query should return **53,604**:
   ```sql
   SELECT COUNT(*) FROM fact_sales;
   ```
4. Open **Query Tool** and run `sql/02_analysis_queries.sql`.

> `\copy` is a psql command, so it doesn't run in pgAdmin's Query Tool. Use the PSQL Tool for loading.

## Business questions answered

| # | Question | Tables used | What it returns |
|---|---|---|---|
| Q1 | **Market share by brand and year** | `fact_sales`, `dim_date`, `dim_product`, `dim_brand` | Revenue per brand and year, with value share (% of revenue) and volume share (% of units) |
| Q2 | **Share of Voice vs Share of Market (2025)** | `fact_ad_investment`, `fact_sales`, `dim_date`, `dim_product`, `dim_brand` | Each brand's share of total ad spend (SOV) and of revenue (SOM), with **excess SOV = SOV − SOM**. Brands with a positive excess are investing to grow. |
| Q3 | **Media mix by brand** | `fact_ad_investment`, `dim_brand`, `dim_media_type` | Spend per brand and media type, and its % of the brand's total budget |
| Q4 | **TV efficiency by channel** | `fact_tv_audience`, `dim_tv_channel` | Spots, GRPs, **cost per GRP** (spot cost ÷ GRPs) and **CPM** (cost per thousand impressions), cheapest first |
| Q5 | **Best dayparts for kids brands** | `fact_tv_audience`, `dim_brand`, `dim_daypart` | Spots, average GRPs per spot and average spot cost per daypart, for the Kids segment |
| Q6 | **Weekly TV pressure vs sales** | `fact_tv_audience`, `fact_sales`, `dim_date`, `dim_product`, `dim_brand` | One row per brand and week with TV GRPs, TV spend, units and revenue. It's ready to export to Power BI or to use for modelling. |



