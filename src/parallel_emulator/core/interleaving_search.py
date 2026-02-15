import threading
from collections import deque
from typing import Dict, List, Optional

from src.parallel_emulator.core.emulator import BlockInterpreter
from src.parallel_emulator.core.state import MutableState, GlobalState
from src.parallel_emulator.domain.entities.project import Project
from src.parallel_emulator.domain.enums.block_type import BlockType


class InterleavingSearch:
    """Пошук по всіх можливих інтерлівінгах (BFS + visited + stop)"""

    def __init__(self, project: Project, input_data: List[int], expected_output: List[int]) -> None:
        self.project = project
        self.expected = expected_output
        self.interpreter = BlockInterpreter(project)

        # початковий стан
        pcs: Dict[int, Optional[int]] = {}
        for thread in project.threads:
            pcs[thread.id] = thread.start_block_id

        initial_mutable = MutableState(
            pcs=pcs,
            variables={v: 0 for v in project.variables},
            input_remaining=input_data.copy(),
            output=[],
            depth=0,
        )
        self.initial_state = initial_mutable.to_frozen()

        self.stop_event = threading.Event()
        self._depth_counts: Dict[int, int] = {}   # для Checked_Paths_K
        self._found_counterexample = False
        self._counterexample_state: Optional[GlobalState] = None

    def get_active_threads(self, state: GlobalState) -> List[int]:
        active: List[int] = []
        mutable = state.to_mutable()  # не мутаємо, тільки читаємо
        for tid, pc in mutable.pcs.items():
            if pc is None:
                continue
            thread = next((t for t in self.project.threads if t.id == tid), None)
            if not thread:
                continue
            block = thread.blocks.get(pc)
            if not block:
                continue
            if block.type == BlockType.INPUT and not mutable.input_remaining:
                continue  # заблоковано
            active.append(tid)
        return active

    def is_complete(self, state: GlobalState) -> bool:
        """Всі потоки завершилися"""
        return all(pc is None for _, pc in state.pcs)

    def check_output_prefix(self, state: GlobalState) -> bool:
        """Раннє відсікання поганих гілок"""
        out_len = len(state.output)
        if out_len > len(self.expected):
            return False
        return state.output == self.expected[:out_len]

    def run(self) -> bool:
        """Повертає True, якщо всі шляхи коректні (або зупинено)"""
        queue = deque([self.initial_state])
        visited = {hash(self.initial_state)}
        self._depth_counts = {0: 1}

        while queue and not self.stop_event.is_set():
            state = queue.popleft()

            if state.depth not in self._depth_counts:
                self._depth_counts[state.depth] = 0
            self._depth_counts[state.depth] += 1

            if not self.check_output_prefix(state):
                self._found_counterexample = True
                self._counterexample_state = state
                return False

            if self.is_complete(state):
                if tuple(state.output) != tuple(self.expected):
                    self._found_counterexample = True
                    self._counterexample_state = state
                    return False
                continue

            active = self.get_active_threads(state)
            if not active:
                continue

            mutable = state.to_mutable()
            for tid in active:
                # копіюємо mutable для кожної гілки
                branch = MutableState(
                    pcs=mutable.pcs.copy(),
                    variables=mutable.variables.copy(),
                    input_remaining=mutable.input_remaining.copy(),
                    output=mutable.output.copy(),
                    depth=mutable.depth,
                )
                self.interpreter.execute_step(branch, tid)
                new_frozen = branch.to_frozen()

                h = hash(new_frozen)
                if h not in visited:
                    visited.add(h)
                    queue.append(new_frozen)

        return not self._found_counterexample

    # === Метрика K (викликається після stop) =================================
    def get_checked_paths_up_to_k(self, k: int) -> int:
        """Кількість перевірених шляхів довжиною ≤ K"""
        return sum(self._depth_counts.get(d, 0) for d in range(k + 1))

    def calculate_total_paths_up_to_k(self, k: int) -> int:
        """Повна кількість можливих шляхів ≤ K (окремий BFS без prune)"""
        if k < 0:
            return 0

        queue = deque([self.initial_state])
        visited = {hash(self.initial_state)}
        total = 0
        depth_limit = k

        while queue:
            state = queue.popleft()
            if state.depth > depth_limit:
                continue
            total += 1

            if state.depth == depth_limit:
                continue

            active = self.get_active_threads(state)
            mutable = state.to_mutable()
            for tid in active:
                branch = MutableState(
                    pcs=mutable.pcs.copy(),
                    variables=mutable.variables.copy(),
                    input_remaining=mutable.input_remaining.copy(),
                    output=mutable.output.copy(),
                    depth=mutable.depth,
                )
                self.interpreter.execute_step(branch, tid)
                new_frozen = branch.to_frozen()

                h = hash(new_frozen)
                if h not in visited:
                    visited.add(h)
                    queue.append(new_frozen)

        return total

    def get_coverage_percent(self, k: int) -> float:
        """(Checked / Total) * 100%"""
        checked = self.get_checked_paths_up_to_k(k)
        total = self.calculate_total_paths_up_to_k(k)
        if total == 0:
            return 100.0
        return (checked / total) * 100