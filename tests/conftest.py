import pytest
import asyncpg
import psycopg2
import asyncio
import os
from pathlib import Path
import shutil
import logging
from .utils import get_tables, clean_tables
from pingou.pg import init_connection
from psycopg2.extensions import connection, ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.errors import DuplicateDatabase


_cur_file = Path(os.path.dirname(__file__))
TMP_PATH = _cur_file / '..' / 'tmp'
NGINX_LOGS_PATH = _cur_file / 'nginx_logs'
DATA_PATH = _cur_file / 'files'
SQL_DIR = _cur_file / '..' / 'sql'


@pytest.fixture(scope='session', autouse=True)
def init_logs():
    from pingou.logs import init_logging
    init_logging(logging.WARNING)


PG_HOST = os.getenv('PG_HOST', 'localhost')
PG_PORT = int(os.getenv('PG_PORT', '5432'))
PG_USER = os.getenv('PG_USER', 'postgres')
PG_PASSWORD = os.getenv('PG_PASSWORD', 'postgres')
PG_DB = os.getenv('PG_DB', 'test_pingou')

PG_URL = f'postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}'


@pytest.fixture(scope='session')
def engine() -> connection:
    conn = psycopg2.connect(f'{PG_URL}/{PG_DB}')
    yield conn
    conn.close()


async def connect_pg(url):
    conn = await asyncpg.connect(url)
    await init_connection(conn)
    return conn


@pytest.fixture(scope='session')
def aengine(loop):
    conn = loop.run_until_complete(connect_pg(f'{PG_URL}/{PG_DB}'))
    yield conn
    loop.run_until_complete(conn.close())


@pytest.fixture(scope='session')
def pool(loop):
    pool = loop.run_until_complete(
        asyncpg.create_pool(f'{PG_URL}/{PG_DB}', loop=loop, init=init_connection))

    yield pool
    loop.run_until_complete(asyncio.wait_for(pool.close(), 1))


@pytest.fixture(scope='session')
def loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
def tmp_path():
    shutil.rmtree(TMP_PATH, ignore_errors=True)
    os.makedirs(TMP_PATH)

    yield TMP_PATH

    shutil.rmtree(TMP_PATH, ignore_errors=True)


@pytest.fixture()
def log_file(tmp_path):
    log_path = tmp_path / 'pingou.log'
    log_path.touch()
    yield log_path


@pytest.fixture(scope='function')
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


@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    pg_conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER,
                               password=PG_PASSWORD)
    pg_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with pg_conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {PG_DB}")
    except DuplicateDatabase:
        pass

    pg_test_conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER,
                                    password=PG_PASSWORD, database=PG_DB)
    for sql_file in sorted(SQL_DIR.glob('*.sql'), key=lambda x: int(x.name.split('_')[0])):
        try:
            with pg_test_conn.cursor() as cursor:
                cursor.execute(sql_file.read_text())
        except Exception:
            print(f'Got an error at: {sql_file.name}')
            raise
    pg_test_conn.commit()

    yield
    #
    # with pg_conn.cursor() as cursor:
    #     cursor.execute(f"DROP DATABASE {PG_DB}")
