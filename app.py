"""ZoneEntry - fast inventory-zone entry with Excel export.

Keyboard flow for one row (never needs the mouse):

    Store Zone: type a few letters  ->  Enter   (takes the top suggestion)
    End Zone:   type the number     ->  Enter   (row is added)
    ...the Start Zone was already filled in with previous End + 1.

Run:  python app.py            (add --selftest to start, check and quit)
"""
from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from tkinter import font as tkfont

import i18n
import zonelogic as zl
from i18n import LANGUAGES, tr
from version import __version__
from widgets import (
    AutocompleteEntry,
    HelpPopup,
    ZoneListDialog,
    ZoneNumberEntry,
    ask as ask_dialog,
    ask_choice as ask_choice_dialog,
    load_globe,
)

MOD = "Command" if sys.platform == "darwin" else "Control"
ERROR_FG = "#c62828"
SAVE_DELAY_MS = 700  # autosave is batched: typing never waits for the disk


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


def resource_path(rel: str) -> Path:
    """Path to a bundled file, both from source and inside the PyInstaller build."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / rel


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()  # build the window off-screen, show it once it's ready (no flicker on slow PCs)

        self.data_dir = zl.app_data_dir()
        self.settings = zl.load_settings(self.data_dir)
        i18n.set_language(self.settings["language"] or i18n.detect_language())

        defs = zl.load_zone_defs(self.data_dir)
        self.zones: list[str] = [name for name, _ in defs]
        self.outdoor: set[str] = {name.casefold() for name, is_out in defs if is_out}  # never get a floor prefix
        session = zl.load_session(self.data_dir)
        self.entries: list[zl.Entry] = session["entries"]
        self._exported: list[zl.Entry] = []  # rows as of the last Excel export (for the "not exported yet" warning)
        self.last_dir: str = session["last_dir"]
        self.history: list[list[zl.Entry]] = []
        self.edit_index: int | None = None
        self._floor_before_edit: str | None = None  # the sticky floor, parked while a row is being edited

        self.scale = max(1.0, self.winfo_fpixels("1i") / 96.0)
        self._fonts()
        self._window_geometry()
        self._set_icon()

        self.store = tk.StringVar(value=session["store"])
        self.floor = tk.StringVar(value=session["floor"])  # "", "EG" or "OG": sticky until changed
        self.status = tk.StringVar()
        self.summary = tk.StringVar()
        self.hint = tk.StringVar()
        self._status_fn = None
        self._status_error = False
        self._hint_fn = None
        self._texts: list[tuple[tk.Widget, str, object]] = []
        self._save_job: str | None = None
        self._focus_job: str | None = None

        self._build()
        self._bind_keys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.store.trace_add("write", lambda *_: self.schedule_save())
        self.floor.trace_add("write", lambda *_: self.schedule_save())

        self.apply_language()
        self.rebuild_table()
        self.update_suggestion()
        if self.entries:
            self.info("status.restored", n=len(self.entries))
        else:
            self.info("status.ready")
        self.deiconify()
        self._focus_job = self.after(100, self.zone.focus_set)

    # ----------------------------------------------------------- scaling/fonts
    def px(self, n: float) -> int:
        """Scale a pixel size for the Windows display-scaling setting (125 %, 150 % ...)."""
        return int(round(n * self.scale))

    def _fonts(self) -> None:
        base = tkfont.nametofont("TkDefaultFont")
        size = abs(int(base.cget("size")))
        family = base.cget("family")
        self.base = tkfont.Font(family=family, size=size)
        self.big = tkfont.Font(family=family, size=size + 3)
        self.bold = tkfont.Font(family=family, size=size, weight="bold")
        self.bold_big = tkfont.Font(family=family, size=size + 2, weight="bold")
        self.small = tkfont.Font(family=family, size=max(size - 1, 8))

    def _window_geometry(self) -> None:
        """Fit the window to the screen: old ThinkPads are often 1366x768."""
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(self.px(1080), sw - 40), min(self.px(720), sh - 110)
        self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 2 - 20)}")

    def fit_minsize(self) -> None:
        """Smallest window = what the current language's buttons actually need (never clipped).

        German or Romanian labels are longer than English ones, so a fixed minimum would cut
        them off on some language or font. Measured instead, and capped to the screen.
        """
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        need = max(self.px(860), self.winfo_reqwidth())
        min_w, min_h = min(need, sw - 20), min(self.px(560), sh - 90)
        self.minsize(min_w, min_h)
        if self.winfo_viewable() and self.winfo_width() < min_w:
            self.geometry(f"{min_w}x{self.winfo_height()}")

    def _set_icon(self) -> None:
        icon = resource_path("assets/zoneentry.ico")
        if sys.platform == "win32" and icon.exists():
            try:
                self.iconbitmap(default=str(icon))
            except tk.TclError:
                pass

    def ctrl_name(self) -> str:
        return "Cmd" if sys.platform == "darwin" else tr("key.ctrl")

    # ------------------------------------------------------------------ layout
    def _reg(self, widget, fn, option: str = "text"):
        """Register a widget whose text depends on the language / state."""
        self._texts.append((widget, option, fn))
        widget.configure(**{option: fn()})
        return widget

    def _refresh_texts(self) -> None:
        for widget, option, fn in self._texts:
            widget.configure(**{option: fn()})

    def _build(self) -> None:
        px = self.px
        style = ttk.Style(self)
        style.configure("Treeview", rowheight=int(self.big.metrics("linespace") * 1.5), font=self.big)
        style.configure("Treeview.Heading", font=self.bold)
        self._default_fg = style.lookup("TLabel", "foreground") or "black"

        main = ttk.Frame(self, padding=px(12))
        main.pack(fill="both", expand=True)

        # ---- top bar: store name on the left; lists, language and help on the right
        top = ttk.Frame(main)
        top.pack(fill="x")
        self._reg(ttk.Label(top), lambda: tr("store.label")).pack(side="left")
        self.store_entry = ttk.Entry(top, textvariable=self.store, width=24, font=self.big)
        self.store_entry.pack(side="left", padx=px(8))

        self.help_btn = ttk.Button(top, text="?", width=3, command=lambda: self.help.click())
        self.help_btn.pack(side="right")
        self.help = HelpPopup(self, self.help_btn)

        self.globe = load_globe(self, self.scale)  # keep a reference or Tk drops the image
        self.lang_var = tk.StringVar(value=i18n.get_language())
        self.lang_btn = ttk.Menubutton(top, image=self.globe, compound="left", width=10)
        menu = tk.Menu(self.lang_btn, tearoff=False)
        for code, name in LANGUAGES.items():
            menu.add_radiobutton(label=name, variable=self.lang_var, value=code, command=lambda c=code: self.set_language(c))
        self.lang_btn["menu"] = menu
        self.lang_btn.pack(side="right", padx=(px(6), px(6)))

        self._reg(ttk.Button(top, command=self.new_list), lambda: tr("btn.new")).pack(side="right")
        self._reg(ttk.Button(top, command=self.edit_zone_list), lambda: tr("btn.zonelist")).pack(side="right", padx=px(6))
        self._reg(ttk.Button(top, command=self.import_file), lambda: tr("btn.import")).pack(side="right")

        # ---- entry box
        box = ttk.LabelFrame(main, padding=px(10))
        self._reg(box, lambda: tr("box.title"))
        box.pack(fill="x", pady=(px(12), px(6)))
        self._reg(ttk.Label(box, font=self.bold), lambda: tr("lbl.floor")).grid(row=0, column=0, sticky="w")
        self._reg(ttk.Label(box, font=self.bold), lambda: tr("lbl.store_zone")).grid(row=0, column=1, sticky="w", padx=(px(16), 0))
        self._reg(ttk.Label(box, font=self.bold), lambda: tr("lbl.start")).grid(row=0, column=2, sticky="w", padx=(px(16), 0))
        self._reg(ttk.Label(box, font=self.bold), lambda: tr("lbl.end")).grid(row=0, column=3, sticky="w", padx=(px(16), 0))

        # floor selector: "–" (none) / EG / OG. Sticky; skipped by Tab; hotkeys Ctrl+0 / Ctrl+1 / Ctrl+2
        floor_box = tk.Frame(box)
        floor_box.grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.floor_buttons: dict[str, tk.Radiobutton] = {}
        for value, text in (("", "–"), ("EG", "EG"), ("OG", "OG")):
            rb = tk.Radiobutton(
                floor_box, text=text, value=value, variable=self.floor, indicatoron=False, width=4,
                font=self.bold, selectcolor="#9cc5f2", activebackground="#dbe9fa", takefocus=False,
                command=self._floor_clicked, pady=px(2),
            )
            rb.pack(side="left")
            self.floor_buttons[value] = rb

        self.zone = AutocompleteEntry(
            box,
            get_values=lambda: self.zones,
            on_commit=self._zone_committed,
            list_font=self.big,
            width=26,
            font=self.big,
        )
        self.zone.grid(row=1, column=1, sticky="w", padx=(px(16), 0), pady=(2, 0))
        self.start = ZoneNumberEntry(box, font=self.big)
        self.start.grid(row=1, column=2, sticky="w", padx=(px(16), 0), pady=(2, 0))
        self.end = ZoneNumberEntry(box, font=self.big)
        self.end.grid(row=1, column=3, sticky="w", padx=(px(16), 0), pady=(2, 0))
        self.add_btn = ttk.Button(box, command=self.submit, width=14)
        self._reg(self.add_btn, lambda: tr("btn.save" if self.edit_index is not None else "btn.add") + "  ⏎")
        self.add_btn.grid(row=1, column=4, padx=(px(16), 0), pady=(2, 0))
        ttk.Label(box, textvariable=self.hint, font=self.small).grid(
            row=2, column=0, columnspan=5, sticky="w", pady=(px(6), 0)
        )

        self.start.bind("<Return>", self._start_enter)
        self.start.bind("<KP_Enter>", self._start_enter)
        self.end.bind("<Return>", self.submit)
        self.end.bind("<KP_Enter>", self.submit)

        # ---- table
        wrap = ttk.Frame(main)
        wrap.pack(fill="both", expand=True, pady=(px(6), px(6)))
        self.tree = ttk.Treeview(wrap, columns=("n", "from", "to", "zone", "count"), show="headings", selectmode="extended")
        for key, width, anchor in (("n", 50, "center"), ("from", 110, "center"), ("to", 110, "center"), ("zone", 320, "w"), ("count", 80, "center")):
            self.tree.column(key, width=px(width), anchor=anchor, stretch=(key == "zone"))
        self.tree.tag_configure("odd", background="#f3f6fa", foreground="#111111")
        self.tree.tag_configure("even", background="#ffffff", foreground="#111111")
        self.tree.tag_configure("editing", background="#fff3c4", foreground="#111111")
        sb = ttk.Scrollbar(wrap, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        # ---- action bar
        bar = ttk.Frame(main)
        bar.pack(fill="x")
        self._reg(ttk.Button(bar, command=self.edit_selected), lambda: f"{tr('btn.edit')}  (F2)").pack(side="left")
        self._reg(ttk.Button(bar, command=self.delete_selected), lambda: f"{tr('btn.delete')}  ({tr('key.del')})").pack(side="left", padx=px(6))
        self._reg(ttk.Button(bar, command=self.undo), lambda: f"{tr('btn.undo')}  ({self.ctrl_name()}+Z)").pack(side="left")
        self.export_btn = ttk.Button(bar, command=self.export)
        self._reg(self.export_btn, lambda: f"{tr('btn.export')}  ({self.ctrl_name()}+S)")
        self.export_btn.pack(side="right")

        # ---- status bar
        sbar = ttk.Frame(main)
        sbar.pack(fill="x", pady=(px(10), 0))
        self.status_lbl = ttk.Label(sbar, textvariable=self.status)
        self.status_lbl.pack(side="left")
        ttk.Label(sbar, textvariable=self.summary, font=self.small).pack(side="right")

    def _bind_keys(self) -> None:
        self.tree.bind("<Double-1>", self._tree_double_click)
        self.tree.bind("<Return>", lambda _e: self.edit_selected())
        self.tree.bind("<F2>", lambda _e: self.edit_selected())
        self.tree.bind("<Delete>", lambda _e: self.delete_selected())
        self.tree.bind("<BackSpace>", lambda _e: self.delete_selected())
        self.bind("<F2>", lambda _e: self.edit_selected())
        self.bind("<Escape>", self._on_escape)
        self.bind_all("<F1>", lambda _e: (self.help.toggle(), "break")[1])
        for seq, fn in (("z", self.undo), ("s", self.export), ("e", self.export)):
            try:
                self.bind_all(f"<{MOD}-{seq}>", lambda _e, f=fn: (f(), "break")[1])
            except tk.TclError:
                pass
        for digit, value in (("0", ""), ("1", "EG"), ("2", "OG")):  # "Key-" matters: <Control-1> alone means mouse button 1
            try:
                self.bind_all(f"<{MOD}-Key-{digit}>", lambda _e, v=value: (self.set_floor(v), "break")[1])
            except tk.TclError:
                pass

    def _on_escape(self, _e=None) -> None:
        if self.help.visible:
            self.help.hide()
        else:
            self.cancel_edit()

    # ---------------------------------------------------------------- language
    def set_language(self, code: str) -> None:
        code = i18n.set_language(code)
        self.lang_var.set(code)
        self.settings["language"] = code
        try:
            zl.save_settings(self.data_dir, self.settings)
        except OSError:
            pass
        self.apply_language()

    def apply_language(self) -> None:
        """Re-translate everything that is on screen, including the current status line."""
        self.title(tr("app.title", version=__version__))
        for key, name in (("n", "col.n"), ("from", "col.from"), ("to", "col.to"), ("zone", "col.zone"), ("count", "col.count")):
            self.tree.heading(key, text=tr(name))
        self.lang_btn.configure(text=LANGUAGES[i18n.get_language()])
        self._refresh_texts()
        self.help.hide()
        self._render_status()
        self._render_hint()
        self.update_summary()
        self.fit_minsize()

    # ----------------------------------------------------------------- status
    @staticmethod
    def _as_fn(msg, params):
        return msg if callable(msg) else (lambda: tr(msg, **params))

    def _render_status(self) -> None:
        text = self._status_fn() if self._status_fn else ""
        self.status.set(("⚠  " if self._status_error else "") + text)
        self.status_lbl.configure(foreground=ERROR_FG if self._status_error else self._default_fg)

    def info(self, msg, **params) -> None:
        """Show a status message: a translation key (+ values) or a function returning text."""
        self._status_fn, self._status_error = self._as_fn(msg, params), False
        self._render_status()

    def error(self, msg, field: tk.Widget | None = None, **params) -> str:
        self._status_fn, self._status_error = self._as_fn(msg, params), True
        self._render_status()
        self.bell()
        if field is not None:
            field.focus_set()
        return "break"

    def set_hint(self, msg, **params) -> None:
        self._hint_fn = self._as_fn(msg, params)
        self._render_hint()

    def _render_hint(self) -> None:
        self.hint.set(self._hint_fn() if self._hint_fn else "")

    def update_summary(self) -> None:
        n = len(self.entries)
        if not n:
            self.summary.set(tr("summary.none"))
            return
        lo = min(e.first for e in self.entries)
        hi = max(e.last for e in self.entries)
        text = tr("summary.main", rows=n, lo=zl.pad(lo), hi=zl.pad(hi), zones=sum(e.count for e in self.entries))
        gaps = zl.find_gaps(self.entries)
        if gaps:
            shown = ", ".join(zl.fmt_range(a, b) for a, b in gaps[:3])
            if len(gaps) > 3:
                shown += f" +{len(gaps) - 3}"
            text += " · " + tr("summary.gaps", list=shown)
        self.summary.set(text)

    # ------------------------------------------------------------------ table
    # Adding a row only inserts that one row (the old code rebuilt the whole table on every
    # Enter, which gets slow on an old PC with a few hundred rows). A full rebuild happens
    # only for delete / undo / import / new list.
    def _row_tag(self, i: int) -> str:
        return "editing" if i == self.edit_index else ("odd" if i % 2 else "even")

    def _row_values(self, i: int) -> tuple:
        e = self.entries[i]
        return (i + 1, e.start, e.end, e.zone, e.count)

    def rebuild_table(self) -> None:
        tree = self.tree
        tree.delete(*tree.get_children())
        for i in range(len(self.entries)):
            tree.insert("", "end", iid=str(i), values=self._row_values(i), tags=(self._row_tag(i),))
        if self.entries:
            tree.see(str(len(self.entries) - 1))
        self.update_summary()

    def _table_append(self) -> None:
        i = len(self.entries) - 1
        self.tree.insert("", "end", iid=str(i), values=self._row_values(i), tags=(self._row_tag(i),))
        self.tree.see(str(i))
        self.update_summary()

    def _table_update(self, i: int) -> None:
        if 0 <= i < len(self.entries):
            self.tree.item(str(i), values=self._row_values(i), tags=(self._row_tag(i),))
        self.update_summary()

    def update_suggestion(self) -> None:
        """Fill Start with previous End + 1 and clear the End field."""
        if self.edit_index is not None:
            return
        last = self.entries[-1] if self.entries else None
        if last is None:
            self.start.var.set("")
            self.set_hint("hint.first")
        else:
            nxt = zl.next_start(last.end)
            if nxt is None:
                self.start.var.set("")
                self.set_hint("hint.max")
            else:
                self.start.var.set(nxt)
                self.set_hint("hint.suggest", start=nxt, prev=last.end)
        self.end.var.set("")

    def _tree_double_click(self, e) -> None:
        iid = self.tree.identify_row(e.y)
        if iid:
            self.begin_edit(int(iid))

    # ------------------------------------------------------------------ input
    def ask(self, kind: str, title: str, message: str, default_yes: bool = True) -> bool:
        return ask_dialog(self, kind, title, message, default_yes)

    # ------------------------------------------------------------------ floors
    def is_outdoor(self, zone: str) -> bool:
        return zone.casefold() in self.outdoor

    def division(self, zone: str) -> str:
        """What goes into the Division column: 'EG Sanitär', or the bare name for no floor / outdoor zones."""
        return zl.with_floor(self.floor.get(), zone, self.is_outdoor(zone))

    def sticky_floor(self) -> str:
        """The floor new rows get (while a row is being edited the box shows that row's floor instead)."""
        return self._floor_before_edit if self._floor_before_edit is not None else self.floor.get()

    def set_floor(self, value: str) -> None:
        self.floor.set(value if value in zl.FLOORS else "")
        self._announce_floor()
        self.zone.focus_set()

    def _floor_clicked(self) -> None:
        self._announce_floor()
        self.zone.focus_set()

    def _announce_floor(self) -> None:
        floor = self.floor.get()
        self.info("status.floor", floor=floor) if floor else self.info("status.floor_none")

    def _restore_floor(self) -> None:
        if self._floor_before_edit is not None:
            self.floor.set(self._floor_before_edit)
            self._floor_before_edit = None

    # ------------------------------------------------------------- zone list
    def ask_choice(self, title: str, message: str, buttons, default: int = 0, cancel=None):
        return ask_choice_dialog(self, title, message, buttons, default, cancel)

    def _zone_defs(self) -> list[zl.ZoneDef]:
        return [(z, self.is_outdoor(z)) for z in self.zones]

    def _save_zone_defs(self) -> bool:
        try:
            zl.save_zone_defs(self.data_dir, self._zone_defs())
            return True
        except OSError as exc:
            self.error("status.zones_save_failed", err=str(exc))
            return False

    def _resolve_or_add(self, text: str) -> str | None:
        """The canonical zone name for what was typed. An unknown name is offered for adding to the list."""
        t = text.strip()
        if not t:
            return None
        zone = zl.resolve_zone(t, self.zones)
        if zone is not None:
            return zone
        name = zl.tidy_new_zone_name(t)
        zone = zl.resolve_zone(name, self.zones)
        if zone is not None:
            return zone
        choice = self.ask_choice(
            tr("dlg.addzone.title"),
            tr("dlg.addzone.msg", name=name),
            [(tr("btn.add"), "add"), (tr("dlg.addzone.outdoor"), "outdoor"), (tr("dlg.cancel"), None)],
            default=0,
            cancel=None,
        )
        if choice is None:
            self.zone.focus_set()
            return None
        self.zones.append(name)
        if choice == "outdoor":
            self.outdoor.add(name.casefold())
        if self._save_zone_defs():
            self.info("status.zone_added", name=name)
        return name

    def _zone_committed(self, text: str) -> None:
        if not text.strip():
            self.error("err.zone_type", self.zone)
            return
        zone = self._resolve_or_add(text)
        if zone is None:
            return
        self.zone.set(zone)
        self.info("status.zone_selected", zone=self.division(zone))
        (self.end if self.start.var.get().strip() else self.start).focus_set()

    def _start_enter(self, _e=None):
        self.start.pad_now()
        self.end.focus_set()
        return "break"

    def submit(self, _e=None):
        zone_text = self.zone.var.get().strip()
        if not zone_text:
            return self.error("err.zone_pick", self.zone)
        zone = self._resolve_or_add(zone_text)
        if zone is None:
            return "break"
        try:
            start = zl.normalize_zone(self.start.var.get(), "lbl.start")
        except zl.ZoneError as exc:
            return self.error(lambda exc=exc: str(exc), self.start)
        try:
            end = zl.normalize_zone(self.end.var.get(), "lbl.end")
        except zl.ZoneError as exc:
            return self.error(lambda exc=exc: str(exc), self.end)
        if int(end) < int(start):
            return self.error("err.end_lt_start", self.end, end=end, start=start)

        hit = zl.find_overlap(self.entries, start, end, skip_index=self.edit_index)
        if hit is not None:
            o = self.entries[hit]
            if not self.ask(
                "yesno",
                tr("dlg.overlap.title"),
                tr("dlg.overlap.msg", start=start, end=end, n=hit + 1, label=o.label()),
                default_yes=False,
            ):
                self.start.focus_set()
                return "break"

        entry = zl.Entry(start, end, self.division(zone))
        self._push_history()
        if self.edit_index is None:
            prev = self.entries[-1] if self.entries else None
            self.entries.append(entry)
            skipped = zl.skipped_between(int(prev.end), int(start)) if prev is not None else None
            backwards = prev is not None and not skipped and int(start) <= int(prev.end)

            def added(label=entry.label(), skipped=skipped, backwards=backwards) -> str:
                msg = tr("status.added", label=label)
                if skipped:
                    msg += "   " + tr("status.skips", range=zl.fmt_range(*skipped))
                elif backwards:
                    msg += "   " + tr("status.not_after")
                return msg

            self._table_append()
            self.info(added)
        else:
            i = self.edit_index
            self.entries[i] = entry
            self.edit_index = None
            self._restore_floor()
            self._refresh_texts()
            self._table_update(i)
            self.info("status.updated", n=i + 1, label=entry.label())

        self.zone.clear()
        self.update_suggestion()
        self.schedule_save()
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
        previous = self.edit_index
        e = self.entries[index]
        self.edit_index = index
        if self._floor_before_edit is None:
            self._floor_before_edit = self.floor.get()
        if zl.resolve_zone(e.zone, self.zones) is not None:  # a zone that really is called "EG Lager"
            floor, base = "", e.zone
        else:
            floor, base = zl.split_floor(e.zone)
        self.floor.set(floor)
        self.zone.set(base)
        self.start.var.set(e.start)
        self.end.var.set(e.end)
        self._refresh_texts()
        self.set_hint("hint.editing", n=index + 1)
        if previous is not None and previous != index:
            self._table_update(previous)
        self._table_update(index)
        self.end.focus_set()

    def cancel_edit(self) -> None:
        if self.edit_index is None:
            return
        i, self.edit_index = self.edit_index, None
        self._restore_floor()
        self._refresh_texts()
        self.zone.clear()
        self._table_update(i)
        self.update_suggestion()
        self.info("status.edit_cancelled")
        self.zone.focus_set()

    def delete_selected(self) -> None:
        sel = sorted((int(i) for i in self.tree.selection()), reverse=True)
        if not sel:
            return
        self.cancel_edit()
        self._push_history()
        for i in sel:
            del self.entries[i]
        self.rebuild_table()
        self.update_suggestion()
        self.info(lambda n=len(sel): tr("status.deleted", n=n, key=f"{self.ctrl_name()}+Z"))
        self.schedule_save()

    def undo(self) -> None:
        if not self.history:
            self.info("status.nothing_undo")
            return
        self.entries = self.history.pop()
        self.edit_index = None
        self._restore_floor()
        self._refresh_texts()
        self.zone.clear()
        self.rebuild_table()
        self.update_suggestion()
        self.info("status.undone")
        self.schedule_save()

    def new_list(self) -> None:
        if self.entries:
            msg = tr("dlg.new.msg", n=len(self.entries), key=f"{self.ctrl_name()}+Z")
            if self.entries != self._exported:
                msg += tr("dlg.new.unexported")
            if not self.ask("yesno", tr("dlg.new.title"), msg, default_yes=False):
                return
        if self.entries:
            self._push_history()
        self.entries = []
        self.edit_index = None
        self._floor_before_edit = None
        self.floor.set("")
        self._refresh_texts()
        self.zone.clear()
        self.store.set("")
        self.rebuild_table()
        self.update_suggestion()
        self.info("status.newlist")
        self.schedule_save()
        self.store_entry.focus_set()

    # ------------------------------------------------------------ zone list
    def edit_zone_list(self) -> None:
        def save(defs: list[zl.ZoneDef]) -> None:
            self.zones = [name for name, _ in defs]
            self.outdoor = {name.casefold() for name, is_out in defs if is_out}
            if self._save_zone_defs():
                self.info("status.zones_saved", n=len(self.zones))

        ZoneListDialog(self, self._zone_defs(), zl.default_zone_defs(), save)

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
            self.ask("info", tr("dlg.export.title"), tr("dlg.export.empty"))
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title=tr("dlg.export.save_title"),
            defaultextension=".xlsx",
            filetypes=[(tr("dlg.filetype.xlsx"), "*.xlsx")],
            initialdir=self._initial_dir(),
            initialfile=zl.default_export_name(self.store.get()),
        )
        if not path:
            return
        try:
            zl.export_xlsx(path, self.entries)
        except PermissionError:
            self.ask("error", tr("dlg.cantsave.title"), tr("dlg.cantsave.msg", file=os.path.basename(path)))
            return
        except OSError as exc:
            self.ask("error", tr("dlg.cantsave.title"), str(exc))
            return
        self.last_dir = os.path.dirname(path)
        self._exported = list(self.entries)
        self.flush_session()
        self.info("status.exported", n=len(self.entries), path=path)

    def import_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title=tr("dlg.import.open_title"),
            filetypes=[(tr("dlg.filetype.xlsx"), "*.xlsx")],
            initialdir=self._initial_dir(),
        )
        if not path:
            return
        try:
            entries, problems = zl.import_xlsx(path)
        except zl.ZoneError as exc:
            self.ask("error", tr("dlg.import.title"), str(exc))
            return
        except Exception as exc:  # corrupt / locked file
            self.ask("error", tr("dlg.import.title"), tr("dlg.import.read_err", err=str(exc)))
            return
        if not entries:
            self.ask("info", tr("dlg.import.title"), tr("dlg.import.none"))
            return
        if self.entries and not self.ask(
            "okcancel", tr("dlg.import.title"), tr("dlg.import.replace", old=len(self.entries), new=len(entries))
        ):
            return
        known = {z.casefold() for z in self.zones}
        new_zones = []
        for e in entries:
            # "EG Sanitär" in a file means zone "Sanitär" on floor EG; the list holds the bare names
            name = e.zone if e.zone.casefold() in known else zl.split_floor(e.zone)[1]
            if name and name.casefold() not in known:
                known.add(name.casefold())
                new_zones.append(name)
                if zl.looks_outdoor(name):
                    self.outdoor.add(name.casefold())
        if new_zones:
            self.zones.extend(new_zones)
            self._save_zone_defs()
        self._push_history()
        self.cancel_edit()
        self.entries = entries
        self.rebuild_table()
        self.update_suggestion()

        n_new, n_bad, n_rows = len(new_zones), len(problems), len(entries)

        def imported() -> str:
            parts = [tr("status.imported", n=n_rows)]
            if n_new:
                parts.append(tr("status.imported_new", n=n_new))
            if n_bad:
                parts.append(tr("status.imported_skipped", n=n_bad))
            return " ".join(parts)

        if problems:
            self.ask("warning", tr("dlg.import.title"), tr("dlg.import.skipped", rows="\n".join(problems[:15])))
        self.info(imported)
        self.schedule_save()
        self.zone.focus_set()

    # ------------------------------------------------------------ persistence
    def schedule_save(self) -> None:
        """Save soon, but not on every keystroke: disk writes are slow on old laptops."""
        if self._save_job is None:
            self._save_job = self.after(SAVE_DELAY_MS, self.flush_session)

    def flush_session(self) -> None:
        if self._save_job is not None:
            try:
                self.after_cancel(self._save_job)
            except tk.TclError:
                pass
            self._save_job = None
        try:
            zl.save_session(self.data_dir, self.store.get(), self.entries, self.last_dir, self.sticky_floor())
        except OSError:
            pass  # never interrupt data entry because autosave failed

    def _on_close(self) -> None:
        self.flush_session()
        self.destroy()

    def destroy(self) -> None:
        for job in (self._save_job, self._focus_job):
            if job:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
        super().destroy()


# =============================================================================
def selftest() -> int:
    """`ZoneEntry.exe --selftest`: open the window, switch through all languages, write and
    re-read an Excel file, close. Used by the build pipeline to prove the packaged exe works."""
    import tempfile
    import traceback

    log = Path(tempfile.gettempdir()) / "zoneentry-selftest.log"
    home = Path(tempfile.mkdtemp(prefix="zoneentry-selftest-"))
    os.environ["ZONEENTRY_HOME"] = str(home)
    try:
        app = App()
        app.update()
        app.entries.append(zl.Entry("0001", "0010", "Kassen"))
        xlsx = home / "selftest.xlsx"
        zl.export_xlsx(xlsx, app.entries)  # proves openpyxl made it into the build
        back, problems = zl.import_xlsx(xlsx)
        assert back == app.entries and not problems, "Excel round trip failed"
        for code in LANGUAGES:
            app.set_language(code)
            app.update()
        app.help.show()
        app.update()
        app.help.hide()
        app.destroy()
        log.write_text("OK\n", encoding="utf-8")
        return 0
    except Exception:
        log.write_text(traceback.format_exc(), encoding="utf-8")
        return 1


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    enable_hidpi()
    if "--selftest" in argv:
        return selftest()
    App().mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
