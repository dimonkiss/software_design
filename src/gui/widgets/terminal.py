from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel


class TerminalWidget(QWidget):
    def __init__(self, thread_name):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок
        self.header = QLabel(f"Console: {thread_name}")
        self.header.setStyleSheet("background-color: #333; color: white; padding: 5px; font-weight: bold;")
        self.layout.addWidget(self.header)

        # Текстове поле (Log)
        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                border: none;
            }
        """)
        self.layout.addWidget(self.output_area)

    def print_text(self, text):
        """Додає текст у консоль."""
        self.output_area.append(str(text))
        # Автоскрол вниз
        sb = self.output_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clear(self):
        self.output_area.clear()