-- =============================================================
-- Caso 01 - ABC-XYZ | Preguntas de negocio
-- Requisito: guarda el resultado de 02_abc_xyz.sql en una tabla
-- abc_xyz_result, o importa data/processed/abc_xyz_result.csv
-- (Import Flat File) con ese nombre.
-- =============================================================
USE supply_analytics;
GO

-- P1. ¿Cuántos SKUs y qué % del valor hay en cada celda de la matriz?
SELECT
    abc_xyz,
    COUNT(*)                                                   AS skus,
    ROUND(SUM(value_12m_pen), 0)                               AS valor_12m,
    ROUND(100.0 * SUM(value_12m_pen) / SUM(SUM(value_12m_pen)) OVER (), 1) AS pct_valor
FROM abc_xyz_result
GROUP BY abc_xyz
ORDER BY abc_xyz;

-- P2. ¿Cuánto capital está inmovilizado en sobrestock o sin movimiento?
SELECT
    stock_status,
    COUNT(*)                         AS skus,
    ROUND(SUM(stock_value_pen), 0)   AS valor_stock,
    ROUND(SUM(excess_value_pen), 0)  AS valor_en_exceso
FROM abc_xyz_result
GROUP BY stock_status
ORDER BY valor_en_exceso DESC;

-- P3. SKUs clase A en riesgo de quiebre (prioridad de compra)
SELECT sku, description, supplier, lead_time_days,
       ROUND(coverage_days, 1) AS cobertura_dias
FROM abc_xyz_result
WHERE abc = 'A' AND stock_status = 'Riesgo de quiebre'
ORDER BY coverage_days;

-- P4. Top 10 SKUs con mayor valor en exceso (candidatos a liquidar o redistribuir)
SELECT TOP 10                 -- MySQL: quita TOP 10 y agrega LIMIT 10 al final
    sku, description, abc_xyz, stock_status,
    ROUND(coverage_days, 0)   AS cobertura_dias,
    ROUND(excess_value_pen, 0) AS valor_exceso
FROM abc_xyz_result
ORDER BY excess_value_pen DESC;

-- P5. Concentración por proveedor en clase A
SELECT supplier,
       COUNT(*)                     AS skus_a,
       ROUND(SUM(value_12m_pen), 0) AS valor_12m
FROM abc_xyz_result
WHERE abc = 'A'
GROUP BY supplier
ORDER BY valor_12m DESC;
