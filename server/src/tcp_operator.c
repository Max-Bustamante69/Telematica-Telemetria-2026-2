/* Servicio TCP (puerto 5001): registro de nodos y consultas de operadores.
 * Un hilo por conexión aceptada. */
#include "log.h"
#include "protocol.h"
#include "server.h"
#include "state.h"

#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

typedef struct {
    int fd;
    char ip[INET_ADDRSTRLEN];
    int port;
} client_t;

int tcp_open(int port) {
    /* 1. creación del socket TCP (SOCK_STREAM) */
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) { perror("socket tcp"); return -1; }

    int yes = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof addr);
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons((uint16_t)port);
    /* 2. bind */
    if (bind(fd, (struct sockaddr *)&addr, sizeof addr) < 0) {
        perror("bind tcp");
        close(fd);
        return -1;
    }
    /* 3. escucha con cola de 16 conexiones pendientes */
    if (listen(fd, 16) < 0) {
        perror("listen tcp");
        close(fd);
        return -1;
    }
    log_msg("TCP", "escuchando operadores y registro en 0.0.0.0:%d", port);
    return fd;
}

static void *client_thread(void *arg) {
    client_t *c = (client_t *)arg;
    char inbuf[MAX_LINE * 2];
    size_t inlen = 0;
    char out[8192];
    int overflow = 0;

    log_msg("TCP", "conexion de %s:%d (fd=%d)", c->ip, c->port, c->fd);
    state_lock();
    g_stats.tcp_connections++;
    g_stats.operators_connected++;
    state_unlock();

    while (g_running) {
        /* 4. recepción: TCP es un flujo, así que se acumula hasta encontrar '\n' */
        ssize_t n = recv(c->fd, inbuf + inlen, sizeof inbuf - inlen - 1, 0);
        if (n == 0) { log_msg("TCP", "%s:%d cerro la conexion", c->ip, c->port); break; }
        if (n < 0) {
            if (errno == EINTR) continue;
            log_msg("TCP", "%s:%d error de recv: %s", c->ip, c->port, strerror(errno));
            break;
        }
        inlen += (size_t)n;
        inbuf[inlen] = '\0';

        char *start = inbuf;
        char *nl;
        int close_now = 0;
        while ((nl = memchr(start, '\n', inlen - (size_t)(start - inbuf))) != NULL) {
            *nl = '\0';
            if (overflow) {
                /* se descarta el resto de una línea demasiado larga */
                overflow = 0;
                snprintf(out, sizeof out, "ERR|105|TOO_LONG\n");
            } else if ((size_t)(nl - start) >= MAX_LINE) {
                snprintf(out, sizeof out, "ERR|105|TOO_LONG\n");
            } else {
                log_msg("TCP", "%s:%d -> %s", c->ip, c->port, start);
                close_now = tlp_handle_tcp(c->fd, start, out, sizeof out);
            }
            /* 5. envío de la respuesta completa (send puede escribir parcial) */
            size_t off = 0, len = strlen(out);
            while (off < len) {
                ssize_t w = send(c->fd, out + off, len - off, MSG_NOSIGNAL);
                if (w <= 0) { close_now = 1; break; }
                off += (size_t)w;
            }
            start = nl + 1;
            if (close_now) break;
        }
        if (close_now) break;

        size_t rest = inlen - (size_t)(start - inbuf);
        memmove(inbuf, start, rest);
        inlen = rest;
        if (inlen >= MAX_LINE) {
            /* línea sin '\n' que ya supera el máximo: se vacía y se marca */
            overflow = 1;
            inlen = 0;
        }
    }

    state_lock();
    state_unsubscribe(c->fd);
    g_stats.operators_connected--;
    state_unlock();
    /* 6. cierre del socket del cliente */
    close(c->fd);
    free(c);
    return NULL;
}

void *tcp_accept_loop(void *arg) {
    int lfd = *(int *)arg;
    while (g_running) {
        struct sockaddr_in peer;
        socklen_t plen = sizeof peer;
        /* aceptación de un cliente; devuelve un socket nuevo por conexión */
        int cfd = accept(lfd, (struct sockaddr *)&peer, &plen);
        if (cfd < 0) {
            if (errno == EINTR) continue;
            if (!g_running) break;
            perror("accept");
            continue;
        }
        client_t *c = malloc(sizeof *c);
        if (!c) { close(cfd); continue; }
        c->fd = cfd;
        inet_ntop(AF_INET, &peer.sin_addr, c->ip, sizeof c->ip);
        c->port = ntohs(peer.sin_port);

        pthread_t th;
        if (pthread_create(&th, NULL, client_thread, c) != 0) {
            perror("pthread_create");
            close(cfd);
            free(c);
            continue;
        }
        pthread_detach(th);
    }
    close(lfd);
    log_msg("TCP", "hilo de aceptacion terminado");
    return NULL;
}
