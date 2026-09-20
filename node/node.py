#!/usr/bin/env python3
"""Nodo de telemetría simulado (protocolo TLP/1.0).

Flujo:
  1. Resuelve el nombre DNS del servidor (getaddrinfo) y muestra la IP obtenida.
  2. Se registra por TCP (REGISTER) y espera OK|REGISTERED.
  3. Envía mediciones por UDP cada INTERVAL segundos, una variable por datagrama,
     con número de secuencia creciente.
  4. Si el servidor responde NACK|104 (por ejemplo tras reiniciar el contenedor),
     vuelve a registrarse por TCP.
  5. Al terminar (Ctrl+C) envía BYE por TCP y muestra el conteo de mensajes.

Uso:
  python node.py --id NODE01 --server telemetria.example.com [--location "Planta Norte"]
                 [--interval 2] [--anomaly-rate 0.05] [--force-alert TEMP]
Variables de entorno equivalentes: NODE_ID, SERVER_HOST, NODE_LOCATION, INTERVAL, ANOMALY_RATE.
"""
import argparse
import os
import random
import signal
import socket
import sys
import time

UDP_PORT = 5000
TCP_PORT = 5001
VARS = ["TEMP", "HUM", "ENERGY", "VIB", "STATUS"]


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


class Node:
    def __init__(self, node_id, server, location, interval, anomaly_rate, force_alert):
        self.id = node_id
        self.server = server
        self.location = location
        self.interval = interval
        self.anomaly_rate = anomaly_rate
        self.force_alert = force_alert
        self.seq = 0
        self.sent = 0
        self.nacks = 0
        self.registered = False
        self.running = True
        self.ip = None
        self.udp = None
        # estado interno de la simulación (cada variable deriva lentamente)
        self.state = {"TEMP": 24.0, "HUM": 55.0, "ENERGY": 1200.0, "VIB": 1.5}

    # ---- DNS ----
    def resolve(self):
        """Traduce el nombre DNS a una IPv4. Es el único lugar donde aparece una IP."""
        infos = socket.getaddrinfo(self.server, TCP_PORT, socket.AF_INET, socket.SOCK_STREAM)
        self.ip = infos[0][4][0]
        log(f"DNS: {self.server} -> {self.ip}")

    # ---- TCP ----
    def register(self):
        """REGISTER por TCP. Reintenta con espera creciente hasta lograrlo."""
        wait = 1
        while self.running:
            try:
                self.resolve()
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(5)
                    s.connect((self.ip, TCP_PORT))
                    msg = f"REGISTER|{self.id}|{self.location}|{','.join(VARS)}\n"
                    s.sendall(msg.encode())
                    reply = self._recv_line(s)
                log(f"TCP -> {msg.strip()}")
                log(f"TCP <- {reply}")
                if reply.startswith("OK|REGISTERED"):
                    self.registered = True
                    self.seq = 0  # el servidor reinicia la secuencia esperada al registrar
                    return
                log(f"registro rechazado: {reply}")
            except (OSError, socket.timeout) as e:
                log(f"error de registro ({e}); reintento en {wait}s")
            time.sleep(wait)
            wait = min(wait * 2, 30)

    def bye(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect((self.ip, TCP_PORT))
                s.sendall(f"BYE|{self.id}\n".encode())
                log(f"TCP <- {self._recv_line(s)}")
        except (OSError, socket.timeout) as e:
            log(f"no se pudo enviar BYE: {e}")

    @staticmethod
    def _recv_line(s):
        data = b""
        while not data.endswith(b"\n"):
            chunk = s.recv(256)
            if not chunk:
                break
            data += chunk
        return data.decode(errors="replace").strip()

    # ---- simulación ----
    def measure(self, var):
        st = self.state
        anomaly = random.random() < self.anomaly_rate or self.force_alert == var
        if var == "TEMP":
            st["TEMP"] += random.uniform(-0.6, 0.6)
            st["TEMP"] = max(15.0, min(35.0, st["TEMP"]))
            return f"{45.0 + random.uniform(0, 5):.1f}" if anomaly else f"{st['TEMP']:.1f}"
        if var == "HUM":
            st["HUM"] += random.uniform(-1.5, 1.5)
            st["HUM"] = max(30.0, min(80.0, st["HUM"]))
            return f"{88.0 + random.uniform(0, 8):.1f}" if anomaly else f"{st['HUM']:.1f}"
        if var == "ENERGY":
            st["ENERGY"] += random.uniform(-80, 80)
            st["ENERGY"] = max(300.0, min(4500.0, st["ENERGY"]))
            return f"{5200.0 + random.uniform(0, 900):.1f}" if anomaly else f"{st['ENERGY']:.1f}"
        if var == "VIB":
            st["VIB"] += random.uniform(-0.3, 0.3)
            st["VIB"] = max(0.2, min(6.0, st["VIB"]))
            return f"{8.5 + random.uniform(0, 3):.2f}" if anomaly else f"{st['VIB']:.2f}"
        if var == "STATUS":
            return "FAULT" if anomaly else random.choice(["OK", "OK", "OK", "WARN"])
        raise ValueError(var)

    # ---- UDP ----
    def send_telemetry(self):
        for var in VARS:
            self.seq += 1
            msg = f"TELEMETRY|{self.id}|{self.seq}|{var}|{self.measure(var)}\n"
            try:
                self.udp.sendto(msg.encode(), (self.ip, UDP_PORT))
                self.sent += 1
                log(f"UDP -> {msg.strip()}")
            except OSError as e:
                log(f"error UDP: {e}")
                return
            time.sleep(0.05)

    def check_nack(self):
        """Lee respuestas UDP pendientes sin bloquear. Solo llega NACK|104."""
        try:
            while True:
                data, _ = self.udp.recvfrom(256)
                text = data.decode(errors="replace").strip()
                log(f"UDP <- {text}")
                if text.startswith("NACK|104"):
                    self.nacks += 1
                    self.registered = False
        except (BlockingIOError, socket.timeout):
            pass
        except ConnectionResetError:
            # Windows entrega ICMP port unreachable como excepción: el servidor no escucha
            log("UDP: puerto inalcanzable (servidor caído?)")
            self.registered = False

    def run(self):
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp.setblocking(False)
        while self.running:
            if not self.registered:
                self.register()
                if not self.running:
                    break
            self.send_telemetry()
            time.sleep(self.interval)
            self.check_nack()
        self.udp.close()
        self.bye()
        log(f"resumen: datagramas UDP enviados={self.sent} nacks={self.nacks} ultimo_seq={self.seq}")

    def stop(self, *_):
        log("deteniendo nodo")
        self.running = False


def main():
    p = argparse.ArgumentParser(description="Nodo de telemetría TLP/1.0")
    p.add_argument("--id", default=os.getenv("NODE_ID", "NODE01"))
    p.add_argument("--server", default=os.getenv("SERVER_HOST", "localhost"))
    p.add_argument("--location", default=os.getenv("NODE_LOCATION", "Sin ubicacion"))
    p.add_argument("--interval", type=float, default=float(os.getenv("INTERVAL", "2")))
    p.add_argument("--anomaly-rate", type=float, default=float(os.getenv("ANOMALY_RATE", "0.03")))
    p.add_argument("--force-alert", choices=VARS, default=os.getenv("FORCE_ALERT") or None,
                   help="fuerza un valor anómalo en esa variable en cada ciclo")
    a = p.parse_args()

    node = Node(a.id, a.server, a.location, a.interval, a.anomaly_rate, a.force_alert)
    signal.signal(signal.SIGINT, node.stop)
    signal.signal(signal.SIGTERM, node.stop)
    log(f"nodo {node.id} ({node.location}) -> {node.server} cada {node.interval}s")
    node.run()


if __name__ == "__main__":
    sys.exit(main())
