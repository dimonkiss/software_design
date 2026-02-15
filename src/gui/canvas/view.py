from PySide6.QtWidgets import QGraphicsView
from PySide6.QtGui import QPainter, QWheelEvent
from PySide6.QtCore import Qt

# ВАЖЛИВО: Імпортуємо наш кастомний клас сцени
from src.gui.canvas.scene import CanvasScene


class CanvasView(QGraphicsView):
    def __init__(self):
        super().__init__()

        # ВАЖЛИВО: Використовуємо CanvasScene замість QGraphicsScene
        self.scene = CanvasScene()
        self.setScene(self.scene)

        # Налаштування рендерингу (без змін)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        # Малюємо фон
        self.setBackgroundBrush(Qt.lightGray)

    def wheelEvent(self, event: QWheelEvent):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)