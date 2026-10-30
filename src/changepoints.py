"""Método 01: quiebres estructurales en la tarifa media relativa de cada línea (ruptures/PELT)."""
import numpy as np
import pandas as pd
import ruptures as rpt


def serie_relativa(sim: pd.DataFrame) -> pd.DataFrame:
    """Tarifa media de cada línea relativa a la mediana de su grupo comparable, en logs.

    Restar la mediana del grupo saca los movimientos que afectan a todas por igual (estación, tarifas, etc.)
    y deja lo propio de cada línea. Devuelve una tabla ancha: filas = meses, columnas = línea.
    """
    d = sim.assign(log_tm=np.log(sim.tarifa_media))
    d["rel"] = d.log_tm - d.groupby(["grupo", "mes"]).log_tm.transform("median")
    return d.pivot(index="mes", columns="linea_id", values="rel")


def sigma_robusto(y: np.ndarray) -> float:
    """Desvío del ruido a partir de diferencias sucesivas (MAD): casi no se contamina por un quiebre."""
    return 1.4826 * np.median(np.abs(np.diff(y) - np.median(np.diff(y)))) / np.sqrt(2)


def detectar_linea(y: np.ndarray, beta: float = 3.0, min_size: int = 3) -> list[dict]:
    """Quiebres de PELT con costo l2. Penalización = beta · σ² · log(n) (tipo BIC).

    Devuelve cada quiebre con su salto (media del tramo siguiente − media del tramo anterior) en unidades de σ.
    """
    n = len(y)
    if n < 4 * min_size:  # series demasiado cortas para hablar de "antes" y "después"
        return []
    s = sigma_robusto(y)
    if s == 0:
        return []
    bk = rpt.Pelt(model="l2", min_size=min_size, jump=1).fit(y).predict(pen=beta * s**2 * np.log(n))[:-1]
    cortes = [0, *bk, n]
    out = []
    for i, b in enumerate(bk):
        antes, despues = y[cortes[i]:b], y[b:cortes[i + 2]]
        out.append({"idx": b, "salto": despues.mean() - antes.mean(), "salto_sigma": (despues.mean() - antes.mean()) / s})
    return out


def detectar(wide: pd.DataFrame, beta: float = 3.0, min_salto: float = 0.0) -> pd.DataFrame:
    """Para cada línea, el mayor quiebre ASCENDENTE (la tarifa sube, que es lo que beneficiaría a la empresa)."""
    filas = []
    for lid in wide.columns:
        y = wide[lid].dropna()
        meses = y.index
        ups = [q for q in detectar_linea(y.to_numpy(), beta) if q["salto"] > min_salto]
        if ups:
            q = max(ups, key=lambda q: q["salto_sigma"])
            filas.append({"linea_id": lid, "n_meses": len(y), "mes_quiebre": meses[q["idx"]],
                          "salto": q["salto"], "salto_sigma": q["salto_sigma"]})
        else:
            filas.append({"linea_id": lid, "n_meses": len(y), "mes_quiebre": pd.NaT, "salto": 0.0, "salto_sigma": 0.0})
    return pd.DataFrame(filas)


def calibrar_beta(wide: pd.DataFrame, hasta: str, tasa_objetivo: float = 0.05, grilla=(1, 1.5, 2, 3, 4, 5, 6, 8, 10)) -> tuple[float, pd.DataFrame]:
    """Elige la penalización sin mirar el fraude: placebo sobre el período previo.

    Corre el detector solo hasta `hasta` (cuando no hay nada que detectar) y devuelve el beta MÁS SENSIBLE
    (más chico) cuya tasa de falsas alarmas no supera `tasa_objetivo`. Supuesto: el pasado es "limpio".
    """
    pre = wide[wide.index < hasta]
    elegibles = pre.columns[pre.notna().sum() >= 12]
    filas = []
    for b in grilla:
        r = detectar(pre[elegibles], beta=b)
        filas.append({"beta": b, "tasa_falsas_alarmas": r.mes_quiebre.notna().mean()})
    tabla = pd.DataFrame(filas)
    ok = tabla[tabla.tasa_falsas_alarmas <= tasa_objetivo]
    return float(ok.beta.min() if len(ok) else tabla.beta.max()), tabla


def evaluar(res: pd.DataFrame, verdad: pd.Series, inicio_fraude: str) -> dict:
    """Matriz de confusión a nivel línea y demora de detección (meses de diferencia con el inicio real)."""
    r = res.set_index("linea_id").join(verdad.rename("fraude"))
    r = r[r.n_meses >= 12]  # solo líneas evaluables
    marca = r.mes_quiebre.notna()
    tp, fp = int((marca & r.fraude).sum()), int((marca & ~r.fraude).sum())
    fn, tn = int((~marca & r.fraude).sum()), int((~marca & ~r.fraude).sum())
    det = r[marca & r.fraude].mes_quiebre
    demora = (det.dt.year - pd.Timestamp(inicio_fraude).year) * 12 + det.dt.month - pd.Timestamp(inicio_fraude).month
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": tp / max(tp + fp, 1), "recall": tp / max(tp + fn, 1),
            "demora_mediana_meses": float(demora.median()) if len(demora) else np.nan, "n_evaluadas": len(r)}
