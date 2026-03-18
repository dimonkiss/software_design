"""
Deterministic, step-by-step interpreter for a set of flowcharts (threads).

Each call to :meth:`Interpreter.step` executes exactly **one** block of
exactly **one** thread atomically and returns a new :class:`SimState`.
This design supports:

* Single random-schedule execution (pick a random runnable thread each step).
* Exhaustive enumeration of all interleavings up to *K* total steps by
  trying every runnable thread at each state.

All 32-bit integer semantics are applied: values are masked to
``0 .. 2**32 - 1`` after every assignment.

Design notes
------------
``SimState`` is a *frozen*, hashable value object so that visited-state
deduplication in BFS/DFS is cheap (just add to a ``set``).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, FrozenSet, List, Optional, Tuple

from models.block import BlockType
from models.program import Program

_MASK32 = 0xFFFF_FFFF


# ──────────────────────────────────────────────────────────────── data types

class StepResult(Enum):
    OK      = auto()   # step executed normally
    BLOCKED = auto()   # chosen thread has no runnable operation (e.g. END)
    DONE    = auto()   # all threads have finished


@dataclass(frozen=True)
class SimState:
    """
    Immutable snapshot of the entire concurrent program.

    Fields
    ------
    shared_vars  : frozenset of (name, value) pairs  –  all shared variables
    thread_pcs   : tuple of block-id or None per thread  (None = finished)
    input_index  : how many input tokens have been consumed
    output       : tuple of ints printed so far  (ordered)
    steps        : total number of atomic steps taken so far
    """

    shared_vars: FrozenSet[Tuple[str, int]]
    thread_pcs: Tuple[Optional[str], ...]
    input_index: int
    output: Tuple[int, ...]
    steps: int

    # ---------------------------------------- convenience constructors
    @classmethod
    def initial(cls, program: Program) -> "SimState":
        thread_pcs = []
        for fc in program.flowcharts:
            start = fc.get_start_block()
            thread_pcs.append(start.id if start else None)
        return cls(
            shared_vars=frozenset(),
            thread_pcs=tuple(thread_pcs),
            input_index=0,
            output=(),
            steps=0,
        )

    # ---------------------------------------- query helpers
    @property
    def vars_dict(self) -> Dict[str, int]:
        return dict(self.shared_vars)

    def is_terminal(self) -> bool:
        return all(pc is None for pc in self.thread_pcs)

    def runnable_threads(self) -> List[int]:
        return [i for i, pc in enumerate(self.thread_pcs) if pc is not None]

    def output_as_str(self) -> str:
        return "\n".join(str(v) for v in self.output)


# ─────────────────────────────────────────────────────────────────── engine

class Interpreter:
    """Executes one atomic step for a chosen thread within a given state."""

    def __init__(self, program: Program, input_values: List[int]) -> None:
        self._program = program
        self._input   = input_values

    # ──────────────────────────────────────────────────────────── public API
    def step(self, state: SimState, thread_idx: int) -> Tuple[StepResult, SimState]:
        """
        Execute *one* block of *thread_idx* inside *state*.

        Returns
        -------
        (StepResult.OK,      new_state)   – step succeeded
        (StepResult.BLOCKED, state)       – thread already finished / no block
        (StepResult.DONE,    new_state)   – all threads finished after this step
        """
        pc = state.thread_pcs[thread_idx]
        if pc is None:
            return StepResult.BLOCKED, state

        fc     = self._program.flowcharts[thread_idx]
        block  = fc.blocks.get(pc)
        if block is None:
            return StepResult.BLOCKED, state

        # Work with mutable copies of state components
        svars      = dict(state.shared_vars)
        t_pcs      = list(state.thread_pcs)
        inp_idx    = state.input_index
        out        = list(state.output)
        bt         = block.block_type
        nb         = block.next_blocks

        def _next(idx: int = 0) -> Optional[str]:
            if idx < len(nb) and nb[idx] and nb[idx] in fc.blocks:
                return nb[idx]
            return None

        # ── dispatch ────────────────────────────────────────────
        if bt == BlockType.START:
            t_pcs[thread_idx] = _next()

        elif bt == BlockType.END:
            t_pcs[thread_idx] = None

        elif bt == BlockType.ASSIGN:
            target   = block.content.get("target", "")
            src_type = block.content.get("src_type", "const")
            source   = block.content.get("source", "0")
            if src_type == "var":
                val = svars.get(source, 0)
            else:
                val = int(source)
            svars[target] = val & _MASK32
            t_pcs[thread_idx] = _next()

        elif bt == BlockType.INPUT:
            if inp_idx >= len(self._input):
                return StepResult.BLOCKED, state   # no input available
            var = block.content.get("var", "")
            svars[var] = self._input[inp_idx] & _MASK32
            inp_idx += 1
            t_pcs[thread_idx] = _next()

        elif bt == BlockType.PRINT:
            var = block.content.get("var", "")
            out.append(svars.get(var, 0))
            t_pcs[thread_idx] = _next()

        elif bt == BlockType.CONDITION:
            var = block.content.get("var", "")
            op  = block.content.get("op", "==")
            val = int(block.content.get("value", "0"))
            lhs = svars.get(var, 0)
            cond = (lhs == val) if op == "==" else (lhs < val)
            t_pcs[thread_idx] = _next(0) if cond else _next(1)

        new_state = SimState(
            shared_vars=frozenset(svars.items()),
            thread_pcs=tuple(t_pcs),
            input_index=inp_idx,
            output=tuple(out),
            steps=state.steps + 1,
        )

        result = StepResult.DONE if new_state.is_terminal() else StepResult.OK
        return result, new_state
