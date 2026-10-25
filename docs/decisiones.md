# Registro de decisiones (Gate D)

Cada decisión indica su valor, la evidencia que la sustenta y el commit en que se congeló. Después de la etiqueta `gate-d` nada de esta tabla cambia sin crear un experimento nuevo.

| Decisión | Valor | Evidencia | Commit |
|---|---|---|---|
| Objetivo del modelo | binario: normal frente a ataque de desconexión; análisis por tipo como reporte adicional | plan, sección 14.1 | |
| Caso de partición | pendiente (A, B o C) | `docs/datos-awid3.md` preguntas 1, 2 y 11 | |
| Proporciones y ubicación de cortes | pendiente | `episodes_exploratory.json` | |
| `S` principal | pendiente | resolución deseada y costo (plan, 8.2.1) | |
| `W` principal | pendiente | estadísticas de entrenamiento (plan, 8.2.1) | |
| `W` de sensibilidad | pendiente (lista; un experimento por valor) | declarada antes de entrenar | |
| `purge_seconds` | pendiente (≥ mayor `W`) | | |
| Método y parámetros de `T` | pendiente (`fixed` o `percentile_multiple`) | intervalos de entrenamiento | |
| `max_gap_seconds` | pendiente (≥ `S`) | | |
| Códigos de motivo con columna propia | pendiente | pregunta 7 | |
| Exclusiones del Caso C | pendiente | pregunta 14 | |
| Características retiradas por falta de campos | pendiente | preguntas 7, 10 y 13 | |
| Tratamiento de tramas con etiqueta ajena (`other`) | pendiente | `preprocessing_summary.json` | |
| Imputación | constante −1, ajustada con entrenamiento | plan, 8.3 | |
| Criterio de umbral | máximo F1 en validación; empate: menor umbral | plan, 8.5 y 8.6 | |
| `tau_high`, `cooldown_seconds` | pendiente | no afectan métricas | |

## Limitaciones declaradas

- La partición es consciente de etiquetas (organiza capturas, verifica clases, ubica cortes). Las etiquetas no entran al modelo, pero esto limita la interpretación de la generalización.
- AWID3 (802.1X/EAP, PMF activo) difiere del escenario de la pequeña empresa.
- Sin validación en hardware físico; la mitigación es simulada.
- La latencia está acotada por `S`.
- El Caso C mide transferencia entre ataques relacionados, no generalización a ataques de otra naturaleza.
- Compatibilidad PMF desconocida cuando `mfpc` es nulo o no existe.
