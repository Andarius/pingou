from asyncpg.connection import Connection

try:
    import ujson as json
except ImportError:
    import json


async def init_connection(conn):
    await conn.set_type_codec(
        'jsonb',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog'
    )
    await conn.set_type_codec(
        'json',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog'
    )


async def insert_pg(conn: Connection, table: str, data: dict) -> str:
    keys, values = zip(*[(k, v) for k, v in data.items()])
    _values = ','.join(f'${i}' for i in range(1, len(keys) + 1))
    query = f"INSERT INTO {table} ({','.join(keys)}) VALUES ({_values})"
    return await conn.execute(query, *values)
