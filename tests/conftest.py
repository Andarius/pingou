import pytest
import asyncpg
import psycopg2
import asyncio
import os
from pathlib import Path
import shutil
import logging
from .utils import get_tables, clean_tables

_cur_file = Path(os.path.dirname(__file__))
TMP_PATH = _cur_file / '..' / 'tmp'


@pytest.fixture(scope='session', autouse=True)
def init_logs():
    from logs import init_logging
    init_logging(logging.WARNING)


@pytest.fixture(scope='session')
def pg_envs():
    return {
        'PG_URL': os.getenv('PG_URL', '127.0.0.1'),
        'PG_USER': os.getenv('PG_USER', 'postgres'),
        'PG_PWD': os.getenv('PG_PWD', 'postgres'),
        'PG_PORT': os.getenv('PG_PORT', 5432),
        'PG_DB': os.getenv('PG_USERS_DB', 'postgres')
    }


@pytest.fixture(scope='session')
def engine(pg_envs):
    conn = psycopg2.connect("user={PG_USER} password={PG_PWD} host={PG_URL} port={PG_PORT} dbname={PG_DB}".format(
        **pg_envs
    ))

    yield conn

    conn.close()


@pytest.fixture(scope='session')
def aengine(loop, pg_envs):
    conn = loop.run_until_complete(asyncpg.connect('postgresql://{PG_USER}:{PG_PWD}@{PG_URL}:{PG_PORT}/{PG_DB}'.format(
        **pg_envs
    )))
    yield conn
    loop.run_until_complete(conn.close())


@pytest.fixture(scope='session')
def pool(loop, pg_envs):
    pool = loop.run_until_complete(
        asyncpg.create_pool('postgresql://{PG_USER}:{PG_PWD}@{PG_URL}:{PG_PORT}/{PG_DB}'.format(
            **pg_envs
        )))

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

    shutil.rmtree(TMP_PATH, ignore_errors=True)


@pytest.fixture()
def log_file(tmp_path):
    log_path = tmp_path / 'log.log'
    log_path.touch()
    yield log_path


@pytest.fixture(scope='function', autouse=False)
def clean_pg(engine, no_clean):
    engine.commit()
    tables = get_tables(engine)

    clean_tables(engine, tables)
    yield
    if not no_clean:
        engine.commit()
        clean_tables(engine, tables)
