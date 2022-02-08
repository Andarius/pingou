import json
import time
from asyncio import Queue, gather
from enum import Enum
from functools import partial

from .env import RELEASE_STAGE
from .logs import logger


class Listener(Enum):
    new_error = 'nginx_error'


async def _on_new_error(item, **kwargs):
    print(item)


CHANNELS_MAPPING = {
    Listener.new_error: _on_new_error
}


def _on_new_event(connection, pid, channel: str, payload: str,
                  queue: Queue):
    data = json.loads(payload)
    data['_channel'] = channel
    data['_queued_at'] = time.time()
    queue.put_nowait(data)
    logger.info('Inserted ', data)


async def listen_errors(pool):
    queue = Queue()
    on_event_fn = partial(_on_new_event, queue=queue)

    conn = await pool.acquire()
    listener_conn = await pool.acquire()

    for listener in Listener:
        await listener_conn.add_listener(listener.value, on_event_fn)

    logger.info('Starting Listener')
    try:
        while True:
            item = await queue.get()
            logger.info('New item ', item)
            try:
                channel = Listener(item.pop('_channel'))
            except ValueError:
                logger.warning('Received unimplemented event from channel {channel}'.format(
                    **item
                ))
                continue

            try:
                fn = CHANNELS_MAPPING[channel]
            except KeyError:
                logger.warning(f'[{channel.name:<10}] No function implemented. Ignoring.')
                continue

            try:
                await fn(item=item)
            except Exception as e:
                logger.exception(f"[{channel.name:<10}] Failed to process item: {item}")
                if RELEASE_STAGE != 'production':
                    raise e

    except KeyboardInterrupt:
        logger.info('Stopping listener')
    finally:
        for x in Listener:
            await listener_conn.remove_listener(x.value, on_event_fn)
        await gather(
            pool.release(conn, timeout=1),
            pool.release(listener_conn, timeout=1)
        )
