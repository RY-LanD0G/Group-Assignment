"""
Frontend data extension pipeline
=================================

Builds on top of the existing CSV/SQL dataset to produce everything the
React+Vite frontend needs:

  1. lat/lon centroids for 16 regions and 69 cities
  2. NZ regions GeoJSON with simplified polygons (for choropleth)
  3. North Island / South Island weekly aggregates
  4. season/year/month derived fields
  5. compact JSON exports under public/data/ (React-friendly)
  6. persona helpers:
       - state-highway corridor membership (truck driver view)
       - cheapest brand per region snapshot (everyday driver view)

Run from the project root:
    python3 scripts/extend_for_frontend.py
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data"
PUBLIC_DATA = BASE / "public" / "data"
PUBLIC_DATA.mkdir(parents=True, exist_ok=True)
SQL_DIR = BASE / "sql"

# ---------------------------------------------------------------------------
# 1. Region & city centroids (lat, lon)
# Centroids cross-checked against Wikipedia / OSM public coordinates.
# ---------------------------------------------------------------------------

REGION_COORDS = {
    # code: (lat, lon, bbox_min_lon, bbox_min_lat, bbox_max_lon, bbox_max_lat)
    "NTL": (-35.60, 173.90, 172.90, -36.50, 174.80, -34.30),
    "AUK": (-36.85, 174.76, 174.30, -37.30, 175.40, -36.30),
    "WKO": (-37.78, 175.28, 174.50, -38.90, 176.80, -36.80),
    "BOP": (-37.93, 176.95, 175.80, -38.80, 178.10, -37.20),
    "GIS": (-38.50, 177.90, 177.20, -39.10, 178.80, -37.50),
    "HKB": (-39.50, 176.85, 175.80, -40.50, 178.10, -38.80),
    "TKI": (-39.34, 174.14, 173.50, -40.00, 175.30, -38.80),
    "MWT": (-39.80, 175.50, 174.50, -41.00, 176.50, -38.80),
    "WGN": (-41.10, 175.30, 174.60, -41.60, 176.20, -40.70),
    "TAS": (-41.40, 172.85, 171.80, -41.90, 173.70, -40.40),
    "NSN": (-41.27, 173.28, 173.10, -41.40, 173.50, -41.10),
    "MBH": (-41.70, 173.85, 173.20, -42.30, 174.60, -41.10),
    "WTC": (-42.80, 171.30, 169.50, -44.30, 172.30, -41.40),
    "CAN": (-43.70, 171.80, 169.80, -45.10, 174.10, -42.20),
    "OTA": (-45.40, 170.00, 167.80, -46.70, 171.30, -43.70),
    "STL": (-46.20, 168.30, 166.50, -47.40, 169.40, -45.40),
}

CITY_COORDS = {
    # Northland
    "WHG": (-35.73, 174.32), "KKE": (-35.23, 173.95),
    "KAI": (-35.11, 173.26), "DAR": (-35.94, 173.88),
    # Auckland
    "AKC": (-36.85, 174.76), "ANS": (-36.79, 174.74),
    "AMK": (-36.99, 174.88), "PUK": (-37.20, 174.91),
    "WHE": (-36.80, 175.10), "GBI": (-36.20, 175.40),
    # Waikato
    "HAM": (-37.79, 175.28), "CAM": (-37.89, 175.47),
    "TEA": (-38.01, 175.32), "TPO": (-38.69, 176.07),
    "TOK": (-38.22, 175.87), "THA": (-37.14, 175.54),
    # Bay of Plenty
    "TGA": (-37.69, 176.17), "ROT": (-38.14, 176.25),
    "WHK": (-37.96, 176.99), "TPU": (-37.79, 176.34),
    # Gisborne
    "GSB": (-38.66, 178.02), "TOL": (-38.37, 178.30),
    # Hawke's Bay
    "NPR": (-39.49, 176.91), "HST": (-39.64, 176.85),
    "HVN": (-39.67, 176.88), "WAI": (-40.00, 176.55),
    # Taranaki
    "NPL": (-39.06, 174.08), "HAW": (-39.59, 174.28),
    "STR": (-39.34, 174.28),
    # Manawatū-Whanganui
    "PMR": (-40.36, 175.61), "WHA": (-39.93, 175.05),
    "LVN": (-40.62, 175.28), "FLD": (-40.23, 175.57),
    "TMR": (-38.88, 175.27), "OHK": (-39.42, 175.40),
    # Wellington
    "WLG": (-41.29, 174.78), "LHT": (-41.21, 174.91),
    "UHT": (-41.13, 175.06), "PRA": (-41.13, 174.84),
    "PAR": (-40.92, 175.00), "MAS": (-40.96, 175.66),
    # Tasman
    "RIC": (-41.34, 173.18), "MOT": (-41.11, 173.01),
    "TAK": (-40.85, 172.81),
    # Nelson
    "NEL": (-41.27, 173.28), "STK": (-41.32, 173.24),
    # Marlborough
    "BLE": (-41.51, 173.96), "PIC": (-41.29, 174.00),
    "REN": (-41.50, 173.84),
    # West Coast
    "GRY": (-42.45, 171.21), "WPT": (-41.75, 171.60),
    "HOK": (-42.72, 170.97), "RFT": (-42.12, 171.86),
    # Canterbury
    "CHC": (-43.53, 172.64), "TIM": (-44.40, 171.25),
    "ASH": (-43.90, 171.74), "RAN": (-43.30, 172.59),
    "KAI2": (-42.40, 173.68), "MET": (-43.63, 171.65),
    # Otago
    "DUN": (-45.88, 170.50), "QNS": (-45.03, 168.66),
    "WAN": (-44.70, 169.13), "OAM": (-45.10, 170.97),
    "ALE": (-45.25, 169.39), "CRO": (-45.05, 169.20),
    # Southland
    "INV": (-46.41, 168.36), "GOR": (-46.10, 168.94),
    "TAN": (-45.41, 167.72), "BLU": (-46.60, 168.34),
}

# ---------------------------------------------------------------------------
# 2. Append lat/lon to regions.csv and cities.csv
# ---------------------------------------------------------------------------

def add_coords_to_regions():
    src = DATA_DIR / "regions.csv"
    dst = PUBLIC_DATA / "regions.csv"
    rows = list(csv.DictReader(src.open()))
    for r in rows:
        lat, lon, *_ = REGION_COORDS[r["region_code"]]
        r["lat"] = lat
        r["lon"] = lon
    fields = list(rows[0].keys())
    with dst.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader(); w.writerows(rows)
    return rows


def add_coords_to_cities():
    src = DATA_DIR / "cities.csv"
    dst = PUBLIC_DATA / "cities.csv"
    rows = list(csv.DictReader(src.open()))
    for r in rows:
        lat, lon = CITY_COORDS[r["city_code"]]
        r["lat"] = lat
        r["lon"] = lon
    fields = list(rows[0].keys())
    with dst.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader(); w.writerows(rows)
    return rows


# ---------------------------------------------------------------------------
# 3. NZ regions GeoJSON (hand-coded simplified polygons)
#    Detail level: suitable for country-scale choropleth.
#    For production-grade boundaries, download Stats NZ
#    "Regional Council 2023 (generalised)" GeoJSON and replace.
# ---------------------------------------------------------------------------

# Simplified polygon vertices per region. Each is a ring (lon, lat) tuples.
# These are roughly approximate — accurate enough for a country-scale map.
REGION_POLYGONS = {
    "NTL": [(172.95, -34.55), (174.45, -34.40), (174.85, -35.45),
            (174.30, -36.45), (173.90, -36.45), (173.40, -36.20),
            (172.95, -34.55)],
    "AUK": [(174.30, -36.40), (175.30, -36.30), (175.40, -36.70),
            (175.05, -37.20), (174.65, -37.25), (174.30, -37.05),
            (174.30, -36.40)],
    "WKO": [(174.55, -36.95), (175.50, -36.85), (176.40, -37.10),
            (176.50, -38.45), (175.40, -38.80), (174.65, -38.20),
            (174.55, -36.95)],
    "BOP": [(175.80, -37.20), (177.45, -37.30), (178.05, -37.95),
            (177.40, -38.70), (176.30, -38.70), (175.80, -37.95),
            (175.80, -37.20)],
    "GIS": [(177.40, -37.50), (178.65, -37.85), (178.55, -38.85),
            (177.55, -39.00), (177.20, -38.50), (177.40, -37.50)],
    "HKB": [(175.95, -38.80), (177.30, -38.95), (178.05, -39.55),
            (177.50, -40.40), (176.20, -40.45), (175.95, -39.65),
            (175.95, -38.80)],
    "TKI": [(173.55, -38.85), (175.20, -38.95), (175.10, -39.85),
            (174.10, -39.95), (173.65, -39.50), (173.55, -38.85)],
    "MWT": [(174.65, -38.85), (175.85, -39.20), (176.45, -39.95),
            (176.20, -40.90), (174.80, -40.80), (174.55, -39.70),
            (174.65, -38.85)],
    "WGN": [(174.65, -40.65), (176.15, -40.75), (176.00, -41.55),
            (174.85, -41.60), (174.65, -41.10), (174.65, -40.65)],
    "TAS": [(171.85, -40.45), (173.45, -40.50), (173.65, -41.45),
            (172.80, -41.85), (171.95, -41.60), (171.85, -40.45)],
    "NSN": [(173.13, -41.10), (173.45, -41.15), (173.45, -41.40),
            (173.13, -41.40), (173.13, -41.10)],
    "MBH": [(173.25, -41.15), (174.55, -41.20), (174.50, -41.90),
            (173.65, -42.25), (173.20, -42.05), (173.25, -41.15)],
    "WTC": [(169.55, -41.45), (172.25, -41.50), (172.30, -42.85),
            (170.45, -44.25), (169.55, -43.60), (169.55, -41.45)],
    "CAN": [(170.45, -42.25), (173.95, -42.30), (174.05, -42.85),
            (173.05, -44.55), (171.20, -45.05), (170.05, -44.10),
            (170.45, -42.25)],
    "OTA": [(167.85, -43.75), (171.25, -44.20), (171.15, -45.50),
            (170.55, -46.65), (168.45, -46.60), (167.85, -45.40),
            (167.85, -43.75)],
    "STL": [(166.55, -45.50), (169.30, -45.45), (169.35, -46.65),
            (168.50, -47.30), (167.40, -47.30), (166.55, -46.55),
            (166.55, -45.50)],
}

REGION_NAME = {
    "NTL": "Northland", "AUK": "Auckland", "WKO": "Waikato",
    "BOP": "Bay of Plenty", "GIS": "Gisborne", "HKB": "Hawke's Bay",
    "TKI": "Taranaki", "MWT": "Manawatū-Whanganui", "WGN": "Wellington",
    "TAS": "Tasman", "NSN": "Nelson", "MBH": "Marlborough",
    "WTC": "West Coast", "CAN": "Canterbury", "OTA": "Otago",
    "STL": "Southland",
}

REGION_ISLAND = {
    "NTL": "North", "AUK": "North", "WKO": "North", "BOP": "North",
    "GIS": "North", "HKB": "North", "TKI": "North", "MWT": "North",
    "WGN": "North",
    "TAS": "South", "NSN": "South", "MBH": "South", "WTC": "South",
    "CAN": "South", "OTA": "South", "STL": "South",
}


def write_regions_geojson():
    features = []
    for code, ring in REGION_POLYGONS.items():
        lat, lon, *_ = REGION_COORDS[code]
        features.append({
            "type": "Feature",
            "properties": {
                "region_code": code,
                "region_name": REGION_NAME[code],
                "island": REGION_ISLAND[code],
                "centroid_lat": lat,
                "centroid_lon": lon,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[lon, lat] for lon, lat in ring]],
            },
        })
    gj = {
        "type": "FeatureCollection",
        "metadata": {
            "name": "NZ Regional Council Areas (simplified)",
            "source": "Hand-coded simplified polygons. For production-quality "
                      "boundaries, download from Stats NZ DataFinder "
                      "(layer 111182, Regional Council 2023 generalised).",
            "crs": "WGS84 / EPSG:4326",
        },
        "features": features,
    }
    out = PUBLIC_DATA / "regions.geojson"
    out.write_text(json.dumps(gj, ensure_ascii=False, indent=1))
    return out


# ---------------------------------------------------------------------------
# 4. Season / year / month / island aggregates
# ---------------------------------------------------------------------------

def nz_season(d: date) -> str:
    m = d.month
    if m in (12, 1, 2): return "Summer"
    if m in (3, 4, 5):  return "Autumn"
    if m in (6, 7, 8):  return "Winter"
    return "Spring"


def write_national_weekly_enriched():
    src = DATA_DIR / "national_weekly.csv"
    rows = []
    with src.open() as f:
        for r in csv.DictReader(f):
            d = date.fromisoformat(r["price_date"])
            r["year"] = d.year
            r["month"] = d.month
            r["season"] = nz_season(d)
            rows.append(r)
    out = PUBLIC_DATA / "national_weekly.csv"
    fields = ["price_date", "fuel_code", "national_avg_nzd_per_l",
              "year", "month", "season"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader(); w.writerows(rows)
    return rows


def write_island_weekly(regions: list[dict]):
    """Aggregate region prices into North / South Island weekly averages."""
    pop = {r["region_code"]: int(r["population_2023"]) for r in regions}
    isl_of = {r["region_code"]: REGION_ISLAND[r["region_code"]] for r in regions}
    by_key = defaultdict(lambda: defaultdict(list))   # (date,island,fuel) -> [(price,pop)]
    with (DATA_DIR / "fuel_prices_long.csv").open() as f:
        for r in csv.DictReader(f):
            island = isl_of[r["region_code"]]
            p = float(r["price_nzd_per_litre"])
            w = pop[r["region_code"]]
            by_key[(r["price_date"], island, r["fuel_code"])][1] = None  # touch
            by_key[(r["price_date"], island, r["fuel_code"])][0] = \
                by_key[(r["price_date"], island, r["fuel_code"])].get(0, []) + [(p, w)]
    rows = []
    for (d, isl, fc), payload in by_key.items():
        pts = payload[0]
        s_num = sum(p * w for p, w in pts)
        s_den = sum(w for _, w in pts)
        avg = round(s_num / s_den, 3)
        dd = date.fromisoformat(d)
        rows.append({
            "price_date": d, "island": isl, "fuel_code": fc,
            "pop_weighted_avg_nzd_per_l": avg,
            "year": dd.year, "month": dd.month, "season": nz_season(dd),
        })
    rows.sort(key=lambda r: (r["price_date"], r["island"], r["fuel_code"]))
    out = PUBLIC_DATA / "island_weekly.csv"
    fields = list(rows[0].keys())
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader(); w.writerows(rows)
    return rows


# ---------------------------------------------------------------------------
# 5. Persona helpers
# ---------------------------------------------------------------------------

# State Highway corridors (simplified mapping of cities -> SH route they sit on)
# Source: NZ Transport Agency standard highway routing.
CITY_HIGHWAYS = {
    # SH1 (length of NZ)
    "WHG": ["SH1"], "AKC": ["SH1"], "ANS": ["SH1"], "AMK": ["SH1"],
    "PUK": ["SH1"], "HAM": ["SH1"], "CAM": ["SH1"], "TOK": ["SH1"],
    "TPO": ["SH1"], "TMR": ["SH1"], "PMR": ["SH1"], "WLG": ["SH1"],
    "LHT": ["SH1"], "UHT": ["SH1"], "PRA": ["SH1"], "PAR": ["SH1"],
    "BLE": ["SH1"], "KAI2": ["SH1"], "CHC": ["SH1"], "ASH": ["SH1"],
    "TIM": ["SH1"], "OAM": ["SH1"], "DUN": ["SH1"], "GOR": ["SH1"],
    "INV": ["SH1"], "BLU": ["SH1"],
    # SH2 (East coast North Island)
    "THA": ["SH2"], "TGA": ["SH2"], "WHK": ["SH2"], "GSB": ["SH2"],
    "TOL": ["SH2"], "NPR": ["SH2"], "HST": ["SH2"], "HVN": ["SH2"],
    "WAI": ["SH2"], "MAS": ["SH2"],
    # SH3 (Western North Island)
    "TEA": ["SH3"], "NPL": ["SH3"], "STR": ["SH3"], "HAW": ["SH3"],
    "WHA": ["SH3"], "FLD": ["SH3"],
    # SH4 (Whanganui–Te Kuiti)
    "OHK": ["SH4"],
    # SH5 (Napier–Taupo)
    # already on SH1 / SH2 for major endpoints
    # SH6 (West Coast / Otago lakes)
    "NEL": ["SH6"], "STK": ["SH6"], "RIC": ["SH6"], "MOT": ["SH6"],
    "WPT": ["SH6"], "GRY": ["SH6"], "HOK": ["SH6"], "WAN": ["SH6"],
    "CRO": ["SH6"], "QNS": ["SH6"],
    # SH7 (Lewis Pass)
    "REN": ["SH7"], "RFT": ["SH7"], "RAN": ["SH7"],
    # SH8 (Central Otago)
    "ALE": ["SH8"], "MET": ["SH8"],
    # SH10 / SH12 (Northland west)
    "KKE": ["SH10"], "KAI": ["SH10"], "DAR": ["SH12"],
    # SH25 (Coromandel)
    # SH35 (East Cape — Gisborne loop)
    # SH94 (Te Anau)
    "TAN": ["SH94"],
    # Islands / remote
    "WHE": [], "GBI": [], "ROT": ["SH5"], "TAK": ["SH60"],
    "TPU": ["SH2"], "LVN": ["SH1"], "PIC": ["SH1"],
}


def write_city_highway_map(cities: list[dict]):
    rows = []
    for c in cities:
        sh = CITY_HIGHWAYS.get(c["city_code"], [])
        rows.append({
            "city_code": c["city_code"],
            "city_name": c["city_name"],
            "region_code": c["region_code"],
            "highways": "|".join(sh),
            "on_sh1": "SH1" in sh,
            "on_sh2": "SH2" in sh,
            "on_sh6": "SH6" in sh,
        })
    out = PUBLIC_DATA / "city_highways.csv"
    fields = list(rows[0].keys())
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader(); w.writerows(rows)
    return rows


def write_cheapest_brand_per_region():
    """For the latest week, pick the cheapest brand per (region, fuel)."""
    rows = []
    by_key = defaultdict(list)
    with (DATA_DIR / "brand_city_prices_long.csv").open() as f:
        reader = csv.DictReader(f)
        for r in reader:
            by_key[r["price_date"]].append(r)
    last = max(by_key)
    agg = defaultdict(list)  # (region, fuel, brand) -> [prices]
    for r in by_key[last]:
        key = (r["region_code"], r["fuel_code"], r["brand_code"])
        agg[key].append(float(r["price_nzd_per_litre"]))
    region_fuel_brand = {(k[0], k[1]): {} for k in agg}
    for (region, fuel, brand), vals in agg.items():
        region_fuel_brand[(region, fuel)][brand] = round(sum(vals) / len(vals), 3)
    for (region, fuel), brands in region_fuel_brand.items():
        cheapest_brand = min(brands, key=brands.get)
        rows.append({
            "price_date": last,
            "region_code": region,
            "fuel_code": fuel,
            "cheapest_brand": cheapest_brand,
            "cheapest_price_nzd_per_l": brands[cheapest_brand],
            "all_brand_prices_json": json.dumps(brands, separators=(",", ":")),
        })
    rows.sort(key=lambda r: (r["region_code"], r["fuel_code"]))
    out = PUBLIC_DATA / "cheapest_brand_per_region_latest.csv"
    fields = list(rows[0].keys())
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader(); w.writerows(rows)
    return rows


# ---------------------------------------------------------------------------
# 6. JSON exports
# ---------------------------------------------------------------------------

def csv_to_json(src: Path, dst: Path):
    """Plain JSON array of objects."""
    rows = list(csv.DictReader(src.open()))
    dst.write_text(json.dumps(rows, ensure_ascii=False))


def compact_national_json():
    """Pivot national weekly into {fuel: [{date, value}]} for line charts."""
    by_fuel = defaultdict(list)
    with (DATA_DIR / "national_weekly.csv").open() as f:
        for r in csv.DictReader(f):
            by_fuel[r["fuel_code"]].append({
                "date": r["price_date"],
                "value": float(r["national_avg_nzd_per_l"]),
            })
    for fc in by_fuel:
        by_fuel[fc].sort(key=lambda x: x["date"])
    out = PUBLIC_DATA / "national_weekly.json"
    out.write_text(json.dumps(by_fuel, ensure_ascii=False))


def compact_region_json():
    """{date: {region: {fuel: price}}}"""
    by_date = defaultdict(lambda: defaultdict(dict))
    with (DATA_DIR / "fuel_prices_long.csv").open() as f:
        for r in csv.DictReader(f):
            by_date[r["price_date"]][r["region_code"]][r["fuel_code"]] = \
                float(r["price_nzd_per_litre"])
    out = PUBLIC_DATA / "regional_weekly.json"
    out.write_text(json.dumps(by_date, ensure_ascii=False))


def write_metadata():
    meta = {
        "dataset": "NZ Fuel Prices — Frontend Bundle",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "weeks_covered": 122,
        "date_range": ["2024-01-05", "2026-05-01"],
        "fuels": ["P91", "P95", "P98", "DSL"],
        "regions": 16,
        "cities": 69,
        "brands": ["Z", "BP", "MOBIL"],
        "files": {
            "regions.csv": "16 regions w/ centroid lat/lon",
            "cities.csv": "69 cities w/ lat/lon and region_code",
            "fuel_types.csv": "4 fuel types",
            "brands.csv": "3 brands (Z, BP, Mobil)",
            "events.csv": "Policy events",
            "regions.geojson": "Simplified region polygons (choropleth)",
            "national_weekly.csv": "MBIE national weekly + season/year/month",
            "national_weekly.json": "Pivoted by fuel: {fuel: [{date, value}]}",
            "island_weekly.csv": "Population-weighted North/South Island weekly avg",
            "fuel_prices_long.csv": "Region weekly (7,808 rows)",
            "city_fuel_prices_long.csv": "City weekly (33,672 rows)",
            "brand_city_prices_long.csv": "Brand x city weekly (76,128 rows)",
            "regional_weekly.json": "{date: {region: {fuel: price}}} compact",
            "city_highways.csv": "City -> State Highway mapping (truck driver persona)",
            "cheapest_brand_per_region_latest.csv": "Cheapest brand per region (latest week)",
        },
        "personas": {
            "everyday_driver": ["regions.geojson", "cheapest_brand_per_region_latest.csv",
                                "cities.csv"],
            "truck_driver": ["city_highways.csv", "fuel_prices_long.csv",
                             "regional_weekly.json"],
            "fleet_manager": ["fuel_prices_long.csv", "national_weekly.csv",
                              "island_weekly.csv", "brand_city_prices_long.csv"],
        },
    }
    (PUBLIC_DATA / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("== Step 1: add lat/lon to regions.csv, cities.csv ==")
    regions = add_coords_to_regions()
    cities = add_coords_to_cities()
    print(f"  regions: {len(regions)}   cities: {len(cities)}")

    print("== Step 2: write NZ regions GeoJSON ==")
    write_regions_geojson()

    print("== Step 3: national_weekly enriched (season/year/month) ==")
    write_national_weekly_enriched()

    print("== Step 4: island_weekly aggregate ==")
    isl = write_island_weekly(regions)
    print(f"  island rows: {len(isl)}")

    print("== Step 5: persona helpers ==")
    hw = write_city_highway_map(cities)
    print(f"  city_highways rows: {len(hw)}")
    cheap = write_cheapest_brand_per_region()
    print(f"  cheapest_brand_per_region rows: {len(cheap)}")

    print("== Step 6: copy core CSVs + compact JSON ==")
    # the long CSVs are already in public/data from the earlier work; copy
    # the smaller maintained ones now (regions/cities already overwritten).
    for fn in ["fuel_types.csv", "brands.csv", "events.csv"]:
        (PUBLIC_DATA / fn).write_text((DATA_DIR / fn).read_text())
    compact_national_json()
    compact_region_json()
    write_metadata()

    print("\n== Outputs in public/data ==")
    for p in sorted(PUBLIC_DATA.iterdir()):
        if p.is_file():
            print(f"  {p.name:<46} {p.stat().st_size/1024:9.1f} KB")


if __name__ == "__main__":
    main()
