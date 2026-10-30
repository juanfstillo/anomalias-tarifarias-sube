"""Fase 1: features geográficos por línea desde los shapefiles de recorridos."""
import geopandas as gpd
import numpy as np
import pandas as pd

from io_sube import RAW, clave_linea

CRS_METROS = "EPSG:5347"  # POSGAR 2007 / Argentina 5 (Buenos Aires), unidades en metros
OBELISCO = (-58.3816, -34.6037)  # proxy del centro de la región (lon, lat)
ESPACIADO_PARADAS_KM = 0.35  # SUPUESTO: no hay datos de paradas; ver docs/fuentes.md


def features_recorridos() -> pd.DataFrame:
    """Una fila por (jurisdicción, línea): largo, ramales, distancia al centro, etc."""
    partes = [gpd.read_file(f) for f in sorted((RAW / "recorridos").glob("*/*.shp"))]
    g = pd.concat(partes, ignore_index=True)
    g = gpd.GeoDataFrame(g, geometry="geometry", crs=partes[0].crs)
    g["jurisdiccion"] = g["JURISDICCI"].str.upper()
    g["linea_key"] = g["LINEA"].astype(str).map(clave_linea)
    g = g.to_crs(CRS_METROS)
    g["largo_km"] = g.length / 1000
    centro = gpd.GeoSeries.from_xy([OBELISCO[0]], [OBELISCO[1]], crs="EPSG:4326").to_crs(CRS_METROS).iloc[0]
    g["dist_centro_km"] = g.geometry.centroid.distance(centro) / 1000
    g["extremo_km"] = g.geometry.apply(lambda s: max(s.bounds[2] - s.bounds[0], s.bounds[3] - s.bounds[1])) / 1000

    # Un "recorrido" es ramal × sentido: el largo de la línea es el promedio de sus recorridos.
    f = g.groupby(["jurisdiccion", "linea_key"]).agg(
        largo_km=("largo_km", "mean"),
        largo_max_km=("largo_km", "max"),
        n_ramales=("RAMAL", "nunique"),
        dist_centro_km=("dist_centro_km", "mean"),
        extremo_km=("extremo_km", "mean"),
    ).reset_index()
    f["paradas_aprox"] = (f.largo_km / ESPACIADO_PARADAS_KM).round()
    return f


def _base(key: str) -> str:
    """'501G' / '501 A' -> '501' (el shapefile guarda el ramal en otra columna)."""
    import re
    return re.sub(r"(?<=\d)\s*[A-Z]$", "", key)


def unir_recorridos(lineas: pd.DataFrame, feats: pd.DataFrame) -> pd.DataFrame:
    """Cruza líneas del panel con features de recorrido, en cascada, y registra cómo cruzó.

    1. exacto: (jurisdicción, línea)
    2. C.A.B.A del SUBE -> NACIONAL del shapefile (esas líneas cruzan la Gral. Paz)
    3. base: se quita la letra final de ramal ('501G' -> '501')
    """
    cols = [c for c in feats.columns if c not in ("jurisdiccion", "linea_key")]
    f = feats.set_index(["jurisdiccion", "linea_key"])
    out = []
    for _, r in lineas.iterrows():
        jur = "NACIONAL" if r.jurisdiccion == "C.A.B.A" else r.jurisdiccion
        for how, key in (("exacto", r.linea_key), ("base", _base(r.linea_key))):
            if (jur, key) in f.index:
                if how == "exacto" and jur != r.jurisdiccion:
                    how = "caba->nacional"
                out.append((how, f.loc[(jur, key), cols].tolist()))
                break
        else:
            out.append((None, [np.nan] * len(cols)))
    res = lineas.copy()
    res["match_geo"] = [o[0] for o in out]
    res[cols] = [o[1] for o in out]
    res["jur_geo"] = res.jurisdiccion.replace({"C.A.B.A": "NACIONAL"})
    return res
