# Arquitectura de la red de referencia

Arquitectura de **diseño** para una pequeña empresa de 5 a 10 usuarios. No se desplegó en hardware: la prueba de concepto se valida con AWID3 y reproducción temporal.

## Topología

```text
+----------------------+
| 5 a 10 clientes      |
| SSID corporativo     |
+----------+-----------+
           ^
           | IEEE 802.11ac / 5 GHz (enlace bidireccional)
           v
+----------+-----------+   captura pasiva del aire   +--------------------+
| Punto de acceso      | . . . . . . . . . . . . . > | Sensor inalámbrico |
| SSID corporativo     |  mismo canal / modo monitor | modo monitor       |
| SSID invitados       |                             +---------+----------+
+----------+-----------+                                       |
           | troncal 802.1Q (VLAN 10, 20, 30)                  | acceso VLAN 20
           v                                                   v
+----------+-----------+        acceso VLAN 20       +---------+----------+
| Switch 802.1Q        +---------------------------->| Servidor de        |
|                      |                             | análisis, ML,      |
+----------+-----------+                             | alertas, registro  |
           | troncal 802.1Q (VLAN 10, 20, 30)        +--------------------+
           v
+----------+-----------+
| Router o gateway     |
| router-on-a-stick    |
| DHCP / DNS / NAT     |
| inter-VLAN y ACL     |
+----------+-----------+
           v
        Internet
```

La línea punteada representa solo la captura pasiva: los clientes no se asocian al sensor.

## Parámetros de diseño (no son mediciones)

| Elemento | Valor |
|---|---|
| Estándar | IEEE 802.11ac |
| Banda / canal / ancho | 5 GHz / canal 36 / 40 MHz |
| VLAN 10 | corporativa, `192.168.10.0/24` |
| VLAN 20 | gestión del AP, sensor y servidor, `192.168.20.0/24` |
| VLAN 30 | invitados, `192.168.30.0/24`, solo salida a Internet |
| Seguridad de referencia | WPA2-Personal con PMF opcional o clientes legacy |
| Seguridad futura | WPA3-Personal con PMF requerido |
| Capacidad estimada | ~400 Mbps físicos, ~200 Mbps útiles, ~20 Mbps por usuario con 10 activos |

- La VLAN 30 no accede a las VLAN 10 ni 20. El acceso a la VLAN 20 se restringe con ACL a las comunicaciones administrativas autorizadas. En la topología verificada, solo la estación administrativa de la VLAN 10 (`PC1`) alcanza la VLAN 20.
- PMF y la migración a IEEE 802.11ax son decisiones independientes.
- Se asume que los clientes principales soportan 5 GHz; los de 2.4 GHz quedan fuera del perfil inicial.

## Canal del sensor al servidor (decisión de diseño, no implementada)

- El sensor calcula las características de cada ventana con `compute_window_features` y envía **un mensaje por ventana cerrada** (uno por paso `S = 1 s`), no las tramas.
- Formato: un objeto JSON por línea, sobre una conexión TCP persistente que inicia el sensor hacia el servidor, con un puerto no privilegiado configurable (por ejemplo, el 5140).
- Ambos equipos están en la VLAN 20: el tráfico no cruza el router ni sus ACL.
- Contenido: versión del formato, identificador neutro del sensor, número de ventana, instante de cierre, `W`, `S` y las 11 características del perfil. Sin direcciones MAC, etiquetas ni tipo de ataque (R2, R11).
- Tamaño de un mensaje de ejemplo, con una ventana real: unos 310 bytes, ~2,5 kbit/s a un mensaje por segundo (cifra en `docs/trazabilidad-paper.md`).
- En un despliegue real: TLS con autenticación de ambos extremos, porque un mensaje falso podría provocar o suprimir alertas.
- Límite: la lista de clientes de la mitigación simulada necesita las observaciones de (re)asociación, que este formato no incluye.

## Configuración inalámbrica objetivo (supuesto de diseño, no verificado)

- Dos SSID: corporativo (VLAN 10) e invitados (VLAN 30), ambos con WPA2-Personal, AES-CCMP, claves precompartidas distintas y WPS desactivado.
- PMF (IEEE 802.11w) en modo opcional; gestión del punto de acceso en la VLAN 20.
- Con PMF opcional, un cliente que no las negocia queda expuesto a tramas de desautenticación y disociación falsificadas; ese hueco es el que cubre el detector.
- WPA3-Personal con PMF requerido es la evolución futura y elimina los clientes heredados.
- Cisco Packet Tracer no permite configurar WPA2 ni PMF, así que no se verificó.

## Verificación a nivel lógico (Cisco Packet Tracer 9.0.1)

La topología se construyó y se probó en Packet Tracer (`docs/diagramas/topologia-empresa.pkt`; resultados en `docs/diagramas/pruebas-topologia.md`). Se verificó con 10 pruebas de ping:

- VLAN 10, 20 y 30 con troncales 802.1Q y router-on-a-stick.
- ACL: los invitados no llegan a las VLAN 10 ni 20 y sí a su puerta de enlace y a «Internet»; solo `PC1` llega a la VLAN 20.
- NAT con sobrecarga hacia un router `ISP` que representa Internet.

Lo que **no** se verificó, y sigue siendo supuesto de diseño: el enlace 802.11ac, el canal 36 y los 40 MHz, WPA2 con PMF opcional (el AP de Packet Tracer queda abierto), el SSID de invitados con su mapeo a la VLAN 30, la captura pasiva del sensor en modo monitor (el sensor es un equipo cableado), DHCP y DNS (todas las IP son estáticas), y la IP de gestión del AP (el AP de Packet Tracer no admite dirección IP). La ACL de Packet Tracer no tiene estado.

## Relación con el código

| Componente | Representación en la prueba de concepto |
|---|---|
| Sensor inalámbrico | registros de AWID3 (`data/raw`) |
| Servidor de análisis | `src/feature_engineering.py`, `src/predict.py`, `src/alerts.py` |
| Operación en línea | `src/replay.py` (reproducción temporal) |
| Respuesta | `src/mitigation_simulator.py` (solo registros) |
