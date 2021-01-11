import pytest
import re
from pathlib import Path
import json

with open(Path(__file__).parent / 'files' / 'tests.json') as f:
    PARSE_TEST = json.load(f)


@pytest.mark.parametrize('item', PARSE_TEST['parse_nginx_logs'])
def test_parse_nginx_line(item):
    from pingou.parser.nginx import parse_line
    from pingou.parser.regexps import parse_regex
    line, reg, expected = item['line'], item['reg'], item['expected']
    log = parse_line(line, re.compile(parse_regex(reg)))
    assert log == expected
