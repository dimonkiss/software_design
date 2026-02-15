from dataclasses import replace

from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QComboBox, QSpinBox, QDialogButtonBox

from src.parallel_emulator.domain.entities.block import Block
from src.parallel_emulator.domain.enums.block_type import BlockType
from src.parallel_emulator.domain.value_objects.condition import Condition
from src.parallel_emulator.domain.value_objects.source import Source


class BlockEditDialog(QDialog):
    def __init__(self, block: Block, parent=None):
        super().__init__(parent)
        self.block = block
        self.setWindowTitle("Редагування блоку")
        layout = QFormLayout(self)

        self.target_edit = QLineEdit(block.target or "")
        self.value_spin = QSpinBox()
        self.value_spin.setRange(0, 2**31 - 1)
        self.var_edit = QLineEdit(block.io_var or "var0")

        if block.type == BlockType.ASSIGN:
            layout.addRow("Target:", self.target_edit)
            self.source_type = QComboBox()
            self.source_type.addItems(["const", "var"])
            layout.addRow("Source type:", self.source_type)
            layout.addRow("Value:", self.value_spin)
        elif block.type in (BlockType.INPUT, BlockType.PRINT):
            layout.addRow("Variable:", self.var_edit)
        elif block.type == BlockType.DECISION:
            self.cond_var = QLineEdit(block.condition.var if block.condition else "var0")
            self.cond_op = QComboBox()
            self.cond_op.addItems(["==", "<"])
            self.cond_const = QSpinBox()
            self.cond_const.setRange(0, 2**31 - 1)
            layout.addRow("Variable:", self.cond_var)
            layout.addRow("Operator:", self.cond_op)
            layout.addRow("Constant:", self.cond_const)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_block(self) -> Block:
        if self.block.type == BlockType.ASSIGN:
            src = Source(type=self.source_type.currentText(), value=self.value_spin.value())
            return replace(self.block, target=self.target_edit.text(), source=src)
        elif self.block.type in (BlockType.INPUT, BlockType.PRINT):
            return replace(self.block, io_var=self.var_edit.text())
        elif self.block.type == BlockType.DECISION:
            cond = Condition(var=self.cond_var.text(), op=self.cond_op.currentText(), const=self.cond_const.value())
            return replace(self.block, condition=cond)
        return self.block