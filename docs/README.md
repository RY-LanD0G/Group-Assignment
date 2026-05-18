# NZ Fuel Prices Dataset — COMPX532 数据子任务

## 概述

本数据集覆盖 **新西兰全部 16 个 Regional Council 区域** × **4 种燃料**
（Regular 91、Premium 95、Premium 98、Automotive Diesel），
时间跨度 **2024-01-05 至 2026-05-01（122 周，超过 2 年）**，
共 **7,808 条** 周度记录，可直接导入 MySQL 用于下一阶段的可视化。

## 数据来源与方法论

1. **国家级周度均价**：来自 MBIE《Weekly Fuel Price Monitoring》官方 CSV
   （`weekly-table.csv`，原始字段 `Adjusted retail price`，单位 NZD c/L）。
   MBIE 直接发布 Regular Petrol（91）、Premium Petrol 95R、Diesel 三个序列。
2. **Premium 98**：MBIE 不单独发布 98 号油价格。按 NZ 市场标准价差，
   `P98 = P95 + 17.0 c/L`，并在 `source` 字段标记为"派生"。
3. **16 个大区**：使用 Stats NZ 标准 Regional Council 划分。每个大区以
   AA Petrolwatch / Stats NZ 历年公开的区域价差为基准，相对全国均价应用一个
   差额（例如 West Coast +12 c/L、Auckland −6 c/L、Wellington −3 c/L 等）。
4. **奥克兰区域燃油税事件**：2024-07-01 起 11.5 c/L 区域油税终止。脚本在
   2024-07-01 之前给 Auckland 加 +5 c/L，之后改为 −6 c/L，从而真实反映了
   政策变更带来的价格台阶。
5. **周度噪声**：每条 (date, region, fuel) 记录在确定性差额基础上叠加一个
   `σ = 1.2 c/L` 的高斯噪声（`random.seed(42)`，可复现），用以模拟站间价格
   离散度。

## 文件清单

```
Group Assignment/
├── data/
│   ├── regions.csv                    16 个大区基础信息
│   ├── fuel_types.csv                 4 种燃料定义
│   ├── events.csv                     政策/市场事件
│   ├── national_weekly.csv            MBIE 原始国家周度均价
│   ├── fuel_prices_long.csv           长表（区级，主表，7,808 行）
│   ├── fuel_prices_wide.csv           宽表（每行 P91/P95/P98/DSL）
│   ├── cities.csv                     69 个主要城镇定义
│   ├── city_fuel_prices_long.csv      城镇长表（33,672 行）
│   ├── city_fuel_prices_wide.csv      城镇宽表
│   ├── brands.csv                     3 个主流连锁 (Z/BP/Mobil)
│   ├── brand_city_prices_long.csv     品牌×城镇长表（76,128 行）
│   └── brand_city_snapshot_latest.csv 最新周品牌快照
├── sql/
│   ├── schema.sql                     MySQL 8.0+ DDL（核心 5 表）
│   ├── data.sql                       批量 INSERT（regions/fuels/national/prices/events）
│   ├── schema_cities.sql              城镇扩展表 DDL
│   ├── data_cities.sql                城镇数据 INSERT
│   ├── schema_brands.sql              品牌扩展表 DDL
│   └── data_brands.sql                品牌数据 INSERT
├── scripts/
│   ├── generate_fuel_dataset.py       区级数据生成（从 MBIE CSV 构建）
│   ├── generate_city_dataset.py       城镇级派生（叠加城镇差额）
│   ├── scraped_brand_snapshot.json    Petrolmate 真实抓取快照 (2026-05-18)
│   └── generate_brand_dataset.py      品牌 × 城镇派生
└── docs/
    ├── README.md                      本文件
    ├── national_trend.png             全国周度趋势
    ├── regional_snapshot.png          区域横截面对比
    ├── city_trend_p91.png             选定城市 P91 时间序列
    └── city_top_bottom.png            最便宜 vs 最贵的 10 个城镇
```

## MySQL 数据库结构

| 表 | 用途 |
|---|---|
| `regions` | 16 个大区，含人口、典型差价 |
| `fuel_types` | 4 种燃料定义 |
| `fuel_prices` | 区级事实表：(price_date, region_code, fuel_code) 联合主键 |
| `national_weekly` | MBIE 原始国家周度价 |
| `price_events` | 政策/市场事件 |
| `cities` | 69 个主要城镇（每区 2-6 个），含 tag 分类 |
| `city_fuel_prices` | 城镇事实表：(price_date, city_code, fuel_code) 联合主键 |
| `brands` | 3 个主流连锁（Z Energy、BP、Mobil） |
| `brand_city_prices` | 品牌×城镇事实表：(price_date, brand_code, city_code, fuel_code) 联合主键 |
| `v_monthly_region`（视图） | 按月、按区聚合 |
| `v_national_vs_region`（视图） | 区域 vs 全国差额 |
| `v_monthly_city`（视图） | 按月、按城镇聚合 |
| `v_city_vs_region`（视图） | 城镇 vs 所在区差额 |
| `v_brand_monthly_city`（视图） | 品牌×城镇月度聚合 |
| `v_brand_vs_market`（视图） | 品牌 vs 城镇市场均价 |

### 城镇分类（tag 字段）

- `urban` —— 区域主要城市中心（CBD/大区域中心）
- `secondary` —— 二级城市/卫星城
- `town` —— 一般城镇
- `remote` —— 偏远地区
- `tourist` —— 旅游城镇（Queenstown、Wānaka、Te Anau 等价格更高）
- `island` —— 离岛（Waiheke、Great Barrier，价差最大）

## 导入步骤

```bash
mysql -u root -p < sql/schema.sql
mysql -u root -p < sql/data.sql
mysql -u root -p < sql/schema_cities.sql      # 城镇扩展
mysql -u root -p < sql/data_cities.sql
mysql -u root -p < sql/schema_brands.sql      # 连锁品牌扩展
mysql -u root -p < sql/data_brands.sql
```

## 连锁加油站数据说明（Z / BP / Mobil）

**数据来源（真实爬取）**: 2026-05-18 从 Petrolmate.com.au 抓取的公开品牌页面，提供：
- Z Energy: 66 个 NZ 站点，覆盖 10 个大区，全网均价 329.4 c/L
- BP: 109 个 NZ 站点，覆盖 13 个大区（NZ 最大连锁），均价 330.3 c/L
- Mobil: 73 个 NZ 站点，覆盖 8 个大区，均价 324.9 c/L

**历史回填方法学**: 对每个 (brand, region) 计算其相对该区市场均价的固定 offset（如 Mobil 在 BOP −9.5 c/L、BP 在 WGN +3.6 c/L），然后将该 offset 应用到 122 周的城镇基础序列上 + 小噪声，重建 2 年品牌×城镇周度历史。**仅生成"该品牌实际有站点"的 region 数据**——例如 Mobil 不在 Northland，则 Northland 城市没有 Mobil 价格记录。

总记录数：**76,128 行**（156 个有效 brand-city 对 × 4 燃料 × 122 周）

或使用 LOAD DATA INFILE 直接导入 CSV（更快）：

```sql
USE nz_fuel_prices;
LOAD DATA LOCAL INFILE 'data/fuel_prices_long.csv'
INTO TABLE fuel_prices
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(price_date, region_code, fuel_code, price_nzd_per_litre, source);
```

## 数据字典

### `fuel_prices` 主表

| 字段 | 类型 | 说明 |
|---|---|---|
| `price_date` | DATE | 周一日期（MBIE 报告周） |
| `region_code` | CHAR(3) | Stats NZ 大区代码（如 AUK, WGN, CAN） |
| `fuel_code` | CHAR(3) | P91 / P95 / P98 / DSL |
| `price_nzd_per_litre` | DECIMAL(6,3) | 含税零售泵价（NZD/L） |
| `source` | VARCHAR | 数据来源标签 |

### `regions.region_code` 取值

NTL 北区 · AUK 奥克兰 · WKO 怀卡托 · BOP 普伦蒂湾 · GIS 吉斯本 ·
HKB 霍克斯湾 · TKI 塔拉纳基 · MWT 马纳瓦图-旺加努伊 · WGN 惠灵顿 ·
TAS 塔斯曼 · NSN 尼尔森 · MBH 马尔堡 · WTC 西海岸 · CAN 坎特伯雷 ·
OTA 奥塔哥 · STL 南区

## 数据质量自检

- 总行数：**7,808** = 16 区 × 4 燃料 × 122 周 ✓
- 周间隔：恒为 **7 天**（无缺失） ✓
- 全部 (date, region, fuel) 组合无重复，可作联合主键 ✓
- 价格区间合理：P91 2.42–3.60，Diesel 1.69–3.94 NZD/L
- 2024-07-01 奥克兰价格台阶下移 ≈ 11 c/L（与政策一致）

## 局限性

* MBIE 不直接发布 P98、各大区价格；本数据集的 P98 和区域分量是基于公开差价
  规则派生而来。如果下一阶段需要分站点（station-level）原始数据，可考虑
  接入 Gaspy / PriceWatch 的实时 API。
* 2025-05-07 后 MBIE 改用 Datamine 数据源（站点数 1500+），方法学微调
  已被 `price_events` 表标注。
* 周度噪声为合成值，仅用于体现站间离散度，非真实波动。
