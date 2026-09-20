# Guion del video de sustentación (15 a 18 minutos)

Tres integrantes: A, B y C. Cada uno explica y demuestra la parte que desarrolló. Grabar con la pantalla compartida y la cámara de quien habla. El video muestra ejecución real, no solo diapositivas.

| Minuto | Quién | Qué se muestra | Cómo se demuestra |
|---|---|---|---|
| 0:00 a 1:30 | A | Presentación del equipo y del problema | Una diapositiva con el diagrama de arquitectura (`docs/INFORME.md`, figura 1) |
| 1:30 a 3:30 | A | Protocolo TLP/1.0 | `docs/PROTOCOLO.md` en pantalla: formato, un mensaje de cada tipo, tabla de errores. Explicar por qué UDP para telemetría y TCP para registro, consultas y alertas |
| 3:30 a 5:30 | B | Servidor en la nube y Docker | Terminal con `ssh ubuntu@telemetria.digitdeck.co`, `docker ps`, `docker logs -f telemetry-server`. Consola de AWS con la instancia y el grupo de seguridad (22, 5000/udp, 5001, 8080) |
| 5:30 a 6:30 | B | DNS | `nslookup telemetria.digitdeck.co` desde el equipo local y la primera línea del nodo (`DNS: telemetria.digitdeck.co -> IP`) |
| 6:30 a 9:00 | C | Cinco nodos simultáneos | Cinco terminales (o `docker compose --profile nodes up` en un equipo) con nodos `NODE01` a `NODE05` enviando a la nube. En paralelo, `docker logs` del servidor mostrando los `REGISTER` y la interfaz web en http://telemetria.digitdeck.co:8080 con los cinco nodos `ACTIVE` |
| 9:00 a 11:00 | C | Cliente operador | `operator_client.py`: `LIST_NODES`, `GET_LAST|NODE03`, `GET_STATUS|NODE01`, `SYSTEM_STATUS`, un comando inválido (`ERR|101`) y un nodo inexistente (`ERR|102`). Dos operadores conectados a la vez desde dos equipos |
| 11:00 a 12:30 | A | Generación de una alerta | Operador con `SUBSCRIBE_ALERTS`. Lanzar `node.py --id NODE06 --force-alert TEMP`. La alerta aparece en el operador, en `GET_ALERTS`, en la web y en el log del servidor |
| 12:30 a 13:30 | B | Recuperación ante fallos | `docker restart telemetry-server` con los nodos corriendo: el nodo recibe `NACK|104`, se vuelve a registrar y sigue. Cerrar un nodo con Ctrl+C: `BYE` y `INACTIVE` en `LIST_NODES` |
| 13:30 a 15:30 | C | Wireshark | Captura ya guardada: un datagrama UDP con `TELEMETRY|...` (IP, puertos, longitud, texto) y el saludo de tres vías TCP del operador seguido de `LIST_NODES`. Relacionar aplicación, transporte y red |
| 15:30 a 16:30 | A | Resultados | Salida de `tests/loss_test.py` (transmitidos, recibidos, perdidos) y de `tests/e2e.sh`. Tabla de la sección 9 del informe |
| 16:30 a 17:00 | Todos | Cierre | Qué aprendió cada uno y dificultades encontradas |

Reparto sugerido de desarrollo (ajustar a lo real):

- A: protocolo, `protocol.c`, alertas, `state.c`, informe.
- B: `main.c`, `tcp_operator.c`, `udp_telemetry.c`, `http.c`, Docker, EC2, DNS.
- C: `node.py`, `operator_client.py`, pruebas, Wireshark.

Antes de grabar: tener los cinco nodos listos en terminales separadas, la web abierta, Wireshark con la captura cargada y el filtro aplicado, y la consola de AWS abierta en la instancia.
