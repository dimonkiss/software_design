from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class Source:
    """Джерело значення для ASSIGN"""
    type: Literal["const", "var"]
    value: Any

    def __post_init__(self) -> None:
        if self.type == "const" and not isinstance(self.value, int):
            raise ValueError("const source must be int")
        if self.type == "var" and not isinstance(self.value, str):
            raise ValueError("var source must be str (variable name)")