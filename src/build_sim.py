"""Construye data/processed/{sim_secciones,sim_subsidio}.parquet. Uso: python src/build_sim.py"""
import pandas as pd

from panel import PROCESSED
from simular import cargar_config, repartir_subsidio, simular

if __name__ == "__main__":
    cfg = cargar_config()
    panel = pd.read_parquet(PROCESSED / "panel.parquet")
    lineas = pd.read_parquet(PROCESSED / "lineas.parquet")
    sim = simular(panel, lineas, cfg)
    sub = repartir_subsidio(sim, cfg)
    sim.to_parquet(PROCESSED / "sim_secciones.parquet")
    sub.to_parquet(PROCESSED / "sim_subsidio.parquet")

    l = sim.drop_duplicates("linea_id")
    print(f"filas: {len(sim)} | líneas: {len(l)} | empresas: {sim.empresa_id.nunique()}")
    print(f"líneas con fraude: {l.verdad_linea_fraude.sum()} ({l.verdad_linea_fraude.mean():.1%}) "
          f"de {sim[sim.verdad_linea_fraude].empresa_id.nunique()} empresas")
    print(f"meses: {sim.mes.min().date()} → {sim.mes.max().date()} | con fraude activo: {sim.verdad_fraude_activo.sum()} filas")
    chk = (sim[["v1", "v2", "v3", "v4", "v5"]].sum(axis=1) == sim.viajes).all()
    imposibles = (sim.viajes_sec_imposible > 0).groupby(sim.verdad_fraude_activo).mean()
    print("suma de secciones == viajes:", chk)
    print("% filas con viajes en secciones geográficamente imposibles (sección cuyo límite inferior supera el largo de la ruta), por fraude_activo:")
    print(imposibles.round(3).to_dict())
    d = sim[sim.verdad_linea_fraude & sim.mes.ge("2026-01-01")]
    print(f"tarifa media líneas fraude desde 2026: {d.tarifa_media.mean():.4f} vs contrafactual {d.verdad_tarifa_media_cf.mean():.4f}"
          f" (+{d.tarifa_media.mean() / d.verdad_tarifa_media_cf.mean() - 1:.2%})")
    t = sub[sub.mes >= "2026-01-01"].groupby("empresa_fraude").transferencia.sum()
    print("transferencia acumulada 2026 (unidades de bolsa mensual=100), por grupo de empresa:", t.round(2).to_dict())
