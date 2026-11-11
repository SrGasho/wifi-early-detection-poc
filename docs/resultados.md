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

## 2. Análisis de sensibilidad (solo validación, nunca prueba)

| Experimento | F1 validación | Qué mide |
|---|---|---|
| RF W=3 s | 1.000 | sensibilidad al ancho de ventana (corto) |
| RF W=10 s | 1.000 | sensibilidad al ancho de ventana (largo) |
| RF sin `rc_*` (perfil no_rc) | 1.000 | aporte de los códigos de motivo (riesgo de atajo) |

## 3. Interpretación

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

## 4. Limitaciones de estos resultados

- Un solo episodio de ataque por captura: la latencia es un valor individual por sentido, sin media ni
  dispersión. Las cifras de detección vienen de una sola ráfaga.
- F1≈1.0 refleja que AWID3 separa el ataque del tráfico normal de forma muy marcada; no debe leerse como
  evidencia de que el problema sea igual de fácil en una red real (ver limitaciones de `decisiones.md`).
- Caso C mide transferencia deauth↔disas (ataques relacionados), no generalización a ataques de otra
  naturaleza.
- Validación corta (66 ventanas): el umbral puede ser inestable.
