# Guía de estudio: aprender estadística con este proyecto

Esta guía usa el proyecto como material de estudio. Tiene dos partes: **el formato** (cómo está armada la investigación y por qué) y **los conceptos** (qué estadística aparece, en qué archivo, y cómo practicarla).

> Los resultados del proyecto son **simulados**: sirven para aprender métodos, no para afirmar nada sobre empresas reales.

---

## Parte 1 · El formato de la investigación

Una investigación de datos ordenada sigue una secuencia. Cada paso responde una pregunta y deja un producto concreto en el repositorio.

| Paso | Pregunta que responde | Dónde está |
|---|---|---|
| 1. Pregunta y encuadre | ¿Qué queremos saber, y qué NO podemos afirmar? | `CLAUDE.md`, `README.md` (sección *Encuadre*) |
| 2. Auditoría de datos | ¿Qué miden realmente las variables? ¿Alcanzan? | `00_exploracion`, `docs/fuentes.md` |
| 3. Base descriptiva | ¿Cómo se ve lo observable, y con qué comparar? | `00b_panel_base` |
| 4. Diseño de la simulación | Si no hay datos, ¿cómo construyo un escenario con verdad conocida? | `00c_simulacion_secciones`, `config.yaml` |
| 5. Métodos de detección | ¿Qué técnicas pueden encontrar la anomalía? | notebooks `01` a `05` |
| 6. Evaluación unificada | ¿Cuál funciona mejor, medido con la misma vara? | `06_evaluacion_comparativa` |
| 7. Sensibilidad | ¿Dónde dejan de funcionar? | barrido en `06` |
| 8. Límites y comunicación | ¿Qué NO muestra este trabajo? | sección *Limitaciones* de cada notebook y del README |

**Tres ideas del formato que conviene aprender a imitar:**

1. **Separar lo que se observa de lo que es verdad.** En la simulación, las columnas `verdad_*` son la respuesta del examen y ningún método las puede usar. Solo sirven para evaluar. Este es el principio que evita engañarse.
2. **Fijar las reglas de decisión antes de mirar los resultados.** Por ejemplo, el umbral del 5 % de falsas alarmas. Cuando un umbral se cambió después de ver resultados (método 02), quedó escrito.
3. **Terminar cada análisis con sus límites.** No como disculpa, sino como parte del resultado.

### Errores del proceso (también son material de estudio)
Durante el trabajo se cometieron errores que luego se corrigieron. Cada uno enseña algo:

| Error | Qué enseña |
|---|---|
| Evaluar contra una "verdad" mal definida (contaba como fraude a líneas que nunca tuvieron datos con fraude: 8 de 35 en la versión final) | Revisar siempre la definición de la variable de referencia antes de culpar al método |
| Atribuir las falsas alarmas de LOF a la distancia del placebo (método 04). Igualar la distancia **no** las redujo | Una explicación plausible y medible (hay deriva) no es necesariamente **la** causa; probarla puede refutarla |
| Escribir conclusiones antes de ver los números, y que los números las contradijeran (varias veces) | Una explicación plausible no es un resultado; hay que verificarla |
| Una ventaja del método 05 que dependía de un parámetro elegido por el autor | Probar cuánto cambia el resultado si el supuesto cambia |
| Anonimizar con una semilla fija: con el código y los datos públicos se podía reconstruir qué líneas reales recibieron el fraude simulado | Anonimizar no es solo cambiar nombres: hay que pensar cómo podría revertirse (sal secreta, ruido en los valores) |
| Rehacer la simulación cambió casi todos los números y obligó a revisar cada texto con cifras escritas a mano | Los resultados dependen de la realización aleatoria concreta: conviene reportar varias semillas y no escribir cifras en el texto sin verificarlas |

---

## Parte 2 · Los conceptos estadísticos

Ordenados de más básico a más avanzado. Para cada uno: la idea, dónde verlo y un ejercicio.

### Nivel 1 · Simulación, ruido y robustez
- **Simular con semilla fija.** Si fijás la semilla, el azar se repite y el resultado es reproducible (`config.yaml → semilla`).
- **Distribución lognormal.** Los viajes largos son menos frecuentes que los cortos y no hay viajes negativos: una distribución asimétrica a la derecha. `src/simular.py` (`probs_secciones`).
- **Multinomial.** Repartir N viajes entre 5 secciones con ciertas probabilidades; la variación de un mes a otro es solo azar de muestreo.
- **Mediana y MAD en lugar de media y desvío.** Son **robustas**: no se dejan arrastrar por valores atípicos. Se usan en `src/changepoints.py` (`sigma_robusto`) y `src/coherencia.py` (`exceso_altas`).
- **Logaritmos.** Para comparar cambios relativos (+3 %) en vez de absolutos.

**Ejercicio:** cambiá `semilla` en `config.yaml` y volvé a correr `python src/build_sim.py`. ¿Qué cambia y qué no? ¿Por qué la conclusión general debería sostenerse?

### Nivel 2 · Inferencia: separar señal de ruido
- **Error estándar y test t de Welch.** ¿La diferencia entre dos promedios es mayor que lo esperable por azar? `src/microdatos.py` (`test_linea`).
- **p-valor.** La probabilidad de ver algo tan extremo **si no pasara nada**. No es la probabilidad de que no pase nada.
- **Comparaciones múltiples (Bonferroni).** Si hacés 24 tests al 5 %, esperás ~1 falsa alarma solo por azar. Bonferroni exige p < 0,05/24.
- **Umbral por placebo.** Correr el método donde sabés que no hay nada y ver cuánto "detecta". Es una forma empírica de calibrar la tasa de falsas alarmas (`calibrar_beta` en `src/changepoints.py`).

**Ejercicio:** en el notebook 05, cambiá `alfa` en `test_linea` y mirá cómo se mueve el compromiso entre detectar y acusar de más.

### Nivel 3 · Evaluar un detector
- **Matriz de confusión:** verdaderos/falsos positivos y negativos.
- **Recall** (de los que tenían fraude, cuántos encontré) vs **precisión** (de los que marqué, cuántos tenían fraude) vs **tasa de falsas alarmas**.
- **Por qué la precisión puede ser baja aunque el recall sea 100 %:** si hay muchos más inocentes que culpables, incluso un 5 % de falsas alarmas son muchas líneas. Es el problema de la **prevalencia baja**.
- **AUC:** la probabilidad de que una línea con fraude, elegida al azar, tenga un puntaje mayor que una sin fraude. 0,5 = azar, 1 = perfecto. No depende del umbral.
- **Curva de sensibilidad:** cómo cambia el recall al variar la magnitud del efecto.

**Ejercicio:** abrí `06_evaluacion_comparativa`. Con la matriz de confusión del caso base, calculá a mano precisión, recall y tasa de falsas alarmas del método 01. ¿Coinciden con la tabla?

### Nivel 4 · Inferencia causal (el corazón del método 02)
- **Contrafactual:** qué habría pasado sin el cambio. No se observa; se estima.
- **Diferencias en diferencias (DiD):** el cambio del grupo tratado menos el cambio del grupo control. Supuesto clave: **tendencias paralelas**.
- **Event study:** estimar el efecto mes a mes alrededor de la fecha, y mirar que **antes** sea ≈ 0 como chequeo del supuesto.
- **Efectos fijos y errores agrupados:** controlar por características constantes de cada línea y de cada mes; agrupar los errores por empresa porque las decisiones se toman a ese nivel. `src/did_sc.py` (`event_study`).
- **Control sintético:** armar el contrafactual como un promedio ponderado de unidades parecidas. `pesos_sinteticos`.
- **Placebos** en el tiempo y en el espacio: probar el método donde no hay efecto para saber cuánto "efecto" aparece por azar.
- **Contaminación del grupo control:** si las unidades de comparación también están afectadas, el efecto se subestima (por eso el 02 excluye donantes sospechosos).
- **Selección sobre el resultado:** si elegís el grupo tratado mirando quién subió, inflás el efecto. Por eso el DiD necesita una lista de sospechosas definida **por fuera** de los datos de tarifa.

**Ejercicio:** en el notebook 02, la tabla de "pista contaminada" muestra que el efecto estimado cae casi en proporción a la fracción de líneas inocentes. Escribí la fórmula: si una fracción *c* del grupo tratado no tiene efecto, ¿cuál es el efecto promedio estimado en función del verdadero?

### Nivel 5 · Series de tiempo y aprendizaje automático
- **Quiebres estructurales (PELT):** buscar el momento en que cambia el nivel. La **penalización** controla cuántos quiebres acepta; es el mismo compromiso detectar vs acusar de más.
- **No estacionariedad / deriva:** si lo "normal" cambia con el tiempo, un umbral calibrado antes deja de valer. Fue el problema del método 04.
- **Isolation Forest y LOF:** detección de rarezas sin ninguna idea previa del fraude. Miden rareza *global* y *local* respectivamente.
- **Explicabilidad:** un ranking sin explicación sirve poco para revisar (`04_anomalias_ml`, sección 4).

**Ejercicio:** en `04_anomalias_ml`, corré el protocolo "con trampa" y el "emparejado". Explicá con tus palabras por qué el primero daba más falsas alarmas.

---

## Parte 3 · Ruta de estudio sugerida

1. **Semana 1.** Leé `README.md` y `docs/fuentes.md`. Corré los notebooks `00` a `00c` y respondé: ¿qué es verdad conocida y qué es observable en cada columna?
2. **Semana 2.** Método 01. Hacé el ejercicio de la semilla y el del nivel 3.
3. **Semana 3.** Método 02. Es el más importante para inferencia causal. Hacé el ejercicio del nivel 4.
4. **Semana 4.** Métodos 03 y 04. Prestá atención a **por qué fallan**, no solo a que fallen.
5. **Semana 5.** Método 05 y evaluación (`06`). Cambiá `fraude.magnitud` y `micro.ruido_mes_sd` y **predecí el resultado antes de correr**. Anotá dónde te equivocaste.
6. **Después.** Tomá un método y reescribilo sin mirar el código. Es la prueba de que lo entendiste.

**Un hábito que sirve más que cualquier lectura:** antes de correr una celda, escribí qué esperás ver. Cuando te equivocás aprendés más que cuando acertás.

## Lecturas recomendadas (verificá disponibilidad y ediciones)
- *Causal Inference: The Mixtape*, Scott Cunningham (DiD y control sintético; hay versión online).
- *Mostly Harmless Econometrics*, Angrist y Pischke (la lógica de la inferencia causal aplicada).
- *An Introduction to Statistical Learning*, James, Witten, Hastie y Tibshirani (clasificación, evaluación, Isolation Forest/LOF en contexto).
- Abadie, Diamond y Hainmueller (2010), artículo original del control sintético, *Journal of the American Statistical Association*.
