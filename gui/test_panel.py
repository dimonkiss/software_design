"""
Test panel – manages test cases and drives execution / enumeration.

Layout
------
Left column   : list of test cases with Add / Remove buttons
Right column  :
    * Input text area
    * Expected-output text area
    * K spinbox (1-20)
    * Buttons: Run Single | Enumerate (stop) | Reset verified
    * Results area: status, actual output, statistics

Thread safety
-------------
BFS enumeration runs in a background ``threading.Thread``.
GUI updates are scheduled with ``widget.after_idle`` via a queue so tkinter
remains responsive and is only touched from the main thread.
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from executor.test_runner import EnumProgress, TestRunner
from models.program import Program, TestCase


class TestPanel(ttk.Frame):
    """Tab panel for automated test-case management and execution."""

    def __init__(self, parent: tk.Widget, **kwargs: object) -> None:
        super().__init__(parent, **kwargs)
        self._program: Optional[Program] = None
        self._runner:  Optional[TestRunner] = None
        self._enum_thread: Optional[threading.Thread] = None
        self._stop_event   = threading.Event()
        self._result_queue: queue.Queue = queue.Queue()
        self._enum_running = False

        self._build_ui()

    # ──────────────────────────────────────────────────────── build UI
    def _build_ui(self) -> None:
        # ── top separator label ──────────────────────────────────────────
        top = ttk.Frame(self)
        top.pack(fill=tk.BOTH, expand=True)

        # ── left: test-case list ──────────────────────────────────────────
        left = ttk.LabelFrame(top, text="Test cases", padding=6)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(6, 3), pady=6)

        self._tc_listbox = tk.Listbox(left, width=22, height=18,
                                      selectmode=tk.SINGLE, exportselection=False)
        self._tc_listbox.pack(fill=tk.BOTH, expand=True)
        self._tc_listbox.bind("<<ListboxSelect>>", self._on_select_tc)

        btn_row = ttk.Frame(left)
        btn_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(btn_row, text="Add",    command=self._add_tc).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="Remove", command=self._remove_tc).pack(side=tk.LEFT, padx=2)

        # ── right: detail + execution ─────────────────────────────────────
        right = ttk.Frame(top)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(3, 6), pady=6)

        # Name
        name_row = ttk.Frame(right)
        name_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(name_row, text="Name:").pack(side=tk.LEFT)
        self._name_var = tk.StringVar()
        self._name_entry = ttk.Entry(name_row, textvariable=self._name_var, width=28)
        self._name_entry.pack(side=tk.LEFT, padx=4)
        ttk.Button(name_row, text="Save", command=self._save_current_tc).pack(side=tk.LEFT)

        # Input
        ttk.Label(right, text="Input data (space / newline separated integers):").pack(
            anchor=tk.W)
        self._input_text = tk.Text(right, height=4, wrap=tk.WORD, font=("Courier New", 10))
        self._input_text.pack(fill=tk.X, pady=(0, 6))

        # Expected output
        ttk.Label(right, text="Expected output (one integer per line):").pack(anchor=tk.W)
        self._expected_text = tk.Text(right, height=4, wrap=tk.WORD, font=("Courier New", 10))
        self._expected_text.pack(fill=tk.X, pady=(0, 6))

        # K parameter
        k_row = ttk.Frame(right)
        k_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(k_row, text="Max steps K (1-20):").pack(side=tk.LEFT)
        self._k_var = tk.IntVar(value=10)
        ttk.Spinbox(k_row, from_=1, to=20, textvariable=self._k_var,
                    width=5).pack(side=tk.LEFT, padx=6)

        # Action buttons
        btn_frame = ttk.Frame(right)
        btn_frame.pack(fill=tk.X, pady=(0, 6))
        self._run_btn = ttk.Button(btn_frame, text="Run single",
                                   command=self._run_single)
        self._run_btn.pack(side=tk.LEFT, padx=2)

        self._enum_btn = ttk.Button(btn_frame, text="Enumerate all",
                                    command=self._toggle_enumerate)
        self._enum_btn.pack(side=tk.LEFT, padx=2)

        ttk.Button(btn_frame, text="Reset verified",
                   command=self._reset_verified).pack(side=tk.LEFT, padx=2)

        # Progress bar
        self._progress = ttk.Progressbar(right, mode="indeterminate")
        self._progress.pack(fill=tk.X, pady=(0, 4))

        # Results
        res_frame = ttk.LabelFrame(right, text="Results", padding=6)
        res_frame.pack(fill=tk.BOTH, expand=True)

        self._status_lbl = ttk.Label(res_frame, text="—", font=("Helvetica", 10, "bold"))
        self._status_lbl.pack(anchor=tk.W)

        self._stats_lbl = ttk.Label(res_frame, text="", foreground="gray")
        self._stats_lbl.pack(anchor=tk.W)

        ttk.Label(res_frame, text="Actual output:").pack(anchor=tk.W, pady=(6, 0))
        self._actual_text = tk.Text(res_frame, height=5, state=tk.DISABLED,
                                    font=("Courier New", 10))
        self._actual_text.pack(fill=tk.BOTH, expand=True)

    # ──────────────────────────────────────────────────────── public API
    def refresh(self, program: Program) -> None:
        """Called whenever the program changes (new load, edit, etc.)."""
        self._program = program
        self._runner  = TestRunner(program)
        self._reload_listbox()

    # ──────────────────────────────────────────────────────── listbox helpers
    def _reload_listbox(self) -> None:
        self._tc_listbox.delete(0, tk.END)
        if self._program:
            for tc in self._program.test_cases:
                self._tc_listbox.insert(tk.END, tc.name)

    def _current_tc(self) -> Optional[TestCase]:
        if not self._program:
            return None
        sel = self._tc_listbox.curselection()
        if not sel:
            return None
        return self._program.test_cases[sel[0]]

    def _on_select_tc(self, _event: tk.Event) -> None:
        tc = self._current_tc()
        if tc is None:
            return
        self._name_var.set(tc.name)
        self._input_text.delete("1.0", tk.END)
        self._input_text.insert("1.0", tc.input_data)
        self._expected_text.delete("1.0", tk.END)
        self._expected_text.insert("1.0", tc.expected_output)
        self._clear_results()

    # ──────────────────────────────────────────────────────── CRUD
    def _add_tc(self) -> None:
        if self._program is None:
            messagebox.showwarning("No program", "Open or create a program first.")
            return
        n   = len(self._program.test_cases) + 1
        tc  = TestCase(name=f"Test {n}", input_data="", expected_output="")
        self._program.test_cases.append(tc)
        self._reload_listbox()
        self._tc_listbox.selection_clear(0, tk.END)
        self._tc_listbox.selection_set(tk.END)
        self._on_select_tc(None)

    def _remove_tc(self) -> None:
        if not self._program:
            return
        sel = self._tc_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        del self._program.test_cases[idx]
        self._reload_listbox()
        self._clear_results()

    def _save_current_tc(self) -> None:
        tc = self._current_tc()
        if tc is None:
            return
        tc.name           = self._name_var.get().strip() or tc.name
        tc.input_data     = self._input_text.get("1.0", tk.END).strip()
        tc.expected_output = self._expected_text.get("1.0", tk.END).strip()
        self._reload_listbox()
        idx = self._program.test_cases.index(tc)
        self._tc_listbox.selection_set(idx)

    # ──────────────────────────────────────────────────────── execution
    def _run_single(self) -> None:
        if not self._check_ready():
            return
        self._save_current_tc()
        tc = self._current_tc()

        result = self._runner.run_single(tc)
        self._show_result(
            passed=result.passed,
            actual=result.actual_output,
            extra=f"Steps taken: {result.steps_taken}",
        )

    def _toggle_enumerate(self) -> None:
        if self._enum_running:
            self._stop_enum()
        else:
            self._start_enum()

    def _start_enum(self) -> None:
        if not self._check_ready():
            return
        self._save_current_tc()
        tc = self._current_tc()

        self._stop_event.clear()
        self._enum_running = True
        self._enum_btn.configure(text="Stop enumeration")
        self._run_btn.configure(state=tk.DISABLED)
        self._progress.start(10)
        self._status_lbl.configure(text="Enumerating…", foreground="blue")

        def _worker() -> None:
            self._runner.enumerate(
                test_case=tc,
                max_steps=self._k_var.get(),
                progress_callback=self._on_enum_progress,
                stop_event=self._stop_event,
            )

        self._enum_thread = threading.Thread(target=_worker, daemon=True)
        self._enum_thread.start()
        self._poll_enum_queue()

    def _stop_enum(self) -> None:
        self._stop_event.set()

    def _poll_enum_queue(self) -> None:
        """Periodically drain the result queue and update the GUI."""
        try:
            while True:
                progress: EnumProgress = self._result_queue.get_nowait()
                self._apply_enum_progress(progress)
                if progress.finished:
                    self._finish_enum()
                    return
        except queue.Empty:
            pass
        if self._enum_running:
            self.after(150, self._poll_enum_queue)

    def _on_enum_progress(self, progress: EnumProgress) -> None:
        """Called from the worker thread – put into queue for main thread."""
        self._result_queue.put(progress)

    def _apply_enum_progress(self, p: EnumProgress) -> None:
        nd = " (non-deterministic)" if p.is_nondeterministic else ""
        self._stats_lbl.configure(
            text=(
                f"States explored: {p.states_explored} | "
                f"Terminal found: {p.terminal_found}{nd} | "
                f"Passed: {p.passed} | "
                f"Verified: {p.percent_verified:.1f}%"
            )
        )

    def _finish_enum(self) -> None:
        self._enum_running = False
        self._progress.stop()
        self._enum_btn.configure(text="Enumerate all")
        self._run_btn.configure(state=tk.NORMAL)
        interrupted = self._stop_event.is_set()
        self._status_lbl.configure(
            text="Enumeration stopped." if interrupted else "Enumeration complete.",
            foreground="orange" if interrupted else "green",
        )

    def _reset_verified(self) -> None:
        tc = self._current_tc()
        if tc and self._runner:
            self._runner.reset_verified(tc.id)
            self._stats_lbl.configure(text="Verification history reset.")

    # ──────────────────────────────────────────────────────── helpers
    def _check_ready(self) -> bool:
        if self._program is None or self._runner is None:
            messagebox.showwarning("No program", "Open or create a program first.")
            return False
        errors = self._program.validate()
        if errors:
            messagebox.showerror("Validation errors",
                                 "\n".join(errors))
            return False
        if self._current_tc() is None:
            messagebox.showwarning("No test case", "Select or add a test case first.")
            return False
        return True

    def _show_result(self, passed: bool, actual: str, extra: str = "") -> None:
        color = "green" if passed else "red"
        label = "PASSED" if passed else "FAILED"
        self._status_lbl.configure(text=label, foreground=color)
        self._stats_lbl.configure(text=extra)
        self._actual_text.configure(state=tk.NORMAL)
        self._actual_text.delete("1.0", tk.END)
        self._actual_text.insert("1.0", actual)
        self._actual_text.configure(state=tk.DISABLED)

    def _clear_results(self) -> None:
        self._status_lbl.configure(text="—", foreground="black")
        self._stats_lbl.configure(text="")
        self._actual_text.configure(state=tk.NORMAL)
        self._actual_text.delete("1.0", tk.END)
        self._actual_text.configure(state=tk.DISABLED)
