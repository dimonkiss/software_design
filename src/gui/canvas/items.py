import math
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsTextItem, QGraphicsItem
from PySide6.QtGui import QPainterPath, QColor, QPen, QBrush, QPolygonF
from PySide6.QtCore import Qt, QPointF, QLineF

# Імпорт лише для анотацій типів
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.models import Block


class ConnectionItem(QGraphicsPathItem):
    def __init__(self, source, dest):
        super().__init__()
        self.source = source
        self.dest = dest

        self.setPen(QPen(Qt.black, 2))
        self.setZValue(-1)

        self.source.add_connection(self)
        self.dest.add_connection(self)

        self.update_path()

    def update_path(self):
        """Перераховує лінію та малює стрілку."""
        if not self.source.scene() or not self.dest.scene():
            return

        start_pos = self.source.scenePos() + self.source.boundingRect().center()
        end_pos = self.dest.scenePos() + self.dest.boundingRect().center()

        path = QPainterPath()
        path.moveTo(start_pos)
        path.lineTo(end_pos)

        # --- Малювання наконечника стрілки ---
        line = QLineF(start_pos, end_pos)
        angle = math.atan2(-line.dy(), line.dx())
        arrow_size = 10

        arrow_p1 = end_pos + QPointF(math.sin(angle - math.pi / 3) * arrow_size,
                                     math.cos(angle - math.pi / 3) * arrow_size)
        arrow_p2 = end_pos + QPointF(math.sin(angle - math.pi + math.pi / 3) * arrow_size,
                                     math.cos(angle - math.pi + math.pi / 3) * arrow_size)

        path.moveTo(end_pos)
        path.lineTo(arrow_p1)
        path.moveTo(end_pos)
        path.lineTo(arrow_p2)

        self.setPath(path)

    def remove_self(self):
        self.source.remove_connection(self)
        self.dest.remove_connection(self)
        if self.scene():
            self.scene().removeItem(self)


class BlockItem(QGraphicsPathItem):
    def __init__(self, block_model: 'Block'):
        super().__init__()
        self.model = block_model
        self.connections = []
        self.label = None  # Ініціалізуємо змінну для напису

        self.setFlags(QGraphicsItem.ItemIsMovable |
                      QGraphicsItem.ItemIsSelectable |
                      QGraphicsItem.ItemSendsGeometryChanges)

        self.setPos(block_model.pos_x, block_model.pos_y)
        self._setup_appearance()
        self._add_label()

    def add_connection(self, connection):
        self.connections.append(connection)

    def remove_connection(self, connection):
        if connection in self.connections:
            self.connections.remove(connection)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            self.model.pos_x = value.x()
            self.model.pos_y = value.y()
            for conn in self.connections:
                conn.update_path()
        return super().itemChange(change, value)

    def _setup_appearance(self):
        path = QPainterPath()
        w, h = 120, 60

        if self.model.type in ('START', 'END'):
            path.addRoundedRect(0, 0, w, h, 20, 20)
            color = QColor("#4CAF50") if self.model.type == 'START' else QColor("#F44336")
        elif self.model.type == 'DECISION':
            path.moveTo(w / 2, 0)
            path.lineTo(w, h / 2)
            path.lineTo(w / 2, h)
            path.lineTo(0, h / 2)
            path.closeSubpath()
            color = QColor("#FF9800")
        elif self.model.type in ('INPUT', 'PRINT'):
            path.moveTo(15, 0)
            path.lineTo(w + 15, 0)
            path.lineTo(w - 15, h)
            path.lineTo(-15, h)
            path.closeSubpath()
            color = QColor("#2196F3")
        else:
            path.addRect(0, 0, w, h)
            color = QColor("#9C27B0")

        self.setPath(path)
        self.setPen(QPen(Qt.black, 2))
        self.setBrush(QBrush(color))

    def _add_label(self):
        self.label = QGraphicsTextItem(self.model.type, self)
        self.label.setDefaultTextColor(Qt.white)

        # Центрування тексту
        b_rect = self.path().boundingRect()
        l_rect = self.label.boundingRect()
        self.label.setPos(
            b_rect.center().x() - l_rect.width() / 2,
            b_rect.center().y() - l_rect.height() / 2
        )