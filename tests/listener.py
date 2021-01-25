import asyncio
from .utils import wait_true, fetch_one, fetch_all
import datetime as dt


def test_file_listener(loop, log_file):
    from pingou.listener.listener import listen_to_file

    queue = asyncio.Queue()
    log_line = 'a log'

    async def listen_events():
        await listen_to_file(log_file, queue)
        await wait_true(lambda _: queue.qsize() == 1)
        item = await queue.get()
        assert item['log'] == log_line
        assert item['file'] == log_file
        assert item['inserted_at']

    async def fn():
        log_file.write_text(log_line)

    done, pending = loop.run_until_complete(
        asyncio.wait([listen_events(), fn()],
                     return_when=asyncio.FIRST_COMPLETED)
    )

    for x in pending:
        x.cancel()
    for x in done:
        x.result()


def test_queue_worker(loop, pool, engine):
    from pingou.config import PipelineItem
    from pingou.listener.listener import queue_worker

    log_line = '162.142.125.54 - - [31/Dec/2020:09:11:34 +0000] "GET / HTTP/1.1" 404 33 "-" "Mozilla/5.0 (compatible; CensysInspect/1.1; +https://about.censys.io/)" cookie="-" rt=0.002 uct=0.000 uht=0.004 urt=0.004'
    pipeline = [
        PipelineItem(
            parse_expression='{IP_ADDRESS:ip_address} - {TEXT:remote_user} \\[{TIMESTAMP:timestamp} {TZ:tz}\\] "{REQUEST_METHOD:request_method} {REQUEST:request} {HTTP_VERSION:http_version}" {NUMBER:status_code} {NUMBER:body_bytes_sent} "{TEXT:http_referer}" "{ANY:user_agent}" cookie="{ANY:cookie}" rt={NUMBER:rt} uct={NUMBER:uct} uht={NUMBER:uht} urt={NUMBER:urt}')
    ]

    queue = asyncio.Queue()

    def count_table():
        return fetch_one(engine, 'SELECT count(*) from pingou.nginx_logs')[0] == 1

    async def worker():
        await queue_worker(queue, pipeline, pool)

    async def test():
        await queue.put({
            'log': log_line,
            'file': 'a file',
            'inserted_at': dt.datetime(2019, 1, 1, 10, 0, 0)
        })
        await wait_true(count_table)
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

    done, pending = loop.run_until_complete(
        asyncio.wait([worker(), test()],
                     return_when=asyncio.FIRST_COMPLETED)
    )

    for x in pending:
        x.cancel()
    for x in done:
        x.result()
