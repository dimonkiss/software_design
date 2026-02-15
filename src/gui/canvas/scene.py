from PySide6.QtWidgets import QGraphicsScene, QGraphicsLineItem, QGraphicsItem
from PySide6.QtCore import Qt, QPointF, QLineF
from PySide6.QtGui import QPen

from src.gui.canvas.items import BlockItem, ConnectionItem
from src.core.models import Block, ThreadModel


class CanvasScene(QGraphicsScene):
    def __init__(self):
        super().__init__(-2000, -2000, 4000, 4000)
        self.thread_model = None

        # Для створення зв'язків
        self.temp_line = None
        self.source_item = None

    def set_thread_model(self, model: ThreadModel):
        self.thread_model = model

    def add_block(self, block_type: str, pos: QPointF):
        if not self.thread_model: return

        # Генеруємо унікальний ID (максимальний існуючий + 1)
        if not self.thread_model.blocks:
            new_id = 1
        else:
            new_id = max(b.id for b in self.thread_model.blocks) + 1

        block_model = Block(id=new_id, type=block_type, pos_x=pos.x(), pos_y=pos.y())
        self.thread_model.blocks.append(block_model)

        item = BlockItem(block_model)
        self.addItem(item)
        return item

    # --- Обробка клавіатури (ВИДАЛЕННЯ) ---
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            self.delete_selected_items()
        else:
            super().keyPressEvent(event)

    def delete_selected_items(self):
        """Видаляє всі виділені блоки та зв'язки."""
        # Спочатку видаляємо зв'язки, щоб не було конфліктів
        for item in self.selectedItems():
            if isinstance(item, ConnectionItem):
                self._delete_connection(item)

        # Потім видаляємо блоки
        for item in self.selectedItems():
            if isinstance(item, BlockItem):
                self._delete_block(item)

    def _delete_connection(self, conn_item: ConnectionItem):
        # 1. Очищуємо логічний зв'язок у моделі Source блоку
        source_block = conn_item.source.model

        # Якщо цей зв'язок вів до наступного блоку, обнуляємо next_id
        if source_block.next_id == conn_item.dest.model.id:
            source_block.next_id = None
        if source_block.true_next_id == conn_item.dest.model.id:
            source_block.true_next_id = None
        if source_block.false_next_id == conn_item.dest.model.id:
            source_block.false_next_id = None

        # 2. Видаляємо графічний елемент
        conn_item.remove_self()

    def _delete_block(self, block_item: BlockItem):
        if not self.thread_model: return

        # 1. Спочатку видаляємо всі зв'язки, прикріплені до цього блоку
        # Робимо копію списку, бо ми будемо його змінювати під час ітерації
        for conn in block_item.connections[:]:
            self._delete_connection(conn)

        # 2. Видаляємо блок з моделі даних (ThreadModel)
        if block_item.model in self.thread_model.blocks:
            self.thread_model.blocks.remove(block_item.model)

        # 3. Видаляємо блок зі сцени
        self.removeItem(block_item)

    # --- Обробка миші (без змін) ---
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            item = self.itemAt(event.scenePos(), self.views()[0].transform())
            if isinstance(item, BlockItem):
                self.source_item = item
                self.temp_line = QGraphicsLineItem(QLineF(event.scenePos(), event.scenePos()))
                self.temp_line.setPen(QPen(Qt.black, 1, Qt.DashLine))
                self.addItem(self.temp_line)
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.temp_line and self.source_item:
            line = QLineF(self.source_item.sceneBoundingRect().center(), event.scenePos())
            self.temp_line.setLine(line)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.temp_line and self.source_item:
            self.removeItem(self.temp_line)
            self.temp_line = None

            end_item = self.itemAt(event.scenePos(), self.views()[0].transform())

            if isinstance(end_item, BlockItem) and end_item != self.source_item:
                self._create_connection(self.source_item, end_item)

            self.source_item = None
            return

        super().mouseReleaseEvent(event)

    def _create_connection(self, source: BlockItem, dest: BlockItem):
        conn = ConnectionItem(source, dest)
        self.addItem(conn)
        source.model.next_id = dest.model.id
        print(f"Connected Block {source.model.id} -> Block {dest.model.id}")