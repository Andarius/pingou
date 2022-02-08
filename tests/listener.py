import asyncio
import datetime as dt

import pytest
import requests

from .conftest import DATA_PATH, PG_URL, PG_DB
from .utils import (
    wait_true, fetch_one, fetch_all, insert_many,
    append_line)


def _count_logs(engine, processed_at_not_null=False):
    query = (
        'SELECT count(*) from monitoring.nginx_logs where processed_at is not null'
        if processed_at_not_null else
        'SELECT count(*) from monitoring.nginx_logs')
    return fetch_one(engine, query)[0]


def _fetch_last_item(engine):
    return fetch_one(engine, 'SELECT * from monitoring.nginx_logs order by inserted_at desc',
                     as_dict=True)


@pytest.mark.usefixtures('clean_pg')
def test_file_listener(loop, log_file, pool, engine):
    from pingou.listener.listener import listen_to_file

    async def fn():
        fut = asyncio.create_task(listen_to_file(str(log_file), pool))
        await asyncio.sleep(0.1)
        for i, log_line in enumerate(['a log', 'a second log']):
            append_line(log_file, log_line)
            await wait_true(lambda: _count_logs(engine) == i + 1)
            item = _fetch_last_item(engine)
            assert item['log'] == log_line
            assert item['file'] == str(log_file)
            assert item['inserted_at']
            assert not item['processed_at']
        fut.cancel()

    loop.run_until_complete(fn())


@pytest.mark.usefixtures('clean_pg')
def test_queue_worker(loop, pool, engine):
    from pingou.config import PipelineItem
    from pingou.listener.listener import queue_worker

    log_line = '162.142.125.54 - - [31/Dec/2020:09:11:34 +0000] "GET / HTTP/1.1" 404 33 "-" "Mozilla/5.0 (compatible; CensysInspect/1.1; +https://about.censys.io/)" cookie="-" rt=0.002 uct=0.000 uht=0.004 urt=0.004'
    pipeline = [
        PipelineItem(
            parse_expression='{IP_ADDRESS:ip_address} - {TEXT:remote_user} \\[{TIMESTAMP_FULL:timestamp} {TZ:tz}\\] "{REQUEST_METHOD:request_method} {REQUEST:request} {HTTP_VERSION:http_version}" {NUMBER:status_code} {NUMBER:body_bytes_sent} "{TEXT:http_referer}" "{ANY:user_agent}" cookie="{ANY:cookie}" rt={NUMBER:rt} uct={NUMBER:uct} uht={NUMBER:uht} urt={NUMBER:urt}')
    ]

    async def test():
        fut = asyncio.create_task(queue_worker(pool, pipeline, [], chunk_size=1))
        await asyncio.sleep(0.1)
        insert_many('monitoring.nginx_logs',
                    [{
                        'log': log_line,
                        'file': 'a file',
                        'inserted_at': dt.datetime(2019, 1, 1, 10, 0, 0),
                        'error': False
                    }],
                    engine)
        await asyncio.sleep(1)
        assert _count_logs(engine, processed_at_not_null=True) == 1
        data = _fetch_last_item(engine)
        assert data.pop('id') is not None
        assert data.pop('processed_at')
        assert data == {'file': 'a file',
                        'infos': {'body_bytes_sent': '33',
                                  'cookie': '-',
                                  'http_referer': '-',
                                  'http_version': '1.1',
                                  'ip_address': '162.142.125.54',
                                  'remote_user': '-',
                                  'request': '/',
                                  'request_method': 'GET',
                                  'rt': '0.002',
                                  'status_code': '404',
                                  'timestamp': '31/Dec/2020:09:11:34',
                                  'tz': '+0000',
                                  'uct': '0.000',
                                  'uht': '0.004',
                                  'urt': '0.004',
                                  'user_agent': 'Mozilla/5.0 (compatible; CensysInspect/1.1; '
                                                '+https://about.censys.io/)'},
                        'inserted_at': dt.datetime(2019, 1, 1, 10, 0),
                        'log': '162.142.125.54 - - [31/Dec/2020:09:11:34 +0000] "GET / HTTP/1.1" 404 '
                               '33 "-" "Mozilla/5.0 (compatible; CensysInspect/1.1; '
                               '+https://about.censys.io/)" cookie="-" rt=0.002 uct=0.000 uht=0.004 '
                               'urt=0.004',
                        'error': False
                        }
        fut.cancel()

    loop.run_until_complete(test())


@pytest.mark.usefixtures('clean_pg')
def test_queue_worker_no_match(engine, pool, loop):
    from pingou.config import PipelineItem
    from pingou.listener.listener import queue_worker

    log_line = '127.0.0.1 - - [25/Jan/2021:16:35:54 +0000] "GET / HTTP/1.1" 200 612 "-" "python-requests/2.25.1" "-"'
    pipeline = [
        PipelineItem(
            parse_expression='{IP_ADDRESS:ip_address} - {TEXT:remote_user} \\[{TIMESTAMP_FULL:timestamp} {TZ:tz}\\] "{REQUEST_METHOD:request_method} {REQUEST:request} {HTTP_VERSION:http_version}" {NUMBER:status_code} {NUMBER:body_bytes_sent} "{TEXT:http_referer}" "{ANY:user_agent}" cookie="{ANY:cookie}" rt={NUMBER:rt} uct={NUMBER:uct} uht={NUMBER:uht} urt={NUMBER:urt}')
    ]

    async def test():
        fut = asyncio.create_task(queue_worker(pool, pipeline, [], chunk_size=1))
        insert_many('monitoring.nginx_logs',
                    [{
                        'log': log_line,
                        'file': 'a file',
                        'inserted_at': dt.datetime(2019, 1, 1, 10, 0, 0),
                        'error': False
                    }],
                    engine)
        await asyncio.sleep(0.5)
        assert _count_logs(engine, processed_at_not_null=True) == 1
        data = _fetch_last_item(engine)
        assert data.pop('id') is not None
        assert data.pop('processed_at')
        assert data == {
            'log': '127.0.0.1 - - [25/Jan/2021:16:35:54 +0000] "GET / HTTP/1.1" 200 612 "-" "python-requests/2.25.1" "-"',
            'infos': None,
            'file': 'a file',
            'inserted_at': dt.datetime(2019, 1, 1, 10, 0),
            'error': False
        }
        fut.cancel()

    loop.run_until_complete(test())


@pytest.mark.xfail
@pytest.mark.usefixtures('clean_pg')
def test_listen_nginx(loop, nginx_logs, pool, engine):
    from pingou.listener.listener import listen_to_file

    access_logs, error_logs = nginx_logs

    async def test():
        f = asyncio.create_task(listen_to_file(str(access_logs), pool))
        f1 = asyncio.create_task(listen_to_file(str(error_logs), pool))
        # Waiting for listener to start
        await asyncio.sleep(1)

        # Testing access
        resp = requests.get('http://127.0.0.1')
        assert resp.status_code == 200
        await wait_true(lambda: _count_logs(engine) == 1)
        item = _fetch_last_item(engine)
        assert item['log'].startswith('127.0.0.1 - - ')
        assert item['file'] == str(access_logs)
        assert item['inserted_at']

        # Testing again access
        resp = requests.get('http://127.0.0.1')
        assert resp.status_code == 200
        await wait_true(lambda: _count_logs(engine) == 2)
        item = _fetch_last_item(engine)
        assert item['log'].startswith('127.0.0.1 - - ')

        # Testing error
        resp = requests.get('http://127.0.0.1/error')
        assert resp.status_code == 404
        await wait_true(lambda: _count_logs(engine) == 4)
        items = fetch_all(engine, 'SELECT * from monitoring.nginx_logs order by inserted_at desc limit 2')
        access_item, error_item = ((items[0], items[1])
                                   if not items[0]['error']
                                   else (items[1], items[0]))
        assert access_item['file'] == str(access_logs)
        assert error_item['file'] == str(error_logs)
        assert 'GET /error ' in access_item['log']
        assert '[error]' in error_item['log']

        f.cancel()
        f1.cancel()

    loop.run_until_complete(test())


DEFAULT_OPTIONS = {
    'pg_url': f'{PG_URL}/{PG_DB}',
    'table': 'monitoring.nginx_logs'
}

@pytest.mark.xfail
@pytest.mark.usefixtures('clean_pg')
def test_listen_nginx_full(loop, nginx_logs, pool, engine):
    from pingou.listener.listener import run_listener, run_worker

    async def listener():
        options = {
            **DEFAULT_OPTIONS,
            'nb_workers': 0,
            'config_path': DATA_PATH / 'config.yml'
        }
        await run_listener(**options)

    async def worker():
        options = {
            **DEFAULT_OPTIONS,
            'nb_workers': 1,
            'config_path': DATA_PATH / 'config.yml'
        }
        await run_worker(**options)

    async def test():
        f1, f2 = asyncio.create_task(worker()), asyncio.create_task(listener())
        # Waiting for listener to start
        await asyncio.sleep(2)

        # Testing access
        resp = requests.get('http://127.0.0.1')
        assert resp.status_code == 200
        await asyncio.sleep(1)
        assert _count_logs(engine) == 1
        assert _count_logs(engine, processed_at_not_null=True) == 1
        item = _fetch_last_item(engine)
        assert item['log'].startswith('127.0.0.1 - - ')
        assert item['inserted_at']
        assert item['infos']

        # Testing again access
        resp = requests.get('http://127.0.0.1')
        assert resp.status_code == 200
        await wait_true(lambda: _count_logs(engine, processed_at_not_null=True) == 2,
                        sleep=0.5)
        item = _fetch_last_item(engine)
        assert item['log'].startswith('127.0.0.1 - - ')
        #
        # # Testing error
        resp = requests.get('http://127.0.0.1/error')
        assert resp.status_code == 404
        await wait_true(lambda: _count_logs(engine, processed_at_not_null=True) == 4, sleep=0.5)
        items = fetch_all(engine, 'SELECT * from monitoring.nginx_logs order by inserted_at desc limit 2')
        access_item, error_item = ((items[0], items[1])
                                   if not items[0]['error']
                                   else (items[1], items[0]))
        assert access_item['infos']
        assert '[error]' in error_item['log']
        f1.cancel()
        f2.cancel()

    loop.run_until_complete(test())


@pytest.mark.xfail
@pytest.mark.usefixtures('clean_pg')
def test_listen_nginx_full_listener_only(loop, nginx_logs, pool, engine):
    from pingou.listener.listener import run_listener

    async def listener():
        options = {
            **DEFAULT_OPTIONS,
            'nb_workers': 1,
            'config_path': DATA_PATH / 'config.yml'
        }
        await run_listener(**options)

    async def test():
        f = asyncio.create_task(listener())
        # Waiting for listener to start
        await asyncio.sleep(1)

        # Testing access
        resp = requests.get('http://127.0.0.1')
        assert resp.status_code == 200
        await wait_true(lambda: _count_logs(engine) == 1)
        await wait_true(lambda: _count_logs(engine, processed_at_not_null=True) == 1,
                        sleep=0.5)
        item = _fetch_last_item(engine)
        assert item['log'].startswith('127.0.0.1 - - ')
        assert item['inserted_at']
        assert item['infos']

        # Testing again access
        resp = requests.get('http://127.0.0.1')
        assert resp.status_code == 200
        await wait_true(lambda: _count_logs(engine, processed_at_not_null=True) == 2,
                        sleep=0.5)
        item = _fetch_last_item(engine)
        assert item['log'].startswith('127.0.0.1 - - ')

        # # Testing error
        resp = requests.get('http://127.0.0.1/error')
        assert resp.status_code == 404
        await wait_true(lambda: _count_logs(engine, processed_at_not_null=True) == 4, sleep=0.5)
        items = fetch_all(engine, 'SELECT * from monitoring.nginx_logs order by inserted_at desc limit 2')
        access_item, error_item = ((items[0], items[1])
                                   if not items[0]['error']
                                   else (items[1], items[0]))
        assert access_item['infos']
        assert '[error]' in error_item['log']

        f.cancel()

    loop.run_until_complete(test())
