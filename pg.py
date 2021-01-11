from asyncpg.connection import Connection


async def insert_pg(conn: Connection, table: str, data: dict) -> str:
    keys, values = zip(*[(k, v) for k, v in data.items()])
    _values = ','.join(f'${i}' for i in range(1, len(keys) + 1))
    query = f"INSERT INTO {table} ({','.join(keys)}) VALUES ({_values})"
    print(query)
    return await conn.execute(query, *values)
