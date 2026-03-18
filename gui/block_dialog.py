"""
Modal dialogs for creating / editing individual flowchart blocks.
"""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, Optional

from models.block import Block, BlockType

_VAR_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _valid_var(name: str) -> bool:
    return bool(_VAR_RE.match(name))


def _valid_const(value: str) -> bool:
    try:
        v = int(value)
        return 0 <= v <= 2**31 - 1
    except ValueError:
        return False


class _BaseBlockDialog(tk.Toplevel):
    """Base class – subclasses add type-specific widgets and validation."""

    def __init__(self, parent: tk.Widget, title: str, block: Optional[Block] = None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.result: Optional[Dict[str, Any]] = None
        self._block = block

        self._build_widgets()
        if block:
            self._populate(block.content)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=12, pady=(4, 10))
        ttk.Button(btn_frame, text="OK",     command=self._on_ok).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)

        self.wait_window(self)

    def _build_widgets(self) -> None:
        raise NotImplementedError

    def _populate(self, content: Dict[str, Any]) -> None:
        pass

    def _validate(self) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def _on_ok(self) -> None:
        result = self._validate()
        if result is not None:
            self.result = result
            self.destroy()


class AssignDialog(_BaseBlockDialog):
    """Dialog for ASSIGN blocks (V1 = V2  or  V = C)."""

    def __init__(self, parent: tk.Widget, block: Optional[Block] = None):
        self._src_type_var = tk.StringVar(value="const")
        super().__init__(parent, "Edit ASSIGN block", block)

    def _build_widgets(self) -> None:
        frame = ttk.LabelFrame(self, text="Assignment  V = <value>", padding=10)
        frame.pack(padx=12, pady=10, fill=tk.BOTH)

        ttk.Label(frame, text="Target variable:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self._target_entry = ttk.Entry(frame, width=18)
        self._target_entry.grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=3)

        ttk.Label(frame, text="Source type:").grid(row=1, column=0, sticky=tk.W, pady=3)
        ttk.Radiobutton(frame, text="Constant",    variable=self._src_type_var,
                        value="const", command=self._refresh_source).grid(row=1, column=1, sticky=tk.W)
        ttk.Radiobutton(frame, text="Variable",    variable=self._src_type_var,
                        value="var",   command=self._refresh_source).grid(row=1, column=2, sticky=tk.W)

        ttk.Label(frame, text="Source value:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self._source_entry = ttk.Entry(frame, width=18)
        self._source_entry.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=3)

        self._hint_label = ttk.Label(frame, text="Integer 0 … 2³¹-1", foreground="gray")
        self._hint_label.grid(row=3, column=1, columnspan=2, sticky=tk.W)

    def _refresh_source(self) -> None:
        if self._src_type_var.get() == "const":
            self._hint_label.configure(text="Integer 0 … 2³¹-1")
        else:
            self._hint_label.configure(text="Variable identifier")

    def _populate(self, content: Dict[str, Any]) -> None:
        self._target_entry.insert(0, content.get("target", ""))
        src_type = content.get("src_type", "const")
        self._src_type_var.set(src_type)
        self._source_entry.insert(0, content.get("source", ""))
        self._refresh_source()

    def _validate(self) -> Optional[Dict[str, Any]]:
        target   = self._target_entry.get().strip()
        src_type = self._src_type_var.get()
        source   = self._source_entry.get().strip()

        if not _valid_var(target):
            messagebox.showerror("Validation", "Target must be a valid identifier.", parent=self)
            return None

        if src_type == "const":
            if not _valid_const(source):
                messagebox.showerror("Validation", "Constant must be an integer 0…2³¹-1.", parent=self)
                return None
        else:
            if not _valid_var(source):
                messagebox.showerror("Validation", "Source must be a valid identifier.", parent=self)
                return None

        return {"target": target, "src_type": src_type, "source": source}


class InputDialog(_BaseBlockDialog):
    """Dialog for INPUT blocks."""

    def __init__(self, parent: tk.Widget, block: Optional[Block] = None):
        super().__init__(parent, "Edit INPUT block", block)

    def _build_widgets(self) -> None:
        frame = ttk.LabelFrame(self, text="INPUT  V", padding=10)
        frame.pack(padx=12, pady=10, fill=tk.BOTH)
        ttk.Label(frame, text="Variable:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self._var_entry = ttk.Entry(frame, width=18)
        self._var_entry.grid(row=0, column=1, sticky=tk.W, pady=3)

    def _populate(self, content: Dict[str, Any]) -> None:
        self._var_entry.insert(0, content.get("var", ""))

    def _validate(self) -> Optional[Dict[str, Any]]:
        var = self._var_entry.get().strip()
        if not _valid_var(var):
            messagebox.showerror("Validation", "Variable must be a valid identifier.", parent=self)
            return None
        return {"var": var}


class PrintDialog(_BaseBlockDialog):
    """Dialog for PRINT blocks."""

    def __init__(self, parent: tk.Widget, block: Optional[Block] = None):
        super().__init__(parent, "Edit PRINT block", block)

    def _build_widgets(self) -> None:
        frame = ttk.LabelFrame(self, text="PRINT  V", padding=10)
        frame.pack(padx=12, pady=10, fill=tk.BOTH)
        ttk.Label(frame, text="Variable:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self._var_entry = ttk.Entry(frame, width=18)
        self._var_entry.grid(row=0, column=1, sticky=tk.W, pady=3)

    def _populate(self, content: Dict[str, Any]) -> None:
        self._var_entry.insert(0, content.get("var", ""))

    def _validate(self) -> Optional[Dict[str, Any]]:
        var = self._var_entry.get().strip()
        if not _valid_var(var):
            messagebox.showerror("Validation", "Variable must be a valid identifier.", parent=self)
            return None
        return {"var": var}


class ConditionDialog(_BaseBlockDialog):
    """Dialog for CONDITION blocks (V == C  or  V < C)."""

    def __init__(self, parent: tk.Widget, block: Optional[Block] = None):
        self._op_var = tk.StringVar(value="==")
        super().__init__(parent, "Edit CONDITION block", block)

    def _build_widgets(self) -> None:
        frame = ttk.LabelFrame(self, text="Condition  V  OP  C", padding=10)
        frame.pack(padx=12, pady=10, fill=tk.BOTH)

        ttk.Label(frame, text="Variable:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self._var_entry = ttk.Entry(frame, width=14)
        self._var_entry.grid(row=0, column=1, sticky=tk.W, pady=3)

        ttk.Label(frame, text="Operator:").grid(row=1, column=0, sticky=tk.W, pady=3)
        op_frame = ttk.Frame(frame)
        op_frame.grid(row=1, column=1, sticky=tk.W)
        ttk.Radiobutton(op_frame, text="==", variable=self._op_var, value="==").pack(side=tk.LEFT)
        ttk.Radiobutton(op_frame, text="< ", variable=self._op_var, value="<" ).pack(side=tk.LEFT)

        ttk.Label(frame, text="Constant:").grid(row=2, column=0, sticky=tk.W, pady=3)
        self._val_entry = ttk.Entry(frame, width=14)
        self._val_entry.grid(row=2, column=1, sticky=tk.W, pady=3)
        ttk.Label(frame, text="Integer 0 … 2³¹-1", foreground="gray").grid(
            row=3, column=1, sticky=tk.W)

    def _populate(self, content: Dict[str, Any]) -> None:
        self._var_entry.insert(0, content.get("var", ""))
        self._op_var.set(content.get("op", "=="))
        self._val_entry.insert(0, content.get("value", ""))

    def _validate(self) -> Optional[Dict[str, Any]]:
        var = self._var_entry.get().strip()
        val = self._val_entry.get().strip()
        if not _valid_var(var):
            messagebox.showerror("Validation", "Variable must be a valid identifier.", parent=self)
            return None
        if not _valid_const(val):
            messagebox.showerror("Validation", "Constant must be an integer 0…2³¹-1.", parent=self)
            return None
        return {"var": var, "op": self._op_var.get(), "value": val}


class BranchDialog(tk.Toplevel):
    """Asks the user which branch (TRUE / FALSE) a new CONDITION connection belongs to."""

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.title("Select branch")
        self.resizable(False, False)
        self.grab_set()
        self.branch: Optional[str] = None

        ttk.Label(self, text="This CONDITION block already has a connection.\n"
                              "Which branch should the new connection use?",
                  justify=tk.CENTER, padding=10).pack()
        btn = ttk.Frame(self)
        btn.pack(pady=(0, 10))
        ttk.Button(btn, text="TRUE  branch", command=lambda: self._pick("true")).pack(side=tk.LEFT,  padx=6)
        ttk.Button(btn, text="FALSE branch", command=lambda: self._pick("false")).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn, text="Cancel",       command=self.destroy).pack(side=tk.LEFT, padx=6)

        self.wait_window(self)

    def _pick(self, branch: str) -> None:
        self.branch = branch
        self.destroy()


def open_block_dialog(parent: tk.Widget, block: Block) -> Optional[Dict[str, Any]]:
    """Open the appropriate dialog for *block* and return updated content or None."""
    bt = block.block_type
    if bt == BlockType.ASSIGN:
        dlg = AssignDialog(parent, block)
    elif bt == BlockType.INPUT:
        dlg = InputDialog(parent, block)
    elif bt == BlockType.PRINT:
        dlg = PrintDialog(parent, block)
    elif bt == BlockType.CONDITION:
        dlg = ConditionDialog(parent, block)
    else:
        return None  # START / END have no editable content
    return dlg.result


def open_new_block_dialog(parent: tk.Widget, block_type: BlockType) -> Optional[Dict[str, Any]]:
    """Open a blank dialog for a freshly created block of *block_type*."""
    tmp = Block(block_type=block_type)
    return open_block_dialog(parent, tmp)
