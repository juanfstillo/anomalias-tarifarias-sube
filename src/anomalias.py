"""Método 04: detección genérica de anomalías (Isolation Forest, LOF) sobre rasgos línea-mes.

No incorpora ninguna idea sobre el fraude: solo marca lo "raro" respecto de lo que el modelo vio en el pasado.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

SEMILLA = 42
SHARES = ["s1", "s2", "s3", "s4", "s5"]
NIVELES = ["log_tm_rel", "altas", "pct_sec_max", "log_largo", "log_viajes", "log_dist_centro", *SHARES]
CAMBIOS = ["d_log_tm_rel", "d_altas"]


def rasgos(sim: pd.DataFrame, rezago: int = 10, ventana: int = 12) -> pd.DataFrame:
    """Rasgos observables por línea-mes (nada de las columnas `verdad_*`).

    - Niveles: tarifa media relativa a su grupo (log), reparto por secciones, proporción en secciones altas, tamaño y geografía.
    - Cambios: desvío del mes respecto del promedio de la propia línea en una ventana de `ventana` meses que termina `rezago`
      meses antes. El rezago evita que los meses recientes contaminen la referencia.
    """
    d = sim.sort_values(["linea_id", "mes"]).copy()
    for k in range(1, 6):
        d[f"s{k}"] = d[f"v{k}"] / d.viajes
    d["altas"] = d[["s3", "s4", "s5"]].sum(axis=1)
    d["log_tm"] = np.log(d.tarifa_media)
    d["log_tm_rel"] = d.log_tm - d.groupby(["grupo", "mes"]).log_tm.transform("median")
    d["log_largo"], d["log_viajes"] = np.log(d.largo_km), np.log(d.viajes)
    d["log_dist_centro"] = np.log1p(d.dist_centro_km)
    for col, nuevo in [("log_tm_rel", "d_log_tm_rel"), ("altas", "d_altas")]:
        # panel con meses faltantes: se reindexa a calendario completo para que el rezago sea en meses y no en filas
        w = d.pivot(index="mes", columns="linea_id", values=col)
        ref = w.shift(rezago).rolling(ventana, min_periods=ventana // 2).mean()
        d[nuevo] = (w - ref).stack().rename(nuevo).reindex(pd.MultiIndex.from_frame(d[["mes", "linea_id"]])).to_numpy()
    return d


class Detector:
    """Entrena con filas hasta `entrena_hasta` y puntúa cualquier fila (más alto = más anómalo)."""

    def __init__(self, modelo: str, cols: list, entrena_hasta: str):
        self.modelo, self.cols, self.hasta = modelo, cols, pd.Timestamp(entrena_hasta)

    def fit(self, d: pd.DataFrame) -> "Detector":
        X = d[d.mes <= self.hasta].dropna(subset=self.cols)[self.cols]
        self.esc = StandardScaler().fit(X)
        Z = self.esc.transform(X)
        if self.modelo == "iforest":
            self.m = IsolationForest(n_estimators=300, random_state=SEMILLA, n_jobs=-1).fit(Z)
        else:
            self.m = LocalOutlierFactor(n_neighbors=35, novelty=True, n_jobs=-1).fit(Z)
        return self

    def puntuar(self, d: pd.DataFrame) -> pd.Series:
        X = d.dropna(subset=self.cols)
        return pd.Series(-self.m.score_samples(self.esc.transform(X[self.cols])), index=X.index)


def puntaje_linea(d: pd.DataFrame, s: pd.Series, hasta: str, ventana: int = 6) -> pd.Series:
    """Promedio del puntaje de anomalía de los últimos `ventana` meses hasta `hasta`; exige la mitad de los meses."""
    h = pd.Timestamp(hasta)
    x = d.loc[s.index].assign(s=s)
    x = x[(x.mes <= h) & (x.mes > h - pd.DateOffset(months=ventana))]
    g = x.groupby("linea_id").s
    return g.mean()[g.count() >= ventana // 2]
