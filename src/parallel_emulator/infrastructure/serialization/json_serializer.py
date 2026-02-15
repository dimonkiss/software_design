from typing import Any, Dict
from uuid import UUID

from src.parallel_emulator.domain.entities.block import Block
from src.parallel_emulator.domain.entities.project import Project
from src.parallel_emulator.domain.entities.thread import Thread
from src.parallel_emulator.domain.enums.block_type import BlockType
from src.parallel_emulator.domain.value_objects.condition import Condition
from src.parallel_emulator.domain.value_objects.source import Source


class ProjectSerializer:
    """Відповідає виключно за перетворення доменних об'єктів ↔ JSON (orjson)"""

    @staticmethod
    def to_dict(project: Project) -> Dict[str, Any]:
        """Серіалізація для збереження"""
        return {
            "id": str(project.id),
            "name": project.name,
            "variables": project.variables,
            "threads": [ProjectSerializer._thread_to_dict(t) for t in project.threads]
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Project:
        """Десеріалізація з JSON"""
        project = Project(
            id=UUID(data["id"]),
            name=data.get("name", "Untitled Project"),
            variables=data.get("variables", []),
        )

        for t_data in data.get("threads", []):
            thread = Thread(
                id=t_data["id"],
                name=t_data.get("name", f"Thread {t_data['id']}"),
            )
            for b_data in t_data.get("blocks", []):
                block = ProjectSerializer._block_from_dict(b_data)
                thread.add_block(block)
            project.add_thread(thread)

        return project

    # ── Приватні допоміжні методи ─────────────────────────────────────
    @staticmethod
    def _thread_to_dict(thread: Thread) -> Dict[str, Any]:
        return {
            "id": thread.id,
            "name": thread.name,
            "blocks": [b.to_dict() for b in thread.blocks.values()],
            "start_block_id": thread.start_block_id,
        }

    @staticmethod
    def _block_from_dict(data: Dict[str, Any]) -> Block:
        block_type = BlockType(data["type"])

        source = None
        if "source" in data:
            source = Source(**data["source"])

        condition = None
        if "condition" in data:
            condition = Condition(**data["condition"])

        return Block(
            id=data["id"],
            type=block_type,
            x=data.get("x", 100.0),
            y=data.get("y", 100.0),
            next=data.get("next"),
            target=data.get("target"),
            source=source,
            io_var=data.get("target") if block_type in (BlockType.INPUT, BlockType.PRINT) else None,
            condition=condition,
            true_next=data.get("true_next"),
            false_next=data.get("false_next"),
        )