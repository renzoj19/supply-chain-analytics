-- =============================================================
-- Caso 01 - ABC-XYZ | Creación de tablas
-- Motor: SQL Server (T-SQL). Notas para MySQL al final.
-- =============================================================

CREATE DATABASE supply_analytics;
GO
USE supply_analytics;
GO

-- Maestro de materiales
CREATE TABLE products (
    sku             VARCHAR(20)   PRIMARY KEY,
    description     VARCHAR(100)  NOT NULL,
    family          VARCHAR(50)   NOT NULL,
    business_line   VARCHAR(20)   NOT NULL,
    uom             VARCHAR(5)    NOT NULL,
    unit_cost_pen   DECIMAL(12,2) NOT NULL,
    supplier        VARCHAR(20)   NOT NULL,
    lead_time_days  INT           NOT NULL,
    imported        BIT           NOT NULL      -- 1 = importado
);

-- Consumo mensual (salidas de almacén por SKU y mes)
CREATE TABLE monthly_consumption (
    sku           VARCHAR(20) NOT NULL REFERENCES products(sku),
    month         DATE        NOT NULL,         -- primer día del mes
    qty_consumed  INT         NOT NULL,
    PRIMARY KEY (sku, month)
);

-- Stock a la fecha de corte
CREATE TABLE current_stock (
    sku          VARCHAR(20) NOT NULL REFERENCES products(sku),
    stock_date   DATE        NOT NULL,
    warehouse    VARCHAR(20) NOT NULL,
    qty_on_hand  INT         NOT NULL,
    PRIMARY KEY (sku, stock_date)
);

-- -------------------------------------------------------------
-- Carga de los CSV (ajusta la ruta a tu carpeta)
-- Alternativa sin código: clic derecho en la base > Tasks > Import Flat File
-- -------------------------------------------------------------
BULK INSERT products
FROM 'C:\ruta\supply-chain-analytics\01-abc-xyz\data\raw\products.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, CODEPAGE = '65001');

BULK INSERT monthly_consumption
FROM 'C:\ruta\supply-chain-analytics\01-abc-xyz\data\raw\monthly_consumption.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, CODEPAGE = '65001');

BULK INSERT current_stock
FROM 'C:\ruta\supply-chain-analytics\01-abc-xyz\data\raw\current_stock.csv'
WITH (FORMAT = 'CSV', FIRSTROW = 2, CODEPAGE = '65001');

-- Nota: products.csv trae imported como True/False. Si BULK INSERT
-- lo rechaza, cárgalo con Import Flat File o cambia el tipo a VARCHAR(5).

-- -------------------------------------------------------------
-- MySQL: quita los GO, usa BOOLEAN en vez de BIT y carga con:
--   LOAD DATA LOCAL INFILE 'ruta/products.csv' INTO TABLE products
--   FIELDS TERMINATED BY ',' ENCLOSED BY '"' IGNORE 1 LINES;
-- -------------------------------------------------------------
