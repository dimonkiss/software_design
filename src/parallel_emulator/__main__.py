from pathlib import Path
import sys

from PyQt6.QtWidgets import QApplication

from src.parallel_emulator.application.services.project_service import ProjectService
from src.parallel_emulator.domain.entities.project import Project
from src.parallel_emulator.domain.entities.thread import Thread
from src.parallel_emulator.infrastructure.gui.main_window import MainWindow
from src.parallel_emulator.infrastructure.persistence.file_storage import FileStorage
from src.parallel_emulator.infrastructure.persistence.project_repository import ProjectRepository
from src.parallel_emulator.infrastructure.serialization.json_serializer import ProjectSerializer


def main():
    app = QApplication(sys.argv)

    storage = FileStorage(Path("data/projects"))
    serializer = ProjectSerializer()
    repository = ProjectRepository(storage, serializer)
    service = ProjectService(repository)

    project = Project(name="Demo Project")
    thread = Thread(id=1, name="Main Thread")
    project.add_thread(thread)

    window = MainWindow(service, project)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()