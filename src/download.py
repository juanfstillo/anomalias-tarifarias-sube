"""Descarga los CSV de la Fase 0 a data/raw/ (no versionado).

Uso: python src/download.py
"""
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

T = "https://datos.transporte.gob.ar/dataset"
U = "https://archivos-datos.transporte.gob.ar/upload/Dat_Ab_Usos"

FILES = {
    # Dataset 2: operaciones de viaje por periodo-modo-jurisdicción-grupo tarifario-empresa-línea
    "operaciones_grupo_tarifario_agregado.csv": f"{T}/a615d532-f4bc-4148-815c-aa0d96d22197/resource/3ca165b6-79c2-41e0-9c1c-357d587c5d86/download/operaciones-de-viaje-por-periodo-modo-jurisdiccion-grupo-tarifario-empresa-linea.csv",
    # Misma serie, con tipo de pasaje
    "operaciones_grupo_tarifario_tipo_pasaje.csv": f"{T}/daa25bf0-5cf3-4c92-98c2-47d8d25e3ff5/resource/03b265af-e60f-4190-938e-171501fee65a/download/operaciones-de-viaje-por-periodo-modo-jurisdiccion-grupo-tarifario-empresa-linea-tipo-de-pasaje.csv",
    # Dataset 3: operaciones por mes en RMBA (detalle de línea)
    "operaciones_mes_linea.csv": f"{T}/880e663e-eb1d-47ec-aab9-23f3df6c49e8/resource/446b61e0-71d3-40c0-b2dd-cb44b0c391ad/download/cancelaciones_mes_mlinea.csv",
    # Catálogo de líneas y empresas
    "lineas_de_transporte.csv": f"{T}/c157c1b3-0f7e-4c6d-b2da-29514fa0c950/resource/4b52a836-d565-4463-a837-31129f8bf7c7/download/lineas-de-transporte.csv",
    # Dataset 4: recorridos de colectivos RMBA (shapefiles zip, se descomprimen en data/raw/recorridos/)
    "recorridos/lineas-nacionales.zip": f"{T}/f87b93d4-ade2-44fc-a409-d3736ba9f3ba/resource/5ab88c4b-b8b0-4f3b-a840-52e0e83e96ab/download/lineas-nacionales.zip",
    "recorridos/lineas-provinciales.zip": f"{T}/f87b93d4-ade2-44fc-a409-d3736ba9f3ba/resource/6dab78ec-d512-4fc4-a5e8-f97a1826ba2f/download/lineas-provinciales.zip",
    "recorridos/lineas-municipales.zip": f"{T}/f87b93d4-ade2-44fc-a409-d3736ba9f3ba/resource/d5b82e09-2844-4adf-8e88-8f20904a7af0/download/lineas-municipales.zip",
    # Dataset 1: transacciones SUBE por día (un archivo por año)
    **{f"usos_{y}.csv": f"{U}/dat-ab-usos-{y}.csv" for y in range(2020, 2027)},
}


def download(name: str, url: str) -> None:
    dest = RAW / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"ya existe  {name}")
        return
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (fraude-sube)"})
    with urlopen(req, timeout=300) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    print(f"descargado {name} ({dest.stat().st_size / 1e6:.1f} MB)")
    if dest.suffix == ".zip":
        with zipfile.ZipFile(dest) as z:
            z.extractall(dest.with_suffix(""))


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        try:
            download(name, url)
        except Exception as e:  # una fuente caída no debe frenar las demás
            print(f"ERROR      {name}: {e}")
