"""
Read-only panel that shows the generated Python source code with syntax
highlighting via the built-in tkinter Text widget tags.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from models.program import Program
from translator.python_translator import PythonTranslator


class CodeViewPanel(ttk.Frame):
    """Tab panel: displays and lets the user copy the generated Python code."""

    def __init__(self, parent: tk.Widget, **kwargs: object) -> None:
        super().__init__(parent, **kwargs)
        self._translator = PythonTranslator()
        self._build_ui()

    # ──────────────────────────────────────────────────────── build UI
    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(4, 0), padx=4)

        ttk.Button(toolbar, text="Copy to clipboard",
                   command=self._copy_to_clipboard).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save to file…",
                   command=self._save_to_file).pack(side=tk.LEFT, padx=2)
        self._status_lbl = ttk.Label(toolbar, text="")
        self._status_lbl.pack(side=tk.LEFT, padx=8)

        text_frame = ttk.Frame(self)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._text = tk.Text(
            text_frame, wrap=tk.NONE, state=tk.DISABLED,
            font=("Courier New", 10), bg="#1E1E1E", fg="#D4D4D4",
            insertbackground="white", selectbackground="#264F78",
        )
        hbar = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL,
                             command=self._text.xview)
        vbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL,
                             command=self._text.yview)
        self._text.configure(xscrollcommand=hbar.set,
                             yscrollcommand=vbar.set)

        hbar.grid(row=1, column=0, sticky=tk.EW)
        vbar.grid(row=0, column=1, sticky=tk.NS)
        self._text.grid(row=0, column=0, sticky=tk.NSEW)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self._configure_tags()

    def _configure_tags(self) -> None:
        t = self._text
        t.tag_configure("keyword",  foreground="#569CD6")
        t.tag_configure("comment",  foreground="#6A9955")
        t.tag_configure("string",   foreground="#CE9178")
        t.tag_configure("function", foreground="#DCDCAA")
        t.tag_configure("number",   foreground="#B5CEA8")
        t.tag_configure("builtin",  foreground="#4EC9B0")

    # ──────────────────────────────────────────────────────── public API
    def refresh(self, program: Program) -> None:
        """Re-generate the code from *program* and update the display."""
        errors = program.validate()
        if errors:
            code = "# === Validation errors – fix them before translating ===\n"
            code += "\n".join(f"# {e}" for e in errors)
        else:
            code = self._translator.translate(program)

        self._text.configure(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        self._text.insert("1.0", code)
        self._apply_highlighting()
        self._text.configure(state=tk.DISABLED)
        self._status_lbl.configure(text=f"{code.count(chr(10))} lines generated")

    def _apply_highlighting(self) -> None:
        """Very lightweight keyword-based highlighting."""
        import re
        t = self._text
        content = t.get("1.0", tk.END)

        patterns = [
            ("keyword",  r'\b(def|return|if|elif|else|while|for|import|from|global|'
                         r'in|not|and|or|True|False|None|with|as|class|pass|break|'
                         r'continue|lambda)\b'),
            ("comment",  r'#[^\n]*'),
            ("string",   r'(""".*?"""|\'\'\'.*?\'\'\'|"[^"\\]*"|\'[^\'\\]*\')'),
            ("number",   r'\b\d+\b'),
            ("builtin",  r'\b(print|input|int|str|len|range|list|dict|set|tuple|'
                         r'threading|Thread|Lock)\b'),
            ("function", r'\b([a-z_][a-z0-9_]*)\s*(?=\()'),
        ]

        for tag_name, pattern in patterns:
            for m in re.finditer(pattern, content, re.DOTALL):
                start = f"1.0 + {m.start()} chars"
                end   = f"1.0 + {m.end()} chars"
                t.tag_add(tag_name, start, end)

    # ──────────────────────────────────────────────────────── actions
    def _copy_to_clipboard(self) -> None:
        code = self._text.get("1.0", tk.END)
        self.clipboard_clear()
        self.clipboard_append(code)
        self._status_lbl.configure(text="Copied to clipboard.")

    def _save_to_file(self) -> None:
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
            title="Save generated code",
        )
        if path:
            code = self._text.get("1.0", tk.END)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(code)
            self._status_lbl.configure(text=f"Saved to {path}")
