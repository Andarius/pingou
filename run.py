import argparse
import os
import logging
import asyncio
import inspect
import sys
from pingou.listener import listener_main, worker_main
from logs import init_logging
from pingou import __version__

parser = argparse.ArgumentParser('Pingou logs parser')
subparsers = parser.add_subparsers()

parser.add_argument('--pg', default='postgres:postgres@postgres:5432', help='PG host/port')
parser.add_argument('--pg-db', default='monitoring', help='PG Database')
parser.add_argument('--log-path', default=os.getenv('LOG_PATH', '/tmp'),
                    help='Logs path')
parser.add_argument('--log-lvl', default=os.getenv('LOG_LEVEL', logging.INFO),
                    help='Log level to user')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='Verbosity (shows or not progress bars)')

# Listener
parser_listener = subparsers.add_parser('listener')
parser_listener.set_defaults(func=listener_main)
parser_listener.add_argument('-p', '--config-path',
                             type=str,
                             help='Config file path')
parser_listener.add_argument('config-file',
                             type=argparse.FileType('r'),
                             nargs='?',
                             default=sys.stdin,
                             help='Config file')
# Worker
parser_worker = subparsers.add_parser('worker')
parser_worker.set_defaults(func=worker_main)
parser_worker.add_argument('-n', '--nb-workers',
                           default=1,
                           type=int,
                           help='Number of workers')
parser_worker.add_argument('-p', '--config-path',
                           type=str,
                           help='Config file path')
parser_worker.add_argument('config-file',
                           type=argparse.FileType('r'),
                           nargs='?',
                           default=sys.stdin,
                           help='Config file')

# Version
parser_version = subparsers.add_parser('version')
parser_version.set_defaults(func=lambda _: logging.info(f'Current version: {__version__}'))


def main(options):
    init_logging(options.log_lvl, options.log_path, __version__)

    if not hasattr(options, 'func'):
        logging.info('Nothing to do')
        return
    try:
        if inspect.iscoroutinefunction(options.func):
            asyncio.run(options.func(options))
        else:
            options.func(options)
    except KeyboardInterrupt:
        logging.info('Stopping')


if __name__ == '__main__':
    options = parser.parse_args()
    main(options)
