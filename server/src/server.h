#ifndef SERVER_H
#define SERVER_H

#include <signal.h>

extern volatile sig_atomic_t g_running;
extern int g_udp_port;

int udp_open(int port);
void *udp_loop(void *arg);

int tcp_open(int port);
void *tcp_accept_loop(void *arg);

int http_open(int port);
void *http_loop(void *arg);

void *watchdog_loop(void *arg);

#endif
