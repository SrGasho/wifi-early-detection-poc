# Guía: topología de la red en Cisco Packet Tracer y pendientes de diseño e implementación

Este documento tiene dos partes:

1. **Guía paso a paso** para construir en Cisco Packet Tracer la topología del paper (sección de diseño), configurarla y comprobar que las VLAN y la ACL funcionan. Está pensada para quien nunca ha usado el programa.
2. **Lista de pendientes** de la sección de diseño e implementación del paper, con qué hace falta, cómo cerrarlo y en qué orden.

> Nota sobre el alcance. Packet Tracer simula la red a nivel lógico: switches, VLAN, router y ACL.
> No simula el enlace de radio 802.11ac ni el modo monitor del sensor. Por eso la topología se usa como
> **diseño verificado a nivel lógico**, no como prueba de la capa inalámbrica.

---

## Parte 1. Guía paso a paso en Packet Tracer

### 1.1 Qué vas a construir

La topología es la de la sección de diseño del paper:

| Elemento | Dispositivo en Packet Tracer | Función |
|---|---|---|
| Router de borde | Router 1941 | Enruta entre VLAN (router-on-a-stick) y aplica la ACL |
| Switch | Switch 2960 | Separa las VLAN y transporta los troncales 802.1Q |
| Access point | Access Point-PT | Representa el AP de la red corporativa |
| PC corporativa (x3) | PC-PT | Clientes en la VLAN 10 |
| Servidor de gestión | Server-PT | Servidor de análisis, en la VLAN 20 |
| Sensor | PC-PT (renombrado `SENSOR`) | Sensor de monitoreo, en la VLAN 20 |
| PC de invitados | PC-PT | Cliente de la VLAN 30 (sin acceso a VLAN 10 ni 20) |

**Plan de VLAN e IP** (el mismo que el paper):

| VLAN | Nombre | Red | Gateway (router) | Dispositivos |
|---|---|---|---|---|
| 10 | CORPORATIVA | 192.168.10.0/24 | 192.168.10.1 | PC1 .10, PC2 .11, PC3 .12 |
| 20 | GESTION | 192.168.20.0/24 | 192.168.20.1 | Servidor .20, sensor .10, AP .2 |
| 30 | INVITADOS | 192.168.30.0/24 | 192.168.30.1 | PC-INV .10 |

**Plan de puertos del switch:**

| Puerto | Tipo | VLAN | Conectado a |
|---|---|---|---|
| Fa0/1 | Troncal | 10, 20, 30 | Router (Gi0/0) |
| Fa0/2 | Troncal | 10, 20, 30 | Access point |
| Fa0/3 y Fa0/4 | Acceso | 10 | PC1 y PC2 |
| Fa0/5 | Acceso | 20 | Servidor |
| Fa0/6 | Acceso | 20 | Sensor |
| Fa0/7 | Acceso | 30 | PC de invitados |

Tu PC3 (VLAN 10) va en Fa0/8, con el mismo comando de acceso que Fa0/3.

### 1.2 Conceptos mínimos (lee esto antes de empezar)

- **VLAN:** una red lógica separada dentro del mismo switch. Los equipos de VLAN 10 no se ven con los de VLAN 20 salvo que pase por el router.
- **Puerto de acceso:** un puerto que pertenece a una sola VLAN. Lo usan los PC, el servidor y el sensor.
- **Puerto troncal (trunk):** un puerto que transporta varias VLAN a la vez, etiquetándolas (802.1Q). Lo usan los enlaces entre switch y router, y entre switch y AP.
- **Router-on-a-stick:** un solo enlace físico desde el router al switch (troncal), con una subinterfaz por VLAN. Cada subinterfaz es la puerta de enlace de su VLAN.
- **ACL (lista de control de acceso):** reglas que el router aplica para permitir o bloquear tráfico entre redes.

### 1.3 Instalar Packet Tracer

1. Crea una cuenta gratuita en **Cisco Networking Academy** (netacad.com).
2. Descarga **Cisco Packet Tracer** desde esa cuenta. Elige la versión para tu sistema operativo.
3. Instálalo y ábrelo. Verás una pantalla de trabajo en blanco con una barra de herramientas y, a la izquierda, la lista de dispositivos.

> Los nombres de los menús y de algunos dispositivos pueden variar según la versión. Si algo no
> coincide, busca por nombre en la lista de dispositivos o en la ayuda del programa.

### 1.4 Colocar los dispositivos

1. En la parte inferior izquierda, la lista muestra categorías de dispositivos. Haz clic en la categoría **Network Devices** y luego en **Switches**.
2. Arrastra un **2960** al área de trabajo. Este será el switch.
3. En **Routers**, arrastra un **1941**.
4. En **Wireless Devices**, arrastra un **Access Point-PT**.
5. En **End Devices**, arrastra cuatro **PC-PT** (PC1, PC2, PC3 y PC de invitados) y un **Server-PT**.
6. Arrastra un quinto **PC-PT** para el sensor.

Para cambiar el nombre de un dispositivo, haz clic sobre él y, en la pestaña **Config**, cambia el campo **Display Name**. Pon nombres claros: `R-EDGE`, `SW-CORP`, `AP-CORP`, `PC1`, `PC2`, `PC3`, `PC-INV`, `SERVIDOR`, `SENSOR`.

### 1.5 Conectar los cables

En la parte inferior izquierda, busca **Connections** (el icono de rayo o de cable). Verás varios tipos de cable.

- Usa **Copper Straight-Through** (cable recto) para conectar router, switch, AP y PC.
- Para conectar dos dispositivos, haz clic en el primero, elige el puerto, haz clic en el segundo y elige su puerto.

Conexiones a hacer:

| Desde | Puerto | Hacia | Puerto |
|---|---|---|---|
| R-EDGE | GigabitEthernet0/0 | SW-CORP | FastEthernet0/1 |
| SW-CORP | FastEthernet0/2 | AP-CORP | Ethernet (el puerto cableado del AP) |
| SW-CORP | FastEthernet0/3 | PC1 | FastEthernet0 |
| SW-CORP | FastEthernet0/4 | PC2 | FastEthernet0 |
| SW-CORP | FastEthernet0/5 | SERVIDOR | FastEthernet0 |
| SW-CORP | FastEthernet0/6 | SENSOR | FastEthernet0 |
| SW-CORP | FastEthernet0/7 | PC-INV | FastEthernet0 |
| SW-CORP | FastEthernet0/8 | PC3 | FastEthernet0 |

Cuando termines, los enlaces deben mostrar un punto verde en cada extremo. Si alguno está naranja o rojo, espera unos segundos: el puerto está negociando. Si sigue sin ponerse verde, revisa el cable y el puerto.

### 1.6 Configurar el switch por línea de comandos (CLI)

1. Haz clic en **SW-CORP** y abre la pestaña **CLI**.
2. Pulsa Enter. Si aparece `Would you like to enter the initial configuration dialog?`, escribe `no`.
3. Escribe los comandos siguientes uno por uno. Cada línea se confirma con Enter.

```text
enable
configure terminal
hostname SW-CORP

vlan 10
 name CORPORATIVA
vlan 20
 name GESTION
vlan 30
 name INVITADOS

interface FastEthernet0/1
 description Troncal-Router
 switchport mode trunk
 switchport trunk allowed vlan 10,20,30

interface FastEthernet0/2
 description Troncal-AP
 switchport mode trunk
 switchport trunk allowed vlan 10,20,30

interface range FastEthernet0/3 - 4
 switchport mode access
 switchport access vlan 10

interface FastEthernet0/5
 description Servidor-GESTION
 switchport mode access
 switchport access vlan 20

interface FastEthernet0/6
 description Sensor-GESTION
 switchport mode access
 switchport access vlan 20

interface FastEthernet0/7
 description Invitados
 switchport mode access
 switchport access vlan 30

interface FastEthernet0/8
 description PC3-CORP
 switchport mode access
 switchport access vlan 10

end
write memory
```

**Qué significa cada bloque:**
- `vlan 10` crea la VLAN y `name` le pone un nombre legible.
- `switchport mode trunk` marca un puerto como troncal. `allowed vlan` dice qué VLAN puede transportar.
- `switchport mode access` y `switchport access vlan` asignan un puerto a una sola VLAN.
- `write memory` guarda la configuración para que no se pierda.

**Comprobar:** escribe `show vlan brief` y verifica que las VLAN 10, 20 y 30 aparecen con los puertos esperados.

### 1.7 Configurar el router (router-on-a-stick y ACL)

1. Haz clic en **R-EDGE**, abre la pestaña **CLI** y pulsa Enter (si pregunta por la configuración inicial, responde `no`).
2. Escribe:

```text
enable
configure terminal
hostname R-EDGE

interface GigabitEthernet0/0
 no shutdown

interface GigabitEthernet0/0.10
 description Gateway-CORPORATIVA
 encapsulation dot1Q 10
 ip address 192.168.10.1 255.255.255.0

interface GigabitEthernet0/0.20
 description Gateway-GESTION
 encapsulation dot1Q 20
 ip address 192.168.20.1 255.255.255.0

interface GigabitEthernet0/0.30
 description Gateway-INVITADOS
 encapsulation dot1Q 30
 ip address 192.168.30.1 255.255.255.0

ip access-list extended ACL-INVITADOS
 deny ip 192.168.30.0 0.0.0.255 192.168.10.0 0.0.0.255
 deny ip 192.168.30.0 0.0.0.255 192.168.20.0 0.0.0.255
 permit ip any any

interface GigabitEthernet0/0.30
 ip access-group ACL-INVITADOS in

end
write memory
```

**Qué significa cada bloque:**
- `no shutdown` enciende el puerto físico. Sin esto, las subinterfaces no funcionan.
- `encapsulation dot1Q 10` dice que la subinterfaz procesa el tráfico etiquetado con VLAN 10.
- `ip address` asigna la puerta de enlace de cada VLAN.
- La ACL bloquea lo que sale de la VLAN de invitados hacia las VLAN 10 y 20. El `permit ip any any` final deja pasar el resto.
- `ip access-group ... in` aplica la ACL al tráfico que **entra** al router desde invitados.

> Limitación para el paper: la ACL de Packet Tracer no tiene estado. Eso significa que una respuesta que
> regresa desde VLAN 10 hacia invitados puede pasar si alguien ya inició la conexión. El diseño real
> debe tener una regla que permita solo las respuestas (`established`) o un firewall con estado. Esto
> debe quedar escrito en el paper.

**Comprobar:** escribe `show ip interface brief` y verifica que las tres subinterfaces están `up/up`. Escribe `show access-lists` para ver la ACL.

### 1.8 Configurar las PC y el servidor

En cada equipo final, haz clic sobre él, abre **Desktop** y luego **IP Configuration**. Elige **Static** y escribe:

| Equipo | IP | Máscara | Gateway |
|---|---|---|---|
| PC1 | 192.168.10.10 | 255.255.255.0 | 192.168.10.1 |
| PC2 | 192.168.10.11 | 255.255.255.0 | 192.168.10.1 |
| PC3 | 192.168.10.12 | 255.255.255.0 | 192.168.10.1 |
| SERVIDOR | 192.168.20.20 | 255.255.255.0 | 192.168.20.1 |
| SENSOR | 192.168.20.10 | 255.255.255.0 | 192.168.20.1 |
| PC-INV | 192.168.30.10 | 255.255.255.0 | 192.168.30.1 |

Para probar la conectividad, haz clic en un PC, abre **Desktop** y luego **Command Prompt**. Escribe `ping` seguido de la IP destino.

### 1.9 Configurar el access point

1. Haz clic en **AP-CORP** y abre la pestaña **Config**.
2. En la sección de puertos cableados (Ethernet), asigna la IP de gestión `192.168.20.2` con máscara `255.255.255.0` y gateway `192.168.20.1`.
3. En la sección inalámbrica, pon el **SSID** `EMPRESA` y, si la opción existe, selecciona **WPA2-PSK** con una contraseña de prueba.

> Limitación de Packet Tracer: el AP-PT es un modelo simplificado. Puede que no acepte etiquetado
> 802.1Q en su puerto cableado. Si el enlace troncal con el AP no funciona, documenta el AP como
> acceso a la VLAN 20 y menciónalo como limitación en el paper. No intentes ajustarlo para que
> "parezca" correcto.

Para la prueba inalámbrica, agrega una tarjeta inalámbrica a un PC (apaga el equipo, cambia la tarjeta por una inalámbrica del catálogo y enciéndelo de nuevo). Luego asigna el SSID `EMPRESA` en su pestaña de configuración.

### 1.10 Pruebas que debes capturar

Estas pruebas son el resultado que el paper necesita. Haz cada una desde el PC indicado y guarda una captura de pantalla.

| Prueba | Desde | Comando | Resultado esperado |
|---|---|---|---|
| Dentro de VLAN 10 | PC1 | `ping 192.168.10.11` | Respuesta |
| VLAN 10 hacia gestión | PC1 | `ping 192.168.20.20` | Respuesta (la ACL no bloquea esta dirección) |
| Invitados hacia corporativa | PC-INV | `ping 192.168.10.10` | **Sin respuesta** (la ACL bloquea) |
| Invitados hacia gestión | PC-INV | `ping 192.168.20.20` | **Sin respuesta** (la ACL bloquea) |
| Invitados a su gateway | PC-INV | `ping 192.168.30.1` | Respuesta |
| Sensor a servidor | SENSOR | `ping 192.168.20.20` | Respuesta (misma VLAN) |

Si una prueba falla, revisa en este orden: el cable (color verde), la VLAN del puerto (`show vlan brief`), la subinterfaz del router (`show ip interface brief`) y la ruta de la PC (la puerta de enlace).

### 1.11 Guardar y exportar la topología

1. Guarda el proyecto: **File** y luego **Save As**. Guárdalo como `docs/diagramas/topologia-empresa.pkt` dentro del repositorio. Así el archivo queda versionado.
2. Para la figura del paper, busca en el menú la opción de exportar o guardar como imagen. Si tu versión no la tiene, toma una captura de pantalla a la topología completa, con todos los nombres visibles. Guárdala en alta resolución (300 dpi o más) en `docs/diagramas/topologia-empresa.png`.
3. Si el paper requiere vector (PDF), convierte la imagen con una herramienta como Inkscape o Draw.io. Esto es más nítido en una publicación IEEE.

### 1.12 Errores frecuentes

| Síntoma | Causa probable | Qué revisar |
|---|---|---|
| El enlace está naranja y no se pone verde | El puerto aún negocia o el cable es incorrecto | Espera 30 s, luego cambia el cable |
| Un PC no responde a nadie | La puerta de enlace está mal o el puerto es de otra VLAN | `show vlan brief`, IP del PC |
| VLAN 10 no llega a VLAN 20 | El router no tiene la subinterfaz o no tiene `encapsulation` | `show ip interface brief` |
| Invitados llegan a VLAN 10 | La ACL no está aplicada en la dirección `in` | `show access-lists` y el `ip access-group` |
| Todo falla tras reiniciar | No guardaste la configuración | Escribe `write memory` después de cada bloque |

---

## Parte 2. Pendientes de diseño e implementación

Cada pendiente indica: qué es, por qué importa, cómo cerrarlo y el orden sugerido. Los números son para referirte a ellos.

### 2.1 Pendientes de diseño

**D1. Figura de topología (Packet Tracer).**
- *Qué falta:* la figura de la arquitectura en el paper. Hoy no hay ninguna figura.
- *Cómo cerrar:* sigue la Parte 1. Luego incluye la imagen en la sección de diseño con `\includegraphics` y una leyenda. Verifica que los nombres de la figura coincidan con los del texto.
- *Dependencia:* ninguna. Es el primer paso.

**D2. Figura del pipeline CRISP-DM.**
- *Qué falta:* un diagrama del flujo que muestre las fases y los módulos.
- *Cómo cerrar:* en Draw.io, dibuja las seis fases (comprensión del contexto, comprensión de datos, preparación, modelado, evaluación, despliegue) con los módulos de la tabla IV del paper. Exporta a PDF vectorial.
- *Dependencia:* ninguna.

**D3. Tabla de VLAN e IP en el paper.**
- *Qué falta:* hoy el paper describe las VLAN en prosa. La tabla de la Parte 1.1 es más clara.
- *Cómo cerrar:* agrega una tabla en la sección de diseño con las mismas columnas (VLAN, nombre, red, gateway, dispositivos). Son datos que ya están en el paper, solo cambia la forma.
- *Dependencia:* D1 (para que coincidan).

**D4. Decidir si la VLAN 30 se implementa.**
- *Qué falta:* el paper dice "si se implementa" la VLAN de invitados. Un paper no puede dejar eso abierto si la figura la muestra.
- *Cómo cerrar:* decide sí o no. Si es sí, la figura y la prueba del paso 1.10 la incluyen. Si es no, quita la VLAN 30 del paper y de la guía.
- *Dependencia:* D1.

**D5. Cómo transmite datos el sensor al servidor.**
- *Qué falta:* el paper dice que el sensor "reenviará registros o características al servidor", pero no define el canal (puerto, protocolo, formato).
- *Cómo cerrar:* define en el paper el puerto y el formato (por ejemplo, un JSON por ventana sobre TCP), y deja claro que en Packet Tracer el enlace es solo lógico.
- *Dependencia:* D1.

**D6. Configuración de seguridad inalámbrica.**
- *Qué falta:* el paper menciona WPA2-Personal con PMF opcional, pero no lo define en el diseño. Packet Tracer no valida PMF.
- *Cómo cerrar:* en el paper, escribe la configuración objetivo (WPA2-PSK, PMF opcional) como decisión de diseño y aclara que Packet Tracer no la verifica.
- *Dependencia:* ninguna.

**D7. Fuente de la capacidad de 200 Mbps.**
- *Qué falta:* el paper da una estimación (400 Mbps físicos, 50 % útil, 200 Mbps) sin fuente.
- *Cómo cerrar:* cita una referencia para la tasa física de 802.11ac en 40 MHz y 2x2, o márcala explícitamente como supuesto de planificación. Hoy el texto ya dice que es una estimación, así que es un cambio menor.
- *Dependencia:* ninguna.

**D8. Requisitos y criterios de aceptación.**
- *Qué falta:* los criterios (latencia ≤ 2 s, ≤ 1 falsa alerta por hora, F1 ≥ 0,90) están en el paper como propuesta del autor, redactados después de ver resultados preliminares.
- *Cómo cerrar:* confirmar o cambiar los valores, y registrarlos en `docs/decisiones.md` con su fecha. Si se confirman después de ver los resultados, el paper debe seguir diciendo que son de diseño y no previos.
- *Dependencia:* ninguna, pero hay que decidirlo antes de escribir la conclusión.

### 2.2 Pendientes de implementación y evaluación

**I1. Mitigación simulada (fase 6 del plan) y objetivo 3 del anteproyecto.**
- *Qué falta:* el paso de mitigación simulada no se ejecutó. El paper lo marca como pendiente.
- *Cómo cerrar:* hay dos opciones.
  - (a) Ejecutar una versión mínima de `mitigation_simulator`, que escriba un registro de decisiones sin enviar tramas. Requiere el paso de replay (I2).
  - (b) Reformular el objetivo 3 como diseño de referencia, sin simulación ejecutada, y ajustar el anteproyecto.
- *Dependencia:* decisión tuya. Es la pieza que más cambia el alcance.

**I2. Replay y medición de latencia de procesamiento.**
- *Qué falta:* el paper dice que el tiempo de procesamiento por ventana y la tasa de entrada no se midieron.
- *Cómo cerrar:* si decides I1 (a), implementa el replay sobre las tramas en orden temporal y mide el tiempo entre la trama y la alerta. Si decides (b), deja el texto como está y quita la mención de latencia de procesamiento de la tabla de protocolo.
- *Dependencia:* I1.

**I3. Figuras de evaluación.**
- *Qué falta:* el paper no tiene figuras de resultados. `evaluate --figures` funciona sobre validación. Para la prueba, la guarda R6 bloquea volver a correr `--final`.
- *Cómo cerrar:* escribir un script que lea los archivos ya guardados (`eval_windows_test.parquet`, `metrics_*`) y genere las figuras sin volver a ejecutar la prueba. Así no se toca R6. Documenta en el script que solo lee resultados ya generados.
- *Dependencia:* ninguna.

**I4. Verificar las citas bibliográficas.**
- *Qué falta:* las diez referencias están escritas, pero no se verificaron una por una (autores, año, volumen, páginas, DOI).
- *Cómo cerrar:* abre cada DOI o la página de la revista y compara. En particular revisa `kolias2016`, `mishra2019`, `zhen2025` y `chatzoglou2021`.
- *Dependencia:* ninguna.

**I5. Compilar el paper en formato IEEEtran.**
- *Qué falta:* no se pudo compilar porque `pdflatex` no está instalado.
- *Cómo cerrar:* compila en Overleaf (sube `paper.tex` con la plantilla IEEEtran) o instala MiKTeX. Revisa: tablas dentro del ancho de la columna, la tabla de doble columna (`table*`), saltos de página y que las referencias aparezcan con número.
- *Dependencia:* D1 y D2 (para incluir las figuras).

**I6. Actualizar el anteproyecto.**
- *Qué falta:* el anteproyecto dice "pronosticar" y "mitigar de forma automatizada". Hay que cambiarlo a "detectar de forma temprana" y "simular la mitigación", y alinear el objetivo 3 con I1.
- *Cómo cerrar:* edita el anteproyecto con el texto de `docs/reporte-gate-d.md`, sección 3, si ese texto existe en tu copia. Si no, redáctalo con la misma idea.
- *Dependencia:* I1.

**I7. Revisar los documentos secundarios del repositorio.**
- *Qué falta:* no revisé en esta sesión `docs/arquitectura.md`, `docs/modelo-amenazas.md`, `docs/protocolo-evaluacion.md`, `docs/diagramas/README.md` ni la sección 5.4 y 11 del plan. Pueden seguir describiendo el Caso B o la validación temporal.
- *Cómo cerrar:* busca en esos archivos las palabras `caso_B`, `Caso B`, `iat_`, `exp_rf` y `validación = tramo final`. Corrige lo que quede.
- *Dependencia:* ninguna.

**I8. Rama de correcciones sin PR.**
- *Qué falta:* la rama `docs/correccion-timestamp-y-paper` está subida al remoto, pero no tiene PR.
- *Cómo cerrar:* decide si se fusiona a `main` (con PR, como las anteriores) o si se deja como rama de referencia.
- *Dependencia:* ninguna.

**I9. Versionar el paper.**
- *Qué falta:* `docs/Entregas_pasadas/` está en `.gitignore`, así que el paper no tiene historial.
- *Cómo cerrar:* mueve `paper.tex` y el anteproyecto a una carpeta versionada, por ejemplo `docs/paper/`. Quita esa carpeta del `.gitignore` solo para ese archivo.
- *Dependencia:* ninguna.

### 2.3 Pendientes de análisis (limitaciones que el paper debe declarar)

**A1. Indicios de reasociación (P4 y P5).** El paper los presenta como indicios, no como resultados. Si quieres una afirmación más fuerte, hace falta una segunda captura independiente, que no tenemos.

**A2. Banda y canal (P12).** Todo está en 5 GHz, canal 36. El paper lo declara como limitación. No se puede evaluar la diversidad de canal con estos datos.

**A3. Un episodio por captura.** La latencia es descriptiva. El paper lo declara. No se puede corregir con estos datos.

**A4. Validación de 66 ventanas.** Las conclusiones de sensibilidad son preliminares. Declarado.

**A5. Ejecución de prueba descartada.** Declarada como desviación de R6, con sus cifras marcadas como no verificables. Declarado.

### 2.4 Orden sugerido para cerrar la sección

1. **D8 y D4:** decidir criterios y alcance de la VLAN 30. Son decisiones, no trabajo.
2. **Parte 1 completa:** construir la topología y capturar las pruebas. Eso cierra **D1**.
3. **D2, D3, D5, D6, D7:** figuras y tablas de diseño. Dependen de D1 solo en parte.
4. **I3:** figuras de evaluación con el script de solo lectura.
5. **I1 y I2:** decidir y, si corresponde, ejecutar la mitigación y el replay.
6. **I6 e I7:** actualizar el anteproyecto y los documentos secundarios.
7. **I4 e I5:** verificar citas y compilar. Es lo último porque cambia con cada edición.
8. **I8 e I9:** cerrar la rama y versionar el paper.

### 2.5 Lo que ya está cerrado (para no repetirlo)

- Caso C con la Opción D como partición principal, y Caso B descartado con su motivo.
- Tag `gate-d` sobre `6a49bb4`, con la prueba final atada a ese commit.
- Tablas de mapeo, características, parámetros y módulos en el paper.
- Regla de alerta y definición de latencia, con el código como referencia.
- Corrección de la docstring de `case_c`.
- Desviación de R6 declarada en el paper y en `decisiones.md`.
