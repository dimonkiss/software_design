from typing import Optional

from src.parallel_emulator.core.state import MutableState
from src.parallel_emulator.domain.entities.block import Block
from src.parallel_emulator.domain.entities.project import Project
from src.parallel_emulator.domain.enums.block_type import BlockType


class BlockInterpreter:
    """Інтерпретатор одного блоку одного потоку (чистий, без стану)"""

    def __init__(self, project: Project) -> None:
        self.project = project

    def _get_thread(self, thread_id: int):
        for t in self.project.threads:
            if t.id == thread_id:
                return t
        raise ValueError(f"Thread {thread_id} not found")

    def _get_block(self, thread, block_id: int) -> Block:
        block = thread.blocks.get(block_id)
        if block is None:
            raise ValueError(f"Block {block_id} not found in thread {thread.id}")
        return block

    def execute_step(self, state: MutableState, thread_id: int) -> None:
        """Виконує один блок і мутає MutableState (викликається тільки якщо потік активний)"""
        thread = self._get_thread(thread_id)
        pc = state.pcs[thread_id]
        if pc is None:
            return

        block = self._get_block(thread, pc)

        next_pc: Optional[int] = None

        if block.type == BlockType.START:
            next_pc = block.next

        elif block.type == BlockType.END:
            next_pc = None

        elif block.type == BlockType.ASSIGN:
            if block.source is None or block.target is None:
                raise ValueError("ASSIGN block missing source/target")
            if block.source.type == "const":
                value = block.source.value
            else:
                value = state.variables.get(block.source.value, 0)
            state.variables[block.target] = value & 0xFFFFFFFF  # 32-bit unsigned wrap
            next_pc = block.next

        elif block.type == BlockType.INPUT:
            if block.io_var is None:
                raise ValueError("INPUT missing io_var")
            if state.input_remaining:
                value = state.input_remaining.pop(0)
                state.variables[block.io_var] = value & 0xFFFFFFFF
                next_pc = block.next
            # else: blocked — не повинно траплятися, бо ми перевіряємо active

        elif block.type == BlockType.PRINT:
            if block.io_var is None:
                raise ValueError("PRINT missing io_var")
            value = state.variables.get(block.io_var, 0)
            state.output.append(value)
            next_pc = block.next

        elif block.type == BlockType.DECISION:
            if block.condition is None:
                raise ValueError("DECISION missing condition")
            var_value = state.variables.get(block.condition.var, 0)
            if block.condition.op == "==":
                cond = var_value == block.condition.const
            else:  # "<"
                cond = var_value < block.condition.const
            next_pc = block.true_next if cond else block.false_next

        state.pcs[thread_id] = next_pc
        state.depth += 1