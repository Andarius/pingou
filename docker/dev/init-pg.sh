#!/usr/bin/env bash

set -xe

readonly INIT_FILE="${PGDATA}/init.sql"
readonly SQL_FOLDER='/sql_scripts'
readonly POSTGRES_USER='postgres'

for f in $(ls -1v "${SQL_FOLDER}"/*.sql)
do
    cat "${f}" >> "${INIT_FILE}"
done

echo "CREATE DATABASE pingou;" | psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER"
< "${INIT_FILE}" psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "pingou"