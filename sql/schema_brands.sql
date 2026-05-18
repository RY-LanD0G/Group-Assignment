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
