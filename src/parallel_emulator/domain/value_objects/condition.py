from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Condition:
    """Умова для Decision-блоку"""
    var: str
    op: Literal["==", "<"]
    const: int

    def __post_init__(self) -> None:
        if self.op not in ("==", "<"):
            raise ValueError("Operator must be '==' or '<'")
        if not isinstance(self.const, int) or not (0 <= self.const <= 2**31 - 1):
            raise ValueError("Constant must be in range 0..2^31-1")