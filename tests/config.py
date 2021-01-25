import pytest
from pathlib import Path


@pytest.mark.parametrize('path', [
    Path(__file__).parent / 'files' / 'config.yml'
])
def test_load_config(path):
    from pingou.config import Config

    conf = Config.load(path)
    assert conf