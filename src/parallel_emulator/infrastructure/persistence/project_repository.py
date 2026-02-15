from typing import List, Optional
from uuid import UUID

from src.parallel_emulator.domain.entities.project import Project
from src.parallel_emulator.infrastructure.persistence.file_storage import FileStorage
from src.parallel_emulator.infrastructure.serialization.json_serializer import ProjectSerializer


class ProjectRepository:
    """Чистий CRUD-репозиторій для проєктів (JSON filesystem)"""

    def __init__(self, storage: FileStorage, serializer: ProjectSerializer):
        self.storage = storage
        self.serializer = serializer

    # ── CREATE ─────────────────────────────────────────────────────────────
    def create(self, project: Project) -> Project:
        project.id = project.id or UUID(int=0)  # генеруємо при збереженні
        path = self.storage.get_project_path(project.id)
        data = self.serializer.to_dict(project)
        self.storage.save(path, data)
        return project

    # ── READ ───────────────────────────────────────────────────────────────
    def get_by_id(self, project_id: UUID) -> Optional[Project]:
        path = self.storage.get_project_path(project_id)
        if not path.exists():
            return None
        data = self.storage.load(path)
        return self.serializer.from_dict(data)

    def list_all(self) -> List[Project]:
        paths = self.storage.list_project_files()
        return [self.serializer.from_dict(self.storage.load(p)) for p in paths]

    # ── UPDATE ─────────────────────────────────────────────────────────────
    def update(self, project: Project) -> Project:
        path = self.storage.get_project_path(project.id)
        data = self.serializer.to_dict(project)
        self.storage.save(path, data)
        return project

    # ── DELETE ─────────────────────────────────────────────────────────────
    def delete(self, project_id: UUID) -> bool:
        path = self.storage.get_project_path(project_id)
        return self.storage.delete(path)