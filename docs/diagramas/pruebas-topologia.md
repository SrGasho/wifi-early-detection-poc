# Verificación de la topología en Cisco Packet Tracer

Construida y verificada el 2026-11-15 con Cisco Packet Tracer 9.0.1.858 y el servidor MCP `packet-tracer-mcp` 0.12.0 (ver `docs/superpowers/plans/2026-11-15-packet-tracer-mcp.md`). Es un **diseño verificado a nivel lógico**: Packet Tracer no simula el enlace 802.11ac, el modo monitor ni WPA2/PMF.

Archivos: `topologia-empresa.pkt` (proyecto), `topologia-empresa.png` (figura recortada) y `topologia-empresa-captura.png` (captura sin recortar). Las tablas de VLAN, IP y puertos son las de `docs/guia-packet-tracer-y-pendientes.md` (§1.1 a §1.8) más el router `ISP` y la ACL de gestión, añadidos por las decisiones T5 y T6.

## Equipos y direccionamiento

| Equipo | Modelo | Puerto | IP | Gateway | VLAN |
|---|---|---|---|---|---|
| `R-EDGE` | 1941 | Gi0/0.10, .20, .30 | 192.168.10.1, 192.168.20.1, 192.168.30.1 /24 | — | 10, 20, 30 |
| `R-EDGE` | 1941 | Gi0/1 | 203.0.113.2/24 (exterior, NAT) | 203.0.113.1 (ruta por defecto) | — |
| `ISP` | 1941 | Gi0/0 | 203.0.113.1/24 | — | — |
| `SW-CORP` | 2960-24TT | Fa0/1 y Fa0/2 troncales; Fa0/3, 4, 8 → VLAN 10; Fa0/5, 6 → VLAN 20; Fa0/7 → VLAN 30 | — | — | — |
| `PC1`, `PC2`, `PC3` | PC-PT | Fa0 (Fa0/3, Fa0/4, Fa0/8) | 192.168.10.10, .11, .12 | 192.168.10.1 | 10 |
| `SERVIDOR` | Server-PT | Fa0 (Fa0/5) | 192.168.20.20 | 192.168.20.1 | 20 |
| `SENSOR` | PC-PT | Fa0 (Fa0/6) | 192.168.20.10 | 192.168.20.1 | 20 |
| `PC-INV` | PC-PT | Fa0 (Fa0/7) | 192.168.30.10 | 192.168.30.1 | 30 |
| `AP-CORP` | AccessPoint-PT-AC | Port 0 (Fa0/2) | **sin IP** (ver limitaciones) | — | — |

Enlaces: cable recto en todos salvo `ISP`–`R-EDGE` (cruzado).

## Pruebas de conectividad (`pt_verify_connectivity`, ping real)

| # | Origen → destino | Esperado | Resultado |
|---|---|---|---|
| 1 | `PC1` → 192.168.10.11 (PC2) | responde | **OK**, 4/4 |
| 2 | `PC1` → 192.168.20.20 (SERVIDOR) | responde (estación administrativa) | **OK**, 4/4 (la primera ejecución dio 3/4 por ARP; la repetición, 4/4) |
| 3 | `PC-INV` → 192.168.10.10 | sin respuesta | **sin respuesta**, 0/4 |
| 4 | `PC-INV` → 192.168.20.20 | sin respuesta | **sin respuesta**, 0/4 |
| 5 | `PC-INV` → 192.168.30.1 | responde | **OK**, 4/4 |
| 6 | `SENSOR` → 192.168.20.20 | responde | **OK**, 4/4 |
| 7 | `PC2` → 192.168.20.20 (T6) | sin respuesta | **sin respuesta**, 0/4 |
| 8 | `PC3` → 192.168.20.10 (T6) | sin respuesta | **sin respuesta**, 0/4 |
| 9 | `PC-INV` → 203.0.113.1 (ISP, T5) | responde | **OK**, 4/4 (la primera ejecución dio 3/4 por ARP) |
| 10 | `PC2` → 192.168.10.1 | responde | **OK**, 4/4 |

Las pruebas 1 a 6 son las de la guía (§1.10). Las 7 y 8 (T6) y la 9 (T5) son las de las decisiones añadidas. La 10 es un control: comprueba que la ACL de gestión no corta el tráfico normal de la VLAN 10 (`PC2` llega a su propia puerta de enlace).

**Motivo de los descartes, leído de Packet Tracer** (`pt_send_pdu`, modo simulación, `PC2` → `SERVIDOR`): en `R-EDGE`, la ACL `ACL-CORP-GESTION` entrante en `Gi0/0.10` descarta el paquete con la regla `deny ip 192.168.10.0 0.0.0.255 192.168.20.0 0.0.0.255` y el router devuelve «Administratively Prohibited». Para `PC-INV` hacia las VLAN 10 y 20 no se pidió el rastro: la única diferencia con las pruebas que responden (5 y 9) es la regla `deny` de `ACL-INVITADOS`.

**NAT:** tras las pruebas, `pt_read_nat` muestra 4 traducciones `192.168.30.10` → `203.0.113.2` con destino `203.0.113.1`, y 3 interfaces «inside» y 1 «outside».

## Lecturas del estado real

- `pt_read_vlans(SW-CORP)`: VLAN 10 `CORPORATIVA` (Fa0/3, 4, 8), VLAN 20 `GESTION` (Fa0/5, 6), VLAN 30 `INVITADOS` (Fa0/7); troncales Fa0/1 y Fa0/2.
- `show interfaces trunk` (SW-CORP): ambos troncales en `802.1q`, `trunking`, VLAN permitidas y activas 10, 20 y 30.
- `pt_read_acl(R-EDGE)`: `ACL-INVITADOS` en `Gi0/0.30` (entrada) y `ACL-CORP-GESTION` en `Gi0/0.10` (entrada); la ACL `1` es la lista interna de NAT.
- `pt_health_check`: topología sana, sin enlaces caídos ni IP duplicadas. Aviso esperado: `R-EDGE Gi0/0` no lleva IP (interfaz padre del router-on-a-stick).

## Configuración de `R-EDGE` (startup-config leída del equipo)

```text
hostname R-EDGE
interface GigabitEthernet0/0
 no ip address
interface GigabitEthernet0/0.10
 encapsulation dot1Q 10
 ip address 192.168.10.1 255.255.255.0
 ip nat inside
 ip access-group ACL-CORP-GESTION in
interface GigabitEthernet0/0.20
 encapsulation dot1Q 20
 ip address 192.168.20.1 255.255.255.0
 ip nat inside
interface GigabitEthernet0/0.30
 encapsulation dot1Q 30
 ip address 192.168.30.1 255.255.255.0
 ip nat inside
 ip access-group ACL-INVITADOS in
interface GigabitEthernet0/1
 description Salida-a-ISP
 ip address 203.0.113.2 255.255.255.0
 ip nat outside
ip nat inside source list 1 interface GigabitEthernet0/1 overload
ip route 0.0.0.0 0.0.0.0 203.0.113.1
access-list 1 permit 192.168.10.0 0.0.0.255
access-list 1 permit 192.168.20.0 0.0.0.255
access-list 1 permit 192.168.30.0 0.0.0.255
ip access-list extended ACL-INVITADOS
 deny ip 192.168.30.0 0.0.0.255 192.168.10.0 0.0.0.255
 deny ip 192.168.30.0 0.0.0.255 192.168.20.0 0.0.0.255
 permit ip any any
ip access-list extended ACL-CORP-GESTION
 permit ip host 192.168.10.10 192.168.20.0 0.0.0.255
 deny ip 192.168.10.0 0.0.0.255 192.168.20.0 0.0.0.255
 permit ip any any
```

(Se omiten las líneas por defecto de Packet Tracer. En `SW-CORP`, el volcado de la herramienta imprime `switchport trunk allowed vlan` en tres líneas; es un efecto de impresión, no de configuración: `show interfaces trunk` confirma `10,20,30`.)

## Limitaciones que el paper debe declarar

1. **El AP no tiene IP de gestión.** El `AccessPoint-PT-AC` es un dispositivo de capa 2: sus puertos no admiten dirección IP. La IP 192.168.20.2 de la guía no se puede configurar ni probar.
2. **El AP no etiqueta 802.1Q.** El puerto `Fa0/2` del switch está configurado como troncal según el diseño, pero el AP reenvía las tramas sin etiqueta (Packet Tracer lo muestra al reenviar STP), así que el etiquetado hacia el AP no se verifica.
3. **El AP queda abierto.** `auth_type 0` y `encrypt_type 0`: Packet Tracer no permite configurar WPA2 en el AP ni el perfil WPA en el cliente. WPA2, PMF opcional, canal 36 y ancho de 40 MHz son supuestos de diseño, no verificaciones. El SSID es `EMPRESA`; no hay clientes inalámbricos porque solo se unen al SSID «Default».
4. **No hay SSID de invitados.** El AP tiene un solo SSID y no hay mapeo SSID→VLAN; `PC-INV` es un equipo cableado en la VLAN 30.
5. **El sensor es un PC cableado.** La captura pasiva en modo monitor no se simula.
6. **ACL sin estado.** `permit ip any any` al final deja pasar respuestas; un diseño real necesita `established` o un cortafuegos con estado.
7. **Sin DHCP ni DNS.** Todas las IP son estáticas. El «Internet» es un único router `ISP` con la dirección 203.0.113.1.
8. **Verificación lógica.** Ninguna prueba mide rendimiento (los 200 Mbps siguen siendo una estimación de planificación).
