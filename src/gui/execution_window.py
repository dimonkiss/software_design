from PySide6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QPushButton, QHBoxLayout
from PySide6.QtCore import QThread

from src.gui.widgets.interpreter import InterpreterWorker
from src.gui.widgets.terminal import TerminalWidget


class ExecutionWindow(QDialog):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Виконання Програми (Simulation)")
        self.resize(800, 600)
        self.project = project
        self.terminals = {}  # {thread_id: TerminalWidget}

        self.layout = QVBoxLayout(self)

        # 1. Область Терміналів (Вкладки)
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # Створюємо термінал для кожного потоку
        for thread in self.project.threads:
            term = TerminalWidget(thread.name)
            self.terminals[thread.id] = term
            self.tabs.addTab(term, thread.name)

        # 2. Кнопки управління
        btn_layout = QHBoxLayout()
        self.btn_stop = QPushButton("Зупинити")
        self.btn_stop.clicked.connect(self.stop_execution)
        self.btn_close = QPushButton("Закрити")
        self.btn_close.clicked.connect(self.close)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addWidget(self.btn_close)
        self.layout.addLayout(btn_layout)

        # 3. Запуск інтерпретатора в окремому потоці QThread
        self.worker_thread = QThread()
        self.worker = InterpreterWorker(self.project)
        self.worker.moveToThread(self.worker_thread)

        # З'єднання сигналів
        self.worker_thread.started.connect(self.worker.run)
        self.worker.sig_print.connect(self.on_print)
        self.worker.sig_finished.connect(self.on_finished)
        self.worker.sig_finished.connect(self.worker_thread.quit)
        self.worker.sig_finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        # Старт
        self.worker_thread.start()

    def on_print(self, thread_id, text):
        if thread_id in self.terminals:
            self.terminals[thread_id].print_text(text)

    def on_finished(self):
        self.btn_stop.setEnabled(False)
        self.btn_stop.setText("Виконання завершено")

    def stop_execution(self):
        if self.worker:
            self.worker.stop()
            self.terminals[self.project.threads[0].id].print_text("\n--- FORCED STOP ---")

    def closeEvent(self, event):
        self.stop_execution()
        super().closeEvent(event)