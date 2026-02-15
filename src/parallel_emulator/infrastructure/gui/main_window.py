from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QToolBar, QDockWidget,
                             QListWidget, QListWidgetItem, QMessageBox)
from PyQt6.QtCore import Qt

from src.parallel_emulator.application.services.project_service import ProjectService
from src.parallel_emulator.domain.entities.project import Project
from src.parallel_emulator.domain.entities.thread import Thread
from src.parallel_emulator.domain.enums.block_type import BlockType
from src.parallel_emulator.infrastructure.gui.editor.flowchart_scene import FlowchartScene
from src.parallel_emulator.infrastructure.gui.editor.flowchart_view import FlowchartView


class MainWindow(QMainWindow):
    def __init__(self, project_service: ProjectService, project: Project):
        super().__init__()
        self.service = project_service
        self.project = project
        self.tabs: dict[int, tuple[FlowchartScene, FlowchartView]] = {}

        self.setWindowTitle(f"Parallel Flowchart Emulator — {project.name}")
        self.resize(1400, 900)

        self._create_toolbar()
        self._create_palette_dock()
        self._create_central_widget()

        self._load_project()

    def _create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        toolbar.addAction("Новий проєкт", self.new_project)
        toolbar.addAction("Зберегти", self.save_project)
        toolbar.addSeparator()
        toolbar.addAction("Додати потік", self.add_thread)

    def _create_palette_dock(self):
        dock = QDockWidget("Палітра блоків", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.palette_list = QListWidget()
        for bt in ["START", "END", "ASSIGN", "INPUT", "PRINT", "DECISION"]:
            item = QListWidgetItem(bt)
            item.setData(Qt.ItemDataRole.UserRole, bt)
            self.palette_list.addItem(item)
        self.palette_list.itemDoubleClicked.connect(self._palette_double_click)
        dock.setWidget(self.palette_list)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

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
        idx = self.tab_widget.addTab(view, f"Thread {thread.id} — {thread.name}")
        self.tabs[thread.id] = (scene, view)
        self.tab_widget.setCurrentIndex(idx)

    def _palette_double_click(self, item):
        block_type_str = item.data(Qt.ItemDataRole.UserRole)
        block_type = BlockType[block_type_str]
        current_view = self.tab_widget.currentWidget()
        if isinstance(current_view, FlowchartView):
            scene = current_view.scene()
            pos = current_view.mapToScene(current_view.viewport().rect().center())
            scene.add_block(block_type, pos)

    def _on_project_changed(self):
        # можна додати autosave або просто позначити "змінено"
        pass

    def add_thread(self):
        new_id = max((t.id for t in self.project.threads), default=0) + 1
        thread = Thread(id=new_id, name=f"Thread {new_id}")
        self.project.add_thread(thread)
        self._add_thread_tab(thread)
        self.service.update_project(self.project)

    def close_thread_tab(self, index):
        thread_id = list(self.tabs.keys())[index]
        self.project.remove_thread(thread_id)
        del self.tabs[thread_id]
        self.tab_widget.removeTab(index)
        self.service.update_project(self.project)

    def save_project(self):
        self.service.update_project(self.project)
        QMessageBox.information(self, "Збережено", "Проєкт успішно збережено")

    def new_project(self):
        # реалізація пізніше
        pass