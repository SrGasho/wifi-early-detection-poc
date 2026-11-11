# Registro de decisiones (Gate D)

Cada decisión indica su valor, la evidencia que la sustenta y el commit en que se congeló. Después de la etiqueta `gate-d` nada de esta tabla cambia sin crear un experimento nuevo.

| Decisión | Valor | Evidencia | Commit |
|---|---|---|---|
| Objetivo del modelo | binario: normal frente a ataque de desconexión; análisis por tipo como reporte adicional | plan, sección 14.1 | |
| Caso de partición | propuesto: **Caso B**. La latencia se reporta como descriptiva sobre entrenamiento y validación, porque con una ráfaga única no es medible en prueba. No se usa para elegir configuración (R6). | `docs/datos-awid3.md` P1, P2, P11; `analisis_linea.txt` | |
| Proporciones y ubicación de cortes | pendiente | `episodes_exploratory.json` | |
| `S` principal | pendiente | resolución deseada y costo (plan, 8.2.1) | |
| `W` principal | pendiente | estadísticas de entrenamiento (plan, 8.2.1) | |
| `W` de sensibilidad | pendiente (lista; un experimento por valor) | declarada antes de entrenar | |
| `purge_seconds` | pendiente (≥ mayor `W`) | | |
| Método y parámetros de `T` | pendiente (`fixed` o `percentile_multiple`) | intervalos de entrenamiento | |
| `max_gap_seconds` | pendiente (≥ `S`) | | |
| Códigos de motivo con columna propia | propuesto: **7 y 1** (rc_7, rc_1, rc_other); código 7 casi exclusivo del ataque | `analisis_cruce.txt`; P14 | |
| Exclusiones del Caso C | propuesto: `n_deauth`, `n_disas`, `rc_7`, `rc_1` (sustitutos del subtipo) | `analisis_cruce.txt`; P14 | |
| Características retiradas por falta de campos | propuesto: ninguna por campo ausente; `mfpr` no existe (no estaba en features) | P7, P10, P13 | |
| Tratamiento de `ts` (fuga por timestamp) | propuesto: **truncar `ts` a segundo entero en `feature_engineering`, solo para `iat_disconn_*`**. Condiciones: (1) confirmar que ninguna otra feature usa la parte fraccionaria de `ts` (las ventanas `[t_end−W, t_end)` dependen de `ts`, hay que comprobar que el efecto de la fracción en el conteo es despreciable); (2) tras truncar, revisar la distribución de `iat_disconn_*` por clase; si queda casi todo en 0, la feature no aporta. | `analisis_timestamp.txt`; P3 | |
| Corrección `reason_code` a Int32 | **aplicado**: Int16 desbordaba (65535 > 32767, p. ej. 32769 → −32767); ahora Int32, 0 negativos | `src/preprocessing.py`; verificación directa | |
| Tratamiento de tramas con etiqueta ajena (`other`) | **cerrado: no aplica** (0 tramas `other`; `attack_type` solo normal + deauth/disas) | `preprocessing_summary.json` | |
| Imputación | constante −1, ajustada con entrenamiento | plan, 8.3 | |
| Criterio de umbral | máximo F1 en validación; empate: menor umbral | plan, 8.5 y 8.6 | |
| `tau_high`, `cooldown_seconds` | pendiente | no afectan métricas | |

## Limitaciones declaradas

- La partición es consciente de etiquetas (organiza capturas, verifica clases, ubica cortes). Las etiquetas no entran al modelo, pero esto limita la interpretación de la generalización.
- AWID3 (802.1X/EAP, PMF activo) difiere del escenario de la pequeña empresa.
- Banda y canal fijos: **5 GHz, canal 36** (`radiotap.channel.freq=5180`) en ambas capturas; sin diversidad de canal.
- Sin validación en hardware físico; la mitigación es simulada.
- La latencia está acotada por `S`.
- El Caso C mide transferencia entre ataques relacionados, no generalización a ataques de otra naturaleza.
- Compatibilidad PMF desconocida cuando `mfpc` es nulo o no existe.
