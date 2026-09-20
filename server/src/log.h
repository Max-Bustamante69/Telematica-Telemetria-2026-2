#ifndef LOG_H
#define LOG_H

/* Escribe una línea con hora y etiqueta en stdout. Segura entre hilos. */
void log_msg(const char *tag, const char *fmt, ...);

#endif
