/* Servicio web mínimo (puerto 8080) escrito sobre sockets TCP.
 * Solo atiende GET / , GET /api/status y GET /health. */
#include "log.h"
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

static const char INDEX_HTML[] =
"<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
"<title>Telemetría · servidor central</title>"
"<style>"
"body{font-family:system-ui,sans-serif;margin:0;background:#f4f5f7;color:#1c1e21}"
"header{background:#1c1e21;color:#fff;padding:14px 20px;display:flex;gap:18px;align-items:baseline}"
"header h1{font-size:18px;margin:0}header span{opacity:.75;font-size:13px}"
"main{padding:16px 20px;display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}"
"section{background:#fff;border-radius:8px;padding:14px 16px;box-shadow:0 1px 2px rgba(0,0,0,.08)}"
"h2{font-size:14px;margin:0 0 10px;text-transform:uppercase;letter-spacing:.04em;color:#555}"
"table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:5px 6px;text-align:left;border-bottom:1px solid #eee}"
"th{color:#777;font-weight:600}.ok{color:#1a7f37}.bad{color:#c0392b;font-weight:600}"
".kv{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;font-size:13px}.kv b{color:#555;font-weight:600}"
"code{background:#f0f1f3;padding:1px 5px;border-radius:4px}"
"</style></head><body>"
"<header><h1>Plataforma de telemetría</h1><span id=\"upd\">cargando…</span></header>"
"<main>"
"<section><h2>Estado del servidor</h2><div class=\"kv\" id=\"srv\"></div></section>"
"<section><h2>Nodos</h2><table><thead><tr><th>Id</th><th>Ubicación</th><th>Estado</th><th>Hace</th><th>Recibidos</th><th>Perdidos</th></tr></thead><tbody id=\"nodes\"></tbody></table></section>"
"<section><h2>Últimas mediciones</h2><table><thead><tr><th>Nodo</th><th>Variable</th><th>Valor</th><th>Hace</th></tr></thead><tbody id=\"meas\"></tbody></table></section>"
"<section><h2>Alertas recientes</h2><table><thead><tr><th>Nodo</th><th>Tipo</th><th>Valor</th><th>Hace</th></tr></thead><tbody id=\"alerts\"></tbody></table></section>"
"</main>"
"<script>"
"function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}"
"async function load(){try{const r=await fetch('/api/status');const d=await r.json();"
"const s=d.server;document.getElementById('srv').innerHTML="
"`<b>Uptime</b><span>${s.uptime_s} s</span><b>Nodos registrados</b><span>${s.nodes}</span><b>Nodos activos</b><span>${s.active}</span>"
"<b>Operadores conectados</b><span>${s.operators}</span><b>UDP recibidos / perdidos</b><span>${s.udp_received} / ${s.udp_lost}</span>"
"<b>UDP rechazados / inválidos</b><span>${s.udp_rejected} / ${s.udp_invalid}</span><b>Comandos TCP</b><span>${s.tcp_commands}</span><b>Alertas</b><span>${s.alerts}</span>`;"
"document.getElementById('nodes').innerHTML=d.nodes.map(n=>`<tr><td><code>${esc(n.id)}</code></td><td>${esc(n.location)}</td><td class=\"${n.active?'ok':'bad'}\">${n.active?'ACTIVE':'INACTIVE'}</td><td>${n.last_seen_s} s</td><td>${n.received}</td><td>${n.lost}</td></tr>`).join('')||'<tr><td colspan=6>Sin nodos</td></tr>';"
"const m=[];d.nodes.forEach(n=>n.measures.forEach(x=>m.push(`<tr><td><code>${esc(n.id)}</code></td><td>${esc(x.var)}</td><td>${esc(x.value)}</td><td>${x.age_s} s</td></tr>`)));"
"document.getElementById('meas').innerHTML=m.join('')||'<tr><td colspan=4>Sin mediciones</td></tr>';"
"document.getElementById('alerts').innerHTML=d.alerts.map(a=>`<tr><td><code>${esc(a.node)}</code></td><td class=\"bad\">${esc(a.type)}</td><td>${esc(a.value)}</td><td>${a.age_s} s</td></tr>`).join('')||'<tr><td colspan=4>Sin alertas</td></tr>';"
"document.getElementById('upd').textContent='actualizado '+new Date().toLocaleTimeString();"
"}catch(e){document.getElementById('upd').textContent='sin conexión con el servidor'}}"
"load();setInterval(load,3000);"
"</script></body></html>";

static size_t build_status_json(char *out, size_t cap) {
    size_t used = 0;
    time_t now = time(NULL);
    state_lock();
    int active = 0;
    int total = state_count_nodes(&active);
    used += (size_t)snprintf(out + used, cap - used,
        "{\"server\":{\"uptime_s\":%ld,\"nodes\":%d,\"active\":%d,\"operators\":%d,"
        "\"udp_received\":%llu,\"udp_lost\":%llu,\"udp_rejected\":%llu,\"udp_invalid\":%llu,"
        "\"tcp_commands\":%llu,\"alerts\":%llu},\"nodes\":[",
        (long)(now - g_stats.started_at), total, active, g_stats.operators_connected,
        (unsigned long long)g_stats.udp_received, (unsigned long long)g_stats.udp_lost,
        (unsigned long long)g_stats.udp_rejected, (unsigned long long)g_stats.udp_invalid,
        (unsigned long long)g_stats.tcp_commands, (unsigned long long)g_stats.alerts_total);
    int first = 1;
    for (int i = 0; i < MAX_NODES && used < cap; i++) {
        node_t *n = &g_nodes[i];
        if (!n->used) continue;
        used += (size_t)snprintf(out + used, cap - used,
            "%s{\"id\":\"%s\",\"location\":\"%s\",\"active\":%s,\"last_seen_s\":%ld,"
            "\"received\":%llu,\"lost\":%llu,\"alerts\":%llu,\"measures\":[",
            first ? "" : ",", n->id, n->location, n->active ? "true" : "false",
            (long)(now - n->last_seen), (unsigned long long)n->received,
            (unsigned long long)n->lost, (unsigned long long)n->alerts);
        for (int k = 0; k < n->nvars && used < cap; k++)
            used += (size_t)snprintf(out + used, cap - used,
                "%s{\"var\":\"%s\",\"value\":\"%s\",\"age_s\":%ld}", k ? "," : "",
                n->vars[k].name, n->vars[k].value, (long)(now - n->vars[k].at));
        used += (size_t)snprintf(out + used, cap - used, "]}");
        first = 0;
    }
    alert_t snap[20];
    int na = state_alerts_snapshot(snap, 20);
    state_unlock();
    used += (size_t)snprintf(out + used, cap - used, "],\"alerts\":[");
    for (int i = 0; i < na && used < cap; i++)
        used += (size_t)snprintf(out + used, cap - used,
            "%s{\"node\":\"%s\",\"type\":\"%s\",\"value\":\"%s\",\"age_s\":%ld}", i ? "," : "",
            snap[i].node_id, snap[i].type, snap[i].value, (long)(now - snap[i].at));
    used += (size_t)snprintf(out + used, cap - used, "]}");
    return used < cap ? used : cap - 1;
}

static void send_all(int fd, const char *buf, size_t len) {
    size_t off = 0;
    while (off < len) {
        ssize_t w = send(fd, buf + off, len - off, MSG_NOSIGNAL);
        if (w <= 0) return;
        off += (size_t)w;
    }
}

static void respond(int fd, int code, const char *reason, const char *ctype, const char *body, size_t blen) {
    char head[256];
    int hl = snprintf(head, sizeof head,
                      "HTTP/1.1 %d %s\r\nContent-Type: %s\r\nContent-Length: %zu\r\n"
                      "Cache-Control: no-store\r\nConnection: close\r\n\r\n",
                      code, reason, ctype, blen);
    send_all(fd, head, (size_t)hl);
    send_all(fd, body, blen);
}

static void *http_client(void *arg) {
    int fd = *(int *)arg;
    free(arg);
    char req[2048];
    ssize_t n = recv(fd, req, sizeof req - 1, 0);
    if (n <= 0) { close(fd); return NULL; }
    req[n] = '\0';

    char method[8] = {0}, path[256] = {0};
    sscanf(req, "%7s %255s", method, path);
    log_msg("HTTP", "%s %s", method, path);

    if (strcmp(method, "GET") != 0) {
        respond(fd, 405, "Method Not Allowed", "text/plain", "solo GET\n", 9);
    } else if (strcmp(path, "/") == 0 || strcmp(path, "/index.html") == 0) {
        respond(fd, 200, "OK", "text/html; charset=utf-8", INDEX_HTML, sizeof INDEX_HTML - 1);
    } else if (strcmp(path, "/api/status") == 0) {
        static __thread char json[65536];
        size_t len = build_status_json(json, sizeof json);
        respond(fd, 200, "OK", "application/json; charset=utf-8", json, len);
    } else if (strcmp(path, "/health") == 0) {
        respond(fd, 200, "OK", "text/plain", "ok\n", 3);
    } else {
        respond(fd, 404, "Not Found", "text/plain", "no existe\n", 10);
    }
    close(fd);
    return NULL;
}

int http_open(int port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) { perror("socket http"); return -1; }
    int yes = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof yes);
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof addr);
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons((uint16_t)port);
    if (bind(fd, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(fd, 16) < 0) {
        perror("bind/listen http");
        close(fd);
        return -1;
    }
    log_msg("HTTP", "interfaz web en 0.0.0.0:%d", port);
    return fd;
}

void *http_loop(void *arg) {
    int lfd = *(int *)arg;
    while (g_running) {
        int cfd = accept(lfd, NULL, NULL);
        if (cfd < 0) {
            if (errno == EINTR) continue;
            if (!g_running) break;
            perror("accept http");
            continue;
        }
        int *p = malloc(sizeof *p);
        if (!p) { close(cfd); continue; }
        *p = cfd;
        pthread_t th;
        if (pthread_create(&th, NULL, http_client, p) != 0) { close(cfd); free(p); continue; }
        pthread_detach(th);
    }
    close(lfd);
    return NULL;
}
