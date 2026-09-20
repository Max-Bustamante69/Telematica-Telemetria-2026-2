/* Parseo y manejo de mensajes TLP/1.0 (ver docs/PROTOCOLO.md). */
#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stddef.h>

#define MAX_LINE 512
#define MAX_FIELDS 8

/* Divide "A|B|C" en campos. Modifica line. Devuelve el número de campos. */
int tlp_split(char *line, char *fields[], int max_fields);

int tlp_valid_id(const char *id);

/* Procesa un datagrama UDP de telemetría.
 * Devuelve el tamaño de la respuesta escrita en reply (0 si no hay respuesta). */
int tlp_handle_udp(const char *datagram, size_t len, char *reply, size_t reply_cap);

/* Procesa una línea TCP (nodo u operador). Escribe la respuesta completa
 * (puede ser multilínea) en out. Devuelve 1 si el servidor debe cerrar la conexión. */
int tlp_handle_tcp(int fd, char *line, char *out, size_t out_cap);

#endif
