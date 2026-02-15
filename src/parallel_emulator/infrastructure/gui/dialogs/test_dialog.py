from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QFormLayout)


class TestDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Налаштування тесту")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.input_edit = QLineEdit("5 10 3")  # приклад
        self.expected_edit = QLineEdit("42 100")
        form.addRow("Вхідні дані (через пробіл):", self.input_edit)
        form.addRow("Очікуваний вивід (через пробіл):", self.expected_edit)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Запустити")
        cancel_btn = QPushButton("Скасувати")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def get_input(self):
        return [int(x) for x in self.input_edit.text().split() if x.strip()]

    def get_expected(self):
        return [int(x) for x in self.expected_edit.text().split() if x.strip()]