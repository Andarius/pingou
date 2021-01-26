from types import SimpleNamespace
import pytest
from .conftest import DATA_PATH, DEFAULT_OPTIONS
from .utils import trackcalls


def test_main(loop, tmp_path):
    from run import main
    options = {
        **DEFAULT_OPTIONS,
        'log_path': tmp_path
    }
    main(SimpleNamespace(**options))


@pytest.mark.parametrize('config_file', [
    DATA_PATH / 'config.yml'])
def test_parser_listener(loop, config_file, monkeypatch):
    @trackcalls
    async def mock_listen_to_file(*args, **kwargs):
        pass

    monkeypatch.setattr('pingou.listener.listener.listen_to_file', mock_listen_to_file)

    from run import parser
    args = parser.parse_args(['--pg', 'postgres:postgres@localhost:5432', 'listener',
                              '-p', str(config_file)])
    loop.run_until_complete(args.func(args))
    assert mock_listen_to_file.call_count == 2


@pytest.mark.parametrize('config_file', [
    DATA_PATH / 'config.yml'])
def test_parser_worker(loop, config_file, monkeypatch):
    @trackcalls
    async def mock_queue_worker(*args, **kwargs):
        pass

    monkeypatch.setattr('pingou.listener.listener.queue_worker', mock_queue_worker)

    from run import parser
    args = parser.parse_args(['--pg', 'postgres:postgres@localhost:5432', 'worker',
                              '-p', str(config_file),
                              '-n', '2'])
    loop.run_until_complete(args.func(args))
    assert mock_queue_worker.call_count == 2


def test_parser_version(loop, tmp_path, log_file):
    from run import parser
    args = parser.parse_args(['version'])
    args.func(args)
