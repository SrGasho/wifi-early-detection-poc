# Seguimiento del proyecto

Última actualización: 10 de noviembre de 2026.

Registra el estado de cada fase, las verificaciones abiertas y los acuerdos. Los commits los hace el autor.

## 1. Estado por fase

| Fase | Estado | Falta para cerrar |
|---|---|---|
| 0. Preparación | Código escrito. 93 pruebas en verde. | — |
| 1. Inspección de AWID3 | Cerrada (PR #1, merged a `main`). 12/14 preguntas; P4/P5 indicios. | — |
| 2. Gate D (partición, episodios, ventanas) | Implementado en rama `gate-d`. Decisiones en `decisiones.md` y `reporte-gate-d.md`. | PR de Gate D + verificaciones 3.1. |
| 3. Entrenamiento (baseline + RF) | En curso: RF Caso C deauth→disas entrenado; F1 val = 1.0. | Baselines Caso C; sentido disas→deauth; sensibilidad. |
| 4-8 | No iniciadas. | Ver plan. |

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

## 5. Dudas abiertas

- ¿El artículo y el anteproyecto se versionan en el repositorio? Los PDF están en `docs/Entregas_pasadas/`.
