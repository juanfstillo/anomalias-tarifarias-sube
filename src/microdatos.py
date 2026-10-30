"""Método 05: microdatos simulados de validaciones e inferencia de la parada de bajada.

El SUBE registra solo el ascenso en colectivo. La bajada se infiere: la próxima validación de la tarjeta ocurre cerca de
donde la persona bajó; para la última del día se usa la primera del día (simetría diaria). Todo es ficticio y 1D: cada línea
es una secuencia de paradas y cada tarjeta usa siempre la misma línea (sin trasbordos ni recorridos que se cruzan).
"""
import numpy as np
import pandas as pd
from scipy.stats import lognorm, ttest_ind


def seccion(d_km: np.ndarray, limites: list) -> np.ndarray:
    """Sección (1..5) de una distancia, según el límite inferior de cada tramo."""
    return np.searchsorted(np.asarray(limites, float), d_km, side="right").astype(np.int8)


def simular_linea(rng, L, cfg, es_fraude, magnitud, meses, inicio_fraude):
    """Validaciones de una línea de largo L km. Devuelve un dict de arrays (una fila por validación)."""
    mc, dv, sec = cfg["micro"], cfg["distancia_viaje"], cfg["secciones"]
    delta, N = mc["espaciado_paradas_km"], int(L / mc["espaciado_paradas_km"]) + 1
    nc = mc["tarjetas_por_linea"]
    mediana = dv["mediana_ref_km"] * (L / dv["largo_ref_km"]) ** dv["elasticidad_largo"] * np.exp(rng.normal(0, dv["efecto_linea_sd"]))
    D = lognorm.ppf(rng.uniform(size=nc) * lognorm.cdf(L, s=dv["sigma_log"], scale=mediana), s=dv["sigma_log"], scale=mediana)
    k = np.clip(np.round(D / delta), 1, N - 1).astype(int)
    dr = rng.choice([-1, 1], nc)
    home = np.where(dr == 1, (rng.uniform(size=nc) * (N - k)).astype(int), 0)
    home = np.where(dr == 1, home, (rng.uniform(size=nc) * (N - k)).astype(int) + k)
    out = {c: [] for c in ["mes", "tarjeta", "dia", "etapa", "sube", "baja_real", "baja_inf", "d_real", "d_inf", "sec_cobrada", "sec_sin_fraude", "sec_inf"]}
    for mes in meses:
        f = np.exp(rng.normal(0, mc["ruido_mes_sd"]))
        nd = np.clip(rng.poisson(mc["dias_mes_media"], nc), 0, 28)
        c = np.repeat(np.arange(nc), nd)
        n = len(c)
        km = np.clip(np.round(k[c] * f), 1, N - 1).astype(int)
        work = np.clip(home[c] + dr[c] * km, 0, N - 1)
        shift = rng.choice([-1, 0, 1], n, p=mc["prob_desplazamiento"])
        work_b = np.clip(work + shift, 0, N - 1)                       # donde se sube en la vuelta
        unico = rng.random(n) < mc["prob_viaje_unico"]
        # etapa 1: home -> work ; etapa 2: work_b -> home (los días de viaje único solo tienen la etapa 1)
        board = np.concatenate([home[c], work_b[~unico]])
        alight = np.concatenate([work, home[c][~unico]])
        etapa = np.concatenate([np.ones(n, np.int8), np.full((~unico).sum(), 2, np.int8)])
        tarj = np.concatenate([c, c[~unico]])
        d_real = np.abs(board - alight) * delta
        # inferencia: bajada = parada del próximo ascenso observado (etapa 1) o primer ascenso del día (etapa 2)
        nxt = np.concatenate([work_b, home[c][~unico]])
        err_gps = rng.choice([-1, 0, 1], len(board), p=[mc["prob_error_gps"] / 2, 1 - mc["prob_error_gps"], mc["prob_error_gps"] / 2])
        alight_hat = np.clip(nxt + err_gps, 0, N - 1)
        d_inf = np.abs(board - alight_hat) * delta
        d_inf[np.concatenate([unico, np.zeros((~unico).sum(), bool)])] = np.nan   # día de una sola validación: sin próxima
        d_inf[rng.random(len(board)) < mc["perdida_inferencia"]] = np.nan
        # sección cobrada: real, con ruido operativo simétrico y, en líneas con fraude, corrimiento hacia arriba
        s_real = seccion(d_real, sec["limites_km"])
        ruido = np.where(rng.random(len(s_real)) < mc["error_operativo"], rng.choice([-1, 1], len(s_real)), 0)
        s_sin = np.clip(s_real + ruido, 1, 5).astype(np.int8)
        s_cob = s_sin.copy()
        if es_fraude and mes >= inicio_fraude:
            mover = (s_real <= cfg["fraude"]["secciones_origen_max"]) & (rng.random(len(s_real)) < magnitud)
            s_cob = np.where(mover, np.minimum(s_real + cfg["fraude"]["salto_secciones"], 5), s_sin).astype(np.int8)
        dia = np.concatenate([np.arange(n), np.arange(n)[~unico]]).astype(np.int32)
        baja_inf = np.where(np.isnan(d_inf), -1, alight_hat).astype(np.int16)
        for nombre, v in [("mes", np.full(len(board), mes.value, np.int64)), ("tarjeta", tarj), ("dia", dia), ("etapa", etapa),
                          ("sube", board.astype(np.int16)), ("baja_real", alight.astype(np.int16)), ("baja_inf", baja_inf), ("d_real", d_real),
                          ("d_inf", d_inf), ("sec_cobrada", s_cob), ("sec_sin_fraude", s_sin),
                          ("sec_inf", np.where(np.isnan(d_inf), 0, seccion(np.nan_to_num(d_inf), sec["limites_km"])).astype(np.int8))]:
            out[nombre].append(v)
    return {k_: np.concatenate(v) for k_, v in out.items()}


def simular_micro(cfg: dict, largos: np.ndarray, magnitud: float | None = None, semilla: int | None = None) -> tuple[pd.DataFrame, pd.Series]:
    """Simula validaciones para `n_lineas` líneas ficticias (M01..) con largos repartidos entre los de las líneas reales."""
    mc = cfg["micro"]
    rng = np.random.default_rng(cfg["semilla"] if semilla is None else semilla)
    magnitud = cfg["fraude"]["magnitud"] if magnitud is None else magnitud
    meses = pd.date_range(mc["desde"], mc["hasta"], freq="MS")
    inicio = pd.Timestamp(cfg["fraude"]["inicio"])
    q = np.quantile(np.sort(largos), (np.arange(mc["n_lineas"]) + 0.5) / mc["n_lineas"])   # largos estratificados
    fraude = np.zeros(mc["n_lineas"], bool)
    fraude[rng.choice(mc["n_lineas"], mc["n_lineas_fraude"], replace=False)] = True
    partes = []
    for i, (L, fr) in enumerate(zip(q, fraude)):
        d = simular_linea(rng, float(L), cfg, bool(fr), magnitud, meses, inicio)
        partes.append(pd.DataFrame(d).assign(linea=f"M{i + 1:02d}", largo_km=L))
    df = pd.concat(partes, ignore_index=True)
    df["mes"] = pd.to_datetime(df["mes"])
    return df, pd.Series(fraude, index=[f"M{i + 1:02d}" for i in range(mc["n_lineas"])], name="fraude")


def resumen_mensual(df: pd.DataFrame, tarifa: list) -> pd.DataFrame:
    """Por línea y mes: lo que ve un analista con y sin la inferencia de bajada."""
    t = np.concatenate([[np.nan], tarifa])           # índice 1..5
    inf = df.d_inf.notna()
    d = df.assign(inf=inf, up=inf & (df.sec_cobrada > df.sec_inf), down=inf & (df.sec_cobrada < df.sec_inf),
                  f_cob=t[df.sec_cobrada], f_sin=t[df.sec_sin_fraude],
                  brecha=np.where(inf, t[df.sec_cobrada] - t[df.sec_inf.clip(lower=1)], np.nan))
    g = d.groupby(["linea", "mes"]).agg(n=("tarjeta", "size"), n_inf=("inf", "sum"), up=("up", "sum"), down=("down", "sum"),
                                        tarifa_media=("f_cob", "mean"), brecha=("brecha", "mean"),
                                        sobrecobro_real=("f_cob", "sum"), sin_fraude=("f_sin", "sum")).reset_index()
    g["neto"] = (g.up - g.down) / g.n_inf
    g["sobrecobro_real"] = g.sobrecobro_real - g.sin_fraude
    return g.drop(columns="sin_fraude")


def test_linea(m: pd.DataFrame, col: str, inicio: str, n_lineas: int, alfa: float = 0.05) -> pd.DataFrame:
    """Welch t (una cola) de `col` entre meses posteriores y previos al inicio, por línea; umbral Bonferroni alfa/n_lineas."""
    ini = pd.Timestamp(inicio)
    filas = []
    for ln, g in m.groupby("linea"):
        a, b = g[g.mes >= ini][col].to_numpy(), g[g.mes < ini][col].to_numpy()
        r = ttest_ind(a, b, equal_var=False, alternative="greater")
        filas.append({"linea": ln, "t": r.statistic, "p": r.pvalue, "dif": a.mean() - b.mean(), "marca": r.pvalue < alfa / n_lineas})
    return pd.DataFrame(filas).set_index("linea")


def evaluar_corrida(cfg: dict, largos: np.ndarray, magnitud: float, semilla: int) -> dict:
    """Una simulación completa: compara la detección con inferencia de bajada vs. mirando solo la tarifa media."""
    from sklearn.metrics import roc_auc_score
    tarifa, inicio, n = cfg["secciones"]["tarifa_relativa"], cfg["fraude"]["inicio"], cfg["micro"]["n_lineas"]
    df, fr = simular_micro(cfg, largos, magnitud, semilla)
    m = resumen_mensual(df, tarifa)
    a, b = test_linea(m, "neto", inicio, n), test_linea(m, "tarifa_media", inicio, n)
    out = {"magnitud": magnitud, "semilla": semilla}
    for nombre, x in [("inferencia", a), ("tarifa_media", b)]:
        x = x.join(fr)
        out.update({f"{nombre}_tp": int((x.marca & x.fraude).sum()), f"{nombre}_fp": int((x.marca & ~x.fraude).sum()),
                    f"{nombre}_fn": int((~x.marca & x.fraude).sum()), f"{nombre}_tn": int((~x.marca & ~x.fraude).sum()),
                    f"{nombre}_auc": roc_auc_score(x.fraude, x.t)})
    # perjuicio: diferencia de brecha (cobrado − inferido) entre post y pre, por validación, extrapolada a todas las validaciones del post
    ini = pd.Timestamp(inicio)
    est = real = 0.0
    for ln in a.index[a.marca]:
        g = m[m.linea == ln]
        dif = g[g.mes >= ini].brecha.mean() - g[g.mes < ini].brecha.mean()
        est += dif * g[g.mes >= ini].n.sum()
        real += g[g.mes >= ini].sobrecobro_real.sum()
    out.update({"sobrecobro_est": est, "sobrecobro_real_marcadas": real, "sobrecobro_real_total": float(m[(m.mes >= ini)].sobrecobro_real.sum())})
    return out
