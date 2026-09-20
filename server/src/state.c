#include "state.h"
#include "log.h"

#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

node_t g_nodes[MAX_NODES];
stats_t g_stats;

static pthread_mutex_t g_mutex = PTHREAD_MUTEX_INITIALIZER;
static alert_t g_alerts[MAX_ALERTS];
static int g_alert_head = 0;   /* siguiente posición a escribir */
static int g_alert_count = 0;
static int g_subscribers[MAX_SUBSCRIBERS];

void state_init(void) {
    memset(g_nodes, 0, sizeof g_nodes);
    memset(&g_stats, 0, sizeof g_stats);
    g_stats.started_at = time(NULL);
    for (int i = 0; i < MAX_SUBSCRIBERS; i++) g_subscribers[i] = -1;
}

void state_lock(void) { pthread_mutex_lock(&g_mutex); }
void state_unlock(void) { pthread_mutex_unlock(&g_mutex); }

node_t *state_find_node(const char *id) {
    for (int i = 0; i < MAX_NODES; i++)
        if (g_nodes[i].used && strcmp(g_nodes[i].id, id) == 0) return &g_nodes[i];
    return NULL;
}

node_t *state_register_node(const char *id, const char *loc) {
    node_t *n = state_find_node(id);
    if (!n) {
        for (int i = 0; i < MAX_NODES; i++)
            if (!g_nodes[i].used) { n = &g_nodes[i]; break; }
        if (!n) return NULL;
        memset(n, 0, sizeof *n);
        n->used = 1;
        snprintf(n->id, ID_LEN, "%s", id);
        n->registered_at = time(NULL);
    }
    snprintf(n->location, LOC_LEN, "%s", loc);
    n->active = 1;
    n->last_seen = time(NULL);
    n->last_seq = 0;          /* un REGISTER reinicia la secuencia esperada */
    n->inactive_alerted = 0;
    return n;
}

int state_count_nodes(int *active_out) {
    int total = 0, active = 0;
    for (int i = 0; i < MAX_NODES; i++) {
        if (!g_nodes[i].used) continue;
        total++;
        if (g_nodes[i].active) active++;
    }
    if (active_out) *active_out = active;
    return total;
}

void state_set_measure(node_t *n, const char *var, const char *value) {
    measure_t *m = NULL;
    for (int i = 0; i < n->nvars; i++)
        if (strcmp(n->vars[i].name, var) == 0) { m = &n->vars[i]; break; }
    if (!m) {
        if (n->nvars >= MAX_VARS) return; /* se ignora una novena variable */
        m = &n->vars[n->nvars++];
        snprintf(m->name, VAR_LEN, "%s", var);
    }
    snprintf(m->value, VAL_LEN, "%s", value);
    m->at = time(NULL);
}

void state_add_alert(const char *node_id, const char *type, const char *value) {
    alert_t *a = &g_alerts[g_alert_head];
    snprintf(a->node_id, ID_LEN, "%s", node_id);
    snprintf(a->type, VAR_LEN, "%s", type);
    snprintf(a->value, VAL_LEN, "%s", value);
    a->at = time(NULL);
    g_alert_head = (g_alert_head + 1) % MAX_ALERTS;
    if (g_alert_count < MAX_ALERTS) g_alert_count++;
    g_stats.alerts_total++;

    node_t *n = state_find_node(node_id);
    if (n) n->alerts++;

    log_msg("ALERT", "%s %s %s", node_id, type, value);

    char line[160];
    int len = snprintf(line, sizeof line, "ALERT|%s|%s|%s|0\n", node_id, type, value);
    for (int i = 0; i < MAX_SUBSCRIBERS; i++) {
        int fd = g_subscribers[i];
        if (fd < 0) continue;
        /* MSG_NOSIGNAL: un operador que cerró no debe matar el servidor con SIGPIPE */
        if (send(fd, line, (size_t)len, MSG_NOSIGNAL) < 0) g_subscribers[i] = -1;
    }
}

int state_alerts_snapshot(alert_t *out, int max) {
    int n = 0;
    for (int k = 1; k <= g_alert_count && n < max; k++) {
        int idx = (g_alert_head - k + MAX_ALERTS) % MAX_ALERTS;
        out[n++] = g_alerts[idx];
    }
    return n;
}

void state_subscribe(int fd) {
    for (int i = 0; i < MAX_SUBSCRIBERS; i++)
        if (g_subscribers[i] == fd) return;
    for (int i = 0; i < MAX_SUBSCRIBERS; i++)
        if (g_subscribers[i] < 0) { g_subscribers[i] = fd; return; }
}

void state_unsubscribe(int fd) {
    for (int i = 0; i < MAX_SUBSCRIBERS; i++)
        if (g_subscribers[i] == fd) g_subscribers[i] = -1;
}
