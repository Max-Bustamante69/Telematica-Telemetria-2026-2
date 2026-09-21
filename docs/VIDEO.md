# Video de sustentación: guion y clips que hay que grabar

Duración objetivo: 16 minutos. Dos integrantes, ocho minutos cada uno. La edición (subtítulos, títulos de sección, figuras y capturas sobre la imagen, corte final) se hace después con la cadena de `packages/video` del brain: se normalizan los clips a 1080p, se transcriben con whisper para los subtítulos y se monta con `render_from_timeline_v2.mjs`. Cada integrante solo tiene que grabar sus clips y mandarlos en una carpeta.

## Cómo grabar

- El texto exacto que dice cada uno está en `docs/video/GUION_DE_GRABACION.md`, y el teleprompter de cada uno es `docs/video/teleprompter-maximiliano.html` o `docs/video/teleprompter-valeria.html`: se abre en el navegador (doble clic), F para pantalla completa, espacio para que el texto avance solo, flechas arriba y abajo para la velocidad, y los números 1 a 4 saltan a cada clip. Conviene ponerlo en un segundo monitor o en el celular, cerca de la cámara.

- Pantalla completa a 1920x1080 con la cámara en una esquina (OBS, o la grabación de Teams o Zoom). Si la cámara va aparte, mandar los dos archivos con el mismo nombre y sufijo `-cam`.
- Un clip por sección, en un solo intento largo; los errores se cortan en edición. No hace falta que quede perfecto.
- Nombre del archivo exactamente como está en la tabla: `01-max-intro.mp4`, `02-max-protocolo.mp4`, etc.
- Antes de grabar tener corriendo lo que pide la columna "En pantalla". El servidor ya está en la nube; los nodos de demo se lanzan con `HOST=telemetria.digitdeck.co bash tests/demo.sh start` (WSL o Linux) o cinco terminales con `node\node.py`.
- Hablar con calma y decir las cifras: son las que van en los subtítulos.

## Sección por sección

### Maximiliano (8 min)

| Clip | Minutos | Qué decir | En pantalla |
|---|---|---|---|
| `01-max-intro.mp4` | 1:30 | Quiénes somos, el problema (instalaciones distribuidas que reportan temperatura, humedad, energía, vibración y estado), y los tres componentes: nodos en Python, servidor en C en EC2 dentro de Docker, cliente operador. Terminar con "el servidor está en telemetria.digitdeck.co". | `docs/figuras/arquitectura.svg` abierto en el navegador (la edición lo superpone igual) |
| `02-max-protocolo.mp4` | 2:00 | TLP/1.0: mensaje de texto, una línea, campos con barra vertical. Leer un `REGISTER`, un `TELEMETRY` y un `GET_LAST` con su respuesta hasta `END`. Por qué UDP para telemetría (5 datagramas cada 2 s, perder uno no importa, el número de secuencia cuenta pérdidas) y TCP para registro, consultas y alertas (necesitan confirmación y orden). Los códigos de error 100 a 106. | `docs/PROTOCOLO.md` en el editor, bajando despacio |
| `03-max-servidor.mp4` | 2:30 | El servidor en C: `socket`, `bind`, `listen`, `accept` en `tcp_operator.c`; `recvfrom` y `sendto` en `udp_telemetry.c`; un hilo por cliente y un mutex sobre el estado en `state.c`; `SIGPIPE` ignorado y `shutdown()` para apagar limpio. Mostrar `docker ps` por SSH y el `HEALTHCHECK`. | VS Code con `server/src/tcp_operator.c` y `udp_telemetry.c`; luego terminal con `ssh -i deploy/aws/telemetria-key.pem ubuntu@telemetria.digitdeck.co "sudo docker ps"` |
| `04-max-nube.mp4` | 2:00 | EC2 t3.micro en us-east-1, grupo de seguridad con 22/tcp, 5000/udp, 5001/tcp, 8080/tcp, IP elástica 100.25.236.127, registro A en Cloudflare con proxy apagado (el proxy solo pasa HTTP). Ningún archivo del repo tiene la IP. Hacer `nslookup telemetria.digitdeck.co` en vivo. | Consola AWS (instancia y grupo de seguridad), panel DNS de Cloudflare, terminal con `nslookup` |

### Valeria (8 min)

| Clip | Minutos | Qué decir | En pantalla |
|---|---|---|---|
| `05-val-nodos.mp4` | 2:00 | El nodo en Python: resuelve el nombre con `getaddrinfo`, se registra por TCP, envía por UDP con `seq`, y si el servidor responde `NACK|104` se vuelve a registrar solo. Lanzar cinco nodos y mostrar que aparecen `ACTIVE` en la web. | Terminales con 5 nodos (o `tests/demo.sh start`) y el navegador en http://telemetria.digitdeck.co:8080 |
| `06-val-operador.mp4` | 2:00 | El cliente operador: `LIST_NODES`, `GET_LAST|NODE03`, `GET_STATUS|NODE01`, `SYSTEM_STATUS`, un comando inválido (`ERR|101`) y un nodo inexistente (`ERR|102`). Luego `SUBSCRIBE_ALERTS` y lanzar `node.py --force-alert TEMP` en otra terminal: la alerta llega sola al operador y aparece en la web. | Terminal con `python operator_client\operator_client.py --server telemetria.digitdeck.co` y una segunda terminal con el nodo que fuerza la alerta |
| `07-val-fallos.mp4` | 1:30 | Recuperación: `docker restart telemetry-server` con nodos corriendo (se ven los `NACK|104` y el nuevo `REGISTER`), Ctrl+C en un nodo (`BYE` e `INACTIVE`), y `tests/e2e.sh telemetria.digitdeck.co` con las 20 comprobaciones en verde. Cerrar con la prueba de pérdida: 500 enviados, 500 recibidos, 0 perdidos. | Terminal del nodo + SSH para el `docker restart`; luego `bash tests/e2e.sh telemetria.digitdeck.co` y `python tests/loss_test.py --server telemetria.digitdeck.co --count 500` |
| `08-val-wireshark.mp4` | 2:30 | Abrir `captures/telemetria-tcp-udp-dns.pcapng`. Filtro `udp.port==5000`: un datagrama, IP origen privada, destino 100.25.236.127, puerto 49921 a 5000, 29 bytes con `TELEMETRY|NODE12|1|TEMP|24.5`. Filtro `tcp.stream==1`: SYN, SYN-ACK, ACK, `GET_LAST`, respuesta, `QUIT`, FIN; 85 ms entre SYN y SYN-ACK. Filtro `dns.qry.name contains "telemetria"`: la respuesta A con TTL 260. Cerrar con la relación aplicación, transporte y red. | Wireshark con la captura del repo |

## Lo que se agrega en edición

Cada clip recibe subtítulos (whisper local) y un título de sección. Sobre la imagen se superponen, en el segundo en que se nombran, la figura 1 (arquitectura), la figura 2 (secuencia), la tabla de transporte, las capturas de `evidencias/` y los resultados de `tests/`. Los ocho clips se concatenan en el orden de los nombres.

## Qué enviar

Una carpeta con los ocho archivos `.mp4` (más los `-cam.mp4` si la cámara va aparte). Nada más: las figuras, capturas y textos ya están en el repo.

## Cómo se editó (20 de septiembre de 2026)

Los ocho clips (cuatro de cámara de Maximiliano, cuatro de pantalla con cámara de Valeria) se normalizaron a 1920x1080, 30 fps y AAC 48 kHz; se transcribieron con el filtro whisper de ffmpeg (modelo `ggml-small`) y las cues se corrigieron contra el guion; cada clip recibió una tarjeta de título, overlays con las figuras del informe, fragmentos del código fuente, `docker ps`, `nslookup` y las capturas de `evidencias/` en el segundo en que se nombran; los clips de Valeria van a 1,06x para cerrar en 18 minutos; se concatenaron y los subtítulos finales se generaron después del montaje. Todo es reproducible con `docs/video/edicion/montaje.py` y `tarjetas.py` a partir de los clips originales.
