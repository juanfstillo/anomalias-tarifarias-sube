"""Fase 1: grupos de líneas comparables (clustering sobre rasgos estructurales)."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

SEMILLA = 42


def asignar_grupos(lineas: pd.DataFrame) -> pd.DataFrame:
    """KMeans sobre largo, distancia al centro y escala de demanda (todo en log).

    Se agrupa DENTRO de cada jurisdicción (`jur_geo`): solo se comparan líneas con el mismo
    régimen tarifario. k crece con la cantidad de líneas (≈15 por grupo, entre 2 y 5).
    """
    partes = []
    for jur, d in lineas.groupby("jur_geo"):
        X = np.column_stack([
            np.log(d.largo_km.clip(lower=1)),
            np.log1p(d.dist_centro_km),
            np.log(d.viajes_dia_med.clip(lower=1)),
        ])
        k = int(np.clip(len(d) // 15, 2, 5))
        d = d.copy()
        d["cluster"] = KMeans(k, n_init=10, random_state=SEMILLA).fit_predict(StandardScaler().fit_transform(X))
        d["grupo"] = jur[:3] + "-" + d.cluster.astype(str)
        partes.append(d.drop(columns="cluster"))
    return pd.concat(partes)
