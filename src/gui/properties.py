from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QComboBox,
                               QSpinBox, QLabel, QGroupBox)
from src.core.models import MAX_VAL, MIN_VAL


class PropertyEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_block_item = None

        # Основний лейаут
        self.layout = QVBoxLayout(self)

        # Група полів
        self.group_box = QGroupBox("Параметри блоку")
        self.form_layout = QFormLayout()
        self.group_box.setLayout(self.form_layout)

        self.layout.addWidget(self.group_box)
        self.layout.addStretch()  # Притискаємо форму до верху

    def set_block(self, block_item):
        """Викликається головним вікном при кліку на блок."""
        self.current_block_item = block_item
        self._clear_layout()

        if not block_item:
            self.form_layout.addRow(QLabel("Не вибрано жодного блоку"))
            return

        model = block_item.model
        self.form_layout.addRow("ID:", QLabel(str(model.id)))
        self.form_layout.addRow("Тип:", QLabel(model.type))

        # --- Генерація полів залежно від типу ---

        # 1. Поля для ASSIGN (V = C або V1 = V2)
        if model.type == 'ASSIGN':
            self._add_var_selector("Цільова змінна:", "target_var")
            self._add_value_input("Значення (Const):")
            # Можна додати перемикач на src_var, але поки спростимо до Const

        # 2. Поля для DECISION (V < C або V == C)
        elif model.type == 'DECISION':
            self._add_var_selector("Змінна (Ліва частина):", "target_var")
            self._add_operator_selector()
            self._add_value_input("Порівняти з (Права частина):")

        # 3. Поля для INPUT / PRINT
        elif model.type in ('INPUT', 'PRINT'):
            self._add_var_selector("Змінна:", "target_var")

    def _clear_layout(self):
        """Очищує форму перед малюванням нових полів."""
        while self.form_layout.count():
            child = self.form_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _add_var_selector(self, label_text, attr_name):
        """Створює випадаючий список змінних var0..var99."""
        combo = QComboBox()
        vars_list = [f"var{i}" for i in range(20)]  # Обмежимо список для зручності
        combo.addItems(vars_list)

        # Встановлюємо поточне значення з моделі
        current_val = getattr(self.current_block_item.model, attr_name)
        if current_val:
            combo.setCurrentText(current_val)
        else:
            # Якщо пусто, ставимо перше значення і зберігаємо в модель
            setattr(self.current_block_item.model, attr_name, "var0")

        # При зміні оновлюємо модель
        combo.currentTextChanged.connect(
            lambda val: setattr(self.current_block_item.model, attr_name, val)
        )
        self.form_layout.addRow(label_text, combo)

    def _add_value_input(self, label_text):
        """Створює поле вводу числа з валідацією."""
        spin = QSpinBox()
        spin.setRange(MIN_VAL, MAX_VAL)  # 0 ... 2^31-1

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