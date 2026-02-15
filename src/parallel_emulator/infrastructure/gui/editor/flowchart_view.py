from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QPainter
from PyQt6.QtWidgets import QGraphicsView, QMessageBox

from src.parallel_emulator.domain.enums.block_type import BlockType
from .flowchart_scene import FlowchartScene


class FlowchartView(QGraphicsView):
    def __init__(self, scene: FlowchartScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing
        )
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        # === DRAG & DROP ===
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        mime = event.mimeData()
        if mime.hasText():
            block_type_str = mime.text().strip().upper()
            try:
                block_type = BlockType[block_type_str]
                scene_pos = self.mapToScene(event.position().toPoint())
                self.scene().add_block(block_type, scene_pos)
                event.acceptProposedAction()
            except Exception as e:
                QMessageBox.warning(self, "Помилка drag & drop",
                                  f"Не вдалося додати {block_type_str}:\n{str(e)}")
                event.ignore()
        else:
            super().dropEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.2 if event.angleDelta().y() > 0 else 0.8
            self.scale(factor, factor)
        else:
            super().wheelEvent(event)