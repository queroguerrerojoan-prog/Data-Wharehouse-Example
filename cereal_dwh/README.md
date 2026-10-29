# Cereal Category Data Warehouse

I built a data warehouse for a group of cereal brands that wanted to combine data from different sources into a single source of truth for **sales, audiences and investment**. All brand names and figures are anonymized: the dataset is synthetic but reproduces realistic market behaviour.

| Source | Content |
|---|---|
| **TV audiences** | Every aired spot with channel, daypart, target, GRPs, impressions and cost |
| **Advertising investment** | Weekly spend by brand, campaign and media type (TV, digital video, social, OOH, radio) |
| **Sales** | Weekly retail sales by product, retailer and region, with price, promotions and distribution |

The data is synthetic but internally consistent. TV investment equals the sum of spot costs. Sales respond to TV pressure (adstock with diminishing returns), seasonality, promotions and price. As a result, the analyses return realistic patterns.

## Brands

| Brand | Manufacturer | Segment | Price tier | Main TV target |
|---|---|---|---|---|
| Brand A | Granja Foods | Kids | Mainstream | Kids 4-12 |
| Brand B | Nordic Cereals Co. | Family | Mainstream | Shoppers 25-54 |
| Brand C | Mediterránea de Alimentación | Health | Premium | Adults 25-54 |
| Brand D | Granja Foods | Kids | Value | Kids 4-12 |
| Brand E | Nordic Cereals Co. | Adult | Premium | Adults 35-64 |

## Data model

| Fact table | Grain | Rows |
|---|---|---|
| `fact_tv_audience` | One aired spot | ~28,000 |
| `fact_ad_investment` | Brand × campaign × media type × week | ~1,100 |
| `fact_sales` | Product × retailer × region × week | ~53,600 |

`dim_brand` and `dim_date` are **conformed dimensions** shared by all three fact tables, which is what lets you compare audiences, investment and sales side by side. Daily TV data rolls up to the weekly grain through `dim_date.week_start`.

## Project structure

```
cereal_dwh/
├── sql/
│   ├── 01_schema.sql            # DDL (PostgreSQL & DuckDB compatible)
│   ├── 02_analysis_queries.sql  # 6 business questions answered in SQL
│   └── 03_load_postgres.sql     # \copy commands to load the CSVs
├── scripts/
│   └── generate_data.py         # Builds the synthetic data (seeded, reproducible)
└── data/
    ├── *.csv                    # One file per table
    └── cereal_dwh.duckdb        # Ready-to-query database
```

## How the tables connect

The warehouse is a star schema: 3 fact tables hold the measures, and 11 dimension tables describe them. Data covers 1 Jan 2024 to 28 Dec 2025.

### Join paths

**`fact_sales`** (product × retailer × region × week)
```
week_date_key → dim_date.date_key
retailer_id   → dim_retailer.retailer_id
region_id     → dim_region.region_id
product_id    → dim_product.product_id → dim_brand.brand_id → dim_manufacturer.manufacturer_id
```
Sales has no `brand_id`: to analyse by brand, always join through `dim_product`.

**`fact_ad_investment`** (brand × campaign × media type × week)
```
week_date_key → dim_date.date_key
brand_id      → dim_brand.brand_id
campaign_id   → dim_campaign.campaign_id
media_type_id → dim_media_type.media_type_id
```

**`fact_tv_audience`** (one aired spot)
```
date_key    → dim_date.date_key   (daily)
brand_id    → dim_brand.brand_id
campaign_id → dim_campaign.campaign_id
channel_id  → dim_tv_channel.channel_id
daypart_id  → dim_daypart.daypart_id
target_id   → dim_target.target_id
```

**Between dimensions**
```
dim_brand.manufacturer_id → dim_manufacturer.manufacturer_id
dim_brand.main_target_id  → dim_target.target_id
dim_product.brand_id      → dim_brand.brand_id
dim_campaign.brand_id     → dim_brand.brand_id
```

### Combining sources

`dim_brand` and `dim_date` are shared by all three fact tables. To compare sales, investment and TV, aggregate each fact table separately by brand and period (for example in CTEs), then join the results on `brand_id` and the period.

Sales and investment are weekly: `week_date_key` is always the Monday of the week. TV is daily, so group it by `dim_date.week_start` to line it up with the weekly tables.

## Business questions answered

The queries in `02_analysis_queries.sql` answer:

1. Market share by brand and year (value and volume)
2. Share of Voice vs Share of Market
3. Media mix by brand
4. TV efficiency: cost per GRP and CPM by channel
5. Best dayparts for kids brands
6. Weekly TV pressure vs sales (dataset for charts or modelling)

---

*All brands, manufacturers, retailers and figures are fictional.*
