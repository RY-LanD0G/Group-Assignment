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
