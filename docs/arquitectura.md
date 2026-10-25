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

- La VLAN 30 no accede a las VLAN 10 ni 20. El acceso a la VLAN 20 se restringe con ACL a las comunicaciones administrativas autorizadas.
- PMF y la migración a IEEE 802.11ax son decisiones independientes.
- Se asume que los clientes principales soportan 5 GHz; los de 2.4 GHz quedan fuera del perfil inicial.

## Relación con el código

| Componente | Representación en la prueba de concepto |
|---|---|
| Sensor inalámbrico | registros de AWID3 (`data/raw`) |
| Servidor de análisis | `src/feature_engineering.py`, `src/predict.py`, `src/alerts.py` |
| Operación en línea | `src/replay.py` (reproducción temporal) |
| Respuesta | `src/mitigation_simulator.py` (solo registros) |
