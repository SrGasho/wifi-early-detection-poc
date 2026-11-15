# Cierre de pendientes del PoC — Plan de implementación

> **Para quien ejecute:** usar superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans. Los pasos usan casillas `- [ ]`.

**Objetivo:** cerrar lo que queda de `docs/guia-packet-tracer-y-pendientes.md` (D1–D8, I1–I9) y `docs/seguimiento.md` sin romper R1–R11.

**Arquitectura:** cuatro carriles. (A) trabajo autónomo sin decisiones; (B) decisiones del autor que cambian el alcance; (C) trabajo condicionado a B (replay y mitigación); (D) trabajo manual del autor (Packet Tracer, git, LaTeX, citas).

**Stack:** Python 3.13 en `.venv` (`.venv/Scripts/python.exe -m pytest -q`), pandas, matplotlib, pytest. El paper es LaTeX (`docs/Entregas_pasadas/paper.tex`, ignorado por git).

**Spec:** `docs/guia-packet-tracer-y-pendientes.md` (Parte 2), `docs/seguimiento.md`, `plan-implementacion-codigo.md` §8.8, §8.9, §11.

## Estado verificado el 2026-11-15

- `pytest -q` en `.venv`: **93 pruebas en verde**. (El Python global no tiene pytest; usar `.venv`.)
- `src/replay.py` (163 líneas) y `src/mitigation_simulator.py` (125) **ya existen** con `test_replay_consistency.py` y `test_mitigation.py`. La Fase 6 está escrita, **no ejecutada**. Por eso `docs/guia…` I1/I2 dicen "no ejecutado" y no "no implementado".
- Los 3 experimentos con prueba (`loao_*` ×2, `baseline_*` ×2) ya tienen `final/{predict,alerts,evaluate}.done`; falta `replay.done` y la mitigación.
- `pdflatex`, `xelatex` y `latexmk` **no están instalados**.
- I7: `arquitectura.md`, `modelo-amenazas.md`, `protocolo-evaluacion.md` y `diagramas/` no contienen `caso_B`, `Caso B`, `iat_` ni `exp_rf`. Único residuo real: `plan-implementacion-codigo.md:893` ("Caso B para clasificación y Caso C para latencia").

## Restricciones globales

- R1 `data/raw/` intacto. R6 la prueba solo con `--final`, una vez por etapa y experimento. R9 ningún módulo envía tramas. R10 `run_*.json` en cada ejecución.
- Cada módulo nuevo lleva su prueba; `pytest -q` debe quedar en verde.
- **No se hacen commits, ramas ni push** (los hace el autor). Los pasos "Commit" quedan para el autor.
- Si el código y el plan difieren, se corrige primero el plan.
- Después de `gate-d` no se tocan `configs/splits/*.json` ni `docs/decisiones.md` sin un experimento nuevo.

## Foco de revisión

- Una figura de evaluación que relea la prueba sin pasar por `guard_final` no debe crear ni borrar `final/*.done` ni reescribir `metrics_*` (R6).
- `replay --final` exige árbol git limpio: ejecutarlo con cambios sin commit falla a propósito.
- Un replay con `consistency_with_batch.valid = false` no se reporta nunca.
- `mfpc` nulo se lista como "desconocido", no como vulnerable.
- Latencia de procesamiento medida sobre 66 ventanas de validación no equivale a la de prueba: no mezclar en el paper.

---

## Carril B — Decisiones del autor (bloquean C y parte de D)

| # | Decisión | Opciones | Recomendación |
|---|---|---|---|
| B1 (I1) | Mitigación simulada | (a) ejecutar replay + mitigación sobre prueba; (b) reformular objetivo 3 como diseño de referencia | **(a)**: el código y las pruebas ya existen; el costo es una ejecución `--final` por experimento. |
| B2 (D4) | VLAN 30 de invitados | sí / no | **Sí**: ya está en la guía y la ACL; quitarla obliga a rehacer figura y guía. |
| B3 (D8) | Criterios de aceptación (latencia ≤ 2 s, ≤ 1 falsa alerta/h, F1 ≥ 0,90) | confirmar / cambiar | Confirmar; registrar fecha en `decisiones.md` con experimento nuevo si ya pasó `gate-d`, y mantener que son de diseño, no previos. |
| B4 (I8) | Rama `docs/correccion-timestamp-y-paper` | PR a `main` / dejarla | PR, como #1 y #2. |
| B5 (I9) | Versionar paper | mover `paper.tex` a `docs/paper/` | Sí; excepción puntual en `.gitignore`. |

---

## Carril A — Autónomo (sin decisiones)

### Task A1: Script de figuras de evaluación de solo lectura (I3)

**Files:**
- Create: `scripts/figuras_evaluacion.py`
- Test: `tests/test_figuras_evaluacion.py`

**Interfaces:**
- Consumes: `src.evaluate.save_figures(ev: DataFrame, episodes: DataFrame, out_dir: Path, split: str) -> None`; archivos `results/<exp_id>/eval_windows_<split>.parquet` y `metrics_episode_<split>.json` (clave `episodes` con `capture_id`, `t_start`, `t_end`).
- Produces: `build_figures(results_dir: Path, split: str, out_dir: Path) -> list[Path]` — escribe PNG en `out_dir/figures/` y devuelve sus rutas.

- [ ] **Step 1: Escribir las pruebas** (`test_builds_pr_and_timeline_pngs`: crea `eval_windows_test.parquet` y `metrics_episode_test.json` sintéticos en `tmp_path`, espera `pr_test.png` y `timeline_cap_b_test.png`; `test_does_not_touch_results_dir`: el listado de `results_dir` con tamaños no cambia y no aparece `final/`; `test_missing_inputs_raise_clear_error`: `FileNotFoundError` con el nombre del archivo faltante).
- [ ] **Step 2:** `.venv/Scripts/python.exe -m pytest tests/test_figuras_evaluacion.py -q` → FALLA (módulo inexistente).
- [ ] **Step 3: Implementar** `build_figures` y un `main` con `--exp <yaml> --split {val,test} --out docs/figuras`; resuelve `exp_id` leyendo `results/_index/<name>.json` (no llama a `resolve_exp_id` con guardas finales ni a `guard_*`). Docstring: "solo lee resultados ya generados; no ejecuta ni repite la prueba (R6)".
- [ ] **Step 4:** pruebas del archivo en verde, luego `pytest -q` completo en verde.
- [ ] **Step 5:** generar figuras reales para `loao_deauth_to_disas` y `loao_disas_to_deauth` (`--split test`) y confirmar que `results/*/final/` no cambió.
- [ ] **Step 6 (autor):** commit.

### Task A2: Corregir residuo de Caso B en el plan (I7)

**Files:** Modify `plan-implementacion-codigo.md:893`

- [ ] Reemplazar "Caso B para clasificación y Caso C para latencia; latencia descriptiva" por "Caso C (Opción D): la prueba conserva el inicio del ataque; latencia descriptiva (valor individual)".
- [ ] `grep -rn "Caso B" docs README.md plan-implementacion-codigo.md` → solo menciones que expliquen el descarte.

### Task A3: Tabla "afirmación del paper → archivo de evidencia" (Fase 7)

**Files:** Create `docs/trazabilidad-paper.md`

- [ ] Una fila por cifra del paper (§Resultados, tabla de `docs/resultados.md` §1, sensibilidad §4) con su archivo en `results/<exp_id>/` y su `run_*.json`. Cifras solo desde los JSON, no de memoria.

---

## Avance del 2026-11-15

| Task | Estado | Evidencia |
|---|---|---|
| A1 figuras de solo lectura | **Hecho** | `scripts/figuras_evaluacion.py` + 15 pruebas; `pytest -q` = 108 verdes (tras la revisión del PR #3); figuras en `docs/figuras/loao_*/figures/`; `results/` sin cambios (hash antes/después) y `final/` sin `.done` nuevos. Eje de tiempo relativo a 0 s por captura. |
| A2 residuo de Caso B | **Hecho** | `plan-implementacion-codigo.md:893` |
| A3 trazabilidad paper→evidencia | Pendiente | — |
| C1 replay en validación | **Hecho** (adelantado: no usa prueba) | los 4 experimentos: `consistency_with_batch.valid = true`, 0 diferencias, `max_abs_score_difference = 0.0`. RF: ≈ 8,7 ms por ventana de extremo a extremo (media, validación). Línea base: ≈ 3,8–4,2 ms. |
| B1–B5 | **Decididas (15-nov): se aplican las recomendaciones** | `docs/seguimiento.md` §4 |
| B2 VLAN 30 | **Hecho** | `paper.tex`: quitado "si se implementa"; añadida nota de ACL sin estado |
| B3 criterios | **Hecho** | párrafo en Protocolo de evaluación (declarados de diseño, posteriores a resultados preliminares) y fila en `seguimiento.md`. **No** en `decisiones.md`: CLAUDE.md la congela tras `gate-d`. Nota: `paper.tex` no traía estos criterios; solo estaban en la guía. |
| B4 PR | Borrador listo | `docs/superpowers/pr-correccion-timestamp-y-paper.md`; lo abre el autor |
| B5 paper versionado | **Hecho** | `docs/paper/paper.tex` (no ignorado). No hizo falta tocar `.gitignore`. |
| I4, I5 | **Omitidos por decisión del autor** | — |
| C2 `--final` replay + mitigación | **Hecho** (commit `545bf2e`, árbol limpio) | 4 experimentos: `replay.done` y `mitigation.done`; `valid = true`; 0 acciones prohibidas. Cifras en `docs/resultados.md` §2. |
| C3 paper tras C2 | **Hecho** (paper); anteproyecto pendiente | `paper.tex`: resumen, §Implementación, §Protocolo, §Resultados, Limitaciones y Conclusiones. El anteproyecto es PDF: no se edita desde aquí (I6). |

## Carril C — Condicionado a B1 = (a)

### Task C1: Replay en validación (ensayo, sin `--final`)

- [ ] `python -m src.replay --exp configs/experiments/exp_loao_deauth_to_disas.yaml --split val --speed max` y el mismo para el otro sentido y las dos líneas base.
- [ ] Esperado: `replay_val.json` con `consistency_with_batch.valid = true` en los cuatro. Si alguno es `false`, **detener** y depurar con superpowers:systematic-debugging (no ejecutar `--final`).

### Task C2: Replay `--final` + mitigación (una vez por experimento)

- [ ] Requisitos: C1 en verde, árbol git limpio (el autor hace commit de A1–A3 antes).
- [ ] `python -m src.replay --exp … --split test --final` y `python -m src.mitigation_simulator --exp … --split test --final` para los 4 experimentos. Una sola vez por etapa (R6).
- [ ] Verificar `final/replay.done`, `replay_test.json` con `valid = true`, `mitigation_log_test.jsonl` sin ninguna de `FORBIDDEN_ACTIONS` y con `tipo_de_evento = ataque_de_desconexion`.
- [ ] Registrar en `docs/resultados.md` y `docs/seguimiento.md` (Fase 6 → hecha) con el commit del run.

### Task C3: Alinear paper y anteproyecto con el resultado de B1

- [ ] Si (a): quitar "queda pendiente" de `paper.tex` líneas ~269, 277, 325, 333; añadir tiempo por ventana medido; actualizar anteproyecto (I6).
- [ ] Si (b): dejar el paper como está, quitar "tiempo de procesamiento" de la tabla de protocolo y reescribir el objetivo 3 del anteproyecto.

---

## Carril D — Trabajo manual del autor (en este orden)

1. **Packet Tracer (D1):** seguir la Parte 1 de la guía; guardar `docs/diagramas/topologia-empresa.pkt` y `.png`; capturar las 6 pruebas de §1.10. *(No automatizable: es GUI.)*
2. **D2, D3, D5, D6, D7:** figura CRISP-DM (Draw.io), tabla VLAN/IP, canal sensor→servidor (propuesta: un JSON por ventana sobre TCP; en Packet Tracer es solo lógico), WPA2-PSK con PMF opcional como decisión de diseño, 200 Mbps como supuesto de planificación o con cita.
3. **I4:** verificar `kolias2016`, `mishra2019`, `zhen2025`, `chatzoglou2021` contra DOI.
4. **I5:** compilar en Overleaf (IEEEtran) o instalar MiKTeX; revisar `table*` y saltos.
5. **I8/I9:** PR de la rama, mover el paper a `docs/paper/`.

## Auto-revisión

- Cobertura: D1–D8 e I1–I9 aparecen en un carril. A1–A5 de análisis ya están declarados en el paper (no requieren tarea).
- Sin tipos huérfanos: `build_figures` se define en A1 y no lo usa otro task.
- Proporción: plan corto a propósito; el código lo escribe quien ejecute.
