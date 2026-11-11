# Reporte de decisiones de Gate D

Fecha: 10 de noviembre de 2026.
Estado: implementado en la rama `gate-d`. Las decisiones se congelan al mergear con la etiqueta `gate-d`.

Este reporte documenta el razonamiento de cada decisión de `docs/decisiones.md`, **incluyendo las alternativas
consideradas y por qué se descartaron**, para que la revisión tenga trazabilidad completa de los hechos.

## 1. Resumen

| Tema | Decisión | Estado |
|---|---|---|
| Caso de partición principal | Caso C (leave-one-attack-out), ambos sentidos | Implementado |
| Caso B | Descartado como partición de 3 vías (ver 2.1) | Documentado |
| Tratamiento de `ts` | Truncar a segundo entero solo en `iat_disconn_*` | Implementado |
| Ventana `S` / `W` | 1.0 s / 5.0 s | Implementado |
| Ventanas de sensibilidad | 3 s y 10 s, solo validación | Implementado |
| `purge_seconds` | 10.0 s | Implementado |
| `T` | fijo, 2.0 s | Implementado |
| `max_gap_seconds` | 1.0 s | Implementado |
| Códigos de motivo | 7 y 1 (`rc_7`, `rc_1`, `rc_other`) | Implementado |
| `loao_exclude` | `n_deauth`, `n_disas`, `rc_7`, `rc_1` | Implementado |
| Perfil sin `rc_*` | perfil `no_rc` (sensibilidad) | Implementado |
| `tau_high`, `cooldown_seconds` | 0.9 y 30 s | Implementado |

## 2. Decisiones

### 2.1 Caso de partición — la decisión con más iteración

**Contexto.** La geometría real de AWID3 (verificada con datos, 2026-11-10): en cada captura el tráfico
normal está al inicio (~420 s) y el ataque es un bloque al final (~180 s). Hay **una sola frontera
normal→ataque por captura**. El código `split_data` exige que cada conjunto (train/val/test) tenga a la
vez ventanas normales y de ataque.

**Alternativas consideradas:**

1. **Caso B, cortes 60/20/20 por cuantil de tramas objetivo** (diseño original).
   Resultado real: train tiene ambas clases, pero val (20 ventanas) y test (51) quedan 100 % ataque,
   porque los cortes caen dentro de la ráfaga final. `split_data` aborta. **Descartada.**

2. **Caso B, cortes por fracción de tiempo de captura.**
   El último 20 % temporal cae dentro del ataque (que es el último tercio). Mismo problema. **Descartada.**

3. **Caso C con val = tramo final del ataque** (diseño original de `case_c`).
   val queda 100 % ataque (el final del ataque no tiene normal). `split_data` aborta en val. **Descartada.**

4. **Caso C con val = último val_fraction del tiempo de captura.**
   Cae dentro del ataque. **Descartada.**

5. **Caso C, Opción D (elegida).** train = la captura de entrenamiento completa menos la franja de
   validación; val = franja que cruza la frontera normal→ataque de esa captura; test = la otra captura
   completa. Como hay una sola frontera por captura, train se parte en **dos unidades** (normal temprano
   + ataque tardío) a los lados de val, con purga. Agregado, train tiene ambas clases; val tiene ambas
   (cruza la frontera); test tiene ambas (captura completa). Verificado con datos:
   train 503 ventanas, val 66, test 600, los tres con normal y ataque.

**Por qué la Opción D y no relajar la regla de clases:** un conjunto de validación de una sola clase no
permite elegir umbral por F1 (no hay negativos o no hay positivos). Relajar la regla produciría métricas
sin sentido estadístico. La Opción D mantiene la regla intacta y es coherente con el artículo (III-D:
"leave-one-attack-out… el ataque de prueba deberá llegar completo").

**Consecuencia positiva:** en Caso C, el conjunto de prueba conserva el inicio del ataque, así que la
**latencia es medible en prueba** (`n_start_complete=1` en test), cosa que Caso B no permitía.

### 2.2 Tratamiento de `ts` (fuga por formato)

Verificado en `feature_engineering.py`: `ts` se usa en (a) la rejilla de ventanas (`window_bounds`,
`grid_indices`) vía `g0` + múltiplos de `S` — solo depende de la fracción en el offset `g0`, no separa
clases; (b) la pertenencia a ventana (`searchsorted`) — la fracción solo mueve tramas entre ventanas
contiguas, efecto despreciable en conteos de cientos/miles; (c) `iat_disconn_*` (`np.diff(ts)`) — **único**
punto donde la fracción entra al valor de la feature.

Decisión: truncar `ts` a segundo entero **solo** en el cálculo de `iat_disconn_*` (`np.diff(np.floor(ts_d))`),
dejando la rejilla con `ts` original. Condición de verificación pendiente: revisar la distribución de
`iat_*` por clase tras truncar; si queda casi todo en 0, la feature no aporta y se documenta.

### 2.3 Ventanas y rejilla

`S = 1.0 s`: la resolución del dato es 1 s; un `S` menor agrega ventanas sin precisión real.
`W = 5.0 s`: cubre suficientes tramas de desconexión. Condición: ≥ 99 % de las ventanas de ataque de
entrenamiento con al menos una trama de desconexión (a verificar con datos).
`W` de sensibilidad 3 s y 10 s: experimentos independientes, solo validación.

### 2.4 Partición (parámetros)

`purge_seconds = 10.0` (≥ mayor W de sensibilidad, R7). `val_fraction = 0.2` en Caso C.
Tamaños reales verificados (deauth→disas): train 503, val 66, test 600 ventanas.

### 2.5 Episodios

`T` fijo 2.0 s: la brecha máxima entre tramas objetivo es 1.0 s (`analisis_linea.txt`), así que
`percentile_multiple` daría un `T` degenerado. `max_gap_seconds = 1.0` (= S).

### 2.6 Códigos de motivo

`rc_7`, `rc_1`, `rc_other`. Riesgo: el código 7 es casi exclusivo del ataque, así que el modelo podría
apoyarse en él como atajo. Mitigación: experimento de sensibilidad con el perfil `no_rc` (excluye todas
las `rc_*`), solo validación, para medir cuánto aporta el código de motivo.

### 2.7 Exclusiones del Caso C (`loao_exclude`)

`n_deauth`, `n_disas`, `rc_7`, `rc_1`. Condición: revisar `frac_broadcast_dst_disconn` y `n_unique_*_disconn`
por clase; excluir si difieren de forma clara entre deauth y disas.

### 2.8 Mitigación

`tau_high = 0.9`, `cooldown_seconds = 30`. Supuestos de simulación; no afectan métricas ni se optimizan.

## 3. Verificaciones con datos (estado)

| Verificación | Estado |
|---|---|
| Partición Caso C con ambas clases en train/val/test | hecho: 503/66/600 ventanas, todas con ambas clases |
| Latencia medible en test (Caso C) | hecho: `n_start_complete=1` en test |
| V1: ≥ 99 % de ventanas de ataque de train con trama de desconexión (W=5) | **hecho: 100 %** (130 ventanas). W=5 confirmado. |
| V2: `frac_broadcast` y `n_unique_*` por clase (loao_exclude) | **hecho, solo con capturas de entrenamiento** (no prueba, R6): difieren claramente en ambos sentidos (deauth→disas train: n_unique_src 2.64 vs 0.01; disas→deauth train: 4.92 vs 0.03). Se añaden a `loao_exclude`. |
| V3: distribución de `iat_*` por clase tras truncar | **hecho**: `iat_min` queda 0 en ambas clases; además en ventanas normales `iat_*` es nulo→imputado a −1, lo que señala la clase (fuga por imputación). Por eso `iat_disconn_*` se **retiran** de `allowed`. |

## 4. Riesgos residuales

- Caso C mide transferencia deauth↔disas, no generalización a ataques de otra naturaleza.
- `rc_7` casi exclusivo del ataque: F1 en validación puede ser ~1.0 por atajo; el experimento `no_rc` lo mide.
- Una sola captura por tipo de ataque: la validación es corta y el umbral puede ser inestable.
- AWID3 no representa la red de la empresa de referencia.

## 5. Nota de proceso: ejecución de prueba descartada

Durante el desarrollo de Gate D hubo una primera ejecución `--final` (exp_id `…2055`/`…2124`) **antes** de
ampliar `loao_exclude` (commit `f3bcfb7`). Esos resultados se descartaron y los experimentos se regeneraron
(exp_id `…2129`) con el conjunto de características definitivo. Para que la integridad de R6 sea completa
—que ningún `--final` preceda a la selección de características— el pipeline se **regenera por entero desde
el commit limpio etiquetado `gate-d`**: splits, ventanas, modelos y prueba. Las exclusiones de `loao`
(`frac_broadcast`, `n_unique_*`) se justifican **solo con las capturas de entrenamiento** (sección 2.7 / V2),
sin mirar la captura de prueba.
