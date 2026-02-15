from dataclasses import dataclass, field
from typing import List
from uuid import UUID, uuid4

from src.parallel_emulator.domain.entities.thread import Thread


@dataclass
class Project:
    """Кореневий агрегат проєкту"""
    id: UUID = field(default_factory=uuid4)
    name: str = "Untitled Project"
    threads: List[Thread] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)

    def add_thread(self, thread: Thread) -> None:
        if any(t.id == thread.id for t in self.threads):
            raise ValueError(f"Thread with id {thread.id} already exists")
        self.threads.append(thread)

    def remove_thread(self, thread_id: int) -> None:
        self.threads = [t for t in self.threads if t.id != thread_id]

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "threads": [t.to_dict() for t in self.threads],
            "variables": self.variables,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        raise NotImplementedError("Use ProjectSerializer.from_dict instead")