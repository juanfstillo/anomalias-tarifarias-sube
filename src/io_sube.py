"""Carga y normalización de las fuentes SUBE (Fase 0)."""
import re
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def cargar_operaciones(nombre: str = "operaciones_grupo_tarifario_agregado.csv") -> pd.DataFrame:
    """Operaciones de viaje 2013-2019 por período-modo-jurisdicción-grupo tarifario-empresa-línea."""
    df = pd.read_csv(RAW / nombre, sep=";", encoding="latin-1")
    df = df.rename(columns={"Suma de CANTIDAD": "cantidad", "GRUPO TARIFARIO": "grupo_tarifario"})
    df["periodo"] = pd.to_datetime(df["PERIODO"].astype(str), format="%Y%m")
    return df


def cargar_usos(anios=range(2020, 2027)) -> pd.DataFrame:
    """Transacciones diarias por línea (2020 a la fecha)."""
    df = pd.concat(pd.read_csv(RAW / f"usos_{a}.csv") for a in anios)
    df["DIA_TRANSPORTE"] = pd.to_datetime(df["DIA_TRANSPORTE"])
    return df


def clave_linea(nombre) -> str:
    """Clave común para cruzar nombres de línea entre datasets
    ('LINEA 060', 'BSAS_LINEA_060' y '60' -> '60')."""
    s = str(nombre).upper()
    s = re.sub(r"^(BSAS|BS_AS|CABA)[_ ]*", "", s)
    s = re.sub(r"LINEA[_ ]*", "", s)
    s = re.sub(r"\s+MERCEDES$", "", s).strip(" _")
    return re.sub(r"^0+(?=\d)", "", s)
