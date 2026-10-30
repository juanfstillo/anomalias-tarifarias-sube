"""Fase 4: protocolo unificado para comparar los métodos.

Todos los métodos deciden con la misma información (datos hasta `as_of`), calibran su umbral con un placebo a la
misma distancia y se evalúan contra la misma verdad: línea con al menos un mes de fraude activo en la ventana.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

import anomalias as an
import changepoints as cp
import coherencia as co
import did_sc as sc
from simular import cargar_config

AS_OF = "2026-06-01"        # decisión con 6 meses de fraude (ene-jun 2026)
PLACEBO_AS_OF = "2025-12-01"  # mismo cálculo 6 meses antes: sin fraude
INICIO = "2026-01-01"
VENTANA = 6
FPR_OBJETIVO = 0.05


def _puntaje_linea_ventana(sim, col, hasta):
    return co.puntaje_linea(sim, col, hasta, VENTANA)


def correr_metodos(sim: pd.DataFrame, cfg: dict | None = None) -> dict:
    """Devuelve {método: DataFrame[linea_id → score, flag]} usando datos hasta AS_OF."""
    cfg = cfg or cargar_config()
    lim = cfg["secciones"]["limites_km"]
    s = sim[sim.mes <= AS_OF].copy()
    out = {}

    # ---- 01 quiebres
    wide_rel = cp.serie_relativa(s)
    beta, _ = cp.calibrar_beta(wide_rel, hasta=INICIO, tasa_objetivo=FPR_OBJETIVO)
    r1 = cp.detectar(wide_rel, beta=beta)
    r1 = r1[r1.n_meses >= 12]
    out["01 Quiebres"] = pd.DataFrame({"score": r1.set_index("linea_id").salto_sigma,
                                       "flag": r1.set_index("linea_id").mes_quiebre.notna()})

    # ---- 02 control sintético (fecha placebo con la misma cantidad de meses post)
    wide = s.pivot(index="mes", columns="linea_id", values="tarifa_media")
    grupo = s.drop_duplicates("linea_id").set_index("linea_id").grupo
    donantes_excl = set(r1.linea_id[r1.mes_quiebre.notna()])
    pl, _ = sc.control_sintetico(wide, grupo, "2025-07-01", "2025-12-01")
    r2, _ = sc.control_sintetico(wide, grupo, INICIO, excluir_donantes=donantes_excl)
    thr = pl.puntaje.quantile(1 - FPR_OBJETIVO)
    r2 = r2.set_index("linea_id")
    out["02 Control sintético"] = pd.DataFrame({"score": r2.puntaje,
                                                "flag": (r2.puntaje > thr) & (r2.brecha_media > 0) & (r2.meses_post >= 3)})

    # ---- 03 coherencia geográfica
    s["z_altas"] = co.exceso_altas(s)
    s["imp"] = co.viajes_imposibles(s, lim, tol=0.10)
    z, zn = _puntaje_linea_ventana(s, "z_altas", AS_OF), _puntaje_linea_ventana(s, "z_altas", PLACEBO_AS_OF)
    imp = _puntaje_linea_ventana(s, "imp", AS_OF)
    out["03 Coherencia geográfica"] = pd.DataFrame({"score": z, "flag": (z > zn.quantile(1 - FPR_OBJETIVO)) | (imp.reindex(z.index) > 0)})

    # ---- 04 anomalías ML (entrenar hasta dic-2025; placebo: entrenar hasta jun-2025 y puntuar jul-dic 2025)
    d = an.rasgos(s)
    for etiqueta, modelo, cols in [("04a Isolation Forest", "iforest", an.NIVELES + an.CAMBIOS), ("04b LOF", "lof", an.NIVELES)]:
        A, B = an.Detector(modelo, cols, "2025-12-01").fit(d), an.Detector(modelo, cols, "2025-06-01").fit(d)
        r, n = an.puntaje_linea(d, A.puntuar(d), AS_OF, VENTANA), an.puntaje_linea(d, B.puntuar(d), PLACEBO_AS_OF, VENTANA)
        out[etiqueta] = pd.DataFrame({"score": r, "flag": r > n.quantile(1 - FPR_OBJETIVO)})
    return out


def verdad(sim: pd.DataFrame) -> pd.Series:
    """Línea expuesta = al menos un mes de fraude activo en la ventana de decisión."""
    h = pd.Timestamp(AS_OF)
    d = sim[(sim.mes <= h) & (sim.mes > h - pd.DateOffset(months=VENTANA))]
    return d.groupby("linea_id").verdad_fraude_activo.any()


def metricas(resultados: dict, v: pd.Series) -> pd.DataFrame:
    """Métricas por método: sobre las líneas evaluables por TODOS los métodos y sobre todas las expuestas."""
    comun = set.intersection(*[set(r.index) for r in resultados.values()]) & set(v.index)
    comun = sorted(comun)
    filas = []
    for m, r in resultados.items():
        rc, yc = r.loc[comun], v.loc[comun]
        f = rc.flag.astype(bool)
        tp, fp, fn, tn = int((f & yc).sum()), int((f & ~yc).sum()), int((~f & yc).sum()), int((~f & ~yc).sum())
        k = int(yc.sum())
        exp_total = v[v].index
        tp_total = int(r.flag.reindex(exp_total).fillna(False).astype(bool).sum())
        filas.append({"metodo": m, "n_comun": len(comun), "expuestas_comun": k, "TP": tp, "FP": fp, "FN": fn, "TN": tn,
                      "recall": tp / max(tp + fn, 1), "precision": tp / max(tp + fp, 1) if tp + fp else np.nan,
                      "fpr": fp / max(fp + tn, 1),
                      "auc": roc_auc_score(yc, rc.score) if 0 < k < len(yc) else np.nan,
                      "precision_en_top_k": float(yc.loc[rc.score.sort_values(ascending=False).head(k).index].mean()) if k else np.nan,
                      "recall_sobre_todas_expuestas": tp_total / max(len(exp_total), 1),
                      "cobertura_expuestas": float(pd.Index(exp_total).isin(r.index).mean())})
    return pd.DataFrame(filas)
