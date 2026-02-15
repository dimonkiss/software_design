import os

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QMainWindow, QTabWidget, QDockWidget,
                               QMessageBox, QToolBar, QStyle, QFileDialog)

from src.core.models import Project, ThreadModel
from src.core.serializer import ProjectSerializer
from src.core.validator import ProjectValidator
from src.gui.canvas.items import BlockItem, ConnectionItem
from src.gui.execution_window import ExecutionWindow
from src.gui.properties import PropertyEditor
from src.gui.widgets.thread_tab import ThreadTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MultiThread Flow Translator")
        self.resize(1200, 800)

        self.project = Project()

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_thread_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.setCentralWidget(self.tab_widget)

        self.property_editor = PropertyEditor()
        self.prop_dock = QDockWidget("Властивості", self)
        self.prop_dock.setWidget(self.property_editor)
        self.addDockWidget(Qt.RightDockWidgetArea, self.prop_dock)

        self._setup_ui()

        if not self.project.threads:
            self.add_new_thread()

    def _setup_ui(self):
        save_act = QAction("Зберегти проект...", self)
        save_act.setShortcut("Ctrl+S")
        save_act.triggered.connect(self.save_project)

        load_act = QAction("Відкрити проект...", self)
        load_act.setShortcut("Ctrl+O")
        load_act.triggered.connect(self.load_project)

        add_thread_act = QAction(self.style().standardIcon(QStyle.SP_FileIcon), "Додати потік", self)
        add_thread_act.setShortcut("Ctrl+T")
        add_thread_act.triggered.connect(self.add_new_thread)

        run_act = QAction(self.style().standardIcon(QStyle.SP_MediaPlay), "Транслювати", self)
        run_act.setShortcut("F5")
        run_act.triggered.connect(self.run_translation)

        menubar = self.menuBar()

        file_menu = menubar.addMenu("Файл")
        file_menu.addAction(add_thread_act)
        file_menu.addSeparator()
        file_menu.addAction(save_act)
        file_menu.addAction(load_act)
        file_menu.addSeparator()
        file_menu.addAction("Вихід", self.close)

        toolbar = QToolBar("Інструменти")
        self.addToolBar(toolbar)

        toolbar.addAction(add_thread_act)
        toolbar.addAction(save_act)
        toolbar.addAction(load_act)
        toolbar.addSeparator()
        toolbar.addAction(run_act)

        toolbar.addSeparator()

        for b_type in ["START", "ASSIGN", "DECISION", "INPUT", "PRINT", "END"]:
            act = QAction(f"+ {b_type}", self)
            act.triggered.connect(lambda checked=False, t=b_type: self.add_block_to_current(t))
            toolbar.addAction(act)

    def add_new_thread(self):
        if len(self.project.threads) >= 100:
            QMessageBox.warning(self, "Ліміт", "Максимум 100 потоків!")
            return

        if self.project.threads:
            new_id = max(t.id for t in self.project.threads) + 1
        else:
            new_id = 1

        model = ThreadModel(id=new_id, name=f"Thread {new_id}")
        self.project.threads.append(model)

        tab = ThreadTab(model)
        tab.view.scene.selectionChanged.connect(self.on_selection_changed)

        self.tab_widget.addTab(tab, model.name)
        self.tab_widget.setCurrentWidget(tab)

    def close_thread_tab(self, index):
        if self.tab_widget.count() <= 1:
            QMessageBox.warning(self, "Увага", "Проект повинен мати мінімум 1 потік!")
            return

        self.tab_widget.removeTab(index)
        if index < len(self.project.threads):
            self.project.threads.pop(index)

    def add_block_to_current(self, block_type):
        current_tab = self.tab_widget.currentWidget()
        if current_tab:
            offset = len(current_tab.thread_model.blocks) * 20
            pos_x = 50 + offset
            pos_y = 50 + offset

            current_tab.view.scene.add_block(block_type, QPointF(pos_x, pos_y))

    def on_tab_changed(self, index):
        self.on_selection_changed()

    def on_selection_changed(self):
        """Оновлює панель властивостей при кліку."""
        current_tab = self.tab_widget.currentWidget()
        if not current_tab: return

        selected = current_tab.view.scene.selectedItems()
        if not selected:
            self.property_editor.set_block(None)
            return

        item = selected[0]
        if isinstance(item, BlockItem):
            self.property_editor.set_block(item)
        else:
            self.property_editor.set_block(None)

    def run_translation(self):
        is_valid, errors = ProjectValidator.validate(self.project)

        if not is_valid:
            msg_text = "Знайдено помилки у проекті:\n"
            for err in errors[:10]:
                msg_text += f"- {err}\n"
            if len(errors) > 10:
                msg_text += f"... і ще {len(errors) - 10} помилок."

            QMessageBox.critical(self, "Помилка валідації", msg_text)
            return

        exec_window = ExecutionWindow(self.project, self)
        exec_window.exec()

    def save_project(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Зберегти проект", "", "JSON Files (*.json)"
        )
        if not file_path:
            return

        try:
            json_data = ProjectSerializer.serialize(self.project)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_data)
            self.statusBar().showMessage(f"Проект збережено: {os.path.basename(file_path)}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Помилка збереження", str(e))

    def load_project(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Відкрити проект", "", "JSON Files (*.json)"
        )
        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = f.read()

            new_project = ProjectSerializer.deserialize(json_data)
            self._rebuild_gui_from_project(new_project)

            self.statusBar().showMessage(f"Проект завантажено: {os.path.basename(file_path)}", 3000)

        except Exception as e:
            QMessageBox.critical(self, "Помилка завантаження", f"Не вдалося відкрити файл:\n{e}")

    def _rebuild_gui_from_project(self, new_project):
        """Перебудовує GUI на основі завантаженого проекту."""
        self.tab_widget.clear()
        self.project = new_project
        self.property_editor.set_block(None)

        for thread in self.project.threads:
            tab = ThreadTab(thread)
            tab.view.scene.selectionChanged.connect(self.on_selection_changed)
            self.tab_widget.addTab(tab, thread.name)

            scene = tab.view.scene
            id_to_item_map = {}

            for block_model in thread.blocks:
                item = BlockItem(block_model)
                scene.addItem(item)
                id_to_item_map[block_model.id] = item

            for block_model in thread.blocks:
                source_item = id_to_item_map.get(block_model.id)
                if not source_item: continue

                def connect_items(target_id):
                    if target_id is None: return
                    dest_item = id_to_item_map.get(target_id)
                    if dest_item:
                        conn = ConnectionItem(source_item, dest_item)
                        scene.addItem(conn)

                connect_items(block_model.next_id)
                connect_items(block_model.true_next_id)
                connect_items(block_model.false_next_id)

        if self.tab_widget.count() == 0:
            self.add_new_thread()