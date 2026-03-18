from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from models.block import Block, BlockType, MAX_NEXT


@dataclass
class Flowchart:
    """Directed graph of Blocks representing one thread's algorithm."""

    name: str
    blocks: Dict[str, Block] = field(default_factory=dict)
    start_block_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # ---------------------------------------------------------- block CRUD
    def add_block(self, block: Block) -> str:
        self.blocks[block.id] = block
        if block.block_type == BlockType.START and self.start_block_id is None:
            self.start_block_id = block.id
        return block.id

    def remove_block(self, block_id: str) -> None:
        self.blocks.pop(block_id, None)
        for blk in self.blocks.values():
            blk.next_blocks = [nid for nid in blk.next_blocks if nid != block_id]
        if self.start_block_id == block_id:
            self.start_block_id = None

    def add_connection(self, src_id: str, dst_id: str, branch: Optional[str] = None) -> bool:
        """
        Connect src_id → dst_id.

        For CONDITION blocks *branch* must be "true" or "false".
        Returns False when the connection would exceed limits or is invalid.
        """
        src = self.blocks.get(src_id)
        dst = self.blocks.get(dst_id)
        if src is None or dst is None:
            return False
        if dst_id == src_id:
            return False

        max_edges = MAX_NEXT.get(src.block_type, 1)

        if src.block_type == BlockType.CONDITION:
            if branch not in ("true", "false"):
                return False
            # Normalise to a length-2 list with "" placeholders
            while len(src.next_blocks) < 2:
                src.next_blocks.append("")
            idx = 0 if branch == "true" else 1
            src.next_blocks[idx] = dst_id
            # Remove any trailing empty slots, but keep structure intact for validation
            # (don't strip – the interpreter reads by index)
        else:
            if len(src.next_blocks) >= max_edges:
                src.next_blocks = [dst_id]   # overwrite
            else:
                src.next_blocks.append(dst_id)

        return True

    def remove_connection(self, src_id: str, dst_id: str) -> None:
        src = self.blocks.get(src_id)
        if src:
            src.next_blocks = [nid for nid in src.next_blocks if nid != dst_id]

    # ------------------------------------------------------ queries / helpers
    def get_start_block(self) -> Optional[Block]:
        if self.start_block_id:
            return self.blocks.get(self.start_block_id)
        return None

    def get_all_variables(self) -> List[str]:
        var_set: Set[str] = set()
        for blk in self.blocks.values():
            c = blk.content
            if "target" in c:
                var_set.add(c["target"])
            if c.get("src_type") == "var" and "source" in c:
                var_set.add(c["source"])
            if "var" in c:
                var_set.add(c["var"])
        return sorted(var_set)

    # ------------------------------------------------------------ validation
    def validate(self) -> List[str]:
        errors: List[str] = []

        if not self.start_block_id or self.start_block_id not in self.blocks:
            errors.append("No START block defined.")

        if not any(b.block_type == BlockType.END for b in self.blocks.values()):
            errors.append("No END block defined.")

        if len(self.blocks) > 100:
            errors.append(f"Too many blocks ({len(self.blocks)}); maximum is 100.")

        for blk in self.blocks.values():
            max_e = MAX_NEXT[blk.block_type]
            if blk.block_type == BlockType.CONDITION:
                # Both branches must be connected
                valid = [nid for nid in blk.next_blocks if nid and nid in self.blocks]
                if len(valid) != 2:
                    errors.append(
                        f"CONDITION block «{blk.get_label()}» must have both TRUE and FALSE branches connected."
                    )
            elif blk.block_type != BlockType.END:
                valid = [nid for nid in blk.next_blocks if nid and nid in self.blocks]
                if len(valid) != 1:
                    errors.append(
                        f"Block «{blk.get_label()}» must have exactly one outgoing connection."
                    )
            # Check dangling references
            for nid in blk.next_blocks:
                if nid and nid not in self.blocks:
                    errors.append(f"Block «{blk.get_label()}» references missing block {nid}.")

        return errors

    # --------------------------------------------------------- serialization
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "blocks": {bid: blk.to_dict() for bid, blk in self.blocks.items()},
            "start_block_id": self.start_block_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Flowchart":
        fc = cls(name=data["name"])
        fc.id = data["id"]
        fc.start_block_id = data.get("start_block_id")
        fc.blocks = {
            bid: Block.from_dict(bd) for bid, bd in data.get("blocks", {}).items()
        }
        return fc
