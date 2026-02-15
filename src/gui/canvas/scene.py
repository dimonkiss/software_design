from PySide6.QtWidgets import QGraphicsScene, QGraphicsLineItem
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

        new_id = len(self.thread_model.blocks) + 1
        block_model = Block(id=new_id, type=block_type, pos_x=pos.x(), pos_y=pos.y())
        self.thread_model.blocks.append(block_model)

        item = BlockItem(block_model)
        self.addItem(item)
        return item

    # --- Обробка миші для створення зв'язків (ПРАВА КНОПКА) ---

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # Шукаємо блок під курсором
            item = self.itemAt(event.scenePos(), self.views()[0].transform())
            if isinstance(item, BlockItem):
                self.source_item = item
                # Створюємо тимчасову лінію
                self.temp_line = QGraphicsLineItem(QLineF(event.scenePos(), event.scenePos()))
                self.temp_line.setPen(QPen(Qt.black, 1, Qt.DashLine))
                self.addItem(self.temp_line)
                return  # Подію оброблено

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.temp_line and self.source_item:
            # Оновлюємо кінець тимчасової лінії
            line = QLineF(self.source_item.sceneBoundingRect().center(), event.scenePos())
            self.temp_line.setLine(line)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.temp_line and self.source_item:
            # Видаляємо тимчасову лінію
            self.removeItem(self.temp_line)
            self.temp_line = None

            # Перевіряємо, чи відпустили над іншим блоком
            end_item = self.itemAt(event.scenePos(), self.views()[0].transform())

            if isinstance(end_item, BlockItem) and end_item != self.source_item:
                self._create_connection(self.source_item, end_item)

            self.source_item = None
            return

        super().mouseReleaseEvent(event)

    def _create_connection(self, source: BlockItem, dest: BlockItem):
        """Створення графічного та логічного зв'язку."""
        # 1. Графічний зв'язок
        conn = ConnectionItem(source, dest)
        self.addItem(conn)

        # 2. Логічний зв'язок (оновлюємо модель)
        # Спрощено: завжди пишемо в next_id.
        # Для Decision треба буде вибирати true/false гілку пізніше.
        source.model.next_id = dest.model.id
        print(f"Connected Block {source.model.id} -> Block {dest.model.id}")