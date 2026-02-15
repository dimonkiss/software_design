from PyQt6.QtCore import QThread, pyqtSignal

from src.parallel_emulator.core.interleaving_search import InterleavingSearch
from src.parallel_emulator.domain.entities.project import Project


class SimulationThread(QThread):
    finished = pyqtSignal(bool, str)  # success, message
    stopped = pyqtSignal()
    progress = pyqtSignal(str)

    def __init__(self, project: Project, input_data: list[int], expected: list[int]):
        super().__init__()
        self.project = project
        self.input_data = input_data
        self.expected = expected
        self.search = None
        self._k = 0

    def run(self):
        try:
            self.search = InterleavingSearch(self.project, self.input_data, self.expected)
            success = self.search.run()
            if success:
                self.finished.emit(True, "Всі шляхи коректні!")
            else:
                self.finished.emit(False, "Знайдено контрприклад!")
        except Exception as e:
            self.finished.emit(False, f"Помилка: {str(e)}")

    def stop(self):
        if self.search:
            self.search.stop_event.set()
        self.stopped.emit()
        self.quit()
        self.wait()