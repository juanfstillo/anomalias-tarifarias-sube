# Fuentes de datos: hallazgos de la Fase 0

Verificado el 2026-10-29. Reproducir con `python src/download.py` y `notebooks/00_exploracion.ipynb`.

## Resumen

**No existe dato público con secciones tarifarias ni montos cobrados.** La Fase 2 debe usar una capa de secciones **simulada**, montada sobre el panel real de líneas y empresas.

## Fuente por fuente

### 1. Transacciones SUBE por día (`dat-ab-usos-AAAA.csv`)
- Columnas: `DIA_TRANSPORTE, NOMBRE_EMPRESA, LINEA, AMBA, TIPO_TRANSPORTE, JURISDICCION, PROVINCIA, MUNICIPIO, CANTIDAD, DATO_PRELIMINAR`.
- Cobertura: **2020-01-01 a 2026-10-27**. Datos marcados preliminares desde 2026-02-01.
- AMBA, colectivo: ~380 líneas por mes, 163 empresas, ~200 M transacciones/mes.
- Solo cantidad de transacciones. Sin monto ni sección.
- **Uso:** base del panel línea × mes (Fase 1).
- Nota: el slug de CKAN difiere del indicado originalmente (`sube-cantidad-de-transacciones-usos-por-fecha`).

### 2. Operaciones de viaje por Período-Modo-Jurisdicción-Grupo Tarifario-Empresa-Línea
- Slug real: `sube-operaciones-viaje-por-mes-region-metropolitana-buenos-aires-agregado` (CSV separado por `;`, codificación latin-1).
- Cobertura: **2013-01 a 2019-10** (la descripción dice 06/2019; los archivos traen hasta 201910). Sin actualizaciones desde 2022.
- **"Grupo tarifario" no es sección.** Valores: `S.G.I.`, `S.G.II.`, `D.F.` (nacional), `U.P.A.`, `U.P.A.M` (provincial), `U.M.A.1.`, `U.M.A.2.` (municipal) y `-`. Cada grupo corresponde a una jurisdicción y se define "según normativa" (diccionario oficial). Es un régimen tarifario administrativo, no una distancia recorrida.
- Existe una variante con `TIPO PASAJE` (normal, atributo social, escolar, etc.).
- **Uso:** solo contexto histórico y validación cruzada de nombres. No sirve para detectar el patrón denunciado.

### 3. Operaciones de SUBE por mes en RMBA
- Cobertura: 2016 a 09/2019. Línea, tipo de pasaje, empresa. Sin sección. Redundante con la fuente 2.

### 4. Catálogo de líneas y empresas (`lineas-de-transporte`)
- Útil como tabla puente línea-empresa-modo, con la misma cobertura (hasta 2019).

### 4b. Recorridos de colectivos RMBA (shapefiles, verificado en Fase 1)
- Dataset `recorridos-de-lineas-de-transporte-rmba-jn`: tres shapefiles (nacional 1172, provincial 600, municipal 459 recorridos), EPSG:4326.
- Columnas: `LINEA, RAMAL, SENTIDO, JURISDICCI`. **No trae paradas ni municipios.**
- Features derivados (`src/features.py`): largo (km, proyectado a POSGAR 2007 faja 5), cantidad de ramales, distancia al Obelisco y extensión.
- **Supuesto:** `paradas_aprox` = largo ÷ 350 m. No es dato; es una aproximación.
- Cruce con el panel en cascada (`unir_recorridos`): exacto (277 líneas), C.A.B.A→NACIONAL (31), sin letra de ramal (54). **70 líneas sin recorrido** (16 % de las líneas, 7,3 % de los viajes). Las 362 restantes cubren el 92,7 % de los viajes.
- Las cruzadas por quitar la letra de ramal (`501G`→`501`) son una heurística: pueden asignar el largo de otra variante.

### 5. Matriz OD de GCBA
- **Verificado solo el metadato** (PDF oficial, abril 2025); **no se ubicó el archivo de datos**: la API de GCBA no respondió y una búsqueda no dio el enlace directo.
- Lo que dice el metadato: día típico de octubre/noviembre por año, 2019-2025; tablas de etapas, viajes y departamentos; orígenes y destinos en hexágonos H3 (resolución 10), **sin línea, solo modo**; destinos **imputados** (parada más cercana al origen de la etapa siguiente, y simetría diaria); incluye factores de expansión.
- Confirma que **el SUBE no registra los descensos en colectivo** (solo ascensos), que es el punto de partida de este proyecto.
- Consecuencia: la distribución de distancias de viaje de la Fase 2 es un **modelo supuesto, no calibrado**. Calibrarlo con esta matriz queda como mejora pendiente.

## Consistencia de nombres línea/empresa
- Los nombres de línea **no coinciden** entre datasets: 31 coincidencias exactas contra 361 con una clave normalizada (`io_sube.clave_linea`: se quitan prefijos `BSAS_`, `LINEA`, ceros a la izquierda).
- Con esa clave, el 97,4 % de las transacciones 2020 cuyas líneas están en la fuente 1 también aparecen en la fuente 2.
- Empresas: 141 nombres coinciden exactos entre ambas fuentes (de 188 y 162). Hace falta una tabla de equivalencias.
- 21 líneas aparecen con más de una empresa en la fuente 1. El identificador de línea no es único: la clave debe incluir empresa y jurisdicción.

## Datos que no son públicos
Recaudación por línea, viajes por sección tarifaria, microdatos de validaciones con monto cobrado y reclamos CNRT desagregados. Posible pedido por Ley 27.275 (Fase 4, `docs/pedido_acceso.md`).

## Decisión
Fase 1 con datos reales (panel desde fuente 1). Fase 2 con secciones simuladas, con el fraude plantado en líneas ficticias o aclarado como simulado.
