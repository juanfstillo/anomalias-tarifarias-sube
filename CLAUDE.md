# Detección de anomalías tarifarias en colectivos (AMBA) con datos SUBE

## Contexto

Proyecto de análisis de datos inspirado en una causa judicial abierta (Infobae, 13/10/2026):
se investiga un presunto fraude de ~$30.000 millones en subsidios a empresas de colectivos.
Según la denuncia, se instruía a choferes a marcar **secciones tarifarias mayores** que el
recorrido real del pasajero. Como los subsidios son una **suma fija repartida entre empresas**,
inflar la recaudación / "distancia media abonada" aumenta la porción de una empresa en
detrimento de las demás. La CNRT registró 136 reclamos por cobros indebidos o mala asignación
de secciones entre mayo 2025 y febrero 2026.

Nota: https://www.infobae.com/judiciales/2026/10/13/avanza-una-investigacion-por-cobrar-de-mas-a-pasajeros-de-colectivos-que-incluye-un-presunto-fraude-en-subsidios/

## Objetivo

Construir un pipeline reproducible que muestre **cómo se detectarían anomalías de este tipo**
con datos, y que sirva como:
- caso práctico para el curso de Data Science para Politólogos (notebooks didácticos),
- proyecto de portfolio en GitHub,
- material para videos de YouTube / posts.

## Encuadre (importante)

- Es una causa judicial abierta. **No se acusa a ninguna empresa.** El proyecto demuestra
  métodos; los resultados sobre datos reales se presentan como "anomalías a revisar", nunca
  como prueba de fraude.
- Las líneas con fraude plantado en la simulación usan identificadores ficticios o se aclara
  explícitamente que el fraude es simulado.
- Foco técnico, no comentario político.

## Variable central

**Tarifa media por viaje (o distribución de viajes por sección), por línea y por mes.**
Se busca detectar cuándo se despega de lo que esperarían (a) su propia historia,
(b) líneas comparables y (c) la geografía del recorrido.

## Fuentes de datos (verificar cada una antes de usar)

1. **Transacciones SUBE por día** (empresa, línea, jurisdicción, tipo de transporte, cantidad)
   https://datos.gob.ar/dataset/transporte-sube---cantidad-transacciones-usos-por-fecha
2. **Operaciones de viaje por Período - Modo - Jurisdicción - Grupo Tarifario - Empresa - Línea**
   https://www.datos.gob.ar/dataset/transporte-sube-operaciones-viaje-por-mes-region-metropolitana-buenos-aires-agregado
   → VERIFICAR qué significa "grupo tarifario": ¿sección tarifaria o tarifa social/normal?
   Si trae secciones, es el dataset clave para datos reales.
3. **Operaciones de SUBE por mes en RMBA** (línea, tipo de pasaje, empresa)
   https://datos.transporte.gob.ar/dataset/operaciones-de-sube-por-mes-en-rmba
4. **Recorridos de líneas RMBA** (shapefile) — en datos.gob.ar, tag RMBA
5. **Viajes y etapas AMBA** (matriz OD a partir de SUBE, día tipo de octubre, GCBA)
   https://cdn.buenosaires.gob.ar/datosabiertos/datasets/transporte-y-obras-publicas/viajes-etapas-transporte-publico/metadatos_viajes_etapas_transporte_publico_amba.pdf
   → útil para calibrar distribuciones realistas de distancia de viaje.

Datos que probablemente **no** son públicos (posible pedido por Ley 27.275 a Secretaría de
Transporte / Nación Servicios): recaudación por línea, viajes por sección tarifaria,
microdatos de validaciones con monto cobrado, reclamos CNRT desagregados.

## Fases

### Fase 0 — Exploración de fuentes
- Script `src/download.py` que baje los CSV a `data/raw/` (no versionar data/raw).
- Notebook `notebooks/00_exploracion.ipynb`: columnas, cobertura temporal (¿llega a 2025-2026?),
  valores de "grupo tarifario", consistencia de nombres de líneas/empresas entre datasets.
- Documentar hallazgos en `docs/fuentes.md`. **Decidir según esto si la Fase 2 usa datos reales
  de secciones o simulados.**

### Fase 1 — Base real
- Panel línea × mes con viajes, empresa, jurisdicción.
- Features por línea desde el shapefile: largo del recorrido, cantidad aproximada de paradas,
  zona/municipios.
- Grupos de líneas comparables (clustering o reglas simples).

### Fase 2 — Capa de secciones simulada (si no hay datos reales)
- Simular por línea-mes la distribución de viajes por sección, condicionada al largo real
  del recorrido (calibrar con distancias de la matriz OD).
- Plantar un "fraude" en un subconjunto de líneas ficticias a partir de una fecha:
  corrimiento de X% de viajes de secciones bajas a altas.
- Calcular el efecto sobre el reparto de una bolsa fija de subsidios entre empresas
  (regla de reparto simplificada y explícita, documentada como supuesto).
- Semilla fija, parámetros en `config.yaml`.

### Fase 3 — Métodos de detección (un notebook por método)
1. `01_changepoints`: quiebres estructurales en tarifa media por línea (`ruptures`).
2. `02_did_control_sintetico`: diferencias en diferencias y control sintético vs líneas
   comparables; estimar monto del perjuicio.
3. `03_coherencia_geografica`: proporción de viajes en sección máxima vs plausibilidad según
   largo del recorrido.
4. `04_anomalias_ml`: Isolation Forest / LOF sobre features línea-mes; ranking de anomalías.
5. (Opcional) `05_inferencia_bajada`: con microdatos simulados de validaciones, inferir parada
   de bajada por encadenamiento de viajes (próxima validación de la tarjeta) y comparar distancia
   estimada vs sección cobrada. Es el método más fuerte; explicar qué datos reales requeriría.

### Fase 4 — Evaluación y comunicación
- Matriz de confusión / precisión-recall de cada método contra el fraude plantado.
- Sensibilidad: ¿desde qué magnitud de fraude cada método lo detecta?
- `README.md` para GitHub con resumen, gráficos y encuadre ético.
- Gráficos limpios exportados a `outputs/figures/` (reutilizables para Instagram/YouTube).
- Borrador de pedido de acceso a la información pública en `docs/pedido_acceso.md`.

## Stack y convenciones

- Python 3.12, entorno con `uv` (o venv). Dependencias: pandas, numpy, geopandas, shapely,
  matplotlib, seaborn, ruptures, statsmodels, scikit-learn, pyyaml, jupyter.
  Control sintético: evaluar `pysyncon` o implementación propia simple.
- Estructura:
  ```
  data/raw/  data/processed/  src/  notebooks/  outputs/figures/  docs/
  ```
- Lógica reutilizable en `src/`, notebooks solo para narrar y graficar.
- Notebooks en español, explicativos, pensados para estudiantes de Ciencia Política
  (explicar cada método en términos intuitivos antes del código).
- Todo reproducible desde cero: `python src/download.py` → notebooks en orden.
- Docker opcional al final.

## Primer paso sugerido

Ejecutar Fase 0 y reportar: qué trae realmente el dataset de "grupo tarifario", hasta qué
fecha llegan los datos y si alcanza para análisis real o hay que ir a simulación.
