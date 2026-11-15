# Seguimiento del proyecto

Última actualización: 10 de noviembre de 2026.

Registra el estado de cada fase, las verificaciones abiertas y los acuerdos. Los commits los hace el autor.

## 1. Estado por fase

| Fase | Estado | Falta para cerrar |
|---|---|---|
| 0. Preparación | Código escrito. 93 pruebas en verde. | — |
| 1. Inspección de AWID3 | Cerrada (PR #1, merged a `main`). 12/14 preguntas; P4/P5 indicios. | — |
| 2. Gate D (partición, episodios, ventanas) | Implementado y verificado (V1/V2/V3). | PR de Gate D. |
| 3. Entrenamiento (baseline + RF) | Hecho: RF y baseline, ambos sentidos Caso C. | — |
| 4. Evaluación (ventana + latencia) | Hecho: test final ambos sentidos; resultados en `docs/resultados.md`. | — |
| 5. Sensibilidad (W=3,10; sin rc) | Hecho (solo validación). F1=1.0 en los tres. | — |
| 6. Replay y mitigación simulada | Hecho el 15-nov con `--final` (commit `545bf2e`): replay válido y mitigación en los 4 experimentos. Cifras en `docs/resultados.md` §2. | — |
| 7-8 (revisión, documentación) | Parcial: figuras (I3) y paper actualizados. | Tabla de trazabilidad; README final; anteproyecto (I6). |

## 2. Hallazgo clave de Gate D: Caso B no viable, se usa Caso C

Con la geometría de AWID3 (normal al inicio, ataque en bloque al final), Caso B no produce una partición
de 3 vías con ambas clases en cada conjunto. Se adoptó **Caso C (leave-one-attack-out)** como principal,
con la Opción D (train en dos unidades a los lados de una validación que cruza la frontera). Razonamiento
y alternativas en `docs/reporte-gate-d.md` 2.1. Verificado con datos: train/val/test con ambas clases y
latencia medible en test.

## 3. Pendientes

### 3.1 Verificaciones con datos
1. ≥ 99 % de ventanas de ataque de entrenamiento con trama de desconexión (criterio de W=5). Pendiente.
2. `frac_broadcast_dst_disconn` y `n_unique_*_disconn` por clase (criterio de `loao_exclude`). Pendiente.
3. Distribución de `iat_disconn_*` por clase tras truncar `ts`. Pendiente.
4. Tamaños de conjuntos de Caso C. Hecho: deauth→disas = 503/66/600 ventanas.

### 3.2 Cambios de código y configuración (hechos en la rama `gate-d`)
1. Truncado de `ts` en `iat_*` en `compute_window_features`. Hecho.
2. Perfil `no_rc` en `resolve_feature_columns` para el experimento de sensibilidad. Hecho.
3. `features.yaml`: `reason_codes: [7, 1]`, `loao_exclude` con `rc_7`/`rc_1`. Hecho.
4. `case_c` reescrito (Opción D). Hecho.
5. Experimentos: valores fijados; `T_method: fixed`; dos de sensibilidad W y uno `no_rc`. Hecho.

### 3.3 Documentos externos (pendientes, fuera de código)
- Artículo: alcance III-A, nota de `mfpr` en III-B. Texto propuesto en `reporte-gate-d.md`.
- Anteproyecto: "pronosticar" → "detectar de forma temprana"; "mitigar" → "simular la mitigación".

## 4. Acuerdos

| Fecha | Acuerdo |
|---|---|
| 10-nov | Fase 1 cerrada y merged (PR #1). |
| 10-nov | Caso B descartado como partición principal; Caso C (Opción D) adoptado. |
| 10-nov | Truncado de `ts` solo en `iat_*`. |
| 10-nov | Trazabilidad: cada decisión de diseño documenta las alternativas consideradas (petición del autor). |
| 15-nov | **B1:** se ejecuta la mitigación simulada (replay y `mitigation_simulator` con `--final`, una vez por experimento). **Ejecutado** tras el commit `545bf2e`: los 4 experimentos con `replay.done` y `mitigation.done`. |
| 15-nov | **B2:** la VLAN 30 (invitados) se implementa; se quitó "si se implementa" del paper. |
| 15-nov | **B3:** criterios de aceptación de diseño confirmados: latencia ≤ 2 s, ≤ 1 falsa alerta por hora, F1 por ventana ≥ 0,90. Son del autor, fijados después de ver resultados preliminares; el paper lo declara. Se registran aquí y no en `decisiones.md` porque esa tabla está congelada tras `gate-d`. |
| 15-nov | **B4:** la rama `docs/correccion-timestamp-y-paper` va a `main` con PR (borrador en `docs/superpowers/pr-correccion-timestamp-y-paper.md`). Lo abre el autor. |
| 15-nov | **B5:** `paper.tex` pasó de `docs/Entregas_pasadas/` (ignorado) a `docs/paper/` (versionable). |
| 15-nov | Omitidos por ahora: verificación de citas (I4) y compilación del paper (I5). Packet Tracer (D1) se hará en otra sesión. |

## 5. Dudas abiertas

- Ninguna sobre versionado: el artículo ahora está en `docs/paper/`. Los PDF de entregas pasadas siguen ignorados en `docs/Entregas_pasadas/`.
