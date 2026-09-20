# Plataforma distribuida de telemetría

Proyecto de Telemática / Internet: Arquitectura y Protocolos (2026-2). Un servidor central en C recibe telemetría de nodos IoT simulados por UDP, atiende operadores por TCP con un protocolo de texto propio (TLP/1.0), genera alertas y expone una interfaz web. El servidor corre en Docker sobre una instancia EC2 y los clientes lo encuentran por DNS.

| Componente | Lenguaje | Transporte | Carpeta |
|---|---|---|---|
| Servidor central | C (POSIX, pthreads) | UDP 5000, TCP 5001, HTTP 8080 | `server/` |
| Nodo de telemetría | Python 3 | TCP (registro), UDP (mediciones) | `node/` |
| Cliente operador | Python 3 | TCP | `operator_client/` |
| Interfaz web | HTML servido por el mismo binario en C | HTTP | `server/src/http.c` |
| Protocolo | texto, `\|` como separador, `\n` como fin de mensaje | | `docs/PROTOCOLO.md` |

Nombre DNS del servidor desplegado: `telemetria.digitdeck.co`.

## Ejecutar en local

Requisitos: Docker, Python 3.10 o superior.

```bash
docker compose up --build -d server            # servidor en un contenedor
python node/node.py --id NODE01 --server localhost --location "Planta Norte"
python operator_client/operator_client.py --server localhost
```

Interfaz web: http://localhost:8080

Cinco nodos de prueba en contenedores:

```bash
docker compose --profile nodes up --build
```

Sin Docker (Linux o WSL):

```bash
make -C server && ./server/build/telemetry-server
```

## Ejecutar contra el servidor en la nube

```bash
python node/node.py --id NODE07 --server telemetria.digitdeck.co --location "Casa de Juan"
python operator_client/operator_client.py --server telemetria.digitdeck.co
python operator_client/operator_client.py --server telemetria.digitdeck.co --cmd LIST_NODES
```

Opciones útiles del nodo:

| Opción | Efecto |
|---|---|
| `--interval 2` | segundos entre ciclos de envío |
| `--anomaly-rate 0.05` | probabilidad de un valor anómalo por variable |
| `--force-alert TEMP` | fuerza una temperatura > 40 en cada ciclo (demostración de alerta) |

## Pruebas

```bash
bash tests/e2e.sh localhost                      # 20 comprobaciones: nodos, consultas, errores, alerta, NACK, web, desconexión
python tests/loss_test.py --server localhost --count 500 --drop 50   # transmitidos, recibidos y perdidos
```

## Despliegue en AWS

1. `deploy/aws/create-instance.sh` crea el grupo de seguridad (22/tcp, 5000/udp, 5001/tcp, 8080/tcp), el par de llaves y la instancia Ubuntu 24.04 con el `user-data` que instala Docker y levanta el contenedor.
2. Apuntar el registro A `telemetria.digitdeck.co` a la IP pública (`deploy/dns.md`).
3. Comprobar desde otro equipo: `python operator_client/operator_client.py --server telemetria.digitdeck.co --cmd PING`.

Operación en la instancia:

```bash
ssh -i deploy/aws/telemetria-key.pem ubuntu@telemetria.digitdeck.co
cd /opt/telemetria && docker compose logs -f server
docker restart telemetry-server
```

## Estructura del repositorio

```
server/src/main.c           arranque, señales, hilos
server/src/udp_telemetry.c  socket UDP, recvfrom/sendto
server/src/tcp_operator.c   socket TCP, listen/accept, un hilo por cliente
server/src/protocol.c       parseo TLP, comandos, umbrales de alerta
server/src/state.c          registro de nodos, mediciones, alertas, mutex
server/src/http.c           interfaz web y /api/status
server/src/watchdog.c       nodos inactivos
node/node.py                nodo simulado
operator_client/            cliente operador
docs/PROTOCOLO.md           especificación del protocolo
docs/INFORME.md             informe técnico (fuente del PDF)
docs/WIRESHARK.md           guía de captura y filtros
docs/VIDEO.md               guion del video de sustentación
deploy/                     EC2, DNS
tests/                      pruebas
evidencias/                 capturas individuales y de despliegue
captures/                   archivos .pcapng
```
