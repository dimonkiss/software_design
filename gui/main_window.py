"""
Main application window.

Layout
------
┌─────────────────────────────────────────────────────────┐
│  Menu bar                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Editor      │  │   Code       │  │   Tests      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────┬──────────────────────────────────────────┐ │
│  │ Threads  │  Toolbar                                 │ │
│  │ (list)   │  ┌──────────────────────────────────────┐│ │
│  │          │  │         FlowchartCanvas               ││ │
│  │ [+][-]   │  └──────────────────────────────────────┘│ │
│  └──────────┴──────────────────────────────────────────┘ │
│  Status bar                                             │
└─────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Optional

from gui.code_view import CodeViewPanel
from gui.flowchart_canvas import FlowchartCanvas
from gui.test_panel import TestPanel
from models.block import BlockType
from models.flowchart import Flowchart
from models.program import Program
from storage.serializer import load_program, save_program


class MainWindow(tk.Tk):
    """Root window of the Flowchart Editor application."""

    APP_TITLE = "Flowchart-MT Editor"

    def __init__(self) -> None:
        super().__init__()
        self.title(self.APP_TITLE)
        self.minsize(900, 620)
        self._program: Program = Program(name="Untitled")
        self._current_file: Optional[str] = None
        self._dirty = False
        self._current_fc_canvas: Optional[FlowchartCanvas] = None

        self._build_menu()
        self._build_notebook()
        self._build_status_bar()

        self._new_program()

    # ──────────────────────────────────────────────────────── menu bar
    def _build_menu(self) -> None:
        mb = tk.Menu(self)
        self.configure(menu=mb)

        # File
        file_menu = tk.Menu(mb, tearoff=False)
        mb.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New",        accelerator="Ctrl+N", command=self._cmd_new)
        file_menu.add_command(label="Open…",      accelerator="Ctrl+O", command=self._cmd_open)
        file_menu.add_command(label="Save",        accelerator="Ctrl+S", command=self._cmd_save)
        file_menu.add_command(label="Save as…",                          command=self._cmd_save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit",                              command=self._cmd_exit)

        # Edit
        edit_menu = tk.Menu(mb, tearoff=False)
        mb.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Add thread",    command=self._add_thread)
        edit_menu.add_command(label="Remove thread", command=self._remove_thread)
        edit_menu.add_command(label="Rename thread", command=self._rename_thread)
        edit_menu.add_separator()
        edit_menu.add_command(label="Validate program", command=self._cmd_validate)

        # Run
        run_menu = tk.Menu(mb, tearoff=False)
        mb.add_cascade(label="Run", menu=run_menu)
        run_menu.add_command(label="Translate to Python", command=self._cmd_translate)
        run_menu.add_command(label="Run test (single)",   command=self._cmd_run_test)

        # Bind shortcuts
        self.bind("<Control-n>", lambda _e: self._cmd_new())
        self.bind("<Control-o>", lambda _e: self._cmd_open())
        self.bind("<Control-s>", lambda _e: self._cmd_save())

    # ──────────────────────────────────────────────────────── notebook
    def _build_notebook(self) -> None:
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill=tk.BOTH, expand=True)
        self._notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # ── Editor tab ────────────────────────────────────────────────
        self._editor_tab = ttk.Frame(self._notebook)
        self._notebook.add(self._editor_tab, text="  Editor  ")
        self._build_editor_tab()

        # ── Code tab ──────────────────────────────────────────────────
        self._code_panel = CodeViewPanel(self._notebook)
        self._notebook.add(self._code_panel, text="  Code  ")

        # ── Tests tab ─────────────────────────────────────────────────
        self._test_panel = TestPanel(self._notebook)
        self._notebook.add(self._test_panel, text="  Tests  ")

    def _build_editor_tab(self) -> None:
        """Two-pane layout: thread list on the left, canvas on the right."""
        paned = ttk.PanedWindow(self._editor_tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # ── Left: thread list ─────────────────────────────────────────
        left = ttk.Frame(paned, width=170)
        paned.add(left, weight=0)

        ttk.Label(left, text="Threads", font=("Helvetica", 10, "bold")).pack(pady=(6, 2))

        self._thread_listbox = tk.Listbox(
            left, selectmode=tk.SINGLE, exportselection=False,
            width=18, height=20,
        )
        self._thread_listbox.pack(fill=tk.BOTH, expand=True, padx=4)
        self._thread_listbox.bind("<<ListboxSelect>>", self._on_select_thread)

        btn_row = ttk.Frame(left)
        btn_row.pack(fill=tk.X, padx=4, pady=(4, 6))
        ttk.Button(btn_row, text="+", width=3, command=self._add_thread).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="–", width=3, command=self._remove_thread).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="✎", width=3, command=self._rename_thread).pack(side=tk.LEFT, padx=2)

        # ── Right: toolbar + canvas ───────────────────────────────────
        right = ttk.Frame(paned)
        paned.add(right, weight=1)

        self._build_canvas_toolbar(right)

        self._canvas_placeholder = ttk.Label(
            right,
            text="Select a thread from the left panel\nor add a new thread (+) to start editing.",
            justify=tk.CENTER, anchor=tk.CENTER,
            font=("Helvetica", 12), foreground="gray",
        )
        self._canvas_placeholder.pack(fill=tk.BOTH, expand=True)

    def _build_canvas_toolbar(self, parent: tk.Widget) -> None:
        tb = ttk.Frame(parent, relief=tk.RIDGE, borderwidth=1)
        tb.pack(fill=tk.X, pady=(2, 0))

        def _mode_btn(text: str, cmd, tip: str = "") -> ttk.Button:
            b = ttk.Button(tb, text=text, width=9, command=cmd)
            b.pack(side=tk.LEFT, padx=2, pady=2)
            return b

        _mode_btn("↖ Select",    self._mode_select)
        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=3)

        _mode_btn("START",      lambda: self._mode_add(BlockType.START))
        _mode_btn("END",        lambda: self._mode_add(BlockType.END))
        _mode_btn("ASSIGN",     lambda: self._mode_add(BlockType.ASSIGN))
        _mode_btn("INPUT",      lambda: self._mode_add(BlockType.INPUT))
        _mode_btn("PRINT",      lambda: self._mode_add(BlockType.PRINT))
        _mode_btn("CONDITION",  lambda: self._mode_add(BlockType.CONDITION))
        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=3)

        _mode_btn("↔ Connect",  self._mode_connect)
        _mode_btn("🗑 Delete",   self._delete_selected)
        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=3)

        _mode_btn("✔ Validate", self._cmd_validate)

        self._mode_label = ttk.Label(tb, text="Mode: SELECT", foreground="navy",
                                     font=("Helvetica", 9, "bold"))
        self._mode_label.pack(side=tk.RIGHT, padx=8)

    # ──────────────────────────────────────────────────────── status bar
    def _build_status_bar(self) -> None:
        self._status_bar = ttk.Label(
            self, text="Ready.", relief=tk.SUNKEN, anchor=tk.W, padding=(4, 2)
        )
        self._status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _set_status(self, msg: str) -> None:
        self._status_bar.configure(text=msg)

    # ──────────────────────────────────────────────────────── program management
    def _new_program(self) -> None:
        self._program       = Program(name="Untitled")
        self._current_file  = None
        self._dirty         = False
        self._current_fc_canvas = None
        self._reload_ui()
        self.title(self.APP_TITLE + " – Untitled")

    def _reload_ui(self) -> None:
        """Rebuild thread list and reset canvas area."""
        lb = self._thread_listbox
        lb.delete(0, tk.END)
        for fc in self._program.flowcharts:
            lb.insert(tk.END, fc.name)

        # Remove old canvas if present
        if self._current_fc_canvas:
            self._current_fc_canvas.pack_forget()
            self._current_fc_canvas.destroy()
            self._current_fc_canvas = None

        self._canvas_placeholder.pack(fill=tk.BOTH, expand=True)
        self._test_panel.refresh(self._program)

    # ──────────────────────────────────────────────────────── thread management
    def _add_thread(self) -> None:
        n    = len(self._program.flowcharts) + 1
        if n > 100:
            messagebox.showerror("Limit reached", "Maximum 100 threads allowed.")
            return
        name = simpledialog.askstring("New thread", "Thread name:", initialvalue=f"Thread {n}")
        if not name:
            return
        fc = Flowchart(name=name)
        self._program.flowcharts.append(fc)
        self._thread_listbox.insert(tk.END, name)
        self._thread_listbox.selection_clear(0, tk.END)
        self._thread_listbox.selection_set(tk.END)
        self._on_select_thread(None)
        self._mark_dirty()

    def _remove_thread(self) -> None:
        sel = self._thread_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        name = self._program.flowcharts[idx].name
        if not messagebox.askyesno("Remove thread", f"Remove thread «{name}»?"):
            return
        del self._program.flowcharts[idx]
        self._reload_ui()
        self._mark_dirty()

    def _rename_thread(self) -> None:
        sel = self._thread_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        fc  = self._program.flowcharts[idx]
        new_name = simpledialog.askstring("Rename thread", "New name:", initialvalue=fc.name)
        if new_name and new_name.strip():
            fc.name = new_name.strip()
            self._thread_listbox.delete(idx)
            self._thread_listbox.insert(idx, fc.name)
            self._thread_listbox.selection_set(idx)
            self._mark_dirty()

    def _on_select_thread(self, _event: Optional[tk.Event]) -> None:
        sel = self._thread_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        fc  = self._program.flowcharts[idx]
        self._load_flowchart_canvas(fc)

    def _load_flowchart_canvas(self, fc: Flowchart) -> None:
        # Destroy old canvas
        if self._current_fc_canvas:
            self._current_fc_canvas.pack_forget()
            self._current_fc_canvas.destroy()

        self._canvas_placeholder.pack_forget()

        # Find the right parent (the right pane of the PanedWindow)
        parent = self._canvas_placeholder.master  # the right ttk.Frame

        self._current_fc_canvas = FlowchartCanvas(
            parent, flowchart=fc,
            on_change=self._on_canvas_change,
        )
        self._current_fc_canvas.pack(fill=tk.BOTH, expand=True)

    def _on_canvas_change(self) -> None:
        self._mark_dirty()

    # ──────────────────────────────────────────────────────── toolbar modes
    def _mode_select(self) -> None:
        if self._current_fc_canvas:
            self._current_fc_canvas.set_mode_select()
        self._mode_label.configure(text="Mode: SELECT")

    def _mode_add(self, bt: BlockType) -> None:
        if self._current_fc_canvas is None:
            messagebox.showinfo("No thread", "Select a thread first.")
            return
        self._current_fc_canvas.set_mode_add_block(bt)
        self._mode_label.configure(text=f"Mode: ADD {bt.value.upper()}")

    def _mode_connect(self) -> None:
        if self._current_fc_canvas is None:
            messagebox.showinfo("No thread", "Select a thread first.")
            return
        self._current_fc_canvas.set_mode_connect()
        self._mode_label.configure(text="Mode: CONNECT")

    def _delete_selected(self) -> None:
        if self._current_fc_canvas:
            self._current_fc_canvas.delete_selected()

    # ──────────────────────────────────────────────────────── notebook tab switch
    def _on_tab_changed(self, _event: tk.Event) -> None:
        current = self._notebook.index(self._notebook.select())
        if current == 1:   # Code tab
            self._code_panel.refresh(self._program)
        elif current == 2: # Tests tab
            self._test_panel.refresh(self._program)

    # ──────────────────────────────────────────────────────── file operations
    def _cmd_new(self) -> None:
        if self._dirty and not messagebox.askyesno("Unsaved changes",
                                                    "Discard unsaved changes?"):
            return
        self._new_program()

    def _cmd_open(self) -> None:
        if self._dirty and not messagebox.askyesno("Unsaved changes",
                                                    "Discard unsaved changes?"):
            return
        path = filedialog.askopenfilename(
            filetypes=[("Flowchart program", "*.fcp"), ("JSON", "*.json"),
                       ("All files", "*.*")],
            title="Open program",
        )
        if not path:
            return
        try:
            self._program       = load_program(path)
            self._current_file  = path
            self._dirty         = False
            self._reload_ui()
            self.title(f"{self.APP_TITLE} – {path}")
            self._set_status(f"Opened: {path}")
        except Exception as exc:
            messagebox.showerror("Open failed", str(exc))

    def _cmd_save(self) -> None:
        if self._current_file:
            self._do_save(self._current_file)
        else:
            self._cmd_save_as()

    def _cmd_save_as(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".fcp",
            filetypes=[("Flowchart program", "*.fcp"), ("JSON", "*.json"),
                       ("All files", "*.*")],
            title="Save program",
        )
        if not path:
            return
        self._do_save(path)

    def _do_save(self, path: str) -> None:
        try:
            save_program(self._program, path)
            self._current_file = path
            self._dirty        = False
            self.title(f"{self.APP_TITLE} – {path}")
            self._set_status(f"Saved: {path}")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))

    def _cmd_exit(self) -> None:
        if self._dirty and not messagebox.askyesno("Unsaved changes",
                                                    "Discard unsaved changes and exit?"):
            return
        self.destroy()

    # ──────────────────────────────────────────────────────── validate / translate
    def _cmd_validate(self) -> None:
        errors = self._program.validate()
        if errors:
            messagebox.showerror("Validation errors", "\n".join(errors))
            self._set_status("Validation FAILED.")
        else:
            messagebox.showinfo("Validation", "Program is valid.")
            self._set_status("Validation OK.")

    def _cmd_translate(self) -> None:
        self._notebook.select(1)  # switch to Code tab
        self._code_panel.refresh(self._program)

    def _cmd_run_test(self) -> None:
        self._notebook.select(2)  # switch to Tests tab

    # ──────────────────────────────────────────────────────── dirty flag
    def _mark_dirty(self) -> None:
        if not self._dirty:
            self._dirty = True
            title = self.title()
            if not title.startswith("*"):
                self.title("* " + title)
