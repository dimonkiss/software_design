from enum import StrEnum, auto


class BlockType(StrEnum):
    """Типи блоків блок-схеми"""
    START = auto()
    END = auto()
    ASSIGN = auto()
    INPUT = auto()
    PRINT = auto()
    DECISION = auto()