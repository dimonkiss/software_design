"""
Test runner with two operating modes.

Single-run mode
---------------
Execute one interleaving chosen uniformly at random; return pass / fail.

Enumeration mode
----------------
BFS over *all* interleavings whose length is ≤ ``max_steps`` (K parameter).
Progress is reported through a callback so the GUI can update live.
Supports cooperative cancellation via a ``threading.Event``.

Non-determinism reporting
-------------------------
If multiple distinct outputs are reachable the program is non-deterministic.
The caller receives:

* ``total_executions``   – distinct terminal states found (≤ K steps)
* ``verified``           – how many of those were *already* verified by previous
  single-run calls (useful for the "% verified" display)
* ``passed``             – terminal states whose output matches expected
* ``is_nondeterministic`` – True when more than one distinct output exists
"""

from __future__ import annotations

import random
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, List, Optional, Set, Tuple

from executor.interpreter import Interpreter, SimState, StepResult
from models.program import Program, TestCase


@dataclass
class SingleRunResult:
    passed: bool
    actual_output: str
    steps_taken: int


@dataclass
class EnumProgress:
    """Incremental update sent to the GUI callback during BFS enumeration."""
    states_explored: int
    terminal_found: int
    passed: int
    total_outputs: int          # distinct output sequences found so far
    is_nondeterministic: bool
    percent_verified: float     # of *all* terminal states (found so far)
    finished: bool = False      # True on the final callback


@dataclass
class EnumResult:
    total_terminal: int
    passed: int
    is_nondeterministic: bool
    distinct_outputs: List[str]
    percent_verified: float
    interrupted: bool


class TestRunner:
    """
    High-level entry point for both single-run and exhaustive enumeration.

    One ``TestRunner`` instance is meant to be re-used across test cases.
    It accumulates the set of *verified* terminal states across calls so that
    the "% verified" counter is meaningful when the user re-runs tests.
    """

    def __init__(self, program: Program) -> None:
        self._program = program
        # Per-test-case tracking of verified terminal output hashes
        self._verified: Dict[str, Set[Tuple[int, ...]]] = {}

    # ─────────────────────────────────────────────────── single random run
    def run_single(self, test_case: TestCase) -> SingleRunResult:
        """Run one random interleaving and return the result."""
        interp = Interpreter(self._program, test_case.get_input_values())
        state  = SimState.initial(self._program)

        while not state.is_terminal():
            runnable = state.runnable_threads()
            if not runnable:
                break   # deadlock
            chosen = random.choice(runnable)
            result, state = interp.step(state, chosen)
            if result == StepResult.BLOCKED:
                # Try remaining threads in random order
                runnable.remove(chosen)
                random.shuffle(runnable)
                advanced = False
                for t in runnable:
                    r2, s2 = interp.step(state, t)
                    if r2 != StepResult.BLOCKED:
                        state = s2
                        advanced = True
                        break
                if not advanced:
                    break  # full deadlock

        actual = state.output_as_str()
        expected_lines = test_case.get_expected_lines()
        actual_lines   = [ln.strip() for ln in actual.splitlines() if ln.strip()]
        passed = (actual_lines == expected_lines)

        # Mark this output as verified
        key = test_case.id
        self._verified.setdefault(key, set()).add(state.output)

        return SingleRunResult(
            passed=passed,
            actual_output=actual,
            steps_taken=state.steps,
        )

    # ──────────────────────────────────────────── exhaustive BFS enumeration
    def enumerate(
        self,
        test_case: TestCase,
        max_steps: int,
        progress_callback: Callable[[EnumProgress], None],
        stop_event: threading.Event,
    ) -> EnumResult:
        """
        BFS over all interleavings with total steps ≤ ``max_steps``.

        *progress_callback* is called regularly from the worker thread –
        the caller must marshal any GUI updates to the main thread itself
        (e.g. via ``widget.after_idle``).

        ``stop_event.set()`` triggers early termination.
        """
        interp = Interpreter(self._program, test_case.get_input_values())
        expected_lines = test_case.get_expected_lines()
        key            = test_case.id
        verified_set   = self._verified.setdefault(key, set())

        initial  = SimState.initial(self._program)
        queue: deque[SimState]   = deque([initial])
        visited: Set[SimState]   = {initial}

        terminal_outputs: Dict[Tuple[int, ...], bool] = {}  # output → passed?
        states_explored = 0
        REPORT_INTERVAL = 200   # callback frequency

        while queue and not stop_event.is_set():
            state = queue.popleft()
            states_explored += 1

            if state.is_terminal():
                if state.output not in terminal_outputs:
                    lines   = [str(v) for v in state.output]
                    passed  = (lines == expected_lines)
                    terminal_outputs[state.output] = passed
                    verified_set.add(state.output)

                if states_explored % REPORT_INTERVAL == 0:
                    progress_callback(self._make_progress(
                        states_explored, terminal_outputs, verified_set, finished=False
                    ))
                continue

            if state.steps >= max_steps:
                continue  # do not expand further

            for t in state.runnable_threads():
                result, new_state = interp.step(state, t)
                if result != StepResult.BLOCKED and new_state not in visited:
                    visited.add(new_state)
                    queue.append(new_state)

            if states_explored % REPORT_INTERVAL == 0:
                progress_callback(self._make_progress(
                    states_explored, terminal_outputs, verified_set, finished=False
                ))

        final_progress = self._make_progress(
            states_explored, terminal_outputs, verified_set, finished=True
        )
        progress_callback(final_progress)

        distinct_outputs = ["\n".join(str(v) for v in out) for out in terminal_outputs]
        total  = len(terminal_outputs)
        passed = sum(1 for p in terminal_outputs.values() if p)

        return EnumResult(
            total_terminal=total,
            passed=passed,
            is_nondeterministic=len(terminal_outputs) > 1,
            distinct_outputs=distinct_outputs,
            percent_verified=final_progress.percent_verified,
            interrupted=stop_event.is_set(),
        )

    # ──────────────────────────────────────────────────────── internal helpers
    def _make_progress(
        self,
        explored: int,
        terminal_outputs: Dict[Tuple[int, ...], bool],
        verified_set: Set[Tuple[int, ...]],
        *,
        finished: bool,
    ) -> EnumProgress:
        total   = len(terminal_outputs)
        passed  = sum(1 for p in terminal_outputs.values() if p)
        ver_cnt = sum(1 for out in terminal_outputs if out in verified_set)
        pct     = (ver_cnt / total * 100.0) if total else 0.0
        return EnumProgress(
            states_explored=explored,
            terminal_found=total,
            passed=passed,
            total_outputs=total,
            is_nondeterministic=(total > 1),
            percent_verified=pct,
            finished=finished,
        )

    def reset_verified(self, test_case_id: str) -> None:
        """Clear the verification history for a specific test case."""
        self._verified.pop(test_case_id, None)
