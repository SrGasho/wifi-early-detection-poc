# Trazabilidad: afirmación del paper → archivo de evidencia

Verificado el 2026-11-15 contra los JSON de `results/` (no versionado; ver `docs/resultados.md`). Las rutas son relativas a `results/<exp_id>/`. Abreviaturas de experimento:

| Abrev. | `exp_id` |
|---|---|
| RF d→s | `20261110-2232-loao_deauth_to_disas` |
| RF s→d | `20261110-2232-loao_disas_to_deauth` |
| LB d→s | `20261110-2233-baseline_deauth_to_disas` |
| LB s→d | `20261110-2233-baseline_disas_to_deauth` |
| W3 / W10 / no_rc | `20261110-2233-rf_sens_W3`, `…rf_sens_W10`, `…loao_deauth_to_disas_no_rc` |

Cada ejecución tiene su `run_<etapa>[_<conjunto>].json` con configuración, commit, semilla y entorno (R10).

## Resultados en prueba (paper, Tabla `tab:resultados`)

| Afirmación | Valor | Archivo | Campo |
|---|---|---|---|
| RF d→s: F1 / recall | 0,9973 / 0,9946 (185 de 186 ventanas de ataque; 0 falsos positivos) | RF d→s `metrics_window_test.json` | `global.f1`, `recall`, `tp=185`, `fn=1`, `fp=0` |
| RF s→d: F1 / recall | 0,9972 / 0,9944 (179 de 180) | RF s→d `metrics_window_test.json` | ídem, `tp=179`, `fn=1` |
| LB d→s: F1 / recall | 1,0000 / 1,0000 (186 de 186) | LB d→s `metrics_window_test.json` | `tp=186`, `fn=0` |
| LB s→d: F1 / recall | 0,9972 / 0,9944 | LB s→d `metrics_window_test.json` | `tp=179`, `fn=1` |
| Precisión 1,000 en las cuatro filas | `fp = 0` en todas | los cuatro `metrics_window_test.json` | `global.precision` |
| Latencia d→s (ambos modelos) | 0,262 s | `metrics_episode_test.json` de RF d→s y LB d→s | `global.latency.value_seconds` |
| Latencia s→d (ambos modelos) | 1,483 s | `metrics_episode_test.json` de RF s→d y LB s→d | ídem |
| Detección por episodio | 1/1 en las cuatro | los cuatro `metrics_episode_test.json` | `global.n_detected / n_episodes` |
| FA/h = 0 | 0 falsas alertas | los cuatro `metrics_episode_test.json` | `false_alerts_per_hour` |
| Un solo episodio por sentido | `n_episodes = 1` | `metrics_episode_test.json` | `global.n_episodes` |
| Ejecución final atada al commit `6a49bb4`, árbol limpio | `git_commit`, `git_dirty = False` | `run_evaluate_test.json` | `git_commit`, `git_dirty` |

## Reproducción y mitigación simulada (paper §Resultados, último párrafo)

| Afirmación | Valor | Archivo | Campo |
|---|---|---|---|
| Reproducción idéntica al lote | 0 diferencias de decisión; diferencia máxima de puntuación 0,0 | `replay_test.json` (los cuatro) | `consistency_with_batch` |
| Commit de la reproducción | `545bf2e`, árbol limpio | `run_replay_test.json` | `git_commit`, `git_dirty` |
| Tiempo por ventana RF | 7,4 ms (d→s) y 6,9 ms (s→d); p95 11,6 y 10,9 ms; máx 44,4 y 57,2 ms | `replay_test.json` de RF d→s / s→d | `end_to_end_seconds` |
| Tiempo por ventana LB | 3,4 ms y 2,5 ms | `replay_test.json` de LB | `end_to_end_seconds.mean` |
| Tasa de entrada | 3 334 y 2 697 tramas/s | `replay_test.json` | `captures[0].input_rate_frames_per_second` |
| Tasa procesada RF | 452 607 y 391 287 tramas/s | `replay_test.json` de RF | `captures[0].processed_rate_frames_per_second` |
| Una notificación por alerta, sin aislamiento | `n_alerts = 1`, `n_notifications = 1`; ningún `aislar/bloquear/desautenticar/expulsar` | `mitigation_log_test.jsonl`, `run_mitigation_test.json` | `tipo_de_evento`, `accion_simulada` |
| `tau_high = 0,9`, enfriamiento 30 s | supuestos de simulación, no optimizados | `configs/experiments/exp_*.yaml` (`tau_high`, `cooldown_seconds`) y `docs/decisiones.md` | fila `tau_high`, `cooldown_seconds` |

## Sensibilidad (solo validación)

| Afirmación | Valor | Archivo |
|---|---|---|
| F1 = 1,000 con W = 3, 5, 10 y sin `rc_*` | F1 = 1,0 en los cuatro | `metrics_window_val.json` de W3, RF d→s, W10 y no_rc |
| «66 ventanas de validación» | Exacto solo para el principal y `no_rc` (66). **W3 tiene 68 y W10 tiene 61**, porque `W` cambia la rejilla | `metrics_window_val.json` (`tp+fp+tn+fn`) |
| Importancia por permutación = 0 en todas las características | — | RF d→s y RF s→d `permutation_importance_val.json` |

## Afirmaciones sin archivo propio (o dependientes del código)

- Separación por `n_disconn` en prueba (82 frente a 1): verificada el 2026-11-15 contra `data/processed/windows_caso_C_deauth_to_disas_W5_S1.parquet` (`split == test`): ventana normal con más desconexiones = 1, ventana de ataque con menos = 82. En disas→deauth: 3 y 48 (archivo `…disas_to_deauth…`). `data/processed/` no se versiona.
- Desviación de R6 (dos ejecuciones `--final`): la primera se descartó y se borró; solo existe la nota del autor en `docs/decisiones.md` y `docs/reporte-gate-d.md` §5.
- Tamaños de partición 503/66/600 (d→s): `configs/splits/*.json` y `docs/resultados.md`.

## Discusión (paper, §Discusión y correcciones del 2026-11-15)

Cifras calculadas el 2026-11-15, **después** de la evaluación final, con fines descriptivos; no modificaron ningún parámetro ni selección.

| Afirmación | Valor | Archivo | Campo |
|---|---|---|---|
| Ventanas por conjunto d→s / s→d | train 503 / 465; val 66 / 105; test 600 / 599 | `data/processed/windows_caso_C_<sentido>_W5_S1.parquet` | `split`, `y` (train = 373+130 y 368+97; val = 31+35 y 31+74; test = 414+186 y 419+180) |
| 100 % de ventanas de ataque de entrenamiento con ≥ 1 desconexión | 130/130 y 97/97 | ídem | `n_disconn >= 1` con `split == train`, `y == 1` |
| Validación: 36 s antes y 35 s (d→s) o 74 s (s→d) después del inicio del ataque | `cap_a` 1608306566,2–1608306637,0; `cap_b` 1608310059,8–1608310170,0 | `configs/splits/caso_C_*.json` | `units.val` |
| Umbrales de la línea base | 48 (d→s) y 122 (s→d); = menor conteo de ataque en la validación respectiva | `models/<exp_id>/metadata.json` y `windows_*.parquet` | `threshold`; mínimo de `n_disconn` con `split == val`, `y == 1` |
| Umbrales del RF | 0,45 (d→s) y 0,93 (s→d) | `models/<exp_id>/metadata.json` | `threshold` |
| Ventana fallida del RF d→s | la última ventana de ataque (+185 s), puntuación 0,44 < 0,45 | `eval_windows_test.parquet` | `y = 1`, `y_pred = 0` |
| Ventana fallida del RF s→d | la primera ventana de ataque, puntuación 0,91 < 0,93 | ídem | ídem |
| Ventana fallida de la línea base s→d | la primera ventana (48 < 122); la siguiente tiene 228; primera alerta +1,0 s | `eval_windows_test.parquet`, `windows_*.parquet` | ídem |
| Línea base d→s sin ventanas fallidas | primera ventana con 122 ≥ 48 | ídem | ídem |
| Horas de tráfico normal evaluadas | 0,1175 h (d→s) y 0,1178 h (s→d); 0 falsas alertas | `metrics_episode_test.json` | `normal_hours_evaluated`, `n_false_alerts` |
| Límite superior de falsas alertas/h ≈ 25 | **cálculo propio**: Poisson con 0 eventos, 95 %: 2,996 / 0,1175 ≈ 25,5 y 2,996 / 0,1178 ≈ 25,4 | derivado de la fila anterior | — |
| Tasa procesada / tasa de entrada ≈ 136 y 145 | 452 607 / 3 334 y 391 287 / 2 697 | `replay_test.json` (RF) | `captures[0]` |
| Clientes en la mitigación | 10 compatibles, 0 no compatibles, 0 desconocidos en los 4 experimentos | `mitigation_log_test.jsonl` | `clientes` |
| Puntuación de la línea base = conteo | `confianza` = 12 016 y 1 424, no una probabilidad; la prioridad «alta» siempre se cumple | `mitigation_log_test.jsonl` (línea base) | `confianza`, `prioridad` |
