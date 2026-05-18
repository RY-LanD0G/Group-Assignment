"""
NZ City-Level Fuel Price Dataset Builder
========================================

Extends the regional dataset down to a town/city level. For each of the 16
NZ regions we define 3-6 main population centres or notable price points,
giving ~75 cities/towns in total.

City-level differentials are layered ON TOP of the regional series, based
on documented patterns from AA Petrolwatch and Gaspy public reports:

  - Largest urban centres in a region                  -3 ..  -1 c/L
  - Regional secondary cities                          -1 ..  +2 c/L
  - Smaller towns                                      +2 ..  +6 c/L
  - Remote rural / "captive" towns                     +6 .. +12 c/L
  - Tourist towns (Queenstown, Wānaka, Te Anau)       +8 .. +15 c/L
  - Island / very remote outliers (Great Barrier)     +30 .. +40 c/L

The output is a NEW pair of tables: `cities` and `city_fuel_prices`. The
existing `regions` / `fuel_prices` tables remain unchanged.

Author: Data team, COMPX532 Group Assignment
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

random.seed(99)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SQL_DIR = BASE_DIR / "sql"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SQL_DIR.mkdir(parents=True, exist_ok=True)

REGIONAL_LONG_CSV = DATA_DIR / "fuel_prices_long.csv"

# ---------------------------------------------------------------------------
# Cities per region:  (city_code, city_name, region_code, diff_c_vs_region,
#                      population_2023, tag)
# Tags: urban / secondary / town / remote / tourist / island
# ---------------------------------------------------------------------------

CITIES = [
    # --- Northland (NTL)
    ("WHG", "Whangārei",        "NTL",  -3.0,  56400, "urban"),
    ("KKE", "Kerikeri",         "NTL",  +5.0,   8200, "town"),
    ("KAI", "Kaitaia",          "NTL",  +8.0,   5300, "remote"),
    ("DAR", "Dargaville",       "NTL",  +6.0,   4900, "town"),

    # --- Auckland (AUK)
    ("AKC", "Auckland Central", "AUK",  -3.0, 460000, "urban"),
    ("ANS", "North Shore",      "AUK",  -2.0, 290000, "urban"),
    ("AMK", "Manukau",          "AUK",  -4.0, 410000, "urban"),
    ("PUK", "Pukekohe",         "AUK",  +1.0,  29000, "secondary"),
    ("WHE", "Waiheke Island",   "AUK", +15.0,   9800, "island"),
    ("GBI", "Great Barrier I.", "AUK", +38.0,    950, "island"),

    # --- Waikato (WKO)
    ("HAM", "Hamilton",         "WKO",  -3.0, 178500, "urban"),
    ("CAM", "Cambridge",        "WKO",  +2.0,  21300, "secondary"),
    ("TEA", "Te Awamutu",       "WKO",  +3.0,  13400, "town"),
    ("TPO", "Taupō",            "WKO",  +8.0,  27300, "tourist"),
    ("TOK", "Tokoroa",          "WKO",  +5.0,  14400, "town"),
    ("THA", "Thames",           "WKO",  +4.0,   7300, "town"),

    # --- Bay of Plenty (BOP)
    ("TGA", "Tauranga",         "BOP",  -2.0, 158300, "urban"),
    ("ROT", "Rotorua",          "BOP",  +3.0,  74000, "secondary"),
    ("WHK", "Whakatāne",        "BOP",  +5.0,  16300, "town"),
    ("TPU", "Te Puke",          "BOP",  +4.0,   9700, "town"),

    # --- Gisborne (GIS)
    ("GSB", "Gisborne",         "GIS",   0.0,  37000, "urban"),
    ("TOL", "Tolaga Bay",       "GIS", +12.0,    900, "remote"),

    # --- Hawke's Bay (HKB)
    ("NPR", "Napier",           "HKB",  -2.0,  66000, "urban"),
    ("HST", "Hastings",         "HKB",  -1.0,  53000, "urban"),
    ("HVN", "Havelock North",   "HKB",  +1.0,  15800, "secondary"),
    ("WAI", "Waipukurau",       "HKB",  +7.0,   4400, "remote"),

    # --- Taranaki (TKI)
    ("NPL", "New Plymouth",     "TKI",  -2.0,  58800, "urban"),
    ("HAW", "Hāwera",           "TKI",  +5.0,  11600, "town"),
    ("STR", "Stratford",        "TKI",  +6.0,   5800, "town"),

    # --- Manawatū-Whanganui (MWT)
    ("PMR", "Palmerston North", "MWT",  -3.0,  91500, "urban"),
    ("WHA", "Whanganui",        "MWT",  +1.0,  43500, "secondary"),
    ("LVN", "Levin",            "MWT",  +2.0,  21000, "town"),
    ("FLD", "Feilding",         "MWT",  +3.0,  17400, "town"),
    ("TMR", "Taumarunui",       "MWT",  +8.0,   4700, "remote"),
    ("OHK", "Ōhakune",          "MWT", +10.0,   1100, "tourist"),

    # --- Wellington (WGN)
    ("WLG", "Wellington Central","WGN", -3.0, 215000, "urban"),
    ("LHT", "Lower Hutt",       "WGN",  -2.0, 113000, "urban"),
    ("UHT", "Upper Hutt",       "WGN",  -1.0,  47000, "secondary"),
    ("PRA", "Porirua",          "WGN",  -1.0,  61000, "urban"),
    ("PAR", "Paraparaumu",      "WGN",  +1.0,  31000, "secondary"),
    ("MAS", "Masterton",        "WGN",  +5.0,  28500, "town"),

    # --- Tasman (TAS)
    ("RIC", "Richmond",         "TAS",   0.0,  17500, "secondary"),
    ("MOT", "Motueka",          "TAS",  +4.0,   8500, "town"),
    ("TAK", "Tākaka",           "TAS", +10.0,   1300, "remote"),

    # --- Nelson (NSN)
    ("NEL", "Nelson",           "NSN",   0.0,  54000, "urban"),
    ("STK", "Stoke",            "NSN",  +1.0,  11000, "secondary"),

    # --- Marlborough (MBH)
    ("BLE", "Blenheim",         "MBH",   0.0,  29000, "urban"),
    ("PIC", "Picton",           "MBH",  +3.0,   4500, "town"),
    ("REN", "Renwick",          "MBH",  +5.0,   2200, "town"),

    # --- West Coast (WTC)
    ("GRY", "Greymouth",        "WTC",   0.0,  10000, "urban"),
    ("WPT", "Westport",         "WTC",  +5.0,   4500, "town"),
    ("HOK", "Hokitika",         "WTC",  +3.0,   3300, "town"),
    ("RFT", "Reefton",          "WTC",  +8.0,    900, "remote"),

    # --- Canterbury (CAN)
    ("CHC", "Christchurch",     "CAN",  -3.0, 396200, "urban"),
    ("TIM", "Timaru",           "CAN",  +3.0,  29000, "secondary"),
    ("ASH", "Ashburton",        "CAN",  +2.0,  20000, "town"),
    ("RAN", "Rangiora",         "CAN",  +1.0,  19000, "secondary"),
    ("KAI2","Kaikōura",         "CAN",  +8.0,   2200, "tourist"),
    ("MET", "Methven",          "CAN", +10.0,   1900, "tourist"),

    # --- Otago (OTA)
    ("DUN", "Dunedin",          "OTA",  -3.0, 134000, "urban"),
    ("QNS", "Queenstown",       "OTA", +12.0,  29000, "tourist"),
    ("WAN", "Wānaka",           "OTA", +10.0,  10000, "tourist"),
    ("OAM", "Oamaru",           "OTA",  +3.0,  14000, "town"),
    ("ALE", "Alexandra",        "OTA",  +5.0,   6000, "town"),
    ("CRO", "Cromwell",         "OTA",  +4.0,   6300, "town"),

    # --- Southland (STL)
    ("INV", "Invercargill",     "STL",  -2.0,  56000, "urban"),
    ("GOR", "Gore",             "STL",  +2.0,  10000, "town"),
    ("TAN", "Te Anau",          "STL", +10.0,   2500, "tourist"),
    ("BLU", "Bluff",            "STL",  +5.0,   1700, "town"),
]


# ---------------------------------------------------------------------------
# 1. Load the regional weekly prices
# ---------------------------------------------------------------------------

def load_regional():
    """Returns {(date_iso, region_code, fuel_code): price}"""
    out = {}
    with REGIONAL_LONG_CSV.open() as f:
        for row in csv.DictReader(f):
            out[(row["price_date"], row["region_code"], row["fuel_code"])] = \
                float(row["price_nzd_per_litre"])
    return out


# ---------------------------------------------------------------------------
# 2. Build city series
# ---------------------------------------------------------------------------

def city_noise(seed_key: tuple, sigma_c: float = 0.9) -> float:
    rng = random.Random(hash(seed_key) & 0xFFFFFFFF)
    return rng.gauss(0.0, sigma_c) / 100.0


def build_city_rows(regional: dict) -> list[dict]:
    rows = []
    for (d, rcode, fcode), reg_p in regional.items():
        for ccode, cname, region_code, diff_c, pop, tag in CITIES:
            if region_code != rcode:
                continue
            p = reg_p + diff_c / 100.0 + city_noise((d, ccode, fcode))
            p = round(p, 3)
            rows.append({
                "price_date": d,
                "city_code": ccode,
                "region_code": region_code,
                "fuel_code": fcode,
                "price_nzd_per_litre": p,
                "source": f"Regional series + city differential ({tag})",
            })
    return rows


# ---------------------------------------------------------------------------
# 3. CSV outputs
# ---------------------------------------------------------------------------

def write_cities_csv():
    with open(DATA_DIR / "cities.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["city_code", "city_name", "region_code",
                    "diff_c_vs_region", "population_2023", "tag"])
        for c in CITIES:
            w.writerow(c)


def write_city_long(rows):
    with open(DATA_DIR / "city_fuel_prices_long.csv", "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["price_date", "city_code", "region_code", "fuel_code",
                    "price_nzd_per_litre", "source"])
        for r in rows:
            w.writerow([r["price_date"], r["city_code"], r["region_code"],
                        r["fuel_code"], r["price_nzd_per_litre"], r["source"]])


def write_city_wide(rows):
    grid = defaultdict(dict)
    for r in rows:
        grid[(r["price_date"], r["city_code"], r["region_code"])][r["fuel_code"]] = r["price_nzd_per_litre"]
    with open(DATA_DIR / "city_fuel_prices_wide.csv", "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["price_date", "city_code", "region_code",
                    "P91", "P95", "P98", "DSL"])
        for (d, c, r), vals in sorted(grid.items()):
            w.writerow([d, c, r,
                        vals.get("P91"), vals.get("P95"),
                        vals.get("P98"), vals.get("DSL")])


# ---------------------------------------------------------------------------
# 4. SQL output (append to existing schema)
# ---------------------------------------------------------------------------

CITY_SCHEMA_SQL = """\
-- =====================================================================
-- City-level extension of the NZ fuel price database
-- Run AFTER schema.sql + data.sql
-- =====================================================================

USE nz_fuel_prices;

CREATE TABLE IF NOT EXISTS cities (
    city_code         VARCHAR(5)   NOT NULL PRIMARY KEY,
    city_name         VARCHAR(64)  NOT NULL,
    region_code       CHAR(3)      NOT NULL,
    diff_c_vs_region  DECIMAL(5,2) NOT NULL,
    population_2023   INT UNSIGNED NOT NULL,
    tag               ENUM('urban','secondary','town','remote','tourist','island')
                      NOT NULL,
    KEY ix_city_region (region_code),
    CONSTRAINT fk_city_region FOREIGN KEY (region_code)
        REFERENCES regions(region_code)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS city_fuel_prices (
    price_date              DATE         NOT NULL,
    city_code               VARCHAR(5)   NOT NULL,
    region_code             CHAR(3)      NOT NULL,
    fuel_code               CHAR(3)      NOT NULL,
    price_nzd_per_litre     DECIMAL(6,3) NOT NULL,
    source                  VARCHAR(120) NOT NULL,
    PRIMARY KEY (price_date, city_code, fuel_code),
    KEY ix_cfp_city   (city_code),
    KEY ix_cfp_region (region_code),
    KEY ix_cfp_fuel   (fuel_code),
    KEY ix_cfp_date   (price_date),
    CONSTRAINT fk_cfp_city   FOREIGN KEY (city_code)   REFERENCES cities(city_code),
    CONSTRAINT fk_cfp_region FOREIGN KEY (region_code) REFERENCES regions(region_code),
    CONSTRAINT fk_cfp_fuel   FOREIGN KEY (fuel_code)   REFERENCES fuel_types(fuel_code)
) ENGINE=InnoDB;

CREATE OR REPLACE VIEW v_monthly_city AS
SELECT  DATE_FORMAT(price_date, '%Y-%m-01') AS month_start,
        city_code, region_code, fuel_code,
        ROUND(AVG(price_nzd_per_litre), 3) AS monthly_avg_nzd_per_l,
        MIN(price_nzd_per_litre) AS month_min,
        MAX(price_nzd_per_litre) AS month_max
FROM city_fuel_prices
GROUP BY month_start, city_code, region_code, fuel_code;

CREATE OR REPLACE VIEW v_city_vs_region AS
SELECT  cfp.price_date, cfp.city_code, c.city_name, cfp.region_code,
        cfp.fuel_code, cfp.price_nzd_per_litre,
        fp.price_nzd_per_litre AS region_price,
        ROUND(cfp.price_nzd_per_litre - fp.price_nzd_per_litre, 3)
            AS diff_vs_region
FROM    city_fuel_prices cfp
JOIN    cities c       ON c.city_code = cfp.city_code
JOIN    fuel_prices fp ON fp.price_date  = cfp.price_date
                      AND fp.region_code = cfp.region_code
                      AND fp.fuel_code   = cfp.fuel_code;
"""


def write_city_sql_files(rows):
    with open(SQL_DIR / "schema_cities.sql", "w", encoding="utf-8") as f:
        f.write(CITY_SCHEMA_SQL)

    with open(SQL_DIR / "data_cities.sql", "w", encoding="utf-8") as f:
        f.write("USE nz_fuel_prices;\nSET autocommit=0;\n\n")

        # cities
        f.write("-- cities\nINSERT INTO cities VALUES\n")
        f.write(",\n".join(
            f"('{c[0]}', '{c[1].replace(chr(39), chr(39)*2)}', '{c[2]}', "
            f"{c[3]}, {c[4]}, '{c[5]}')"
            for c in CITIES
        ))
        f.write(";\n\n")

        # city_fuel_prices
        f.write("-- city_fuel_prices (long)\n")
        B = 500
        for i in range(0, len(rows), B):
            chunk = rows[i:i + B]
            f.write("INSERT INTO city_fuel_prices VALUES\n")
            f.write(",\n".join(
                f"('{r['price_date']}', '{r['city_code']}', '{r['region_code']}', "
                f"'{r['fuel_code']}', {r['price_nzd_per_litre']}, "
                f"'{r['source'].replace(chr(39), chr(39)*2)}')"
                for r in chunk
            ))
            f.write(";\n")
        f.write("\nCOMMIT;\n")


# ---------------------------------------------------------------------------
# 5. Main
# ---------------------------------------------------------------------------

def main():
    print("Loading regional dataset...")
    regional = load_regional()
    print(f"  regional rows: {len(regional):,}")

    print("Building city-level dataset...")
    rows = build_city_rows(regional)
    print(f"  cities defined: {len(CITIES)}")
    print(f"  city rows: {len(rows):,}")
    weeks = len({r['price_date'] for r in rows})
    print(f"  weeks: {weeks}")

    write_cities_csv()
    write_city_long(rows)
    write_city_wide(rows)
    write_city_sql_files(rows)

    print("\nNew outputs:")
    for fname in ["cities.csv", "city_fuel_prices_long.csv",
                  "city_fuel_prices_wide.csv"]:
        p = DATA_DIR / fname
        print(f"  data/{fname:<32}  {p.stat().st_size/1024:8.1f} KB")
    for fname in ["schema_cities.sql", "data_cities.sql"]:
        p = SQL_DIR / fname
        print(f"  sql/{fname:<32}  {p.stat().st_size/1024:8.1f} KB")


if __name__ == "__main__":
    main()
