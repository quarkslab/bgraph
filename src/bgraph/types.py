import enum
import pathlib
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    Final,
    Generator,
    Iterable,
    List,
    Literal,
    Optional,
    overload,
    Set,
    Tuple,
    TypedDict,
    Union,
)


class OutChoice(str, enum.Enum):
    """Output format choices"""

    TXT: str = "text"
    JSON: str = "json"
    DOT: str = "dot"


class QueryType(str, enum.Enum):
    """Possible query types"""

    SOURCE: str = "source"
    TARGET: str = "target"
    DEPENDENCY: str = "dependency"


NodeType = str
"""Type of a node."""

ResultDict = TypedDict(
    "ResultDict", {"sources": List[str], "target": List[Tuple[str, str]]}, total=False
)
"""Type of a result dict (used in formatter)."""


# TODO(dm): Wait until TypedDict accept Final as keys to rewrite this
class Section(TypedDict, total=False):
    soong_parser_section_type: str
    soong_parser_section_project: str
    soong_parser_project_path: pathlib.Path
    soong_parser_soong_path: pathlib.Path

    # Some value names from Soong
    defaults: Union[str, List[str]]
