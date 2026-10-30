"""Método 02: diferencias en diferencias (event study) y control sintético sobre la tarifa media."""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.optimize import minimize


# ---------------------------------------------------------------- DiD / event study
def event_study(sim: pd.DataFrame, tratadas: set, inicio: str, desde: str = "2024-01-01", rezago_ref: int = -1):
    """TWFE con efectos fijos de línea y de mes. Coeficientes por mes relativo al inicio (referencia: mes -1).

    Variable: log de la tarifa media. Errores agrupados por empresa (el fraude se decide a nivel empresa).
    Devuelve (tabla de coeficientes del event study, ATT = efecto promedio post, error estándar del ATT).
    """
    ini = pd.Timestamp(inicio)
    d = sim[sim.mes >= desde].copy()
    d["y"] = np.log(d.tarifa_media)
    d["trat"] = d.linea_id.isin(tratadas).astype(int)
    d["t"] = (d.mes.dt.year - ini.year) * 12 + d.mes.dt.month - ini.month
    d["post"] = (d.t >= 0).astype(int)
    d["tp"] = d.trat * d.post
    att = smf.ols("y ~ tp + C(linea_id) + C(mes)", data=d).fit(cov_type="cluster", cov_kwds={"groups": d.empresa_id.astype("category").cat.codes})
    ts = sorted(d.t.unique())
    for k in ts:
        if k != rezago_ref:
            d[f"e{k}".replace("-", "m")] = ((d.t == k) & (d.trat == 1)).astype(int)
    cols = [f"e{k}".replace("-", "m") for k in ts if k != rezago_ref]
    es = smf.ols("y ~ " + " + ".join(cols) + " + C(linea_id) + C(mes)", data=d).fit(
        cov_type="cluster", cov_kwds={"groups": d.empresa_id.astype("category").cat.codes})
    tabla = pd.DataFrame({"t": [k for k in ts if k != rezago_ref],
                          "coef": [es.params[c] for c in cols], "se": [es.bse[c] for c in cols]})
    tabla = pd.concat([tabla, pd.DataFrame({"t": [rezago_ref], "coef": [0.0], "se": [0.0]})]).sort_values("t")
    return tabla, float(att.params["tp"]), float(att.bse["tp"])


# ---------------------------------------------------------------- control sintético
def pesos_sinteticos(y: np.ndarray, D: np.ndarray) -> np.ndarray:
    """Pesos w ≥ 0, suma 1, que minimizan ||y − D w||² (y: pre-período de la línea; D: pre-período de los donantes)."""
    k = D.shape[1]
    w0 = np.full(k, 1 / k)
    r = minimize(lambda w: np.sum((y - D @ w) ** 2), w0, jac=lambda w: -2 * D.T @ (y - D @ w),
                 bounds=[(0, 1)] * k, constraints={"type": "eq", "fun": lambda w: w.sum() - 1, "jac": lambda w: np.ones(k)},
                 method="SLSQP", options={"maxiter": 200, "ftol": 1e-12})
    return r.x


def control_sintetico(wide: pd.DataFrame, grupo: pd.Series, inicio: str, fin: str | None = None, ventana: int = 36,
                      excluir_donantes: set = frozenset(), min_donantes: int = 5, eps: float = 1e-4) -> pd.DataFrame:
    """Para cada línea: contrafactual = combinación de líneas de su mismo grupo que mejor replica su pre-período.

    - Ajuste: `ventana` meses previos a `inicio`. Se exige serie completa en esa ventana y al menos un mes posterior.
    - Donantes: mismo grupo (si hay menos de `min_donantes`, todo el régimen jurisdiccional), con datos completos en ajuste y
      post, y fuera de `excluir_donantes` (líneas ya sospechosas, para no contaminar el contrafactual).
    - Puntaje = brecha media post / RMSPE pre (cuántos "errores típicos de ajuste" se despega).
    """
    ini = pd.Timestamp(inicio)
    pre = wide[(wide.index < ini)].tail(ventana)
    post = wide[(wide.index >= ini) & ((wide.index <= pd.Timestamp(fin)) if fin else True)]
    ok_pre = pre.notna().all()
    filas, brechas = [], {}
    for lid in wide.columns:
        if not ok_pre[lid] or post[lid].notna().sum() == 0:
            continue
        g = grupo[lid]
        pool = [c for c in wide.columns if c != lid and ok_pre[c] and c not in excluir_donantes and post[c].notna().all()]
        mismos = [c for c in pool if grupo[c] == g]
        if len(mismos) < min_donantes:
            mismos = [c for c in pool if grupo[c][:3] == g[:3]]
        if len(mismos) < min_donantes:
            continue
        w = pesos_sinteticos(pre[lid].to_numpy(), pre[mismos].to_numpy())
        sint_pre, sint_post = pre[mismos].to_numpy() @ w, post[mismos].to_numpy() @ w
        rmspe = float(np.sqrt(np.mean((pre[lid].to_numpy() - sint_pre) ** 2)))
        gap = post[lid] - sint_post
        sint_pre = pd.Series(sint_pre, index=pre.index)
        brechas[lid] = pd.concat([pre[lid] - sint_pre, gap.dropna()])  # pre (ajuste) + post (brecha)
        filas.append({"linea_id": lid, "n_donantes": len(mismos), "rmspe_pre": rmspe, "brecha_media": float(gap.mean()),
                      "puntaje": float(gap.mean() / max(rmspe, eps)), "meses_post": int(gap.notna().sum())})
    return pd.DataFrame(filas), brechas


# ---------------------------------------------------------------- perjuicio
def sobrecobro_estimado(sim: pd.DataFrame, brechas: dict, lineas: list, inicio: str) -> pd.DataFrame:
    """Sobrecobro por línea-mes = (tarifa media observada − sintética) × viajes, en 'unidades de tarifa × viaje'.

    Para cada línea marcada, la brecha post es lo que cobró de más respecto de su contrafactual sintético.
    Incluye la verdad (recaudación observada − contrafactual simulado) solo para poder evaluar la estimación.
    """
    ini = pd.Timestamp(inicio)
    filas = []
    for lid in lineas:
        gap = brechas[lid][brechas[lid].index >= ini]
        filas.append(pd.DataFrame({"linea_id": lid, "mes": gap.index, "brecha": gap.to_numpy()}))
    est = pd.concat(filas, ignore_index=True)
    est = est.merge(sim[["linea_id", "mes", "empresa_id", "viajes", "recaudacion", "verdad_recaudacion_cf"]], on=["linea_id", "mes"])
    est["sobrecobro_est"] = est.brecha * est.viajes
    est["sobrecobro_real"] = est.recaudacion - est.verdad_recaudacion_cf
    return est


def transferencia_estimada(sub: pd.DataFrame, est: pd.DataFrame, inicio: str, bolsa: float) -> pd.DataFrame:
    """Reasigna la bolsa fija restando a cada empresa su sobrecobro estimado; la diferencia con lo cobrado es la transferencia."""
    o = est.groupby(["empresa_id", "mes"], as_index=False).sobrecobro_est.sum()
    s = sub[sub.mes >= inicio].merge(o, on=["empresa_id", "mes"], how="left").fillna({"sobrecobro_est": 0.0})
    s["rec_corr"] = s.rec - s.sobrecobro_est
    s["subsidio_cf_est"] = bolsa * s.rec_corr / s.groupby("mes").rec_corr.transform("sum")
    s["transferencia_est"] = s.subsidio - s.subsidio_cf_est
    return s
