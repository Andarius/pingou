import asyncio
from .utils import (
    run_first_completed,
    wait_true, fetch_one, fetch_all,
    append_line)
import datetime as dt
import requests


def test_file_listener(loop, log_file):
    from pingou.listener.listener import listen_to_file

    queue = asyncio.Queue()

    async def listen_events():
        await listen_to_file(log_file, queue)

    async def fn():
        await asyncio.sleep(1)
        log_line = 'a log'
        append_line(log_file, log_line)
        await wait_true(lambda: queue.qsize() == 1)
        item = await queue.get()
        assert item['log'] == log_line
        assert item['file'] == log_file
        assert item['inserted_at']

        # Adding another line
        log_line = 'a second line'
        append_line(log_file, log_line)
        await wait_true(lambda: queue.qsize() == 1)
        item = await queue.get()
        assert item['log'] == log_line
        assert item['file'] == log_file
        assert item['inserted_at']

    run_first_completed(loop, listen_events(), fn())


def test_queue_worker(loop, pool, engine):
    from pingou.config import PipelineItem
    from pingou.listener.listener import queue_worker

    log_line = '162.142.125.54 - - [31/Dec/2020:09:11:34 +0000] "GET / HTTP/1.1" 404 33 "-" "Mozilla/5.0 (compatible; CensysInspect/1.1; +https://about.censys.io/)" cookie="-" rt=0.002 uct=0.000 uht=0.004 urt=0.004'
    pipeline = [
        PipelineItem(
            parse_expression='{IP_ADDRESS:ip_address} - {TEXT:remote_user} \\[{TIMESTAMP:timestamp} {TZ:tz}\\] "{REQUEST_METHOD:request_method} {REQUEST:request} {HTTP_VERSION:http_version}" {NUMBER:status_code} {NUMBER:body_bytes_sent} "{TEXT:http_referer}" "{ANY:user_agent}" cookie="{ANY:cookie}" rt={NUMBER:rt} uct={NUMBER:uct} uht={NUMBER:uht} urt={NUMBER:urt}')
    ]

    queue = asyncio.Queue()

    async def worker():
        await queue_worker(queue, pipeline, pool)

    async def test():
        await queue.put({
            'log': log_line,
            'file': 'a file',
            'inserted_at': dt.datetime(2019, 1, 1, 10, 0, 0)
        })
        await wait_true(lambda: fetch_one(engine, 'SELECT count(*) from pingou.nginx_logs')[0] == 1)
        data = fetch_all(engine, 'SELECT * from pingou.nginx_logs')
        assert data[0].pop('id') is not None
        assert data == [{'file': 'a file',
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
                                'urt=0.004'}]

    run_first_completed(loop, worker(), test())


def test_queue_worker_no_match(engine, pool, loop):
    from pingou.config import PipelineItem
    from pingou.listener.listener import queue_worker

    log_line = '127.0.0.1 - - [25/Jan/2021:16:35:54 +0000] "GET / HTTP/1.1" 200 612 "-" "python-requests/2.25.1" "-"'
    pipeline = [
        PipelineItem(
            parse_expression='{IP_ADDRESS:ip_address} - {TEXT:remote_user} \\[{TIMESTAMP:timestamp} {TZ:tz}\\] "{REQUEST_METHOD:request_method} {REQUEST:request} {HTTP_VERSION:http_version}" {NUMBER:status_code} {NUMBER:body_bytes_sent} "{TEXT:http_referer}" "{ANY:user_agent}" cookie="{ANY:cookie}" rt={NUMBER:rt} uct={NUMBER:uct} uht={NUMBER:uht} urt={NUMBER:urt}')
    ]
    queue = asyncio.Queue()

    async def worker():
        await queue_worker(queue, pipeline, pool)

    async def test():
        await queue.put({
            'log': log_line,
            'file': 'a file',
            'inserted_at': dt.datetime(2019, 1, 1, 10, 0, 0)
        })
        await wait_true(lambda: fetch_one(engine, 'SELECT count(*) from pingou.nginx_logs')[0] == 1)
        data = fetch_all(engine, 'SELECT * from pingou.nginx_logs')[0]
        assert data.pop('id') is not None
        assert data == {
            'log': '127.0.0.1 - - [25/Jan/2021:16:35:54 +0000] "GET / HTTP/1.1" 200 612 "-" "python-requests/2.25.1" "-"',
            'infos': None,
            'file': 'a file',
            'inserted_at': dt.datetime(2019, 1, 1, 10, 0)
        }

    run_first_completed(loop, worker(), test())


def test_listen_nginx(loop, nginx_logs):
    from pingou.listener.listener import listen_to_file

    queue = asyncio.Queue()

    access_logs, error_logs = nginx_logs

    async def listen_access_events():
        await listen_to_file(str(access_logs), queue)

    async def listen_error_events():
        await listen_to_file(str(error_logs), queue)

    async def test():
        # Waiting for listener to start
        await asyncio.sleep(1)

        # Testing access
        resp = requests.get('http://127.0.0.1')
        assert resp.status_code == 200
        await wait_true(lambda: queue.qsize() == 1)
        item = queue.get_nowait()
        assert item['log'].startswith('127.0.0.1 - - ')
        assert item['file'] == str(access_logs)
        assert item['inserted_at']

        # Testing again access
        resp = requests.get('http://127.0.0.1')
        assert resp.status_code == 200
        await wait_true(lambda: queue.qsize() == 1)
        item = queue.get_nowait()
        assert item['log'].startswith('127.0.0.1 - - ')

        # Testing error
        resp = requests.get('http://127.0.0.1/error')
        assert resp.status_code == 404
        await wait_true(lambda: queue.qsize() == 2, sleep=1)
        item_1, item_2 = queue.get_nowait(), queue.get_nowait()
        access_item, error_item = ((item_1, item_2)
                                   if item_1['file'] == str(access_logs)
                                   else (item_2, item_1))
        assert access_item['file'] == str(access_logs)
        assert error_item['file'] == str(error_logs)
        assert 'GET /error ' in access_item['log']
        assert '[error]' in error_item['log']

    run_first_completed(loop,
                        listen_error_events(),
                        listen_access_events(),
                        test())


