from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QPen, QColor, QPainterPath, QPainterPathStroker
from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsItem

from src.parallel_emulator.domain.enums.block_type import BlockType


class ConnectionItem(QGraphicsPathItem):
    def __init__(self, from_item, to_item, is_true=False):
        super().__init__()
        self.from_item = from_item
        self.to_item = to_item
        self.is_true = is_true

        color = QColor(100, 180, 255)
        if from_item.block.type == BlockType.DECISION:
            color = QColor(0, 200, 0) if is_true else QColor(220, 0, 0)

        self.visible_pen = QPen(color, 3)

        self.setPen(self.visible_pen)
        self.setBrush(QColor(0, 0, 0, 0))
        self.setZValue(-1)

        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

        self.update_position()

    def update_position(self):
        start = self._get_start_pos()
        end = self._get_end_pos()

        path = QPainterPath(start)
        path.lineTo(end)
        self.setPath(path)

    def shape(self):
        stroker = QPainterPathStroker()
        stroker.setWidth(20)
        return stroker.createStroke(self.path())

    def boundingRect(self):
        r = super().boundingRect()
        pad = 12.0
        return r.adjusted(-pad, -pad, pad, pad)

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

    def hoverEnterEvent(self, event):
        self.setPen(QPen(self.visible_pen.color(), 6))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setPen(self.visible_pen)
        super().hoverLeaveEvent(event)

    def _delayed_delete(self):
        if self.scene():
            self.scene().remove_connection(self)