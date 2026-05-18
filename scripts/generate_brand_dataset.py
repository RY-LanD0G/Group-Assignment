"""
NZ Brand × City Fuel Price Dataset Builder
==========================================

Combines two sources:

  1. REAL scraped snapshot (week of 2026-05-18) from
     petrolmate.com.au/brand/{z,bp,mobil}. Gives brand × region station
     counts, min / avg / max ULP prices, and named cheapest stations.

  2. Historical backfill — applies a brand-specific differential to the
     existing city-level weekly series (`city_fuel_prices_long.csv`) to
     reconstruct ~2 years of Z / BP / Mobil prices per city.

Brand differentials are calibrated so that:
  - The latest week (2026-05-18) matches the scraped snapshot averages.
  - Pre-snapshot weeks inherit the same brand-vs-market spread.
  - Per-city, the brand price = city_price + brand_offset_for_region
                                + weekly noise (sigma 1.0 c/L).

Coverage filter
---------------
A (brand, city) pair is included ONLY if the brand actually operates
at least one station in that region (per scraped data). E.g. Mobil has
no Northland stations, so no NTL cities get Mobil prices.

Outputs
-------
  data/brands.csv
  data/brand_city_prices_long.csv
  data/brand_city_snapshot_latest.csv
  sql/schema_brands.sql
  sql/data_brands.sql

Author: Data team, COMPX532 Group Assignment
"""

from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from datetime import date
from pathlib import Path

random.seed(7)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SQL_DIR = BASE_DIR / "sql"
SNAPSHOT_FILE = BASE_DIR / "scripts" / "scraped_brand_snapshot.json"
CITY_LONG_CSV = DATA_DIR / "city_fuel_prices_long.csv"

# ---------------------------------------------------------------------------
# Brand reference table
# ---------------------------------------------------------------------------

BRANDS = [
    # code,   full name,     network_type, stations_nz, app_loyalty
    ("Z",     "Z Energy",    "major",      66,  "Pumped"),
    ("BP",    "BP",          "major",      109, "BPme / Rewards"),
    ("MOBIL", "Mobil",       "major",      73,  "Mobil Smiles"),
]

# Premium 95/98 mark-ups vs ULP for each brand
# (from Petrolmate per-fuel averages observed in scrape)
BRAND_FUEL_MARKUP = {
    # brand -> {P95 over P91, P98 over P91, DSL vs P91}
    "Z":     {"P95": +15.2, "P98": +30.0, "DSL": -11.1},
    "BP":    {"P95": +21.1, "P98": +31.1, "DSL":  -7.0},
    "MOBIL": {"P95": +22.2, "P98": +32.4, "DSL":  -3.3},
}

# ---------------------------------------------------------------------------
# Load scrape
# ---------------------------------------------------------------------------

with SNAPSHOT_FILE.open() as f:
    SNAP = json.load(f)

SNAPSHOT_DATE = SNAP["snapshot_date"]
MARKET_AVG_LATEST = SNAP["nz_market_reference"]["market_avg"]   # 327.8 c/L


# ---------------------------------------------------------------------------
# Per-region brand offset (c/L) vs the regional ULP market average for the
# snapshot week. Computed: brand_region_avg - regional_market_avg.
#
# For weeks before the snapshot we keep this offset constant; it represents
# the brand's structural position. The base city_price already moves
# with national/MBIE trends, so the brand series tracks the market.
# ---------------------------------------------------------------------------

# Build a regional "market average" from scrape (when multiple brands
# operate in a region, blend their avgs weighted by station count).
def build_region_market_avg() -> dict[str, float]:
    """Weighted regional ULP market avg from scraped Z/BP/Mobil data."""
    region_num = defaultdict(float)
    region_den = defaultdict(float)
    for bcode, info in SNAP["brands"].items():
        for rcode, stats in info["regions"].items():
            n = stats["stations"]
            region_num[rcode] += stats["avg"] * n
            region_den[rcode] += n
    return {r: region_num[r] / region_den[r] for r in region_num}


REGION_MARKET_LATEST = build_region_market_avg()


def brand_region_offset(brand: str, region: str) -> float | None:
    """c/L offset of a brand in a region vs that region's market avg.
       Returns None if the brand does not operate in that region."""
    rstats = SNAP["brands"][brand]["regions"].get(region)
    if not rstats:
        return None
    return rstats["avg"] - REGION_MARKET_LATEST[region]


# ---------------------------------------------------------------------------
# Load the city long table
# ---------------------------------------------------------------------------

def load_city_long():
    """Returns list of dicts."""
    rows = []
    with CITY_LONG_CSV.open() as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


# ---------------------------------------------------------------------------
# Build brand × city × fuel weekly rows
# ---------------------------------------------------------------------------

def build_brand_rows(city_rows: list[dict]) -> list[dict]:
    rows = []
    for r in city_rows:
        if r["fuel_code"] != "P91":
            # we'll generate all four fuels below per-brand from P91 base
            continue
        city_p91 = float(r["price_nzd_per_litre"])
        d = r["price_date"]
        city = r["city_code"]
        region = r["region_code"]

        for bcode, *_ in BRANDS:
            off = brand_region_offset(bcode, region)
            if off is None:
                continue   # brand absent from region
            # Brand P91 = city P91 + brand offset + small noise
            seed = (d, bcode, city, "P91")
            rng = random.Random(hash(seed) & 0xFFFFFFFF)
            noise = rng.gauss(0.0, 1.0) / 100.0
            p91 = round(city_p91 + off / 100.0 + noise, 3)
            mk = BRAND_FUEL_MARKUP[bcode]
            for fc, delta_c in [("P91", 0.0),
                                 ("P95", mk["P95"]),
                                 ("P98", mk["P98"]),
                                 ("DSL", mk["DSL"])]:
                seed2 = (d, bcode, city, fc)
                rng2 = random.Random(hash(seed2) & 0xFFFFFFFF)
                n2 = rng2.gauss(0.0, 0.7) / 100.0
                p = round(p91 + delta_c / 100.0 + n2, 3)
                rows.append({
                    "price_date": d,
                    "brand_code": bcode,
                    "city_code": city,
                    "region_code": region,
                    "fuel_code": fc,
                    "price_nzd_per_litre": p,
                    "source": "petrolmate scrape (2026-05-18) + brand-offset backfill",
                })
    return rows


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

def write_brands_csv():
    with open(DATA_DIR / "brands.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["brand_code", "brand_name", "network_type",
                    "stations_nz", "loyalty_program"])
        for b in BRANDS:
            w.writerow(b)


def write_brand_long(rows):
    with open(DATA_DIR / "brand_city_prices_long.csv", "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["price_date", "brand_code", "city_code", "region_code",
                    "fuel_code", "price_nzd_per_litre", "source"])
        for r in rows:
            w.writerow([r["price_date"], r["brand_code"], r["city_code"],
                        r["region_code"], r["fuel_code"],
                        r["price_nzd_per_litre"], r["source"]])


def write_latest_snapshot(rows):
    """Slice latest week for quick inspection."""
    last_dates = sorted({r["price_date"] for r in rows})
    last = last_dates[-1]
    with open(DATA_DIR / "brand_city_snapshot_latest.csv", "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["price_date", "brand_code", "city_code", "region_code",
                    "fuel_code", "price_nzd_per_litre"])
        for r in rows:
            if r["price_date"] == last:
                w.writerow([r["price_date"], r["brand_code"], r["city_code"],
                            r["region_code"], r["fuel_code"],
                            r["price_nzd_per_litre"]])


SCHEMA_SQL = """\
-- =====================================================================
-- Brand × city extension of the NZ fuel price database
-- Run AFTER schema.sql + data.sql + schema_cities.sql + data_cities.sql
-- =====================================================================

USE nz_fuel_prices;

CREATE TABLE IF NOT EXISTS brands (
    brand_code        VARCHAR(8)   NOT NULL PRIMARY KEY,
    brand_name        VARCHAR(64)  NOT NULL,
    network_type      ENUM('major','discount','supermarket','independent') NOT NULL,
    stations_nz       INT UNSIGNED NOT NULL,
    loyalty_program   VARCHAR(64)  NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS brand_city_prices (
    price_date              DATE         NOT NULL,
    brand_code              VARCHAR(8)   NOT NULL,
    city_code               VARCHAR(5)   NOT NULL,
    region_code             CHAR(3)      NOT NULL,
    fuel_code               CHAR(3)      NOT NULL,
    price_nzd_per_litre     DECIMAL(6,3) NOT NULL,
    source                  VARCHAR(150) NOT NULL,
    PRIMARY KEY (price_date, brand_code, city_code, fuel_code),
    KEY ix_bcp_brand  (brand_code),
    KEY ix_bcp_city   (city_code),
    KEY ix_bcp_region (region_code),
    KEY ix_bcp_fuel   (fuel_code),
    KEY ix_bcp_date   (price_date),
    CONSTRAINT fk_bcp_brand  FOREIGN KEY (brand_code)  REFERENCES brands(brand_code),
    CONSTRAINT fk_bcp_city   FOREIGN KEY (city_code)   REFERENCES cities(city_code),
    CONSTRAINT fk_bcp_region FOREIGN KEY (region_code) REFERENCES regions(region_code),
    CONSTRAINT fk_bcp_fuel   FOREIGN KEY (fuel_code)   REFERENCES fuel_types(fuel_code)
) ENGINE=InnoDB;

CREATE OR REPLACE VIEW v_brand_monthly_city AS
SELECT  DATE_FORMAT(price_date, '%Y-%m-01') AS month_start,
        brand_code, city_code, region_code, fuel_code,
        ROUND(AVG(price_nzd_per_litre), 3) AS monthly_avg
FROM    brand_city_prices
GROUP BY month_start, brand_code, city_code, region_code, fuel_code;

CREATE OR REPLACE VIEW v_brand_vs_market AS
SELECT  bcp.price_date, bcp.brand_code, bcp.city_code, bcp.region_code,
        bcp.fuel_code, bcp.price_nzd_per_litre,
        cfp.price_nzd_per_litre AS city_market_price,
        ROUND(bcp.price_nzd_per_litre - cfp.price_nzd_per_litre, 3) AS diff_vs_city_market
FROM    brand_city_prices bcp
JOIN    city_fuel_prices cfp
        ON cfp.price_date = bcp.price_date
       AND cfp.city_code  = bcp.city_code
       AND cfp.fuel_code  = bcp.fuel_code;
"""


def write_sql_files(rows):
    with open(SQL_DIR / "schema_brands.sql", "w", encoding="utf-8") as f:
        f.write(SCHEMA_SQL)

    with open(SQL_DIR / "data_brands.sql", "w", encoding="utf-8") as f:
        f.write("USE nz_fuel_prices;\nSET autocommit=0;\n\n")
        f.write("-- brands\nINSERT INTO brands VALUES\n")
        f.write(",\n".join(
            f"('{b[0]}', '{b[1]}', '{b[2]}', {b[3]}, "
            f"'{b[4].replace(chr(39), chr(39)*2)}')"
            for b in BRANDS
        ))
        f.write(";\n\n")

        f.write("-- brand_city_prices\n")
        B = 500
        for i in range(0, len(rows), B):
            chunk = rows[i:i+B]
            f.write("INSERT INTO brand_city_prices VALUES\n")
            f.write(",\n".join(
                f"('{r['price_date']}', '{r['brand_code']}', '{r['city_code']}', "
                f"'{r['region_code']}', '{r['fuel_code']}', {r['price_nzd_per_litre']}, "
                f"'{r['source'].replace(chr(39), chr(39)*2)}')"
                for r in chunk
            ))
            f.write(";\n")
        f.write("\nCOMMIT;\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Loading scraped snapshot from {SNAPSHOT_DATE}")
    print(f"  market avg ULP: {MARKET_AVG_LATEST} c/L")
    print("\nRegion-level market averages (weighted from scrape):")
    for r, v in sorted(REGION_MARKET_LATEST.items()):
        print(f"  {r}: {v:.1f} c/L")

    print("\nBrand offsets vs region market (snapshot week):")
    for b, *_ in BRANDS:
        offs = []
        for r in REGION_MARKET_LATEST:
            off = brand_region_offset(b, r)
            if off is not None:
                offs.append(f"{r}{off:+.1f}")
        print(f"  {b:<5} {' '.join(offs)}")

    print("\nLoading city weekly data...")
    city_rows = load_city_long()
    print(f"  city rows: {len(city_rows):,}")

    print("Building brand × city × fuel × week rows...")
    rows = build_brand_rows(city_rows)
    print(f"  brand rows: {len(rows):,}")
    print(f"  brand-cities: {len({(r['brand_code'], r['city_code']) for r in rows})}")
    print(f"  weeks covered: {len({r['price_date'] for r in rows})}")

    write_brands_csv()
    write_brand_long(rows)
    write_latest_snapshot(rows)
    write_sql_files(rows)

    print("\nOutputs:")
    for fname in ["brands.csv", "brand_city_prices_long.csv",
                  "brand_city_snapshot_latest.csv"]:
        p = DATA_DIR / fname
        print(f"  data/{fname:<35} {p.stat().st_size/1024:8.1f} KB")
    for fname in ["schema_brands.sql", "data_brands.sql"]:
        p = SQL_DIR / fname
        print(f"  sql/{fname:<35} {p.stat().st_size/1024:8.1f} KB")


if __name__ == "__main__":
    main()
