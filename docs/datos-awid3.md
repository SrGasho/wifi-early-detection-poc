# AWID3: respuestas de la Fase 1

Cada respuesta cita su evidencia: `results/inspection/report.md`, `inventory.json`, `discover.json`, `episodes_exploratory.json` o una figura del notebook. Mientras una respuesta esté pendiente, la decisión que dependa de ella no puede congelarse en Gate D.

| # | Pregunta | Respuesta | Evidencia | Decisión afectada |
|---|---|---|---|---|
| 1 | ¿Cuántas capturas independientes existen por ataque? | pendiente | | caso A, B o C |
| 2 | ¿Los eventos aparecen en tramos contiguos? | pendiente | | ubicación de cortes |
| 3 | ¿Existen marcas temporales utilizables? | pendiente | | ventanas y latencia |
| 4 | ¿Los clientes se reasocian después del evento? | pendiente | | referencia de impacto |
| 5 | ¿Existe un efecto observable que pueda utilizarse como referencia? | pendiente | | uso del término "anticipación" |
| 6 | ¿Qué proporción de tramas tiene protección activada? | pendiente | | `frac_protected_mgmt` |
| 7 | ¿Están disponibles `wlan.seq`, potencia de señal y códigos de motivo? | pendiente | | `seq_jump_max`, `signal_std_disconn`, `rc_*` |
| 8 | ¿Existen eventos legítimos de desautenticación o disociación? | pendiente | | dificultad real del problema |
| 9 | ¿Las etiquetas separan difusión, ataques dirigidos y disociación? | pendiente | | alcance de ataques dirigidos |
| 10 | ¿Qué campos son comunes a todas las capturas? | pendiente | | lista `allowed` |
| 11 | ¿Cada ataque es una ráfaga continua o varias separadas por silencios? | pendiente | | episodios, `T`, caso de partición |
| 12 | ¿Cuál es la banda y el canal de las capturas? | pendiente | | limitación de dominio |
| 13 | ¿Están disponibles `mfpc` y `mfpr` en asociación o reasociación? | pendiente | | mitigación simulada |
| 14 | ¿Qué características podrían actuar como sustitutos del subtipo? | pendiente | | `loao_exclude` |

## Mapeo real de columnas

Completar al terminar el descubrimiento y copiar a `configs/data.yaml`.

| Nombre interno | Columna en AWID3 | Confirmada |
|---|---|---|
| `ts` | | |
| `fc_type` / `fc_subtype` o `fc_type_subtype` | | |
| `src`, `dst`, `bssid` | | |
| `reason_code` | | |
| `seq` | | |
| `signal_dbm` | | |
| `protected` | | |
| `mfpc`, `mfpr` | | |
| `label` | | |

## `T` provisional (solo exploración)

- Valor: pendiente
- Cómo se eligió (percentiles y mayores silencios de `episodes_exploratory.json`): pendiente
