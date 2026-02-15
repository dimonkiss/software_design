from dataclasses import replace

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QPen, QColor, QFont
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsItem, QMenu

from src.parallel_emulator.domain.entities.block import Block
from src.parallel_emulator.domain.enums.block_type import BlockType


class BlockItem(QGraphicsRectItem):
    WIDTH = 140
    HEIGHT = 70

    def __init__(self, block: Block, parent=None):
        super().__init__(0, 0, self.WIDTH, self.HEIGHT, parent)
        self.block = block
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
                      QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setPen(QPen(Qt.GlobalColor.black, 2))
        self.setBrush(self._get_brush())

        # Основний текст
        self.text_item = QGraphicsTextItem(block.type.value.upper(), self)
        self.text_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.text_item.setPos(10, 8)

        # Параметри
        self.param_text = QGraphicsTextItem(self._get_param_text(), self)
        self.param_text.setPos(10, 38)
        self.param_text.setFont(QFont("Segoe UI", 8))

        # ==================== ПОРТИ ====================

        # Вхідний порт (зверху) — є у всіх, крім START
        self.in_port = None
        if block.type != BlockType.START:
            self.in_port = QGraphicsEllipseItem(62, -8, 16, 16, self)
            self.in_port.setBrush(QBrush(QColor(0, 100, 255)))  # синій = вхід
            self.in_port.setPen(QPen(Qt.GlobalColor.black))

        # Вихідний порт (знизу) — є ТІЛЬКИ у ASSIGN, INPUT, PRINT
        # НЕМАЄ у END і DECISION
        self.out_port = None
        if block.type in (BlockType.ASSIGN, BlockType.INPUT, BlockType.PRINT, BlockType.START):
            self.out_port = QGraphicsEllipseItem(62, self.HEIGHT - 8, 16, 16, self)
            self.out_port.setBrush(QBrush(QColor(0, 180, 0)))  # зелений = вихід
            self.out_port.setPen(QPen(Qt.GlobalColor.black))

        # Спеціальні порти для DECISION (True / False)
        self.true_port = None
        self.false_port = None
        if block.type == BlockType.DECISION:
            self.true_port = QGraphicsEllipseItem(self.WIDTH - 20, 25, 16, 16, self)  # справа
            self.true_port.setBrush(QBrush(QColor(0, 200, 0)))  # зелений = True
            self.false_port = QGraphicsEllipseItem(4, 25, 16, 16, self)  # зліва
            self.false_port.setBrush(QBrush(QColor(220, 0, 0)))  # червоний = False

    def _get_brush(self) -> QBrush:
        colors = {
            BlockType.START:    QColor(100, 200, 100),
            BlockType.END:      QColor(200, 100, 100),
            BlockType.ASSIGN:   QColor(100, 150, 255),
            BlockType.INPUT:    QColor(255, 200, 100),
            BlockType.PRINT:    QColor(255, 150, 100),
            BlockType.DECISION: QColor(180, 100, 255),
        }
        return QBrush(colors.get(self.block.type, QColor(220, 220, 220)))

    def _get_param_text(self) -> str:
        if self.block.type == BlockType.ASSIGN and self.block.source:
            return f"{self.block.target} = {self.block.source.value}"
        if self.block.type in (BlockType.INPUT, BlockType.PRINT) and self.block.io_var:
            return self.block.io_var
        if self.block.type == BlockType.DECISION and self.block.condition:
            return f"{self.block.condition.var} {self.block.condition.op} {self.block.condition.const}"
        return ""

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            new_block = replace(self.block, x=float(self.pos().x()), y=float(self.pos().y()))
            self.block = new_block
            if hasattr(self.scene(), "on_block_moved"):
                self.scene().on_block_moved(self)
        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        if hasattr(self.scene(), "edit_block"):
            self.scene().edit_block(self)

    def contextMenuEvent(self, event):
        menu = QMenu()
        edit_action = menu.addAction("Редагувати блок")
        delete_action = menu.addAction("Видалити блок")
        edit_action.setEnabled(self.block.type not in (BlockType.START, BlockType.END))

        chosen = menu.exec(event.screenPos())
        if chosen == edit_action and hasattr(self.scene(), "edit_block"):
            self.scene().edit_block(self)
        elif chosen == delete_action and hasattr(self.scene(), "remove_block"):
            self.scene().remove_block(self)

    def contextMenuEvent(self, event):
        menu = QMenu()

        edit_action = menu.addAction("Редагувати блок")
        delete_action = menu.addAction("Видалити блок")

        # Забороняємо редагування START і END
        edit_action.setEnabled(self.block.type not in (BlockType.START, BlockType.END))

        chosen = menu.exec(event.screenPos())

        if chosen == edit_action:
            if hasattr(self.scene(), "edit_block"):
                self.scene().edit_block(self)
        elif chosen == delete_action:
            if hasattr(self.scene(), "remove_block"):
                self.scene().remove_block(self)