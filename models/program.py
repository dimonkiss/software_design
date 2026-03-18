from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import List, Set

from models.flowchart import Flowchart


@dataclass
class TestCase:
    """One (input, expected-output) pair for automated testing."""

    name: str
    input_data: str   # whitespace-separated integers (may be empty)
    expected_output: str  # newline-separated integers
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def get_input_values(self) -> List[int]:
        tokens = self.input_data.split()
        result = []
        for t in tokens:
            try:
                result.append(int(t))
            except ValueError:
                pass
        return result

    def get_expected_lines(self) -> List[str]:
        return [ln.strip() for ln in self.expected_output.splitlines() if ln.strip()]

    # --------------------------------------------------------- serialization
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "input_data": self.input_data,
            "expected_output": self.expected_output,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TestCase":
        tc = cls(
            name=data["name"],
            input_data=data.get("input_data", ""),
            expected_output=data.get("expected_output", ""),
        )
        tc.id = data["id"]
        return tc


@dataclass
class Program:
    """A collection of N flowcharts (threads) plus a test-case suite."""

    name: str
    flowcharts: List[Flowchart] = field(default_factory=list)
    test_cases: List[TestCase] = field(default_factory=list)

    # -------------------------------------------------------- helpers
    def get_all_variables(self) -> List[str]:
        var_set: Set[str] = set()
        for fc in self.flowcharts:
            for v in fc.get_all_variables():
                var_set.add(v)
        return sorted(var_set)

    def validate(self) -> List[str]:
        errors: List[str] = []
        n = len(self.flowcharts)
        if n < 1:
            errors.append("Program must have at least 1 thread.")
        if n > 100:
            errors.append(f"Too many threads ({n}); maximum is 100.")
        for i, fc in enumerate(self.flowcharts, 1):
            for err in fc.validate():
                errors.append(f"Thread {i} ({fc.name}): {err}")
        return errors

    # --------------------------------------------------------- serialization
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "flowcharts": [fc.to_dict() for fc in self.flowcharts],
            "test_cases": [tc.to_dict() for tc in self.test_cases],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Program":
        prog = cls(name=data["name"])
        prog.flowcharts = [Flowchart.from_dict(fd) for fd in data.get("flowcharts", [])]
        prog.test_cases = [TestCase.from_dict(td) for td in data.get("test_cases", [])]
        return prog
