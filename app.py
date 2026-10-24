"""ZoneEntry - fast inventory-zone entry with Excel export.

Keyboard flow for one row (never needs the mouse):

    Store Zone: type a few letters  ->  Enter   (takes the top suggestion)
    End Zone:   type the number     ->  Enter   (row is added)
    ...the Start Zone was already filled in with previous End + 1.

Run:  python app.py
"""
from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

import zonelogic as zl

__version__ = "1.0.0"

MOD = "Command" if sys.platform == "darwin" else "Control"
MODNAME = "Cmd" if sys.platform == "darwin" else "Ctrl"
ERROR_FG = "#c62828"


def enable_hidpi() -> None:
    """Without this, Tk text looks blurry on Windows laptops with display scaling."""
    if sys.platform != "win32":
        return
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# =============================================================================
# Widgets
# =============================================================================
class AutocompleteEntry(ttk.Entry):
    """Entry with a filter-as-you-type suggestion list.

    * typing filters the list (prefix matches first, then word starts, then contains)
    * Up/Down move through suggestions, Enter or Tab accepts the highlighted one
    * Enter with the list hidden still calls on_commit(text) so the caller can validate
    The list is a plain Listbox placed inside the window (not a separate popup
    window), so keyboard focus never leaves the entry.
    """

    MAX_ROWS = 8

    def __init__(self, master, get_values, on_commit=None, list_font=None, **kw):
        self.var = tk.StringVar()
        super().__init__(master, textvariable=self.var, **kw)
        self._get_values = get_values
        self._on_commit = on_commit
        self._list_font = list_font
        self._matches: list[str] = []
        self._muted = False
        self._visible = False
        self._lb: tk.Listbox | None = None

        self.var.trace_add("write", self._text_changed)
        self.bind("<Down>", self._key_down)
        self.bind("<Up>", self._key_up)
        self.bind("<Return>", self._key_return)
        self.bind("<KP_Enter>", self._key_return)
        self.bind("<Tab>", self._key_tab)
        self.bind("<Escape>", self._key_escape)
        self.bind("<FocusOut>", lambda _e: self.hide())
        self.bind("<FocusIn>", lambda _e: self.after_idle(self.select_range, 0, "end"))

    # -- public ---------------------------------------------------------------
    def set(self, text: str) -> None:
        self._muted = True
        try:
            self.var.set(text)
        finally:
            self._muted = False
        self.icursor("end")
        self.hide()

    def clear(self) -> None:
        self.set("")

    def hide(self) -> None:
        if self._lb is not None:
            self._lb.place_forget()
        self._visible = False

    def accept(self, value: str) -> None:
        self.set(value)
        if self._on_commit:
            self._on_commit(value)

    # -- popup ----------------------------------------------------------------
    def _listbox(self) -> tk.Listbox:
        if self._lb is None:
            lb = tk.Listbox(
                self.winfo_toplevel(),
                height=1,
                activestyle="none",
                exportselection=False,
                takefocus=0,
                borderwidth=1,
                relief="solid",
                highlightthickness=0,
                font=self._list_font,
            )
            lb.bind("<Button-1>", self._click)  # handled here so the entry keeps focus
            self._lb = lb
        return self._lb

    def _show(self) -> None:
        if not self._matches:
            self.hide()
            return
        lb = self._listbox()
        lb.delete(0, "end")
        lb.insert("end", *self._matches)
        lb.configure(height=min(len(self._matches), self.MAX_ROWS))
        top = self.winfo_toplevel()
        x = self.winfo_rootx() - top.winfo_rootx()
        y = self.winfo_rooty() - top.winfo_rooty() + self.winfo_height()
        lb.place(x=x, y=y, width=max(self.winfo_width(), 240))
        lb.lift()
        self._select(0)
        self._visible = True

    def _select(self, index: int) -> None:
        lb = self._lb
        if lb is None or not self._matches:
            return
        index = max(0, min(index, len(self._matches) - 1))
        lb.selection_clear(0, "end")
        lb.selection_set(index)
        lb.activate(index)
        lb.see(index)

    def _index(self) -> int:
        sel = self._lb.curselection() if self._lb is not None else ()
        return sel[0] if sel else 0

    # -- events ---------------------------------------------------------------
    def _text_changed(self, *_):
        if self._muted:
            return
        text = self.var.get().strip()
        if not text:
            self.hide()
            return
        self._matches = zl.filter_zones(text, self._get_values())
        self._show()

    def _key_down(self, _e):
        if not self._visible:
            self._matches = zl.filter_zones(self.var.get(), self._get_values())
            self._show()
        else:
            self._select(self._index() + 1)
        return "break"

    def _key_up(self, _e):
        if self._visible:
            self._select(self._index() - 1)
            return "break"

    def _key_return(self, _e):
        if self._visible and self._matches:
            self.accept(self._matches[self._index()])
        elif self._on_commit:
            self._on_commit(self.var.get())
        return "break"

    def _key_tab(self, _e):
        if self._visible and self._matches:
            self.accept(self._matches[self._index()])
            return "break"

    def _key_escape(self, _e):
        if self._visible:
            self.hide()
            return "break"

    def _click(self, e):
        if self._lb is not None and self._matches:
            self.accept(self._matches[self._lb.nearest(e.y)])
        return "break"


class ZoneNumberEntry(ttk.Entry):
    """4-digit entry: digits only, left-padded with zeros when you leave it."""

    def __init__(self, master, **kw):
        self.var = tk.StringVar()
        vcmd = (master.register(self._validate), "%P")
        super().__init__(
            master,
            textvariable=self.var,
            width=7,
            justify="center",
            validate="key",
            validatecommand=vcmd,
            **kw,
        )
        self.bind("<FocusIn>", lambda _e: self.after_idle(self.select_range, 0, "end"))
        self.bind("<FocusOut>", lambda _e: self.pad_now())

    @staticmethod
    def _validate(proposed: str) -> bool:
        return proposed == "" or (len(proposed) <= 4 and proposed.isascii() and proposed.isdigit())

    def pad_now(self) -> None:
        t = self.var.get().strip()
        if t.isdigit() and int(t) > 0:
            self.var.set(t.zfill(4))


class ZoneListDialog(tk.Toplevel):
    """Edit the predefined Store Zone list (one name per line)."""

    def __init__(self, master, zones, defaults, on_save):
        super().__init__(master)
        self.title("Store Zone list")
        self.transient(master)
        self.geometry("380x520")
        self._on_save = on_save
        self._defaults = defaults

        ttk.Label(
            self,
            text="One Store Zone per line. Existing rows are not changed.",
            padding=(12, 10, 12, 4),
        ).pack(anchor="w")
        frame = ttk.Frame(self, padding=(12, 0))
        frame.pack(fill="both", expand=True)
        self.text = tk.Text(frame, wrap="none", undo=True, font=master.big)
        sb = ttk.Scrollbar(frame, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.text.insert("1.0", "\n".join(zones))

        bar = ttk.Frame(self, padding=12)
        bar.pack(fill="x")
        ttk.Button(bar, text="Reset to defaults", command=self._reset).pack(side="left")
        ttk.Button(bar, text="Save", command=self._save).pack(side="right")
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right", padx=6)
        self.bind("<Escape>", lambda _e: self.destroy())
        self.text.focus_set()
        self.grab_set()

    def _reset(self):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", "\n".join(self._defaults))

    def _save(self):
        zones = zl.parse_zone_lines(self.text.get("1.0", "end"))
        if not zones:
            messagebox.showwarning("Store Zone list", "The list can't be empty.", parent=self)
            return
        self._on_save(zones)
        self.destroy()


# =============================================================================
# Main window
# =============================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"ZoneEntry {__version__} – Inventory Zones")
        self.minsize(860, 580)
        self.geometry("1000x700")

        self.data_dir = zl.app_data_dir()
        self.zones: list[str] = zl.load_zones(self.data_dir)
        session = zl.load_session(self.data_dir)
        self.entries: list[zl.Entry] = session["entries"]
        self.last_dir: str = session["last_dir"]
        self.history: list[list[zl.Entry]] = []
        self.edit_index: int | None = None

        base = tkfont.nametofont("TkDefaultFont")
        size = abs(int(base.cget("size")))
        self.big = tkfont.Font(family=base.cget("family"), size=size + 3)
        self.bold = tkfont.Font(family=base.cget("family"), size=size, weight="bold")
        self.small = tkfont.Font(family=base.cget("family"), size=max(size - 1, 8))

        self.store = tk.StringVar(value=session["store"])
        self.status = tk.StringVar()
        self.summary = tk.StringVar()
        self.hint = tk.StringVar()

        self._build()
        self._bind_keys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.store.trace_add("write", lambda *_: self._save_session())

        self.refresh()
        self.update_suggestion()
        if self.entries:
            self.info(f"Restored {len(self.entries)} rows from your last session.")
        else:
            self.info("Ready. Type a Store Zone to begin.")
        self._focus_job = self.after(100, self.zone.focus_set)

    # ------------------------------------------------------------------ layout
    def _build(self):
        style = ttk.Style(self)
        style.configure("Treeview", rowheight=int(self.big.metrics("linespace") * 1.5), font=self.big)
        style.configure("Treeview.Heading", font=self.bold)
        self._default_fg = style.lookup("TLabel", "foreground") or "black"

        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        # top bar
        top = ttk.Frame(main)
        top.pack(fill="x")
        ttk.Label(top, text="Store / location:").pack(side="left")
        self.store_entry = ttk.Entry(top, textvariable=self.store, width=34, font=self.big)
        self.store_entry.pack(side="left", padx=8)
        ttk.Label(top, text="(only used for the file name)", font=self.small).pack(side="left")
        ttk.Button(top, text="New list", command=self.new_list).pack(side="right")
        ttk.Button(top, text="Zone list…", command=self.edit_zone_list).pack(side="right", padx=6)
        ttk.Button(top, text="Import…", command=self.import_file).pack(side="right")

        # entry box
        box = ttk.LabelFrame(main, text="New entry", padding=10)
        box.pack(fill="x", pady=(12, 6))
        ttk.Label(box, text="Store Zone", font=self.bold).grid(row=0, column=0, sticky="w")
        ttk.Label(box, text="Start Zone", font=self.bold).grid(row=0, column=1, sticky="w", padx=(16, 0))
        ttk.Label(box, text="End Zone", font=self.bold).grid(row=0, column=2, sticky="w", padx=(16, 0))

        self.zone = AutocompleteEntry(
            box,
            get_values=lambda: self.zones,
            on_commit=self._zone_committed,
            list_font=self.big,
            width=26,
            font=self.big,
        )
        self.zone.grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.start = ZoneNumberEntry(box, font=self.big)
        self.start.grid(row=1, column=1, sticky="w", padx=(16, 0), pady=(2, 0))
        self.end = ZoneNumberEntry(box, font=self.big)
        self.end.grid(row=1, column=2, sticky="w", padx=(16, 0), pady=(2, 0))
        self.add_btn = ttk.Button(box, text="Add  ⏎", command=self.submit, width=10)
        self.add_btn.grid(row=1, column=3, padx=(16, 0), pady=(2, 0))
        ttk.Label(box, textvariable=self.hint, font=self.small).grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(6, 0)
        )

        self.start.bind("<Return>", self._start_enter)
        self.start.bind("<KP_Enter>", self._start_enter)
        self.end.bind("<Return>", self.submit)
        self.end.bind("<KP_Enter>", self.submit)

        # table
        wrap = ttk.Frame(main)
        wrap.pack(fill="both", expand=True, pady=(6, 6))
        cols = ("n", "from", "to", "zone", "count")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="extended")
        for key, title, width, anchor in (
            ("n", "#", 50, "center"),
            ("from", "from", 110, "center"),
            ("to", "to", 110, "center"),
            ("zone", "Division", 320, "w"),
            ("count", "Zones", 80, "center"),
        ):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor=anchor, stretch=(key == "zone"))
        self.tree.tag_configure("odd", background="#f3f6fa", foreground="#111111")
        self.tree.tag_configure("even", background="#ffffff", foreground="#111111")
        self.tree.tag_configure("editing", background="#fff3c4", foreground="#111111")
        sb = ttk.Scrollbar(wrap, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        # actions
        bar = ttk.Frame(main)
        bar.pack(fill="x")
        ttk.Button(bar, text="Edit  (F2)", command=self.edit_selected).pack(side="left")
        ttk.Button(bar, text="Delete  (Del)", command=self.delete_selected).pack(side="left", padx=6)
        ttk.Button(bar, text=f"Undo  ({MODNAME}+Z)", command=self.undo).pack(side="left")
        self.export_btn = ttk.Button(bar, text=f"Export to Excel…  ({MODNAME}+S)", command=self.export)
        self.export_btn.pack(side="right")

        # status bar
        sbar = ttk.Frame(main)
        sbar.pack(fill="x", pady=(10, 0))
        self.status_lbl = ttk.Label(sbar, textvariable=self.status)
        self.status_lbl.pack(side="left")
        ttk.Label(sbar, textvariable=self.summary, font=self.small).pack(side="right")

    def _bind_keys(self):
        self.tree.bind("<Double-1>", self._tree_double_click)
        self.tree.bind("<Return>", lambda _e: self.edit_selected())
        self.tree.bind("<F2>", lambda _e: self.edit_selected())
        self.tree.bind("<Delete>", lambda _e: self.delete_selected())
        self.tree.bind("<BackSpace>", lambda _e: self.delete_selected())
        self.bind("<F2>", lambda _e: self.edit_selected())
        self.bind("<Escape>", lambda _e: self.cancel_edit())
        for seq, fn in (("z", self.undo), ("s", self.export), ("e", self.export)):
            try:
                self.bind_all(f"<{MOD}-{seq}>", lambda _e, f=fn: (f(), "break")[1])
            except tk.TclError:
                pass

    # ----------------------------------------------------------------- status
    def info(self, msg: str) -> None:
        self.status.set(msg)
        self.status_lbl.configure(foreground=self._default_fg)

    def error(self, msg: str, field: tk.Widget | None = None) -> str:
        self.status.set("⚠  " + msg)
        self.status_lbl.configure(foreground=ERROR_FG)
        self.bell()
        if field is not None:
            field.focus_set()
        return "break"

    def update_summary(self) -> None:
        n = len(self.entries)
        if not n:
            self.summary.set("No rows yet")
            return
        lo = min(e.first for e in self.entries)
        hi = max(e.last for e in self.entries)
        text = f"{n} rows · {zl.pad(lo)}–{zl.pad(hi)} · {sum(e.count for e in self.entries)} zones"
        gaps = zl.find_gaps(self.entries)
        if gaps:
            shown = ", ".join(zl.fmt_range(a, b) for a, b in gaps[:3])
            more = f" +{len(gaps) - 3}" if len(gaps) > 3 else ""
            text += f" · not covered: {shown}{more}"
        self.summary.set(text)

    # ------------------------------------------------------------------ table
    def refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for i, e in enumerate(self.entries):
            tag = "editing" if i == self.edit_index else ("odd" if i % 2 else "even")
            self.tree.insert("", "end", iid=str(i), values=(i + 1, e.start, e.end, e.zone, e.count), tags=(tag,))
        if self.entries:
            self.tree.see(str(len(self.entries) - 1))
        self.update_summary()

    def update_suggestion(self) -> None:
        """Fill Start with previous End + 1 and clear the End field."""
        if self.edit_index is not None:
            return
        last = self.entries[-1] if self.entries else None
        if last is None:
            self.start.var.set("")
            self.hint.set("First row: type the Start Zone yourself (e.g. 0001), then the End Zone.")
        else:
            nxt = zl.next_start(last.end)
            if nxt is None:
                self.start.var.set("")
                self.hint.set("Zone 9999 reached – there is no next zone.")
            else:
                self.start.var.set(nxt)
                self.hint.set(f"Start Zone suggested: {nxt}  (previous End {last.end} + 1) – overwrite it if the numbering skips.")
        self.end.var.set("")

    def _tree_double_click(self, e):
        iid = self.tree.identify_row(e.y)
        if iid:
            self.begin_edit(int(iid))

    # ------------------------------------------------------------------ input
    def _zone_committed(self, text: str) -> None:
        zone = zl.resolve_zone(text, self.zones)
        if zone is None:
            t = text.strip()
            msg = (
                f"'{t}' is not in the Store Zone list (add it via “Zone list…”)."
                if t
                else "Type a few letters of the Store Zone first."
            )
            self.error(msg, self.zone)
            return
        self.zone.set(zone)
        self.info(f"{zone} selected.")
        (self.end if self.start.var.get().strip() else self.start).focus_set()

    def _start_enter(self, _e=None):
        self.start.pad_now()
        self.end.focus_set()
        return "break"

    def submit(self, _e=None):
        zone_text = self.zone.var.get().strip()
        zone = zl.resolve_zone(zone_text, self.zones)
        if zone is None:
            return self.error(
                f"'{zone_text}' is not in the Store Zone list." if zone_text else "Pick a Store Zone first.",
                self.zone,
            )
        try:
            start = zl.normalize_zone(self.start.var.get(), "Start Zone")
        except zl.ZoneError as exc:
            return self.error(str(exc), self.start)
        try:
            end = zl.normalize_zone(self.end.var.get(), "End Zone")
        except zl.ZoneError as exc:
            return self.error(str(exc), self.end)
        if int(end) < int(start):
            return self.error(f"End Zone {end} is smaller than Start Zone {start}.", self.end)

        hit = zl.find_overlap(self.entries, start, end, skip_index=self.edit_index)
        if hit is not None:
            o = self.entries[hit]
            if not messagebox.askyesno(
                "Overlapping zones",
                f"{start}–{end} overlaps with row {hit + 1}:\n\n    {o.label()}\n\nAdd it anyway?",
                icon="warning",
                default="no",
                parent=self,
            ):
                self.start.focus_set()
                return "break"

        entry = zl.Entry(start, end, zone)
        self._push_history()
        if self.edit_index is None:
            prev = self.entries[-1] if self.entries else None
            self.entries.append(entry)
            msg = f"Added  {entry.label()}"
            skipped = zl.skipped_between(int(prev.end), int(start)) if prev is not None else None
            if skipped:
                msg += f"   ⚠ skips {zl.fmt_range(*skipped)}"
            elif prev is not None and int(start) <= int(prev.end):
                msg += "   ⚠ not after the previous row"
        else:
            self.entries[self.edit_index] = entry
            msg = f"Row {self.edit_index + 1} updated:  {entry.label()}"
            self.edit_index = None
            self.add_btn.configure(text="Add  ⏎")

        self.zone.clear()
        self.refresh()
        self.update_suggestion()
        self.info(msg)
        self._save_session()
        self.zone.focus_set()
        return "break"

    # ------------------------------------------------------- edit/delete/undo
    def _push_history(self) -> None:
        self.history.append(list(self.entries))
        del self.history[:-200]

    def edit_selected(self) -> None:
        sel = self.tree.selection()
        if sel:
            self.begin_edit(int(sel[0]))

    def begin_edit(self, index: int) -> None:
        e = self.entries[index]
        self.edit_index = index
        self.zone.set(e.zone)
        self.start.var.set(e.start)
        self.end.var.set(e.end)
        self.add_btn.configure(text="Save  ⏎")
        self.hint.set(f"Editing row {index + 1} – Enter saves, Esc cancels.")
        self.refresh()
        self.end.focus_set()

    def cancel_edit(self) -> None:
        if self.edit_index is None:
            return
        self.edit_index = None
        self.add_btn.configure(text="Add  ⏎")
        self.zone.clear()
        self.refresh()
        self.update_suggestion()
        self.info("Edit cancelled.")
        self.zone.focus_set()

    def delete_selected(self) -> None:
        sel = sorted((int(i) for i in self.tree.selection()), reverse=True)
        if not sel:
            return
        self.cancel_edit()
        self._push_history()
        for i in sel:
            del self.entries[i]
        self.refresh()
        self.update_suggestion()
        self.info(f"Deleted {len(sel)} row(s). Undo with {MODNAME}+Z.")
        self._save_session()

    def undo(self) -> None:
        if not self.history:
            self.info("Nothing to undo.")
            return
        self.entries = self.history.pop()
        self.edit_index = None
        self.add_btn.configure(text="Add  ⏎")
        self.zone.clear()
        self.refresh()
        self.update_suggestion()
        self.info("Undone.")
        self._save_session()

    def new_list(self) -> None:
        if self.entries and not messagebox.askyesno(
            "New list",
            f"Clear all {len(self.entries)} rows and start a new store?\n(You can still undo with {MODNAME}+Z.)",
            parent=self,
        ):
            return
        if self.entries:
            self._push_history()
        self.entries = []
        self.edit_index = None
        self.add_btn.configure(text="Add  ⏎")
        self.zone.clear()
        self.store.set("")
        self.refresh()
        self.update_suggestion()
        self.info("New list. Enter the store name, then the first Store Zone.")
        self._save_session()
        self.store_entry.focus_set()

    # ------------------------------------------------------------ zone list
    def edit_zone_list(self) -> None:
        def save(zones: list[str]) -> None:
            self.zones = zones
            try:
                zl.save_zones(self.data_dir, zones)
            except OSError as exc:
                self.error(f"Could not save the zone list: {exc}")
                return
            self.info(f"Zone list saved ({len(zones)} zones).")

        ZoneListDialog(self, self.zones, zl.DEFAULT_STORE_ZONES, save)

    # -------------------------------------------------------------- Excel I/O
    def _initial_dir(self) -> str:
        if self.last_dir and os.path.isdir(self.last_dir):
            return self.last_dir
        for name in ("Documents", "Desktop"):
            p = Path.home() / name
            if p.is_dir():
                return str(p)
        return str(Path.home())

    def export(self) -> None:
        if not self.entries:
            messagebox.showinfo("Export", "There are no rows to export yet.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export to Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
            initialdir=self._initial_dir(),
            initialfile=zl.default_export_name(self.store.get()),
        )
        if not path:
            return
        try:
            zl.export_xlsx(path, self.entries)
        except PermissionError:
            messagebox.showerror(
                "Can't save",
                f"{os.path.basename(path)} can't be written.\nIs it open in Excel? Close it and try again.",
                parent=self,
            )
            return
        except OSError as exc:
            messagebox.showerror("Can't save", str(exc), parent=self)
            return
        self.last_dir = os.path.dirname(path)
        self._save_session()
        self.info(f"Exported {len(self.entries)} rows → {path}")

    def import_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Import a zone sheet",
            filetypes=[("Excel workbook", "*.xlsx")],
            initialdir=self._initial_dir(),
        )
        if not path:
            return
        try:
            entries, problems = zl.import_xlsx(path)
        except zl.ZoneError as exc:
            messagebox.showerror("Import", str(exc), parent=self)
            return
        except Exception as exc:  # corrupt / locked file
            messagebox.showerror("Import", f"Could not read the file:\n{exc}", parent=self)
            return
        if not entries:
            messagebox.showinfo("Import", "No usable rows found in that file.", parent=self)
            return
        if self.entries and not messagebox.askokcancel(
            "Import",
            f"This replaces the {len(self.entries)} rows currently in the list "
            f"with {len(entries)} rows from the file.\n(Undo brings them back.)",
            parent=self,
        ):
            return
        known = {z.casefold() for z in self.zones}
        new_zones = []
        for e in entries:
            if e.zone and e.zone.casefold() not in known:
                known.add(e.zone.casefold())
                new_zones.append(e.zone)
        if new_zones:
            self.zones.extend(new_zones)
            try:
                zl.save_zones(self.data_dir, self.zones)
            except OSError:
                pass
        self._push_history()
        self.cancel_edit()
        self.entries = entries
        self.refresh()
        self.update_suggestion()
        msg = f"Imported {len(entries)} rows."
        if new_zones:
            msg += f" Added {len(new_zones)} new zone name(s) to your list."
        if problems:
            msg += f" Skipped {len(problems)} bad row(s)."
            messagebox.showwarning("Import", "Skipped rows:\n\n" + "\n".join(problems[:15]), parent=self)
        self.info(msg)
        self._save_session()
        self.zone.focus_set()

    # ------------------------------------------------------------ persistence
    def _save_session(self) -> None:
        try:
            zl.save_session(self.data_dir, self.store.get(), self.entries, self.last_dir)
        except OSError:
            pass  # never interrupt data entry because autosave failed

    def _on_close(self) -> None:
        self._save_session()
        self.destroy()

    def destroy(self) -> None:
        try:
            self.after_cancel(self._focus_job)
        except (AttributeError, tk.TclError):
            pass
        super().destroy()


def main() -> None:
    enable_hidpi()
    App().mainloop()


if __name__ == "__main__":
    main()
