from .tail import tail
from typing import List
import asyncio
from logs import logger
import time
from asyncpg import Connection
from asyncpg.pool import Pool
from ..parser import parse_line
from ..config import Config, PipelineItem
from pg import insert_pg, iterate_pg, connect_pool
import datetime as dt

_GET_LOG_QUERY = 'SELECT id, log from {table} where processed_at is NULL order by inserted_at asc'


async def update_items(conn: Connection,
                       table: str,
                       data: List[dict]):
    query = f"""
    UPDATE {table}
        SET infos = $1,
            processed_at = now()
    WHERE id = $2
    """
    await conn.executemany(query, [(x['infos'], x['id'])
                                   for x in data])


async def queue_worker(pool: Pool,
                       pipelines: List[PipelineItem],
                       *,
                       table: str = 'pingou.nginx_logs',
                       chunk_size: int = 100):
    if not pipelines:
        logger.warning(f'No pipelines specified, stopping worker')
        return

    conn = await pool.acquire()
    try:
        async for chunk in iterate_pg(conn,
                                      _GET_LOG_QUERY.format(table=table),
                                      chunk_size=chunk_size):
            data = []
            for item in chunk:
                log_line = item['log']
                for _pipe in pipelines:
                    log_infos = parse_line(log_line, _pipe.regex)
                    if log_infos:
                        break
                else:
                    log_infos = None
                data.append({'infos': log_infos, 'id': item['id']})


            await update_items(conn, table, data)
    finally:
        await pool.release(conn, timeout=10)


async def listen_to_file(file_path: str,
                         pool: Pool,
                         *,
                         last_lines: int = 0,
                         fp_poll_secs: float = 0.125,
                         table: str = 'pingou.nginx_logs'):
    logger.info(f'Listening to file: {file_path}')
    conn = await pool.acquire()
    try:
        async for line in tail(file_path,
                               last_lines=last_lines,
                               fp_poll_secs=fp_poll_secs):
            await insert_pg(conn, table, {'log': line, 'file': file_path, 'inserted_at': dt.datetime.now()})
    finally:
        await pool.release(conn, timeout=10)


async def listener_main(options):
    config = Config.load(options.config)

    pool = await connect_pool(options.pg, options.pg_db)

    file_listeners = [
        listen_to_file(_path, pool)
        for _path in config.sources.access
    ]
    file_listeners += [
        listen_to_file(_path, pool)
        for _path in config.sources.error
    ]
    try:
        await asyncio.gather(*file_listeners)
    except KeyboardInterrupt:
        logger.info('Stopping listeners')


async def worker_main(options):
    config = Config.load(options.config)
    pool = await connect_pool(options.pg, options.pg_db)
    workers = [
        queue_worker(pool, config.pipelines)
        for _path in range(options.nb_workers)
    ]
    try:
        await asyncio.gather(*workers)
    except KeyboardInterrupt:
        logger.info('Stopping workers')
