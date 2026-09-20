#!/bin/bash
# Script de arranque (user data) para una instancia EC2 con Ubuntu 24.04.
# Instala Docker, clona el repositorio y levanta el servidor en un contenedor.
# Variables que debe reemplazar el equipo antes de lanzar la instancia:
#   REPO_URL   URL del repositorio (privado: usar un token de solo lectura o una deploy key)
set -eux
REPO_URL="${REPO_URL:-https://github.com/Max-Bustamante69/Telematica-Telemetria-2026-2.git}"

apt-get update
apt-get install -y ca-certificates curl git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
usermod -aG docker ubuntu

cd /opt
git clone "$REPO_URL" telemetria
cd telemetria
docker compose up -d --build server
docker ps
