"""
Clasificación ABC-XYZ de inventarios.

ABC (por valor consumido en los últimos 12 meses):
  A = SKUs que acumulan el 80 % del valor
  B = siguiente 15 %  (hasta 95 %)
  C = último 5 %

XYZ (por variabilidad de la demanda mensual, coeficiente de variación CV):
  X = CV <= 0.5   demanda estable, fácil de pronosticar
  Y = 0.5 < CV <= 1.0   variable / estacional
  Z = CV > 1.0    errática

Además calcula cobertura (días de inventario) y marca sobrestock / riesgo de quiebre.

Entrada:  data/raw/*.csv
Salida:   data/processed/abc_xyz_result.csv  (lo lee Power BI)
          docs/matriz_abc_xyz.png

Uso: python python/01_abc_xyz.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "data" / "raw"
OUT = RAIZ / "data" / "processed"
DOCS = RAIZ / "docs"
OUT.mkdir(parents=True, exist_ok=True)

# Parámetros de negocio (ajústalos según la política de la empresa)
CORTE_A, CORTE_B = 0.80, 0.95
CORTE_X, CORTE_Y = 0.5, 1.0
COBERTURA_MIN_DIAS = 15     # debajo: riesgo de quiebre
COBERTURA_MAX_DIAS = 120    # encima: sobrestock

# --- 1. Cargar datos ------------------------------------------------------
products = pd.read_csv(RAW / "products.csv")
monthly = pd.read_csv(RAW / "monthly_consumption.csv", parse_dates=["month"])
stock = pd.read_csv(RAW / "current_stock.csv")

# Últimos 12 meses
ultimo_mes = monthly["month"].max()
m12 = monthly[monthly["month"] > ultimo_mes - pd.DateOffset(months=12)]

# --- 2. Métricas por SKU -----------------------------------------------------
stats = (m12.groupby("sku")["qty_consumed"]
            .agg(qty_12m="sum", avg_month="mean", std_month="std")
            .reset_index())
stats["cv"] = (stats["std_month"] / stats["avg_month"]).fillna(99)  # sin consumo = Z

df = (products.merge(stats, on="sku", how="left")
              .merge(stock[["sku", "qty_on_hand"]], on="sku", how="left"))
df["value_12m_pen"] = df["qty_12m"] * df["unit_cost_pen"]
df["stock_value_pen"] = df["qty_on_hand"] * df["unit_cost_pen"]

# --- 3. Clasificación ABC ---------------------------------------------------
df = df.sort_values("value_12m_pen", ascending=False).reset_index(drop=True)
df["cum_share"] = df["value_12m_pen"].cumsum() / df["value_12m_pen"].sum()
df["abc"] = pd.cut(df["cum_share"], bins=[-1, CORTE_A, CORTE_B, 2],
                   labels=["A", "B", "C"]).astype(str)
# El primer SKU que cruza el 80 % también es A
df.loc[df["cum_share"].shift(fill_value=0) < CORTE_A, "abc"] = "A"

# --- 4. Clasificación XYZ ---------------------------------------------------
df["xyz"] = pd.cut(df["cv"], bins=[-1, CORTE_X, CORTE_Y, float("inf")],
                   labels=["X", "Y", "Z"]).astype(str)
df["abc_xyz"] = df["abc"] + df["xyz"]

# --- 5. Cobertura y alertas -------------------------------------------------
consumo_diario = df["avg_month"] / 30
df["coverage_days"] = (df["qty_on_hand"] / consumo_diario).where(consumo_diario > 0)
df["stock_status"] = "OK"
df.loc[df["coverage_days"] < COBERTURA_MIN_DIAS, "stock_status"] = "Riesgo de quiebre"
df.loc[df["coverage_days"] > COBERTURA_MAX_DIAS, "stock_status"] = "Sobrestock"
df.loc[df["coverage_days"].isna() & (df["qty_on_hand"] > 0), "stock_status"] = "Sin movimiento"

# Valor en exceso: lo que sobra por encima del máximo de cobertura
max_qty = consumo_diario * COBERTURA_MAX_DIAS
df["excess_value_pen"] = ((df["qty_on_hand"] - max_qty).clip(lower=0)
                          * df["unit_cost_pen"]).round(2)
df.loc[df["stock_status"] == "Sin movimiento", "excess_value_pen"] = df["stock_value_pen"]

# Política sugerida según la celda de la matriz
politica = {
    "AX": "Reposición automática, stock de seguridad bajo, revisión semanal",
    "AY": "Forecast con estacionalidad, revisión semanal",
    "AZ": "Compra contra pedido / acuerdo con proveedor, seguimiento diario",
    "BX": "Reposición automática, revisión quincenal",
    "BY": "Forecast estacional, revisión quincenal",
    "BZ": "Stock de seguridad alto o compra bajo pedido",
    "CX": "Lotes grandes, revisión mensual",
    "CY": "Revisión mensual",
    "CZ": "Evaluar descontinuar o comprar solo bajo pedido",
}
df["suggested_policy"] = df["abc_xyz"].map(politica)

# --- 6. Guardar resultado ---------------------------------------------------
cols = ["sku", "description", "family", "business_line", "supplier", "imported",
        "lead_time_days", "unit_cost_pen", "qty_12m", "avg_month", "std_month",
        "cv", "value_12m_pen", "cum_share", "abc", "xyz", "abc_xyz",
        "qty_on_hand", "stock_value_pen", "coverage_days", "stock_status",
        "excess_value_pen", "suggested_policy"]
df[cols].round(4).to_csv(OUT / "abc_xyz_result.csv", index=False, encoding="utf-8")

# --- 7. Resumen en consola ----------------------------------------------------
print("\n=== SKUs por celda ABC-XYZ ===")
print(pd.crosstab(df["abc"], df["xyz"], margins=True, margins_name="Total"))

print("\n=== % del valor consumido por clase ABC ===")
print((df.groupby("abc")["value_12m_pen"].sum() / df["value_12m_pen"].sum() * 100).round(1))

print("\n=== Estado del stock ===")
print(df.groupby("stock_status").agg(skus=("sku", "count"),
                                     valor_stock=("stock_value_pen", "sum"),
                                     valor_exceso=("excess_value_pen", "sum")).round(0))

# --- 8. Gráfico: matriz ABC-XYZ (para el README) ------------------------------
matriz_n = pd.crosstab(df["abc"], df["xyz"]).reindex(index=list("ABC"), columns=list("XYZ"), fill_value=0)
matriz_v = (df.pivot_table(index="abc", columns="xyz", values="value_12m_pen", aggfunc="sum")
              .reindex(index=list("ABC"), columns=list("XYZ")).fillna(0))
share_v = matriz_v / matriz_v.values.sum() * 100

fig, ax = plt.subplots(figsize=(6.5, 5))
ax.imshow(share_v.values, cmap="Blues")
for i, a in enumerate("ABC"):
    for j, x in enumerate("XYZ"):
        color = "white" if share_v.iloc[i, j] > 25 else "#1a1a1a"
        ax.text(j, i, f"{a}{x}\n{matriz_n.iloc[i, j]} SKUs\n{share_v.iloc[i, j]:.1f}% valor",
                ha="center", va="center", fontsize=10, color=color)
ax.set_xticks(range(3), ["X (estable)", "Y (variable)", "Z (errática)"])
ax.set_yticks(range(3), ["A", "B", "C"])
ax.set_title("Matriz ABC-XYZ: SKUs y % del valor consumido (12 meses)")
plt.tight_layout()
plt.savefig(DOCS / "matriz_abc_xyz.png", dpi=150)
print(f"\nResultado: {OUT / 'abc_xyz_result.csv'}")
