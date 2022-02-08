import pytest

from .conftest import DATA_PATH, PG_DB
from .utils import trackcalls


@pytest.mark.parametrize('config_file', [
    DATA_PATH / 'config.yml'])
def test_parser_listener(loop, config_file, monkeypatch):
    from run import cli

    @trackcalls
    async def mock_listen_to_file(*args, **kwargs):
        pass

    monkeypatch.setattr('pingou.listener.listener.listen_to_file', mock_listen_to_file)

    cli.run_with_args('listener', '-p', str(config_file), '--db', PG_DB, '--nb-workers', '0')
    assert mock_listen_to_file.call_count == 2


@pytest.mark.parametrize('config_file', [
    DATA_PATH / 'config.yml'])
def test_parser_worker(loop, config_file, monkeypatch):
    @trackcalls
    async def mock_queue_worker(*args, **kwargs):
        pass

    monkeypatch.setattr('pingou.listener.listener.queue_worker', mock_queue_worker)

    from run import cli
    cli.run_with_args('worker', '-p', str(config_file), '-n', '2', '--db', PG_DB)
    assert mock_queue_worker.call_count == 2
