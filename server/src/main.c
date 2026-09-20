/* Servidor central de telemetría (TLP/1.0).
 *
 * Hilos:
 *   - principal: acepta conexiones TCP (registro de nodos y operadores)
 *   - udp_loop:  recibe telemetría por UDP
 *   - http_loop: interfaz web
 *   - watchdog:  marca nodos inactivos
 *   - uno por cada cliente TCP y por cada petición HTTP
 *
 * Variables de entorno: UDP_PORT (5000), TCP_PORT (5001), HTTP_PORT (8080).
 */
#include "log.h"
#include "server.h"
#include "state.h"

#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <string.h>
#include <unistd.h>

volatile sig_atomic_t g_running = 1;
static int g_udp_fd = -1, g_tcp_fd = -1, g_http_fd = -1;

static void on_signal(int sig) {
    (void)sig;
    g_running = 0;
    /* shutdown despierta a accept()/recvfrom() bloqueados para que los hilos salgan */
    if (g_udp_fd >= 0) shutdown(g_udp_fd, SHUT_RDWR);
    if (g_tcp_fd >= 0) shutdown(g_tcp_fd, SHUT_RDWR);
    if (g_http_fd >= 0) shutdown(g_http_fd, SHUT_RDWR);
}

static int env_port(const char *name, int def) {
    const char *v = getenv(name);
    if (!v || !*v) return def;
    int p = atoi(v);
    return (p > 0 && p < 65536) ? p : def;
}

int main(void) {
    int udp_port = env_port("UDP_PORT", 5000);
    int tcp_port = env_port("TCP_PORT", 5001);
    int http_port = env_port("HTTP_PORT", 8080);
    g_udp_port = udp_port;

    /* Un cliente que cierra a mitad de un send no debe matar el proceso */
    signal(SIGPIPE, SIG_IGN);
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = on_signal;
    sigaction(SIGINT, &sa, NULL);
    sigaction(SIGTERM, &sa, NULL);

    state_init();
    log_msg("MAIN", "servidor de telemetria iniciando (udp=%d tcp=%d http=%d)", udp_port, tcp_port, http_port);

    g_udp_fd = udp_open(udp_port);
    g_tcp_fd = tcp_open(tcp_port);
    g_http_fd = http_open(http_port);
    if (g_udp_fd < 0 || g_tcp_fd < 0 || g_http_fd < 0) {
        log_msg("MAIN", "no se pudieron abrir los puertos; saliendo");
        return 1;
    }

    pthread_t t_udp, t_http, t_wd;
    pthread_create(&t_udp, NULL, udp_loop, &g_udp_fd);
    pthread_create(&t_http, NULL, http_loop, &g_http_fd);
    pthread_create(&t_wd, NULL, watchdog_loop, NULL);

    tcp_accept_loop(&g_tcp_fd); /* bloquea hasta la señal de parada */

    pthread_join(t_udp, NULL);
    pthread_join(t_http, NULL);
    pthread_join(t_wd, NULL);
    log_msg("MAIN", "servidor detenido limpiamente");
    return 0;
}
