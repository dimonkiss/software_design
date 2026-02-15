from dataclasses import dataclass
from typing import Optional

from src.parallel_emulator.domain.enums.block_type import BlockType
from src.parallel_emulator.domain.value_objects.condition import Condition
from src.parallel_emulator.domain.value_objects.source import Source


@dataclass(frozen=True)
class Block:
    """Блок блок-схеми (immutable)"""
    id: int
    type: BlockType
    x: float = 100.0
    y: float = 100.0

    # ASSIGN
    target: Optional[str] = None
    source: Optional[Source] = None

    # INPUT / PRINT
    io_var: Optional[str] = None

    # DECISION
    condition: Optional[Condition] = None
    true_next: Optional[int] = None
    false_next: Optional[int] = None

    # звичайний next (для START, ASSIGN, INPUT, PRINT, END)
    next: Optional[int] = None

    def __post_init__(self) -> None:
        """Валідація залежно від типу блоку"""
        if self.type == BlockType.START and self.next is None:
            raise ValueError("START block must have 'next'")
        if self.type == BlockType.END and self.next is not None:
            raise ValueError("END block cannot have 'next'")

        if self.type == BlockType.ASSIGN:
            if not self.target or not self.source:
                raise ValueError("ASSIGN requires target and source")
        elif self.type in (BlockType.INPUT, BlockType.PRINT):
            if not self.io_var:
                raise ValueError("INPUT/PRINT requires io_var")
        elif self.type == BlockType.DECISION:
            if not self.condition or self.true_next is None or self.false_next is None:
                raise ValueError("DECISION requires condition, true_next and false_next")

    def to_dict(self) -> dict:
        """Для серіалізації (використовується тільки в infrastructure)"""
        d: dict = {"id": self.id, "type": self.type.value, "x": self.x, "y": self.y}
        if self.next is not None:
            d["next"] = self.next
        if self.target is not None:
            d["target"] = self.target
        if self.source is not None:
            d["source"] = {"type": self.source.type, "value": self.source.value}
        if self.io_var is not None:
            d["target"] = self.io_var  # сумісність з твоїм початковим JSON
        if self.condition is not None:
            d["condition"] = {"var": self.condition.var, "op": self.condition.op, "const": self.condition.const}
        if self.true_next is not None:
            d["true_next"] = self.true_next
        if self.false_next is not None:
            d["false_next"] = self.false_next
        return d