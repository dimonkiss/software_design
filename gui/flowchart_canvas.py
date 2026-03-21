"""
Interactive flowchart canvas widget.

Supported interactions
----------------------
SELECT mode
    Left-click         – select / deselect block
    Left-drag          – move selected block
    Double-left-click  – open block property editor
    Right-click        – context menu (edit / delete block, delete connection)
    Ctrl+A             – select all (future)

ADD_BLOCK mode
    Left-click on canvas – place a new block of the pre-selected type

CONNECT mode
    Left-click on source block  – start rubber-band line
    Left-click on target block  – create connection; ask branch for CONDITION
    Escape                      – cancel connection

Block shapes
------------
START / END   : oval
ASSIGN        : rectangle
INPUT / PRINT : parallelogram  (standard flowchart I/O symbol)
CONDITION     : diamond  (standard decision symbol)
"""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import messagebox, ttk

from gui.block_dialog import BranchDialog, open_block_dialog, open_new_block_dialog
from models.block import Block, BlockType, BLOCK_COLORS
from models.flowchart import Flowchart

# ──────────────────────────────────────────────────────────────── dimensions
BW   = 130   # block width
BH   = 48    # block height (for rect / oval / parallelogram)
DS   = 55    # diamond half-width (CONDITION)
DH   = 35    # diamond half-height

FONT      = ("Helvetica", 9)
FONT_BOLD = ("Helvetica", 9, "bold")

SEL_COLOR    = "#0055FF"
ARROW_COLOR  = "#333333"
RUBBER_COLOR = "#888888"


# ═══════════════════════════════════════════════════════════════════ geometry

def _block_poly(block: Block) -> List[float]:
    """Return polygon points for *block*'s shape (canvas coordinates)."""
    x, y = block.x, block.y
    bt = block.block_type

    if bt in (BlockType.START, BlockType.END):
        # Oval approximated as 12-gon so create_polygon can be used uniformly
        pts = []
        for i in range(12):
            a = math.radians(i * 30)
            pts += [x + BW / 2 * math.cos(a), y + BH / 2 * math.sin(a)]
        return pts

    if bt == BlockType.ASSIGN:
        hw, hh = BW / 2, BH / 2
        return [x - hw, y - hh,  x + hw, y - hh,
                x + hw, y + hh,  x - hw, y + hh]

    if bt in (BlockType.INPUT, BlockType.PRINT):
        hw, hh, sk = BW / 2, BH / 2, 14   # skew
        return [x - hw + sk, y - hh,  x + hw + sk, y - hh,
                x + hw - sk, y + hh,  x - hw - sk, y + hh]

    if bt == BlockType.CONDITION:
        return [x,      y - DH,
                x + DS, y,
                x,      y + DH,
                x - DS, y]

    return [x - BW / 2, y - BH / 2, x + BW / 2, y + BH / 2]


def _block_bbox(block: Block) -> Tuple[float, float, float, float]:
    """Bounding box (x0, y0, x1, y1) for *block*."""
    x, y = block.x, block.y
    if block.block_type == BlockType.CONDITION:
        return x - DS, y - DH, x + DS, y + DH
    if block.block_type in (BlockType.INPUT, BlockType.PRINT):
        return x - BW / 2 - 14, y - BH / 2, x + BW / 2 + 14, y + BH / 2
    return x - BW / 2, y - BH / 2, x + BW / 2, y + BH / 2


def _boundary_point(block: Block, tx: float, ty: float) -> Tuple[float, float]:
    """
    Return the point on *block*'s outline that lies on the line from
    block-centre toward (tx, ty).  Used to anchor arrow endpoints.
    """
    cx, cy = block.x, block.y
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy

    bt = block.block_type
    if bt == BlockType.CONDITION:
        # Diamond: |x-cx|/DS + |y-cy|/DH = 1
        denom = abs(dx) / DS + abs(dy) / DH
        t = 1.0 / denom
    elif bt in (BlockType.START, BlockType.END):
        # Ellipse: (dx/a)^2 + (dy/b)^2 = 1  → t = 1/sqrt(...)
        a, b = BW / 2, BH / 2
        t = 1.0 / math.sqrt((dx / a) ** 2 + (dy / b) ** 2)
    elif bt in (BlockType.INPUT, BlockType.PRINT):
        # Use rectangle bounding box for simplicity
        hw, hh = BW / 2 + 14, BH / 2
        t = min((hw / abs(dx)) if dx != 0 else 1e9,
                (hh / abs(dy)) if dy != 0 else 1e9)
    else:
        hw, hh = BW / 2, BH / 2
        t = min((hw / abs(dx)) if dx != 0 else 1e9,
                (hh / abs(dy)) if dy != 0 else 1e9)

    return cx + dx * t, cy + dy * t


def _condition_exit_point(block: Block, branch: int) -> Tuple[float, float]:
    """
    Return the canonical exit point for a CONDITION block.
    branch 0 → right vertex (TRUE), branch 1 → left vertex (FALSE).
    """
    x, y = block.x, block.y
    if branch == 0:
        return x + DS, y
    return x - DS, y


# ═══════════════════════════════════════════════════════════════════ widget

class FlowchartCanvas(ttk.Frame):
    """
    Interactive canvas for editing a single :class:`~models.flowchart.Flowchart`.
    """

    def __init__(
        self,
        parent: tk.Widget,
        flowchart: Flowchart,
        on_change: Optional[Callable[[], None]] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.flowchart  = flowchart
        self._on_change = on_change or (lambda: None)

        # ── canvas + scrollbars ────────────────────────────────────────────
        self._canvas = tk.Canvas(
            self, bg="white", cursor="arrow",
            scrollregion=(0, 0, 2000, 2000),
        )
        self._hbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL,
                                   command=self._canvas.xview)
        self._vbar = ttk.Scrollbar(self, orient=tk.VERTICAL,
                                   command=self._canvas.yview)
        self._canvas.configure(xscrollcommand=self._hbar.set,
                               yscrollcommand=self._vbar.set)

        self._hbar.grid(row=1, column=0, sticky=tk.EW)
        self._vbar.grid(row=0, column=1, sticky=tk.NS)
        self._canvas.grid(row=0, column=0, sticky=tk.NSEW)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # ── interaction state ──────────────────────────────────────────────
        self._mode:             str            = "select"
        self._add_block_type:   Optional[BlockType] = None
        self._selected_id:      Optional[str]  = None
        self._drag_origin:      Optional[Tuple[float, float]] = None
        self._drag_block_start: Optional[Tuple[float, float]] = None
        self._connect_src_id:   Optional[str]  = None
        self._rubber_line:      Optional[int]  = None  # canvas item id

        # ── bind events ───────────────────────────────────────────────────
        c = self._canvas
        c.bind("<Button-1>",         self._on_click)
        c.bind("<B1-Motion>",        self._on_drag)
        c.bind("<ButtonRelease-1>",  self._on_release)
        c.bind("<Double-Button-1>",  self._on_double_click)
        c.bind("<Button-3>",         self._on_right_click)
        c.bind("<Escape>",           self._on_escape)
        c.bind("<Delete>",           lambda e: self._delete_selected())
        # Scroll with mouse wheel
        c.bind("<MouseWheel>",       self._on_mousewheel)
        c.bind("<Shift-MouseWheel>", lambda e: self._canvas.xview_scroll(
            -1 if e.delta > 0 else 1, "units"))

        self.render()

    # ──────────────────────────────────────────────────────── public API
    def set_mode_select(self) -> None:
        self._mode = "select"
        self._connect_src_id = None
        self._remove_rubber_line()
        self._canvas.configure(cursor="arrow")

    def set_mode_add_block(self, block_type: BlockType) -> None:
        self._mode = "add_block"
        self._add_block_type = block_type
        self._connect_src_id = None
        self._remove_rubber_line()
        self._canvas.configure(cursor="crosshair")

    def set_mode_connect(self) -> None:
        self._mode = "connect"
        self._connect_src_id = None
        self._remove_rubber_line()
        self._canvas.configure(cursor="crosshair")

    def delete_selected(self) -> None:
        self._delete_selected()

    def reload(self, flowchart: Flowchart) -> None:
        """Replace the flowchart being edited and re-render."""
        self.flowchart = flowchart
        self._selected_id = None
        self._connect_src_id = None
        self._remove_rubber_line()
        self.render()

    # ──────────────────────────────────────────────────────── rendering
    def render(self) -> None:
        c = self._canvas
        c.delete("all")

        # Connections first (drawn behind blocks)
        for blk in self.flowchart.blocks.values():
            for i, next_id in enumerate(blk.next_blocks):
                if next_id and next_id in self.flowchart.blocks:
                    self._draw_connection(blk, next_id, i)

        # Blocks on top
        for blk in self.flowchart.blocks.values():
            self._draw_block(blk)

        # Rubber-band line stays on top
        if self._rubber_line:
            c.tag_raise(self._rubber_line)

    # ──────────────────────────────────────────────────────── draw helpers
    def _draw_block(self, block: Block) -> None:
        c    = self._canvas
        tag  = f"block_{block.id}"
        pts  = _block_poly(block)
        fill = BLOCK_COLORS.get(block.block_type, "#FFFFFF")
        outline = SEL_COLOR if block.id == self._selected_id else "black"
        width   = 3 if block.id == self._selected_id else 2

        c.create_polygon(pts, fill=fill, outline=outline, width=width,
                         tags=(tag, "block", "block_shape"))
        c.create_text(block.x, block.y, text=block.get_multiline_label(),
                      font=FONT_BOLD if block.block_type in (BlockType.START, BlockType.END) else FONT,
                      fill="#111111",
                      justify=tk.CENTER, tags=(tag, "block", "block_text"))

        if block.block_type == BlockType.CONDITION:
            # Label the branches
            x, y = block.x, block.y
            c.create_text(x + DS + 8, y - 6, text="T", fill="green",
                          font=("Helvetica", 8, "bold"), anchor=tk.W, tags=("conn_label",))
            c.create_text(x - DS - 8, y - 6, text="F", fill="red",
                          font=("Helvetica", 8, "bold"), anchor=tk.E, tags=("conn_label",))

    def _draw_connection(self, src: Block, dst_id: str, branch_idx: int) -> None:
        dst = self.flowchart.blocks.get(dst_id)
        if dst is None:
            return
        c = self._canvas

        # Source exit point
        if src.block_type == BlockType.CONDITION:
            sx, sy = _condition_exit_point(src, branch_idx)
        else:
            sx, sy = _boundary_point(src, dst.x, dst.y)

        # Target entry point (clipped to boundary coming from source)
        tx, ty = _boundary_point(dst, sx, sy)

        tag = f"conn_{src.id}_{dst_id}_{branch_idx}"
        color = "green" if (src.block_type == BlockType.CONDITION and branch_idx == 0) \
            else ("red" if (src.block_type == BlockType.CONDITION and branch_idx == 1) \
            else ARROW_COLOR)

        c.create_line(sx, sy, tx, ty,
                      arrow=tk.LAST, arrowshape=(10, 12, 5),
                      fill=color, width=2,
                      tags=(tag, "connection", f"conn_src_{src.id}",
                            f"conn_dst_{dst_id}"))

    # ──────────────────────────────────────────────────────── hit testing
    def _canvas_xy(self, event: tk.Event) -> Tuple[float, float]:
        return (self._canvas.canvasx(event.x),
                self._canvas.canvasy(event.y))

    def _block_at(self, cx: float, cy: float) -> Optional[str]:
        """Return block id at canvas position or None."""
        items = self._canvas.find_overlapping(cx - 2, cy - 2, cx + 2, cy + 2)
        for item in reversed(items):
            for tag in self._canvas.gettags(item):
                if tag.startswith("block_") and not tag.startswith("block_shape") \
                        and not tag.startswith("block_text"):
                    return tag[len("block_"):]
            # Also check shape/text tags
        for item in reversed(items):
            for tag in self._canvas.gettags(item):
                if tag == "block_shape" or tag == "block_text" or tag == "block":
                    # find the block_ tag in the same item
                    for t in self._canvas.gettags(item):
                        if t.startswith("block_") and t not in ("block_shape", "block_text"):
                            return t[len("block_"):]
        return None

    def _connection_at(self, cx: float, cy: float):
        """Return (src_id, dst_id, branch) for a connection near (cx, cy), or None."""
        items = self._canvas.find_overlapping(cx - 4, cy - 4, cx + 4, cy + 4)
        for item in items:
            tags = self._canvas.gettags(item)
            if "connection" in tags:
                # Extract src and dst from tags
                src_id = dst_id = None
                for t in tags:
                    if t.startswith("conn_src_"):
                        src_id = t[len("conn_src_"):]
                    elif t.startswith("conn_dst_"):
                        dst_id = t[len("conn_dst_"):]
                if src_id and dst_id:
                    return src_id, dst_id
        return None

    # ──────────────────────────────────────────────────────── event handlers
    def _on_click(self, event: tk.Event) -> None:
        cx, cy = self._canvas_xy(event)

        if self._mode == "select":
            bid = self._block_at(cx, cy)
            if bid:
                self._selected_id = bid
            else:
                self._selected_id = None
            self.render()

        elif self._mode == "add_block":
            self._place_block(cx, cy)

        elif self._mode == "connect":
            bid = self._block_at(cx, cy)
            if bid is None:
                return
            if self._connect_src_id is None:
                self._connect_src_id = bid
                self._selected_id = bid
                self.render()
            else:
                self._finish_connection(bid)

    def _on_drag(self, event: tk.Event) -> None:
        cx, cy = self._canvas_xy(event)

        if self._mode == "select" and self._selected_id:
            if self._drag_origin is None:
                blk = self.flowchart.blocks.get(self._selected_id)
                if blk:
                    self._drag_origin = (cx, cy)
                    self._drag_block_start = (blk.x, blk.y)
            else:
                ox, oy = self._drag_origin
                bx, by = self._drag_block_start
                blk = self.flowchart.blocks.get(self._selected_id)
                if blk:
                    blk.x = bx + (cx - ox)
                    blk.y = by + (cy - oy)
                    self.render()

        elif self._mode == "connect" and self._connect_src_id:
            self._update_rubber_line(cx, cy)

    def _on_release(self, event: tk.Event) -> None:
        if self._drag_origin is not None:
            self._drag_origin = None
            self._drag_block_start = None
            self._on_change()

    def _on_double_click(self, event: tk.Event) -> None:
        cx, cy = self._canvas_xy(event)
        bid = self._block_at(cx, cy)
        if bid:
            self._edit_block(bid)

    def _on_right_click(self, event: tk.Event) -> None:
        cx, cy = self._canvas_xy(event)
        bid  = self._block_at(cx, cy)
        conn = self._connection_at(cx, cy) if not bid else None

        menu = tk.Menu(self._canvas, tearoff=False)

        if bid:
            menu.add_command(label="Edit block",   command=lambda: self._edit_block(bid))
            menu.add_command(label="Delete block",  command=lambda: self._delete_block(bid))
        elif conn:
            src_id, dst_id = conn
            menu.add_command(label="Delete connection",
                             command=lambda: self._delete_connection(src_id, dst_id))
        else:
            return

        menu.tk_popup(event.x_root, event.y_root)

    def _on_escape(self, event: tk.Event) -> None:
        self._connect_src_id = None
        self._remove_rubber_line()
        self.render()

    def _on_mousewheel(self, event: tk.Event) -> None:
        self._canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    # ──────────────────────────────────────────────────────── block actions
    def _place_block(self, cx: float, cy: float) -> None:
        if self._add_block_type is None:
            return
        bt = self._add_block_type

        # Quick-fill for START/END
        if bt in (BlockType.START, BlockType.END):
            content: Dict = {}
        else:
            content = open_new_block_dialog(self._canvas, bt)
            if content is None:
                return  # user cancelled

        blk = Block(block_type=bt, content=content, x=cx, y=cy)

        # Enforce single START
        if bt == BlockType.START:
            for existing in self.flowchart.blocks.values():
                if existing.block_type == BlockType.START:
                    messagebox.showerror("Error",
                        "Only one START block is allowed per flowchart.",
                        parent=self._canvas)
                    return

        self.flowchart.add_block(blk)
        self._selected_id = blk.id
        self._on_change()
        self.render()

    def _edit_block(self, block_id: str) -> None:
        blk = self.flowchart.blocks.get(block_id)
        if not blk:
            return
        result = open_block_dialog(self._canvas, blk)
        if result is not None:
            blk.content = result
            self._on_change()
            self.render()

    def _delete_block(self, block_id: str) -> None:
        self.flowchart.remove_block(block_id)
        if self._selected_id == block_id:
            self._selected_id = None
        self._on_change()
        self.render()

    def _delete_selected(self) -> None:
        if self._selected_id:
            self._delete_block(self._selected_id)

    def _delete_connection(self, src_id: str, dst_id: str) -> None:
        self.flowchart.remove_connection(src_id, dst_id)
        self._on_change()
        self.render()

    # ──────────────────────────────────────────────────────── connections
    def _finish_connection(self, dst_id: str) -> None:
        src_id = self._connect_src_id
        self._connect_src_id = None
        self._remove_rubber_line()

        if src_id == dst_id:
            messagebox.showwarning("Connection",
                "Cannot connect a block to itself.", parent=self._canvas)
            self.render()
            return

        src = self.flowchart.blocks.get(src_id)
        if src is None:
            self.render()
            return

        branch: Optional[str] = None
        if src.block_type == BlockType.CONDITION:
            connected = [nid for nid in src.next_blocks if nid and nid in self.flowchart.blocks]
            if len(connected) >= 2:
                messagebox.showerror("Connection",
                    "CONDITION block already has both branches connected.\n"
                    "Delete an existing connection first.",
                    parent=self._canvas)
                self.render()
                return
            dlg = BranchDialog(self._canvas)
            branch = dlg.branch
            if branch is None:
                self.render()
                return

        ok = self.flowchart.add_connection(src_id, dst_id, branch)
        if not ok:
            messagebox.showerror("Connection",
                "Could not add connection (check block limits).",
                parent=self._canvas)
        self._on_change()
        self.render()

    def _update_rubber_line(self, cx: float, cy: float) -> None:
        src = self.flowchart.blocks.get(self._connect_src_id)
        if src is None:
            return
        if self._rubber_line:
            self._canvas.delete(self._rubber_line)
        self._rubber_line = self._canvas.create_line(
            src.x, src.y, cx, cy,
            dash=(4, 4), fill=RUBBER_COLOR, width=1,
            tags=("rubber_line",),
        )

    def _remove_rubber_line(self) -> None:
        if self._rubber_line:
            self._canvas.delete(self._rubber_line)
            self._rubber_line = None
