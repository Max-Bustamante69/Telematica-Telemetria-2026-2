# Etapa 1: compilar el servidor en C
FROM gcc:14 AS build
WORKDIR /src
COPY server/ ./server/
RUN make -C server clean all

# Etapa 2: imagen final pequeña, solo el binario
FROM debian:bookworm-slim
RUN useradd --system --no-create-home telemetry
COPY --from=build /src/server/build/telemetry-server /usr/local/bin/telemetry-server
USER telemetry

ENV UDP_PORT=5000 TCP_PORT=5001 HTTP_PORT=8080
# 5000/udp telemetría · 5001/tcp registro y operadores · 8080/tcp web
EXPOSE 5000/udp 5001/tcp 8080/tcp

HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD bash -c 'exec 3<>/dev/tcp/127.0.0.1/8080 && printf "GET /health HTTP/1.0\r\n\r\n" >&3 && grep -q ok <&3' || exit 1

ENTRYPOINT ["/usr/local/bin/telemetry-server"]
