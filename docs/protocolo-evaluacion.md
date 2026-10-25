# Protocolo de evaluación

Definiciones exactas que implementa `src/evaluate.py`. Cualquier cambio se registra en `docs/decisiones.md` antes de evaluar la prueba.

## Por ventana

- **Ventana positiva:** `score ≥ threshold`. Instante de alerta: `t_end`.
- **Etiqueta de referencia:** `y = 1` si la ventana contiene al menos una trama objetivo (k = 1).
- Se reportan matriz de confusión, precisión (*precision*), exhaustividad (*recall*), F1, FPR y FNR.
- **Por tipo de ataque:** sobre el subconjunto de ventanas normales más las ventanas que contienen ese tipo. Si el tipo no está en el conjunto: "no disponible para esta partición", nunca cero.

## Eventos de alerta

- Dos ventanas positivas de la misma captura pertenecen al mismo evento si `t_end(j) − t_end(i) ≤ max_gap_seconds`.
- Cobertura de un evento: `[t_alert − W, t_last)`.

## Por episodio (solo episodios definitivos)

- **Episodio detectado:** al menos una ventana positiva se solapa con `[t_start, t_end]`.
- **Latencia:** `t_end` de la primera ventana positiva solapada menos `t_start`, solo si `start_complete = True`.
- **Tramas antes de la alerta:** tramas objetivo del episodio con `ts` menor que el instante de alerta.
- **Un solo episodio medible:** se reporta el valor individual, sin media ni mediana.
- **Ningún episodio con inicio completo:** "no disponible para esta partición".
- **Resolución:** la latencia está acotada por `S`; diferencias menores que `S` no son interpretables.

## Falsas alertas

- **Falsa alerta:** evento cuya cobertura no se solapa con ningún episodio definitivo del conjunto.
- **Falsas alertas por hora:** falsas alertas / horas de tiempo normal evaluado.
- **Tiempo normal evaluado:** por captura, `(último t_end − primer t_end) + W` de las ventanas del conjunto (sin purgas), menos la duración de sus episodios.

## Rendimiento operativo (`replay.py`)

- Tiempo de características, de predicción y total por ventana (media, p50, p95, máximo).
- Tasa de tramas procesadas frente a tasa de entrada.
- Solo es válido si `consistency_with_batch.valid = true`.
- No se reportan como resultados reales la reconexión, la continuidad del servicio ni el impacto sobre usuarios.

## Uso del conjunto de prueba

- Una sola ejecución por etapa, con `--final`, con la configuración principal y el árbol git limpio.
- Los experimentos de sensibilidad nunca se ejecutan sobre la prueba.
