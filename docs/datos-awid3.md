# AWID3: respuestas de la Fase 1

Cada respuesta cita su evidencia: `results/inspection/report.md`, `inventory.json`, `discover.json`, `episodes_exploratory.json` o una figura del notebook. Mientras una respuesta esté pendiente, la decisión que dependa de ella no puede congelarse en Gate D.

## Cómo reproducir la evidencia

Las salidas `results/inspection/*` no se versionan (`.gitignore`). Para regenerarlas desde `data/raw`
(requiere el dataset AWID3 descomprimido y, para `preprocessing`, la variable `WIFI_ML_SALT`):

```
# Inventario e informe (inspect_data)
python -m src.inspect_data --data configs/data.yaml --out results/inspection

# Preprocesado y episodios exploratorios
python -m src.preprocessing --data configs/data.yaml
python -m src.episodes --mode exploratory --data configs/data.yaml --T-provisional 2.0

# Análisis de apoyo (cada modo escribe results/inspection/analisis_<modo>.txt)
python -m scripts.analisis_fase1 --data configs/data.yaml --modo timestamp
python -m scripts.analisis_fase1 --data configs/data.yaml --modo cruce
python -m scripts.analisis_fase1 --data configs/data.yaml --modo linea
python -m scripts.analisis_fase1 --data configs/data.yaml --modo reasociacion
```

Las tablas que sostienen P3, P8 y P11 están copiadas al final de este documento para que la
evidencia quede en el repositorio aunque la salida original no se suba.

| # | Pregunta | Respuesta | Evidencia | Decisión afectada |
|---|---|---|---|---|
| 1 | ¿Cuántas capturas independientes existen por ataque? | Deauth: 33 archivos CSV (`cap_a`); Disas: 41 archivos CSV (`cap_b`). Cada ataque está en su carpeta. | `discover.json`; `report.md` (cap_a/cap_b: n.º de archivos) | caso A, B o C |
| 2 | ¿Los eventos aparecen en tramos contiguos? | Sí, **demostrado con la línea de tiempo**. El ataque dura ~180 s (no toda la captura) y ocupa el 100 % de los bloques de 10 s (cap_a 18/18, cap_b 19/19), con 0 bloques vacíos. Mediana de tramas objetivo por bloque: cap_a ~2190; cap_b ~2458 (mediana), pero el promedio de cap_b es ~3950 (75 131 tramas en 19 bloques), por la mayor densidad de Disas. | `analisis_linea.txt`; `episodes_exploratory.json` | ubicación de cortes |
| 3 | ¿Existen marcas temporales utilizables? | Sí. `ts` 0 % nulo. **Las tramas de ataque (gestión, type=0) tienen `ts` entero en el 100 %.** Las desautenticaciones de gestión Normal son muy pocas (cap_a 72 = 69 disas + 3 deauth; cap_b 51 = 45 disas + 6 deauth), así que no hay una comparación de "mismo subtipo gestión" significativa. **El `ts` entero NO es exclusivo del ataque**: tramas Normal de gestión de otros subtipos (2 y 3) también tienen `ts` entero casi siempre (~0.98–1.00), así que la fracción no separa por sí sola. Las tramas Normal con subtipo 12 pero type=1 (control, ~300k) sí tienen fracción ~0.49–0.59, pero no son desautenticaciones. Riesgo residual: `iat_disconn_*` se derivan de `ts` entero → se retiraron de `allowed` (Gate D). | `analisis_timestamp.txt` (desglosado por type) | ventanas y latencia; features retiradas |
| 4 | ¿Los clientes se reasocian después del evento? | Indicio, no concluyente (1 captura, referencia no independiente). En cap_b las solicitudes de (re)asociación caen de 358 (40 clientes) antes a 18 (4 clientes) tras el episodio; en cap_a el ataque ocupa toda la captura y no hay "después" limpio. | `analisis_reasociacion.txt` | referencia de impacto |
| 5 | ¿Existe un efecto observable que pueda utilizarse como referencia? | Parcial: la caída de reasociaciones tras el ataque (P4) es el único efecto medible, pero con 1 captura no es tráfico de referencia independiente. Evitar el término "anticipación". | `analisis_reasociacion.txt` | uso del término "anticipación" |
| 6 | ¿Qué proporción de tramas tiene protección activada? | `cap_a`: 542 003 / 1 626 469 = **33.3 %** con `protected=1`. `cap_b`: 720 177 / 2 013 716 = **35.8 %**. | `report.md` (tabla "Protección activa") | `frac_protected_mgmt` |
| 7 | ¿Están disponibles `wlan.seq`, potencia de señal y códigos de motivo? | Sí. `seq` presente (~63–66 % nulo, poblado en gestión); `signal_dbm` (`radiotap.dbm_antsignal`) **0 % nulo**; `reason_code` presente en tramas de desconexión (dominan 7 y 1). | `report.md` (fracción nula; reason codes) | `seq_jump_max`, `signal_std_disconn`, `rc_*` |
| 8 | ¿Existen eventos legítimos de desautenticación o disociación? | **Corregido (Gate D).** Un conteo inicial por `fc_subtype` solo daba ~320k "desconexiones Normal" en cap_b, pero al filtrar por `fc_type` resulta que **las desconexiones de gestión (fc_type=0) etiquetadas Normal son: cap_a 72 (69 disas + 3 deauth); cap_b 51 (45 disas + 6 deauth)**. El resto de las ~320k son `fc_type=1` (control) o `fc_type=2` (data), que comparten el número de subtipo pero NO son deauth/disas. Las desautenticaciones de ataque son fc_type=0 el 100 %. Conclusión: desconexión de gestión legítima real = **decenas** por captura, no cientos de miles. | `frames_cap_*.parquet` (fc_type=0 × fc_subtype × label) | dificultad real del problema |
| 9 | ¿Las etiquetas separan difusión, ataques dirigidos y disociación? | Parcial. La etiqueta es por tipo (`Normal`/`Deauth`/`Disas`), no distingue difusión vs dirigido; se infiere de `is_broadcast_dst`. En el ataque de gestión (type=0), la mayoría NO es broadcast (dirigido): cap_a, de las deauth con rc=7, 27 009 unicast vs 5 714 broadcast. El cruce tipo×subtipo×etiqueta (filtrado por type=0) separa deauth (12) de disas (10). | `analisis_cruce.txt` (tipo×subtipo, columna Broadcast) | alcance de ataques dirigidos |
| 10 | ¿Qué campos son comunes a todas las capturas? | Todos. Las **745 CSV comparten exactamente las mismas 254 columnas**. Columnas mapeadas ausentes: ninguna en cap_a ni cap_b. | `discover.json`; `report.md` ("Columnas mapeadas ausentes: ninguna") | lista `allowed` |
| 11 | ¿Cada ataque es una ráfaga continua o varias separadas por silencios? | **Una ráfaga continua, demostrado.** 100 % de bloques de 10 s ocupados, 0 vacíos, ~2190/2458 por captura, tramas/bloque (mediana). Dura ~180 s. 1 episodio por captura. | `analisis_linea.txt`; `episodes_exploratory.json` | episodios, `T`, caso de partición |
| 12 | ¿Cuál es la banda y el canal de las capturas? | **5 GHz, canal 36** (`radiotap.channel.freq=5180`) en ambas capturas. Valor fijo; no se mapea en `data.yaml`, se registra como limitación de dominio. | lectura puntual de `radiotap.channel.freq`/`wlan_radio.channel` | limitación de dominio |
| 13 | ¿Están disponibles `mfpc` y `mfpr` en asociación o reasociación? | `mfpc` (`wlan.rsn.capabilities.mfpc`) **existe** pero ~99.6 % nulo (solo en tramas RSN de asociación). **`mfpr` NO existe** en AWID3 CSV. | `discover.json`; `report.md` (mfpc nulo); mapeo | mitigación simulada |
| 14 | ¿Qué características podrían actuar como sustitutos del subtipo? | **`reason_code` confirmado como sustituto** (cruce filtrado a gestión, type=0): código **7** casi exclusivo del ataque (cap_a deauth type=0: ~32 700 con rc=7 entre unicast y broadcast; en Normal de gestión es marginal) y código **1** secundario. Las desautenticaciones de gestión Normal son muy pocas, así que rc=7 separa casi perfectamente. Van en `loao_exclude` junto con `n_deauth`/`n_disas`, `frac_broadcast` y `n_unique_*` (verificación V2, solo con entrenamiento). | `analisis_cruce.txt` (type=0) | `loao_exclude` |

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

## Evidencia copiada (para reproducibilidad en el repositorio)

Tablas extraídas de `results/inspection/analisis_*.txt` (no versionados). Regenerar con los
comandos de la sección "Cómo reproducir la evidencia".

### P3 — fracción de `ts` entero por etiqueta, **tipo** y subtipo (`analisis_timestamp.txt`)

Desglosado por `fc_type` (0=gestión, 1=control, 2=datos). El ataque es gestión (type=0) con ts entero
al 100 %. Las desautenticaciones de gestión Normal son muy pocas (3 en cap_a, 6 en cap_b). Las tramas
Normal con subtipo 12 pero type=1 (~300k) NO son desautenticaciones:

```
## cap_a
| Etiqueta | Tipo | Subtipo | Tramas | Ts enteros | Fracción |
| Deauth   | 0    | 10      | 49     | 49         | 1.0000   |
| Deauth   | 0    | 12      | 38893  | 38893      | 1.0000   |
| Normal   | 0    | 12      | 3      | 3          | 1.0000   |  (gestión Normal: solo 3)
| Normal   | 1    | 12      | 300954 | 176690     | 0.5871   |  (control, NO desconexión)
| Normal   | 2    | 12      | 1930   | 976        | 0.5057   |  (datos, NO desconexión)

## cap_b
| Etiqueta | Tipo | Subtipo | Tramas | Ts enteros | Fracción |
| Disas    | 0    | 10      | 68994  | 68994      | 1.0000   |
| Disas    | 0    | 12      | 6137   | 6137       | 1.0000   |
| Normal   | 0    | 10      | 45     | 44         | 0.9778   |  (gestión Normal: solo 45)
| Normal   | 1    | 12      | 315981 | 154277     | 0.4882   |  (control, NO desconexión)
```

### P8 — desconexiones de GESTIÓN etiquetadas Normal (`analisis_cruce.txt`, filtrado type=0)

```
## cap_a — tipo × subtipo (etiqueta Normal):
  Normal | type=0 | subtipo 10: 69     (gestión real)
  Normal | type=0 | subtipo 12: 3      (gestión real)
  => desconexiones de gestión Normal en cap_a: 72 (no ~303 000)
  Normal | type=1 | subtipo 12: 300954 (CONTROL, no es desautenticación)
  Normal | type=2 | subtipo 10/12: 2041 (DATOS, no es desautenticación)

## cap_b — tipo × subtipo (etiqueta Normal):
  Normal | type=0 | subtipo 10: 45
  Normal | type=0 | subtipo 12: 6
  => desconexiones de gestión Normal en cap_b: 51
  (el resto, ~320k, es control/datos)
```

### P11 — línea de tiempo de tramas objetivo (`analisis_linea.txt`)

```
## cap_a
- Tramas objetivo: 38942 ; duración 179.0 s
- Bloques de 10 s con tramas objetivo: 18 de 18 ; racha máxima vacía: 0
- Tramas por bloque ocupado: mín 1311, mediana 2190, máx 2828

## cap_b
- Tramas objetivo: 75131 ; duración 181.0 s
- Bloques de 10 s con tramas objetivo: 19 de 19 ; racha máxima vacía: 0
- Tramas por bloque ocupado: mín 305, mediana 2458, máx 21399 (promedio ~3950)
```
