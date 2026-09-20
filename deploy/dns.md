# DNS

El nombre que usan los nodos y los operadores es `telemetria.digitdeck.co`. El código nunca contiene la IP pública: los clientes llaman a `getaddrinfo()` y el resultado se imprime en la primera línea de cada componente.

## Registro en Cloudflare

Zona `digitdeck.co`, panel DNS:

| Tipo | Nombre | Contenido | Proxy | TTL |
|---|---|---|---|---|
| A | `telemetria` | IP pública de la instancia EC2 | Desactivado (nube gris, "DNS only") | Auto |

El proxy de Cloudflare debe quedar apagado. El proxy solo reenvía HTTP y HTTPS, así que con el proxy activo el tráfico UDP 5000 y TCP 5001 nunca llegaría a la instancia.

Con la API de Cloudflare (token con permiso `Zone.DNS:Edit`):

```bash
ZONE_ID=...; TOKEN=...; IP=...
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  --data "{\"type\":\"A\",\"name\":\"telemetria\",\"content\":\"$IP\",\"ttl\":1,\"proxied\":false}"
```

## Verificación

```bash
nslookup telemetria.digitdeck.co
dig +short telemetria.digitdeck.co
python -c "import socket; print(socket.gethostbyname('telemetria.digitdeck.co'))"
```

Los tres deben devolver la IP de la instancia. Si la instancia se reinicia sin IP elástica, la IP cambia y hay que actualizar el registro. Para evitarlo se puede asociar una Elastic IP:

```bash
aws ec2 allocate-address --domain vpc
aws ec2 associate-address --instance-id <id> --allocation-id <eipalloc-...>
```
