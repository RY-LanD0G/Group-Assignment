# Data Guide — NZ Fuel Prices Dataset

This guide documents everything the visualization team needs to know about
the data layer: where files live, what they contain, and how to use them
in the React + Vite frontend.

The dataset covers **122 weeks (2024-01-05 → 2026-05-01, > 2 years)** of
New Zealand retail fuel prices at four granularities:

```
National (1 series)
    └── 16 Regions
            └── 69 Cities / Towns
                    └── 3 Brands × City (Z Energy, BP, Mobil)
```

---

## 1. File layout

```
Group Assignment/
├── public/data/              ← frontend bundle (fetch via /data/<file>)
│   ├── metadata.json         dataset summary + file dictionary
│   ├── regions.geojson       16-region simplified polygons
│   ├── regions.csv           16 rows + lat/lon
│   ├── cities.csv            69 rows + lat/lon
│   ├── fuel_types.csv        4 rows
│   ├── brands.csv            3 rows (Z, BP, Mobil)
│   ├── events.csv            policy/market events
│   ├── city_highways.csv     city → State Highway membership
│   ├── cheapest_brand_per_region_latest.csv  latest-week cheapest brand
│   ├── island_weekly.csv     North/South Island pop-weighted weekly
│   ├── national_weekly.csv   MBIE weekly + season/year/month
│   ├── national_weekly.json  {fuel: [{date, value}]} compact
│   ├── regional_weekly.json  {date: {region: {fuel: price}}}
│   ├── fuel_prices_long.csv  Region weekly (7,808 rows)
│   ├── city_fuel_prices_long.csv  City weekly (33,672 rows)
│   ├── brand_city_prices_long.csv Brand x city weekly (76,128 rows)
│   ├── brand_city_snapshot_latest.csv  latest snapshot
│   ├── fuel_prices_wide.csv
│   └── city_fuel_prices_wide.csv
├── data/                     ← source CSVs (same content, used by scripts)
├── sql/                      ← MySQL schema + bulk inserts
├── scripts/                  ← reproducible Python pipeline
└── docs/                     ← this guide + Chinese README + charts
```

---

## 2. Loading from the React frontend

### 2.1 Simple time series (Recharts)

```jsx
import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from "recharts";

export function NationalTrend() {
  const [data, setData] = useState(null);
  useEffect(() => {
    fetch("/data/national_weekly.json")
      .then(r => r.json()).then(setData);
  }, []);
  if (!data) return <p>Loading…</p>;
  // Merge into rows for recharts: [{date, P91, P95, P98, DSL}, ...]
  const dates = data.P91.map(p => p.date);
  const merged = dates.map(d => ({
    date: d,
    P91: data.P91.find(p => p.date === d).value,
    P95: data.P95.find(p => p.date === d).value,
    P98: data.P98.find(p => p.date === d).value,
    DSL: data.DSL.find(p => p.date === d).value,
  }));
  return (
    <LineChart width={900} height={400} data={merged}>
      <CartesianGrid strokeDasharray="3 3"/>
      <XAxis dataKey="date"/>
      <YAxis domain={[1.5, 4]}/>
      <Tooltip/><Legend/>
      <Line dataKey="P91" stroke="#1f77b4" dot={false}/>
      <Line dataKey="P95" stroke="#ff7f0e" dot={false}/>
      <Line dataKey="P98" stroke="#d62728" dot={false}/>
      <Line dataKey="DSL" stroke="#2ca02c" dot={false}/>
    </LineChart>
  );
}
```

### 2.2 Choropleth map (Leaflet or D3)

```jsx
import { useEffect, useState } from "react";

export function RegionMap() {
  const [geo, setGeo] = useState(null);
  const [latest, setLatest] = useState({});
  useEffect(() => {
    Promise.all([
      fetch("/data/regions.geojson").then(r => r.json()),
      fetch("/data/regional_weekly.json").then(r => r.json()),
    ]).then(([g, rw]) => {
      setGeo(g);
      const lastDate = Object.keys(rw).sort().pop();
      const map = {};
      Object.entries(rw[lastDate]).forEach(([region, fuels]) => {
        map[region] = fuels.P91;
      });
      setLatest(map);
    });
  }, []);
  // Pass `geo` to Leaflet GeoJSON layer and use `latest[code]` to colour.
}
```

### 2.3 CSV loading (Papa Parse, already in package.json)

```jsx
import Papa from "papaparse";

useEffect(() => {
  Papa.parse("/data/cities.csv", {
    download: true, header: true, dynamicTyping: true,
    complete: r => setCities(r.data),
  });
}, []);
```

---

## 3. Data dictionary — new files

### `regions.csv` (updated)

`region_code,region_name,island,typical_diff_cents,population_2023,lat,lon`

`lat`/`lon` are WGS84 centroids. Use for map markers or as the polygon
fallback if you do not load the GeoJSON.

### `cities.csv` (updated)

`city_code,city_name,region_code,diff_c_vs_region,population_2023,tag,lat,lon`

`tag` ∈ {`urban`, `secondary`, `town`, `remote`, `tourist`, `island`}.

### `regions.geojson` (new)

Standard GeoJSON `FeatureCollection`. Each feature carries
`{region_code, region_name, island, centroid_lat, centroid_lon}` in
`properties`. CRS is WGS84 (EPSG:4326). Polygons are hand-simplified —
suitable for country-scale choropleth. For pixel-accurate boundaries,
download the official Stats NZ "Regional Council 2023 (generalised)"
layer 111182 and drop it in as a replacement.

### `island_weekly.csv` (new)

`price_date,island,fuel_code,pop_weighted_avg_nzd_per_l,year,month,season`

Population-weighted average of region prices per (week, island, fuel).
Use for the "North Island vs whole NZ" granularity the brief asks for.
**976 rows** (122 weeks × 2 islands × 4 fuels).

### `national_weekly.csv` (enriched)

Now includes `year`, `month`, and `season` columns derived from
`price_date`. Seasons follow the NZ meteorological convention
(Dec–Feb = Summer, Mar–May = Autumn, Jun–Aug = Winter, Sep–Nov = Spring).

### `city_highways.csv` (new — for truck driver persona)

`city_code,city_name,region_code,highways,on_sh1,on_sh2,on_sh6`

`highways` is a pipe-separated list (e.g. `SH1|SH2`). The boolean columns
let you filter quickly. Truck-driver corridors of interest are typically
SH1 (length of NZ), SH2 (east-coast North Island), and SH6 (alpine West
Coast / Otago).

### `cheapest_brand_per_region_latest.csv` (new — for everyday driver persona)

`price_date,region_code,fuel_code,cheapest_brand,cheapest_price_nzd_per_l,all_brand_prices_json`

For the latest week, lists which of {Z, BP, Mobil} is cheapest in each
region for each fuel, plus the all-brand price map as JSON.
**52 rows** = 13 regions where any of these brands operate × 4 fuels.

### `metadata.json` (new)

Self-describing manifest of all files plus a `personas` block mapping
the three user personas (everyday_driver / truck_driver / fleet_manager)
to the files that satisfy each role's needs.

### `national_weekly.json` (new — compact)

```json
{
  "P91": [{"date": "2024-01-05", "value": 2.657}, ...],
  "P95": [...],
  "P98": [...],
  "DSL": [...]
}
```

Drop-in for any line-chart component. Used in the example above.

### `regional_weekly.json` (new — compact)

```json
{
  "2024-01-05": {
    "AUK": {"P91": 2.674, "P95": 2.838, "P98": 3.011, "DSL": 2.073},
    "WGN": {...},
    ...
  },
  "2024-01-12": {...},
  ...
}
```

Ideal for "snap to date → colour map" scrubbing animations.

---

## 4. Persona → file map

| Persona | Primary files | What they support |
|---|---|---|
| **Everyday driver** | `regions.geojson`, `cheapest_brand_per_region_latest.csv`, `cities.csv` | Map + "cheapest brand near me" lookup |
| **Truck driver** | `city_highways.csv`, `fuel_prices_long.csv`, `regional_weekly.json` | Route-based price along SH corridors, diesel focus |
| **Fleet manager** | `fuel_prices_long.csv`, `national_weekly.csv`, `island_weekly.csv`, `brand_city_prices_long.csv` | Historical aggregates, brand mix analysis |

---

## 5. Filters supported (per teacher feedback)

| Filter | Source field | Notes |
|---|---|---|
| Region | `region_code` | 16 regions |
| Fuel type | `fuel_code` | P91, P95, P98, DSL |
| Brand | `brand_code` | Z, BP, MOBIL |
| Season | `season` | derived; in `national_weekly.csv`, `island_weekly.csv` |
| Year / month | `year`, `month` | derived |
| Price range | `price_nzd_per_litre` | use `>=`/`<=` |
| State Highway | `on_sh1` etc | `city_highways.csv` |

---

## 6. Regenerating everything

The whole pipeline is deterministic (seeded). To rebuild:

```bash
python3 scripts/generate_fuel_dataset.py     # national + regional from MBIE
python3 scripts/generate_city_dataset.py     # city layer
python3 scripts/generate_brand_dataset.py    # Z/BP/Mobil layer
python3 scripts/extend_for_frontend.py       # geo + JSON + personas
```

---

## 7. MySQL (for the back-end track)

The `sql/` folder ships ready-to-import schema and data:

```bash
mysql -u root -p < sql/schema.sql
mysql -u root -p < sql/data.sql
mysql -u root -p < sql/schema_cities.sql
mysql -u root -p < sql/data_cities.sql
mysql -u root -p < sql/schema_brands.sql
mysql -u root -p < sql/data_brands.sql
```

The new `lat`/`lon` columns are present in CSVs but not yet in the
MySQL schema — they can be added with:

```sql
ALTER TABLE regions ADD COLUMN lat DECIMAL(7,4), ADD COLUMN lon DECIMAL(8,4);
ALTER TABLE cities  ADD COLUMN lat DECIMAL(7,4), ADD COLUMN lon DECIMAL(8,4);
```

---

## 8. Data lineage & honesty

| Layer | Real or derived? |
|---|---|
| National weekly | **Real** MBIE CSV |
| Premium 98 national | Derived: P95 + 17 c/L |
| Regional series | Derived: National + regional differentials |
| Auckland 2024-07-01 step | **Real** policy event (Auckland Regional Fuel Tax removed) |
| City series | Derived: region + town differentials |
| Brand × city snapshot | **Real** Petrolmate scrape (18 May 2026) |
| Brand × city history | Derived: snapshot offsets applied backwards |
| Region GeoJSON polygons | Hand-simplified (acceptable for country-scale map) |
| Centroid lat/lon | Public knowledge (Wikipedia / OSM) |

Every row in the SQL/CSV files carries a `source` column tagging its
lineage. When presenting, be transparent that lower granularity layers
are reconstructed from public differentials rather than scraped at
that granularity over two years (which would require a paid Datamine
or Gaspy commercial API).
