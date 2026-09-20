/* Hilo receptor de telemetría por UDP (puerto 5000). */
#include "log.h"
#include "protocol.h"
#include "server.h"

#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int udp_open(int port) {
    /* 1. creación del socket UDP (SOCK_DGRAM) */
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) { perror("socket udp"); return -1; }

    int yes = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);

    /* 2. asociación a la dirección local (todas las interfaces) */
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof addr);
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons((uint16_t)port);
    if (bind(fd, (struct sockaddr *)&addr, sizeof addr) < 0) {
        perror("bind udp");
        close(fd);
        return -1;
    }
    log_msg("UDP", "escuchando telemetria en 0.0.0.0:%d", port);
    return fd;
}

void *udp_loop(void *arg) {
    int fd = *(int *)arg;
    char buf[MAX_LINE + 1];
    char reply[64];

    while (g_running) {
        struct sockaddr_in from;
        socklen_t fromlen = sizeof from;
        /* 3. recepción de un datagrama con la dirección del emisor */
        ssize_t n = recvfrom(fd, buf, MAX_LINE, 0, (struct sockaddr *)&from, &fromlen);
        if (n < 0) {
            if (errno == EINTR) continue;
            if (!g_running) break;
            perror("recvfrom");
            continue;
        }
        int rlen = tlp_handle_udp(buf, (size_t)n, reply, sizeof reply);
        if (rlen > 0) {
            /* 4. respuesta al mismo emisor (solo NACK|104) */
            char ip[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &from.sin_addr, ip, sizeof ip);
            log_msg("UDP", "NACK a %s:%d (nodo no registrado)", ip, ntohs(from.sin_port));
            if (sendto(fd, reply, (size_t)rlen, 0, (struct sockaddr *)&from, fromlen) < 0)
                perror("sendto");
        }
    }
    /* 5. cierre */
    close(fd);
    log_msg("UDP", "hilo terminado");
    return NULL;
}
