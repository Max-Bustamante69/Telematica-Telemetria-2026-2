#!/usr/bin/env bash
# Prueba de extremo a extremo contra un servidor ya en ejecución.
#   tests/e2e.sh [host]        (por defecto localhost)
# Requiere python3 y curl. Devuelve 1 si alguna comprobación falla.
set -u
HOST="${1:-localhost}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OP="python3 $ROOT/operator_client/operator_client.py --server $HOST --cmd"
fail=0
check() { # check "descripcion" "patron" "texto"
  if grep -q -- "$2" <<<"$3"; then echo "  [ok]   $1"; else echo "  [FAIL] $1"; echo "         obtenido: $3" | head -3; fail=1; fi
}

echo "== 1. servidor responde por TCP"
check "PING -> OK|PONG" "OK|PONG" "$($OP PING 2>&1)"

echo "== 2. cinco nodos simultaneos por UDP"
pids=()
for i in 1 2 3 4 5; do
  python3 "$ROOT/node/node.py" --id "NODE0$i" --server "$HOST" --location "Sitio $i" --interval 1 --anomaly-rate 0 >"/tmp/node0$i.log" 2>&1 &
  pids+=($!)
done
sleep 4
out="$($OP LIST_NODES 2>&1)"
check "LIST_NODES muestra 5 nodos" "OK|NODES|5" "$out"
check "NODE01 ACTIVE" "NODE01 .*ACTIVE" "$out"
check "NODE05 ACTIVE" "NODE05 .*ACTIVE" "$out"

echo "== 3. consultas de operador"
check "GET_LAST|NODE03 trae TEMP" "TEMP" "$($OP 'GET_LAST|NODE03' 2>&1)"
check "GET_STATUS|NODE02 ACTIVE" "ACTIVE" "$($OP 'GET_STATUS|NODE02' 2>&1)"
check "SYSTEM_STATUS reporta nodes" "nodes *5" "$($OP SYSTEM_STATUS 2>&1)"

echo "== 4. errores del protocolo"
check "comando desconocido -> 101" "error 101" "$($OP HOLA 2>&1)"
check "nodo inexistente -> 102" "error 102" "$($OP 'GET_STATUS|NODE99' 2>&1)"
check "parametro invalido -> 103" "error 103" "$($OP 'GET_STATUS|NO DE' 2>&1)"
check "REGISTER incompleto -> 100" "error 100" "$($OP 'REGISTER|X' 2>&1)"

echo "== 5. alerta generada por un valor anomalo"
python3 "$ROOT/node/node.py" --id NODE06 --server "$HOST" --location "Caldera" --interval 1 --force-alert TEMP >/tmp/node06.log 2>&1 &
pids+=($!)
sleep 3
check "GET_ALERTS contiene TEMP_HIGH de NODE06" "NODE06 *TEMP_HIGH" "$($OP GET_ALERTS 2>&1)"

echo "== 6. telemetria de un nodo no registrado recibe NACK"
nack="$(python3 - "$HOST" <<'EOF'
import socket, sys
ip = socket.getaddrinfo(sys.argv[1], 5000, socket.AF_INET, socket.SOCK_DGRAM)[0][4][0]
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(3)
s.sendto(b"TELEMETRY|GHOST|1|TEMP|20.0\n", (ip, 5000))
try: print(s.recv(128).decode().strip())
except socket.timeout: print("sin respuesta")
EOF
)"
check "NACK|104|NOT_REGISTERED" "NACK|104" "$nack"

echo "== 7. datagrama malformado no tumba el servidor"
python3 - "$HOST" <<'EOF'
import socket, sys
ip = socket.getaddrinfo(sys.argv[1], 5000, socket.AF_INET, socket.SOCK_DGRAM)[0][4][0]
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
for m in [b"", b"basura", b"TELEMETRY|NODE01|x|TEMP|1\n", b"TELEMETRY|NODE01|9|TEMP|abc\n", b"A" * 600]:
    s.sendto(m, (ip, 5000))
EOF
sleep 1
check "servidor sigue vivo tras basura UDP" "OK|PONG" "$($OP PING 2>&1)"
check "udp_invalid contabilizado" "udp_invalid *[1-9]" "$($OP SYSTEM_STATUS 2>&1)"

echo "== 8. linea TCP demasiado larga -> 105 y la conexion sigue"
long="$(python3 - "$HOST" <<'EOF'
import socket, sys
ip = socket.getaddrinfo(sys.argv[1], 5001, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
s = socket.create_connection((ip, 5001), timeout=5)
s.sendall(b"X" * 700 + b"\nPING\n")
data = b""
while data.count(b"\n") < 2: data += s.recv(1024)
print(data.decode().strip().replace("\n", " / "))
EOF
)"
check "ERR|105 seguido de OK|PONG" "ERR|105|TOO_LONG / OK|PONG" "$long"

echo "== 9. interfaz web"
check "GET /health" "ok" "$(curl -s "http://$HOST:8080/health")"
check "GET /api/status es JSON con nodes" '"nodes":\[' "$(curl -s "http://$HOST:8080/api/status")"
check "GET / es HTML" "<title>" "$(curl -s "http://$HOST:8080/")"

echo "== 10. desconexion: al detener un nodo pasa a INACTIVE"
kill -INT "${pids[0]}"; wait "${pids[0]}" 2>/dev/null
sleep 1
check "NODE01 INACTIVE tras BYE" "NODE01 .*INACTIVE" "$($OP LIST_NODES 2>&1)"

echo "== limpieza"
for p in "${pids[@]:1}"; do kill -INT "$p" 2>/dev/null; done
wait 2>/dev/null
echo
if [ $fail -eq 0 ]; then echo "TODAS LAS COMPROBACIONES PASARON"; else echo "HAY FALLOS"; fi
exit $fail
