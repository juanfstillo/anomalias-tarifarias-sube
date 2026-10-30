"""Método 03: coherencia geográfica. ¿Lo cobrado es posible/plausible dado el largo del recorrido?

No mira la historia de cada línea: compara cada línea con lo esperable para su largo en el MISMO mes (corte transversal).
"""
import numpy as np
import pandas as pd
from statsmodels.nonparametric.smoothers_lowess import lowess

SECC = ["v1", "v2", "v3", "v4", "v5"]


def viajes_imposibles(sim: pd.DataFrame, limites_km: list, tol: float = 0.10) -> pd.Series:
    """Proporción de viajes en secciones cuyo límite inferior supera el largo del recorrido (más un margen `tol`).

    Una sección que empieza a 12 km no puede usarse en una línea de 8 km. El margen cubre errores de medición del recorrido
    (el shapefile promedia ramales; un ramal puede ser más largo que el promedio).
    """
    lim = np.asarray(limites_km, float)
    imposible = lim[None, :] >= (sim.largo_km.to_numpy() * (1 + tol))[:, None]
    return pd.Series((sim[SECC].to_numpy() * imposible).sum(axis=1) / sim.viajes.to_numpy(), index=sim.index)


def exceso_altas(sim: pd.DataFrame, desde_seccion: int = 3, frac: float = 0.5) -> pd.Series:
    """Exceso de viajes en secciones altas (≥ `desde_seccion`) respecto de lo esperable para el largo, en desvíos robustos.

    Cada mes: se estima con LOWESS robusto cómo varía la proporción de viajes altos con el log del largo entre TODAS las líneas
    (la mediana local no se deja arrastrar por el 10 % de líneas atípicas), se calcula el residuo de cada línea y se lo
    expresa en MAD (desvío absoluto mediano) de los residuos de ese mes.
    """
    altas = sim[SECC[desde_seccion - 1:]].sum(axis=1) / sim.viajes
    out = pd.Series(np.nan, index=sim.index)
    for mes, idx in sim.groupby("mes").groups.items():
        x, y = np.log(sim.loc[idx, "largo_km"].to_numpy()), altas.loc[idx].to_numpy()
        if len(idx) < 30:
            continue
        ajuste = lowess(y, x, frac=frac, it=3, return_sorted=False)
        res = y - ajuste
        mad = 1.4826 * np.median(np.abs(res - np.median(res)))
        out.loc[idx] = (res - np.median(res)) / max(mad, 1e-6)
    return out


def puntaje_linea(sim: pd.DataFrame, col: str, hasta: str, ventana: int = 6) -> pd.Series:
    """Promedio de `col` en los últimos `ventana` meses hasta `hasta` (inclusive). Exige al menos la mitad de los meses."""
    h = pd.Timestamp(hasta)
    d = sim[(sim.mes <= h) & (sim.mes > h - pd.DateOffset(months=ventana))]
    g = d.groupby("linea_id")[col]
    return g.mean()[g.count() >= ventana // 2]
