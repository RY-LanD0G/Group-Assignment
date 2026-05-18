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
