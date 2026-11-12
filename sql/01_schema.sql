-- =====================================================================
-- CEREAL CATEGORY DATA WAREHOUSE  (star schema)
-- Dummy data for 5 fictional cereal brands: TV audiences,
-- advertising investment and retail sales.
-- Written in standard SQL: runs on PostgreSQL and DuckDB as-is.
-- =====================================================================

-- ---------------------------------------------------------------------
-- DIMENSIONS
-- ---------------------------------------------------------------------

-- Calendar: one row per day. week_start lets daily facts roll up to the
-- weekly grain used by investment and sales.
CREATE TABLE dim_date (
    date_key        INTEGER PRIMARY KEY,      -- YYYYMMDD
    full_date       DATE        NOT NULL,
    year            SMALLINT    NOT NULL,
    quarter         SMALLINT    NOT NULL,
    month           SMALLINT    NOT NULL,
    month_name      VARCHAR(10) NOT NULL,
    iso_week        SMALLINT    NOT NULL,
    week_start      DATE        NOT NULL,     -- Monday of that week
    day_of_week     SMALLINT    NOT NULL,     -- 1 = Monday ... 7 = Sunday
    day_name        VARCHAR(10) NOT NULL,
    is_weekend      BOOLEAN     NOT NULL,
    season          VARCHAR(10) NOT NULL      -- Winter / Spring / Summer / Autumn
);

CREATE TABLE dim_manufacturer (
    manufacturer_id   SMALLINT PRIMARY KEY,
    manufacturer_name VARCHAR(60) NOT NULL,
    country           VARCHAR(40) NOT NULL
);

CREATE TABLE dim_brand (
    brand_id        SMALLINT PRIMARY KEY,
    brand_name      VARCHAR(60) NOT NULL,
    manufacturer_id SMALLINT    NOT NULL REFERENCES dim_manufacturer(manufacturer_id),
    segment         VARCHAR(20) NOT NULL,     -- Kids / Family / Health / Adult
    price_tier      VARCHAR(10) NOT NULL,     -- Value / Mainstream / Premium
    main_target_id  SMALLINT    NOT NULL,     -- primary TV buying target
    launch_year     SMALLINT    NOT NULL
);

CREATE TABLE dim_product (
    product_id      INTEGER PRIMARY KEY,
    brand_id        SMALLINT     NOT NULL REFERENCES dim_brand(brand_id),
    sku_code        VARCHAR(20)  NOT NULL UNIQUE,
    product_name    VARCHAR(80)  NOT NULL,
    pack_size_g     SMALLINT     NOT NULL,
    list_price_eur  NUMERIC(6,2) NOT NULL
);

CREATE TABLE dim_retailer (
    retailer_id     SMALLINT PRIMARY KEY,
    retailer_name   VARCHAR(60) NOT NULL,
    channel_type    VARCHAR(20) NOT NULL,     -- Hypermarket / Supermarket / Discounter / Online
    coverage        VARCHAR(20) NOT NULL      -- National / Regional
);

CREATE TABLE dim_region (
    region_id       SMALLINT PRIMARY KEY,
    region_name     VARCHAR(40) NOT NULL,
    population_m    NUMERIC(5,2) NOT NULL
);

CREATE TABLE dim_tv_channel (
    channel_id      SMALLINT PRIMARY KEY,
    channel_name    VARCHAR(40) NOT NULL,
    channel_group   VARCHAR(40) NOT NULL,
    channel_type    VARCHAR(20) NOT NULL      -- Generalist / Kids / Thematic
);

CREATE TABLE dim_daypart (
    daypart_id      SMALLINT PRIMARY KEY,
    daypart_name    VARCHAR(30) NOT NULL,
    start_hour      SMALLINT    NOT NULL,
    end_hour        SMALLINT    NOT NULL
);

-- Audience target the spot was bought / measured against
CREATE TABLE dim_target (
    target_id       SMALLINT PRIMARY KEY,
    target_name     VARCHAR(40) NOT NULL,
    universe_000    INTEGER     NOT NULL      -- people in the target, thousands
);

CREATE TABLE dim_media_type (
    media_type_id   SMALLINT PRIMARY KEY,
    media_type      VARCHAR(30) NOT NULL      -- TV / Digital Video / Social / OOH / Radio
);

CREATE TABLE dim_campaign (
    campaign_id     INTEGER PRIMARY KEY,
    brand_id        SMALLINT     NOT NULL REFERENCES dim_brand(brand_id),
    campaign_name   VARCHAR(80)  NOT NULL,
    objective       VARCHAR(20)  NOT NULL,    -- Awareness / Launch / Promo / Always-on
    start_date      DATE         NOT NULL,
    end_date        DATE         NOT NULL,
    budget_eur      NUMERIC(12,2) NOT NULL
);

-- ---------------------------------------------------------------------
-- FACTS
-- ---------------------------------------------------------------------

-- 1) TV AUDIENCES  -- grain: one row per aired spot
CREATE TABLE fact_tv_audience (
    spot_id           BIGINT PRIMARY KEY,
    date_key          INTEGER  NOT NULL REFERENCES dim_date(date_key),
    brand_id          SMALLINT NOT NULL REFERENCES dim_brand(brand_id),
    campaign_id       INTEGER  NOT NULL REFERENCES dim_campaign(campaign_id),
    channel_id        SMALLINT NOT NULL REFERENCES dim_tv_channel(channel_id),
    daypart_id        SMALLINT NOT NULL REFERENCES dim_daypart(daypart_id),
    target_id         SMALLINT NOT NULL REFERENCES dim_target(target_id),
    air_time          TIME     NOT NULL,
    spot_length_sec   SMALLINT NOT NULL,      -- 10 / 20 / 30
    grp               NUMERIC(6,2) NOT NULL,  -- rating points in the target
    impressions_000   NUMERIC(10,1) NOT NULL, -- grp/100 * target universe
    spot_cost_eur     NUMERIC(10,2) NOT NULL
);

-- 2) ADVERTISING INVESTMENT  -- grain: brand x campaign x media type x week
CREATE TABLE fact_ad_investment (
    investment_id     BIGINT PRIMARY KEY,
    week_date_key     INTEGER  NOT NULL REFERENCES dim_date(date_key),  -- Monday
    brand_id          SMALLINT NOT NULL REFERENCES dim_brand(brand_id),
    campaign_id       INTEGER  NOT NULL REFERENCES dim_campaign(campaign_id),
    media_type_id     SMALLINT NOT NULL REFERENCES dim_media_type(media_type_id),
    spend_eur         NUMERIC(12,2) NOT NULL,
    impressions_000   NUMERIC(12,1) NOT NULL
);

-- 3) SALES  -- grain: product x retailer x region x week (retail panel style)
CREATE TABLE fact_sales (
    sales_id          BIGINT PRIMARY KEY,
    week_date_key     INTEGER  NOT NULL REFERENCES dim_date(date_key),  -- Monday
    product_id        INTEGER  NOT NULL REFERENCES dim_product(product_id),
    retailer_id       SMALLINT NOT NULL REFERENCES dim_retailer(retailer_id),
    region_id         SMALLINT NOT NULL REFERENCES dim_region(region_id),
    units_sold        INTEGER  NOT NULL,
    revenue_eur       NUMERIC(12,2) NOT NULL,
    avg_price_eur     NUMERIC(6,2)  NOT NULL,
    on_promotion      BOOLEAN  NOT NULL,
    numeric_distribution_pct NUMERIC(5,2) NOT NULL  -- % of stores stocking it
);

-- Helpful indexes for the typical joins
CREATE INDEX ix_tv_date_brand    ON fact_tv_audience (date_key, brand_id);
CREATE INDEX ix_inv_week_brand   ON fact_ad_investment (week_date_key, brand_id);
CREATE INDEX ix_sales_week_prod  ON fact_sales (week_date_key, product_id);
