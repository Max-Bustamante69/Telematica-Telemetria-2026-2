/* Hilo que marca como INACTIVE a los nodos que dejaron de reportar. */
#include "log.h"
#include "server.h"
#include "state.h"

#include <stdio.h>
#include <time.h>
#include <unistd.h>

void *watchdog_loop(void *arg) {
    (void)arg;
    while (g_running) {
        sleep(1);
        time_t now = time(NULL);
        state_lock();
        for (int i = 0; i < MAX_NODES; i++) {
            node_t *n = &g_nodes[i];
            if (!n->used || !n->active) continue;
            if (now - n->last_seen > INACTIVE_AFTER_S) {
                n->active = 0;
                log_msg("NODE", "%s pasa a INACTIVE (%lds sin telemetria)", n->id,
                        (long)(now - n->last_seen));
                if (!n->inactive_alerted) {
                    n->inactive_alerted = 1;
                    char secs[16];
                    snprintf(secs, sizeof secs, "%ld", (long)(now - n->last_seen));
                    state_add_alert(n->id, "NODE_INACTIVE", secs);
                }
            }
        }
        state_unlock();
    }
    return NULL;
}
