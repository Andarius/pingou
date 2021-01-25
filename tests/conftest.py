import pytest
import asyncpg
import psycopg2
import asyncio
import os
from pathlib import Path
import shutil
import logging
from .utils import get_tables, clean_tables
from pg import init_connection

_cur_file = Path(os.path.dirname(__file__))
TMP_PATH = _cur_file / '..' / 'tmp'
NGINX_LOGS_PATH = _cur_file / 'nginx_logs'
DATA_PATH = _cur_file / 'files'

@pytest.fixture(scope='session', autouse=True)
def init_logs():
    from logs import init_logging
    init_logging(logging.WARNING)


@pytest.fixture(scope='session')
def pg_envs():
    return {
        'PG_URL': '127.0.0.1',
        'PG_USER': 'postgres',
        'PG_PWD': 'postgres',
        'PG_PORT': '5432',
        'PG_DB': 'monitoring'
    }


@pytest.fixture(scope='session')
def engine(pg_envs):
    conn = psycopg2.connect("user={PG_USER} password={PG_PWD} host={PG_URL} port={PG_PORT} dbname={PG_DB}".format(
        **pg_envs
    ))

    yield conn

    conn.close()


async def connect_pg(pg_envs):
    conn = await asyncpg.connect('postgresql://{PG_USER}:{PG_PWD}@{PG_URL}:{PG_PORT}/{PG_DB}'.format(
        **pg_envs
    ))
    await init_connection(conn)
    return conn


@pytest.fixture(scope='session')
def aengine(loop, pg_envs):
    conn = loop.run_until_complete(connect_pg(pg_envs))
    yield conn
    loop.run_until_complete(conn.close())


@pytest.fixture(scope='session')
def pool(loop, pg_envs):
    pool = loop.run_until_complete(
        asyncpg.create_pool('postgresql://{PG_USER}:{PG_PWD}@{PG_URL}:{PG_PORT}/{PG_DB}'.format(
            **pg_envs
        ), init=init_connection))

    yield pool
    loop.run_until_complete(asyncio.wait_for(pool.close(), 1))


@pytest.fixture(scope='session')
def loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.get_event_loop()
    return loop


@pytest.fixture()
def tmp_path():
    shutil.rmtree(TMP_PATH, ignore_errors=True)
    os.makedirs(TMP_PATH)

    yield TMP_PATH

    # shutil.rmtree(TMP_PATH, ignore_errors=True)


@pytest.fixture()
def log_file(tmp_path):
    log_path = tmp_path / 'pingou.log'
    log_path.touch()
    yield log_path


@pytest.fixture(scope='function', autouse=True)
def clean_pg(engine):
    engine.commit()
    tables = get_tables(engine)

    clean_tables(engine, tables)
    yield
    engine.commit()
    clean_tables(engine, tables)


@pytest.fixture()
def nginx_logs():
    access_file = NGINX_LOGS_PATH / 'access.log'
    error_file = NGINX_LOGS_PATH / 'error.log'

    # access_file.touch()
    # error_file.touch()

    return (access_file, error_file)
