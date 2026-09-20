#!/usr/bin/env bash
# Demo local sin Docker: servidor + 5 nodos normales + 1 nodo que fuerza alertas.
#   tests/demo.sh start | stop | status
# Logs en /tmp/telemetry-demo/. Útil para el video y para capturas.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG=/tmp/telemetry-demo
HOST="${HOST:-localhost}"

case "${1:-start}" in
  start)
    mkdir -p "$LOG"
    if [ "$HOST" = "localhost" ]; then
      [ -x "$ROOT/server/build/telemetry-server" ] || make -C "$ROOT/server"
      setsid "$ROOT/server/build/telemetry-server" >"$LOG/server.log" 2>&1 &
      sleep 1
    fi
    for i in 1 2 3 4 5; do
      setsid python3 "$ROOT/node/node.py" --id "NODE0$i" --server "$HOST" --location "Sitio $i" --interval 2 >"$LOG/node0$i.log" 2>&1 &
    done
    setsid python3 "$ROOT/node/node.py" --id NODE06 --server "$HOST" --location "Caldera" --interval 4 --force-alert TEMP >"$LOG/node06.log" 2>&1 &
    sleep 3
    echo "servidor y 6 nodos corriendo; logs en $LOG"
    python3 "$ROOT/operator_client/operator_client.py" --server "$HOST" --cmd LIST_NODES
    ;;
  stop)
    pkill -INT -f "node/node.py" 2>/dev/null
    sleep 1
    pkill -INT -f telemetry-server 2>/dev/null
    echo "detenido"
    ;;
  status)
    python3 "$ROOT/operator_client/operator_client.py" --server "$HOST" --cmd SYSTEM_STATUS
    python3 "$ROOT/operator_client/operator_client.py" --server "$HOST" --cmd GET_ALERTS
    ;;
esac
