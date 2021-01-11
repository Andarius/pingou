#!/usr/bin/env bash

set -xe

readonly INIT_FILE="${PGDATA}/init.sql"
readonly SQL_FOLDER='/sql_scripts'
readonly DB_NAME='monitoring'

for f in $(ls -1v "${SQL_FOLDER}"/*.sql)
do
    cat "${f}" >> "${INIT_FILE}"
done

readonly CREATE_DB_QUERY="SELECT 'CREATE DATABASE $DB_NAME' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec"

echo "$CREATE_DB_QUERY" | psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER"
< "${INIT_FILE}" psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$DB_NAME"