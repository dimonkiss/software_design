from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QAction
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QToolBar, QDockWidget, QListWidget, QListWidgetItem,
    QMessageBox, QStatusBar, QProgressBar, QInputDialog
)

from src.parallel_emulator.application.services.project_service import ProjectService
from src.parallel_emulator.domain.entities.project import Project
from src.parallel_emulator.domain.entities.thread import Thread
from src.parallel_emulator.infrastructure.gui.dialogs.test_dialog import TestDialog
from src.parallel_emulator.infrastructure.gui.editor.flowchart_scene import FlowchartScene
from src.parallel_emulator.infrastructure.gui.editor.flowchart_view import FlowchartView
from src.parallel_emulator.infrastructure.gui.simulation_thread import SimulationThread
from src.parallel_emulator.domain.enums.block_type import BlockType


class MainWindow(QMainWindow):
    def __init__(self, project_service: ProjectService, project: Project):
        super().__init__()
        self.service = project_service
        self.project = project
        self.tabs: dict[int, tuple[FlowchartScene, FlowchartView]] = {}
        self.sim_thread: SimulationThread | None = None

        self.setWindowTitle(f"Parallel Flowchart Emulator — {project.name}")
        self.resize(1600, 900)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.progress = QProgressBar()
        self.statusBar.addPermanentWidget(self.progress)
        self.progress.hide()

        self._create_toolbar()
        self._create_palette_dock()
        self._create_central_widget()
        self._load_project()

    # ==================== TOOLBAR ====================
    def _create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        toolbar.addAction("Новий проєкт", self.new_project)
        toolbar.addAction("Зберегти", self.save_project)
        toolbar.addSeparator()
        toolbar.addAction("Додати потік", self.add_thread)
        toolbar.addSeparator()

        self.run_action = QAction("▶ Запустити тест", self)
        self.run_action.triggered.connect(self.run_test)
        toolbar.addAction(self.run_action)

        self.stop_action = QAction("⏹ Стоп", self)
        self.stop_action.setEnabled(False)
        self.stop_action.triggered.connect(self.stop_test)
        toolbar.addAction(self.stop_action)

    # ==================== ПАЛІТРА (з drag & drop) ====================
    def _create_palette_dock(self):
        dock = QDockWidget("Палітра блоків", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        self.palette_list = QListWidget()
        self.palette_list.setDragEnabled(True)
        self.palette_list.setDragDropMode(QListWidget.DragDropMode.DragOnly)

        for name in ["START", "END", "ASSIGN", "INPUT", "PRINT", "DECISION"]:
            item = QListWidgetItem(name)
            self.palette_list.addItem(item)

        self.palette_list.itemDoubleClicked.connect(self._palette_double_click)  # запасний варіант
        dock.setWidget(self.palette_list)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

    # ==================== ЦЕНТРАЛЬНА ЧАСТИНА ====================
    def _create_central_widget(self):
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_thread_tab)
        self.setCentralWidget(self.tab_widget)

    def _load_project(self):
        self.tab_widget.clear()
        self.tabs.clear()
        for thread in self.project.threads:
            self._add_thread_tab(thread)

    def _add_thread_tab(self, thread: Thread):
        scene = FlowchartScene(thread)
        scene.block_changed.connect(self._on_project_changed)

        view = FlowchartView(scene)
        view.setBackgroundBrush(QColor(35, 35, 35))   # щоб було видно полотно

        idx = self.tab_widget.addTab(view, f"Потік {thread.id}")
        self.tabs[thread.id] = (scene, view)
        self.tab_widget.setCurrentIndex(idx)

    # ==================== ДРАГ З ПАЛІТРИ ====================
    def _palette_double_click(self, item: QListWidgetItem):
        block_type_str = item.text().strip().upper()
        try:
            block_type = BlockType[block_type_str]

            current_view = self.tab_widget.currentWidget()
            if not isinstance(current_view, FlowchartView):
                return

            scene = current_view.scene()
            pos = current_view.mapToScene(current_view.viewport().rect().center())
            scene.add_block(block_type, pos)

        except Exception as e:
            QMessageBox.warning(self, "Не вдалося додати блок",
                                f"Блок {block_type_str} не вдалося створити:\n{str(e)}")
    # ==================== РЕШТА МЕТОДІВ ====================
    def add_thread(self):
        new_id = max((t.id for t in self.project.threads), default=0) + 1
        thread = Thread(id=new_id, name=f"Потік {new_id}")
        self.project.add_thread(thread)
        self._add_thread_tab(thread)
        self.service.update_project(self.project)

    def close_thread_tab(self, index: int):
        thread_id = list(self.tabs.keys())[index]
        self.project.remove_thread(thread_id)
        del self.tabs[thread_id]
        self.tab_widget.removeTab(index)
        self.service.update_project(self.project)

    def save_project(self):
        self.service.update_project(self.project)
        QMessageBox.information(self, "Збережено", "Проєкт збережено")

    def new_project(self):
        QMessageBox.information(self, "Новий проєкт", "Функція в розробці")

    def _on_project_changed(self):
        pass  # можна додати autosave пізніше

    # ==================== ТЕСТУВАННЯ ====================
    def run_test(self):
        dialog = TestDialog(self)
        if dialog.exec():
            input_data = dialog.get_input()
            expected = dialog.get_expected()

            self.statusBar.showMessage("Запуск емуляції...")
            self.progress.show()
            self.run_action.setEnabled(False)
            self.stop_action.setEnabled(True)

            self.sim_thread = SimulationThread(self.project, input_data, expected)
            self.sim_thread.finished.connect(self.on_simulation_finished)
            self.sim_thread.stopped.connect(self.on_simulation_stopped)
            self.sim_thread.start()

    def stop_test(self):
        if self.sim_thread:
            self.sim_thread.stop()

    def on_simulation_finished(self, success: bool, message: str):
        self._cleanup()
        QMessageBox.information(self, "Результат", message)
        self._ask_for_k()

    def on_simulation_stopped(self):
        self._cleanup()
        self._ask_for_k()

    def _cleanup(self):
        self.run_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.progress.hide()
        self.sim_thread = None

    def _ask_for_k(self):
        k, ok = QInputDialog.getInt(self, "Метрика K", "Введіть K (1-20):", 5, 1, 20)
        if ok and self.sim_thread and self.sim_thread.search:
            percent = self.sim_thread.search.get_coverage_percent(k)
            checked = self.sim_thread.search.get_checked_paths_up_to_k(k)
            total = self.sim_thread.search.calculate_total_paths_up_to_k(k)
            msg = f"Перевірено {checked}/{total} шляхів\nВідсоток: {percent:.2f}%"
            QMessageBox.information(self, f"K = {k}", msg)