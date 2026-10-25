"""Reusable Tk widgets for ZoneEntry: autocomplete entry, number entry, hover help,
translated modal dialogs and the zone-list editor."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

import zonelogic as zl
from i18n import tr


# =============================================================================
# Entry widgets
# =============================================================================
class AutocompleteEntry(ttk.Entry):
    """Entry with a filter-as-you-type suggestion list.

    * typing filters the list (exact match first, then prefix, word start, contains)
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


# =============================================================================
# Icons
# =============================================================================
def load_globe(root: tk.Misc, scale: float) -> tk.PhotoImage:
    """The wire-globe icon, in the embedded size closest to 18 logical pixels."""
    from icons import GLOBE_PNG

    wanted = round(18 * scale)
    size = min(GLOBE_PNG, key=lambda s: abs(s - wanted))
    return tk.PhotoImage(master=root, data=GLOBE_PNG[size])


# =============================================================================
# Dialogs (own implementation so the buttons follow the app language, not Windows')
# =============================================================================
class ModalDialog(tk.Toplevel):
    GLYPHS = {"info": "ⓘ", "warning": "⚠", "error": "✖", "question": "?"}

    def __init__(self, parent, title, message, buttons, default=0, cancel=None, kind="info"):
        super().__init__(parent)
        self.withdraw()
        self.title(title)
        self.transient(parent)
        self.resizable(False, False)
        self.result = cancel
        self._buttons: list[ttk.Button] = []
        self._values = [v for _, v in buttons]
        self._default = default
        self._cancel = cancel
        px = getattr(parent, "px", lambda n: n)

        body = ttk.Frame(self, padding=(px(20), px(18), px(20), px(8)))
        body.pack(fill="both", expand=True)
        glyph_font = tkfont.Font(font=getattr(parent, "big", "TkDefaultFont"))
        glyph_font.configure(size=abs(int(glyph_font.cget("size"))) * 2)
        ttk.Label(body, text=self.GLYPHS.get(kind, ""), font=glyph_font).grid(row=0, column=0, sticky="n", padx=(0, px(14)))
        ttk.Label(body, text=message, wraplength=px(420), justify="left").grid(row=0, column=1, sticky="w")

        bar = ttk.Frame(self, padding=(px(20), px(6), px(20), px(16)))
        bar.pack(fill="x")
        for i, (text, value) in enumerate(reversed(buttons)):
            b = ttk.Button(bar, text=text, command=lambda v=value: self._finish(v), width=max(8, len(text) + 2))
            b.pack(side="right", padx=(px(8), 0))
            self._buttons.append(b)
        self._buttons.reverse()  # now in the same order as `buttons`

        self.bind("<Return>", self._on_return)
        self.bind("<KP_Enter>", self._on_return)
        self.bind("<Escape>", lambda _e: self._finish(self._cancel))
        self.protocol("WM_DELETE_WINDOW", lambda: self._finish(self._cancel))

        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        try:
            x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
            y = parent.winfo_rooty() + (parent.winfo_height() - h) // 3
        except tk.TclError:
            x = y = 100
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.deiconify()
        self.wait_visibility()
        self.grab_set()
        self._buttons[default].focus_set()
        self.wait_window()

    def _on_return(self, _e):
        focused = self.focus_get()
        for b, v in zip(self._buttons, self._values):
            if focused is b:
                return self._finish(v)
        return self._finish(self._values[self._default])

    def _finish(self, value):
        self.result = value
        self.destroy()
        return "break"


def ask(parent, kind: str, title: str, message: str, default_yes: bool = True) -> bool:
    """kind: yesno | okcancel | info | warning | error  ->  True for Yes/OK, False otherwise."""
    if kind == "yesno":
        buttons, glyph = [(tr("dlg.yes"), True), (tr("dlg.no"), False)], "question"
        default = 0 if default_yes else 1
    elif kind == "okcancel":
        buttons, glyph, default = [(tr("dlg.ok"), True), (tr("dlg.cancel"), False)], "question", 0
    else:
        buttons, glyph, default = [(tr("dlg.ok"), True)], kind, 0
    cancel = False if len(buttons) == 2 else True
    return bool(ModalDialog(parent, title, message, buttons, default, cancel, glyph).result)


class ZoneListDialog(tk.Toplevel):
    """Edit the predefined Store Zone list (one name per line)."""

    def __init__(self, master, zones, defaults, on_save):
        super().__init__(master)
        self.withdraw()
        self.title(tr("zl.title"))
        self.transient(master)
        px = master.px
        self._on_save = on_save
        self._defaults = defaults
        self._master = master

        ttk.Label(self, text=tr("zl.help"), padding=(px(12), px(10), px(12), px(4)), wraplength=px(380)).pack(anchor="w")
        frame = ttk.Frame(self, padding=(px(12), 0))
        frame.pack(fill="both", expand=True)
        self.text = tk.Text(frame, wrap="none", undo=True, font=master.big, width=28, height=16)
        sb = ttk.Scrollbar(frame, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)
        self.text.insert("1.0", "\n".join(zones))

        bar = ttk.Frame(self, padding=px(12))
        bar.pack(fill="x")
        ttk.Button(bar, text=tr("zl.reset"), command=self._reset).pack(side="left")
        ttk.Button(bar, text=tr("btn.save"), command=self._save).pack(side="right")
        ttk.Button(bar, text=tr("dlg.cancel"), command=self.destroy).pack(side="right", padx=px(6))
        self.bind("<Escape>", lambda _e: self.destroy())

        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = master.winfo_rootx() + (master.winfo_width() - w) // 2
        y = master.winfo_rooty() + max(0, (master.winfo_height() - h) // 3)
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.deiconify()
        self.wait_visibility()
        self.text.focus_set()
        self.grab_set()

    def _reset(self):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", "\n".join(self._defaults))

    def _save(self):
        zones = zl.parse_zone_lines(self.text.get("1.0", "end"))
        if not zones:
            ask(self, "warning", tr("zl.title"), tr("zl.empty"))
            return
        self._on_save(zones)
        self.destroy()


# =============================================================================
# Hover help
# =============================================================================
class HelpPopup:
    """Small borderless guide next to the "?" button.

    Hover the button to peek; click it (or press F1) to keep the guide open, then click
    anywhere / press Esc / F1 to close it.
    """

    BG, FG, BORDER, CAP = "#ffffff", "#1a1a1a", "#7a7a7a", "#f0f0f0"

    def __init__(self, app, button):
        self.app = app
        self.button = button
        self.win: tk.Toplevel | None = None
        self.pinned = False
        self._jobs: list[str] = []
        button.bind("<Enter>", self._on_enter, add="+")
        button.bind("<Leave>", self._on_leave, add="+")
        app.bind_all("<Button-1>", self._global_click, add="+")

    # -- state ------------------------------------------------------------------
    @property
    def visible(self) -> bool:
        return self.win is not None

    def show(self, pin: bool = False) -> None:
        self._cancel_jobs()
        if self.win is None:
            self.win = self._build()
        if pin:
            self.pinned = True

    def hide(self) -> None:
        self._cancel_jobs()
        self.pinned = False
        if self.win is not None:
            self.win.destroy()
            self.win = None

    def click(self) -> None:
        """Button click: pin the guide open, or close it if it is already pinned."""
        if self.visible and self.pinned:
            self.hide()
        else:
            self.show(pin=True)

    def toggle(self) -> None:  # F1
        if self.visible:
            self.hide()
        else:
            self.show(pin=True)

    # -- events -----------------------------------------------------------------
    def _cancel_jobs(self) -> None:
        for job in self._jobs:
            try:
                self.app.after_cancel(job)
            except tk.TclError:
                pass
        self._jobs.clear()

    def _on_enter(self, _e) -> None:
        self._cancel_jobs()
        if self.win is None:
            self._jobs.append(self.app.after(180, self.show))  # small delay: no flicker on fly-bys

    def _on_leave(self, _e) -> None:
        self._cancel_jobs()
        if not self.pinned:
            self._jobs.append(self.app.after(80, self.hide))

    def _global_click(self, e) -> None:
        if self.win is None or not self.pinned:
            return
        w = str(e.widget)
        if e.widget is self.button or w.startswith(str(self.win)):
            return
        self.hide()

    # -- content ------------------------------------------------------------------
    def _build(self) -> tk.Toplevel:
        app = self.app
        px = app.px
        bg, fg = self.BG, self.FG
        win = tk.Toplevel(app)
        win.withdraw()
        win.overrideredirect(True)
        try:
            win.attributes("-topmost", True)
        except tk.TclError:
            pass
        outer = tk.Frame(win, bg=self.BORDER, padx=1, pady=1)
        outer.pack()
        box = tk.Frame(outer, bg=bg, padx=px(16), pady=px(12))
        box.pack()
        wrap = px(460)

        tk.Label(box, text=tr("help.title"), font=app.bold_big, bg=bg, fg=fg, anchor="w").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, px(6))
        )
        row = 1
        for n, key in enumerate(("help.step1", "help.step2", "help.step3"), start=1):
            tk.Label(box, text=f"{n}.", font=app.bold, bg=bg, fg=fg).grid(row=row, column=0, sticky="ne", padx=(0, px(8)))
            tk.Label(box, text=tr(key), font=app.base, bg=bg, fg=fg, justify="left", anchor="w", wraplength=wrap).grid(
                row=row, column=1, sticky="w", pady=px(2)
            )
            row += 1

        tk.Frame(box, bg="#dddddd", height=1).grid(row=row, column=0, columnspan=2, sticky="ew", pady=px(9))
        row += 1
        tk.Label(box, text=tr("help.hotkeys"), font=app.bold, bg=bg, fg=fg, anchor="w").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, px(4))
        )
        row += 1

        ctrl = app.ctrl_name()
        hot = tk.Frame(box, bg=bg)
        hot.grid(row=row, column=0, columnspan=2, sticky="w")
        keys = [
            ("Enter", "hk.enter"),
            ("↑  ↓", "hk.updown"),
            ("Tab  /  Shift+Tab", "hk.tab"),
            ("Esc", "hk.esc"),
            ("F2", "hk.f2"),
            (tr("key.del"), "hk.del"),
            (f"{ctrl}+Z", "hk.undo"),
            (f"{ctrl}+S", "hk.export"),
            ("F1", "hk.f1"),
        ]
        for r, (cap, key) in enumerate(keys):
            tk.Label(hot, text=cap, font=app.bold, bg=self.CAP, fg=fg, relief="solid", bd=1, padx=px(6)).grid(
                row=r, column=0, sticky="ew", pady=px(2), padx=(0, px(10))
            )
            tk.Label(hot, text=tr(key), font=app.base, bg=bg, fg=fg, anchor="w", justify="left", wraplength=wrap - px(130)).grid(
                row=r, column=1, sticky="w"
            )
        row += 1
        tk.Label(box, text=tr("help.note"), font=app.small, bg=bg, fg="#555555", anchor="w", justify="left", wraplength=wrap + px(30)).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(px(10), 0)
        )

        win.update_idletasks()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        bx, by = self.button.winfo_rootx(), self.button.winfo_rooty()
        sw, sh = app.winfo_screenwidth(), app.winfo_screenheight()
        x = max(0, min(bx + self.button.winfo_width() - w, sw - w))
        y = by + self.button.winfo_height() + px(6)
        if y + h > sh:
            y = max(0, by - h - px(6))
        win.geometry(f"+{x}+{y}")
        win.deiconify()
        return win
