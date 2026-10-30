#!/usr/bin/env bash
# Reproduce todo el pipeline: descarga -> base real -> simulación -> notebooks.
# Variables: SKIP_BARRIDO=1 salta el barrido de sensibilidad (~25 min) y el notebook 06.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 1/4 Descarga de fuentes (data/raw)"
python src/download.py

echo "== 2/4 Base real y simulación (data/processed)"
(cd src && python build_base.py && python build_sim.py)

echo "== 3/4 Notebooks de datos y métodos"
run_nb() { jupyter nbconvert --to notebook --execute --inplace "notebooks/$1.ipynb" --log-level WARN; }
for nb in 00_exploracion 00b_panel_base 00c_simulacion_secciones 01_changepoints 02_did_control_sintetico \
          03_coherencia_geografica 04_anomalias_ml 05_inferencia_bajada; do
  echo "   - $nb"; run_nb "$nb"
done

echo "== 4/4 Evaluación comparativa"
if [ "${SKIP_BARRIDO:-0}" = "1" ]; then
  echo "   SKIP_BARRIDO=1: se omite el barrido y el notebook 06"
else
  (cd src && python barrido.py)
  run_nb 06_evaluacion_comparativa
fi
echo "Listo. Gráficos en outputs/figures/, tablas en data/processed/."
