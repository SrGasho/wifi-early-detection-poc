# Datos

Esta carpeta no se sube al repositorio, salvo este archivo.

## Cómo obtener AWID3

Fuente oficial del proyecto AWID: [Aegean Wi-Fi Intrusion Dataset](https://icsdweb.aegean.gr/awid/).

Página oficial de AWID3: [The AWID3 Dataset](https://icsdweb.aegean.gr/awid/awid3).

La página oficial indica que AWID3 se distribuye como:

- Archivos **PCAP** originales.
- **AWID3-CSV**, una extracción de características en CSV complementaria a los PCAP.

El acceso a los datasets se solicita mediante el flujo de registro de la página oficial. No se debe descargar el dataset desde repositorios de terceros ni subirlo al repositorio del proyecto.

Después de obtener el acceso:

1. Descargar la versión **AWID3-CSV**.
2. Copiar únicamente las capturas o archivos correspondientes a desautenticación y disociación dentro de `data/raw/`, conservando la estructura original.
3. No modificar los archivos crudos.
4. Ejecutar:

   ```bash
   python -m src.inspect_data --data configs/data.yaml --discover
   ```

5. Con base en el informe generado, completar en `configs/data.yaml`:
   - patrones de `captures`;
   - nombres reales de las columnas;
   - etiquetas de desautenticación, disociación y tráfico normal.
6. Usar identificadores neutros como `cap_a` y `cap_b`; el tipo de ataque debe provenir de la etiqueta y no del nombre del archivo (R11).

La primera implementación trabajará con CSV. Los PCAP solo se usarán como contingencia si un campo indispensable no aparece en el CSV y el acceso a los PCAP está disponible.

Cita del conjunto de datos: E. Chatzoglou, G. Kambourakis y C. Kolias, "Empirical Evaluation of Attacks Against IEEE 802.11 Enterprise Networks: The AWID3 Dataset", *IEEE Access*, vol. 9, pp. 34188–34205, 2021.

## Subcarpetas

| Carpeta | Contenido | Quién escribe |
|---|---|---|
| `raw/` | AWID3 tal como se descarga. **Nunca se modifica.** | el autor |
| `interim/` | tramas normalizadas y anonimizadas, episodios | `preprocessing`, `episodes` |
| `processed/` | ventanas con características | `feature_engineering` |

## Anonimización

Las direcciones MAC se reemplazan por `HMAC-SHA256(sal, mac)` truncado. La sal se define en la variable de entorno `WIFI_ML_SALT` y no se guarda en el repositorio. Las MAC originales solo existen en `raw/`.
