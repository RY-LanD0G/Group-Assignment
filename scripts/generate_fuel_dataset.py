"""
NZ Fuel Price Dataset Builder
==============================

Builds a 2+ year weekly fuel price dataset (2024-01-01 .. 2026-05-01)
covering all 16 New Zealand regions and 4 fuel types
(Regular 91, Premium 95, Premium 98, Diesel), grounded in the real
MBIE Weekly Fuel Price Monitoring CSV (weekly-table.csv).

Pipeline
--------
1. Parse the raw MBIE weekly CSV (long/melted format).
2. Pivot out the "Adjusted retail price" national weekly average for
   Regular Petrol (91), Premium Petrol 95R (95) and Diesel.
3. Derive Premium 98 as P95 + 17.0 c/L (NZ industry-standard differential;
   MBIE does not publish 98 separately). This is documented in
   docs/data_dictionary.md.
4. Apply documented regional differentials (AA Petrolwatch / Stats NZ CPI
   regional pattern) to fan the 1 national series out to 16 regions, with
   a small deterministic noise term to reflect station-level dispersion.
5. Encode policy events (Auckland Regional Fuel Tax removal on 30 Jun 2024)
   so Auckland's series shifts the right amount at the right date.
6. Emit CSVs (long + wide) and a MySQL schema + bulk-insert SQL file.

Author: Data team, COMPX532 Group Assignment
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

random.seed(42)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SQL_DIR = BASE_DIR / "sql"
RAW_MBIE_CSV = Path("/sessions/compassionate-great-turing/mnt/uploads/weekly-table.csv")
DATA_DIR.mkdir(parents=True, exist_ok=True)
SQL_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = date(2024, 1, 1)        # >= 2 years
END_DATE = date(2026, 12, 31)        # parse everything available

# ---------------------------------------------------------------------------
# Reference tables
# ---------------------------------------------------------------------------

# 16 Regional Council Areas (Stats NZ). diff_c = typical c/L vs national.
# population = StatsNZ 2023 census estimate (rounded).
REGIONS = [
    # code,  name,                  island,   diff_c, population
    ("NTL",  "Northland",           "North",   +5.0,  201500),
    ("AUK",  "Auckland",            "North",   -6.0, 1715600),  # post-RFT
    ("WKO",  "Waikato",             "North",   -2.0,  513800),
    ("BOP",  "Bay of Plenty",       "North",    0.0,  354400),
    ("GIS",  "Gisborne",            "North",  +10.0,   53000),
    ("HKB",  "Hawke's Bay",         "North",   +3.0,  185100),
    ("TKI",  "Taranaki",            "North",   +2.0,  127300),
    ("MWT",  "Manawatu-Whanganui",  "North",   -1.0,  263300),
    ("WGN",  "Wellington",          "North",   -3.0,  551100),
    ("TAS",  "Tasman",              "South",   +5.0,   58700),
    ("NSN",  "Nelson",              "South",   +4.0,   55400),
    ("MBH",  "Marlborough",         "South",   +6.0,   53400),
    ("WTC",  "West Coast",          "South",  +12.0,   33700),
    ("CAN",  "Canterbury",          "South",   -2.0,  679200),
    ("OTA",  "Otago",               "South",    0.0,  256000),
    ("STL",  "Southland",           "South",   +3.0,  103700),
]

# Maps MBIE "Fuel" label -> our internal fuel_code.
MBIE_FUEL_MAP = {
    "Regular Petrol":     "P91",
    "Premium Petrol 95R": "P95",
    "Diesel":             "DSL",
}

FUEL_TYPES = [
    # code,   display_name,            octane, is_petrol
    ("P91",   "Regular Petrol 91",     91,     True),
    ("P95",   "Premium Petrol 95",     95,     True),
    ("P98",   "Premium Petrol 98",     98,     True),
    ("DSL",   "Automotive Diesel",     None,   False),
]

P98_OVER_P95_CENTS = 17.0   # documented NZ industry differential

EVENTS = [
    (date(2024, 6, 30),
     "Auckland Regional Fuel Tax (11.5 c/L) ends — Auckland prices step down from 1 Jul 2024",
     -11.5, "AUK"),
    (date(2025, 5,  7),
     "MBIE switches weekly fuel monitoring methodology to Datamine source",
     0.0, None),
]


# ---------------------------------------------------------------------------
# Step 1 — parse the MBIE raw CSV
# ---------------------------------------------------------------------------

def parse_mbie_weekly_csv(path: Path):
    """Returns {(price_date, fuel_code): adjusted_retail_price_NZD_per_L}."""
    out: dict[tuple[date, str], float] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Variable"] != "Adjusted retail price":
                continue
            fuel_lbl = row["Fuel"]
            if fuel_lbl not in MBIE_FUEL_MAP:
                continue
            # MBIE date format is d/m/YYYY
            try:
                d = datetime.strptime(row["Date"], "%d/%m/%Y").date()
            except ValueError:
                continue
            if not (START_DATE <= d <= END_DATE):
                continue
            try:
                # MBIE values are in NZD c/L  ->  divide by 100 to get NZD/L
                price = float(row["Value"]) / 100.0
            except (TypeError, ValueError):
                continue
            out[(d, MBIE_FUEL_MAP[fuel_lbl])] = round(price, 3)
    return out


# ---------------------------------------------------------------------------
# Step 2 — derive P98 from P95 + standard differential
# ---------------------------------------------------------------------------

def derive_p98(national: dict[tuple[date, str], float]):
    for (d, fc), v in list(national.items()):
        if fc == "P95":
            national[(d, "P98")] = round(v + P98_OVER_P95_CENTS / 100.0, 3)
    return national


# ---------------------------------------------------------------------------
# Step 3 — fan national series out across 16 regions
# ---------------------------------------------------------------------------

def regional_diff(region_code: str, d: date) -> float:
    """Differential vs national in NZD/L. Auckland has a tax regime change."""
    base = next(r for r in REGIONS if r[0] == region_code)
    diff_c = base[3]
    # During the Auckland Regional Fuel Tax era (pre 1 Jul 2024) AUK sat
    # roughly +5 c/L vs national instead of -6 c/L.
    if region_code == "AUK" and d < date(2024, 7, 1):
        diff_c = +5.0
    return diff_c / 100.0


def weekly_noise(seed_key: tuple, sigma_c: float = 1.2) -> float:
    rng = random.Random(hash(seed_key) & 0xFFFFFFFF)
    return rng.gauss(0.0, sigma_c) / 100.0


def fan_regions(national: dict[tuple[date, str], float]) -> list[dict]:
    rows: list[dict] = []
    fuel_codes = [fc for fc, *_ in FUEL_TYPES]
    by_date = defaultdict(dict)
    for (d, fc), v in national.items():
        by_date[d][fc] = v
    for d in sorted(by_date):
        for region_code, *_ in REGIONS:
            for fc in fuel_codes:
                if fc not in by_date[d]:
                    continue
                p = (by_date[d][fc]
                     + regional_diff(region_code, d)
                     + weekly_noise((d.toordinal(), region_code, fc)))
                p = round(p, 3)
                src = ("MBIE Weekly Fuel Price Monitoring (national) "
                       "+ regional differential")
                if fc == "P98":
                    src = ("Derived from MBIE P95 + 17 c/L "
                           "+ regional differential")
                rows.append({
                    "price_date": d.isoformat(),
                    "region_code": region_code,
                    "fuel_code": fc,
                    "price_nzd_per_litre": p,
                    "source": src,
                })
    return rows


# ---------------------------------------------------------------------------
# Step 4 — CSV output
# ---------------------------------------------------------------------------

def write_regions_csv():
    with open(DATA_DIR / "regions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["region_code", "region_name", "island",
                    "typical_diff_cents", "population_2023"])
        for code, name, island, diff_c, pop in REGIONS:
            w.writerow([code, name, island, diff_c, pop])


def write_fuel_types_csv():
    with open(DATA_DIR / "fuel_types.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fuel_code", "fuel_name", "octane_rating", "is_petrol"])
        for code, name, oct_, is_petrol in FUEL_TYPES:
            w.writerow([code, name, oct_ if oct_ is not None else "",
                        1 if is_petrol else 0])


def write_events_csv():
    with open(DATA_DIR / "events.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["event_date", "description", "impact_cents", "affected_region"])
        for d, desc, c, reg in EVENTS:
            w.writerow([d.isoformat(), desc, c, reg or ""])


def write_long_csv(rows):
    with open(DATA_DIR / "fuel_prices_long.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["price_date", "region_code", "fuel_code",
                    "price_nzd_per_litre", "source"])
        for r in rows:
            w.writerow([r["price_date"], r["region_code"], r["fuel_code"],
                        r["price_nzd_per_litre"], r["source"]])


def write_wide_csv(rows):
    grid: dict[tuple[str, str], dict[str, float]] = {}
    for r in rows:
        key = (r["price_date"], r["region_code"])
        grid.setdefault(key, {})[r["fuel_code"]] = r["price_nzd_per_litre"]
    with open(DATA_DIR / "fuel_prices_wide.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["price_date", "region_code", "P91", "P95", "P98", "DSL"])
        for (d, reg), vals in sorted(grid.items()):
            w.writerow([d, reg, vals.get("P91"), vals.get("P95"),
                        vals.get("P98"), vals.get("DSL")])


def write_national_csv(national):
    with open(DATA_DIR / "national_weekly.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["price_date", "fuel_code", "national_avg_nzd_per_l"])
        for (d, fc), v in sorted(national.items()):
            w.writerow([d.isoformat(), fc, v])


# ---------------------------------------------------------------------------
# Step 5 — MySQL output
# ---------------------------------------------------------------------------

SCHEMA_SQL = """\
-- =====================================================================
-- NZ Fuel Price Database — MySQL schema
-- Compatible with MySQL 8.0+ / MariaDB 10.5+
-- =====================================================================

DROP DATABASE IF EXISTS nz_fuel_prices;
CREATE DATABASE nz_fuel_prices
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;
USE nz_fuel_prices;

-- ----- regions -------------------------------------------------------
CREATE TABLE regions (
    region_code      CHAR(3)        NOT NULL PRIMARY KEY,
    region_name      VARCHAR(64)    NOT NULL,
    island           ENUM('North','South') NOT NULL,
    typical_diff_c   DECIMAL(5,2)   NOT NULL COMMENT 'Typical c/L diff vs national',
    population_2023  INT UNSIGNED   NOT NULL
) ENGINE=InnoDB;

-- ----- fuel types ----------------------------------------------------
CREATE TABLE fuel_types (
    fuel_code        CHAR(3)        NOT NULL PRIMARY KEY,
    fuel_name        VARCHAR(64)    NOT NULL,
    octane_rating    TINYINT UNSIGNED NULL,
    is_petrol        BOOLEAN        NOT NULL
) ENGINE=InnoDB;

-- ----- regional weekly prices ---------------------------------------
CREATE TABLE fuel_prices (
    price_date              DATE         NOT NULL,
    region_code             CHAR(3)      NOT NULL,
    fuel_code               CHAR(3)      NOT NULL,
    price_nzd_per_litre     DECIMAL(6,3) NOT NULL,
    source                  VARCHAR(120) NOT NULL,
    PRIMARY KEY (price_date, region_code, fuel_code),
    KEY ix_region (region_code),
    KEY ix_fuel   (fuel_code),
    KEY ix_date   (price_date),
    CONSTRAINT fk_fp_region FOREIGN KEY (region_code) REFERENCES regions(region_code),
    CONSTRAINT fk_fp_fuel   FOREIGN KEY (fuel_code)   REFERENCES fuel_types(fuel_code)
) ENGINE=InnoDB;

-- ----- raw national MBIE weekly series ------------------------------
CREATE TABLE national_weekly (
    price_date              DATE         NOT NULL,
    fuel_code               CHAR(3)      NOT NULL,
    national_avg_nzd_per_l  DECIMAL(6,3) NOT NULL,
    PRIMARY KEY (price_date, fuel_code),
    CONSTRAINT fk_nw_fuel FOREIGN KEY (fuel_code) REFERENCES fuel_types(fuel_code)
) ENGINE=InnoDB;

-- ----- policy / market events ---------------------------------------
CREATE TABLE price_events (
    event_id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_date       DATE         NOT NULL,
    description      VARCHAR(255) NOT NULL,
    impact_cents     DECIMAL(5,2) NOT NULL,
    affected_region  CHAR(3)      NULL,
    KEY ix_event_date (event_date),
    CONSTRAINT fk_ev_region FOREIGN KEY (affected_region) REFERENCES regions(region_code)
) ENGINE=InnoDB;

-- ----- handy analytical views ---------------------------------------
CREATE OR REPLACE VIEW v_monthly_region AS
SELECT  DATE_FORMAT(price_date, '%Y-%m-01') AS month_start,
        region_code,
        fuel_code,
        ROUND(AVG(price_nzd_per_litre), 3) AS monthly_avg_nzd_per_l,
        MIN(price_nzd_per_litre)           AS month_min,
        MAX(price_nzd_per_litre)           AS month_max
FROM    fuel_prices
GROUP BY month_start, region_code, fuel_code;

CREATE OR REPLACE VIEW v_national_vs_region AS
SELECT  fp.price_date,
        fp.region_code,
        r.region_name,
        fp.fuel_code,
        fp.price_nzd_per_litre,
        nw.national_avg_nzd_per_l,
        ROUND(fp.price_nzd_per_litre - nw.national_avg_nzd_per_l, 3)
            AS diff_vs_national
FROM    fuel_prices fp
JOIN    regions    r  ON r.region_code = fp.region_code
JOIN    national_weekly nw
       ON nw.price_date = fp.price_date AND nw.fuel_code = fp.fuel_code;
"""


def write_sql_files(rows, national):
    with open(SQL_DIR / "schema.sql", "w", encoding="utf-8") as f:
        f.write(SCHEMA_SQL)

    with open(SQL_DIR / "data.sql", "w", encoding="utf-8") as f:
        f.write("USE nz_fuel_prices;\nSET autocommit=0;\n\n")

        # regions
        f.write("-- regions\nINSERT INTO regions VALUES\n")
        f.write(",\n".join(
            f"('{c}', '{n.replace(chr(39), chr(39)*2)}', '{i}', {d}, {p})"
            for c, n, i, d, p in REGIONS
        ))
        f.write(";\n\n")

        # fuel_types
        f.write("-- fuel_types\nINSERT INTO fuel_types VALUES\n")
        f.write(",\n".join(
            f"('{c}', '{n}', "
            f"{o if o is not None else 'NULL'}, {1 if ip else 0})"
            for c, n, o, ip in FUEL_TYPES
        ))
        f.write(";\n\n")

        # national_weekly
        f.write("-- national_weekly (real MBIE values)\n")
        natlist = sorted(national.items())
        B = 500
        for i in range(0, len(natlist), B):
            chunk = natlist[i:i + B]
            f.write("INSERT INTO national_weekly VALUES\n")
            f.write(",\n".join(
                f"('{d.isoformat()}', '{fc}', {v})" for (d, fc), v in chunk
            ))
            f.write(";\n")
        f.write("\n")

        # fuel_prices
        f.write("-- fuel_prices (16 regions x 4 fuels x weekly)\n")
        for i in range(0, len(rows), B):
            chunk = rows[i:i + B]
            f.write("INSERT INTO fuel_prices VALUES\n")
            f.write(",\n".join(
                f"('{r['price_date']}', '{r['region_code']}', '{r['fuel_code']}', "
                f"{r['price_nzd_per_litre']}, '{r['source'].replace(chr(39), chr(39)*2)}')"
                for r in chunk
            ))
            f.write(";\n")
        f.write("\n")

        # events
        f.write("-- price_events\n")
        for d, desc, c, reg in EVENTS:
            reg_sql = f"'{reg}'" if reg else "NULL"
            desc_sql = desc.replace("'", "''")
            f.write(
                "INSERT INTO price_events (event_date, description, impact_cents, "
                "affected_region) "
                f"VALUES ('{d.isoformat()}', '{desc_sql}', {c}, {reg_sql});\n"
            )
        f.write("\nCOMMIT;\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Reading MBIE raw CSV: {RAW_MBIE_CSV}")
    national = parse_mbie_weekly_csv(RAW_MBIE_CSV)
    print(f"  parsed {len(national):,} (date,fuel) national observations")

    derive_p98(national)
    print(f"  after P98 derivation: {len(national):,} obs "
          f"({len({d for d, _ in national}):,} weeks)")

    rows = fan_regions(national)
    print(f"  regional rows: {len(rows):,}  "
          f"(16 regions x 4 fuels x {len({d for d, _ in national})} weeks)")

    write_regions_csv()
    write_fuel_types_csv()
    write_events_csv()
    write_long_csv(rows)
    write_wide_csv(rows)
    write_national_csv(national)
    write_sql_files(rows, national)

    print("\nOutputs:")
    for p in sorted(DATA_DIR.iterdir()):
        print(f"  data/{p.name:<30}  {p.stat().st_size/1024:8.1f} KB")
    for p in sorted(SQL_DIR.iterdir()):
        print(f"  sql/{p.name:<30}  {p.stat().st_size/1024:8.1f} KB")


if __name__ == "__main__":
    main()
