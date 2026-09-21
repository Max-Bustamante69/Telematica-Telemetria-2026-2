"""Tarjetas 1920x1080 para superponer: código, terminal y tablas. Mismo estilo que las capturas (fondo oscuro)."""
import os, re
from PIL import Image, ImageDraw, ImageFont

W = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(W, "assets"); R = os.path.dirname(W)
MONO = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 30)
MONO_S = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 26)
UI = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 34)
UIB = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 40)
BG = (10, 10, 12, 235); PANEL = (24, 24, 28, 255); FG = (225, 225, 225); DIM = (150, 150, 150); ACC = (120, 190, 255); KW = (255, 190, 110)

def canvas():
    im = Image.new("RGBA", (1920, 1080), BG); return im, ImageDraw.Draw(im)

def code_card(name, title, lines, font=MONO, highlight=()):
    im, d = canvas()
    d.rounded_rectangle((120, 90, 1800, 990), 14, fill=PANEL, outline=(60, 60, 66, 255), width=2)
    d.text((160, 112), title, font=UIB, fill=ACC)
    y = 180; lh = font.size + 10
    for ln in lines[: int((980 - y) / lh)]:
        color = FG
        if any(h in ln for h in highlight): color = KW
        if ln.lstrip().startswith(("/*", "*", "//", "#")): color = DIM
        d.text((160, y), ln.rstrip("\n").replace("\t", "    ")[:110], font=font, fill=color); y += lh
    im.save(os.path.join(A, f"ov-{name}.png")); print("ov-" + name)

def src_lines(path, start, end):
    L = open(os.path.join(R, path), encoding="utf-8").read().split("\n")
    return L[start - 1:end]

def table_card(name, title, header, rows, colw):
    im, d = canvas()
    d.rounded_rectangle((120, 90, 1800, 990), 14, fill=PANEL, outline=(60, 60, 66, 255), width=2)
    d.text((160, 112), title, font=UIB, fill=ACC)
    x0 = 160; y = 190
    x = x0
    for h, w in zip(header, colw): d.text((x, y), h, font=UIB, fill=DIM); x += w
    y += 60; d.line((x0, y, 1760, y), fill=(70, 70, 76), width=2); y += 14
    for row in rows:
        x = x0
        for cell, w in zip(row, colw):
            d.text((x, y), cell, font=UI, fill=FG); x += w
        y += 52
    im.save(os.path.join(A, f"ov-{name}.png")); print("ov-" + name)

# --- código del servidor (líneas reales de los fuentes) ---
tcp = src_lines("server/src/tcp_operator.c", 23, 50)
code_card("code-tcp", "server/src/tcp_operator.c · socket, bind, listen", tcp, MONO_S, ("socket(", "bind(", "listen(", "accept("))
udp = src_lines("server/src/udp_telemetry.c", 14, 34) + ["", "    /* ... en el bucle del hilo UDP: */"] + src_lines("server/src/udp_telemetry.c", 44, 48) + src_lines("server/src/udp_telemetry.c", 54, 62)
code_card("code-udp", "server/src/udp_telemetry.c · socket UDP, recvfrom, sendto", udp, MONO_S, ("socket(", "bind(", "recvfrom(", "sendto("))
state = ["/* main.c */"] + src_lines("server/src/main.c", 27, 34) + [""] + src_lines("server/src/main.c", 47, 53) + ["", "/* state.c: todo acceso al estado pasa por el mutex */"] + src_lines("server/src/state.c", 12, 13) + src_lines("server/src/state.c", 24, 26) + ["", "/* tcp_operator.c: un hilo por cliente */"] + src_lines("server/src/tcp_operator.c", 139, 147)
code_card("code-state", "main.c, state.c, tcp_operator.c · señales, mutex y un hilo por cliente", state, MONO_S, ("SIGPIPE", "shutdown(", "pthread_mutex", "pthread_create", "pthread_detach"))
code_card("dockerfile", "Dockerfile · dos etapas: gcc compila, Debian slim ejecuta", open(os.path.join(R, "Dockerfile"), encoding="utf-8").read().split("\n"), MONO, ("FROM", "COPY --from", "EXPOSE", "HEALTHCHECK"))
code_card("docker-ps", "En la instancia EC2: docker ps", open(os.path.join(W, "docker-ps.txt"), encoding="utf-8").read().split("\n"), MONO_S, ("healthy", "114MB"))
code_card("nslookup", "nslookup telemetria.digitdeck.co", open(os.path.join(W, "nslookup.txt"), encoding="utf-8").read().split("\n"), MONO, ("100.25.236.127",))

# --- tablas del informe ---
table_card("tabla-errores", "Códigos de error de TLP/1.0", ["Código", "Texto", "Cuándo"],
           [["100", "BAD_FORMAT", "Faltan campos"], ["101", "UNKNOWN_COMMAND", "Tipo de mensaje desconocido"], ["102", "UNKNOWN_NODE", "El nodo consultado no existe"],
            ["103", "BAD_PARAM", "Parámetro inválido"], ["104", "NOT_REGISTERED", "Telemetría sin REGISTER (viaja por UDP)"], ["105", "TOO_LONG", "Línea de más de 512 bytes"], ["106", "SERVER_FULL", "Ya hay 64 nodos"]],
           [200, 420, 900])
table_card("tabla-transporte", "Transporte elegido por servicio", ["Servicio", "Transporte", "Por qué"],
           [["Telemetría periódica", "UDP 5000", "5 datagramas cada 2 s; perder uno no importa; seq cuenta pérdidas"],
            ["Registro del nodo", "TCP 5001", "Necesita el OK|REGISTERED confirmado"],
            ["Consultas del operador", "TCP 5001", "Respuestas largas, en orden y completas"],
            ["Alertas al operador", "TCP 5001", "Una alerta perdida es un incidente sin atender"],
            ["Interfaz web", "HTTP 8080", "Requisito del enunciado; solo lectura"]],
           [430, 260, 900])
table_card("tabla-pruebas", "Resultados medidos", ["Prueba", "Resultado"],
           [["tests/e2e.sh contra telemetria.digitdeck.co", "20 de 20 comprobaciones en verde"],
            ["loss_test.py, 500 datagramas desde Medellín", "500 recibidos, 0 perdidos, 478 msg/s"],
            ["loss_test.py local con 10 huecos deliberados", "9 de 10 detectados (el último no se puede distinguir)"],
            ["docker restart con nodo activo", "5 NACK|104, REGISTER y OK|REGISTERED en 11 s"],
            ["Datagramas basura y línea TCP de 700 bytes", "Contados como inválidos; el servidor sigue"]],
           [860, 800])
table_card("tabla-capas", "Qué añade cada capa", ["Capa", "Qué se vio en la captura"],
           [["Aplicación (TLP)", "TELEMETRY|NODE12|1|TEMP|24.5 en los bytes del datagrama"],
            ["Transporte UDP", "Puertos 49921 a 5000, longitud 37; sin conexión ni confirmación"],
            ["Transporte TCP", "SYN, SYN-ACK, ACK; seq y ack por byte; 85 ms de ida y vuelta"],
            ["Red (IP)", "192.168.58.130 a 100.25.236.127; NAT del router; TTL 128"],
            ["DNS", "Consulta A y respuesta 100.25.236.127 con TTL 260 s"]],
           [420, 1240])
