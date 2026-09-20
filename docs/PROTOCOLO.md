# TLP/1.0 · Telemetry Line Protocol

Protocolo de capa de aplicación diseñado para este proyecto. Es un protocolo de texto, orientado a líneas, que corre sobre UDP (telemetría) y sobre TCP (registro, consultas de operador y alertas).

## 1. Formato general

- Codificación ASCII (UTF-8 permitido en el campo de ubicación).
- Un mensaje es una línea terminada en `\n` (LF). El servidor tolera `\r\n`.
- Los campos se separan con `|`. El primer campo es el tipo de mensaje, en mayúsculas.
- Longitud máxima de un mensaje: 512 bytes incluido el `\n`. Un mensaje más largo se rechaza con el error 105.
- Los identificadores de nodo aceptan letras, dígitos, `_` y `-` (máximo 32 caracteres).
- Los valores numéricos usan punto decimal (`24.8`).

Gramática:

```
mensaje  := tipo ( "|" campo )* "\n"
tipo     := [A-Z_]+
campo    := cualquier byte excepto "|" y "\n"
```

## 2. Servicios y transporte

| Servicio | Transporte | Puerto | Justificación |
|---|---|---|---|
| Registro y baja de nodos | TCP | 5001 | El registro es crítico. Sin confirmación el nodo no sabe si el servidor lo conoce. |
| Telemetría periódica | UDP | 5000 | Se envía cada pocos segundos. Perder una lectura es tolerable y UDP evita el costo de conexión y retransmisión. |
| Consultas y comandos del operador | TCP | 5001 | Una consulta necesita respuesta completa, ordenada y sin pérdida. |
| Alertas enviadas al operador | TCP | 5001 | Una alerta no se puede perder. Se envían por la misma conexión del operador suscrito. |
| Interfaz web | HTTP/1.1 sobre TCP | 8080 | Requisito de la sección 7 del enunciado. Solo lectura. |

El puerto 5001 recibe tanto nodos como operadores. El tipo del mensaje indica quién habla, así que el servidor no necesita un puerto por rol.

## 3. Mensajes del nodo

### 3.1 REGISTER (TCP)

```
REGISTER|<node_id>|<ubicacion>|<VAR1,VAR2,...>
```

Respuesta correcta:

```
OK|REGISTERED|<node_id>|<puerto_udp>
```

El nodo puede cerrar la conexión TCP después de recibir el `OK`, o dejarla abierta para enviar `BYE` al terminar.

Errores posibles: 100, 103, 106.

### 3.2 TELEMETRY (UDP)

```
TELEMETRY|<node_id>|<seq>|<VAR>|<valor>
```

- `seq` es un entero que empieza en 1 y crece en 1 por cada datagrama enviado por el nodo. Con él el servidor calcula datagramas perdidos.
- `VAR` es el nombre de la variable: `TEMP`, `HUM`, `ENERGY`, `VIB`, `STATUS`.
- `valor` es numérico, salvo para `STATUS`, que acepta `OK`, `WARN` o `FAULT`.

El servidor no responde a un `TELEMETRY` válido. Si el nodo no está registrado (por ejemplo, el servidor se reinició), el servidor responde por UDP:

```
NACK|104|NOT_REGISTERED
```

y el nodo debe volver a registrarse por TCP.

### 3.3 BYE (TCP)

```
BYE|<node_id>
```

Respuesta: `OK|BYE`. El nodo pasa a estado `INACTIVE` de inmediato.

## 4. Mensajes del operador (TCP)

| Comando | Respuesta |
|---|---|
| `PING` | `OK|PONG` |
| `LIST_NODES` | `OK|NODES|<n>` seguido de `n` líneas `NODE|<id>|<ubicacion>|<estado>|<hace_s>|<recibidos>|<perdidos>` y una línea `END` |
| `GET_STATUS|<id>` | `OK|STATUS|<id>|<estado>|<ubicacion>|<hace_s>|<recibidos>|<perdidos>|<alertas>` |
| `GET_LAST|<id>` | `OK|LAST|<id>|<n>` seguido de `n` líneas `MEASURE|<id>|<VAR>|<valor>|<hace_s>` y `END` |
| `GET_ALERTS` o `GET_ALERTS|<max>` | `OK|ALERTS|<n>` seguido de `n` líneas `ALERT|<id>|<tipo>|<valor>|<hace_s>` y `END` |
| `SYSTEM_STATUS` | `OK|SYSTEM|uptime=<s>;nodes=<n>;active=<n>;operators=<n>;udp_received=<n>;udp_lost=<n>;udp_rejected=<n>;udp_invalid=<n>;tcp_commands=<n>;alerts=<n>` |
| `SUBSCRIBE_ALERTS` | `OK|SUBSCRIBED`. Desde ese momento el servidor envía `ALERT|<id>|<tipo>|<valor>|0` por la misma conexión cada vez que se genera una alerta. |
| `QUIT` | `OK|BYE` y el servidor cierra la conexión |

`<estado>` es `ACTIVE` o `INACTIVE`. Un nodo pasa a `INACTIVE` cuando lleva más de 15 segundos sin enviar telemetría o cuando envía `BYE`.

## 5. Alertas

El servidor evalúa cada medición al recibirla. Umbrales:

| Variable | Condición | Tipo de alerta |
|---|---|---|
| TEMP | valor > 40.0 | `TEMP_HIGH` |
| TEMP | valor < -10.0 | `TEMP_LOW` |
| HUM | valor > 85.0 | `HUM_HIGH` |
| ENERGY | valor > 5000.0 | `ENERGY_HIGH` |
| VIB | valor > 8.0 | `VIB_HIGH` |
| STATUS | valor = `FAULT` | `STATUS_FAULT` |
| (cualquiera) | nodo sin telemetría por 15 s | `NODE_INACTIVE` |

Formato de una alerta:

```
ALERT|<node_id>|<tipo>|<valor>|<hace_s>
```

Ejemplo: `ALERT|NODE03|TEMP_HIGH|42.1|0`.

## 6. Códigos de error

Formato: `ERR|<codigo>|<texto>`.

| Código | Texto | Cuándo |
|---|---|---|
| 100 | BAD_FORMAT | Faltan campos o el mensaje está vacío |
| 101 | UNKNOWN_COMMAND | El tipo de mensaje no existe |
| 102 | UNKNOWN_NODE | El `node_id` consultado no está registrado |
| 103 | BAD_PARAM | Un parámetro tiene un valor inválido (id con caracteres prohibidos, número no numérico, seq negativo) |
| 104 | NOT_REGISTERED | Telemetría de un nodo que no hizo `REGISTER` |
| 105 | TOO_LONG | La línea supera 512 bytes |
| 106 | SERVER_FULL | Se alcanzó el máximo de nodos registrados |

En UDP el único error que el servidor devuelve es `NACK|104|NOT_REGISTERED`. Los datagramas malformados se cuentan en `udp_invalid` y se descartan sin respuesta.

## 7. Ejemplos de intercambio

### 7.1 Ciclo completo de un nodo

```
[TCP 5001]  N -> S : REGISTER|NODE03|Planta Norte|TEMP,HUM,ENERGY,VIB,STATUS
[TCP 5001]  S -> N : OK|REGISTERED|NODE03|5000
[UDP 5000]  N -> S : TELEMETRY|NODE03|1|TEMP|24.8
[UDP 5000]  N -> S : TELEMETRY|NODE03|2|HUM|61.2
[UDP 5000]  N -> S : TELEMETRY|NODE03|3|ENERGY|1320.5
[UDP 5000]  N -> S : TELEMETRY|NODE03|4|VIB|1.9
[UDP 5000]  N -> S : TELEMETRY|NODE03|5|STATUS|OK
...
[UDP 5000]  N -> S : TELEMETRY|NODE03|41|TEMP|42.1      <- genera ALERT|NODE03|TEMP_HIGH|42.1
[TCP 5001]  N -> S : BYE|NODE03
[TCP 5001]  S -> N : OK|BYE
```

### 7.2 Sesión de operador

```
O -> S : LIST_NODES
S -> O : OK|NODES|2
S -> O : NODE|NODE01|Planta Norte|ACTIVE|1|120|0
S -> O : NODE|NODE03|Bodega Sur|ACTIVE|0|118|2
S -> O : END
O -> S : GET_LAST|NODE03
S -> O : OK|LAST|NODE03|5
S -> O : MEASURE|NODE03|TEMP|42.1|3
S -> O : MEASURE|NODE03|HUM|61.2|2
S -> O : MEASURE|NODE03|ENERGY|1320.5|2
S -> O : MEASURE|NODE03|VIB|1.9|1
S -> O : MEASURE|NODE03|STATUS|OK|1
S -> O : END
O -> S : GET_STATUS|NODE99
S -> O : ERR|102|UNKNOWN_NODE
O -> S : HOLA
S -> O : ERR|101|UNKNOWN_COMMAND
O -> S : SUBSCRIBE_ALERTS
S -> O : OK|SUBSCRIBED
S -> O : ALERT|NODE03|TEMP_HIGH|43.0|0        <- llega sin que el operador pida nada
O -> S : QUIT
S -> O : OK|BYE
```

### 7.3 Servidor reiniciado

```
[UDP] N -> S : TELEMETRY|NODE03|900|TEMP|25.0
[UDP] S -> N : NACK|104|NOT_REGISTERED
[TCP] N -> S : REGISTER|NODE03|Bodega Sur|TEMP,HUM,ENERGY,VIB,STATUS
[TCP] S -> N : OK|REGISTERED|NODE03|5000
[UDP] N -> S : TELEMETRY|NODE03|901|TEMP|25.1
```

## 8. Interfaz web (HTTP, puerto 8080)

No es parte del protocolo TLP. Es una vista de solo lectura sobre el mismo estado.

| Ruta | Contenido |
|---|---|
| `GET /` | Página HTML que se actualiza sola cada 3 segundos |
| `GET /api/status` | JSON con servidor, nodos, últimas mediciones y alertas |
| `GET /health` | `ok` en texto plano |
