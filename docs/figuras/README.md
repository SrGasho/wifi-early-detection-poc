# Figuras de evaluación

Generadas por `python -m scripts.figuras_evaluacion` a partir de resultados ya guardados (no repiten la prueba). Cada carpeta trae `figures/` y `run_figuras_<split>.json` (commit, entorno y hash de los archivos leídos).

## Cómo leer las líneas temporales

- El eje X está rotulado `t_end (s)` y es **relativo**: 0 s es el instante más temprano mostrado de esa captura (el cierre de la primera ventana evaluada, o el inicio de un episodio si fuera anterior). **No es el inicio de la captura.**
- La franja roja es el episodio de ataque de referencia. La latencia no se lee de la figura; sale de `metrics_episode_<split>.json` (`global.latency.value_seconds`).
- Para el pie de figura en el paper: «Tiempo relativo a la primera ventana evaluada».
- La curva PR no se genera si el conjunto tiene una sola clase (el script avisa).
