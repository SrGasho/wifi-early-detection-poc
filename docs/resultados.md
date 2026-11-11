# Resultados del PoC

Fecha: 10 de noviembre de 2026. Rama `gate-d`.
Partición principal: Caso C (leave-one-attack-out), ambos sentidos. W=5 s, S=1 s, T=2 s, purga=10 s.
Salida bruta en `results/` (no versionada). Este documento fija las cifras en el repositorio.

## 1. Detección y latencia en prueba (test final)

Caso C: entrena+valida con un tipo de ataque, prueba con la captura COMPLETA del otro (incluye su inicio,
por lo que la latencia es medible). `rc_*`, `n_deauth/disas`, `frac_broadcast` y `n_unique_*` excluidos en
el perfil `loao` (sustitutos del subtipo, verificación V2).

| Modelo | Sentido | F1 ventana | Precisión | Recall | Detección | Latencia | Falsas alertas/h |
|---|---|---|---|---|---|---|---|
| Random Forest | deauth→disas | 1.000 | 1.00 | 1.00 | 1/1 | 0.262 s | 0.0 |
| Random Forest | disas→deauth | 0.997 | 1.00 | 0.994 | 1/1 | 1.483 s | 0.0 |
| Línea base (umbral n_disconn) | deauth→disas | 1.000 | 1.00 | 1.00 | 1/1 | 0.262 s | 0.0 |
| Línea base (umbral n_disconn) | disas→deauth | 0.997 | 1.00 | 0.994 | 1/1 | 1.483 s | 0.0 |

## 3. Por qué estas cifras (evidencia de separabilidad)

**Distribución de `n_disconn` en prueba (deauth→disas, test = cap_b):**

| cuantil | ventanas de ataque | ventanas normales |
|---|---|---|
| mín | 82 | 0 |
| mediana | 1 229 | 0 |
| p90 | 4 107 | 0 |
| p99 | 11 682 | 1 |
| máx | 12 016 | 1 |

Las clases **no se solapan**: la ventana normal con más desconexiones de gestión tiene 1; la de ataque con
menos tiene 82. La razón de fondo (corregida en Gate D, ver `datos-awid3.md` P8): en cap_b casi no hay
desautenticaciones de **gestión** normales — las ~320 000 tramas con subtipo 10/12 y etiqueta Normal son en
su mayoría de `fc_type` control/data, que **no** cuentan como desconexión (`n_disconn` exige `fc_type=0`).
Solo 51 desautenticaciones de gestión normales en toda la captura. Por eso ninguna ventana normal acumula
desconexiones y el ataque (ráfaga de gestión densa) queda perfectamente separado.

**Nota:** la tabla del §1 se regeneró tras retirar `iat_disconn_*` de `allowed` (fuga por imputación, V3) y
tras recongelar los splits desde el commit limpio. Las cifras **no cambiaron** (el resultado no dependía de
`iat_*`: `n_disconn` ya separa), lo que confirma que las features con fuga no sostenían el F1.

**Por qué RF y línea base dan cifras idénticas.** Con esa separación, cualquier modelo acierta. La
importancia por permutación del RF en validación es **0 para todas las features** (quitar cualquiera no
cambia la métrica, porque varias separan por sí solas). La línea base usa directamente `n_disconn`. Ambos
convergen a la misma frontera trivial. No es un error de pipeline: es que el problema es linealmente
separable por una sola característica. Features del RF (perfil `loao`, sin sustitutos del subtipo):
`n_frames_total, n_mgmt, n_data, ratio_data_mgmt, n_disconn, rate_disconn, iat_disconn_*, delta_n_disconn,
frac_protected_mgmt, rc_other, seq_jump_max, signal_std_disconn`.

**Verificación de `iat_*` tras truncar (prueba):** `iat_disconn_mean` (med 0.003) e `iat_disconn_std`
(med 0.057) tienen valores en el ataque; en ventanas normales son `nan` (no hay pares de desconexión que
promediar). `iat_disconn_min` queda 0 en el 100 % del ataque tras truncar, así que **no aporta** y se
documenta como tal. La fuga de formato quedó mitigada (el truncado iguala ambas clases en el cálculo).

## 4. Análisis de sensibilidad (solo validación, nunca prueba)

| Experimento | F1 validación | Qué mide |
|---|---|---|
| RF W=3 s | 1.000 | sensibilidad al ancho de ventana (corto) |
| RF W=10 s | 1.000 | sensibilidad al ancho de ventana (largo) |
| RF sin `rc_*` (perfil no_rc) | 1.000 | aporte de los códigos de motivo (riesgo de atajo) |

**Limitación: la validación tiene solo 66 ventanas.** Con tan pocas, que W=3/5/10 den F1=1.0 es una señal
débil de robustez, no una prueba. Se declara explícitamente como limitación.

## 5. Interpretación

- **El problema es casi separable en estos datos.** El ataque es una ráfaga densa (cientos de tramas de
  desconexión por segundo), así que incluso un umbral sobre `n_disconn` alcanza F1≈1.0. El Random Forest
  **no supera** a la línea base; empatan. Esto se reporta sin forzar una conclusión de superioridad
  (artículo III-E).
- **El modelo NO depende del atajo del código de motivo.** El experimento sin `rc_*` mantiene F1=1.0 en
  validación, así que la detección no se apoya en el código 7 (casi exclusivo del ataque). Esto mitiga la
  preocupación del atajo registrada en Gate D 2.6.
- **La detección es robusta al ancho de ventana** (W=3, 5, 10 dan F1=1.0 en validación).
- **Latencia baja:** 0.26 s (deauth→disas) y 1.48 s (disas→deauth) desde el inicio del ataque hasta la
  primera alerta. Medible gracias a Caso C (la prueba conserva el inicio del ataque).
- **Caso C excluye los sustitutos del subtipo** y aun así el F1 se mantiene alto, lo que indica que la
  transferencia entre deauth y disas se apoya en características agregadas de desconexión, no en el subtipo.

## 6. Limitaciones de estos resultados

- Un solo episodio de ataque por captura: la latencia es un valor individual por sentido, sin media ni
  dispersión. Las cifras de detección vienen de una sola ráfaga.
- F1≈1.0 refleja que AWID3 separa el ataque del tráfico normal de forma muy marcada; no debe leerse como
  evidencia de que el problema sea igual de fácil en una red real (ver limitaciones de `decisiones.md`).
- Caso C mide transferencia deauth↔disas (ataques relacionados), no generalización a ataques de otra
  naturaleza.
- Validación corta (66 ventanas): el umbral puede ser inestable.
