from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QComboBox,
                               QSpinBox, QLabel, QGroupBox)

from src.core.models import MAX_VAL, MIN_VAL


class PropertyEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_block_item = None

        self.layout = QVBoxLayout(self)

        self.group_box = QGroupBox("Параметри блоку")
        self.form_layout = QFormLayout()
        self.group_box.setLayout(self.form_layout)

        self.layout.addWidget(self.group_box)
        self.layout.addStretch()

    def set_block(self, block_item):
        self.current_block_item = block_item
        self._clear_layout()

        if not block_item:
            self.form_layout.addRow(QLabel("Не вибрано жодного блоку"))
            return

        model = block_item.model
        self.form_layout.addRow("ID:", QLabel(str(model.id)))
        self.form_layout.addRow("Тип:", QLabel(model.type))

        # --- ASSIGN (V = C або V = V) ---
        if model.type == 'ASSIGN':
            self._add_var_selector("Цільова змінна (V1):", "target_var")

            # Вибір типу джерела: Константа чи Змінна
            src_type_combo = QComboBox()
            src_type_combo.addItems(["Константа (C)", "Змінна (V2)"])

            # Визначаємо поточний стан: якщо є src_var, то це режим "Змінна"
            if model.src_var:
                src_type_combo.setCurrentIndex(1)
            else:
                src_type_combo.setCurrentIndex(0)

            self.form_layout.addRow("Тип присвоєння:", src_type_combo)

            # Створюємо віджети для обох варіантів
            # 1. Спінбокс для константи
            self.val_spin = QSpinBox()
            self.val_spin.setRange(MIN_VAL, MAX_VAL)
            self.val_spin.setValue(model.value if model.value is not None else 0)
            self.val_spin.valueChanged.connect(
                lambda val: setattr(self.current_block_item.model, 'value', val)
            )

            # 2. Комбобокс для змінної-джерела
            self.src_var_combo = QComboBox()
            self.src_var_combo.addItems([f"var{i}" for i in range(100)])  # 100 змінних
            if model.src_var:
                self.src_var_combo.setCurrentText(model.src_var)
            self.src_var_combo.currentTextChanged.connect(
                lambda val: setattr(self.current_block_item.model, 'src_var', val)
            )

            # Додаємо обидва поля в layout, але сховаємо непотрібне
            self.form_layout.addRow("Значення (C):", self.val_spin)
            self.form_layout.addRow("Джерело (V2):", self.src_var_combo)

            # Логіка перемикання
            def update_visibility(index):
                if index == 0:  # Constant
                    self.val_spin.setVisible(True)
                    self.src_var_combo.setVisible(False)
                    # Очищаємо src_var в моделі, щоб генератор знав, що це константа
                    self.current_block_item.model.src_var = None
                    # Відновлюємо лейбл (QFormLayout іноді ховає і лейбли)
                    self.form_layout.labelForField(self.val_spin).setVisible(True)
                    self.form_layout.labelForField(self.src_var_combo).setVisible(False)
                else:  # Variable
                    self.val_spin.setVisible(False)
                    self.src_var_combo.setVisible(True)
                    # Записуємо поточне значення з комбобокса в модель
                    self.current_block_item.model.src_var = self.src_var_combo.currentText()

                    self.form_layout.labelForField(self.val_spin).setVisible(False)
                    self.form_layout.labelForField(self.src_var_combo).setVisible(True)

            src_type_combo.currentIndexChanged.connect(update_visibility)

            # Ініціалізація стану
            update_visibility(src_type_combo.currentIndex())

        # --- DECISION ---
        elif model.type == 'DECISION':
            self._add_var_selector("Змінна (V):", "target_var")
            self._add_operator_selector()
            self._add_value_input("Порівняти з (C):")  # ТЗ вимагає порівняння з константою

        # --- INPUT / PRINT ---
        elif model.type in ('INPUT', 'PRINT'):
            self._add_var_selector("Змінна:", "target_var")

    def _clear_layout(self):
        while self.form_layout.count():
            child = self.form_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _add_var_selector(self, label_text, attr_name):
        combo = QComboBox()
        # ТЗ: до 100 змінних
        vars_list = [f"var{i}" for i in range(100)]
        combo.addItems(vars_list)

        current_val = getattr(self.current_block_item.model, attr_name)
        if current_val:
            combo.setCurrentText(current_val)
        else:
            setattr(self.current_block_item.model, attr_name, "var0")

        combo.currentTextChanged.connect(
            lambda val: setattr(self.current_block_item.model, attr_name, val)
        )
        self.form_layout.addRow(label_text, combo)

    def _add_value_input(self, label_text):
        spin = QSpinBox()
        spin.setRange(MIN_VAL, MAX_VAL)
        val = self.current_block_item.model.value
        spin.setValue(val if val is not None else 0)
        spin.valueChanged.connect(
            lambda val: setattr(self.current_block_item.model, 'value', val)
        )
        self.form_layout.addRow(label_text, spin)

    def _add_operator_selector(self):
        combo = QComboBox()
        combo.addItems(["==", "<"])
        current_op = self.current_block_item.model.operator
        combo.setCurrentText(current_op if current_op else "==")
        combo.currentTextChanged.connect(
            lambda val: setattr(self.current_block_item.model, 'operator', val)
        )
        self.form_layout.addRow("Оператор:", combo)