from __future__ import annotations

import json
from pathlib import Path

from models.program import Program


def save_program(program: Program, path: str | Path) -> None:
    """Serialise the program to a pretty-printed JSON file."""
    data = program.to_dict()
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_program(path: str | Path) -> Program:
    """Load a program from a JSON file previously saved with :func:`save_program`."""
    raw = Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    return Program.from_dict(data)
