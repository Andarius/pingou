from collections import Counter
from pathlib import Path
import re
import yaml

with open(Path(__file__).parent / '..' / '..' / 'static' / 'regexps.yml', 'r') as f:
    _REGEXPS = yaml.load(f, Loader=yaml.CLoader)

_items_reg = re.compile(r'\{(?P<reg>[A-Z_\d]+)\:(?P<fmt>[a-zA-Z\d_-]+)\}')


def parse_regex(regex: str) -> str:
    matches = _items_reg.findall(regex)

    if not matches:
        raise ValueError('No matches found when parsing the parsing expression')

    counter = Counter([x[1] for x in matches])
    duplicated_keys = [x for x in counter if counter[x] > 1]
    if duplicated_keys:
        duplicated_keys = ', '.join(duplicated_keys)
        raise KeyError(f'Found one or more elements with the same key: {duplicated_keys}')

    for reg_name, fmt_name in matches:
        _reg = _REGEXPS.get(reg_name)
        if not _reg:
            raise KeyError(f'Could not found a matching regex for "{reg_name}"')
        regex = regex.replace('{' + f'{reg_name}:{fmt_name}' + '}', _reg.format(name=fmt_name))

    return regex
