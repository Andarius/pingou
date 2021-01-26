#!/usr/bin/env bash


cd "$(dirname "$0")/.." || exit

docker-compose --project-directory "docker/prd" \
                 -f "docker/prd/docker-compose.yml" "${@}"
