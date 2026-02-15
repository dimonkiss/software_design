from dataclasses import dataclass, field
from typing import Dict


@dataclass
class SharedState:
    """Спільна пам'ять (змінні)"""
    variables: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in self.variables.items():
            if not isinstance(value, int) or not (0 <= value <= 2**32 - 1):
                raise ValueError(f"Variable {name} must be 32-bit unsigned integer")

    def get(self, var: str) -> int:
        return self.variables.get(var, 0)

    def set(self, var: str, value: int) -> None:
        """32-bit wrap-around (unsigned)"""
        self.variables[var] = value & 0xFFFFFFFF

    def to_dict(self) -> dict:
        return self.variables.copy()