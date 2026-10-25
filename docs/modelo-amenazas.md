# Modelo de amenazas

## Ataques en el alcance

| Ataque | Mecanismo | Núcleo del estudio |
|---|---|---|
| Desautenticación de difusión | tramas de gestión subtipo 12 hacia `ff:ff:ff:ff:ff:ff`, suplantando al AP | sí |
| Disociación tipo *flood* | tramas de gestión subtipo 10 en ráfaga | sí |
| Desautenticación dirigida | subtipo 12 hacia un cliente concreto | solo si AWID3 la etiqueta por separado |

## Supuestos sobre el atacante

- Transmite tramas de gestión falsificadas en el canal del AP.
- Puede usar la dirección MAC del AP o de un cliente legítimo. Por eso **nunca** se aísla una fuente por su MAC.
- No necesita asociarse a la red.

## Qué hace y qué no hace el detector

- Detecta, lo antes posible después de su inicio, ventanas con comportamiento compatible con un ataque de desconexión.
- No predice el ataque antes de su primera trama.
- No sustituye a PMF: aporta visibilidad, registro y apoyo a la decisión cuando PMF es opcional o hay clientes legacy.
- No distingue entre desautenticación y disociación en sus salidas (objetivo binario, R11).

## Contexto del conjunto de datos

AWID3 se capturó en una red IEEE 802.1X/EAP con PMF activo, según la documentación del conjunto. El escenario de la pequeña empresa (WPA2/WPA3-Personal) es un dominio distinto; la diferencia se declara como limitación.

## Respuesta simulada

Ver `src/mitigation_simulator.py` y la sección 8.9 del plan. Las acciones de cambio de canal y localización por RSSI se registran como `solo_diseno` y no se ejecutan.
