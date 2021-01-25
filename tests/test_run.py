from types import SimpleNamespace
import logging
import pytest
from .conftest import DATA_PATH
from .utils import trackcalls

_DEFAULT_OPTIONS = {
    'log_lvl': logging.WARNING,
    'pg': 'postgres:postgres@localhost:5432',
    'pg_db': 'monitoring',
    'verbose': False,
}


def test_main(loop, tmp_path):
    from run import main
    options = {
        **_DEFAULT_OPTIONS,
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
                              '-c', str(config_file)])
    loop.run_until_complete(args.func(args))
    assert mock_listen_to_file.call_count == 4


def test_parser_version(loop, tmp_path, log_file):
    from run import parser
    args = parser.parse_args(['version'])
    args.func(args)
