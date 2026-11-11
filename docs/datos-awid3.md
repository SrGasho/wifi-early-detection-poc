# AWID3: respuestas de la Fase 1

Cada respuesta cita su evidencia: `results/inspection/report.md`, `inventory.json`, `discover.json`, `episodes_exploratory.json` o una figura del notebook. Mientras una respuesta esté pendiente, la decisión que dependa de ella no puede congelarse en Gate D.

| # | Pregunta | Respuesta | Evidencia | Decisión afectada |
|---|---|---|---|---|
| 1 | ¿Cuántas capturas independientes existen por ataque? | Deauth: 33 archivos CSV (`cap_a`); Disas: 41 archivos CSV (`cap_b`). Cada ataque está en su carpeta. | `discover.json`; `report.md` (cap_a/cap_b: n.º de archivos) | caso A, B o C |
| 2 | ¿Los eventos aparecen en tramos contiguos? | Sí, **demostrado con la línea de tiempo**. El ataque dura ~180 s (no toda la captura) y ocupa el 100 % de los bloques de 10 s (cap_a 18/18, cap_b 19/19), con 0 bloques vacíos. Mediana ~2200–2460 tramas objetivo por bloque. | `analisis_linea.txt`; `episodes_exploratory.json` | ubicación de cortes |
| 3 | ¿Existen marcas temporales utilizables? | Sí, pero con **FUGA confirmada**. `ts` 0 % nulo. **Las tramas de ataque tienen `ts` entero en el 100 %**; las Normal del mismo subtipo 12 solo 0.49–0.59. La parte fraccionaria separa la clase → `iat_disconn_*` (derivadas de `ts`) pueden filtrar la etiqueta por un artefacto de formato. Mitigación en Gate D: truncar `ts` a segundo entero antes de las features, o retirar `iat_disconn_std/min/mean`. | `analisis_timestamp.txt`; `report.md` | ventanas y latencia; features retiradas |
| 4 | ¿Los clientes se reasocian después del evento? | Indicio, no concluyente (1 captura, referencia no independiente). En cap_b las solicitudes de (re)asociación caen de 358 (40 clientes) antes a 18 (4 clientes) tras el episodio; en cap_a el ataque ocupa toda la captura y no hay "después" limpio. | `analisis_reasociacion.txt` | referencia de impacto |
| 5 | ¿Existe un efecto observable que pueda utilizarse como referencia? | Parcial: la caída de reasociaciones tras el ataque (P4) es el único efecto medible, pero con 1 captura no es tráfico de referencia independiente. Evitar el término "anticipación". | `analisis_reasociacion.txt` | uso del término "anticipación" |
| 6 | ¿Qué proporción de tramas tiene protección activada? | `cap_a`: 542 003 / 1 626 469 = **33.3 %** con `protected=1`. `cap_b`: 720 177 / 2 013 716 = **35.8 %**. | `report.md` (tabla "Protección activa") | `frac_protected_mgmt` |
| 7 | ¿Están disponibles `wlan.seq`, potencia de señal y códigos de motivo? | Sí. `seq` presente (~63–66 % nulo, poblado en gestión); `signal_dbm` (`radiotap.dbm_antsignal`) **0 % nulo**; `reason_code` presente en tramas de desconexión (dominan 7 y 1). | `report.md` (fracción nula; reason codes) | `seq_jump_max`, `signal_std_disconn`, `rc_*` |
| 8 | ¿Existen eventos legítimos de desautenticación o disociación? | **Matizado.** Las ~303k/320k desconexiones "Normal" (subtipos 12 y 10 sumados; 302 887 + 180 en cap_a) tienen, en ~99 %, **`src` nulo y `reason_code` nulo**, no protegidas, no broadcast (cap_a: 300 957 de 303 067 con src nulo; solo 88 fuentes distintas). Su causa no está verificada (podrían ser tramas sin cuerpo en la disección). Desconexión legítima con `src` real = unos pocos miles. | `analisis_cruce.txt` | dificultad real del problema |
| 9 | ¿Las etiquetas separan difusión, ataques dirigidos y disociación? | Parcial. La etiqueta es por tipo (`Normal`/`Deauth`/`Disas`), no distingue difusión vs dirigido; se infiere de `is_broadcast_dst` + subtipo. En el ataque, la mayoría NO es broadcast (dirigido); solo una fracción es broadcast (cap_a: 5 714 de 32 772 con rc=7). | `analisis_cruce.txt` (columna Broadcast) | alcance de ataques dirigidos |
| 10 | ¿Qué campos son comunes a todas las capturas? | Todos. Las **745 CSV comparten exactamente las mismas 254 columnas**. Columnas mapeadas ausentes: ninguna en cap_a ni cap_b. | `discover.json`; `report.md` ("Columnas mapeadas ausentes: ninguna") | lista `allowed` |
| 11 | ¿Cada ataque es una ráfaga continua o varias separadas por silencios? | **Una ráfaga continua, demostrado.** 100 % de bloques de 10 s ocupados, 0 vacíos, ~2200–2460 tramas/bloque (mediana). Dura ~180 s. 1 episodio por captura. | `analisis_linea.txt`; `episodes_exploratory.json` | episodios, `T`, caso de partición |
| 12 | ¿Cuál es la banda y el canal de las capturas? | **5 GHz, canal 36** (`radiotap.channel.freq=5180`) en ambas capturas. Valor fijo; no se mapea en `data.yaml`, se registra como limitación de dominio. | lectura puntual de `radiotap.channel.freq`/`wlan_radio.channel` | limitación de dominio |
| 13 | ¿Están disponibles `mfpc` y `mfpr` en asociación o reasociación? | `mfpc` (`wlan.rsn.capabilities.mfpc`) **existe** pero ~99.6 % nulo (solo en tramas RSN de asociación). **`mfpr` NO existe** en AWID3 CSV. | `discover.json`; `report.md` (mfpc nulo); mapeo | mitigación simulada |
| 14 | ¿Qué características podrían actuar como sustitutos del subtipo? | **`reason_code` confirmado como sustituto** (cruce por etiqueta): código **7** casi exclusivo del ataque (cap_a: 32 772 ataque vs 3 Normal; cap_b: ~63 847 vs 1) y código **1** secundario; Normal es `reason_code` nulo. Deben ir en `loao_exclude`. También `n_deauth`/`n_disas` y la tasa de desconexión. | `analisis_cruce.txt` | `loao_exclude` |

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

## Hallazgo relevante: fuga por resolución temporal (riesgo serio)

El dato crudo `frame.time_epoch` tiene resolución sub-milisegundo en tramas normales
(ej. `1608306178.4826`, `.58501`), pero **las tramas de ataque etiquetadas `Deauth`/`Disas`
tienen el timestamp entero en el 100 %** (parte decimal = 0). El artefacto **no es exclusivo
del ataque**: tramas Normal de los subtipos 2 y 3 también tienen `ts` entero casi al 100 %
(0.98 y 1.00), y el subtipo 13 entre 0.82 (cap_a) y 0.95 (cap_b) (`analisis_timestamp.txt`), así que la fracción de `ts` depende del subtipo y del origen de la
trama, no solo de la clase. Aun así, para los subtipos de desconexión (10/12) la diferencia
ataque (1.00) vs Normal (0.49–0.59) es casi perfecta y las features `iat_disconn_mean/std/min`
se derivan de `ts`, por lo que el modelo podría aprender este canal lateral; R2 protege las
etiquetas pero no esto.

Decisión para Gate D (preferida: la primera, por eliminar la diferencia para todas las clases):
- **Truncar todo `ts` a segundo entero** antes de calcular las features (iguala ataque y Normal);
  después hay que reconfirmar que las features de tiempo conservan señal real, o
- Retirar `iat_disconn_std`, `iat_disconn_min` e `iat_disconn_mean` de `allowed`.

Esto también limita la latencia de alerta a 1 s (R3/R4).
