-- =============================================================
-- Caso 01 - ABC-XYZ | Clasificación hecha 100 % en SQL
-- Motor: SQL Server. Compara el resultado con python/01_abc_xyz.py
-- Conceptos que practicas: CTE, GROUP BY, JOIN, funciones de ventana
-- (SUM OVER, ORDER BY dentro de OVER), CASE.
-- =============================================================
USE supply_analytics;
GO

WITH
-- 1. Últimos 12 meses de consumo
ultimos_12m AS (
    SELECT sku, month, qty_consumed
    FROM monthly_consumption
    WHERE month > DATEADD(MONTH, -12, (SELECT MAX(month) FROM monthly_consumption))
),

-- 2. Métricas por SKU: total, promedio y desviación estándar mensual
metricas AS (
    SELECT
        sku,
        SUM(qty_consumed)                 AS qty_12m,
        AVG(CAST(qty_consumed AS FLOAT))  AS avg_month,
        STDEV(qty_consumed)               AS std_month   -- MySQL: STDDEV_SAMP
    FROM ultimos_12m
    GROUP BY sku
),

-- 3. Valor consumido y coeficiente de variación
base AS (
    SELECT
        p.sku, p.description, p.family, p.supplier, p.unit_cost_pen,
        m.qty_12m, m.avg_month,
        m.qty_12m * p.unit_cost_pen AS value_12m_pen,
        CASE WHEN m.avg_month = 0 THEN 99
             ELSE m.std_month / m.avg_month END AS cv,
        s.qty_on_hand
    FROM products p
    JOIN metricas      m ON m.sku = p.sku
    JOIN current_stock s ON s.sku = p.sku
),

-- 4. Participación acumulada (curva de Pareto)
pareto AS (
    SELECT *,
        SUM(value_12m_pen) OVER (ORDER BY value_12m_pen DESC
                                 ROWS UNBOUNDED PRECEDING)
        / SUM(value_12m_pen) OVER ()            AS cum_share,
        -- participación acumulada SIN contar el SKU actual
        (SUM(value_12m_pen) OVER (ORDER BY value_12m_pen DESC
                                  ROWS UNBOUNDED PRECEDING) - value_12m_pen)
        / SUM(value_12m_pen) OVER ()            AS prev_share
    FROM base
)

-- 5. Clasificación final
SELECT
    sku, description, family, supplier,
    ROUND(value_12m_pen, 2) AS value_12m_pen,
    ROUND(cum_share, 4)     AS cum_share,
    CASE WHEN prev_share < 0.80 THEN 'A'      -- el SKU que cruza el 80 % sigue siendo A
         WHEN cum_share  <= 0.95 THEN 'B'
         ELSE 'C' END                          AS abc,
    ROUND(cv, 3)                               AS cv,
    CASE WHEN cv <= 0.5 THEN 'X'
         WHEN cv <= 1.0 THEN 'Y'
         ELSE 'Z' END                          AS xyz,
    qty_on_hand,
    CASE WHEN avg_month = 0 THEN NULL
         ELSE ROUND(qty_on_hand / (avg_month / 30.0), 1) END AS coverage_days
FROM pareto
ORDER BY value_12m_pen DESC;
