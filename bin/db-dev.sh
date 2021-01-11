#!/usr/bin/env bash


cd "$(dirname "$0")/.." || exit

docker-compose --project-directory "docker/dev" \
                 -f "docker/dev/docker-compose.yml" "${@}"
