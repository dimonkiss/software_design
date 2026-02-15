from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPen, QColor, QPainterPath
from PyQt6.QtWidgets import QGraphicsPathItem

from src.parallel_emulator.domain.enums.block_type import BlockType
from src.parallel_emulator.infrastructure.gui.editor.block_item import BlockItem


class ConnectionItem(QGraphicsPathItem):
    def __init__(self, start_item: "BlockItem", end_item: "BlockItem", is_true: bool = False, parent=None):
        super().__init__(parent)
        self.start_item = start_item
        self.end_item = end_item
        self.is_true = is_true
        self.setPen(QPen(QColor(50, 50, 50), 3, Qt.PenStyle.SolidLine))
        self.setZValue(-1)
        self.update_path()

    def update_path(self):
        start_pos = self.start_item.pos() + self.start_item.out_port.pos() + self.start_item.out_port.rect().center()
        if self.start_item.block.type == BlockType.DECISION and self.is_true and self.start_item.true_port:
            start_pos = self.start_item.pos() + self.start_item.true_port.pos() + self.start_item.true_port.rect().center()
        elif self.start_item.block.type == BlockType.DECISION and not self.is_true and self.start_item.false_port:
            start_pos = self.start_item.pos() + self.start_item.false_port.pos() + self.start_item.false_port.rect().center()

        end_pos = self.end_item.pos() + QPointF(70, 0)  # top center of target

        path = QPainterPath()
        path.moveTo(start_pos)
        path.lineTo(end_pos)
        self.setPath(path)