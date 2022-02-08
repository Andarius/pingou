import pytest
from pathlib import Path


@pytest.mark.parametrize('path', [
    Path(__file__).parent / 'files' / 'config.yml'
])
def test_load_config(path):
    from pingou.config import Config

    conf = Config.load(path)
    assert conf
    assert conf.access_files
    for _file in conf.access_files:
        assert 'tests/files/../nginx_logs/access.log' in str(_file)

    assert conf.error_files
    for _file in conf.error_files:
        assert 'tests/files/../nginx_logs/error.log' in str(_file)
