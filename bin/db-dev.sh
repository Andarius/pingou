#!/usr/bin/env bash


cd "$(dirname "$0")/.." || exit

# If the volume does not exist, create it: docker volume create --name=nginx_logs
docker-compose --project-directory "docker" \
                 -f "docker/docker-compose.yml" "${@}"
