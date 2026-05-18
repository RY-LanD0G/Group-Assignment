# NZ Fuel Prices Database — COMPX532 Group Assignment

A relational MySQL database covering New Zealand retail fuel prices at
**national**, **regional**, **city/town** and **brand × city** granularity,
spanning **122 weeks (2024-01-05 → 2026-05-01, > 2 years)**, with four
fuel types (Regular 91, Premium 95, Premium 98, Automotive Diesel).

This repository contains the raw inputs, build scripts, derived CSVs, and
ready-to-import MySQL `.sql` files that the visualization team can load
directly into a local or shared MySQL 8.0+ instance.

---

## Quick start

```bash
# 1. Clone the repo
git clone <repo-url>
cd "Group Assignment"

# 2. Create the database and load everything (run in order)
mysql -u root -p < sql/schema.sql
mysql -u root -p < sql/data.sql
mysql -u root -p < sql/schema_cities.sql
mysql -u root -p < sql/data_cities.sql
mysql -u root -p < sql/schema_brands.sql
mysql -u root -p < sql/data_brands.sql

# 3. Verify
mysql -u root -p -e "USE nz_fuel_prices; SHOW TABLES;"
```

Expected output: 9 tables + 6 views.

---

## Database overview

Database name: **`nz_fuel_prices`**
Engine: InnoDB · Charset: utf8mb4

```
                +-------------+        +-----------+
                |   regions   |◄──┐    │ fuel_types│
                +------+------+   │    +-----+-----+
                       ▲          │          ▲
        +--------------+----+-----┴-----+----+--------+
        │                   │           │             │
        │                   │           │             │
        ▼                   ▼           ▼             ▼
   +---------+        +-----------+ +--------+  +------------+
   | cities  |        |fuel_prices| │national│  │price_events│
   +----+----+        |  (region) | │_weekly │  +------------+
        ▲             +-----------+ +--------+
        │                   ▲
        │                   │
        ▼                   │
  +-----------+        +----+-----------+
  │city_fuel_ │◄──┐    │brand_city_     │
  │ prices    │   │    │ prices         │
  +-----------+   │    +-------+--------+
                  └────────────┘
                          ▲
                          │
                      +---+----+
                      │ brands │
                      +--------+
```

---

## Tables

### 1. `regions` — 16 NZ Regional Council Areas

| Column | Type | Notes |
|---|---|---|
| `region_code` | CHAR(3) | **PK**. e.g. `AUK`, `WGN`, `CAN` |
| `region_name` | VARCHAR(64) | Full name, e.g. *Auckland* |
| `island` | ENUM('North','South') | Island |
| `typical_diff_c` | DECIMAL(5,2) | Typical c/L offset vs national average |
| `population_2023` | INT UNSIGNED | StatsNZ 2023 estimate |

Row count: **16**

### 2. `fuel_types` — 4 fuels

| Column | Type | Notes |
|---|---|---|
| `fuel_code` | CHAR(3) | **PK**. `P91`, `P95`, `P98`, `DSL` |
| `fuel_name` | VARCHAR(64) | Display name |
| `octane_rating` | TINYINT UNSIGNED | NULL for diesel |
| `is_petrol` | BOOLEAN | true for P91/P95/P98 |

Row count: **4**

### 3. `national_weekly` — Real MBIE national weekly retail prices

| Column | Type | Notes |
|---|---|---|
| `price_date` | DATE | **PK part 1**. Monday of the week |
| `fuel_code` | CHAR(3) | **PK part 2**. FK → `fuel_types` |
| `national_avg_nzd_per_l` | DECIMAL(6,3) | Pump price including GST |

Row count: **488** (122 weeks × 4 fuels; P98 is derived from P95 + 17 c/L)

### 4. `fuel_prices` — Regional weekly retail prices

| Column | Type | Notes |
|---|---|---|
| `price_date` | DATE | **PK part 1** |
| `region_code` | CHAR(3) | **PK part 2**. FK → `regions` |
| `fuel_code` | CHAR(3) | **PK part 3**. FK → `fuel_types` |
| `price_nzd_per_litre` | DECIMAL(6,3) | Pump price including GST |
| `source` | VARCHAR(120) | Data lineage tag |

Row count: **7,808** (16 regions × 4 fuels × 122 weeks)

### 5. `price_events` — Notable policy / market events

| Column | Type | Notes |
|---|---|---|
| `event_id` | INT UNSIGNED AUTO_INCREMENT | **PK** |
| `event_date` | DATE | When the event occurred |
| `description` | VARCHAR(255) | Plain-text description |
| `impact_cents` | DECIMAL(5,2) | Step change in c/L |
| `affected_region` | CHAR(3) NULL | FK → `regions`, or NULL for national |

Row count: **2** (Auckland Regional Fuel Tax removal, MBIE methodology change)

### 6. `cities` — 69 main NZ towns/cities

| Column | Type | Notes |
|---|---|---|
| `city_code` | VARCHAR(5) | **PK** e.g. `AKC`, `CHC`, `QNS` |
| `city_name` | VARCHAR(64) | Display name |
| `region_code` | CHAR(3) | FK → `regions` |
| `diff_c_vs_region` | DECIMAL(5,2) | c/L offset vs region average |
| `population_2023` | INT UNSIGNED | StatsNZ 2023 estimate |
| `tag` | ENUM | `urban` / `secondary` / `town` / `remote` / `tourist` / `island` |

Row count: **69** (3–6 per region)

### 7. `city_fuel_prices` — City-level weekly retail prices

| Column | Type | Notes |
|---|---|---|
| `price_date` | DATE | **PK part 1** |
| `city_code` | VARCHAR(5) | **PK part 2**. FK → `cities` |
| `region_code` | CHAR(3) | FK → `regions` (denormalised for join speed) |
| `fuel_code` | CHAR(3) | **PK part 3**. FK → `fuel_types` |
| `price_nzd_per_litre` | DECIMAL(6,3) | Pump price |
| `source` | VARCHAR(120) | Lineage tag |

Row count: **33,672** (69 cities × 4 fuels × 122 weeks)

### 8. `brands` — Major chain operators

| Column | Type | Notes |
|---|---|---|
| `brand_code` | VARCHAR(8) | **PK**. `Z`, `BP`, `MOBIL` |
| `brand_name` | VARCHAR(64) | Display name |
| `network_type` | ENUM | `major` / `discount` / `supermarket` / `independent` |
| `stations_nz` | INT UNSIGNED | NZ station count (from Petrolmate scrape) |
| `loyalty_program` | VARCHAR(64) | e.g. *Pumped*, *BPme* |

Row count: **3**

### 9. `brand_city_prices` — Brand × City weekly retail prices

| Column | Type | Notes |
|---|---|---|
| `price_date` | DATE | **PK part 1** |
| `brand_code` | VARCHAR(8) | **PK part 2**. FK → `brands` |
| `city_code` | VARCHAR(5) | **PK part 3**. FK → `cities` |
| `region_code` | CHAR(3) | FK → `regions` |
| `fuel_code` | CHAR(3) | **PK part 4**. FK → `fuel_types` |
| `price_nzd_per_litre` | DECIMAL(6,3) | Pump price |
| `source` | VARCHAR(150) | Lineage tag |

Row count: **76,128** (156 valid brand-city pairs × 4 fuels × 122 weeks).

*Brand-city pairs only exist where the brand actually operates stations
in the city's region (per the Petrolmate snapshot).*

---

## Views

| View | Purpose |
|---|---|
| `v_national_weekly` | National weekly avg (any aggregation level) |
| `v_monthly_region` | Region × fuel monthly avg/min/max |
| `v_national_vs_region` | Region price minus national avg, per week |
| `v_monthly_city` | City × fuel monthly avg/min/max |
| `v_city_vs_region` | City price minus its region price, per week |
| `v_brand_monthly_city` | Brand × city monthly avg |
| `v_brand_vs_market` | Brand price minus city market price |

---

## Example queries

**Weekly national diesel price for the last 26 weeks**

```sql
SELECT price_date, national_avg_nzd_per_l
FROM   national_weekly
WHERE  fuel_code = 'DSL'
ORDER  BY price_date DESC
LIMIT  26;
```

**Most expensive cities for 91 octane in the latest week**

```sql
SELECT c.city_name, c.region_code, cfp.price_nzd_per_litre
FROM   city_fuel_prices cfp
JOIN   cities c ON c.city_code = cfp.city_code
WHERE  cfp.fuel_code = 'P91'
       AND cfp.price_date = (SELECT MAX(price_date) FROM city_fuel_prices)
ORDER  BY cfp.price_nzd_per_litre DESC
LIMIT  10;
```

**Brand competitiveness in Auckland (latest week, 91)**

```sql
SELECT bcp.brand_code, c.city_name,
       bcp.price_nzd_per_litre AS brand_price,
       cfp.price_nzd_per_litre AS market_price,
       ROUND(bcp.price_nzd_per_litre - cfp.price_nzd_per_litre, 3) AS diff
FROM   brand_city_prices bcp
JOIN   cities c        ON c.city_code = bcp.city_code
JOIN   city_fuel_prices cfp
        ON cfp.price_date = bcp.price_date
       AND cfp.city_code  = bcp.city_code
       AND cfp.fuel_code  = bcp.fuel_code
WHERE  bcp.region_code = 'AUK'
       AND bcp.fuel_code = 'P91'
       AND bcp.price_date = (SELECT MAX(price_date) FROM brand_city_prices);
```

**Price impact of Auckland Regional Fuel Tax removal (1 Jul 2024)**

```sql
SELECT 'before' AS period,
       ROUND(AVG(price_nzd_per_litre), 3) AS avg_p91
FROM   fuel_prices
WHERE  region_code = 'AUK' AND fuel_code = 'P91'
       AND price_date BETWEEN '2024-05-01' AND '2024-06-30'
UNION ALL
SELECT 'after',
       ROUND(AVG(price_nzd_per_litre), 3)
FROM   fuel_prices
WHERE  region_code = 'AUK' AND fuel_code = 'P91'
       AND price_date BETWEEN '2024-07-08' AND '2024-08-31';
```

---

## Data sources & lineage

| Layer | Source | Real or derived? |
|---|---|---|
| National weekly | MBIE *Weekly Fuel Price Monitoring* CSV (`weekly-table.csv`, public) | **Real**: `Adjusted retail price` field, GST-inclusive |
| Premium 98 national | Derived: P95 + 17.0 c/L (NZ industry standard differential) | Derived |
| Regional series | National series + AA Petrolwatch / Stats NZ regional differentials | Derived |
| Auckland 2024-07-01 step | Auckland Regional Fuel Tax removed (11.5 c/L) | Real policy event |
| City series | Regional series + documented town-level differentials | Derived |
| Brand × city snapshot | **Scraped** from petrolmate.com.au/brand/{z,bp,mobil} on 2026-05-18 | **Real** |
| Brand × city history | Snapshot brand offsets applied backwards to city series | Derived |

The Python build scripts (`scripts/generate_*.py`) are deterministic
(seeded random) so the entire dataset can be regenerated from the raw
MBIE CSV and the scraped JSON snapshot.

---

## What's in this repo

```
Group Assignment/
├── README.md                              ← you are here
├── .gitignore
├── data/                                  Derived CSVs (also imported into MySQL)
│   ├── regions.csv
│   ├── fuel_types.csv
│   ├── events.csv
│   ├── national_weekly.csv
│   ├── fuel_prices_long.csv               7,808 rows
│   ├── fuel_prices_wide.csv
│   ├── cities.csv
│   ├── city_fuel_prices_long.csv          33,672 rows
│   ├── city_fuel_prices_wide.csv
│   ├── brands.csv
│   ├── brand_city_prices_long.csv         76,128 rows
│   └── brand_city_snapshot_latest.csv
├── sql/                                   MySQL DDL + INSERTs
│   ├── schema.sql                         core tables + views
│   ├── data.sql
│   ├── schema_cities.sql
│   ├── data_cities.sql
│   ├── schema_brands.sql
│   └── data_brands.sql
├── scripts/                               Reproducible build pipeline
│   ├── generate_fuel_dataset.py
│   ├── generate_city_dataset.py
│   ├── generate_brand_dataset.py
│   └── scraped_brand_snapshot.json        Real Petrolmate scrape, 2026-05-18
└── docs/                                  Reference docs and exploratory charts
    ├── README.md                          中文版说明
    ├── national_trend.png
    ├── regional_snapshot.png
    ├── city_trend_p91.png
    ├── city_top_bottom.png
    ├── brand_akc_p91.png
    └── brand_auk_cities.png
```

---

## Reproducing the dataset

```bash
# (Optional) re-download MBIE raw CSV
# weekly-table.csv from https://www.mbie.govt.nz/.../weekly-table.csv

# Then run the pipeline (regenerates all CSVs + SQL)
python3 scripts/generate_fuel_dataset.py     # national + regional
python3 scripts/generate_city_dataset.py     # city
python3 scripts/generate_brand_dataset.py    # brand × city
```

All scripts use `random.seed(...)` for reproducibility — re-running
produces byte-identical output.

---

## License & attribution

- MBIE data is published under the **NZ Government Open Access** licence.
- Petrolmate / Petrolspy data is used here for non-commercial educational
  purposes; please respect their respective Terms of Use.
- This dataset and code: COMPX532 Group Assignment, University of Waikato.

---

## Maintainers

- Data team: see Git commit history.

For questions about the data pipeline, contact the data team. For
visualization-related questions, refer to the corresponding sub-team.
