#!/usr/bin/env python3
"""Cliente operador (protocolo TLP/1.0 sobre TCP).

Modo interactivo:
  python operator_client/operator_client.py --server telemetria.example.com

Modo un solo comando (útil para scripts y evidencias):
  python operator_client/operator_client.py --server telemetria.example.com --cmd "GET_STATUS|NODE03"

Comandos: LIST_NODES, GET_STATUS|<id>, GET_LAST|<id>, GET_ALERTS[|n],
SYSTEM_STATUS, SUBSCRIBE_ALERTS, PING, QUIT.  En modo interactivo también
funcionan los números del menú.
"""
import argparse
import os
import socket
import sys
import threading

TCP_PORT = 5001

MENU = """
 1) LIST_NODES         nodos registrados y su estado
 2) GET_LAST|<id>      últimas mediciones de un nodo
 3) GET_STATUS|<id>    estado de un nodo
 4) GET_ALERTS         alertas recientes
 5) SYSTEM_STATUS      estado general del servidor
 6) SUBSCRIBE_ALERTS   recibir alertas en tiempo real
 7) QUIT
Escriba el número o el comando TLP completo."""


class Operator:
    def __init__(self, server):
        self.server = server
        infos = socket.getaddrinfo(server, TCP_PORT, socket.AF_INET, socket.SOCK_STREAM)
        self.ip = infos[0][4][0]
        print(f"DNS: {server} -> {self.ip}")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.sock.connect((self.ip, TCP_PORT))
        print(f"TCP conectado a {self.ip}:{TCP_PORT}")
        self.buf = b""
        self.lock = threading.Lock()
        self.subscribed = False

    def _readline(self):
        while b"\n" not in self.buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("el servidor cerró la conexión")
            self.buf += chunk
        line, self.buf = self.buf.split(b"\n", 1)
        return line.decode(errors="replace").rstrip("\r")

    def send(self, cmd):
        """Envía un comando y devuelve la respuesta completa (lista de líneas).
        Las respuestas multilínea terminan en END."""
        with self.lock:
            self.sock.sendall((cmd + "\n").encode())
            lines = []
            multi = False
            while True:
                line = self._readline()
                if line.startswith("ALERT|") and self.subscribed and not lines:
                    print(f"  ** {line}")  # alerta asíncrona que llegó antes de la respuesta
                    continue
                lines.append(line)
                if not lines[1:]:
                    multi = line.startswith(("OK|NODES", "OK|LAST", "OK|ALERTS"))
                if not multi or line == "END":
                    break
            return lines

    def listen_alerts(self):
        """Hilo que imprime ALERT|... cuando el operador está suscrito y ocioso."""
        self.sock.settimeout(0.5)
        while self.subscribed:
            try:
                with self.lock:
                    line = self._readline()
                print(f"\n  ** ALERTA en tiempo real: {line}")
            except socket.timeout:
                continue
            except (OSError, ConnectionError):
                break

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def pretty(lines):
    for line in lines:
        f = line.split("|")
        if f[0] == "ERR":
            print(f"  error {f[1]}: {f[2]}")
        elif f[0] == "NODE":
            print(f"  {f[1]:<10} {f[2]:<24} {f[3]:<9} hace {f[4]:>3}s  recibidos={f[5]} perdidos={f[6]}")
        elif f[0] == "MEASURE":
            print(f"  {f[2]:<8} {f[3]:>10}   (hace {f[4]}s)")
        elif f[0] == "ALERT":
            print(f"  {f[1]:<10} {f[2]:<14} {f[3]:>10}   (hace {f[4]}s)")
        elif f[0] == "OK" and len(f) > 1 and f[1] == "SYSTEM":
            for kv in f[2].split(";"):
                k, v = kv.split("=")
                print(f"  {k:<14} {v}")
        elif line == "END":
            pass
        else:
            print(f"  {line}")


def interactive(op):
    print(MENU)
    while True:
        try:
            raw = input("\ntlp> ").strip()
        except (EOFError, KeyboardInterrupt):
            raw = "QUIT"
        if not raw:
            continue
        if raw in ("2", "3"):
            node = input("id del nodo: ").strip()
            raw = ("GET_LAST|" if raw == "2" else "GET_STATUS|") + node
        raw = {"1": "LIST_NODES", "4": "GET_ALERTS", "5": "SYSTEM_STATUS",
               "6": "SUBSCRIBE_ALERTS", "7": "QUIT"}.get(raw, raw)
        try:
            lines = op.send(raw)
        except (OSError, ConnectionError) as e:
            print(f"conexión perdida: {e}")
            return 1
        pretty(lines)
        if raw == "SUBSCRIBE_ALERTS" and lines and lines[0] == "OK|SUBSCRIBED":
            op.subscribed = True
            threading.Thread(target=op.listen_alerts, daemon=True).start()
            print("  (las alertas aparecerán aquí mientras espera; Enter sigue funcionando)")
        if raw == "QUIT":
            return 0


def main():
    p = argparse.ArgumentParser(description="Cliente operador TLP/1.0")
    p.add_argument("--server", default=os.getenv("SERVER_HOST", "localhost"))
    p.add_argument("--cmd", help="ejecuta un solo comando y sale")
    a = p.parse_args()
    try:
        op = Operator(a.server)
    except OSError as e:
        print(f"no se pudo conectar a {a.server}:{TCP_PORT}: {e}")
        return 2
    try:
        if a.cmd:
            pretty(op.send(a.cmd))
            op.send("QUIT")
            return 0
        return interactive(op)
    finally:
        op.close()


if __name__ == "__main__":
    sys.exit(main())
