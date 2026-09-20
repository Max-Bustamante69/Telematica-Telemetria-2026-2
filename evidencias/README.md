# Evidencias individuales

Cada integrante guarda aquí sus capturas de pantalla, con el nombre `<integrante>-<numero>-<que-muestra>.png`. Las capturas se referencian en la sección 12 del informe.

Cada integrante necesita como mínimo dos capturas tomadas en su propio computador.

En Windows los dos scripts de esta carpeta hacen todo: `pwsh -File evidencias\capturar.ps1 NODE12 "Casa de Valeria"` y `pwsh -File evidencias\capturar-operador.ps1`. Tomar la captura con la ventana completa.

## Captura 1: identidad y ejecución de un componente

En la misma terminal, sin cerrarla:

Windows (PowerShell):

```powershell
whoami; hostname; Get-Date
python node\node.py --id NODE0X --server telemetria.digitdeck.co --location "Casa de <nombre>"
```

Linux o macOS:

```bash
whoami; hostname; date
python3 node/node.py --id NODE0X --server telemetria.digitdeck.co --location "Casa de <nombre>"
```

La captura debe mostrar el usuario, el hostname, la fecha, la línea `DNS: telemetria.digitdeck.co -> <IP>`, el `OK|REGISTERED` y varias líneas `UDP -> TELEMETRY|...`.

## Captura 2: consulta al servidor en la nube

```powershell
whoami; hostname; Get-Date
python operator_client\operator_client.py --server telemetria.digitdeck.co --cmd LIST_NODES
```

Debe verse el nodo del integrante en la lista.

## Capturas del equipo (una vez, quien despliega)

- `aws-instancia.png`: consola EC2 con la instancia en estado running y su IP pública.
- `aws-security-group.png`: reglas de entrada 22/tcp, 5000/udp, 5001/tcp, 8080/tcp.
- `docker-ps.png`: `docker ps` y `docker logs telemetry-server` por SSH en la instancia.
- `docker-build.png`: salida de `docker compose build server` en la instancia.
- `dns-cloudflare.png`: registro A `telemetria` en el panel DNS.
- `dns-nslookup.png`: `nslookup telemetria.digitdeck.co` desde un equipo del grupo.
- `web.png`: http://telemetria.digitdeck.co:8080 con nodos y alertas.
- `wireshark-udp.png`, `wireshark-tcp-handshake.png`, `wireshark-dns.png`: ver `docs/WIRESHARK.md`.
- `e2e.png`: salida de `tests/e2e.sh telemetria.digitdeck.co`.
- `loss.png`: salida de `tests/loss_test.py --server telemetria.digitdeck.co --count 500`.
