from dataclasses import replace

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
                             QSpinBox, QDialogButtonBox, QHBoxLayout)

from src.parallel_emulator.domain.entities.block import Block
from src.parallel_emulator.domain.enums.block_type import BlockType
from src.parallel_emulator.domain.value_objects.condition import Condition
from src.parallel_emulator.domain.value_objects.source import Source


class BlockEditDialog(QDialog):
    def __init__(self, block: Block, parent=None):
        super().__init__(parent)
        self.block = block
        self.setWindowTitle("Редагування блоку")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        if block.type == BlockType.ASSIGN:
            # Target (змінна, куди присвоювати)
            self.target_edit = QLineEdit(block.target or "var0")
            form.addRow("Target (змінна):", self.target_edit)

            # Source type
            self.source_type = QComboBox()
            self.source_type.addItems(["const", "var"])
            current_type = block.source.type if block.source else "const"
            self.source_type.setCurrentText(current_type)
            form.addRow("Source type:", self.source_type)

            # Динамічне поле для value
            self.source_value_layout = QHBoxLayout()
            self.source_value_widget = self._create_source_widget(current_type, block.source.value if block.source else 0)
            self.source_value_layout.addWidget(self.source_value_widget)
            form.addRow("Source value:", self.source_value_layout)

            # Зміна типу — міняємо widget
            self.source_type.currentTextChanged.connect(self._on_source_type_changed)

        elif block.type in (BlockType.INPUT, BlockType.PRINT):
            self.io_var = QLineEdit(block.io_var or "var0")
            form.addRow("Змінна:", self.io_var)

        elif block.type == BlockType.DECISION:
            self.cond_var = QLineEdit(block.condition.var if block.condition else "var0")
            self.cond_op = QComboBox()
            self.cond_op.addItems(["==", "<"])
            self.cond_op.setCurrentText(block.condition.op if block.condition else "==")
            self.cond_const = QSpinBox()
            self.cond_const.setRange(0, 2**31 - 1)
            self.cond_const.setValue(block.condition.const if block.condition else 0)
            form.addRow("Змінна:", self.cond_var)
            form.addRow("Оператор:", self.cond_op)
            form.addRow("Константа:", self.cond_const)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _create_source_widget(self, source_type: str, current_value):
        if source_type == "const":
            widget = QSpinBox()
            widget.setRange(0, 2**31 - 1)
            widget.setValue(current_value if isinstance(current_value, int) else 0)
            return widget
        else:
            widget = QLineEdit()
            widget.setText(str(current_value) if current_value else "var0")
            return widget

    def _on_source_type_changed(self, text):
        old_widget = self.source_value_widget
        new_widget = self._create_source_widget(text, 0 if text == "const" else "var0")
        self.source_value_layout.replaceWidget(old_widget, new_widget)
        old_widget.deleteLater()
        self.source_value_widget = new_widget

    def get_block(self) -> Block:
        if self.block.type == BlockType.ASSIGN:
            source_type = self.source_type.currentText()
            if source_type == "const":
                value = self.source_value_widget.value()
            else:
                value = self.source_value_widget.text().strip() or "var0"  # базова валідація

            source = Source(type=source_type, value=value)
            return replace(self.block, target=self.target_edit.text().strip() or "var0", source=source)

        elif self.block.type in (BlockType.INPUT, BlockType.PRINT):
            return replace(self.block, io_var=self.io_var.text().strip() or "var0")

        elif self.block.type == BlockType.DECISION:
            cond = Condition(
                var=self.cond_var.text().strip() or "var0",
                op=self.cond_op.currentText(),
                const=self.cond_const.value()
            )
            return replace(self.block, condition=cond)

        return self.block