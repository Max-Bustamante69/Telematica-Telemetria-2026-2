#!/usr/bin/env bash
# Autoriza una llave pública SSH de un integrante SOLO para reiniciar el contenedor.
# La llave queda con forced command: al conectar se ejecuta /usr/local/bin/reiniciar-telemetria y nada más.
#   deploy/autorizar-reinicio.sh "ssh-ed25519 AAAA... valeria-telemetria"
#   deploy/autorizar-reinicio.sh --revocar valeria-telemetria
set -euo pipefail
HOST="${HOST:-telemetria.digitdeck.co}"
KEY="$(dirname "$0")/aws/telemetria-key.pem"
if [ "${1:-}" = "--revocar" ]; then
  ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "ubuntu@$HOST" "sed -i '/ $2\$/d' ~/.ssh/authorized_keys && echo revocada: $2"
  exit 0
fi
PUB="$1"
LINE="command=\"/usr/local/bin/reiniciar-telemetria\",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty $PUB"
ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "ubuntu@$HOST" "grep -qF '$PUB' ~/.ssh/authorized_keys || echo '$LINE' >> ~/.ssh/authorized_keys; tail -1 ~/.ssh/authorized_keys | cut -c1-80"
echo "Valeria reinicia con:  ssh -i ~/.ssh/telemetria-valeria ubuntu@$HOST"
