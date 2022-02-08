import logging
from pathlib import Path

from piou import Cli, Option, Derived

from pingou.env import (
    NB_WORKERS, PG_TABLE,
    PG_DB, PG_HOST, PG_USER, PG_PORT, PG_PASSWORD
)
from pingou.logs import init_logging

cli = Cli('Pingou logs parser')


@cli.processor()
def init(
        verbose: bool = Option(False, '-v', '--verbose'),
        verbose2: bool = Option(False, '-vv', '--verbose2'),
):
    init_logging(
        logging.DEBUG if verbose2 else
        logging.INFO if verbose else
        logging.WARNING
    )


def get_pg_url(
        pg_user: str = Option(PG_USER, '--user'),
        pg_pwd: str = Option(PG_PASSWORD, '--pwd'),
        pg_host: str = Option(PG_HOST, '--host'),
        pg_port: int = Option(PG_PORT, '--port'),
        pg_db: str = Option(PG_DB, '--db')

):
    return f'postgres://{pg_user}:{pg_pwd}@{pg_host}:{pg_port}/{pg_db}'


ConfigPath = Option(Path('/static/config.yml'), '-p',
                    help='Config path')
NbWorkers = Option(NB_WORKERS, '-n', '--nb-workers',
                   help='Number of workers to run')
Table = Option(PG_TABLE, '--table', help='Table to write the logs to')


@cli.command('listener')
async def listener_main(
        config_path: Path = ConfigPath,
        nb_workers: int = NbWorkers,
        pg_url: str = Derived(get_pg_url),
        table: str = Table
):
    from pingou import run_listener

    await run_listener(config_path=config_path,
                       nb_workers=nb_workers,
                       pg_url=pg_url,
                       table=table)


@cli.command('worker')
async def worker_main(
        config_path: Path = ConfigPath,
        nb_workers: int = NbWorkers,
        table: str = Table,
        pg_url: str = Derived(get_pg_url),
):
    from pingou import run_worker
    await run_worker(config_path=config_path,
                     nb_workers=nb_workers,
                     pg_url=pg_url,
                     table=table)


def run():
    cli.run()


if __name__ == '__main__':
    run()
