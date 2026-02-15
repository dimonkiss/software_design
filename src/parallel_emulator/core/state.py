from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class GlobalState:
    """Immutable глобальний стан виконання (для хешування та visited)"""
    # (thread_id, pc) — відсортовані для детермінованого хешу
    pcs: Tuple[Tuple[int, Optional[int]], ...]
    variables: Tuple[Tuple[str, int], ...]          # (var_name, value) sorted
    input_remaining: Tuple[int, ...]
    output: Tuple[int, ...]
    depth: int = 0

    def to_mutable(self) -> "MutableState":
        return MutableState(
            pcs=dict(self.pcs),
            variables=dict(self.variables),
            input_remaining=list(self.input_remaining),
            output=list(self.output),
            depth=self.depth,
        )


@dataclass
class MutableState:
    """Мутабельна версія для зручного оновлення в execute_step"""
    pcs: Dict[int, Optional[int]]
    variables: Dict[str, int]
    input_remaining: List[int]
    output: List[int]
    depth: int

    def to_frozen(self) -> GlobalState:
        pcs_tuple = tuple(sorted(self.pcs.items()))
        vars_tuple = tuple(sorted(self.variables.items()))
        return GlobalState(
            pcs=pcs_tuple,
            variables=vars_tuple,
            input_remaining=tuple(self.input_remaining),
            output=tuple(self.output),
            depth=self.depth,
        )