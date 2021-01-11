import asyncio
from .utils import wait_true
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


def test_queue_worker(loop, pool):
    from pingou.config import PipelineItem
    from pingou.listener.listener import queue_worker
    log_line = '162.142.125.54 - - [31/Dec/2020:09:11:34 +0000] "GET / HTTP/1.1" 404 33 "-" "Mozilla/5.0 (compatible; CensysInspect/1.1; +https://about.censys.io/)" cookie="-" rt=0.002 uct=0.000 uht=0.004 urt=0.004'
    pipeline = [
        PipelineItem(
            parse_expression='{IP_ADDRESS:ip_address} - {TEXT:remote_user} \[{TIMESTAMP:timestamp} {TZ:tz}\] "{REQUEST_METHOD:request_method} {REQUEST:request} {HTTP_VERSION:http_version}" {NUMBER:status_code} {NUMBER:body_bytes_sent} "{TEXT:http_referer}" "{ANY:user_agent}" cookie="{ANY:cookie}" rt={NUMBER:rt} uct={NUMBER:uct} uht={NUMBER:uht} urt={NUMBER:urt}')
    ]

    queue = asyncio.Queue()

    async def worker():
        await queue_worker(queue, pipeline, pool)

    async def fn():
        await queue.put({
            'log': log_line,
            'file': 'a file',
            'inserted_at': dt.datetime(2019, 1, 1, 10, 0, 0).timestamp()
        })
        await asyncio.sleep(3)

    done, pending = loop.run_until_complete(
        asyncio.wait([worker(), fn()],
                     return_when=asyncio.FIRST_COMPLETED)
    )

    for x in pending:
        x.cancel()
    for x in done:
        x.result()
