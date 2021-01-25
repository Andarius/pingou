import argparse
import os
import logging
import asyncio
import inspect

from pingou.listener import listener_main
from logs import init_logging
from pingou import __version__

parser = argparse.ArgumentParser('Pingou logs parser')
subparsers = parser.add_subparsers()

parser.add_argument('--pg', default='postgres:postgres@postgres:5432', help='PG host/port')
parser.add_argument('--pg-db', default='postgres', help='PG Database')
parser.add_argument('--log-path', default=os.getenv('LOG_PATH', '/tmp'),
                    help='Logs path')
parser.add_argument('--log-lvl', default=os.getenv('LOG_LEVEL', logging.INFO),
                    help='Log level to user')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='Verbosity (shows or not progress bars)')

# Listener
parser_listener = subparsers.add_parser('listener')
parser_listener.set_defaults(func=listener_main)
parser_listener.add_argument('-c', '--config',
                             type=str,
                             required=True,
                             help='Config file path')

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
