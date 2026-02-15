from dataclasses import dataclass, field
from typing import Dict, Optional

from src.parallel_emulator.domain.entities.block import Block
from src.parallel_emulator.domain.enums.block_type import BlockType


@dataclass
class Thread:
    """Один потік (не frozen — можна додавати блоки під час редагування)"""
    id: int
    name: str = ""
    blocks: Dict[int, Block] = field(default_factory=dict)
    start_block_id: Optional[int] = None

    def add_block(self, block: Block) -> None:
        """Додає блок і автоматично встановлює start_block_id"""
        if block.id in self.blocks:
            raise ValueError(f"Block with id {block.id} already exists in thread {self.id}")
        self.blocks[block.id] = block
        if block.type == BlockType.START:
            self.start_block_id = block.id

    def remove_block(self, block_id: int) -> None:
        """Видаляє блок (з майбутньою перевіркою зв'язків)"""
        if block_id in self.blocks:
            del self.blocks[block_id]
            if self.start_block_id == block_id:
                self.start_block_id = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "blocks": [b.to_dict() for b in self.blocks.values()],
            "start_block_id": self.start_block_id,
        }