# Valeria: todo lo que tienes que correr, en orden

Todo se hace en tu computador con Windows. El servidor ya está en la nube (`telemetria.digitdeck.co`), no tienes que instalar nada de C ni de Docker. Cuando dice "captura" es una imagen fija (Win+Shift+S, recorta la ventana entera, guárdala con ese nombre en `evidencias/`). Cuando dice "clip" es un video de pantalla con tu cámara en la esquina (OBS, o la grabación de Teams o Zoom), leyendo del teleprompter `docs/video/teleprompter-valeria.html`.

## Parte 0: preparar el equipo (una sola vez, 15 min)

1. Instala Python 3 desde https://www.python.org/downloads/ marcando "Add python.exe to PATH".
2. Instala Git desde https://git-scm.com/download/win con las opciones por defecto.
3. Instala Wireshark desde https://www.wireshark.org/download.html (el instalador te ofrece Npcap: acéptalo).
4. Acepta la invitación al repositorio privado que te llega al correo de GitHub.
5. Abre PowerShell y clona el proyecto:

```powershell
cd $HOME\Desktop
git clone https://github.com/Max-Bustamante69/Telematica-Telemetria-2026-2.git
cd Telematica-Telemetria-2026-2
```

6. Comprueba que llegas al servidor:

```powershell
python operator_client\operator_client.py --server telemetria.digitdeck.co --cmd PING
```

Debe responder `OK|PONG`. Si dice "no se pudo conectar", avísale a Max antes de seguir.

## Parte 1: tus dos evidencias individuales (5 min)

Son obligatorias por el enunciado (sección 12.3): tienen que salir de tu computador con tu usuario y tu hostname.

7. Terminal 1, nodo:

```powershell
pwsh -File evidencias\capturar.ps1 NODE21 "Casa de Valeria"
```

Espera a que salgan 15 o 20 líneas `UDP -> TELEMETRY|NODE21|...`.

**Captura 1:** la ventana completa, desde `whoami` hasta las líneas de telemetría. Guarda como `evidencias/valeria-1-nodo.png`. Deja ese nodo corriendo.

8. Terminal 2, operador:

```powershell
pwsh -File evidencias\capturar-operador.ps1
```

**Captura 2:** la ventana completa; tiene que verse `NODE21` en la lista. Guarda como `evidencias/valeria-2-operador.png`.

9. Cierra el nodo de la terminal 1 con Ctrl+C.

## Parte 2: clips del video

Antes de cada clip: abre `docs/video/teleprompter-valeria.html` (doble clic), pulsa el número del clip para saltar a su texto, F para pantalla completa, y espacio para que avance. Ponlo en el celular o en un segundo monitor cerca de la cámara. Graba cada clip de corrido; si te equivocas, callas dos segundos y repites la frase.

### Clip 05: `05-val-nodos.mp4` (2 min)

Preparación: cinco terminales de PowerShell en la carpeta del proyecto y el navegador en http://telemetria.digitdeck.co:8080. No los arranques todavía.

10. Empieza a grabar. Lee el texto del clip 1 del teleprompter.
11. Cuando el texto llega a "Aquí lanzo cinco nodos", ejecuta uno por terminal:

```powershell
python node\node.py --id NODE01 --server telemetria.digitdeck.co --location "Planta Norte"
python node\node.py --id NODE02 --server telemetria.digitdeck.co --location "Bodega Sur"
python node\node.py --id NODE03 --server telemetria.digitdeck.co --location "Subestacion Este"
python node\node.py --id NODE04 --server telemetria.digitdeck.co --location "Torre de Enfriamiento"
python node\node.py --id NODE05 --server telemetria.digitdeck.co --location "Cuarto de Bombas"
```

12. Muestra en una de ellas la línea `DNS: telemetria.digitdeck.co -> 100.25.236.127` y `TCP <- OK|REGISTERED`.
13. Cambia al navegador y recarga: los cinco en `ACTIVE`, "Recibidos" subiendo, "Perdidos" en 0.

**Captura 3:** el navegador con los cinco nodos `ACTIVE`. Guarda como `evidencias/valeria-3-web.png`.

14. Termina de leer el texto y para la grabación. Deja los cinco nodos corriendo para los siguientes clips.

### Clip 06: `06-val-operador.mp4` (2 min)

Preparación: dos terminales más. En la primera arranca el operador y déjalo en el menú:

```powershell
python operator_client\operator_client.py --server telemetria.digitdeck.co
```

15. Empieza a grabar. Lee el texto del clip 2 y ve escribiendo en el operador, en este orden, cuando el texto los nombra:

```
LIST_NODES
GET_LAST|NODE03
GET_STATUS|NODE01
SYSTEM_STATUS
HOLA
GET_STATUS|NODE99
SUBSCRIBE_ALERTS
```

`HOLA` responde `error 101`; `NODE99` responde `error 102`.

16. Cuando el texto diga "en otra terminal, lanzo un nodo con la opción force alert", ejecuta en la segunda terminal:

```powershell
python node\node.py --id NODE06 --server telemetria.digitdeck.co --location "Caldera" --force-alert TEMP
```

17. Vuelve al operador: aparecen solas líneas `** ALERTA en tiempo real: ALERT|NODE06|TEMP_HIGH|...`. Escribe `GET_ALERTS` y muestra la lista. Recarga la web y muestra la tabla "Alertas recientes".

**Captura 4:** el operador con las alertas en tiempo real. Guarda como `evidencias/valeria-4-alerta.png`.

18. Para la grabación. Cierra el nodo NODE06 con Ctrl+C. Deja el operador abierto.

### Clip 07: `07-val-fallos.mp4` (1:30)

Preparación: este clip necesita reiniciar el contenedor en la nube. Hay dos formas: Max te pasa por un canal privado el archivo `telemetria-key.pem` y lo guardas en `deploy\aws\`, o Max ejecuta el reinicio cuando tú se lo digas por llamada. Ten a la vista la terminal de NODE01.

19. Empieza a grabar. Lee el texto del clip 3.
20. Al decir "reinicio el contenedor", ejecuta (o pide a Max que ejecute):

```powershell
ssh -i deploy\aws\telemetria-key.pem ubuntu@telemetria.digitdeck.co "sudo docker restart telemetry-server"
```

21. Mira la terminal de NODE01: en unos 10 segundos salen `UDP <- NACK|104|NOT_REGISTERED` (cinco veces), luego `TCP -> REGISTER|NODE01|...` y `TCP <- OK|REGISTERED|NODE01|5000`, y sigue la telemetría.

**Captura 5:** la terminal de NODE01 con los NACK y el nuevo REGISTER. Guarda como `evidencias/valeria-5-reinicio.png`.

22. Al decir "si detengo un nodo con control C", pulsa Ctrl+C en la terminal de NODE05: sale `TCP <- OK|BYE`. En el operador escribe `LIST_NODES`: NODE05 aparece `INACTIVE`.
23. Al decir "tests e2e", en una terminal nueva ejecuta (necesita Git Bash, que se instaló con Git):

```powershell
& "C:\Program Files\Git\bin\bash.exe" tests/e2e.sh telemetria.digitdeck.co
```

Tarda unos 40 segundos y termina con `TODAS LAS COMPROBACIONES PASARON`.

**Captura 6:** el final de la salida con las líneas `[ok]` y el mensaje final. Guarda como `evidencias/valeria-6-e2e.png`.

24. Al decir "la prueba de conteo", ejecuta:

```powershell
python tests\loss_test.py --server telemetria.digitdeck.co --count 500
```

**Captura 7:** el resumen (transmitidos, recibidos, perdidos). Guarda como `evidencias/valeria-7-perdida.png`.

25. Para la grabación.

### Clip 08: `08-val-wireshark.mp4` (2:30)

Preparación: abre Wireshark y el archivo `captures\telemetria-tcp-udp-dns.pcapng` del repositorio (Archivo, Abrir). Es la captura ya tomada; no hace falta capturar en vivo. Ten estos tres filtros copiados:

```
udp.port==5000 && frame contains "NODE12"
tcp.stream==1
dns.qry.name contains "telemetria"
```

26. Empieza a grabar. Lee el texto del clip 4.
27. Pega el primer filtro en la barra verde y Enter. Haz clic en el paquete 101. En el panel de detalles abre "Internet Protocol Version 4" (origen 192.168.58.130, destino 100.25.236.127), "User Datagram Protocol" (puertos 49921 y 5000, longitud 37) y "Data": en el panel de bytes de la derecha se lee `TELEMETRY|NODE12|1|TEMP|24.5`.
28. Pega el segundo filtro. Señala los tres primeros paquetes (SYN, SYN ACK, ACK), el 269 con `GET_LAST|NODE12`, el 271 con la respuesta de 160 bytes, el 272 `QUIT` y los FIN. Clic derecho en el 269, "Follow", "TCP Stream" para ver la conversación en texto; ciérralo.
29. Pega el tercer filtro. Clic en el paquete 89 y abre "Domain Name System (response)", "Answers": `telemetria.digitdeck.co: type A, addr 100.25.236.127`, TTL 260.
30. Termina el texto y para la grabación.

Si además quieres una captura tuya (opcional, suma como evidencia individual): en PowerShell como administrador, con NODE01 corriendo,

```powershell
& "C:\Program Files\Wireshark\tshark.exe" -D
& "C:\Program Files\Wireshark\tshark.exe" -i <numero de tu Wi-Fi o Ethernet> -f "host 100.25.236.127" -a duration:20 -w captures\valeria.pcapng
```

y ábrela en Wireshark igual que la otra.

## Parte 3: entregar

31. Cierra los nodos que queden con Ctrl+C.
32. Manda a Max una carpeta con los cuatro clips (`05-val-nodos.mp4`, `06-val-operador.mp4`, `07-val-fallos.mp4`, `08-val-wireshark.mp4`) y las siete capturas `valeria-1` a `valeria-7`. Las capturas también pueden subirse al repositorio:

```powershell
git add evidencias\valeria-*.png
git commit -m "evidencias: capturas de Valeria"
git push
```

## Resumen de capturas

| Archivo | Qué muestra |
|---|---|
| `valeria-1-nodo.png` | whoami, hostname, fecha, DNS, REGISTER y telemetría de NODE21 |
| `valeria-2-operador.png` | whoami, hostname, nslookup, LIST_NODES con NODE21, alertas y SYSTEM_STATUS |
| `valeria-3-web.png` | http://telemetria.digitdeck.co:8080 con cinco nodos ACTIVE |
| `valeria-4-alerta.png` | operador recibiendo ALERT en tiempo real |
| `valeria-5-reinicio.png` | NODE01 con NACK 104 y nuevo REGISTER tras docker restart |
| `valeria-6-e2e.png` | tests/e2e.sh con TODAS LAS COMPROBACIONES PASARON |
| `valeria-7-perdida.png` | loss_test con 500 enviados y 500 recibidos |
