import asyncio
import datetime as dt
from pathlib import Path
from typing import List

from asyncpg import Connection
from asyncpg.pool import Pool

from pingou.logs import logger
from pingou.pg import insert_pg, iterate_pg, connect_pool
from .tail import tail
from ..config import Config, PipelineItem
from ..parser import parse_line

_GET_LOG_QUERY = 'SELECT id, log, error from {table} where processed_at is NULL order by inserted_at asc'


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
                       access_pipelines: List[PipelineItem],
                       error_pipelines: List[PipelineItem],
                       *,
                       table: str = 'monitoring.nginx_logs',
                       chunk_size: int = 100):
    if not access_pipelines and not error_pipelines:
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
                pipelines = error_pipelines if item['error'] else access_pipelines
                for _pipe in pipelines:
                    log_infos = parse_line(log_line, _pipe.regex)
                    if log_infos:
                        break
                else:
                    log_infos = None
                data.append({'infos': log_infos, 'id': item['id']})
            try:
                await update_items(conn, table, data)
            except Exception as e:
                print(e.args)
    finally:
        await pool.release(conn, timeout=10)


async def listen_to_file(file_path: str,
                         pool: Pool,
                         *,
                         is_error: bool = False,
                         last_lines: int = 0,
                         fp_poll_secs: float = 0.125,
                         table: str = 'monitoring.nginx_logs'):
    if not Path(file_path).exists():
        raise FileNotFoundError(f'No file found at {file_path}')

    logger.info(f'Listening to file: {file_path}')
    conn = await pool.acquire()
    try:
        async for line in tail(file_path,
                               last_lines=last_lines,
                               fp_poll_secs=fp_poll_secs):
            await insert_pg(conn, table, {
                'log': line,
                'file': file_path,
                'inserted_at': dt.datetime.now(),
                'error': is_error
            })
    finally:
        await pool.release(conn, timeout=10)


async def run_worker(
        config_path: Path,
        nb_workers: int,
        table: str,
        pg_url: str,
):
    config = Config.load(config_path)
    pool = await connect_pool(pg_url)
    logger.info(f'Listening to events...')
    workers = [
        queue_worker(pool, config.access_pipelines, config.error_pipelines,
                     table=table)
        for _path in range(nb_workers)
    ]
    try:
        await asyncio.gather(*workers)
    except KeyboardInterrupt:
        logger.info('Stopping workers')


async def run_listener(
        config_path: Path,
        nb_workers: int,
        table: str,
        pg_url: str,
):
    config = Config.load(config_path)
    pool = await connect_pool(pg_url)

    fns = [
        listen_to_file(str(_path), pool, table=table)
        for _path in config.access_files
    ]
    fns += [
        listen_to_file(str(_path), pool, is_error=True,
                       table=table)
        for _path in config.error_files
    ]
    if nb_workers:
        logger.info(f'Starting {nb_workers} workers')
        fns += [
            queue_worker(pool,
                         config.access_pipelines,
                         config.error_pipelines,
                         table=table)
            for _ in range(nb_workers)
        ]
    try:
        await asyncio.gather(*fns)
    except KeyboardInterrupt:
        logger.info('Stopping listeners')
