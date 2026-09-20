#include "protocol.h"
#include "log.h"
#include "state.h"

#include <ctype.h>
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int g_udp_port = 5000; /* lo fija main.c; se informa en OK|REGISTERED */

int tlp_split(char *line, char *fields[], int max_fields) {
    int n = 0;
    char *p = line;
    while (n < max_fields) {
        fields[n++] = p;
        char *bar = strchr(p, '|');
        if (!bar) break;
        *bar = '\0';
        p = bar + 1;
    }
    return n;
}

int tlp_valid_id(const char *id) {
    size_t len = strlen(id);
    if (len == 0 || len >= ID_LEN) return 0;
    for (size_t i = 0; i < len; i++) {
        unsigned char c = (unsigned char)id[i];
        if (!(isalnum(c) || c == '_' || c == '-')) return 0;
    }
    return 1;
}

static int parse_double(const char *s, double *out) {
    char *end;
    errno = 0;
    double v = strtod(s, &end);
    if (end == s || *end != '\0' || errno != 0) return 0;
    *out = v;
    return 1;
}

static void trim_crlf(char *s) {
    size_t n = strlen(s);
    while (n > 0 && (s[n - 1] == '\n' || s[n - 1] == '\r')) s[--n] = '\0';
}

/* Evalúa umbrales y genera la alerta si aplica. Requiere lock. */
static void check_thresholds(node_t *n, const char *var, const char *value) {
    double v;
    int numeric = parse_double(value, &v);
    if (strcmp(var, "TEMP") == 0 && numeric) {
        if (v > 40.0) state_add_alert(n->id, "TEMP_HIGH", value);
        else if (v < -10.0) state_add_alert(n->id, "TEMP_LOW", value);
    } else if (strcmp(var, "HUM") == 0 && numeric) {
        if (v > 85.0) state_add_alert(n->id, "HUM_HIGH", value);
    } else if (strcmp(var, "ENERGY") == 0 && numeric) {
        if (v > 5000.0) state_add_alert(n->id, "ENERGY_HIGH", value);
    } else if (strcmp(var, "VIB") == 0 && numeric) {
        if (v > 8.0) state_add_alert(n->id, "VIB_HIGH", value);
    } else if (strcmp(var, "STATUS") == 0) {
        if (strcmp(value, "FAULT") == 0) state_add_alert(n->id, "STATUS_FAULT", value);
    }
}

int tlp_handle_udp(const char *datagram, size_t len, char *reply, size_t reply_cap) {
    char buf[MAX_LINE];
    if (len == 0 || len >= sizeof buf) {
        state_lock(); g_stats.udp_invalid++; state_unlock();
        return 0;
    }
    memcpy(buf, datagram, len);
    buf[len] = '\0';
    trim_crlf(buf);

    char *f[MAX_FIELDS];
    int nf = tlp_split(buf, f, MAX_FIELDS);

    /* TELEMETRY|<id>|<seq>|<VAR>|<valor> */
    if (nf != 5 || strcmp(f[0], "TELEMETRY") != 0 || !tlp_valid_id(f[1]) ||
        strlen(f[3]) == 0 || strlen(f[3]) >= VAR_LEN || strlen(f[4]) == 0 || strlen(f[4]) >= VAL_LEN) {
        state_lock(); g_stats.udp_invalid++; state_unlock();
        log_msg("UDP", "datagrama invalido descartado (%d campos)", nf);
        return 0;
    }
    char *end;
    long seq = strtol(f[2], &end, 10);
    if (*end != '\0' || seq < 0) {
        state_lock(); g_stats.udp_invalid++; state_unlock();
        return 0;
    }
    /* STATUS solo admite tres valores; el resto debe ser numérico */
    double dummy;
    if (strcmp(f[3], "STATUS") == 0) {
        if (strcmp(f[4], "OK") && strcmp(f[4], "WARN") && strcmp(f[4], "FAULT")) {
            state_lock(); g_stats.udp_invalid++; state_unlock();
            return 0;
        }
    } else if (!parse_double(f[4], &dummy)) {
        state_lock(); g_stats.udp_invalid++; state_unlock();
        return 0;
    }

    state_lock();
    node_t *n = state_find_node(f[1]);
    if (!n) {
        g_stats.udp_rejected++;
        state_unlock();
        return snprintf(reply, reply_cap, "NACK|104|NOT_REGISTERED\n");
    }
    /* Conteo de pérdidas por huecos en la secuencia */
    if (seq > n->last_seq + 1 && n->last_seq > 0) {
        uint64_t gap = (uint64_t)(seq - n->last_seq - 1);
        n->lost += gap;
        g_stats.udp_lost += gap;
    }
    if (seq > n->last_seq || seq <= 1) n->last_seq = seq; /* seq<=1: el nodo reinició */
    n->received++;
    g_stats.udp_received++;
    n->last_seen = time(NULL);
    if (!n->active) log_msg("NODE", "%s vuelve a estar ACTIVE", n->id);
    n->active = 1;
    n->inactive_alerted = 0;
    state_set_measure(n, f[3], f[4]);
    check_thresholds(n, f[3], f[4]);
    state_unlock();
    return 0;
}

/* --------- TCP --------- */

static int append(char *out, size_t cap, size_t *used, const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    int w = vsnprintf(out + *used, cap - *used, fmt, ap);
    va_end(ap);
    if (w < 0 || (size_t)w >= cap - *used) return 0;
    *used += (size_t)w;
    return 1;
}

static int err(char *out, size_t cap, int code, const char *text) {
    snprintf(out, cap, "ERR|%d|%s\n", code, text);
    return 0;
}

int tlp_handle_tcp(int fd, char *line, char *out, size_t out_cap) {
    size_t used = 0;
    out[0] = '\0';
    trim_crlf(line);
    if (line[0] == '\0') return err(out, out_cap, 100, "BAD_FORMAT");

    char *f[MAX_FIELDS];
    int nf = tlp_split(line, f, MAX_FIELDS);
    const char *cmd = f[0];

    state_lock();
    g_stats.tcp_commands++;
    state_unlock();

    if (strcmp(cmd, "PING") == 0) {
        snprintf(out, out_cap, "OK|PONG\n");
        return 0;
    }

    if (strcmp(cmd, "QUIT") == 0) {
        snprintf(out, out_cap, "OK|BYE\n");
        return 1;
    }

    if (strcmp(cmd, "REGISTER") == 0) {
        if (nf < 3) return err(out, out_cap, 100, "BAD_FORMAT");
        if (!tlp_valid_id(f[1]) || strlen(f[2]) == 0 || strlen(f[2]) >= LOC_LEN)
            return err(out, out_cap, 103, "BAD_PARAM");
        state_lock();
        node_t *n = state_register_node(f[1], f[2]);
        state_unlock();
        if (!n) return err(out, out_cap, 106, "SERVER_FULL");
        log_msg("NODE", "REGISTER %s (%s) vars=%s", f[1], f[2], nf >= 4 ? f[3] : "-");
        snprintf(out, out_cap, "OK|REGISTERED|%s|%d\n", f[1], g_udp_port);
        return 0;
    }

    if (strcmp(cmd, "BYE") == 0) {
        if (nf < 2) return err(out, out_cap, 100, "BAD_FORMAT");
        state_lock();
        node_t *n = state_find_node(f[1]);
        if (n) { n->active = 0; n->inactive_alerted = 1; }
        state_unlock();
        if (!n) return err(out, out_cap, 102, "UNKNOWN_NODE");
        log_msg("NODE", "BYE %s", f[1]);
        snprintf(out, out_cap, "OK|BYE\n");
        return 0;
    }

    if (strcmp(cmd, "LIST_NODES") == 0) {
        time_t now = time(NULL);
        state_lock();
        int total = state_count_nodes(NULL);
        append(out, out_cap, &used, "OK|NODES|%d\n", total);
        for (int i = 0; i < MAX_NODES; i++) {
            node_t *n = &g_nodes[i];
            if (!n->used) continue;
            append(out, out_cap, &used, "NODE|%s|%s|%s|%ld|%llu|%llu\n", n->id, n->location,
                   n->active ? "ACTIVE" : "INACTIVE", (long)(now - n->last_seen),
                   (unsigned long long)n->received, (unsigned long long)n->lost);
        }
        state_unlock();
        append(out, out_cap, &used, "END\n");
        return 0;
    }

    if (strcmp(cmd, "GET_STATUS") == 0 || strcmp(cmd, "GET_LAST") == 0) {
        if (nf < 2) return err(out, out_cap, 100, "BAD_FORMAT");
        if (!tlp_valid_id(f[1])) return err(out, out_cap, 103, "BAD_PARAM");
        time_t now = time(NULL);
        state_lock();
        node_t *n = state_find_node(f[1]);
        if (!n) { state_unlock(); return err(out, out_cap, 102, "UNKNOWN_NODE"); }
        if (cmd[4] == 'S') {
            append(out, out_cap, &used, "OK|STATUS|%s|%s|%s|%ld|%llu|%llu|%llu\n", n->id,
                   n->active ? "ACTIVE" : "INACTIVE", n->location, (long)(now - n->last_seen),
                   (unsigned long long)n->received, (unsigned long long)n->lost,
                   (unsigned long long)n->alerts);
        } else {
            append(out, out_cap, &used, "OK|LAST|%s|%d\n", n->id, n->nvars);
            for (int i = 0; i < n->nvars; i++)
                append(out, out_cap, &used, "MEASURE|%s|%s|%s|%ld\n", n->id, n->vars[i].name,
                       n->vars[i].value, (long)(now - n->vars[i].at));
            append(out, out_cap, &used, "END\n");
        }
        state_unlock();
        return 0;
    }

    if (strcmp(cmd, "GET_ALERTS") == 0) {
        int max = 20;
        if (nf >= 2) {
            char *end;
            long v = strtol(f[1], &end, 10);
            if (*end != '\0' || v <= 0 || v > 100) return err(out, out_cap, 103, "BAD_PARAM");
            max = (int)v;
        }
        alert_t snap[100];
        time_t now = time(NULL);
        state_lock();
        int n = state_alerts_snapshot(snap, max);
        state_unlock();
        append(out, out_cap, &used, "OK|ALERTS|%d\n", n);
        for (int i = 0; i < n; i++)
            append(out, out_cap, &used, "ALERT|%s|%s|%s|%ld\n", snap[i].node_id, snap[i].type,
                   snap[i].value, (long)(now - snap[i].at));
        append(out, out_cap, &used, "END\n");
        return 0;
    }

    if (strcmp(cmd, "SYSTEM_STATUS") == 0) {
        state_lock();
        int active = 0;
        int total = state_count_nodes(&active);
        snprintf(out, out_cap,
                 "OK|SYSTEM|uptime=%ld;nodes=%d;active=%d;operators=%d;udp_received=%llu;"
                 "udp_lost=%llu;udp_rejected=%llu;udp_invalid=%llu;tcp_commands=%llu;alerts=%llu\n",
                 (long)(time(NULL) - g_stats.started_at), total, active, g_stats.operators_connected,
                 (unsigned long long)g_stats.udp_received, (unsigned long long)g_stats.udp_lost,
                 (unsigned long long)g_stats.udp_rejected, (unsigned long long)g_stats.udp_invalid,
                 (unsigned long long)g_stats.tcp_commands, (unsigned long long)g_stats.alerts_total);
        state_unlock();
        return 0;
    }

    if (strcmp(cmd, "SUBSCRIBE_ALERTS") == 0) {
        state_lock();
        state_subscribe(fd);
        state_unlock();
        snprintf(out, out_cap, "OK|SUBSCRIBED\n");
        return 0;
    }

    return err(out, out_cap, 101, "UNKNOWN_COMMAND");
}
