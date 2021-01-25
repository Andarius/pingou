from .tail import tail
from typing import List
import asyncio
from logs import logger
import time
from asyncpg.pool import Pool
from ..parser import parse_line
from ..config import Config, PipelineItem
from pg import insert_pg


async def queue_worker(queue: asyncio.Queue,
                       pipeline: List[PipelineItem],
                       pool: Pool,
                       dest_table: str = 'pingou.nginx_logs'):
    if not pipeline:
        logger.warning(f'No pipeline specified, stopping queue listener')
        return

    conn = await pool.acquire()
    try:
        while True:
            item = await queue.get()
            log_infos, log_line = None, None
            for _pipe in pipeline:
                log_line = item.pop('log')
                log_infos = parse_line(log_line, _pipe.regex)
                if log_infos:
                    break
            if log_line is not None:
                data = {
                    'infos': log_infos,
                    'log': log_line.strip(),
                    **item
                }
                await insert_pg(conn, dest_table, data)
            queue.task_done()
    finally:
        await pool.release(conn, timeout=10)


async def listen_to_file(file_path: str,
                         queue: asyncio.Queue,
                         last_lines: int = 0,
                         fp_poll_secs: float = 0.125):
    logger.info(f'Listening to file: {file_path}')
    async for line in tail(file_path,
                           last_lines=last_lines,
                           fp_poll_secs=fp_poll_secs):
        await queue.put({'log': line, 'file': file_path, 'inserted_at': time.time()})


async def listener_main(options):
    config = Config.load(options.config)

    file_listeners = [
        listen_to_file(_path, config.access_pipeline)
        for _path in config.sources.access
    ]
    file_listeners += [
        listen_to_file(_path, config.error_pipeline)
        for _path in config.sources.error
    ]
    try:
        await asyncio.gather(*file_listeners)
    except KeyboardInterrupt:
        logger.info('Stopping listeners')
