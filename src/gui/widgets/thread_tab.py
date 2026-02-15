from PySide6.QtWidgets import QWidget, QVBoxLayout
from src.gui.canvas.view import CanvasView
from src.core.models import ThreadModel


class ThreadTab(QWidget):
    def __init__(self, thread_model: ThreadModel):
        super().__init__()
        self.thread_model = thread_model

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.view = CanvasView()
        self.layout.addWidget(self.view)

        # ВАЖЛИВО: Передаємо модель сцені
        self.view.scene.set_thread_model(thread_model)