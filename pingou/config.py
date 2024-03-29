from dataclasses import dataclass, InitVar, field
import yaml
from typing import Union, List
from collections import namedtuple
import re
from .parser import parse_regex
from pathlib import Path

Sources = namedtuple('Sources', ['error', 'access'])


@dataclass
class PipelineItem:
    parse_expression: InitVar[str]
    regex: re.Pattern = field(init=False)

    def __post_init__(self, parse_expression: str):
        self.regex = re.compile(parse_regex(parse_expression))


@dataclass
class Config:
    access_pipelines: list[PipelineItem]
    error_pipelines: list[PipelineItem]

    sources: Sources
    _file_path: Path | None = None

    @property
    def access_files(self) -> List[Path]:
        if self._file_path:
            return [self._file_path / x
                    if not x.startswith('/') else Path(x)
                    for x in self.sources.access]
        else:
            return self.sources.access

    @property
    def error_files(self) -> List[Path]:
        if self._file_path:
            return [self._file_path / x
                    if not x.startswith('/') else Path(x)
                    for x in self.sources.error]
        else:
            return self.sources.error

    @classmethod
    def load(cls, file: Path):
        with file.open('r') as f:
            _file = yaml.load(f, Loader=yaml.CLoader)

        pipeline = _file.pop('pipeline', {})
        access_pipelines = [PipelineItem(parse_expression=x) for x in pipeline.get('access', [])]
        error_pipelines = [PipelineItem(parse_expression=x) for x in pipeline.get('error', [])]

        _cls = cls(
            **_file,
            access_pipelines=access_pipelines,
            error_pipelines=error_pipelines,
            _file_path=file,
        )

        return _cls

    def __post_init__(self):
        self._file_path = Path(self._file_path).parent if self._file_path else None
        self.sources = (self.sources if isinstance(self.sources, Sources) else Sources(**self.sources))
