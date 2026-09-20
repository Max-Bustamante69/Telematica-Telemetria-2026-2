#!/usr/bin/env python3
"""Prueba de conteo de mensajes (sección 11 del enunciado).

Registra un nodo de prueba por TCP, envía N datagramas UDP numerados y luego
pregunta al servidor cuántos recibió. Reporta enviados, recibidos y perdidos.
Con --drop se omiten deliberadamente algunos números de secuencia para
comprobar que el servidor los detecta como perdidos.

  python loss_test.py --server telemetria.example.com --count 500 [--drop 5]
"""
import argparse
import socket
import time

UDP_PORT, TCP_PORT = 5000, 5001


def tcp(ip, cmd):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5)
        s.connect((ip, TCP_PORT))
        s.sendall((cmd + "\n").encode())
        data = b""
        while not data.endswith(b"\n"):
            chunk = s.recv(1024)
            if not chunk:
                break
            data += chunk
    return data.decode().strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--server", default="localhost")
    p.add_argument("--count", type=int, default=500)
    p.add_argument("--drop", type=int, default=0, help="omitir 1 de cada N secuencias")
    p.add_argument("--id", default="TESTLOSS")
    a = p.parse_args()

    ip = socket.getaddrinfo(a.server, TCP_PORT, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
    print(f"DNS: {a.server} -> {ip}")
    print("TCP:", tcp(ip, f"REGISTER|{a.id}|Laboratorio|TEMP"))

    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sent = skipped = 0
    t0 = time.time()
    for seq in range(1, a.count + 1):
        if a.drop and seq % a.drop == 0:
            skipped += 1
            continue
        udp.sendto(f"TELEMETRY|{a.id}|{seq}|TEMP|25.0\n".encode(), (ip, UDP_PORT))
        sent += 1
        time.sleep(0.002)
    elapsed = time.time() - t0
    time.sleep(1.0)  # dar tiempo a que lleguen los últimos datagramas

    status = tcp(ip, f"GET_STATUS|{a.id}")
    print("TCP:", status)
    f = status.split("|")
    received, lost = int(f[6]), int(f[7])
    print()
    print(f"datagramas transmitidos : {sent}")
    print(f"omitidos a proposito    : {skipped}")
    print(f"recibidos por el servidor: {received}")
    print(f"perdidos segun servidor  : {lost}")
    print(f"perdidos en la red       : {sent - received}")
    print(f"tiempo                   : {elapsed:.2f}s ({sent / elapsed:.0f} msg/s)")
    print("TCP:", tcp(ip, f"BYE|{a.id}"))


if __name__ == "__main__":
    main()
