#!/usr/bin/env bash
# Envía el código del commit actual a la instancia y reconstruye el contenedor.
# El repositorio es privado, así que no se clona desde la instancia: se manda un tar por SSH.
#   deploy/deploy.sh [host]      (por defecto telemetria.digitdeck.co)
set -euo pipefail
HOST="${1:-telemetria.digitdeck.co}"
KEY="$(dirname "$0")/aws/telemetria-key.pem"
cd "$(dirname "$0")/.."
git archive --format=tar HEAD | ssh -i "$KEY" -o StrictHostKeyChecking=no "ubuntu@$HOST" '
  sudo mkdir -p /opt/telemetria && sudo chown ubuntu /opt/telemetria &&
  rm -rf /opt/telemetria/* && tar -x -C /opt/telemetria &&
  cd /opt/telemetria && sudo docker compose up -d --build server && sleep 2 &&
  sudo docker ps --filter name=telemetry-server && curl -s localhost:8080/health'
