from dataclasses import dataclass, field
from typing import List, Optional, Literal

MAX_VAL = 2 ** 31 - 1
MIN_VAL = 0


@dataclass
class Block:
    id: int
    type: Literal['START', 'END', 'ASSIGN', 'INPUT', 'PRINT', 'DECISION']
    pos_x: float = 0.0
    pos_y: float = 0.0

    # Параметри логіки
    target_var: Optional[str] = None
    src_var: Optional[str] = None
    value: Optional[int] = None
    operator: Optional[str] = None

    # Зв'язки (ID наступних блоків)
    next_id: Optional[int] = None
    true_next_id: Optional[int] = None
    false_next_id: Optional[int] = None

    def validate(self):
        """Перевірка обмежень ТЗ для констант."""
        if self.value is not None:
            if not (MIN_VAL <= self.value <= MAX_VAL):
                raise ValueError(f"Value {self.value} out of range [0, 2^31-1]")


@dataclass
class ThreadModel:
    id: int
    name: str
    blocks: List[Block] = field(default_factory=list)

    def get_block_by_id(self, block_id: int) -> Optional[Block]:
        return next((b for b in self.blocks if b.id == block_id), None)


@dataclass
class Project:
    name: str = "New Project"
    threads: List[ThreadModel] = field(default_factory=list)
    shared_variables: List[str] = field(default_factory=list)  # Реєстр var0...var99