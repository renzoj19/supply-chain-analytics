# Power BI: guía del dashboard ABC-XYZ

## 1. Cargar datos
*Obtener datos > Texto/CSV* > `data/processed/abc_xyz_result.csv`.
En Power Query revisa los tipos: `cv`, `coverage_days`, montos = número decimal; `imported` = verdadero/falso.
Nombra la tabla **abc_xyz**.

## 2. Medidas DAX
Crea una tabla vacía llamada `_Medidas` (*Especificar datos* > Cargar) y agrega:

```dax
SKUs = COUNTROWS ( abc_xyz )

Valor Consumido 12M = SUM ( abc_xyz[value_12m_pen] )

% Valor Consumido =
DIVIDE ( [Valor Consumido 12M], CALCULATE ( [Valor Consumido 12M], ALL ( abc_xyz ) ) )

Valor Stock = SUM ( abc_xyz[stock_value_pen] )

Valor en Exceso = SUM ( abc_xyz[excess_value_pen] )

% Stock en Exceso = DIVIDE ( [Valor en Exceso], [Valor Stock] )

SKUs Riesgo Quiebre =
CALCULATE ( [SKUs], abc_xyz[stock_status] = "Riesgo de quiebre" )

SKUs A en Riesgo =
CALCULATE ( [SKUs], abc_xyz[stock_status] = "Riesgo de quiebre", abc_xyz[abc] = "A" )

Cobertura Promedio (días) =
-- ponderada por valor de stock: más representativa que un promedio simple
DIVIDE (
    SUMX ( FILTER ( abc_xyz, NOT ISBLANK ( abc_xyz[coverage_days] ) ),
           abc_xyz[coverage_days] * abc_xyz[stock_value_pen] ),
    CALCULATE ( [Valor Stock], NOT ISBLANK ( abc_xyz[coverage_days] ) )
)

Rotación Anual =
-- veces que rota el inventario al año (valor consumido / valor stock)
DIVIDE ( [Valor Consumido 12M], [Valor Stock] )
```

## 3. Diseño sugerido (una página)

| Zona | Visual | Campos |
|---|---|---|
| Fila superior | 5 tarjetas | Valor Stock, Valor en Exceso, % Stock en Exceso, SKUs A en Riesgo, Rotación Anual |
| Centro izquierda | **Matriz** | Filas: `abc` · Columnas: `xyz` · Valores: SKUs y % Valor Consumido. Formato condicional de fondo por % Valor |
| Centro derecha | Gráfico combinado (Pareto) | Eje: `sku` ordenado por valor · Columnas: Valor Consumido 12M · Línea: `cum_share` |
| Inferior izquierda | Barras apiladas | Eje: `family` · Valor: Valor Stock · Leyenda: `stock_status` |
| Inferior derecha | Tabla | sku, description, abc_xyz, coverage_days, stock_status, excess_value_pen, suggested_policy |
| Segmentadores | — | business_line, supplier, imported |

Colores para `stock_status`: Riesgo de quiebre = rojo, Sobrestock = ámbar, Sin movimiento = gris, OK = verde.

## 4. Captura para el README
Cuando termines, exporta una captura del dashboard como `docs/dashboard.png` y súbela al repo:
es lo que verá un reclutador, ya que GitHub no abre archivos `.pbix`.
