#include "log.h"

#include <pthread.h>
#include <stdarg.h>
#include <stdio.h>
#include <time.h>

static pthread_mutex_t g_log_mutex = PTHREAD_MUTEX_INITIALIZER;

void log_msg(const char *tag, const char *fmt, ...) {
    char ts[32];
    time_t now = time(NULL);
    struct tm tm;
    gmtime_r(&now, &tm);
    strftime(ts, sizeof ts, "%Y-%m-%dT%H:%M:%SZ", &tm);

    pthread_mutex_lock(&g_log_mutex);
    printf("%s [%s] ", ts, tag);
    va_list ap;
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    printf("\n");
    fflush(stdout);
    pthread_mutex_unlock(&g_log_mutex);
}
