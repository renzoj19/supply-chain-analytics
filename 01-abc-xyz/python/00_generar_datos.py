"""
Genera datos sintéticos para el caso ABC-XYZ.
Empresa ficticia: distribuidora farmacéutica y de consumo en Lima.

Salidas (data/raw/):
  - products.csv          maestro de materiales (SKU)
  - monthly_consumption.csv  consumo mensual por SKU (24 meses)
  - current_stock.csv     stock a la fecha de corte

Uso: python python/00_generar_datos.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEMILLA = 42                     # misma semilla = mismos datos cada vez
N_SKUS = 300
MESES = pd.date_range("2024-11-01", "2026-10-01", freq="MS")   # 24 meses
FECHA_CORTE = "2026-10-31"

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "data" / "raw"
SALIDA.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(SEMILLA)

# --- 1. Maestro de materiales -------------------------------------------
familias = {
    "Analgésicos":      ("Farma",   "UND", (2, 15)),
    "Antibióticos":     ("Farma",   "UND", (5, 40)),
    "Vitaminas":        ("Farma",   "UND", (8, 60)),
    "Dermocosmética":   ("Consumo", "UND", (12, 90)),
    "Higiene personal": ("Consumo", "UND", (3, 25)),
    "Material médico":  ("Insumos", "UND", (1, 30)),
    "Envases":          ("Insumos", "MIL", (20, 150)),
}
nombres_fam = list(familias)
proveedores = [f"PROV-{i:03d}" for i in range(1, 26)]

filas = []
for i in range(1, N_SKUS + 1):
    fam = rng.choice(nombres_fam, p=[.18, .14, .14, .14, .16, .14, .10])
    linea, um, (cmin, cmax) = familias[fam]
    filas.append({
        "sku": f"MAT-{100000 + i}",
        "description": f"{fam} producto {i:03d}",
        "family": fam,
        "business_line": linea,
        "uom": um,
        "unit_cost_pen": round(float(rng.uniform(cmin, cmax)), 2),
        "supplier": rng.choice(proveedores),
        "lead_time_days": int(rng.choice([7, 15, 30, 45, 60, 90],
                                         p=[.15, .25, .2, .15, .15, .1])),
        "imported": None,
    })
products = pd.DataFrame(filas)
products["imported"] = products["lead_time_days"] >= 45

# --- 2. Consumo mensual --------------------------------------------------
# Demanda base con distribución de cola larga (pocos SKUs mueven mucho)
base = rng.lognormal(mean=5.5, sigma=1.3, size=N_SKUS)

# Cada SKU recibe un "perfil" de variabilidad
perfil = rng.choice(["estable", "estacional", "erratico", "sin_mov"], size=N_SKUS,
                    p=[.42, .30, .23, .05])

consumos = []
for idx, row in products.iterrows():
    for m in MESES:
        b = base[idx]
        if perfil[idx] == "estable":
            q = rng.normal(b, b * 0.12)
        elif perfil[idx] == "estacional":
            # pico en invierno peruano (may-ago) para analgésicos, vitaminas, etc.
            factor = 1 + 0.9 * np.sin((m.month - 3) / 12 * 2 * np.pi)
            q = rng.normal(b * factor, b * 0.3)
        elif perfil[idx] == "sin_mov":
            # se dejó de vender hace 14 meses, pero queda stock en almacén
            q = rng.normal(b, b * 0.2) if m < MESES[10] else 0
        else:
            # errático: muchos meses en cero y picos ocasionales
            q = rng.choice([0, b * rng.uniform(1.5, 4)], p=[.55, .45])
        consumos.append({
            "sku": row["sku"],
            "month": m.date().isoformat(),
            "qty_consumed": max(0, int(round(q))),
        })
monthly = pd.DataFrame(consumos)

# --- 3. Stock actual -----------------------------------------------------
consumo_prom = monthly.groupby("sku")["qty_consumed"].mean()
# Stock = entre 0.3 y 6 meses de consumo (para que haya quiebres y excesos)
meses_stock = rng.choice([0.3, 1, 2, 3, 6], size=N_SKUS, p=[.1, .3, .3, .2, .1])
stock = pd.DataFrame({
    "sku": products["sku"],
    "stock_date": FECHA_CORTE,
    "warehouse": rng.choice(["ALM-LIMA", "ALM-CALLAO"], size=N_SKUS, p=[.7, .3]),
    "qty_on_hand": (consumo_prom.reindex(products["sku"]).values * meses_stock)
                   .round().astype(int),
})
# Los SKUs sin movimiento conservan stock "olvidado"
stock.loc[perfil == "sin_mov", "qty_on_hand"] = (
    base[perfil == "sin_mov"] * rng.uniform(1, 3, (perfil == "sin_mov").sum())).round().astype(int)

# --- Guardar ---------------------------------------------------------------
products.to_csv(SALIDA / "products.csv", index=False, encoding="utf-8")
monthly.to_csv(SALIDA / "monthly_consumption.csv", index=False, encoding="utf-8")
stock.to_csv(SALIDA / "current_stock.csv", index=False, encoding="utf-8")

print(f"products.csv: {len(products)} filas")
print(f"monthly_consumption.csv: {len(monthly)} filas")
print(f"current_stock.csv: {len(stock)} filas")
