from dataclasses import dataclass
from typing import Literal, Optional
import re

REQUEST_METHOD = Literal['GET', 'POST', 'PUT', 'HEAD', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH']


@dataclass
class NginxLog:
    ip_address: str
    user: str
    timestamp: int
    request_method: REQUEST_METHOD
    http_version: float
    status: int
    body_bytes_sent: int
    referer: str
    user_agent: str
    cookie: str = None
    request_time: int = None
    upstream_connect_time: int = None
    upstream_header_time: int = None
    upstream_response_time: int = None


def parse_line(line: str,
               reg: re.Pattern) -> Optional[dict]:
    match = reg.search(line)
    return match.groupdict() if match else None
