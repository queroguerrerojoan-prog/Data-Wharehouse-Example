"""
Generate dummy data for the cereal-category data warehouse and load it.

Outputs
  data/*.csv           one CSV per table (to load into PostgreSQL, Power BI, etc.)
  data/cereal_dwh.duckdb   ready-to-query DuckDB database built from sql/01_schema.sql

The numbers are fake but internally consistent:
  * TV spend in fact_ad_investment = sum of spot costs in fact_tv_audience
  * Sales respond to TV pressure (adstock with diminishing returns),
    seasonality, promotions and price -> so the analysis queries return
    meaningful patterns.

Run:  python scripts/generate_data.py
"""
from pathlib import Path
import numpy as np
import pandas as pd
import duckdb

SEED = 42
START, END = "2024-01-01", "2025-12-28"   # 104 full Monday-start weeks
rng = np.random.default_rng(SEED)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

# ---------------------------------------------------------------------
# Static dimensions
# ---------------------------------------------------------------------
dim_manufacturer = pd.DataFrame([
    (1, "Granja Foods", "Spain"),
    (2, "Nordic Cereals Co.", "Sweden"),
    (3, "Mediterránea de Alimentación", "Spain"),
], columns=["manufacturer_id", "manufacturer_name", "country"])

dim_target = pd.DataFrame([
    (1, "Individuals 4+",  46200),
    (2, "Adults 25-54",    20500),
    (3, "Kids 4-12",        4300),
    (4, "Shoppers 25-54",  11000),
    (5, "Adults 35-64",    19600),
], columns=["target_id", "target_name", "universe_000"])

# brand_id, name, manufacturer, segment, tier, main target, launch,
# base weekly units (national), TV effect strength, half-saturation GRPs
BRANDS = [
    (1, "ChocoPlanet",        1, "Kids",   "Mainstream", 3, 2008, 210_000, 0.22, 180),
    (2, "Crispy Valley",      2, "Family", "Mainstream", 4, 1996, 260_000, 0.12, 220),
    (3, "FiberFit",           3, "Health", "Premium",    2, 2015, 120_000, 0.18, 200),
    (4, "Golden Honey Rings", 1, "Kids",   "Value",      3, 2001, 150_000, 0.15, 160),
    (5, "Muesli Alpino",      2, "Adult",  "Premium",    5, 2019,  70_000, 0.25, 150),
]
dim_brand = pd.DataFrame(
    [b[:7] for b in BRANDS],
    columns=["brand_id", "brand_name", "manufacturer_id", "segment",
             "price_tier", "main_target_id", "launch_year"])
brand_params = {b[0]: dict(base=b[7], beta=b[8], half_sat=b[9]) for b in BRANDS}

# product_id, brand_id, sku, name, grams, price, share of brand volume
PRODUCTS = [
    (101, 1, "CHP-375", "ChocoPlanet Original 375g",        375, 2.95, 0.55),
    (102, 1, "CHP-750", "ChocoPlanet Original 750g",        750, 4.99, 0.25),
    (103, 1, "CHP-WHT", "ChocoPlanet White Choco 375g",     375, 3.15, 0.20),
    (201, 2, "CRV-500", "Crispy Valley Corn Flakes 500g",   500, 2.49, 0.50),
    (202, 2, "CRV-1KG", "Crispy Valley Corn Flakes 1kg",   1000, 4.29, 0.30),
    (203, 2, "CRV-HNY", "Crispy Valley Honey Flakes 500g",  500, 2.79, 0.20),
    (301, 3, "FBF-ORG", "FiberFit Original 400g",           400, 3.89, 0.50),
    (302, 3, "FBF-RED", "FiberFit Red Berries 400g",        400, 4.19, 0.30),
    (303, 3, "FBF-PRO", "FiberFit Protein 350g",            350, 4.59, 0.20),
    (401, 4, "GHR-375", "Golden Honey Rings 375g",          375, 2.29, 0.60),
    (402, 4, "GHR-700", "Golden Honey Rings 700g",          700, 3.79, 0.25),
    (403, 4, "GHR-CHO", "Golden Honey Rings Choco 375g",    375, 2.45, 0.15),
    (501, 5, "MSA-CLA", "Muesli Alpino Classic 500g",       500, 4.49, 0.45),
    (502, 5, "MSA-FRU", "Muesli Alpino Fruits & Nuts 500g", 500, 4.99, 0.35),
    (503, 5, "MSA-CRU", "Muesli Alpino Crunchy 450g",       450, 4.79, 0.20),
]
dim_product = pd.DataFrame(
    [p[:6] for p in PRODUCTS],
    columns=["product_id", "brand_id", "sku_code", "product_name",
             "pack_size_g", "list_price_eur"])
product_share = {p[0]: p[6] for p in PRODUCTS}

# retailer_id, name, type, coverage, share of category volume, base distribution
RETAILERS = [
    (1, "HiperMax",    "Hypermarket", "National", 0.24, 96),
    (2, "SuperCasa",   "Supermarket", "National", 0.30, 92),
    (3, "FreshMarket", "Supermarket", "Regional", 0.14, 85),
    (4, "AhorroPlus",  "Discounter",  "National", 0.18, 70),
    (5, "BioMercat",   "Supermarket", "Regional", 0.06, 60),
    (6, "ClickCompra", "Online",      "National", 0.08, 99),
]
dim_retailer = pd.DataFrame(
    [r[:4] for r in RETAILERS],
    columns=["retailer_id", "retailer_name", "channel_type", "coverage"])

dim_region = pd.DataFrame([
    (1, "Catalonia", 8.00), (2, "Madrid", 7.00), (3, "Andalusia", 8.60),
    (4, "Valencia", 5.30), (5, "North", 6.40), (6, "Centre & Islands", 12.70),
], columns=["region_id", "region_name", "population_m"])

dim_tv_channel = pd.DataFrame([
    (1, "La 1",      "RTVE",             "Generalist"),
    (2, "Antena 3",  "Atresmedia",       "Generalist"),
    (3, "Telecinco", "Mediaset España",  "Generalist"),
    (4, "Cuatro",    "Mediaset España",  "Generalist"),
    (5, "laSexta",   "Atresmedia",       "Generalist"),
    (6, "Clan",      "RTVE",             "Kids"),
    (7, "Boing",     "Mediaset España",  "Kids"),
    (8, "Neox",      "Atresmedia",       "Thematic"),
    (9, "FDF",       "Mediaset España",  "Thematic"),
], columns=["channel_id", "channel_name", "channel_group", "channel_type"])

dim_daypart = pd.DataFrame([
    (1, "Morning",        7, 14),
    (2, "Afternoon",     14, 17),
    (3, "Early evening", 17, 20),
    (4, "Prime time",    20, 24),
    (5, "Late night",     0,  2),
], columns=["daypart_id", "daypart_name", "start_hour", "end_hour"])

dim_media_type = pd.DataFrame([
    (1, "TV"), (2, "Digital Video"), (3, "Social"), (4, "OOH"), (5, "Radio"),
], columns=["media_type_id", "media_type"])

# ---------------------------------------------------------------------
# Date dimension
# ---------------------------------------------------------------------
dates = pd.date_range(START, END, freq="D")
season = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring",
          5: "Spring", 6: "Summer", 7: "Summer", 8: "Summer",
          9: "Autumn", 10: "Autumn", 11: "Autumn"}
dim_date = pd.DataFrame({
    "date_key": dates.strftime("%Y%m%d").astype(int),
    "full_date": dates.date,
    "year": dates.year,
    "quarter": dates.quarter,
    "month": dates.month,
    "month_name": dates.strftime("%B"),
    "iso_week": dates.isocalendar().week.astype(int).values,
    "week_start": (dates - pd.to_timedelta(dates.dayofweek, unit="D")).date,
    "day_of_week": dates.dayofweek + 1,
    "day_name": dates.strftime("%A"),
    "is_weekend": dates.dayofweek >= 5,
    "season": [season[m] for m in dates.month],
})
weeks = pd.date_range(START, END, freq="W-MON")
week_keys = weeks.strftime("%Y%m%d").astype(int)
n_weeks = len(weeks)

# ---------------------------------------------------------------------
# Campaigns (flights of 3-6 weeks; kids brands peak at back-to-school
# and Christmas, health brand in January "new year resolutions")
# ---------------------------------------------------------------------
preferred_starts = {          # ISO weeks where flights tend to start
    1: [2, 14, 36, 46], 2: [5, 18, 37, 44], 3: [1, 10, 20, 38],
    4: [6, 22, 36, 47], 5: [3, 15, 39, 45],
}
objectives = ["Awareness", "Promo", "Awareness", "Always-on"]
campaign_rows, flight_weeks = [], {}   # flight_weeks[(brand, week_idx)] = campaign_id
cid = 1000
for brand_id, starts in preferred_starts.items():
    for year in (2024, 2025):
        for i, wk in enumerate(starts):
            wk = int(np.clip(wk + rng.integers(-1, 2), 1, 48))
            length = int(rng.integers(3, 7))
            start = pd.Timestamp.fromisocalendar(year, wk, 1)
            end = start + pd.Timedelta(weeks=length) - pd.Timedelta(days=1)
            obj = "Launch" if (brand_id == 3 and year == 2025 and i == 2) else objectives[i]
            name = f"{dim_brand.loc[brand_id-1,'brand_name']} {obj} {year}-{i+1}"
            cid += 1
            campaign_rows.append([cid, brand_id, name, obj, start.date(), end.date(), 0.0])
            for w in range(length):
                idx = weeks.get_indexer([start + pd.Timedelta(weeks=w)])[0]
                if idx >= 0:
                    flight_weeks[(brand_id, idx)] = cid
dim_campaign = pd.DataFrame(campaign_rows, columns=[
    "campaign_id", "brand_id", "campaign_name", "objective",
    "start_date", "end_date", "budget_eur"])

# ---------------------------------------------------------------------
# TV spots  (fact_tv_audience)
# ---------------------------------------------------------------------
cpp = {1: 1450, 2: 1150, 3: 520, 4: 980, 5: 1050}        # € per GRP for a 20" spot
len_index = {10: 0.60, 20: 1.00, 30: 1.40}
daypart_hours = {1: (7, 13), 2: (14, 16), 3: (17, 19), 4: (20, 23), 5: (0, 1)}
kids_channels, adult_channels = [6, 7, 2, 3, 8], [1, 2, 3, 4, 5, 8, 9]

spot_rows, weekly_grps = [], np.zeros((6, n_weeks))
spot_id = 1
for (brand_id, w), camp in flight_weeks.items():
    target = int(dim_brand.loc[brand_id - 1, "main_target_id"])
    weekly_goal = rng.uniform(140, 320) * (1.3 if dim_campaign.set_index("campaign_id").loc[camp, "objective"] == "Launch" else 1)
    grp_acc = 0.0
    while grp_acc < weekly_goal:
        kids = target == 3
        channel = int(rng.choice(kids_channels if kids else adult_channels))
        daypart = int(rng.choice([1, 2, 3, 4, 5], p=[.35, .25, .25, .10, .05] if kids else [.15, .20, .20, .38, .07]))
        length = int(rng.choice([10, 20, 30], p=[.25, .55, .20]))
        base = 2.6 if (kids and channel in (6, 7)) else (1.8 if daypart == 4 else 1.0)
        grp = round(float(rng.gamma(2.0, base / 2.0)) + 0.05, 2)
        day = weeks[w] + pd.Timedelta(days=int(rng.integers(0, 7)))
        h0, h1 = daypart_hours[daypart]
        air = f"{int(rng.integers(h0, h1 + 1)):02d}:{int(rng.integers(0, 60)):02d}:00"
        universe = int(dim_target.loc[target - 1, "universe_000"])
        premium = 1.15 if channel in (2, 3) else 1.0
        cost = round(grp * cpp[target] * len_index[length] * premium * rng.uniform(0.9, 1.1), 2)
        spot_rows.append([spot_id, int(day.strftime("%Y%m%d")), brand_id, camp, channel,
                          daypart, target, air, length, grp,
                          round(grp / 100 * universe, 1), cost])
        spot_id += 1
        grp_acc += grp
    weekly_grps[brand_id, w] += grp_acc

fact_tv_audience = pd.DataFrame(spot_rows, columns=[
    "spot_id", "date_key", "brand_id", "campaign_id", "channel_id", "daypart_id",
    "target_id", "air_time", "spot_length_sec", "grp", "impressions_000",
    "spot_cost_eur"]).sort_values(["date_key", "air_time"]).reset_index(drop=True)
fact_tv_audience["spot_id"] = np.arange(1, len(fact_tv_audience) + 1)

# ---------------------------------------------------------------------
# Advertising investment (fact_ad_investment)
# TV = exact sum of spot costs; other media added around TV flights,
# plus an always-on social budget every week.
# ---------------------------------------------------------------------
spots_week = fact_tv_audience.assign(
    week=pd.to_datetime(fact_tv_audience["date_key"].astype(str)).dt.to_period("W-SUN").dt.start_time
).groupby(["week", "brand_id", "campaign_id"], as_index=False).agg(
    spend=("spot_cost_eur", "sum"), imps=("impressions_000", "sum"))

inv_rows = []
for r in spots_week.itertuples():
    inv_rows.append([int(r.week.strftime("%Y%m%d")), r.brand_id, r.campaign_id, 1,
                     round(r.spend, 2), round(r.imps, 1)])
    for mt, share, cpm in [(2, .22, 9.5), (4, .12, 4.0), (5, .08, 3.2)]:
        if mt == 2 or rng.random() < 0.5:
            spend = round(r.spend * share * rng.uniform(0.7, 1.3), 2)
            inv_rows.append([int(r.week.strftime("%Y%m%d")), r.brand_id, r.campaign_id,
                             mt, spend, round(spend / cpm, 1)])

always_on = dim_campaign[dim_campaign.objective == "Always-on"]
for brand_id in range(1, 6):
    aon = always_on[always_on.brand_id == brand_id].sort_values("start_date")
    for w, wk in enumerate(weeks):
        camp = int(aon[aon.start_date.astype(str) <= str(wk.date())].campaign_id.max()
                   if (aon.start_date.astype(str) <= str(wk.date())).any()
                   else aon.campaign_id.min())
        spend = round(rng.uniform(4_000, 11_000) * (1.6 if brand_id in (3, 5) else 1), 2)
        inv_rows.append([int(wk.strftime("%Y%m%d")), brand_id, camp, 3, spend,
                         round(spend / 5.5, 1)])

fact_ad_investment = pd.DataFrame(inv_rows, columns=[
    "week_date_key", "brand_id", "campaign_id", "media_type_id",
    "spend_eur", "impressions_000"])
fact_ad_investment.insert(0, "investment_id", np.arange(1, len(fact_ad_investment) + 1))

budgets = fact_ad_investment.groupby("campaign_id").spend_eur.sum()
dim_campaign["budget_eur"] = (dim_campaign.campaign_id.map(budgets).fillna(0)
                              * rng.uniform(1.0, 1.08, len(dim_campaign))).round(-2)

# ---------------------------------------------------------------------
# Sales (fact_sales)
# units = base * seasonality * trend * (1 + TV uplift) * promo * noise
# ---------------------------------------------------------------------
woy = weeks.isocalendar().week.values.astype(int)
seasonality = 1 + 0.10 * np.cos(2 * np.pi * (woy - 38) / 52)          # Sep/Oct peak
seasonality *= np.where((woy >= 31) & (woy <= 34), 0.85, 1.0)         # August dip
seasonality *= np.where(woy <= 3, 1.06, 1.0)                           # January
trend = {1: 0.0, 2: -0.03, 3: 0.08, 4: -0.01, 5: 0.12}                 # yearly growth

def adstock(x, decay=0.6):
    out = np.zeros_like(x)
    for t in range(len(x)):
        out[t] = x[t] + (decay * out[t - 1] if t else 0)
    return out

region_w = (dim_region.population_m / dim_region.population_m.sum()).values
sales_rows = []
for prod in PRODUCTS:
    pid, bid, price = prod[0], prod[1], prod[5]
    p = brand_params[bid]
    ad = adstock(weekly_grps[bid])
    uplift = p["beta"] * (1 - np.exp(-ad / p["half_sat"]))
    t = np.arange(n_weeks) / 52
    launch_ramp = np.clip((np.arange(n_weeks) - 70) / 10, 0, 1) if pid == 303 else 1.0
    nat_units = p["base"] * product_share[pid] * seasonality * (1 + trend[bid]) ** t * (1 + uplift) * launch_ramp
    for ret in RETAILERS:
        rid, r_share, dist = ret[0], ret[4], ret[5]
        disc = 0.92 if ret[2] == "Discounter" else (1.03 if ret[2] == "Online" else 1.0)
        promo = rng.random(n_weeks) < (0.18 if ret[2] != "Online" else 0.10)
        price_paid = price * disc * np.where(promo, rng.uniform(0.70, 0.85, n_weeks), 1.0)
        promo_lift = np.where(promo, rng.uniform(1.25, 1.60, n_weeks), 1.0)
        for reg_idx, reg in enumerate(dim_region.region_id):
            reg_pref = 1.15 if (bid == 3 and reg in (1, 2)) else 1.0
            units = nat_units * r_share * region_w[reg_idx] * reg_pref * promo_lift * rng.normal(1, 0.07, n_weeks)
            units = np.maximum(units, 0).round().astype(int)
            d = np.clip(dist + rng.normal(0, 1.5, n_weeks), 30, 100).round(2)
            for w in range(n_weeks):
                if units[w] == 0:
                    continue
                sales_rows.append([int(week_keys[w]), pid, rid, int(reg), int(units[w]),
                                   round(units[w] * price_paid[w], 2), round(price_paid[w], 2),
                                   bool(promo[w]), d[w]])

fact_sales = pd.DataFrame(sales_rows, columns=[
    "week_date_key", "product_id", "retailer_id", "region_id", "units_sold",
    "revenue_eur", "avg_price_eur", "on_promotion", "numeric_distribution_pct"])
fact_sales.insert(0, "sales_id", np.arange(1, len(fact_sales) + 1))

# ---------------------------------------------------------------------
# Write CSVs and build the DuckDB warehouse
# ---------------------------------------------------------------------
tables = {
    "dim_date": dim_date, "dim_manufacturer": dim_manufacturer, "dim_brand": dim_brand,
    "dim_product": dim_product, "dim_retailer": dim_retailer, "dim_region": dim_region,
    "dim_tv_channel": dim_tv_channel, "dim_daypart": dim_daypart, "dim_target": dim_target,
    "dim_media_type": dim_media_type, "dim_campaign": dim_campaign,
    "fact_tv_audience": fact_tv_audience, "fact_ad_investment": fact_ad_investment,
    "fact_sales": fact_sales,
}
for name, df in tables.items():
    df.to_csv(DATA / f"{name}.csv", index=False)

db_path = DATA / "cereal_dwh.duckdb"
db_path.unlink(missing_ok=True)
con = duckdb.connect(str(db_path))
con.execute((ROOT / "sql" / "01_schema.sql").read_text())
for name in tables:   # dimension tables first (dict order) so FKs are satisfied
    con.execute(f"INSERT INTO {name} SELECT * FROM read_csv_auto('{DATA / (name + '.csv')}', header=true)")
for name in tables:
    print(f"{name:<22}{con.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]:>9,} rows")
con.close()
print(f"\nWarehouse written to {db_path}")
