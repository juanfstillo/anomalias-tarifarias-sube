# Borrador: pedido de acceso a la información pública (Ley 27.275)

> **Es un borrador.** Antes de enviarlo hay que: completar los datos entre `[corchetes]`, verificar el organismo competente vigente y
> los canales de presentación, y confirmar los artículos citados contra el texto vigente de la ley. No es asesoramiento legal.

## Para qué sirve este pedido
El análisis público de este proyecto no puede medir secciones tarifarias ni montos cobrados, porque esos datos **no están publicados**
(ver `docs/fuentes.md`). El proyecto trabaja con una capa simulada. Este pedido apunta a la información que permitiría
hacer el análisis con datos reales, **sin pedir ningún dato personal**: solo agregados por línea y mes.

## Destinatarios posibles
- Secretaría de Transporte de la Nación (o el organismo que hoy ejerza esa competencia): `[verificar denominación vigente]`.
- Nación Servicios S.A., en su carácter de administradora del sistema SUBE: `[verificar]`.
- Comisión Nacional de Regulación del Transporte (CNRT), para el punto 4.

Conviene presentar pedidos separados, cada uno con los puntos que le corresponden.

## Texto del pedido

**A:** `[Organismo]` — Responsable de Acceso a la Información Pública
**De:** `[Nombre y apellido]`, DNI `[número]`, correo `[correo]`, domicilio `[domicilio]`
**Fecha:** `[fecha]`

En ejercicio del derecho de acceso a la información pública reconocido por la Ley 27.275, solicito la siguiente información,
en formato digital abierto y reutilizable (CSV o similar):

1. **Recaudación por línea y mes.** Para cada línea de colectivo de la Región Metropolitana de Buenos Aires (RMBA), desde
   enero de 2023 hasta el último mes disponible: monto total cobrado a los pasajeros por validaciones, y cantidad de validaciones (usos).
2. **Distribución de validaciones por sección tarifaria.** Para cada línea y mes del mismo período: cantidad de validaciones cobradas en cada
   sección tarifaria (o, si no se registra por sección, la tarifa media cobrada por viaje).
3. **Criterio de reparto de compensaciones.** Normativa, fórmula y variables utilizadas para distribuir entre empresas las
   compensaciones o subsidios tarifarios, incluyendo si interviene la recaudación, la distancia media abonada o las secciones
   registradas, y los montos asignados por empresa y mes en el mismo período.
4. **Reclamos de usuarios** *(a la CNRT)*. Cantidad de reclamos por cobros indebidos o por asignación incorrecta de secciones tarifarias,
   desagregados por línea y mes, y su estado de resolución, entre mayo de 2025 y el último mes disponible.
5. **Controles existentes.** Descripción de los controles que el organismo aplica para verificar la coherencia entre la sección
   cobrada y el recorrido efectivo, y los resultados de esos controles en el mismo período.

**No se solicitan datos personales** de usuarios, ni identificadores de tarjetas, ni información sobre personas determinadas.
Si algún dato estuviera alcanzado por una excepción legal, se solicita su entrega parcial, tachando únicamente la parte protegida,
e indicando la excepción invocada y su fundamento.

Se solicita que la información se entregue por medios electrónicos a la dirección de correo indicada.

`[Firma]`

## Pedido adicional, más sensible (microdatos)

El método 05 (`notebooks/05_inferencia_bajada.ipynb`) es el más potente, pero necesita datos de validaciones individuales. Son datos de movilidad personal, aunque anonimizados, así que conviene pedirlos con cuidado:

6. **Muestra acotada de validaciones.** Para un conjunto de líneas y de días a definir con el organismo: identificador de tarjeta **enmascarado e irreversible**, hora redondeada, línea, posición geográfica de la validación y sección o monto cobrado.
   Alternativa que evita entregar microdatos: que **el propio organismo ejecute el análisis** (comparar sección cobrada contra distancia inferida) y entregue **solo resultados agregados por línea y mes**.

`[Evaluar con asesoramiento legal la protección de datos personales (Ley 25.326) antes de presentar este punto.]`

## Notas de uso
- **Sin justificación.** La ley, en su régimen general, no exige motivar el pedido; no hace falta explicar para qué se usará.
  Conviene no hacerlo en el texto formal. `[verificar artículo]`
- **Plazos.** La ley fija un plazo de respuesta de 15 días hábiles, prorrogable por otros 15 con aviso fundado. `[verificar artículo]`
- **Si no responden o niegan.** Existe la posibilidad de reclamar ante la Agencia de Acceso a la Información Pública y, luego,
  la vía judicial. `[verificar procedimiento y plazos vigentes]`
- **Canal.** Muchos organismos reciben pedidos por la plataforma de trámites a distancia o por mesa de entrada.
  `[verificar canal para cada organismo]`
- **Qué hacer con la respuesta.** Si llega información, el pipeline de este proyecto está pensado para reemplazar la capa simulada
  (`src/simular.py`) por los datos reales; el resto (métodos 01 a 04) se reutiliza. Los resultados se seguirían presentando como
  **anomalías a revisar**, nunca como prueba de fraude, y sin acusar a ninguna empresa.
