import json
from pathlib import Path
from enum import Enum
import asyncio
import functools
from typing import List
from psycopg2.extensions import connection

TABLES = None


def get_insert_query(table, data, **kwargs):
    """
    Format data and get the index query
    Args:
        table (str): the table to index to
        data (List[dict]): the data to index
    Returns:
        Tuple[str, List[dict]]: the index query and the formatted data
    """

    def get_values(x, keys):
        values = []
        for k in keys:
            v = x.get(k, None)
            if isinstance(v, dict):
                v = json.dumps(v)
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                v = json.dumps(v)
            elif isinstance(v, Enum):
                v = v.value
            elif isinstance(v, Path):
                v = str(v)
            else:
                pass
            values.append(v)
        return tuple(values)

    keys = frozenset().union(*data)
    data_fmt = [get_values(x, keys) for x in data]
    values_fmt = ', '.join('%s' for _ in keys)
    query = "INSERT INTO {} ({}) VALUES ( {} )".format(table,
                                                       ', '.join(keys),
                                                       values_fmt)
    return query, data_fmt


def fetch_all(engine, query, as_dict=True, data=None):
    with engine.cursor() as cur:
        cur.execute(query) if not data else cur.execute(query, data)
        col_names = [desc[0] for desc in cur.description]
        resp = cur.fetchall()
    return [
        dict(zip(col_names, d)) if as_dict else d[0]
        for d in resp
    ]


def fetch_one(engine, query, *args, **kwargs):
    with engine.cursor() as cur:
        cur.execute(query, args)
        col_names = [desc[0] for desc in cur.description]
        resp = cur.fetchone()
    return dict(zip(col_names, resp)) if kwargs.get('as_dict') else resp


def exec_req(engine, req, *args):
    with engine.cursor() as curr:
        curr.execute(req, args)
    return engine.commit()


def get_tables(engine, ignore=None):
    global TABLES
    if TABLES:
        return TABLES

    table_query = """
    SELECT concat_ws('.', schemaname, tablename) as table
    from pg_catalog.pg_tables
    where schemaname IN ('monitoring')
    ORDER BY schemaname, tablename
    """
    resp = fetch_all(engine, table_query)
    # Foreign keys
    ignore = set(ignore) if ignore else []
    TABLES = [x['table'] for x in resp if x['table'] not in ignore]
    return TABLES


def insert_many(table: str, data: List[dict], conn: connection, **kwargs):
    query, data = get_insert_query(table, data, **kwargs)
    with conn.cursor() as cur:
        _ = cur.executemany(query, data)
    return conn.commit()


_CLEAN_IGNORE_TABLES = set()


def clean_tables(engine, tables):
    tables = set(tables) - _CLEAN_IGNORE_TABLES
    if not tables:
        return
    tables = ', '.join(tables)
    exec_req(engine, f'TRUNCATE {tables}')


async def wait_true(cond, nb_retries=5, sleep=0.2):
    for _ in range(nb_retries):
        if cond():
            break
        await asyncio.sleep(sleep)
    else:
        raise ValueError('Condition was never true')


def trackcalls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, call_count=wrapper.call_count, **kwargs)
        wrapper.called = True
        wrapper.call_count += 1
        return res

    wrapper.called = False
    wrapper.call_count = 0
    return wrapper


def run_first_completed(loop, *fns):
    done, pending = loop.run_until_complete(
        asyncio.wait(fns,
                     return_when=asyncio.FIRST_COMPLETED)
    )

    for x in pending:
        x.cancel()
    for x in done:
        x.result()


def append_line(file: Path, line: str):
    with file.open('a') as f:
        f.write(line)
