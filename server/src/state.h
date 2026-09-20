/* Estado compartido del servidor: nodos, mediciones, alertas y contadores.
 * Todo acceso pasa por state_lock()/state_unlock(). */
#ifndef STATE_H
#define STATE_H

#include <pthread.h>
#include <stdint.h>
#include <time.h>

#define MAX_NODES 64
#define MAX_VARS 8
#define MAX_ALERTS 256
#define MAX_SUBSCRIBERS 32
#define ID_LEN 32
#define LOC_LEN 64
#define VAR_LEN 16
#define VAL_LEN 32
#define INACTIVE_AFTER_S 15

typedef struct {
    char name[VAR_LEN];
    char value[VAL_LEN];
    time_t at;
} measure_t;

typedef struct {
    int used;
    char id[ID_LEN];
    char location[LOC_LEN];
    int active;
    time_t registered_at;
    time_t last_seen;
    uint64_t received;   /* datagramas UDP válidos */
    uint64_t lost;       /* huecos en la secuencia */
    uint64_t alerts;
    long last_seq;
    int inactive_alerted;
    measure_t vars[MAX_VARS];
    int nvars;
} node_t;

typedef struct {
    char node_id[ID_LEN];
    char type[VAR_LEN];
    char value[VAL_LEN];
    time_t at;
} alert_t;

typedef struct {
    time_t started_at;
    uint64_t udp_received;
    uint64_t udp_lost;
    uint64_t udp_rejected;
    uint64_t udp_invalid;
    uint64_t tcp_commands;
    uint64_t tcp_connections;
    uint64_t alerts_total;
    int operators_connected;
} stats_t;

void state_init(void);
void state_lock(void);
void state_unlock(void);

node_t *state_find_node(const char *id);          /* requiere lock */
node_t *state_register_node(const char *id, const char *loc); /* requiere lock; NULL si lleno */
int state_count_nodes(int *active_out);           /* requiere lock */
void state_set_measure(node_t *n, const char *var, const char *value); /* requiere lock */

/* Registra la alerta y la reenvía a los operadores suscritos. Requiere lock. */
void state_add_alert(const char *node_id, const char *type, const char *value);
int state_alerts_snapshot(alert_t *out, int max); /* requiere lock; devuelve n, más reciente primero */

void state_subscribe(int fd);   /* requiere lock */
void state_unsubscribe(int fd); /* requiere lock */

extern node_t g_nodes[MAX_NODES];
extern stats_t g_stats;

#endif
