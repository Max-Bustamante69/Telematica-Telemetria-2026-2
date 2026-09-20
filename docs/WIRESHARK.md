# Captura y análisis con Wireshark

## Qué capturar

Dos capturas desde el computador de un integrante, con el servidor ya desplegado en EC2:

1. `captures/telemetria-tcp-udp-dns.pcapng`: abrir Wireshark en la interfaz de red activa, aplicar el filtro de captura `host telemetria.digitdeck.co and (tcp port 5001 or udp port 5000)`, y ejecutar un nodo durante 20 segundos y luego el operador con `LIST_NODES` y `GET_LAST|NODE01`.
2. `captures/dns.pcapng`: filtro de captura `udp port 53`, ejecutar `nslookup telemetria.digitdeck.co`.

Antes de capturar conviene vaciar la caché DNS para que la consulta salga a la red: `ipconfig /flushdns` en Windows, `resolvectl flush-caches` en Linux.

## Filtros de visualización

| Qué ver | Filtro |
|---|---|
| Solo el protocolo TLP por UDP | `udp.port == 5000` |
| Solo el protocolo TLP por TCP | `tcp.port == 5001` |
| Saludo de tres vías | `tcp.flags.syn == 1 && tcp.port == 5001` |
| Cierre de conexión | `tcp.flags.fin == 1 && tcp.port == 5001` |
| Datagramas con un mensaje concreto | `udp.port == 5000 && frame contains "TELEMETRY"` |
| Consultas y respuestas DNS | `dns.qry.name contains "telemetria"` |
| Retransmisiones (si las hubo) | `tcp.analysis.retransmission` |

Para leer el texto del protocolo: clic derecho en un paquete, "Follow" > "TCP Stream" o "UDP Stream". El contenido aparece en claro porque TLP es un protocolo de texto sin cifrado.

## Qué explicar en el informe por cada captura

Para un datagrama UDP de telemetría, tomar una captura de pantalla con los tres paneles y anotar:

| Capa | Campo | Dónde está en Wireshark |
|---|---|---|
| Red (IP) | IP origen (equipo del integrante, privada si hay NAT) e IP destino (EC2) | Internet Protocol Version 4 > Source / Destination |
| Transporte (UDP) | Puerto origen efímero, puerto destino 5000, longitud, checksum | User Datagram Protocol |
| Aplicación (TLP) | `TELEMETRY|NODE01|17|TEMP|24.3` | Data (bytes en la parte inferior) |

Para la conexión TCP del operador:

1. Tres paquetes `SYN`, `SYN-ACK`, `ACK` con los números de secuencia relativos 0 y 1. Explicar quién inicia (el operador) y qué puerto usa cada lado.
2. El segmento `PSH, ACK` que lleva `LIST_NODES\n` y el `ACK` del servidor.
3. Los segmentos con la respuesta `OK|NODES|...` y `END`.
4. El cierre con `FIN` cuando el operador envía `QUIT`.

Relación con las capas: el texto TLP viaja como carga útil; TCP añade puertos, secuencia y confirmación (fiabilidad); UDP añade solo puertos y longitud (sin confirmación, por eso el servidor cuenta pérdidas con el número de secuencia del propio TLP); IP añade las direcciones de origen y destino que permiten cruzar Internet hasta la instancia.

## Comprobación con tshark

Si el integrante prefiere línea de comandos:

```bash
tshark -r captures/telemetria-tcp-udp-dns.pcapng -Y "udp.port == 5000" -T fields -e ip.src -e ip.dst -e udp.srcport -e udp.dstport -e data.text -o data.show_as_text:TRUE | head
tshark -r captures/telemetria-tcp-udp-dns.pcapng -Y "tcp.flags.syn == 1"
tshark -r captures/dns.pcapng -Y "dns" -T fields -e dns.qry.name -e dns.a
```
