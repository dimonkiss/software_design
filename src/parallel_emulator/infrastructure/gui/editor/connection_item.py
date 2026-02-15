from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPen, QColor
from PyQt6.QtWidgets import QGraphicsLineItem, QGraphicsItem

from src.parallel_emulator.domain.enums.block_type import BlockType


class ConnectionItem(QGraphicsLineItem):
    def __init__(self, from_item, to_item, is_true=False):
        super().__init__()
        self.from_item = from_item
        self.to_item = to_item
        self.is_true = is_true

        color = QColor(100, 180, 255)
        if from_item.block.type == BlockType.DECISION:
            color = QColor(0, 200, 0) if is_true else QColor(220, 0, 0)

        self.setPen(QPen(color, 3))
        self.setZValue(-1)  # під блоками

        self.update_position()

    def update_position(self):
        start = self._get_start_pos()
        end = self._get_end_pos()
        self.setLine(start.x(), start.y(), end.x(), end.y())

    def _get_start_pos(self):
        if self.from_item.block.type == BlockType.DECISION:
            port = self.from_item.true_port if self.is_true else self.from_item.false_port
        else:
            port = self.from_item.out_port
        return self.from_item.mapToScene(port.rect().center())

    def _get_end_pos(self):
        if self.to_item.in_port:
            return self.to_item.mapToScene(self.to_item.in_port.rect().center())
        return self.to_item.scenePos() + QPointF(70, 0)

    # Оновлення при русі блоків
    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.update_position()
        return super().itemChange(change, value)