"""
Code & Run panel.

Toolbar layout
--------------
  [▶ Run All]   Thread: [Combobox ▼]  [▶ Run Thread]   [■ Stop]   0.000 s

Interactive console
-------------------
The console is a proper terminal widget:
  • Process stdout/stderr streams in live (line-by-line, unbuffered).
  • The user types input directly in the console and presses Enter.
  • Everything typed after the last output line is sent to the process stdin.
  • Previous output is read-only; the cursor is redirected to the input area
    on any printable keystroke.

Toggle strip
------------
  [▼ Source code]   [Copy]   [Save .py…]   N lines
  ─── collapsible syntax-highlighted code viewer ───
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import re
from typing import List, Optional

# os.read() chunk size – large enough for performance, small enough for responsiveness
_READ_CHUNK = 4096

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from models.program import Program
from translator.python_translator import PythonTranslator

# ── VS Code Dark+ palette ────────────────────────────────────────────────────
_BG         = "#1E1E1E"
_FG         = "#D4D4D4"
_CON_BG     = "#0C0C0C"
_CON_FG     = "#CCCCCC"
_SEL_BG     = "#264F78"


# ═══════════════════════════════════════════════════════ interactive console

class _Console(tk.Text):
    """
    Terminal-like tk.Text widget.

    * ``write(text, tag)``  – append output (moves the editable boundary forward).
    * ``clear()``           – reset.
    * ``attach_process(p)`` – register the running Popen so Enter sends to stdin.

    Only the area *after* the last written output is editable.  Typing before
    that boundary is silently redirected to the end.
    """

    _BOUNDARY = "io_boundary"

    def __init__(self, parent: tk.Widget, **kwargs: object) -> None:
        super().__init__(
            parent,
            wrap=tk.WORD,
            font=("Courier New", 11),
            bg=_CON_BG, fg=_CON_FG,
            insertbackground="#AEAFAD",
            selectbackground=_SEL_BG,
            relief=tk.FLAT, borderwidth=0,
            undo=False,
            **kwargs,
        )
        self._proc: Optional[subprocess.Popen] = None
        self.mark_set(self._BOUNDARY, "1.0")
        self.mark_gravity(self._BOUNDARY, tk.LEFT)

        self._configure_tags()
        self._bind_keys()

    # ── tags ────────────────────────────────────────────────────────────────
    def _configure_tags(self) -> None:
        self.tag_configure("cmd",   foreground="#61AFEF",
                           font=("Courier New", 11, "bold"))
        self.tag_configure("info",  foreground="#56B6C2")
        self.tag_configure("sep",   foreground="#3E3E3E")
        self.tag_configure("ok",    foreground="#98C379",
                           font=("Courier New", 11, "bold"))
        self.tag_configure("err",   foreground="#E06C75",
                           font=("Courier New", 11, "bold"))
        self.tag_configure("warn",  foreground="#E5C07B",
                           font=("Courier New", 11, "bold"))
        self.tag_configure("stdin", foreground="#ABB2BF",
                           font=("Courier New", 11, "italic"))
        self.tag_configure("out",   foreground=_CON_FG)

    # ── key bindings ────────────────────────────────────────────────────────
    def _bind_keys(self) -> None:
        # Redirect any printable char to the input area
        self.bind("<Key>",       self._on_key,       add=True)
        self.bind("<Return>",    self._on_return)
        self.bind("<BackSpace>", self._on_backspace)
        self.bind("<Delete>",    self._on_delete)
        # Ctrl+C → copy; Ctrl+A → select all (read only, fine)
        self.bind("<Control-c>", self._on_ctrl_c)

    # ── public API ──────────────────────────────────────────────────────────
    def attach_process(self, proc: Optional[subprocess.Popen]) -> None:
        self._proc = proc

    def write(self, text: str, tag: str = "out") -> None:
        """Append *text* tagged with *tag*.  Boundary moves forward.

        BOUNDARY must always sit at "end-1c" (one position before tkinter's
        implicit final newline), NOT at "end".  If it sat at "end":
          get(BOUNDARY, "end-1c") → "" always  →  user input silently lost.
        """
        # Save whatever the user has already typed after the current boundary
        pending = self.get(self._BOUNDARY, "end-1c")
        if pending:
            self.delete(self._BOUNDARY, tk.END)

        self.insert(self._BOUNDARY, text, tag)

        # ← KEY FIX: "end-1c", not tk.END
        # "end" is AFTER the implicit final newline; "end-1c" is just before it.
        # Only the region [BOUNDARY … end-1c] is user-editable input.
        self.mark_set(self._BOUNDARY, "end-1c")

        if pending:
            # Re-insert the partial user input at the end (before implicit \n).
            # Due to LEFT gravity, BOUNDARY stays to the left of this text.
            self.insert("end-1c", pending)

        self.see(tk.END)

    def clear(self) -> None:
        self.delete("1.0", tk.END)
        self.mark_set(self._BOUNDARY, "1.0")
        self._proc = None

    # ── event handlers ──────────────────────────────────────────────────────
    def _on_key(self, event: tk.Event) -> None:
        """Redirect cursor to the input area before any printable character."""
        if not event.char or event.keysym in (
            "Return", "BackSpace", "Delete", "Tab",
            "Escape", "F1", "F2", "F3", "F4", "F5",
        ):
            return
        if event.state & 0x4:     # Ctrl held
            return
        if self.compare(tk.INSERT, "<", self._BOUNDARY):
            # Move cursor to end-1c (writable area, before implicit \n)
            self.mark_set(tk.INSERT, "end-1c")

    def _on_return(self, event: tk.Event) -> str:
        """Send the pending input line to the process and echo it."""
        line = self.get(self._BOUNDARY, "end-1c")
        # Replace plain typed text with the styled stdin echo
        self.delete(self._BOUNDARY, tk.END)
        self.insert(self._BOUNDARY, line + "\n", "stdin")
        # ← KEY FIX: "end-1c", not tk.END
        self.mark_set(self._BOUNDARY, "end-1c")
        self.see(tk.END)

        if self._proc and self._proc.poll() is None:
            try:
                # stdin is a binary pipe → encode to bytes
                self._proc.stdin.write((line + "\n").encode("utf-8"))
                self._proc.stdin.flush()
            except (OSError, BrokenPipeError):
                pass
        return "break"

    def _on_backspace(self, event: tk.Event) -> Optional[str]:
        if self.compare(tk.INSERT, "<=", self._BOUNDARY):
            return "break"
        return None

    def _on_delete(self, event: tk.Event) -> Optional[str]:
        if self.compare(tk.INSERT, "<", self._BOUNDARY):
            return "break"
        return None

    def _on_ctrl_c(self, event: tk.Event) -> str:
        try:
            sel = self.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.clipboard_clear()
            self.clipboard_append(sel)
        except tk.TclError:
            pass
        return "break"


# ═══════════════════════════════════════════════════════════ main panel

class CodeViewPanel(ttk.Frame):
    """Combined run-console + source-code panel."""

    def __init__(self, parent: tk.Widget, **kwargs: object) -> None:
        super().__init__(parent, **kwargs)
        self._translator   = PythonTranslator()
        self._program: Optional[Program] = None
        self._process: Optional[subprocess.Popen] = None
        self._out_queue: queue.Queue = queue.Queue()
        self._start_time: float = 0.0
        self._tmp_path: Optional[str] = None

        self._build_ui()

    # ═══════════════════════════════════════════════════════════ build
    def _build_ui(self) -> None:

        # ── 1. Run toolbar ──────────────────────────────────────────────
        tb = ttk.Frame(self, padding=(6, 4, 6, 4))
        tb.pack(fill=tk.X)

        ttk.Button(tb, text="▶  Run All",
                   command=self._run_all).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Separator(tb, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=6, pady=3)

        ttk.Label(tb, text="Thread:").pack(side=tk.LEFT, padx=(0, 4))
        self._thread_combo = ttk.Combobox(
            tb, state="readonly", width=20,
            font=("Helvetica", 10),
        )
        self._thread_combo.pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(tb, text="▶  Run Thread",
                   command=self._run_selected_thread).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Separator(tb, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=6, pady=3)

        self._stop_btn = ttk.Button(tb, text="■  Stop",
                                    command=self._stop_process,
                                    state=tk.DISABLED)
        self._stop_btn.pack(side=tk.LEFT, padx=(0, 8))

        self._timer_lbl = ttk.Label(tb, text="", foreground="gray",
                                    font=("Courier New", 10))
        self._timer_lbl.pack(side=tk.LEFT)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=4)

        # ── 2. Console ──────────────────────────────────────────────────
        con_outer = ttk.Frame(self)
        con_outer.pack(fill=tk.BOTH, expand=True, padx=6, pady=(4, 2))

        self._console = _Console(con_outer)
        con_vbar = ttk.Scrollbar(con_outer, orient=tk.VERTICAL,
                                 command=self._console.yview)
        self._console.configure(yscrollcommand=con_vbar.set)
        con_vbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._console.pack(fill=tk.BOTH, expand=True)

        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=4, pady=(2, 0))

        # ── 3. Toggle strip ─────────────────────────────────────────────
        strip = ttk.Frame(self, padding=(6, 3))
        strip.pack(fill=tk.X)

        self._toggle_btn = ttk.Button(strip, text="▼  Source code",
                                      command=self._toggle_code, width=16)
        self._toggle_btn.pack(side=tk.LEFT)

        ttk.Button(strip, text="Copy",
                   command=self._copy_code).pack(side=tk.LEFT, padx=6)
        ttk.Button(strip, text="Save .py…",
                   command=self._save_code).pack(side=tk.LEFT)

        self._code_status = ttk.Label(strip, text="", foreground="gray",
                                      font=("Helvetica", 9))
        self._code_status.pack(side=tk.LEFT, padx=10)

        # ── 4. Code viewer (hidden by default) ──────────────────────────
        self._code_frame = ttk.Frame(self)
        # not packed yet

        inner = ttk.Frame(self._code_frame)
        inner.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0, 4))

        self._code_text = tk.Text(
            inner, wrap=tk.NONE, state=tk.DISABLED,
            font=("Courier New", 10), bg=_BG, fg=_FG,
            insertbackground=_FG, selectbackground=_SEL_BG,
        )
        code_hbar = ttk.Scrollbar(inner, orient=tk.HORIZONTAL,
                                  command=self._code_text.xview)
        code_vbar = ttk.Scrollbar(inner, orient=tk.VERTICAL,
                                  command=self._code_text.yview)
        self._code_text.configure(xscrollcommand=code_hbar.set,
                                  yscrollcommand=code_vbar.set)
        code_hbar.grid(row=1, column=0, sticky=tk.EW)
        code_vbar.grid(row=0, column=1, sticky=tk.NS)
        self._code_text.grid(row=0, column=0, sticky=tk.NSEW)
        inner.columnconfigure(0, weight=1)
        inner.rowconfigure(0, weight=1)

        self._configure_code_tags()

    # ═══════════════════════════════════════════════════════════ public
    def refresh(self, program: Program) -> None:
        self._program = program
        self._rebuild_combo()
        self._regenerate_code()

    # ═══════════════════════════════════════════════════════════ combo
    def _rebuild_combo(self) -> None:
        if self._program is None:
            self._thread_combo["values"] = []
            return
        names = [f"{i}: {fc.name}"
                 for i, fc in enumerate(self._program.flowcharts)]
        self._thread_combo["values"] = names
        if names:
            self._thread_combo.current(0)

    # ═══════════════════════════════════════════════════════════ run
    def _run_all(self) -> None:
        if self._program is None:
            return
        self._launch(list(range(len(self._program.flowcharts))))

    def _run_selected_thread(self) -> None:
        if self._program is None:
            return
        sel = self._thread_combo.current()
        if sel < 0:
            messagebox.showwarning("No thread", "Select a thread from the dropdown.")
            return
        self._launch([sel])

    def _launch(self, indices: List[int]) -> None:
        if not self._program:
            return

        # Guard: already running?
        if self._process and self._process.poll() is None:
            messagebox.showwarning("Running",
                                   "A process is already running.\nStop it first.")
            return

        # Build sub-program
        from models.program import Program as Prog
        fcs     = [self._program.flowcharts[i] for i in indices]
        sub     = Prog(name=self._program.name, flowcharts=fcs)
        errors  = sub.validate()
        if errors:
            messagebox.showerror("Validation errors", "\n".join(errors))
            return

        code = self._translator.translate(sub)

        # Write to temp file
        tmp = tempfile.NamedTemporaryFile(
            suffix=".py", delete=False, mode="w", encoding="utf-8")
        tmp.write(code)
        tmp.close()
        self._tmp_path = tmp.name

        # Reset console
        self._console.clear()
        thread_names = ", ".join(fcs[j].name for j in range(len(fcs)))
        self._console.write(f"$ python  {os.path.basename(tmp.name)}"
                            f"  [{thread_names}]\n", "cmd")
        self._console.write("─" * 52 + "\n", "sep")

        # Env: force unbuffered output
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        try:
            self._process = subprocess.Popen(
                [sys.executable, tmp.name],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                # Binary mode so os.read() can bypass all Python-level
                # line-buffering.  ">>> " (no newline) arrives immediately.
                text=False,
                bufsize=0,
                env=env,
            )
        except Exception as exc:
            self._console.write(f"Launch error: {exc}\n", "err")
            return

        self._console.attach_process(self._process)
        self._stop_btn.configure(state=tk.NORMAL)
        self._start_time = time.perf_counter()
        self._timer_lbl.configure(text="running…")

        # Background reader thread
        self._out_queue = queue.Queue()
        t = threading.Thread(target=self._reader_worker, daemon=True)
        t.start()
        self.after(40, self._poll_queue)

    # ── subprocess I/O ──────────────────────────────────────────────────────
    def _reader_worker(self) -> None:
        """
        Read stdout/stderr from the subprocess using raw os.read().

        os.read() is a direct syscall: it returns whatever bytes are
        available in the pipe right now, without waiting for a newline.
        This is the only reliable way to display partial lines such as
        the ">>> " input prompt the moment the subprocess writes them.
        """
        assert self._process is not None
        fd = self._process.stdout.fileno()
        while True:
            try:
                data = os.read(fd, _READ_CHUNK)
            except OSError:
                break
            if not data:
                break
            self._out_queue.put(("chunk", data.decode("utf-8", errors="replace")))
        self._process.wait()
        elapsed = time.perf_counter() - self._start_time
        self._out_queue.put(("done", self._process.returncode, elapsed))

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self._out_queue.get_nowait()
                if item[0] == "chunk":
                    self._console.write(item[1])
                elif item[0] == "done":
                    self._on_done(item[1], item[2])
                    return
        except queue.Empty:
            pass
        self.after(40, self._poll_queue)

    def _on_done(self, returncode: int, elapsed: float) -> None:
        self._console.write("─" * 52 + "\n", "sep")
        if returncode == 0:
            self._console.write(f"✔  Finished  ({elapsed:.3f} s)\n", "ok")
        else:
            self._console.write(
                f"✘  Exit code {returncode}  ({elapsed:.3f} s)\n", "err")
        self._console.attach_process(None)
        self._stop_btn.configure(state=tk.DISABLED)
        self._timer_lbl.configure(
            text=f"{'OK' if returncode == 0 else 'ERR'}  {elapsed:.3f} s")
        if self._tmp_path:
            try:
                os.unlink(self._tmp_path)
            except OSError:
                pass
            self._tmp_path = None

    def _stop_process(self) -> None:
        if self._process and self._process.poll() is None:
            self._process.terminate()
            self._console.write("\n■  Stopped by user.\n", "warn")
            self._console.attach_process(None)
            self._stop_btn.configure(state=tk.DISABLED)
            self._timer_lbl.configure(text="stopped")

    # ═══════════════════════════════════════════════════════════ code toggle
    def _toggle_code(self) -> None:
        if self._code_frame.winfo_ismapped():
            self._code_frame.pack_forget()
            self._toggle_btn.configure(text="▼  Source code")
        else:
            self._code_frame.pack(fill=tk.BOTH, expand=False,
                                  padx=6, pady=(0, 6))
            self._toggle_btn.configure(text="▲  Source code")

    # ═══════════════════════════════════════════════════════════ code gen
    def _regenerate_code(self) -> None:
        if self._program is None:
            return
        errors = self._program.validate()
        if errors:
            code = "# === Validation errors – fix before running ===\n"
            code += "\n".join(f"# {e}" for e in errors)
        else:
            code = self._translator.translate(self._program)

        t = self._code_text
        t.configure(state=tk.NORMAL)
        t.delete("1.0", tk.END)
        t.insert("1.0", code)
        self._apply_highlighting()
        t.configure(state=tk.DISABLED)
        n = code.count("\n")
        self._code_status.configure(text=f"{n} lines")

    def _configure_code_tags(self) -> None:
        t = self._code_text
        t.tag_configure("keyword",  foreground="#569CD6")
        t.tag_configure("comment",  foreground="#6A9955")
        t.tag_configure("string",   foreground="#CE9178")
        t.tag_configure("function", foreground="#DCDCAA")
        t.tag_configure("number",   foreground="#B5CEA8")
        t.tag_configure("builtin",  foreground="#4EC9B0")

    def _apply_highlighting(self) -> None:
        t = self._code_text
        content = t.get("1.0", tk.END)
        patterns = [
            ("keyword",  r'\b(def|return|if|elif|else|while|for|import|from|global|'
                         r'in|not|and|or|True|False|None|with|as|class|pass|break|'
                         r'continue|lambda)\b'),
            ("comment",  r'#[^\n]*'),
            ("string",   r'(?s)(""".*?"""|\'\'\'.*?\'\'\'|"[^"\\]*"|\'[^\'\\]*\')'),
            ("number",   r'\b\d+\b'),
            ("builtin",  r'\b(print|input|int|str|len|range|list|dict|set|tuple|'
                         r'threading|Thread|Lock)\b'),
            ("function", r'\b([a-z_][a-z0-9_]*)\s*(?=\()'),
        ]
        for tag, pattern in patterns:
            for m in re.finditer(pattern, content):
                t.tag_add(tag,
                          f"1.0 + {m.start()} chars",
                          f"1.0 + {m.end()} chars")

    # ═══════════════════════════════════════════════════════════ copy/save
    def _copy_code(self) -> None:
        code = self._code_text.get("1.0", tk.END)
        self.clipboard_clear()
        self.clipboard_append(code)
        self._code_status.configure(text="Copied!")

    def _save_code(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
            title="Save generated code",
        )
        if not path:
            return
        code = self._code_text.get("1.0", tk.END)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(code)
        self._code_status.configure(text=f"Saved → {os.path.basename(path)}")
