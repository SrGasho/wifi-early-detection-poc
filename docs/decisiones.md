# Registro de decisiones (Gate D)

Cada decisión indica su valor, la evidencia que la sustenta, su estado y el commit en que se congeló. Después de la etiqueta `gate-d` nada de esta tabla cambia sin crear un experimento nuevo.

Estados:
- **aceptado (fecha)**: decidido por el autor. Puede tener una condición de verificación pendiente, que se indica en la fila.
- **pendiente**: sin decidir.
- **resuelto**: hecho verificable, sin decisión de diseño.

Razonamiento completo de las decisiones de este registro: `docs/reporte-gate-d.md`.

| Decisión | Valor | Evidencia | Estado | Commit |
|---|---|---|---|---|
| Objetivo del modelo | binario: normal frente a ataque de desconexión (Deauth y Disas de AWID3); análisis por tipo como reporte adicional | plan, 14.1; artículo III-A | aceptado (2026-11-10) | |
| Alcance del ataque | desautenticación (Deauth) y disociación (Disas) del conjunto AWID3, sin separar difusión y dirigido. La proporción de difusión se reporta como análisis complementario. | `datos-awid3.md` P9; `analisis_cruce.txt` | aceptado (2026-11-10). Cambio pendiente en artículo y anteproyecto | |
| Caso de partición principal | **Caso C** (leave-one-attack-out), en ambos sentidos. Reemplaza a Caso B tras la verificación con datos (ver fila siguiente). El artículo (III-D) lo contempla como "evaluación alternativa o principal". Da clasificación y latencia medible (el ataque de prueba llega completo). | `split_data` 2026-11-10; artículo III-D | aceptado (2026-11-10) | |
| Caso B (descartado como partición principal) | **No viable como partición de 3 vías** con la geometría de AWID3: el ataque está en un bloque al final de cada captura y todo el tráfico normal antes, así que los cortes 60/20/20 por cuantil de tramas objetivo dejan val y test 100 % ataque, sin ventanas normales, y `split_data` aborta (regla de presencia de ambas clases). Se documenta como hallazgo; no se usa. | `split_data` preview 2026-11-10 (val=20, test=51 ventanas, todas de ataque) | aceptado (2026-11-10) | |
| Proporciones y ubicación de cortes | Caso C: entrena+valida con una captura (val = tramo final, `val_fraction=0.2`), prueba con la otra captura completa | `reporte-gate-d.md` 2.4 | aceptado (2026-11-10). Verificar tamaños reales con `split_data` | |
| `S` principal | 1.0 s | resolución del dato (1 s) | aceptado (2026-11-10) | |
| `W` principal | 5.0 s | `reporte-gate-d.md` 2.3 | aceptado (2026-11-10). **Condición**: al menos una trama de desconexión en ≥ 99 % de las ventanas de ataque de entrenamiento | |
| `W` de sensibilidad | 3.0 s y 10.0 s; experimentos independientes, solo en validación | artículo III-C, V | aceptado (2026-11-10) | |
| `purge_seconds` | 10.0 s (≥ mayor `W`, R7) | plan, 8.4 | aceptado (2026-11-10) | |
| Método y parámetros de `T` | `fixed`, `T_seconds = 2.0`. La brecha máxima entre tramas objetivo en todo el dataset es 1.0 s, así que cualquier subconjunto la cumple; no depende de datos de prueba. | `analisis_linea.txt`; `reporte-gate-d.md` 2.5 | aceptado (2026-11-10). Cambiado en `exp_rf.yaml` y experimentos de Caso C de `percentile_multiple` a `fixed` | |
| `max_gap_seconds` | 1.0 s (= `S`) | plan, 8.7 | aceptado (2026-11-10) | |
| Códigos de motivo con columna propia | **7 y 1** (`rc_7`, `rc_1`, `rc_other`). Código 7 casi exclusivo del ataque. | `analisis_cruce.txt`; `datos-awid3.md` P14 | aceptado (2026-11-10). Experimento de sensibilidad sin `rc_*` usa el perfil `no_rc` | |
| Códigos fuera del catálogo 802.11 (p. ej. 58499) | se mantienen en `rc_other`; no se anulan en esta tanda | `datos-awid3.md`; `analisis_cruce.txt` | aceptado (2026-11-10) | |
| Exclusiones del Caso C (`loao_exclude`) | `n_deauth`, `n_disas`, `rc_7`, `rc_1`, `frac_broadcast_dst_disconn`, `n_unique_src_disconn`, `n_unique_dst_disconn` | artículo III-C; `datos-awid3.md` P14; verificación V2 | aceptado (2026-11-10). V2 confirmó que frac_broadcast y n_unique_* difieren por clase; añadidos. | |
| Tratamiento de `ts` (fuga por timestamp) | **truncar `ts` a segundo entero solo para `iat_disconn_*`**, en `compute_window_features` antes de `np.diff`. Las ventanas usan `ts` original. | `analisis_timestamp.txt`; `reporte-gate-d.md` 2.2 | aceptado (2026-11-10). **Implementado**. Condición: tras ejecutar, revisar distribución de `iat_*` por clase | |
| Características retiradas por falta de campos | ninguna por campo ausente. `mfpr` no existe en AWID3 CSV; `mfpc` tiene ~99.6 % de nulos y no entra a features | `datos-awid3.md` P7, P10, P13 | resuelto | |
| Corrección `reason_code` a `Int32` | Int16 desbordaba (valores hasta 65535); ahora Int32 | `src/preprocessing.py` | resuelto (PR #1) | |
| Tratamiento de tramas `other` | no aplica: 0 tramas `other` | `preprocessing_summary.json` | resuelto | |
| `tau_high`, `cooldown_seconds` | 0.9 y 30 s. Supuestos de simulación; no afectan métricas ni se optimizan. | plan, 8.9 | aceptado (2026-11-10) | |
| Imputación | constante −1, ajustada con entrenamiento | plan, 8.3 | aceptado (plan) | |
| Criterio de umbral | máximo F1 en validación; empate: menor umbral | plan, 8.5 y 8.6 | aceptado (plan) | |

## Limitaciones declaradas

- La partición es consciente de etiquetas (organiza capturas, verifica clases, ubica cortes). Las etiquetas no entran al modelo, pero esto limita la interpretación de la generalización.
- **Caso B no es una partición de 3 vías viable con esta geometría** (ataque en bloque al final de cada captura). Se usa Caso C como principal.
- Caso C mide transferencia entre ataques relacionados (deauth ↔ disas), no generalización frente a ataques de otra naturaleza.
- El código de motivo 7 casi solo aparece en ataques. Los resultados con `rc_*` pueden sobreestimar la detección; el experimento de sensibilidad sin `rc_*` (perfil `no_rc`) lo mide.
- AWID3 (802.1X/EAP, PMF activo según su documentación) difiere del escenario de la pequeña empresa.
- Banda y canal fijos: **5 GHz, canal 36** (`radiotap.channel.freq=5180`) en ambas capturas; sin diversidad de canal.
- Sin validación en hardware físico; la mitigación es simulada.
- La latencia está acotada por `S`.
- Compatibilidad PMF desconocida cuando `mfpc` es nulo o no existe.
