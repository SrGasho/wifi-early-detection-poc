# wifi-early-detection-poc

Prueba de concepto para la **detección temprana de ataques de desautenticación y disociación** en una red Wi-Fi de referencia para pequeña empresa, mediante aprendizaje automático.

**Autor:** Juan David Quiroga — Proyecto Curricular de Ingeniería de Sistemas, Universidad Distrital Francisco José de Caldas.

## Alcance

- Detecta ventanas de tráfico de gestión compatibles con un ataque de desconexión **después de su inicio** y mide la latencia hasta la alerta. No predice el ataque antes de su primera trama.
- Usa **AWID3** como única fuente de datos. No hay validación en hardware físico.
- Compara una **línea base de umbral** con **Random Forest** sobre ventanas temporales.
- La mitigación es **simulada**: solo escribe registros y nunca ejecuta acciones de red.

El plan completo, con reglas, contratos de datos y fases, está en [`plan-implementacion-codigo.md`](plan-implementacion-codigo.md).

## Instalación

El desarrollo parte de cero sobre un equipo con **16 GB de RAM** y aproximadamente **500 GB de espacio disponible**. El procesamiento se hace por bloques y por captura; el proyecto no pretende ocupar todo el disco.

Antes de instalar, comprobar la versión del equipo:

```bash
python3 --version
```

Luego crear el entorno:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Si `pip` no encuentra alguna versión exacta para la versión de Python instalada, instala las ocho librerías compatibles, corre `pytest -q` y regenera `requirements.txt` con `pip freeze` filtrado a esas librerías. Registra la versión final en `run_*.json`.

## Datos

La primera versión usará **AWID3 en CSV**. El flujo principal no depende de PCAP. PCAP y `tshark` solo se usarán como contingencia si el CSV no contiene un campo indispensable y el archivo está disponible.

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

# Fase 2: Gate D (completar los < > de configs/experiments/ y docs/decisiones.md)
python -m src.split_data --exp configs/experiments/exp_rf.yaml            # vista previa
python -m src.split_data --exp configs/experiments/exp_rf.yaml --freeze
python -m src.episodes --mode definitive --exp configs/experiments/exp_rf.yaml
python -m src.feature_engineering --exp configs/experiments/exp_rf.yaml

# Fases 3 y 4: solo validación
python -m src.baseline --exp configs/experiments/exp_baseline.yaml
python -m src.train --exp configs/experiments/exp_rf.yaml --importance
python -m src.predict --exp configs/experiments/exp_rf.yaml --split val
python -m src.alerts --exp configs/experiments/exp_rf.yaml --split val
python -m src.evaluate --exp configs/experiments/exp_rf.yaml --split val --figures

# Fase 5: prueba, una sola vez y con el árbol git limpio
python -m src.predict --exp configs/experiments/exp_rf.yaml --split test --final
python -m src.alerts --exp configs/experiments/exp_rf.yaml --split test --final
python -m src.evaluate --exp configs/experiments/exp_rf.yaml --split test --final --figures

# Fase 6
python -m src.replay --exp configs/experiments/exp_rf.yaml --split test --final
python -m src.mitigation_simulator --exp configs/experiments/exp_rf.yaml --split test --final
```

Los mismos pasos de las fases 3 a 6 se ejecutan con `exp_baseline.yaml`. Los experimentos de sensibilidad (`role: sensitivity`) solo llegan hasta la validación.

## Diseño de red

La topología se entrega como diseño de referencia, no como una simulación funcional de ataques 802.11. El diagrama editable está en [`docs/diagramas/arquitectura.mmd`](docs/diagramas/arquitectura.mmd); las instrucciones de visualización y exportación están en [`docs/diagramas/README.md`](docs/diagramas/README.md).

## Estructura

```text
configs/    configuración de datos, características, particiones y experimentos
docs/       arquitectura, modelo de amenazas, respuestas sobre AWID3, protocolo y decisiones
data/       datos (no se suben)
src/        código; un módulo por etapa
tests/      pruebas sobre datos sintéticos en formato interno
models/     modelos entrenados (no se suben)
results/    resultados por experimento (no se suben salvo resúmenes)
```

## Reproducibilidad

- Cada ejecución guarda `results/<exp_id>/run_<etapa>.json` con configuración, commit, semilla, partición y entorno.
- `models/<exp_id>/metadata.json` contiene todo lo necesario para repetir las predicciones sin reentrenar.
- La prueba solo se toca con `--final`, una vez por etapa.

## Referencia del conjunto de datos

E. Chatzoglou, G. Kambourakis y C. Kolias, "Empirical Evaluation of Attacks Against IEEE 802.11 Enterprise Networks: The AWID3 Dataset", *IEEE Access*, vol. 9, pp. 34188–34205, 2021.
