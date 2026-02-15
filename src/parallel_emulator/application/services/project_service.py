from typing import List, Optional
from uuid import UUID

from src.parallel_emulator.domain.entities.project import Project
from src.parallel_emulator.domain.entities.thread import Thread
from src.parallel_emulator.domain.exceptions import DuplicateThreadException
from src.parallel_emulator.infrastructure.persistence.project_repository import ProjectRepository


class ProjectService:
    """Application Service — оркестрація CRUD операцій над проєктами"""

    def __init__(self, repository: ProjectRepository) -> None:
        self._repo = repository

    # ── CREATE ─────────────────────────────────────────────────────────────
    def create_project(self, name: str = "Untitled Project") -> Project:
        """Створює новий порожній проєкт"""
        project = Project(name=name)
        return self._repo.create(project)

    # ── READ ───────────────────────────────────────────────────────────────
    def get_project(self, project_id: UUID) -> Optional[Project]:
        """Повертає проєкт за ID"""
        return self._repo.get_by_id(project_id)

    def list_projects(self) -> List[Project]:
        """Список всіх збережених проєктів"""
        return self._repo.list_all()

    # ── UPDATE ─────────────────────────────────────────────────────────────
    def update_project(self, project: Project) -> Project:
        """Зберігає зміни в проєкті"""
        return self._repo.update(project)

    def add_thread_to_project(self, project_id: UUID, thread: Thread) -> Project:
        """Додає новий потік до проєкту"""
        project = self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        if any(t.id == thread.id for t in project.threads):
            raise DuplicateThreadException(f"Thread {thread.id} already exists")

        project.add_thread(thread)
        return self._repo.update(project)

    # ── DELETE ─────────────────────────────────────────────────────────────
    def delete_project(self, project_id: UUID) -> bool:
        """Видаляє проєкт"""
        return self._repo.delete(project_id)