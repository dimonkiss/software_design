from PySide6.QtWidgets import (QMainWindow, QTabWidget, QDockWidget,
                               QMessageBox, QToolBar, QStyle)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

from src.gui.execution_window import ExecutionWindow
from src.gui.widgets.thread_tab import ThreadTab
from src.gui.properties import PropertyEditor
from src.core.models import Project, ThreadModel
from src.gui.canvas.items import BlockItem
from PySide6.QtWidgets import QTextEdit, QDialog, QVBoxLayout, QPushButton, QFileDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MultiThread Flow Translator")
        self.resize(1200, 800)

        # Головна структура даних
        self.project = Project()

        # 1. Центральний віджет (Вкладки)
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_thread_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.setCentralWidget(self.tab_widget)

        # 2. Док-станція (Властивості)
        self.property_editor = PropertyEditor()
        self.prop_dock = QDockWidget("Властивості", self)
        self.prop_dock.setWidget(self.property_editor)
        self.addDockWidget(Qt.RightDockWidgetArea, self.prop_dock)

        # 3. Меню та Тулбар
        self._setup_ui()

        # Створюємо початковий потік
        self.add_new_thread()

    def _setup_ui(self):
        # 1. Створення дій (Actions)

        # Дія: Додати потік
        add_thread_act = QAction(self.style().standardIcon(QStyle.SP_FileIcon), "Додати потік", self)
        add_thread_act.setShortcut("Ctrl+T")
        add_thread_act.triggered.connect(self.add_new_thread)

        # Дія: Транслювати (Генерувати код)
        run_act = QAction(self.style().standardIcon(QStyle.SP_MediaPlay), "Транслювати", self)
        run_act.setShortcut("F5")
        run_act.triggered.connect(self.run_translation)

        # 2. Налаштування Меню (Верхня смужка: Файл, Інструменти...)
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Файл")
        file_menu.addAction(add_thread_act)
        file_menu.addAction(run_act)
        file_menu.addSeparator()
        file_menu.addAction("Вихід", self.close)

        # 3. Налаштування Панелі інструментів (Toolbar)
        toolbar = QToolBar("Інструменти")
        self.addToolBar(toolbar)

        toolbar.addAction(add_thread_act)
        toolbar.addAction(run_act)  # <--- ОСЬ ТУТ МИ ДОДАЄМО КНОПКУ!

        toolbar.addSeparator()

        # Кнопки додавання блоків
        for b_type in ["START", "ASSIGN", "DECISION", "INPUT", "PRINT", "END"]:
            act = QAction(f"+ {b_type}", self)
            act.triggered.connect(lambda checked=False, t=b_type: self.add_block_to_current(t))
            toolbar.addAction(act)

    def add_new_thread(self):
        if len(self.project.threads) >= 100:
            QMessageBox.warning(self, "Ліміт", "Максимум 100 потоків!")
            return

        new_id = len(self.project.threads) + 1
        model = ThreadModel(id=new_id, name=f"Thread {new_id}")
        self.project.threads.append(model)

        tab = ThreadTab(model)
        # Підписуємось на виділення у сцені цієї вкладки
        tab.view.scene.selectionChanged.connect(self.on_selection_changed)

        self.tab_widget.addTab(tab, model.name)
        self.tab_widget.setCurrentWidget(tab)

    def close_thread_tab(self, index):
        if self.tab_widget.count() <= 1:
            return
        self.tab_widget.removeTab(index)
        # Примітка: видалення з self.project.threads потребує обережності з ID,
        # тут спрощено.

    def add_block_to_current(self, block_type):
        """Додає блок у поточну активну вкладку."""
        current_tab = self.tab_widget.currentWidget()
        if current_tab:
            # Додаємо трохи зміщення, щоб блоки не накладалися
            pos_x = 50 + len(current_tab.thread_model.blocks) * 20
            pos_y = 50 + len(current_tab.thread_model.blocks) * 20

            # Викликаємо метод сцени (через view)
            from PySide6.QtCore import QPointF
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
        # Перевіряємо, чи це BlockItem (а не стрілка ConnectionItem)
        if isinstance(item, BlockItem):
            self.property_editor.set_block(item)
        else:
            self.property_editor.set_block(None)

    def run_translation(self):
        if not self.project.threads:
            return

        exec_window = ExecutionWindow(self.project, self)
        exec_window.exec()

    def _show_code_dialog(self, code):
        dialog = QDialog(self)
        dialog.setWindowTitle("Згенерований код Python")
        dialog.resize(600, 500)

        layout = QVBoxLayout(dialog)

        text_edit = QTextEdit()
        text_edit.setPlainText(code)
        text_edit.setReadOnly(True)
        text_edit.setFontFamily("Consolas")  # Або "Courier New"
        layout.addWidget(text_edit)

        btn_save = QPushButton("Зберегти у файл...")
        btn_save.clicked.connect(lambda: self._save_code_to_file(code))
        layout.addWidget(btn_save)

        dialog.exec()

    def _save_code_to_file(self, code):
        filename, _ = QFileDialog.getSaveFileName(self, "Зберегти Python файл", "", "Python Files (*.py)")
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(code)