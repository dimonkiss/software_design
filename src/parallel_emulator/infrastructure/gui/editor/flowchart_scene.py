from dataclasses import replace
from typing import Dict, Optional
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsSceneMouseEvent

from src.parallel_emulator.domain.entities.block import Block
from src.parallel_emulator.domain.entities.thread import Thread
from src.parallel_emulator.domain.enums.block_type import BlockType
from src.parallel_emulator.domain.value_objects.condition import Condition
from src.parallel_emulator.domain.value_objects.source import Source
from src.parallel_emulator.infrastructure.gui.dialogs.block_dialog import BlockEditDialog
from src.parallel_emulator.infrastructure.gui.editor.block_item import BlockItem
from src.parallel_emulator.infrastructure.gui.editor.connection_item import ConnectionItem


class FlowchartScene(QGraphicsScene):
    block_changed = pyqtSignal()   # для оновлення Project

    def __init__(self, thread: Thread, parent=None):
        super().__init__(parent)
        self.thread = thread
        self.block_items: Dict[int, BlockItem] = {}
        self.connections: list[ConnectionItem] = []
        self._connection_start: Optional[BlockItem] = None
        self._rubber_line = None
        self._is_true_branch = False

        self.setSceneRect(0, 0, 2000, 2000)
        self.load_from_thread()

    def load_from_thread(self):
        self.clear()
        self.block_items.clear()
        self.connections.clear()

        for block in self.thread.blocks.values():
            item = BlockItem(block)
            item.setPos(block.x, block.y)
            self.addItem(item)
            self.block_items[block.id] = item

        # TODO: завантаження зв’язків (можна додати пізніше, якщо зберігати connections окремо)

    def start_connection(self, from_item: BlockItem, is_true: bool = False):
        self._connection_start = from_item
        self._is_true_branch = is_true
        self._rubber_line = self.addLine(0, 0, 0, 0, Qt.PenStyle.DashLine)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self._rubber_line and self._connection_start:
            start_pos = self._connection_start.pos() + QPointF(70, 60)
            self._rubber_line.setLine(start_pos.x(), start_pos.y(), event.scenePos().x(), event.scenePos().y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self._connection_start and self._rubber_line:
            end_item = self.itemAt(event.scenePos(), self.views()[0].transform())
            if isinstance(end_item, BlockItem) and end_item != self._connection_start:
                self._create_connection(self._connection_start, end_item, self._is_true_branch)
            self.removeItem(self._rubber_line)
            self._rubber_line = None
            self._connection_start = None
        super().mouseReleaseEvent(event)

    def _create_connection(self, from_item: BlockItem, to_item: BlockItem, is_true: bool):
        # оновлюємо модель
        from_block = from_item.block
        to_id = to_item.block.id

        if from_block.type == BlockType.DECISION:
            new_block = replace(from_block,
                                true_next=to_id if is_true else from_block.true_next,
                                false_next=to_id if not is_true else from_block.false_next)
        else:
            new_block = replace(from_block, next=to_id)

        self.thread.blocks[from_block.id] = new_block
        from_item.block = new_block   # оновлюємо item

        conn = ConnectionItem(from_item, to_item, is_true)
        self.addItem(conn)
        self.connections.append(conn)
        self.block_changed.emit()

    def add_block(self, block_type: BlockType, pos: QPointF):
        """Створює блок з усіма обов'язковими полями одразу — проходить __post_init__"""
        new_id = max(self.thread.blocks.keys(), default=0) + 1

        if block_type == BlockType.START:
            block = Block(
                id=new_id,
                type=block_type,
                x=pos.x(),
                y=pos.y(),
                next=new_id + 1
            )
        elif block_type == BlockType.END:
            block = Block(
                id=new_id,
                type=block_type,
                x=pos.x(),
                y=pos.y()
            )
        elif block_type == BlockType.ASSIGN:
            block = Block(
                id=new_id,
                type=block_type,
                x=pos.x(),
                y=pos.y(),
                target="var0",
                source=Source(type="const", value=0),
                next=new_id + 1
            )
        elif block_type in (BlockType.INPUT, BlockType.PRINT):
            block = Block(
                id=new_id,
                type=block_type,
                x=pos.x(),
                y=pos.y(),
                io_var="var0",
                next=new_id + 1
            )
        elif block_type == BlockType.DECISION:
            block = Block(
                id=new_id,
                type=block_type,
                x=pos.x(),
                y=pos.y(),
                condition=Condition(var="var0", op="<", const=0),
                true_next=new_id + 1,
                false_next=new_id + 2
            )

        # Додаємо в модель потоку
        self.thread.add_block(block)

        # Створюємо візуальний елемент
        item = BlockItem(block)
        item.setPos(pos)
        self.addItem(item)
        self.block_items[new_id] = item

        self.block_changed.emit()

    def edit_block(self, item: BlockItem):
        dialog = BlockEditDialog(item.block, self.views()[0])
        if dialog.exec():
            new_block = dialog.get_block()
            self.thread.blocks[new_block.id] = new_block
            item.block = new_block
            item.param_text.setPlainText(item._get_param_text())
            self.block_changed.emit()

    def remove_block(self, item: BlockItem):
        """Видаляє блок + всі зв’язки до/від нього"""
        block_id = item.block.id

        if block_id in self.thread.blocks:
            del self.thread.blocks[block_id]

        self.removeItem(item)
        if block_id in self.block_items:
            del self.block_items[block_id]

        to_remove = []
        for conn in self.connections[:]:
            if (conn.start_item.block.id == block_id or
                conn.end_item.block.id == block_id):
                to_remove.append(conn)

        for conn in to_remove:
            self.removeItem(conn)
            self.connections.remove(conn)

        self.block_changed.emit()