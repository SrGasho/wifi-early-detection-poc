# Reglas para el asistente de código

Leer `plan-implementacion-codigo.md` y `configs/` antes de escribir código. Si el código y el plan difieren, se corrige primero el plan.

## No negociables (R1–R11)

- `data/raw/` nunca se modifica (R1).
- Sin etiquetas en `X`: solo columnas de `features.yaml`; nunca `y`, `is_target`, `attack_type`, `label_raw`, `episode_id`, `split` ni `ref_*` (R2).
- Ventanas causales `[t_end − W, t_end)`; solo la ventana anterior para `delta_*` (R3).
- La alerta ocurre en `t_end` (R4).
- `k = 1` fijo (R5).
- El conjunto de prueba solo con `--final`, una vez por etapa y por experimento; nunca para elegir nada (R6).
- Purga `>= W` y `>= max_W_seconds` (R7).
- Una sola función de características, `compute_window_features`; `predict` y `replay` solo leen `metadata.json` (R8).
- Ningún módulo envía tramas, abre sockets hacia equipos ni ejecuta comandos de red (R9).
- Cada ejecución deja `run_*.json` con configuración, commit, semilla y entorno (R10).
- El detector no afirma el tipo de ataque; identificadores de captura neutros (R11).

## Otras reglas

- No escribir nombres de columnas de AWID3 a mano; vienen de `configs/data.yaml`.
- Un valor `< >` en la configuración es una decisión pendiente: no inventarlo.
- Los episodios exploratorios nunca se usan para métricas ni entrenamiento.
- Los experimentos de sensibilidad (`role: sensitivity`) nunca llegan a la prueba.
- Cada módulo nuevo llega con su prueba en `tests/`; `pytest -q` debe quedar en verde.
- Después de `gate-d` no se modifican `configs/splits/*.json` ni `docs/decisiones.md` sin crear un experimento nuevo.
- No hacer commits, push, ramas ni cambios de configuración de git: los hace el autor.
