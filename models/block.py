from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class BlockType(Enum):
    START = "start"
    END = "end"
    ASSIGN = "assign"       # V1=V2  or  V=C
    INPUT = "input"         # INPUT V
    PRINT = "print"         # PRINT V
    CONDITION = "condition"  # V==C  or  V<C


BLOCK_COLORS: Dict[BlockType, str] = {
    BlockType.START:     "#90EE90",  # light-green
    BlockType.END:       "#FA8072",  # salmon
    BlockType.ASSIGN:    "#ADD8E6",  # light-blue
    BlockType.INPUT:     "#FFFACD",  # lemon-chiffon
    BlockType.PRINT:     "#FFE4B5",  # moccasin
    BlockType.CONDITION: "#FFB6C1",  # light-pink
}

# Maximum number of outgoing edges per block type
MAX_NEXT: Dict[BlockType, int] = {
    BlockType.START:     1,
    BlockType.END:       0,
    BlockType.ASSIGN:    1,
    BlockType.INPUT:     1,
    BlockType.PRINT:     1,
    BlockType.CONDITION: 2,
}


@dataclass
class Block:
    """A single node in a flowchart (block diagram)."""

    block_type: BlockType
    content: Dict[str, Any] = field(default_factory=dict)
    x: float = 200.0
    y: float = 200.0
    # Ordered list of successor block-ids.
    # For CONDITION: index 0 = TRUE branch, index 1 = FALSE branch.
    next_blocks: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # ------------------------------------------------------------------ label
    def get_label(self) -> str:
        bt = self.block_type
        if bt == BlockType.START:
            return "START"
        if bt == BlockType.END:
            return "END"
        if bt == BlockType.ASSIGN:
            target = self.content.get("target", "?")
            source = self.content.get("source", "?")
            return f"{target} = {source}"
        if bt == BlockType.INPUT:
            return f"INPUT {self.content.get('var', '?')}"
        if bt == BlockType.PRINT:
            return f"PRINT {self.content.get('var', '?')}"
        if bt == BlockType.CONDITION:
            var = self.content.get("var", "?")
            op  = self.content.get("op", "==")
            val = self.content.get("value", "?")
            return f"{var} {op} {val}"
        return "?"

    # --------------------------------------------------------------- multiline
    def get_multiline_label(self) -> str:
        """Returns label split into lines ≤ 14 chars for canvas display."""
        lbl = self.get_label()
        if len(lbl) <= 14:
            return lbl
        # Split at spaces
        words = lbl.split()
        lines, current = [], ""
        for w in words:
            if current and len(current) + len(w) + 1 > 14:
                lines.append(current)
                current = w
            else:
                current = current + " " + w if current else w
        if current:
            lines.append(current)
        return "\n".join(lines)

    # ---------------------------------------------------------- serialization
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "block_type": self.block_type.value,
            "content": self.content,
            "x": self.x,
            "y": self.y,
            "next_blocks": self.next_blocks,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Block":
        block = cls(
            block_type=BlockType(data["block_type"]),
            content=data.get("content", {}),
            x=data.get("x", 200.0),
            y=data.get("y", 200.0),
            next_blocks=data.get("next_blocks", []),
        )
        block.id = data["id"]
        return block
