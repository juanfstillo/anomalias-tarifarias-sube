"""Construye data/processed/{panel,lineas}.parquet. Uso: python src/build_base.py"""
import pandas as pd

from features import features_recorridos, unir_recorridos
from grupos import asignar_grupos
from panel import PROCESSED, construir_panel

if __name__ == "__main__":
    PROCESSED.mkdir(parents=True, exist_ok=True)
    panel = construir_panel()
    feats = features_recorridos()
    # Línea a nivel de resumen: mediana de viajes/día sobre meses completos
    completos = panel[panel.dias >= 25]
    resumen = completos.groupby(["jurisdiccion", "linea_key"]).agg(
        empresa=("empresa", lambda s: s.mode().iat[0]),
        municipio=("municipio", lambda s: s.mode().iat[0]),
        viajes_dia_med=("viajes_dia", "median"),
        meses=("mes", "nunique"),
    ).reset_index()
    lineas = unir_recorridos(resumen, feats)
    print(lineas.match_geo.value_counts(dropna=False).to_dict())
    print(f"líneas en panel: {len(lineas)} | con recorrido: {lineas.largo_km.notna().sum()}")
    print("viajes cubiertos por recorrido: "
          f"{lineas[lineas.largo_km.notna()].viajes_dia_med.sum() / lineas.viajes_dia_med.sum():.1%}")
    con_geo = lineas.dropna(subset=["largo_km"])
    lineas = lineas.merge(asignar_grupos(con_geo)[["jurisdiccion", "linea_key", "grupo"]],
                          on=["jurisdiccion", "linea_key"], how="left")
    panel = panel.merge(lineas[["jurisdiccion", "linea_key", "grupo"]].drop_duplicates(),
                        on=["jurisdiccion", "linea_key"], how="left")
    panel.to_parquet(PROCESSED / "panel.parquet")
    lineas.to_parquet(PROCESSED / "lineas.parquet")
    print(panel.shape, lineas.shape)
    print(lineas.groupby("grupo").agg(n=("linea_key", "size"), largo=("largo_km", "median"),
                                      centro=("dist_centro_km", "median"), vd=("viajes_dia_med", "median")).round(1))
