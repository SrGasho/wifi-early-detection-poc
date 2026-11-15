# Topología en Packet Tracer con MCP — preparación y plan de construcción

Cierra D1 de `docs/guia-packet-tracer-y-pendientes.md` usando el servidor MCP de Packet Tracer en lugar de construir a mano. La guía (Parte 1) sigue siendo la especificación: este plan solo dice **con qué herramienta** se hace cada paso.

## 1. Estado de la instalación (2026-11-15)

| Pieza | Estado | Detalle |
|---|---|---|
| Cisco Packet Tracer | Instalado | 9.0.1.858 (`C:\Program Files\Cisco Packet Tracer 9.0.1\`); el MCP exige 8.2+ |
| `uv` | Instalado | 0.11.31 |
| Servidor MCP `packet-tracer` | **Registrado y conectado** | `packet-tracer-mcp` **0.12.0 fijado**, ámbito `local` (solo este proyecto), `uvx packet-tracer-mcp@0.12.0 --stdio`. Para quitarlo: `claude mcp remove packet-tracer -s local` |
| Skill `packet-tracer` | Instalada | `%USERPROFILE%\.claude\skills\packet-tracer` (guía operativa que carga Claude antes de usar las herramientas) |
| Extensión `MCP-Control-Center.pts` | **Agregada y en ejecución** | Se agregó en *Configure PT Script Modules → Add…* y hubo que pulsar **Start** (no basta con agregarla). Verificado el 15-nov: el navegador interno de PT (`QtWebEngineProcess`) consulta `127.0.0.1:54321` y `%LOCALAPPDATA%\packet-tracer-mcp\bridge\alive.txt` se actualiza cada segundo |
| Herramientas `pt_*` en la sesión de Claude | **Pendiente: reiniciar la sesión** | El servidor MCP solo se carga al iniciar la sesión; en la sesión donde se instaló no está disponible |

### Pasos pendientes del autor

1. Reiniciar la sesión de Claude Code (o `/reload-skills` para la skill) para cargar las herramientas `pt_*`.
2. Con Packet Tracer abierto y el módulo en *Start*, comprobar con `pt_bridge_status` → «ACTIVE and CONNECTED». Si Packet Tracer se cierra, hay que volver a pulsar **Start** en *Configure PT Script Modules*.

## 2. Verificación de seguridad hecha antes de instalar

| Comprobación | Resultado |
|---|---|
| Wheel de PyPI 0.12.0 frente al código de GitHub | **190 de 190 archivos idénticos**; SHA-256 del wheel = el publicado en PyPI |
| Dependencias | solo `mcp[cli]` y `pydantic` (`comtypes` es opcional y no se instala) |
| Red | el puente escucha **solo en `127.0.0.1`** (puertos 54321 y, con HTTP, 39400); token aleatorio persistido en `%LOCALAPPDATA%\packet-tracer-mcp\bridge_token`; valida la cabecera `Host`. Sin llamadas a internet. |
| Ejecución local | un solo subproceso: `clip.exe` (portapapeles). Sin `eval`/`exec` en el servidor |
| Skill | texto de instrucciones; sin `curl`, `sudo`, credenciales ni órdenes de ocultar acciones |
| Extensión `.pts` | hash = el publicado por GitHub (`d2ef0372…f1d0`). **El binario es un formato propietario de PT y no se puede auditar**; el código que debería representar (`EXTENSION/`) solo habla con `127.0.0.1:54321` |

Riesgos que se aceptan, según el propio `SECURITY.md` del proyecto: `pt_send_raw` ejecuta JavaScript arbitrario dentro de Packet Tracer (es su función), y cualquier proceso del usuario puede leer el token. Por eso: no abrir páginas ni archivos de origen no confiable mientras el puente está activo, y no pegar en la conversación contenido externo que pueda traer instrucciones.

**Alcance con las reglas del proyecto:** Packet Tracer es un simulador; no se envían tramas ni se tocan equipos reales (R9 se refiere al código del PoC, que no cambia). Nada de esto toca `data/raw/`, `configs/` ni resultados.

## 3. Mapa de la guía → herramientas MCP

Nombres de dispositivo (solo letras, dígitos, `-` y `_`): `R-EDGE`, `SW-CORP`, `AP-CORP`, `PC1`, `PC2`, `PC3`, `PC-INV`, `SERVIDOR`, `SENSOR`.

| Paso de la guía | Herramienta | Notas |
|---|---|---|
| 0. Preparar | `pt_bridge_status`, `pt_workspace_options(auto_cabling=0)`, `pt_canvas_info` | `auto_cabling=0` para que los cables vayan a los puertos exactos de la tabla 1.5 |
| 1.4 Dispositivos | `pt_list_devices`, `pt_get_device_details`, `pt_add_device` | Modelos: Router `1941`, Switch `2960-24TT`, `AccessPoint-PT-AC` (variante 802.11ac), `PC-PT`, `Server-PT`. El sensor es un `PC-PT` renombrado |
| 1.5 Cables | `pt_add_link` (cable recto) | Los 8 enlaces de la tabla 1.5 (R-EDGE Gi0/0 ↔ SW-CORP Fa0/1, etc.) |
| 1.6 Switch (VLAN, troncales, accesos) | `pt_apply_vlan` (`dry_run=True` primero) y/o `pt_cli` | VLAN 10/20/30; troncales Fa0/1 y Fa0/2; accesos Fa0/3–Fa0/8 |
| 1.7 Router (subinterfaces `dot1Q`) | `pt_apply_vlan` o `pt_cli` | Gi0/0.10, .20, .30 con 192.168.10/20/30.1 |
| 1.7 ACL de invitados | `pt_apply_acl` (`dry_run=True` primero), luego `pt_read_acl` | `ACL-INVITADOS` aplicada `in` en Gi0/0.30 |
| 1.8 IP de PC y servidor | `pt_host_ip_config` (estática) | Tabla 1.8; el servidor necesita IP fija |
| 1.9 AP | `pt_wireless_ap` (SSID `EMPRESA`) y `pt_host_ip_config`/`pt_cli` para la IP de gestión 192.168.20.2 | **Limitaciones:** WPA2-PSK no está entre los parámetros de `pt_wireless_ap` y el perfil WPA/WEP del cliente solo se configura por la GUI; se documenta como no verificable en PT (coherente con D6). Un portátil solo se une al SSID «Default», así que renombrar el SSID a `EMPRESA` **desconecta cualquier cliente inalámbrico**: ver T7 |
| (nuevo) Salida a Internet de la VLAN 30 | `pt_add_device` (router `ISP`), `pt_add_link`, `pt_apply_nat`, `pt_cli` (ruta por defecto) | Solo si T5 = sí; ver §4 |
| (nuevo) ACL de acceso a la VLAN 20 | `pt_apply_acl` (`dry_run=True` primero), `pt_read_acl` | Solo si T6 = sí; ver §4 |
| 1.10 Las 6 pruebas | `pt_verify_connectivity` | Tres veredictos: `CONNECTIVITY OK`, `PARTIAL` (repetir una vez por el ARP) y `NO CONNECTIVITY`. Las pruebas de invitados esperan `NO CONNECTIVITY` |
| Verificación | `pt_read_vlans`, `pt_read_acl`, `pt_inspect_ports`, `pt_health_check`, `pt_audit_security` | Leen el estado real del equipo, no el plan |
| 1.11 Exportar | `pt_save_project(filename="topologia-empresa", directory="docs/diagramas")`, `pt_screenshot` | El directorio debe quedar dentro del directorio de trabajo del MCP; se comprueba al ejecutar |
| Respaldo | `pt_backup_config` por equipo | Opcional: guarda la configuración real |

Orden de ejecución: dispositivos → cables → VLAN/troncales → subinterfaces → ACL → IP de equipos → AP → pruebas → guardar y captura.

## 4. Decisiones a confirmar antes de construir

| # | Decisión | Recomendación |
|---|---|---|
| T1 | Modelo del AP: `AccessPoint-PT-AC` o `AccessPoint-PT` | `AccessPoint-PT-AC`, por coherencia con 802.11ac del diseño |
| T2 | Construir con IP y puertos exactos de la guía (a mano con herramientas atómicas) o usar `pt_full_build` | A mano: el planificador automático asigna su propio direccionamiento y no respeta la tabla de la guía |
| T3 | Si el AP-PT no acepta troncal 802.11Q | Dejarlo como acceso a la VLAN 20 y declararlo como limitación (la guía ya lo prevé), sin forzar |
| T4 | Reglas ACL sin estado | Mantener `permit ip any any` como en la guía y declarar la limitación (ya está en el paper) |

### Desajustes de coherencia detectados el 15-nov (guía y plan frente a `docs/arquitectura.md` y el paper)

La guía de Packet Tracer es más reducida que lo que afirman la arquitectura y el paper. Hay que cerrar cada punto construyéndolo o declarando la omisión; no se puede dejar silencioso.

| # | Lo que dicen `arquitectura.md` y el paper | Lo que haría la guía hoy | Decisión | Recomendación |
|---|---|---|---|---|
| T5 | La VLAN 30 «tendrá únicamente salida a Internet»; el router hace NAT y sale a Internet | No hay nodo de Internet ni NAT; solo se prueba que la ACL **bloquea**, nunca que la salida **funciona** | Añadir un router `ISP` (203.0.113.1/24, rango de documentación) con NAT *overload* y ruta por defecto en R-EDGE, y una prueba `PC-INV → ISP` | **Sí**: la afirmación del paper quedaría verificada, con costo bajo (2 dispositivos y 3 herramientas) |
| T6 | «El acceso a la VLAN 20 se restringe con ACL a las comunicaciones administrativas autorizadas» | Solo se bloquea a invitados; PC1, PC2 y PC3 llegan sin restricción al servidor y al sensor | Añadir `ACL-CORP-GESTION` en Gi0/0.10 (`in`): permitir solo `host 192.168.10.10` (PC1, estación administrativa) hacia 192.168.20.0/24, denegar el resto de VLAN 10 hacia VLAN 20 y `permit ip any any`; pruebas nuevas `PC2 → SERVIDOR` (sin respuesta) y `PC1 → SERVIDOR` (respuesta) | **Sí**; si no, hay que reescribir esa frase del paper y de la arquitectura |
| T7 | El AP tiene SSID corporativo **y** de invitados, y se usa `EMPRESA` | `AccessPoint-PT-AC` tiene un solo SSID y sin mapeo SSID→VLAN; `PC-INV` es un equipo cableado, no un cliente Wi-Fi; renombrar el SSID desconecta clientes | No simular clientes inalámbricos: poner SSID `EMPRESA` en el AP, no añadir portátiles, y declarar que el SSID de invitados y el mapeo SSID→VLAN no se verifican en PT | **Sí**, declarando la limitación en la guía y en el paper (D6) |
| T8 | El router hace DHCP, DNS y NAT; el sensor captura pasivamente el aire en modo monitor | Todas las IP son estáticas, no hay DHCP ni DNS, y el sensor es un `PC-PT` cableado | Mantener IP estáticas y sensor cableado; añadir una nota en el lienzo (`pt_add_note`) «captura pasiva no simulada» y declarar DHCP/DNS como no simulados. NAT queda cubierto por T5 | **Sí** |

Además, ni el canal 36 con 40 MHz, ni WPA2 con PMF opcional, ni los 200 Mbps se pueden representar en Packet Tracer; siguen siendo supuestos de diseño (D6, D7), no verificaciones.

## 4b. Resultado de la construcción (15-nov)

Las decisiones T1 a T8 se aprobaron como se recomendaban («todas como recomiendas») y se ejecutaron. Evidencia completa en `docs/diagramas/pruebas-topologia.md`.

| Decisión | Resultado |
|---|---|
| T1 AP `AccessPoint-PT-AC` | Hecho. Su puerto es `Port 0` |
| T2 herramientas atómicas | Hecho: `pt_add_device`, `pt_add_link`, `pt_apply_vlan`, `pt_apply_acl`, `pt_apply_nat`, `pt_host_ip_config`, `pt_cli`; todas con `dry_run` previo y lectura posterior |
| T3 troncal del AP | El enlace sube con el troncal configurado, pero el AP no etiqueta 802.1Q; se declara como limitación |
| T4 ACL sin estado | Mantenida y declarada |
| T5 Internet | Hecho: router `ISP` 203.0.113.1/24, NAT/PAT en `R-EDGE`, ruta por defecto; 4 traducciones observadas |
| T6 ACL de gestión | Hecho: `ACL-CORP-GESTION`; `PC2` y `PC3` no llegan a la VLAN 20, `PC1` sí |
| T7 SSID | `EMPRESA`, sin clientes inalámbricos; queda **abierto** (WPA2 no configurable) |
| T8 DHCP, DNS, sensor | Mantenidos como no simulados y anotados en el lienzo |

Descubrimientos que cambian el plan original: el AP-PT **no admite dirección IP de gestión**, de modo que la IP 192.168.20.2 de la guía no se puede aplicar; y el MCP guarda sus archivos en `%USERPROFILE%\PacketTracerMCP\` (no en el repo), por lo que `.pkt` y `.png` se copiaron a `docs/diagramas/`.

## 5. Criterio de cierre de D1

**Cumplido el 15-nov.** (Se conserva el criterio original para trazabilidad.)

- Las 6 pruebas de la sección 1.10 dan el resultado esperado, con la salida de `pt_verify_connectivity` guardada. Al aprobarse T5 y T6 se sumaron cuatro pruebas: `PC2 → SERVIDOR` y `PC3 → SENSOR` (sin respuesta), `PC-INV → ISP` (responde) y `PC2 → puerta de enlace` (control); `PC1 → SERVIDOR` ya estaba en la guía.
- `pt_read_vlans` y `pt_read_acl` coinciden con las tablas de la guía.
- Existen `docs/diagramas/topologia-empresa.pkt` y `.png`.
- Se actualizan D1, D3, D4 y D5 en la guía, y el paper recibe la figura (`\includegraphics`) y la tabla de VLAN e IP (D3).
