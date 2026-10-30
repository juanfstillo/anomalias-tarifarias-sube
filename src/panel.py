"""Fase 1: panel real línea × mes a partir de las transacciones diarias SUBE."""
import pandas as pd

from io_sube import RAW, cargar_usos, clave_linea

PROCESSED = RAW.parent / "processed"


def construir_panel() -> pd.DataFrame:
    """Colectivos AMBA, agregados por jurisdicción-línea-empresa-mes.

    - `linea_key` normaliza el nombre (ver io_sube.clave_linea); junto con la
      jurisdicción identifica la línea (el número solo no es único).
    - `dias`: días con dato en el mes; `viajes_dia` corrige meses incompletos.
    """
    u = cargar_usos()
    u = u[(u.TIPO_TRANSPORTE == "COLECTIVO") & (u.AMBA == "SI")].copy()
    u["linea_key"] = u.LINEA.map(clave_linea)
    u["mes"] = u.DIA_TRANSPORTE.dt.to_period("M").dt.to_timestamp()
    g = u.groupby(["JURISDICCION", "linea_key", "NOMBRE_EMPRESA", "mes"], as_index=False).agg(
        viajes=("CANTIDAD", "sum"),
        dias=("DIA_TRANSPORTE", "nunique"),
        preliminar=("DATO_PRELIMINAR", lambda s: (s == "SI").any()),
        municipio=("MUNICIPIO", lambda s: s.mode().iat[0] if len(s.mode()) else None),
    )
    g = g.rename(columns={"JURISDICCION": "jurisdiccion", "NOMBRE_EMPRESA": "empresa"})
    g["viajes_dia"] = g.viajes / g.dias
    return g
