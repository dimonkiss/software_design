"""
Translates a Program (set of flowcharts) into multi-threaded Python source code.

Generated code structure
------------------------
* All shared variables are declared at module level (initial value = 0).
* A single ``threading.Lock`` serialises every shared-variable access,
  making each block operation atomic in the generated program.
* A separate lock guards stdout so PRINT output is not interleaved.
* Input is read from a list pre-filled from stdin; access is protected by
  another lock so multiple threads cannot consume the same token.
* Each flowchart becomes a Python function executed by a daemon-free Thread.
* ``main()`` is the entry point: it spawns all threads, then joins them.

Implementation note
-------------------
Because flowchart graphs can contain cycles, we cannot translate them into
straight-line Python.  We use a *state-machine* loop inside each thread
function: ``_pc`` holds the current block id; the loop dispatches on it and
updates ``_pc`` after every atomic step.
"""

from __future__ import annotations

from typing import List

from models.block import Block, BlockType
from models.flowchart import Flowchart
from models.program import Program

# Indentation helpers
_I1 = " " * 4
_I2 = " " * 8
_I3 = " " * 12
_I4 = " " * 16


class PythonTranslator:
    """Translates a :class:`~models.program.Program` to Python source code."""

    def translate(self, program: Program) -> str:
        lines: List[str] = []

        # ── header ──────────────────────────────────────────────────────────
        lines += [
            "# Auto-generated multi-threaded program",
            "# DO NOT EDIT by hand – regenerate from the flowchart editor",
            "",
            "import threading",
            "import sys",
            "",
        ]

        # ── shared variables ─────────────────────────────────────────────────
        all_vars = program.get_all_variables()
        lines.append("# ── Shared variables (32-bit integer semantics) ──")
        if all_vars:
            for v in all_vars:
                lines.append(f"{v}: int = 0")
        else:
            lines.append("# (no shared variables)")
        lines.append("")

        # ── infrastructure ───────────────────────────────────────────────────
        lines += [
            "# ── Synchronisation primitives ──",
            "_shared_lock = threading.Lock()  # protects all shared variables",
            "_output_lock = threading.Lock()  # serialises stdout",
            "_input_lock  = threading.Lock()  # one thread reads stdin at a time",
            "",
        ]
        # _consume_input written as a plain indented string to avoid any
        # f-string indentation arithmetic mistakes.
        lines.append(
            "def _consume_input() -> int:\n"
            '    """Read one integer from stdin; shows ">>> " prompt each attempt."""\n'
            "    with _input_lock:\n"
            "        while True:\n"
            '            sys.stderr.write(">>> ")\n'
            "            sys.stderr.flush()\n"
            "            raw = sys.stdin.readline()\n"
            "            if not raw:\n"
            "                raise EOFError('stdin closed')\n"
            "            stripped = raw.strip()\n"
            "            if not stripped:\n"
            "                continue  # blank Enter – ask again silently\n"
            "            try:\n"
            "                return int(stripped) & 0xFFFF_FFFF\n"
            "            except ValueError:\n"
            "                sys.stderr.write(\n"
            "                    f'Expected integer, got {stripped!r}\\n')\n"
            "                sys.stderr.flush()\n"
        )
        lines.append("")

        # ── thread functions ─────────────────────────────────────────────────
        for idx, fc in enumerate(program.flowcharts):
            lines += self._translate_flowchart(fc, idx, all_vars)
            lines.append("")

        # ── main ─────────────────────────────────────────────────────────────
        lines += self._build_main(len(program.flowcharts), all_vars)

        return "\n".join(lines)

    # ──────────────────────────────────────────── flowchart → thread function
    def _translate_flowchart(
        self, fc: Flowchart, index: int, all_vars: List[str]
    ) -> List[str]:
        lines: List[str] = []
        func_name = f"thread_{index}"

        lines.append(f"# ── Thread {index}: {fc.name} ──")
        lines.append(f"def {func_name}() -> None:")

        # global declaration only for variables actually used in this flowchart
        local_vars = fc.get_all_variables()
        global_vars = sorted(set(all_vars) | set(local_vars))
        if global_vars:
            lines.append(f"{_I1}global {', '.join(global_vars)}")
        lines.append("")

        start = fc.get_start_block()
        if start is None:
            lines.append(f"{_I1}pass  # no START block")
            lines.append("")
            return lines

        lines.append(f"{_I1}_pc: str | None = {start.id!r}")
        lines.append(f"{_I1}while _pc is not None:")

        first_branch = True
        for block in fc.blocks.values():
            kw = "if" if first_branch else "elif"
            first_branch = False
            lines.append(f"{_I2}{kw} _pc == {block.id!r}:  # {block.get_label()}")
            for stmt in self._translate_block(block, all_vars):
                lines.append(f"{_I3}{stmt}")

        if first_branch:
            # No blocks at all
            lines.append(f"{_I2}pass")

        lines.append("")
        return lines

    # ──────────────────────────────────────────────────── single block → stmts
    def _translate_block(self, block: Block, all_vars: List[str]) -> List[str]:
        bt = block.block_type
        nb = block.next_blocks

        def next_pc(idx: int = 0) -> str:
            if idx < len(nb) and nb[idx]:
                return repr(nb[idx])
            return "None"

        lines: List[str] = []

        if bt == BlockType.START:
            lines.append(f"_pc = {next_pc()}")

        elif bt == BlockType.END:
            lines.append("_pc = None")

        elif bt == BlockType.ASSIGN:
            target = block.content.get("target", "_x")
            src_type = block.content.get("src_type", "const")
            source = block.content.get("source", "0")
            lines.append("with _shared_lock:")
            if src_type == "var":
                lines.append(f"    {target} = {source}")
            else:
                # Clamp to 32-bit unsigned range
                lines.append(f"    {target} = {int(source)} & 0xFFFF_FFFF")
            lines.append(f"_pc = {next_pc()}")

        elif bt == BlockType.INPUT:
            var = block.content.get("var", "_x")
            lines.append("with _shared_lock:")
            lines.append(f"    {var} = _consume_input()")
            lines.append(f"_pc = {next_pc()}")

        elif bt == BlockType.PRINT:
            var = block.content.get("var", "_x")
            lines.append("with _output_lock:")
            lines.append(f"    print({var}, flush=True)")
            lines.append(f"_pc = {next_pc()}")

        elif bt == BlockType.CONDITION:
            var = block.content.get("var", "_x")
            op  = block.content.get("op", "==")
            val = block.content.get("value", "0")
            true_pc  = next_pc(0)
            false_pc = next_pc(1)
            lines.append("with _shared_lock:")
            lines.append(f"    _cond = ({var} {op} {int(val)})")
            lines.append(f"_pc = {true_pc} if _cond else {false_pc}")

        return lines

    # ──────────────────────────────────────────────────────────── main()
    def _build_main(self, n_threads: int, all_vars: List[str]) -> List[str]:
        lines: List[str] = [
            "def main() -> None:",
        ]
        if all_vars:
            lines.append(f"{_I1}global {', '.join(all_vars)}")
        lines += [
            "",
            f"{_I1}threads = [",
        ]
        for i in range(n_threads):
            lines.append(f"{_I2}threading.Thread(target=thread_{i}, name='Thread-{i}'),")
        lines += [
            f"{_I1}]",
            "",
            f"{_I1}for t in threads:",
            f"{_I2}t.start()",
            f"{_I1}for t in threads:",
            f"{_I2}t.join()",
            "",
            "",
            "if __name__ == '__main__':",
            f"{_I1}main()",
        ]
        return lines
