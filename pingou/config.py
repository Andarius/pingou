from dataclasses import dataclass, InitVar, field
import yaml
from typing import Union, List
from collections import namedtuple
from itertools import chain
import re
from .parser import parse_regex

Sources = namedtuple('Sources', ['error', 'access'])


@dataclass
class PipelineItem:
    parse_expression: InitVar[str]
    regex: re.Pattern = field(init=False)

    def __post_init__(self, parse_expression: str):
        self.regex = re.compile(parse_regex(parse_expression))


@dataclass
class Config:
    sources: Union[dict, Sources]

    access_pipeline: List[PipelineItem]
    error_pipeline: List[PipelineItem]

    @property
    def pipelines(self):
        return chain(self.access_pipeline, self.error_pipeline)

    @property
    def paths(self):
        return chain(self.sources.error, self.sources.access)

    @classmethod
    def load(cls, file: str):
        with open(file, 'r') as f:
            _file = yaml.load(f, Loader=yaml.CLoader)

        pipeline = _file.pop('pipeline', {})
        access_pipeline = [PipelineItem(parse_expression=x) for x in pipeline.get('access', [])]
        error_pipeline = [PipelineItem(parse_expression=x) for x in pipeline.get('error', [])]

        return cls(
            **_file,
            access_pipeline=access_pipeline,
            error_pipeline=error_pipeline
        )

    def __post_init__(self):
        self.sources = (self.sources if isinstance(self.sources, Sources) else Sources(**self.sources))
