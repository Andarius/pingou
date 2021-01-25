import asyncpg
from asyncpg.connection import Connection
from typing import List, AsyncIterator
import asyncio

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


async def connect_pool(url: str, db: str):
    pool = await asyncpg.create_pool(f'postgresql://{url}/{db}', init=init_connection)
    return pool


async def insert_pg(conn: Connection, table: str, data: dict) -> str:
    keys, values = zip(*[(k, v) for k, v in data.items()])
    _values = ','.join(f'${i}' for i in range(1, len(keys) + 1))
    query = f"INSERT INTO {table} ({','.join(keys)}) VALUES ({_values})"
    return await conn.execute(query, *values)


async def iterate_pg(conn: Connection,
                     query: str,
                     *args,
                     sleep_no_data=1,
                     chunk_size=500) -> AsyncIterator[List[dict]]:
    nb_args = len(args)
    query = f"""
    {query}
    OFFSET ${nb_args + 1} LIMIT ${nb_args + 2}
    """
    from_offset = 0
    while True:
        data = await conn.fetch(query, *args, from_offset, from_offset + chunk_size)
        if not data:
            await asyncio.sleep(sleep_no_data)
        yield data
        from_offset += chunk_size
