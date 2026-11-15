# wifi-early-detection-poc

Prueba de concepto para la **detección temprana de ataques de desautenticación y disociación** en una red Wi-Fi de referencia para pequeña empresa, mediante aprendizaje automático.

**Autor:** Juan David Quiroga — Proyecto Curricular de Ingeniería de Sistemas, Universidad Distrital Francisco José de Caldas.

## Alcance

- Detecta ventanas de tráfico de gestión compatibles con un ataque de desconexión **después de su inicio** y mide la latencia hasta la alerta. No predice el ataque antes de su primera trama.
- Usa **AWID3** como única fuente de datos. No hay validación en hardware físico.
- Compara una **línea base de umbral** con **Random Forest** sobre ventanas temporales.
- La mitigación es **simulada**: solo escribe registros y nunca ejecuta acciones de red.

El plan completo, con reglas, contratos de datos y fases, está en [`plan-implementacion-codigo.md`](plan-implementacion-codigo.md).

## Estado del proyecto

Las fases 0 a 6 están ejecutadas. El estado detallado y los acuerdos están en [`docs/seguimiento.md`](docs/seguimiento.md); lo que sigue pendiente (diseño de red en Packet Tracer, anteproyecto) está en [`docs/guia-packet-tracer-y-pendientes.md`](docs/guia-packet-tracer-y-pendientes.md).

Resultados en prueba, con la partición principal **Caso C** (leave-one-attack-out, ambos sentidos), `W = 5 s`, `S = 1 s`:

| Modelo | Sentido | F1 ventana | Latencia | Falsas alertas/h | Tiempo por ventana (media) |
|---|---|---|---|---|---|
| Random Forest | deauth→disas | 0,9973 | 0,262 s | 0 | 7,4 ms |
| Random Forest | disas→deauth | 0,9972 | 1,483 s | 0 | 6,9 ms |
| Línea base (umbral `n_disconn`) | deauth→disas | 1,0000 | 0,262 s | 0 | 3,4 ms |
| Línea base (umbral `n_disconn`) | disas→deauth | 0,9972 | 1,483 s | 0 | 2,5 ms |

El Random Forest **no supera** a la línea base: en AWID3 el ataque es una ráfaga densa y una sola característica ya separa las clases. Cada cifra, con su archivo de evidencia, está en [`docs/trazabilidad-paper.md`](docs/trazabilidad-paper.md); el análisis completo y las limitaciones, en [`docs/resultados.md`](docs/resultados.md). Los tiempos se midieron en un equipo de desarrollo, con un solo proceso y una captura por sentido; no son hardware de sensor.

## Instalación

El desarrollo parte de cero sobre un equipo con **16 GB de RAM** y aproximadamente **500 GB de espacio disponible**. El procesamiento se hace por bloques y por captura; el proyecto no pretende ocupar todo el disco.

Las versiones fijadas en `requirements.txt` se verificaron con **Python 3.13** (las pruebas pasan con 97 casos). Comprobar la versión del equipo:

```bash
python --version
```

Crear el entorno. En Linux o macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

En Windows (PowerShell), activar con `.venv\Scripts\Activate.ps1` en lugar de `source`; o llamar directamente a `.venv\Scripts\python.exe -m pytest -q`.

Si `pip` no encuentra alguna versión exacta para la versión de Python instalada, instala las ocho librerías compatibles, corre `pytest -q` y regenera `requirements.txt` con `pip freeze` filtrado a esas librerías. Registra la versión final en `run_*.json`.

## Datos

El flujo usa **AWID3 en CSV**. No depende de PCAP. PCAP y `tshark` solo se usarían como contingencia si el CSV no contuviera un campo indispensable y el archivo estuviera disponible.

Ver [`data/README.md`](data/README.md). En resumen: copiar las capturas CSV de desautenticación y disociación de AWID3 en `data/raw/`, y definir la sal de anonimización:

```bash
export WIFI_ML_SALT='<una cadena secreta que no se sube al repositorio>'
```

## Cómo ejecutar

Cada paso recibe un archivo de configuración. Un valor `< >` en la configuración es una decisión pendiente y el código se niega a usarlo.

```bash
# Fase 1: inspección de AWID3
python -m src.inspect_data --data configs/data.yaml --discover      # archivos y columnas
python -m src.inspect_data --data configs/data.yaml --max-rows 200000
python -m src.preprocessing --data configs/data.yaml
python -m src.episodes --mode exploratory --data configs/data.yaml --T-provisional <s>

# Fase 2: Gate D (ya congelado). Partición principal: Caso C (leave-one-attack-out), ambos sentidos.
python -m src.split_data --exp configs/experiments/exp_loao_deauth_to_disas.yaml            # vista previa
python -m src.split_data --exp configs/experiments/exp_loao_deauth_to_disas.yaml --freeze
python -m src.episodes --mode definitive --exp configs/experiments/exp_loao_deauth_to_disas.yaml
python -m src.feature_engineering --exp configs/experiments/exp_loao_deauth_to_disas.yaml

# Fases 3 y 4: solo validación
python -m src.baseline --exp configs/experiments/exp_baseline_deauth_to_disas.yaml
python -m src.train --exp configs/experiments/exp_loao_deauth_to_disas.yaml --importance
python -m src.predict --exp configs/experiments/exp_loao_deauth_to_disas.yaml --split val
python -m src.alerts --exp configs/experiments/exp_loao_deauth_to_disas.yaml --split val
python -m src.evaluate --exp configs/experiments/exp_loao_deauth_to_disas.yaml --split val --figures

# Fase 5: prueba, una sola vez y con el árbol git limpio
python -m src.predict --exp configs/experiments/exp_loao_deauth_to_disas.yaml --split test --final
python -m src.alerts --exp configs/experiments/exp_loao_deauth_to_disas.yaml --split test --final
python -m src.evaluate --exp configs/experiments/exp_loao_deauth_to_disas.yaml --split test --final --figures

# Fase 6
python -m src.replay --exp configs/experiments/exp_loao_deauth_to_disas.yaml --split test --final
python -m src.mitigation_simulator --exp configs/experiments/exp_loao_deauth_to_disas.yaml --split test --final
```

Repetir las fases 2 a 6 con el sentido inverso (`exp_loao_disas_to_deauth.yaml`) y con las dos líneas base
(`exp_baseline_deauth_to_disas.yaml`, `exp_baseline_disas_to_deauth.yaml`; ellas usan `src.baseline` en
lugar de `src.train`). Cada etapa `--final` se ejecuta **una sola vez por experimento** y exige el árbol git
limpio; una segunda ejecución se rechaza. Los experimentos de sensibilidad (`role: sensitivity`:
`exp_rf_sens_W3.yaml`, `exp_rf_sens_W10.yaml`, `exp_loao_deauth_to_disas_no_rc.yaml`) solo llegan hasta
la validación. El Caso B se descartó (geometría de AWID3); ver `docs/reporte-gate-d.md` 2.1.

### Figuras de evaluación sin repetir la prueba

Para generar las figuras (curva PR y línea temporal) a partir de resultados **ya guardados**, sin tocar
`--final` (R6):

```bash
python -m scripts.figuras_evaluacion --exp configs/experiments/exp_loao_deauth_to_disas.yaml --split test
```

Las figuras salen en `docs/figuras/<experimento>/figures/`. El script solo lee `results/`.

### Pruebas

```bash
pytest -q          # 97 pruebas sobre datos sintéticos en formato interno; deben quedar en verde
```

## Diseño de red

La topología se entrega como diseño de referencia, no como una simulación funcional de ataques 802.11. El diagrama editable está en [`docs/diagramas/arquitectura.mmd`](docs/diagramas/arquitectura.mmd); las instrucciones de visualización y exportación están en [`docs/diagramas/README.md`](docs/diagramas/README.md).

## Estructura

```text
configs/    configuración de datos, características, particiones y experimentos
docs/       arquitectura, modelo de amenazas, respuestas sobre AWID3, protocolo, decisiones,
            resultados y trazabilidad
docs/paper/     artículo (LaTeX, versionado)
docs/figuras/   figuras de evaluación generadas desde resultados guardados
data/       datos (no se suben)
src/        código; un módulo por etapa
scripts/    análisis de apoyo (Fase 1) y figuras de evaluación (solo lectura)
tests/      pruebas sobre datos sintéticos en formato interno
models/     modelos entrenados (no se suben)
results/    resultados por experimento (no se suben salvo resúmenes)
```

Los PDF de entregas anteriores están en `docs/Entregas_pasadas/` y no se versionan.

## Reproducibilidad

- Cada ejecución guarda `results/<exp_id>/run_<etapa>.json` con configuración, commit, semilla, partición y entorno.
- `models/<exp_id>/metadata.json` contiene todo lo necesario para repetir las predicciones sin reentrenar.
- La prueba solo se toca con `--final`, una vez por etapa.

## Referencia del conjunto de datos

E. Chatzoglou, G. Kambourakis y C. Kolias, "Empirical Evaluation of Attacks Against IEEE 802.11 Enterprise Networks: The AWID3 Dataset", *IEEE Access*, vol. 9, pp. 34188–34205, 2021.
