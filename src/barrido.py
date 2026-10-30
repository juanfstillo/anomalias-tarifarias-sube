"""Barrido de sensibilidad: ¿desde qué magnitud de fraude detecta cada método?

Uso: python src/barrido.py   (≈ 40 s por combinación; guarda data/processed/barrido.parquet de a una corrida)
"""
import time

import numpy as np
import pandas as pd

from evaluacion import correr_metodos, metricas, verdad
from panel import PROCESSED
from simular import cargar_config, simular

MAGNITUDES = [0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.15, 0.20, 0.30]
SEMILLAS = [42, 43, 44]

if __name__ == "__main__":
    panel = pd.read_parquet(PROCESSED / "panel.parquet")
    lineas = pd.read_parquet(PROCESSED / "lineas.parquet")
    filas = []
    for sem in SEMILLAS:
        for mag in MAGNITUDES:
            t = time.time()
            cfg = cargar_config()
            cfg["semilla"], cfg["fraude"]["magnitud"] = sem, mag
            sim = simular(panel, lineas, cfg)
            act = sim[sim.verdad_fraude_activo]
            efecto = float(np.expm1(np.log(act.tarifa_media / act.verdad_tarifa_media_cf).mean()))
            v = verdad(sim)
            m = metricas(correr_metodos(sim, cfg), v).assign(semilla=sem, magnitud=mag, efecto_tarifa=efecto, n_expuestas_total=int(v.sum()))
            filas.append(m)
            pd.concat(filas).to_parquet(PROCESSED / "barrido.parquet")
            print(f"semilla={sem} magnitud={mag}: efecto tarifa {efecto:+.2%}, expuestas {int(v.sum())} ({time.time() - t:.0f}s)", flush=True)
