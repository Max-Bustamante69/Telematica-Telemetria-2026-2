"""Montaje del video de sustentación.

Orden que no se salta: normalizar (hecho) -> transcribir (hecho) -> corregir subtítulos contra el guion
-> montar cada clip con título y overlays -> concatenar -> subtítulos finales desplazados por el inicio real.

Uso:  python montaje.py            (renderiza todo a export/)
      python montaje.py --solo 03  (un clip, para revisar)
"""
import json, os, re, subprocess, sys

W = os.path.dirname(os.path.abspath(__file__))
NORM, SRT, ASSETS, WORK, EXPORT = [os.path.join(W, d) for d in ("norm", "srt", "assets_v2", "work", "export")]
os.makedirs(WORK, exist_ok=True); os.makedirs(EXPORT, exist_ok=True)
FONT = "segoeui.ttf"
FONTB = "segoeuib.ttf"

# ---------- 1. Clips: título, recorte y overlays (start, end en segundos del clip normalizado) ----------
# cam="full" = la grabación es solo cámara: los overlays van a pantalla completa y la cámara queda en una esquina.
# cam="screen" = la grabación ya es pantalla con cámara: los overlays van a media pantalla.
CLIPS = [
    dict(id="01-max-intro", who="Maximiliano Bustamante", title="1 · Presentación y problema", cam="full",
         trim=(0.0, 89.5),
         overlays=[("ov-arquitectura.png", 26.0, 71.0), ("ov-web-telemetria-digitdeck-co.png", 71.0, 84.0)]),
    dict(id="02-max-protocolo", who="Maximiliano Bustamante", title="2 · Protocolo TLP/1.0", cam="full",
         trim=(0.0, 119.5),
         overlays=[("ov-secuencia.png", 24.0, 65.0), ("ov-tabla-errores.png", 65.0, 88.0), ("ov-tabla-transporte.png", 88.0, 116.0)]),
    dict(id="03-max-servidor", who="Maximiliano Bustamante", title="3 · El servidor en C", cam="full",
         trim=(0.0, 106.5),
         overlays=[("ov-code-tcp.png", 11.0, 40.0), ("ov-code-udp.png", 40.0, 60.0), ("ov-code-state.png", 60.0, 92.0), ("ov-docker-ps.png", 92.0, 106.0)]),
    dict(id="04-max-nube", who="Maximiliano Bustamante", title="4 · Nube, DNS y Docker", cam="full",
         trim=(0.0, 107.5),
         overlays=[("ov-aws-instancia-security-group.png", 10.0, 45.0), ("ov-dns-cloudflare.png", 45.0, 73.0), ("ov-nslookup.png", 73.0, 86.0), ("ov-dockerfile.png", 86.0, 107.0)]),
    dict(id="05-val-nodos", who="Valeria Hornung", title="5 · Nodos de telemetría", cam="screen",
         trim=(0.0, 139.5), speed=1.06,
         overlays=[("ov-secuencia.png", 24.0, 46.0)]),
    dict(id="06-val-operador", speed=1.06, who="Valeria Hornung", title="6 · Cliente operador y alertas", cam="screen",
         trim=(0.0, 193.5), overlays=[]),
    dict(id="07-val-fallos", speed=1.06, who="Valeria Hornung", title="7 · Recuperación ante fallos y pruebas", cam="screen",
         trim=(0.0, 153.8),
         overlays=[("ov-tabla-pruebas.png", 125.0, 153.0)]),
    dict(id="08-val-wireshark", speed=1.06, who="Valeria Hornung", title="8 · Análisis de tráfico con Wireshark", cam="screen",
         trim=(0.0, 214.5),
         overlays=[("ov-tabla-capas.png", 192.0, 214.0)]),
]

# ---------- 2. Correcciones de la transcripción contra el guion (whisper falla en nombres y términos) ----------
FIX = [
    (r"Maximilianus Tamanty Val\s*eria", "Maximiliano Bustamante y Valeria"), (r"Maximilianus", "Maximiliano"),
    (r"tiene sentido\.", "tiene sensores"), (r"equip\s+os\.", "equipos."), (r"activ\s+ado", "activado"),
    (r"nuevos de telemetr", "nodos de telemetr"), (r"amazon s2", "Amazon EC2"), (r"Amazon S2", "Amazon EC2"),
    (r"nombre\s+de nes", "nombre DNS"), (r"el punto digit deck\.co", "telemetria.digitdeck.co"), (r"punto iridec punto ceo", "punto digitdeck punto co"),
    (r"pipelines", "barras verticales"), (r"cient�ficador", "su identificador"), (r"identificador", "identificador"),
    (r"ubic\s+aci�n", "ubicaci�n"), (r"puerto de P", "puerto UDP"), (r"sec\s+uencia", "secuencia"),
    (r"list nodes", "LIST_NODES"), (r"getlast", "GET_LAST"), (r"getstatus", "GET_STATUS"), (r'"end"', "END"),
    (r"regist\s+rado", "registrado"), (r"por WP", "por UDP"), (r"cada no domanda 5 dg", "cada nodo manda 5 datagramas"),
    (r"cu�ntos di�mes", "cu�ntos datagramas"), (r"pues de p�rdida", "perdida"),
    (r"los objetos", "los sockets"), (r"dos objetos 1 TCP", "dos sockets: uno TCP"), (r"mens\s+aje", "mensaje"),
    (r"desalto de l�nea", "corte por salto de l�nea"), (r"cada diagrama", "cada datagrama"), (r"al form", "con recvfrom"),
    (r"con Centrum", "con sendto"), (r"el no no est�", "el nodo no est�"), (r"no, dos mediciones", "nodos, mediciones"),
    (r"varios h\s+ilos", "varios hilos"), (r"puesto el rato", "al mismo tiempo"), (r"sick pipe", "SIGPIPE"), (r"sickterm", "SIGTERM"),
    (r"los okeds", "los sockets"), (r"y aqu� es el video\.?\s*estar�a al docker\.ps", "y aqu� est� docker ps"), (r"contenerizadosin", "contenerizado sin"), (r"El contador est�", "El contenedor est�"),
    (r"el check dice", "el healthcheck dice"), (r"Virinia", "Virginia"), (r"en la cl\s+ave\.", "en la clase."),
    (r"el 50001", "el 5001"), (r"8080 para el UDP\. por tener", "8080 para tener"), (r"IP el�st\s+ica", "IP el�stica"),
    (r"100\.25\.136\.127", "100.25.236.127"), (r"100\.25\.136\.", "100.25.236.127"), (r"100\.25\.166\.127", "100.25.236.127"),
    (r"registro a de clover", "registro A de Cloudflare"), (r"la direcci�n y p", "la direcci�n IP"), (r"prox\s*ie clover", "proxy de Cloudflare"),
    (r"proxie", "proxy"), (r"lo compramos en vivo con el Enzlookup", "lo comprobamos en vivo con nslookup"), (r"esplegar", "desplegar"),
    (r"la devian\.", "Debian,"), (r"114 meg\s+abytes", "114 megabytes"),
    (r"provee mi nombre", "profe, mi nombre"), (r"nudos", "nodos"), (r"5/8", "5 nodos"), (r"serv\s+idor", "servidor"),
    (r"Jeter Info", "getaddrinfo"), (r"OK register", "OK REGISTERED"), (r"con register", "con REGISTER"),
    (r"un accidento 4", "un NACK 104"), (r"as� en intervenci�n", "sin intervenci�n"), (r"5 nodes", "5 nodos"),
    (r"DNS, DJT\.co", "DNS: telemetria.digitdeck.co"), (r"reyesar", "REGISTER"), (r"reaniciar", "recargar"),
    (r"\[AUDIO_EN_BLANCO\]", ""), (r"\[M�SICA\]", ""), (r"Last, o sea cuando utilizamos GetLast y Unidentificador", "Con GET_LAST y un identificador"),
    (r"de Seno", "de ese nodo"), (r"Note 0", "NODE0"), (r"GetStatus", "GET_STATUS"), (r"system status", "SYSTEM_STATUS"),
    (r"IP loss, IP project", "udp_lost, udp_rejected"), (r"1, 0, 1", "101"), (r"error 100 todos", "error 102"), (r"node 099", "NODE99"),
    (r"subscribes alert, alerta", "SUBSCRIBE_ALERTS"), (r"Force Alert Temp", "force-alert TEMP"), (r"Force Alert", "force-alert"),
    (r"Temps 2 High", "TEMP_HIGH"), (r"Temps too high", "TEMP_HIGH"), (r"Temp High", "TEMP_HIGH"), (r"Num High", "HUM_HIGH"), (r"Temtuhai", "TEMP_HIGH"),
    (r"Get alerts", "GET_ALERTS"), (r"el 9\.06", "el NODE06"), (r"nuevo 6", "NODE06"),
    (r"5 NAC 104", "5 NACK 104"), (r"ok register", "OK REGISTERED"), (r"register otra vez", "REGISTER otra vez"),
    (r'manda "byport\.cp"', "manda BYE por TCP"), (r"el nuevo 5", "el NODE05"), (r"ese no 05", "ese NODE05"), (r"los no,", "los nodos,"),
    (r"por E2E", "con tests/e2e.sh"), (r"Parez con provaciones", "Son 20 comprobaciones"), (r"ese no 0 6", "ese NODE06"),
    (r"Wehr\s*schark", "Wireshark"), (r"un oper\s+ador", "un operador"), (r"la Nui", "la nube"),
    (r"filtro de P\. con portico a las 5\.000", "filtro udp.port==5000"), (r"190, de unos 680, 5830", "192.168.58.130"),
    (r"100, 2530, 627", "100.25.236.127"), (r"puerto de signo", "puerto destino"), (r"telemetrino 12 1 temp 24\.5", "TELEMETRY|NODE12|1|TEMP|24.5"),
    (r"conex\s+i�n", "conexi�n"), (r"TCP stream igual la 1", "tcp.stream==1"), (r"sin sin\s+ac y ac", "SYN, SYN-ACK y ACK"),
    (r"saludo 3v�as", "saludo de tres v�as"), (r"85 milisimundos entre sin y el sinac", "85 milisegundos entre SYN y SYN-ACK"),
    (r"push hack", "PSH-ACK"), (r"el hack del servidor", "el ACK del servidor"), (r"Get Last", "GET_LAST"), (r"OK buy", "OK|BYE"),
    (r"\$299", "269"), (r"el DDS, SNS query", "dns.qry.name"), (r"TTP de 260", "TTL de 260"), (r"UDP o TCP A�ada\.", "UDP o TCP a�aden"),
    (r"El IP a�ade", "IP a�ade"), (r"prev\s+iamente", "previamente"),
]

def load_srt(path):
    cues = []
    for block in open(path, encoding="utf-8").read().strip().split("\n\n"):
        lines = block.split("\n")
        if len(lines) < 3: continue
        m = re.match(r"(\d\d):(\d\d):(\d\d),(\d+) --> (\d\d):(\d\d):(\d\d),(\d+)", lines[1])
        a = int(m[1])*3600+int(m[2])*60+int(m[3])+int(m[4])/1000
        b = int(m[5])*3600+int(m[6])*60+int(m[7])+int(m[8])/1000
        cues.append([a, b, " ".join(lines[2:]).strip()])
    return cues

def fix_text(t):
    for pat, rep in FIX: t = re.sub(pat, rep, t)
    return re.sub(r"\s+", " ", t).strip()

def regroup(cues, max_chars=84, max_dur=6.0):
    """Whisper parte palabras entre cues. Se juntan fragmentos en frases de hasta dos líneas."""
    out = []; cur = None
    for a, b, t in cues:
        if cur is None: cur = [a, b, t]; continue
        joined = (cur[2] + ("" if re.search(r"\w$", cur[2]) and re.match(r"^[a-z��������]{1,4}", t) and len(t.split()[0]) <= 4 else " ") + t)
        if len(joined) <= max_chars and b - cur[0] <= max_dur and not re.search(r"[.?!]$", cur[2]):
            cur[1] = b; cur[2] = joined
        else:
            out.append(cur); cur = [a, b, t]
    if cur: out.append(cur)
    res = []
    for a, b, t in out:
        t = fix_text(t)
        if not t: continue
        if b - a < 0.8: b = a + 0.8
        if res and a < res[-1][1]: res[-1][1] = a  # nunca solapar: se recorta la anterior
        res.append([a, b, t])
    return res

def two_lines(t, width=58):
    if len(t) <= width: return t
    words = t.split(); l1 = ""
    for w in words:
        if len(l1) + len(w) + 1 > width: break
        l1 += (" " if l1 else "") + w
    return l1 + "\\N" + t[len(l1):].strip()

def ass_time(s):
    h = int(s // 3600); m = int(s % 3600 // 60); sec = s % 60
    return f"{h}:{m:02d}:{sec:05.2f}"

ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Segoe UI Semibold,46,&H00FFFFFF,&H00FFFFFF,&H30000000,&H70000000,0,0,0,0,100,100,0.4,0,1,2,4,2,160,160,48,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def write_ass(cues, path, offset=0.0):
    with open(path, "w", encoding="utf-8") as f:
        f.write(ASS_HEAD)
        for a, b, t in cues:
            if offset == 0.0 and a < 4.2:  # durante la tarjeta de sección no hay subtítulo
                if b <= 4.4: continue
                a = 4.2
            f.write("Dialogue: 0," + ass_time(a+offset) + "," + ass_time(b+offset) + ",Sub,,0,0,0,,{\\fad(120,120)}" + two_lines(t) + "\n")

def write_srt(cues, path, offset=0.0):
    def st(s):
        h = int(s // 3600); m = int(s % 3600 // 60); sec = int(s % 60); ms = int(round((s - int(s)) * 1000))
        return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"
    with open(path, "w", encoding="utf-8") as f:
        for i, (a, b, t) in enumerate(cues, 1):
            f.write(f"{i}\n{st(a+offset)} --> {st(b+offset)}\n{two_lines(t).replace(chr(92)+'N', chr(10))}\n\n")

def esc(s):  # para drawtext
    return s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%")

def render_clip(c):
    src = os.path.join(NORM, c["id"] + ".mp4")
    t0, t1 = c["trim"]; cut = c.get("cut"); speed = c.get("speed", 1.0)
    def remap(t):  # tiempo original -> tiempo en el clip final (tras trim, cut y speed)
        t = t - t0
        if cut:
            ca, cb = cut[0] - t0, cut[1] - t0
            if t > cb: t -= (cb - ca)
            elif t > ca: t = ca
        return t
    dur = remap(t1)
    cues = [[remap(a), remap(b), t] for a, b, t in regroup(load_srt(os.path.join(SRT, c["id"] + ".srt"))) if a >= t0 and a < t1 and not (cut and cut[0] <= a < cut[1])]
    ovl = [(ov, remap(a), remap(b)) for ov, a, b in c["overlays"]]
    c = dict(c, overlays=ovl)
    ass = os.path.join(WORK, c["id"] + ".ass"); write_ass(cues, ass)
    inputs = ["-ss", f"{t0}", "-t", f"{dur}", "-i", src]
    for ov, _, _ in c["overlays"]:
        inputs += ["-loop", "1", "-t", f"{dur}", "-i", os.path.join(ASSETS, ov)]
    # cadena: base -> overlays (fade 0.4 s) -> cámara en esquina cuando hay overlay (solo cam=full) -> título 0-5 s -> subtítulos
    vpre = "[0:v]"; apre = "[0:a]"
    f = []
    if cut:
        ca, cb = cut[0] - t0, cut[1] - t0
        f.append(f"[0:v]trim=0:{ca},setpts=PTS-STARTPTS[v1c];[0:v]trim={cb},setpts=PTS-STARTPTS[v2c]")
        f.append(f"[0:a]atrim=0:{ca},asetpts=PTS-STARTPTS[a1c];[0:a]atrim={cb},asetpts=PTS-STARTPTS[a2c]")
        f.append("[v1c][a1c][v2c][a2c]concat=n=2:v=1:a=1[vc][ac]")
        vpre, apre = "[vc]", "[ac]"
    f.append(f"{vpre}format=yuv420p,split=3[base][cam][cam2]")
    f.append(f"{apre}anull[aout]")
    last = "base"
    if c["cam"] == "full" and c["overlays"]:
        # miniatura de la cámara, abajo a la derecha, visible mientras haya overlay
        f.append("[cam]scale=416:234,format=yuva420p[pipraw]"); inputs += ["-loop", "1", "-t", f"{dur}", "-i", os.path.join(W, "pip-mask.png")]; f.append(f"[{len(c['overlays'])+1}:v]format=gray,scale=416:234[pm]"); f.append("[pipraw][pm]alphamerge[pip]")
    else:
        f.append("[cam]nullsink")
    for i, (ov, a, b) in enumerate(c["overlays"], 1):
        fade = f"fade=t=in:st={a}:d=0.6:alpha=1,fade=t=out:st={b-0.6}:d=0.6:alpha=1"
        if c["cam"] == "full":
            f.append(f"[{i}:v]format=yuva420p,{fade}[ov{i}]")
            f.append(f"[{last}][ov{i}]overlay=0:0:enable='between(t,{a},{b})'[v{i}]")
        else:
            f.append(f"[{i}:v]scale=1152:648,format=yuva420p,{fade}[ov{i}]")
            f.append(f"[{last}][ov{i}]overlay=W-w-40:40:enable='between(t,{a},{b})'[v{i}]")
        last = f"v{i}"
    if c["cam"] == "full" and c["overlays"]:
        en = "+".join(f"between(t,{a},{b})" for _, a, b in c["overlays"])
        f.append(f"[{last}][pip]overlay=W-w-32:H-h-32:enable='{en}'[vp]"); last = "vp"
    # tarjeta de sección (0 a 4.2 s): la propia imagen desenfocada y oscurecida, título ligero que entra desde abajo, nombre y línea fina
    T0, T1 = 0.0, 4.2
    f.append(f"[cam2]scale=480:270,gblur=sigma=18,scale=1920:1080,eq=brightness=-0.35:saturation=0.7,format=yuva420p,fade=t=out:st={T1-0.6}:d=0.6:alpha=1[blur]")
    f.append(f"[{last}][blur]overlay=0:0:enable='between(t,{T0},{T1})'[vb]")
    slide = "if(lt(t\,0.9)\,40*(1-t/0.9)*(1-t/0.9)\,0)"   # ease-out desde 40 px abajo (comas escapadas para drawtext)
    alpha_in = "if(lt(t\,0.9)\,t/0.9\,1)"
    fade_out = f"if(gt(t\,{T1-0.6})\,1-(t-{T1-0.6})/0.6\,1)"
    f.append(f"[vb]drawtext=fontfile=segoeuil.ttf:text='{esc(c['title'].split(' · ',1)[1])}':fontsize=96:fontcolor=white:alpha='({alpha_in})*({fade_out})':x=(w-text_w)/2:y=(h-text_h)/2-40+{slide}:enable='between(t,{T0},{T1})',"
             f"drawtext=fontfile=seguisb.ttf:text='{esc(c['title'].split(' · ',1)[0])}':fontsize=30:fontcolor=0xE0E0E0@0.85:alpha='({alpha_in})*({fade_out})':x=(w-text_w)/2:y=(h-text_h)/2-150+{slide}:enable='between(t,{T0},{T1})',"
             f"drawbox=x=(iw-120)/2:y=ih/2+58:w=120:h=2:color=white@0.6:t=fill:enable='between(t,{T0+0.6},{T1-0.5})',"
             f"drawtext=fontfile=segoeuisl.ttf:text='{esc(c['who'])}':fontsize=38:fontcolor=white@0.9:alpha='({alpha_in})*({fade_out})':x=(w-text_w)/2:y=(h-text_h)/2+90+{slide}:enable='between(t,{T0+0.3},{T1})',"
             f"drawtext=fontfile=segoeuisl.ttf:text='Plataforma distribuida de telemetría · Telemática · EAFIT':fontsize=26:fontcolor=white@0.55:alpha='({alpha_in})*({fade_out})':x=(w-text_w)/2:y=h-90:enable='between(t,{T0+0.3},{T1})'[vt]")
    f.append(f"[vt]ass='{os.path.basename(ass)}'[vout]")
    out = os.path.join(WORK, c["id"] + ".v2.mp4")
    cmd = ["ffmpeg", "-y", "-v", "warning", *inputs, "-filter_complex", ";".join(f), "-map", "[vout]", "-map", "[aout]",
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out]
    print("==", c["id"], f"{dur:.1f}s", len(cues), "cues")
    subprocess.run(cmd, cwd=WORK, check=True)
    if speed != 1.0:
        fast = out.replace(".mp4", ".fast.mp4")
        subprocess.run(["ffmpeg", "-y", "-v", "warning", "-i", out, "-filter_complex", f"[0:v]setpts=PTS/{speed}[v];[0:a]atempo={speed}[a]",
                        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-r", "30", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", fast], check=True)
        out = fast; dur = dur / speed; cues = [[a / speed, b / speed, t] for a, b, t in cues]
    return out, dur, cues

def main():
    solo = sys.argv[sys.argv.index("--solo") + 1] if "--solo" in sys.argv else None
    parts = []; allcues = []; offset = 0.0
    for c in CLIPS:
        if solo and not c["id"].startswith(solo): continue
        out, dur, cues = render_clip(c)
        parts.append(out); allcues += [[a + offset, b + offset, t] for a, b, t in cues]; offset += dur
    if solo: return
    lst = os.path.join(WORK, "concat.txt")
    open(lst, "w", encoding="utf-8").write("".join(f"file '{p.replace(chr(92), '/')}'\n" for p in parts))
    final = os.path.join(EXPORT, "sustentacion-telemetria-v2-1080p.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", final], check=True)
    # subtítulos finales DESPUÉS del montaje, desplazados por el inicio real de cada parte
    write_srt(allcues, os.path.join(EXPORT, "sustentacion-telemetria-v2.es-CO.srt"))
    vtt = os.path.join(EXPORT, "sustentacion-telemetria-v2.es-CO.vtt")
    srt_txt = open(os.path.join(EXPORT, "sustentacion-telemetria-v2.es-CO.srt"), encoding="utf-8").read()
    open(vtt, "w", encoding="utf-8").write("WEBVTT\n\n" + re.sub(r"(\d\d:\d\d:\d\d),(\d\d\d)", r"\1.\2", srt_txt))
    print("FINAL", final, f"{offset/60:.1f} min")

if __name__ == "__main__":
    main()
