# AWID3: respuestas de la Fase 1

Cada respuesta cita su evidencia: `results/inspection/report.md`, `inventory.json`, `discover.json`, `episodes_exploratory.json` o una figura del notebook. Mientras una respuesta esté pendiente, la decisión que dependa de ella no puede congelarse en Gate D.

| # | Pregunta | Respuesta | Evidencia | Decisión afectada |
|---|---|---|---|---|
| 1 | ¿Cuántas capturas independientes existen por ataque? | Deauth: 33 archivos CSV (`cap_a`); Disas: 41 archivos CSV (`cap_b`). Cada ataque está en su carpeta. | `discover.json`; `report.md` (cap_a/cap_b: n.º de archivos) | caso A, B o C |
| 2 | ¿Los eventos aparecen en tramos contiguos? | Sí. Con `T=2 s` provisional cada captura produce **1 solo episodio**; el mayor silencio entre tramas objetivo es 1 s. El ataque es un tramo contiguo. | `episodes_exploratory.json` (`largest_gaps`=[1.0...], `n_episodes`=1) | ubicación de cortes |
| 3 | ¿Existen marcas temporales utilizables? | Sí, con un matiz. `ts` (`frame.time_epoch`) 0 % nulo, rango ~602 s por captura, pocas inversiones (4–5 en fronteras de archivo). **Las tramas de ataque traen `ts` redondeado a segundos enteros** (parte decimal = 0); las normales tienen sub-segundo. | `report.md` (ts 0 % nulo); verificación directa del CSV crudo | ventanas y latencia |
| 4 | ¿Los clientes se reasocian después del evento? | pendiente: requiere seguir subtipos de (re)asociación (subtipo 0/1/2) tras cada episodio. No contestable solo con el inventario. | | referencia de impacto |
| 5 | ¿Existe un efecto observable que pueda utilizarse como referencia? | pendiente: depende de P4. | | uso del término "anticipación" |
| 6 | ¿Qué proporción de tramas tiene protección activada? | `cap_a`: 542 003 / 1 626 469 = **33.3 %** con `protected=1`. `cap_b`: 720 177 / 2 013 716 = **35.8 %**. | `report.md` (tabla "Protección activa") | `frac_protected_mgmt` |
| 7 | ¿Están disponibles `wlan.seq`, potencia de señal y códigos de motivo? | Sí. `seq` presente (~63–66 % nulo, poblado en gestión); `signal_dbm` (`radiotap.dbm_antsignal`) **0 % nulo**; `reason_code` presente en tramas de desconexión (dominan 7 y 1). | `report.md` (fracción nula; reason codes) | `seq_jump_max`, `signal_std_disconn`, `rc_*` |
| 8 | ¿Existen eventos legítimos de desautenticación o disociación? | **Sí, masivamente.** `cap_a`: subtipo 12 (deauth) → 302 887 `Normal` vs 38 893 `Deauth`. `cap_b`: subtipo 12 → 319 917 `Normal`; subtipo 10 (disas) → 68 994 `Disas` vs 136 `Normal`. El problema NO es trivial: la mayoría de tramas deauth son legítimas; hay que detectar el patrón de ráfaga, no la trama suelta. | `report.md` (tabla "Subtipo desconexión \| Etiqueta") | dificultad real del problema |
| 9 | ¿Las etiquetas separan difusión, ataques dirigidos y disociación? | Parcial. La etiqueta es por tipo (`Normal`/`Deauth`/`Disas`), no distingue difusión vs dirigido; eso se infiere de `is_broadcast_dst` + subtipo. El cruce subtipo×etiqueta separa deauth (12) de disas (10). | `report.md` (tabla de subtipos y cruce) | alcance de ataques dirigidos |
| 10 | ¿Qué campos son comunes a todas las capturas? | Todos. Las **745 CSV comparten exactamente las mismas 254 columnas**. Columnas mapeadas ausentes: ninguna en cap_a ni cap_b. | `discover.json`; `report.md` ("Columnas mapeadas ausentes: ninguna") | lista `allowed` |
| 11 | ¿Cada ataque es una ráfaga continua o varias separadas por silencios? | **Una ráfaga continua** (dentro de la resolución de 1 s): 1 episodio por captura, IAT mediana 0 s, máximo 1 s. | `episodes_exploratory.json` | episodios, `T`, caso de partición |
| 12 | ¿Cuál es la banda y el canal de las capturas? | pendiente: las columnas `radiotap.channel.freq` / `wlan_radio.channel` / `wlan_radio.frequency` existen pero **no están mapeadas** en `data.yaml`; no se resumen en el inventario. Requiere lectura puntual o mapearlas. | `discover.json` (columnas presentes) | limitación de dominio |
| 13 | ¿Están disponibles `mfpc` y `mfpr` en asociación o reasociación? | `mfpc` (`wlan.rsn.capabilities.mfpc`) **existe** pero ~99.6 % nulo (solo en tramas RSN de asociación). **`mfpr` NO existe** en AWID3 CSV. | `discover.json`; `report.md` (mfpc nulo); mapeo | mitigación simulada |
| 14 | ¿Qué características podrían actuar como sustitutos del subtipo? | `reason_code` es el candidato principal: en desconexiones dominan los códigos 7 (previous auth no longer valid) y 1 (unspecified). También `frac_broadcast_dst`, `n_unique_src/dst` y la tasa de tramas de desconexión. | `report.md` (reason codes en desconexiones) | `loao_exclude` |

## Mapeo real de columnas

Confirmado en la Fase 1 y copiado a `configs/data.yaml`.

| Nombre interno | Columna en AWID3 | Confirmada |
|---|---|---|
| `ts` | `frame.time_epoch` | sí (0 % nulo) |
| `fc_type` / `fc_subtype` | `wlan.fc.type` / `wlan.fc.subtype` (separados, no `fc_type_subtype`) | sí (0 % nulo) |
| `src`, `dst`, `bssid` | `wlan.sa`, `wlan.da`, `wlan.bssid` | sí |
| `reason_code` | `wlan.fixed.reason_code` | sí (presente en desconexiones) |
| `seq` | `wlan.seq` | sí (poblado en gestión) |
| `signal_dbm` | `radiotap.dbm_antsignal` | sí (0 % nulo) |
| `protected` | `wlan.fc.protected` | sí (0 % nulo) |
| `mfpc` | `wlan.rsn.capabilities.mfpc` | sí (~99.6 % nulo) |
| `mfpr` | — (no existe en AWID3 CSV) | ausente; omitida |
| `label` | `Label` | sí (valores: Normal / Deauth / Disas) |

## `T` provisional (solo exploración)

- Valor: **2.0 s** (provisional, no se usa para métricas).
- Cómo se eligió: punto de partida tentativo para separar ráfagas. El resumen
  `episodes_exploratory.json` muestra que es holgado: con `T=2 s` hay 1 episodio por
  captura y el mayor silencio entre tramas objetivo es 1 s. El `T` definitivo se
  calculará en modo `definitive` solo con el conjunto de entrenamiento (Gate D).

## Hallazgo relevante: resolución temporal de las tramas de ataque

El dato crudo `frame.time_epoch` tiene resolución sub-milisegundo en tramas normales
(ej. `1608306178.4826`, `.58501`), pero **las tramas de ataque etiquetadas `Deauth`/`Disas`
traen el timestamp redondeado a segundos enteros** (parte decimal = 0). Esto limita la
granularidad de las ventanas y de la latencia de alerta a 1 s para los episodios de ataque,
y debe tenerse en cuenta al elegir `W` y `S` (R3/R4).
