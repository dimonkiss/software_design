from dataclasses import replace
from typing import Dict
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QTimer
from PyQt6.QtGui import QPen, QColor
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
        self._rubber_line = None
        self._connection_start = None
        self._is_true_branch = False
        self._pending_delete_conns: list[ConnectionItem] = []

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

    def start_connection(self, from_item: BlockItem, is_true: bool = False):
        print("СТАРТ ЗВ'ЯЗКУ від блоку", from_item.block.id)  # DEBUG
        self._connection_start = from_item
        self._is_true_branch = is_true

        start_pos = self._get_port_position(from_item, is_true)
        self._rubber_line = self.addLine(
            start_pos.x(), start_pos.y(),
            start_pos.x(), start_pos.y(),
            QPen(QColor(100, 180, 255), 4, Qt.PenStyle.DashLine)
        )
        self.update()

    def _get_port_position(self, item: BlockItem, is_true: bool) -> QPointF:
        if item.block.type == BlockType.DECISION:
            if is_true and item.true_port:
                return item.pos() + item.true_port.pos() + item.true_port.rect().center()
            if item.false_port:
                return item.pos() + item.false_port.pos() + item.false_port.rect().center()
        if item.out_port:
            return item.pos() + item.out_port.pos() + item.out_port.rect().center()
        return item.pos() + QPointF(70, 60)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self._rubber_line is not None:
            print("Оновлюю стрілку")  # DEBUG
            start_pos = self._get_port_position(self._connection_start, self._is_true_branch)
            self._rubber_line.setLine(
                start_pos.x(), start_pos.y(),
                event.scenePos().x(), event.scenePos().y()
            )
        super().mouseMoveEvent(event)

    def finish_connection(self, to_item: BlockItem):
        print("ФІНІШ ЗВ'ЯЗКУ на блоку", to_item.block.id)  # DEBUG
        if self._connection_start is None:
            return

        if to_item == self._connection_start:
            self._cancel_connection()
            return

        self._create_connection(self._connection_start, to_item, self._is_true_branch)
        self._cancel_connection()

    def _cancel_connection(self):
        print("СКАСУВАННЯ")  # DEBUG
        if self._rubber_line is not None:
            self.removeItem(self._rubber_line)
            self._rubber_line = None
        self._connection_start = None

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        item = self.itemAt(event.scenePos(), self.views()[0].transform())

        if self._connection_start is not None and item is None:
            print("Клік на порожнє місце — скасування")
            self._cancel_connection()

        super().mousePressEvent(event)

    def _create_connection(self, from_item: BlockItem, to_item: BlockItem, is_true: bool):
        print("ФІКСАЦІЯ ПОСТІЙНОЇ СТРІЛКИ від", from_item.block.id, "до", to_item.block.id)

        from_block = from_item.block
        to_id = to_item.block.id

        if from_block.type == BlockType.DECISION:
            new_block = replace(from_block,
                                true_next=to_id if is_true else from_block.true_next,
                                false_next=to_id if not is_true else from_block.false_next)
        else:
            new_block = replace(from_block, next=to_id)

        self.thread.blocks[from_block.id] = new_block
        from_item.block = new_block

        conn = ConnectionItem(from_item, to_item, is_true)
        self.addItem(conn)
        self.connections.append(conn)
        print("Стрілка додана, всього:", len(self.connections))
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
        print("ВИДАЛЕННЯ БЛОКУ", item.block.id)
        block_id = item.block.id

        for b in list(self.thread.blocks.values()):
            updated = False
            if b.next == block_id:
                b = replace(b, next=None)
                updated = True
            if b.type == BlockType.DECISION:
                if b.true_next == block_id:
                    b = replace(b, true_next=None)
                    updated = True
                if b.false_next == block_id:
                    b = replace(b, false_next=None)
                    updated = True
            if updated:
                self.thread.blocks[b.id] = b
                if b.id in self.block_items:
                    self.block_items[b.id].block = b
                    # Оновлюємо стрілки
                    for conn in self.connections:
                        if conn.from_item.block.id == b.id:
                            conn.update_position()

        to_remove = [conn for conn in self.connections if conn.from_item == item or conn.to_item == item]
        for conn in to_remove:
            self.removeItem(conn)
            self.connections.remove(conn)

        del self.thread.blocks[block_id]
        self.removeItem(item)
        del self.block_items[block_id]

        self.block_changed.emit()

    def on_block_moved(self, item: BlockItem):
        for conn in self.connections:
            if conn.from_item == item or conn.to_item == item:
                conn.update_position()