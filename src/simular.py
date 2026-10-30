"""Fase 2: capa de secciones tarifarias SIMULADA sobre el panel real de líneas.

Todo lo que sale de acá es ficticio: las líneas y empresas se anonimizan (L001, E001) y el
fraude se planta sobre esos identificadores. No hay forma de leer estos resultados como
afirmaciones sobre empresas reales.

Desidentificación: con semilla fija y datos de entrada públicos, el mapeo línea real -> id ficticio (y qué
empresas reciben el fraude) sería reconstruible por cualquiera. Por eso esas decisiones salen de un generador que
depende de una SAL SECRETA (variable de entorno FRAUDE_SUBE_SAL o archivo `.sal`, no versionado). Además, cada línea
recibe un factor secreto de escala en sus viajes y un pequeño jitter en el largo y la distancia al centro, para que
los valores impresos en los notebooks no coincidan con los de los datos públicos.
"""
import hashlib
import os
import secrets
import sys

import numpy as np
import pandas as pd
import yaml
from scipy.stats import lognorm

from io_sube import RAW

CONFIG = RAW.parents[1] / "config.yaml"


def cargar_config(path=CONFIG) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


SAL_ARCHIVO = RAW.parents[1] / ".sal"


def obtener_sal() -> int:
    """Sal secreta: FRAUDE_SUBE_SAL, o el archivo `.sal`; si no existe ninguna, se genera una y se guarda (no se versiona)."""
    if os.environ.get("FRAUDE_SUBE_SAL"):
        texto = os.environ["FRAUDE_SUBE_SAL"]
    elif SAL_ARCHIVO.exists():
        texto = SAL_ARCHIVO.read_text().strip()
    else:
        texto = secrets.token_hex(16)
        SAL_ARCHIVO.write_text(texto + "\n")
        SAL_ARCHIVO.chmod(0o600)
        print(f"[simular] Se generó una sal secreta nueva en {SAL_ARCHIVO.name}. No la publiques: los resultados "
              "dependen de ella (otra sal => otra asignación del fraude).", file=sys.stderr)
    return int.from_bytes(hashlib.sha256(texto.encode()).digest()[:8], "big") >> 1


def probs_secciones(largo_km, mediana_km, sigma, limites) -> np.ndarray:
    """P(sección k) para un viaje lognormal truncado a [0, largo]. Sección imposible => 0."""
    cortes = np.append(np.asarray(limites, float), np.inf)
    F = lambda x: lognorm.cdf(x, s=sigma, scale=mediana_km)
    total = F(largo_km)
    p = np.array([max(F(min(b, largo_km)) - F(a), 0.0) if a < largo_km else 0.0
                  for a, b in zip(cortes[:-1], cortes[1:])])
    return p / total


def elegir_empresas_fraude(lineas_por_empresa: pd.Series, cfg_f: dict, rng) -> list:
    """Empresas completas hasta acercarse a la proporción objetivo de líneas (sin pasarse de la tolerancia)."""
    total = lineas_por_empresa.sum()
    objetivo, tol = cfg_f["proporcion_lineas"], cfg_f["tolerancia"]
    elegidas, acum = [], 0
    for emp in rng.permutation(lineas_por_empresa.index):
        n = lineas_por_empresa[emp]
        if (acum + n) / total <= objetivo + tol:
            elegidas.append(emp)
            acum += n
        if acum / total >= objetivo - tol:
            break
    return elegidas


def simular(panel: pd.DataFrame, lineas: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    rng = np.random.default_rng(cfg["semilla"])                    # ruido de la simulación (reproducible con la semilla)
    priv = np.random.default_rng([cfg["semilla"], obtener_sal()])  # decisiones que no deben poder reconstruirse
    sec, dv, fr = cfg["secciones"], cfg["distancia_viaje"], cfg["fraude"]
    ns = len(sec["limites_km"])
    tarifa = np.array(sec["tarifa_relativa"])

    # --- universo: líneas con geografía y meses completos
    base = panel[(panel.dias >= cfg["panel"]["min_dias"])].merge(
        lineas.dropna(subset=["largo_km"])[["jurisdiccion", "linea_key", "largo_km", "dist_centro_km", "n_ramales"]],
        on=["jurisdiccion", "linea_key"])
    # una "línea" es jurisdicción + número + empresa (el número solo no es único)
    clave = base.jurisdiccion + "|" + base.linea_key + "|" + base.empresa

    # --- desidentificación: factor secreto por línea sobre volumen y geografía (ver docstring del módulo)
    def ruido_linea(sd):
        u = clave.unique()
        return np.exp(clave.map(pd.Series(priv.normal(0, sd, len(u)), index=u)))
    base["viajes_dia"] = base.viajes_dia * ruido_linea(0.25)
    base["largo_km"] = base.largo_km * ruido_linea(0.10)
    base["dist_centro_km"] = base.dist_centro_km * ruido_linea(0.10)
    base["viajes_mes"] = np.round(base.viajes_dia * base.mes.dt.days_in_month).astype(np.int64)

    # --- anonimización: ids ficticios en orden aleatorio (generador privado)
    def anon(valores, pref):
        u = priv.permutation(valores.unique())
        return valores.map({k: f"{pref}{i + 1:03d}" for i, k in enumerate(u)})
    base["linea_id"] = anon(clave, "L")
    base["empresa_id"] = anon(base.empresa, "E")

    # --- selección del fraude (a nivel empresa, generador privado)
    lxe = base.drop_duplicates("linea_id").groupby("empresa_id").size()
    emp_fraude = set(elegir_empresas_fraude(lxe, fr, priv))
    base["verdad_linea_fraude"] = base.empresa_id.isin(emp_fraude)

    # --- probabilidades de sección por línea-mes
    ef_linea = pd.Series(rng.normal(0, dv["efecto_linea_sd"], base.linea_id.nunique()), index=base.linea_id.unique())
    mediana = (dv["mediana_ref_km"] * (base.largo_km / dv["largo_ref_km"]) ** dv["elasticidad_largo"]
               * np.exp(base.linea_id.map(ef_linea) + rng.normal(0, dv["ruido_mensual_sd"], len(base))))
    P = np.vstack([probs_secciones(L, m, dv["sigma_log"], sec["limites_km"])
                   for L, m in zip(base.largo_km.to_numpy(), mediana.to_numpy())])
    cf = np.vstack([rng.multinomial(n, p) for n, p in zip(base.viajes_mes.to_numpy(), P)])  # contrafactual

    # --- fraude: corrimiento de viajes bajos a altos
    inicio = pd.Timestamp(fr["inicio"])
    meses_desde = ((base.mes.dt.year - inicio.year) * 12 + base.mes.dt.month - inicio.month).to_numpy()
    r = fr["rampa_meses"]
    intensidad = np.where(meses_desde < 0, 0.0, 1.0 if r == 0 else np.minimum((meses_desde + 1) / r, 1.0))
    activo = base.verdad_linea_fraude.to_numpy() & (intensidad > 0)
    obs = cf.copy()
    for s in range(fr["secciones_origen_max"]):
        mov = rng.binomial(cf[:, s], np.where(activo, fr["magnitud"] * intensidad, 0.0))
        obs[:, s] -= mov
        obs[np.arange(len(obs)), np.minimum(s + fr["salto_secciones"], ns - 1)] += mov
    base["verdad_fraude_activo"] = activo

    # --- variables observables y contrafactuales
    for k in range(ns):
        base[f"v{k + 1}"] = obs[:, k]
    viajes = obs.sum(1)
    base["viajes"] = viajes
    base["tarifa_media"] = obs @ tarifa / viajes
    base["dist_media_abonada"] = obs @ np.array(sec["punto_medio_km"]) / viajes
    base["pct_sec_max"] = obs[:, -1] / viajes
    base["recaudacion"] = obs @ tarifa
    base["verdad_tarifa_media_cf"] = cf @ tarifa / viajes
    base["verdad_recaudacion_cf"] = cf @ tarifa
    lim = np.asarray(sec["limites_km"], float)
    base["viajes_sec_imposible"] = (obs * (lim[None, :] >= base.largo_km.to_numpy()[:, None])).sum(axis=1)
    return base[["linea_id", "empresa_id", "jurisdiccion", "grupo", "mes", "largo_km", "dist_centro_km", "n_ramales",
                 "viajes", *[f"v{k + 1}" for k in range(ns)], "tarifa_media", "dist_media_abonada", "pct_sec_max",
                 "recaudacion", "viajes_sec_imposible", "verdad_linea_fraude", "verdad_fraude_activo", "verdad_tarifa_media_cf",
                 "verdad_recaudacion_cf"]].reset_index(drop=True)


def repartir_subsidio(sim: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Reparto de una bolsa fija entre empresas, proporcional a la recaudación (regla simplificada).

    Devuelve por empresa-mes: subsidio observado, contrafactual (sin fraude) y la transferencia entre ambos.
    """
    F = cfg["subsidio"]["bolsa_mensual"]
    e = sim.groupby(["empresa_id", "mes"], as_index=False).agg(
        rec=("recaudacion", "sum"), rec_cf=("verdad_recaudacion_cf", "sum"),
        empresa_fraude=("verdad_linea_fraude", "max"))
    e["subsidio"] = F * e.rec / e.groupby("mes").rec.transform("sum")
    e["subsidio_cf"] = F * e.rec_cf / e.groupby("mes").rec_cf.transform("sum")
    e["transferencia"] = e.subsidio - e.subsidio_cf
    return e
