"""End-to-end GUI tests: types the sample sheet through the real widgets.

Needs a display, so it only runs when ZONEENTRY_GUI_TESTS=1
(on Linux:  xvfb-run -a env ZONEENTRY_GUI_TESTS=1 python -m pytest tests/test_gui_smoke.py).
"""
import os
import time
import tkinter as tk
from pathlib import Path

import pytest

if os.environ.get("ZONEENTRY_GUI_TESTS") != "1":
    pytest.skip("set ZONEENTRY_GUI_TESTS=1 to run GUI tests", allow_module_level=True)

import app as appmod
import i18n
import widgets
import zonelogic as zl
from i18n import LANGUAGES, tr
from version import __version__

SAMPLE = Path(__file__).parent / "data" / "ZoneUpdate_sample.xlsx"


def no_dialog(*a, **k):  # a modal dialog would block a headless run forever
    raise AssertionError(f"unexpected dialog: {a[:3]}")


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("ZONEENTRY_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("LANG", "en_US.UTF-8")  # first-start language is detected from this
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    a = appmod.App()
    a.ask = no_dialog
    a.ask_choice = no_dialog
    a.update()
    yield a
    a.destroy()
    i18n.set_language("en")


def press(widget, key):
    widget.focus_force()
    widget.update()
    widget.event_generate(f"<{key}>")
    widget.update()


def add_row(app, zone_text, end, start=None):
    """Exactly what a person does: type zone, Enter, (start), end, Enter."""
    app.zone.focus_force()
    app.update()
    app.zone.var.set(zone_text)  # fires the suggestion popup like typing would
    app.update()
    press(app.zone, "Return")
    if start is not None:
        app.start.var.set(start)
    app.end.focus_force()
    app.end.var.set(end)
    press(app.end, "Return")


def table_matches_entries(app) -> bool:
    """The Treeview shows exactly the entries, with the right striping."""
    ids = list(app.tree.get_children())
    if len(ids) != len(app.entries):
        return False
    for i, (iid, e) in enumerate(zip(ids, app.entries)):
        row = [app.tree.set(iid, c) for c in ("n", "from", "to", "zone", "count")]
        if row != [str(i + 1), e.start, e.end, e.zone, str(e.count)]:
            return False
        want = "editing" if i == app.edit_index else ("odd" if i % 2 else "even")
        if tuple(app.tree.item(iid, "tags")) != (want,):
            return False
    return True


def wait(app, seconds=0.5):
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.01)


# ============================================================ original behaviour
def test_whole_sample_typed_through_the_gui(app):
    rows, _ = zl.import_xlsx(SAMPLE)
    for i, row in enumerate(rows):
        suggested = app.start.var.get()
        needs_start = suggested != row.start  # first row, or numbering skips (7747 -> 7750)
        add_row(app, row.zone, row.end, start=row.start if needs_start else None)
        assert len(app.entries) == i + 1, f"row {i + 1} ({row}) was not added: {app.status.get()}"
    assert app.entries == rows
    assert app.start.var.get() == "7765"  # last End 7764 + 1
    assert table_matches_entries(app)


def test_auto_start_and_short_end_padding(app):
    add_row(app, "kas", "42", start="1")
    assert app.entries[0] == zl.Entry("0001", "0042", "Kassen")
    assert app.start.var.get() == "0043"  # +1 with leading zeros
    assert app.zone.var.get() == "" and app.end.var.get() == ""


def test_short_prefix_picks_top_suggestion(app):
    add_row(app, "san", "10", start="1")
    add_row(app, "ELEK", "20")
    add_row(app, "garten", "30")  # exact match must beat "Garten Grill"
    assert [e.zone for e in app.entries] == ["Sanitär", "Elektro", "Garten"]


def test_popup_visible_while_typing_and_hidden_after_accept(app):
    app.zone.focus_force()
    app.update()
    app.zone.var.set("ka")
    app.update()
    assert app.zone._visible and app.zone._lb.winfo_ismapped()
    assert app.zone._lb.size() == 3
    press(app.zone, "Down")
    assert app.zone._index() == 1
    press(app.zone, "Return")
    assert app.zone.var.get() == "Kalthalle Wand"
    assert not app.zone._visible


def test_unknown_zone_cancelled_adds_nothing(app):
    asked = []
    app.ask_choice = lambda title, msg, buttons, default=0, cancel=None: asked.append((msg, [v for _, v in buttons])) or None
    add_row(app, "zzz", "10", start="1")
    assert app.entries == [] and "Zzz" not in app.zones
    assert asked and "“Zzz” is not in the Store Zone list" in asked[0][0]
    assert asked[0][1] == ["add", "outdoor", None]  # Enter on the first button = plain add


def test_end_before_start_is_rejected(app):
    add_row(app, "holz", "5", start="10")
    assert app.entries == []
    assert "smaller" in app.status.get()


def test_overlap_asks_and_respects_no(app):
    add_row(app, "kassen", "10", start="1")
    asked = []
    app.ask = lambda *a, **k: asked.append(a) or False
    add_row(app, "holz", "20", start="5")
    assert asked and len(app.entries) == 1
    assert asked[0][0] == "yesno" and k_default_is_no(asked[0])
    app.ask = lambda *a, **k: True
    press(app.end, "Return")
    assert len(app.entries) == 2


def k_default_is_no(call_args) -> bool:  # the overlap question must default to "No"
    return True  # default_yes is passed as keyword; checked separately below


def test_overlap_question_defaults_to_no(app):
    add_row(app, "kassen", "10", start="1")
    seen = {}
    app.ask = lambda kind, title, msg, default_yes=True: seen.update(kind=kind, default_yes=default_yes, title=title) or False
    add_row(app, "holz", "20", start="5")
    assert seen == {"kind": "yesno", "default_yes": False, "title": tr("dlg.overlap.title")}


def test_edit_delete_undo(app):
    add_row(app, "kassen", "10", start="1")
    add_row(app, "holz", "20")
    add_row(app, "deko", "30")

    app.begin_edit(1)
    assert app.edit_index == 1 and app.end.var.get() == "0020"
    assert app.add_btn.cget("text").startswith(tr("btn.save"))
    assert table_matches_entries(app)  # row 2 is highlighted as "editing"
    app.end.var.set("0018")
    press(app.end, "Return")
    assert app.entries[1].end == "0018" and app.edit_index is None
    assert app.add_btn.cget("text").startswith(tr("btn.add"))
    assert app.start.var.get() == "0031"  # suggestion still follows the last row
    assert table_matches_entries(app)

    app.tree.selection_set("2")
    app.delete_selected()
    assert len(app.entries) == 2 and app.start.var.get() == "0019"  # 0018 + 1
    app.undo()
    assert len(app.entries) == 3 and app.entries[2].zone == "Deko"
    app.undo()  # undoes the edit
    assert app.entries[1].end == "0020"
    assert table_matches_entries(app)


def test_cancel_edit_with_escape(app):
    add_row(app, "kassen", "10", start="1")
    add_row(app, "holz", "20")
    app.begin_edit(0)
    press(app.end, "Escape")
    assert app.edit_index is None and table_matches_entries(app)
    assert app.start.var.get() == "0021"


def test_edit_that_overlaps_asks_first(app):
    add_row(app, "kassen", "10", start="1")
    add_row(app, "holz", "20")
    asked = []
    app.ask = lambda *a, **k: asked.append(a) or False
    app.begin_edit(0)
    app.end.var.set("0015")  # would run into row 2
    press(app.end, "Return")
    assert asked and app.entries[0].end == "0010"


def test_autosave_is_batched_and_restored(app):
    add_row(app, "kassen", "10", start="1")
    assert app._save_job is not None  # scheduled, not written yet
    assert not (app.data_dir / "session.json").exists()
    app.store.set("Markt Test")
    app.flush_session()
    assert app._save_job is None and (app.data_dir / "session.json").exists()
    second = appmod.App()
    try:
        assert second.entries == app.entries and second.store.get() == "Markt Test"
        assert second.start.var.get() == "0011"
        assert table_matches_entries(second)
    finally:
        second.destroy()


def test_many_edits_cause_a_single_disk_write(app, monkeypatch):
    writes = []
    real = zl.save_session
    monkeypatch.setattr(zl, "save_session", lambda *a, **k: writes.append(1) or real(*a, **k))
    for i in range(10):
        app.store.set(f"Markt {i}")  # like typing 10 letters
    add_row(app, "kassen", "10", start="1")
    assert writes == []
    wait(app, appmod.SAVE_DELAY_MS / 1000 + 0.4)
    assert len(writes) == 1


def test_table_stays_consistent_through_many_operations(app):
    rows, _ = zl.import_xlsx(SAMPLE)
    for i, row in enumerate(rows[:14]):
        add_row(app, row.zone, row.end, start=row.start if app.start.var.get() != row.start else None)
        assert table_matches_entries(app), f"after add {i}"
    app.tree.selection_set("3", "4", "9")
    app.delete_selected()
    assert table_matches_entries(app)
    app.begin_edit(2)
    assert table_matches_entries(app)
    app.begin_edit(5)  # switch the edit to another row
    assert table_matches_entries(app)
    app.cancel_edit()
    assert table_matches_entries(app)
    app.undo()
    app.undo() if app.history else None
    assert table_matches_entries(app)


# ================================================================= languages
def test_language_switch_retranslates_everything_but_keeps_data(app):
    add_row(app, "kassen", "10", start="1")
    for code, name in LANGUAGES.items():
        app.set_language(code)
        app.update()
        assert i18n.get_language() == code
        assert app.lang_btn.cget("text") == name  # the chosen language, next to the globe
        assert app.title() == tr("app.title", version=__version__)
        assert app.add_btn.cget("text") == tr("btn.add") + "  ⏎"
        assert app.export_btn.cget("text").startswith(tr("btn.export"))
        for col, key in (("from", "col.from"), ("to", "col.to"), ("zone", "col.zone"), ("count", "col.count")):
            assert app.tree.heading(col, "text") == tr(key)
        assert app.hint.get() == tr("hint.suggest", start="0011", prev="0010")
        assert app.summary.get() == tr("summary.main", rows=1, lo="0001", hi="0010", zones=10)
    # zone names and rows are data: untouched by translation
    assert app.zones == list(zl.DEFAULT_STORE_ZONES)
    assert app.entries == [zl.Entry("0001", "0010", "Kassen")]
    assert app.tree.set("0", "zone") == "Kassen"


def test_globe_button_has_icon_and_language_name(app):
    assert str(app.lang_btn.cget("image")[0]) == str(app.globe)  # ttk reports the image as a tuple
    assert str(app.lang_btn.cget("compound")) == "left"
    assert app.lang_btn.cget("text") == "English"
    menu = app.nametowidget(app.lang_btn.cget("menu"))
    assert [menu.entrycget(i, "label") for i in range(menu.index("end") + 1)] == list(LANGUAGES.values())
    menu.invoke(menu.index("end"))  # click the last entry: Deutsch
    assert i18n.get_language() == "de" and app.lang_btn.cget("text") == "Deutsch"


def test_visible_status_message_is_retranslated(app):
    add_row(app, "", "10", start="1")  # no zone typed
    assert app.status.get() == "⚠  " + tr("err.zone_pick")
    app.set_language("hu")
    assert app.status.get() == "⚠  " + tr("err.zone_pick")
    assert app.status.get() != "⚠  " + i18n.STRINGS["err.zone_pick"]["en"]
    add_row(app, "holz", "x", start="1")  # a ZoneError message
    assert "számjegy" in app.status.get()
    app.set_language("de")
    assert "Ziffern" in app.status.get()


def test_language_choice_is_remembered(app):
    app.set_language("pl")
    second = appmod.App()
    try:
        assert i18n.get_language() == "pl"
        assert second.lang_btn.cget("text") == "Polski"
        assert second.title() == tr("app.title", version=__version__)
    finally:
        second.destroy()
        i18n.set_language("en")


def test_first_start_uses_the_system_language(tmp_path, monkeypatch):
    monkeypatch.setenv("ZONEENTRY_HOME", str(tmp_path / "fresh"))
    monkeypatch.setenv("LANG", "ro_RO.UTF-8")
    a = appmod.App()
    try:
        assert a.lang_btn.cget("text") == "Română"
        assert a.add_btn.cget("text").startswith("Adaugă")
    finally:
        a.destroy()
        i18n.set_language("en")


@pytest.mark.parametrize("code", list(LANGUAGES))
def test_every_language_fits_a_small_screen_and_is_never_clipped(app, code):
    app.set_language(code)
    add_row(app, "kassen", "10", start="1")
    app.update_idletasks()
    need = app.winfo_reqwidth()
    assert need <= 1280 - 40, f"{code}: needs {need}px, would not fit a 1366px-wide laptop"
    assert app.minsize()[0] >= need, f"{code}: window could be shrunk below the {need}px its content needs"
    assert app.winfo_width() >= need


def test_window_grows_if_the_new_language_needs_more_room(app):
    app.geometry("900x700")
    app.update()
    app.set_language("ro")  # the widest language
    app.update()
    assert app.winfo_width() >= app.winfo_reqwidth()


# ================================================================ help popup
def descendants(w):
    for c in w.winfo_children():
        yield c
        yield from descendants(c)


def popup_text(app) -> str:
    return "\n".join(str(w.cget("text")) for w in descendants(app.help.win) if isinstance(w, tk.Label))


def test_help_popup_show_pin_and_hide(app):
    assert not app.help.visible
    app.help.show()
    app.update()
    assert app.help.visible and app.help.win.winfo_ismapped()
    text = popup_text(app)
    for needle in ("Quick guide", "Hotkeys", "F2", "Ctrl+Z", "Ctrl+S", "F1", "Esc", "Del", "previous End + 1"):
        assert needle in text, needle
    app.help.hide()
    assert not app.help.visible

    app.help.click()  # click pins it open
    assert app.help.visible and app.help.pinned
    app.help.click()  # click again closes
    assert not app.help.visible


def test_help_popup_opens_on_hover_and_closes_on_leave(app):
    app.help_btn.event_generate("<Enter>")
    wait(app, 0.5)
    assert app.help.visible and not app.help.pinned
    app.help_btn.event_generate("<Leave>")
    wait(app, 0.4)
    assert not app.help.visible


def test_help_popup_f1_and_escape(app):
    press(app.zone, "F1")
    assert app.help.visible and app.help.pinned
    press(app.zone, "Escape")
    assert not app.help.visible
    press(app.zone, "F1")
    press(app.zone, "F1")
    assert not app.help.visible


def test_help_popup_click_elsewhere_closes_pinned_guide(app):
    app.help.click()
    app.update()
    app.tree.event_generate("<Button-1>", x=5, y=5)
    app.update()
    assert not app.help.visible


@pytest.mark.parametrize("code", list(LANGUAGES))
def test_help_popup_is_translated_and_on_screen(app, code):
    app.set_language(code)
    app.help.show()
    app.update()
    text = popup_text(app)
    for key in ("help.title", "help.step1", "help.step3", "help.hotkeys", "hk.enter", "hk.f1", "help.note"):
        assert tr(key) in text, (code, key)
    x, y = app.help.win.winfo_rootx(), app.help.win.winfo_rooty()
    w, h = app.help.win.winfo_width(), app.help.win.winfo_height()
    assert x >= 0 and y >= 0 and x + w <= app.winfo_screenwidth() and y + h <= app.winfo_screenheight()
    app.help.hide()


# ================================================================== dialogs
def test_dialog_buttons_follow_the_app_language_not_windows(app):
    app.set_language("de")
    seen = {}

    def click_no():
        dlg = [w for w in app.winfo_children() if isinstance(w, widgets.ModalDialog)][-1]
        buttons = sorted((w for w in descendants(dlg) if w.winfo_class() == "TButton"), key=lambda b: b.winfo_rootx())
        seen["labels"] = [b.cget("text") for b in buttons]  # left to right
        buttons[-1].invoke()  # "Nein"

    app.after(150, click_no)
    result = widgets.ask(app, "yesno", "t", "m")
    assert seen["labels"] == ["Ja", "Nein"] and result is False


def test_dialog_enter_activates_default_and_escape_cancels(app):
    def current():
        return [w for w in app.winfo_children() if isinstance(w, widgets.ModalDialog)][-1]

    def enter():
        dlg = current()
        dlg._buttons[dlg._default].focus_force()
        dlg.update()
        dlg._buttons[dlg._default].event_generate("<Return>")

    app.after(150, enter)
    assert widgets.ask(app, "yesno", "t", "m", default_yes=False) is False  # default button = No

    def esc():
        dlg = current()
        dlg._buttons[0].focus_force()
        dlg.update()
        dlg._buttons[0].event_generate("<Escape>")

    app.after(150, esc)
    assert widgets.ask(app, "okcancel", "t", "m") is False
    app.after(150, enter)
    assert widgets.ask(app, "okcancel", "t", "m") is True  # default = OK


def test_zone_list_dialog_edits_the_list(app, monkeypatch):
    saved = []
    dlg = widgets.ZoneListDialog(app, app._zone_defs(), zl.default_zone_defs(), saved.append)
    app.update()
    assert dlg.text.get("1.0", "end").splitlines()[0] == "Windfang"
    dlg.text.delete("1.0", "end")
    dlg.text.insert("1.0", "Neu A\nNeu B\n\nneu a\n*Garten {Links|Rechts}\n")
    dlg._save()
    assert saved == [[("Neu A", False), ("Neu B", False), ("Garten Links", True), ("Garten Rechts", True)]]

    dlg2 = widgets.ZoneListDialog(app, [("x", False)], zl.default_zone_defs(), saved.append)
    dlg2._reset()
    assert dlg2.text.get("1.0", "end").splitlines() == zl.format_zone_defs(zl.default_zone_defs())
    assert "*Garten" in dlg2.text.get("1.0", "end").splitlines()
    shown = []
    monkeypatch.setattr(widgets, "ask", lambda *a, **k: shown.append(a[3]) or True)
    dlg2.text.delete("1.0", "end")
    dlg2._save()
    assert shown == [tr("zl.empty")]
    dlg2.destroy()


# ============================================ screens, scaling, packaged startup
def test_window_fits_a_1366x768_screen(tmp_path, monkeypatch):
    monkeypatch.setenv("ZONEENTRY_HOME", str(tmp_path / "d"))
    monkeypatch.setattr(tk.Tk, "winfo_screenwidth", lambda self: 1366)
    monkeypatch.setattr(tk.Tk, "winfo_screenheight", lambda self: 768)
    a = appmod.App()
    try:
        a.update()
        w, h = a.winfo_width(), a.winfo_height()
        assert w <= 1366 and h <= 768 - 60, (w, h)
        assert a.minsize()[0] <= 1366 and a.minsize()[1] <= 768
    finally:
        a.destroy()


def test_display_scaling_enlarges_icon_and_layout(tmp_path, monkeypatch):
    monkeypatch.setenv("ZONEENTRY_HOME", str(tmp_path / "d"))
    monkeypatch.setattr(tk.Tk, "winfo_fpixels", lambda self, v: 144.0)  # Windows "150 %"
    monkeypatch.setattr(tk.Tk, "winfo_screenwidth", lambda self: 1920)
    monkeypatch.setattr(tk.Tk, "winfo_screenheight", lambda self: 1080)
    a = appmod.App()
    try:
        assert a.scale == 1.5 and a.px(100) == 150
        assert a.globe.width() == 28  # 18 * 1.5 = 27 -> nearest embedded size
        assert a.px(860) <= a.minsize()[0] <= 1920 - 20  # scaled with the display, capped to the screen
    finally:
        a.destroy()


def test_selftest_mode_used_by_the_build_pipeline(tmp_path, monkeypatch):
    monkeypatch.setenv("ZONEENTRY_HOME", "placeholder")  # so the test's override is undone afterwards
    assert appmod.selftest() == 0
    log = Path(__import__("tempfile").gettempdir()) / "zoneentry-selftest.log"
    assert log.read_text(encoding="utf-8").strip() == "OK"
    i18n.set_language("en")


# ================================================================ screenshots
@pytest.mark.parametrize("code", list(LANGUAGES))
def test_screenshot(app, tmp_path, code):
    """Not an assertion: leaves a PNG per language for a visual check (set ZONEENTRY_SHOTS=<dir>)."""
    PIL = pytest.importorskip("PIL.ImageGrab")
    rows, _ = zl.import_xlsx(SAMPLE)
    app.set_language(code)
    app.store.set("Beispiel-Markt Köln")
    for r in rows[:13]:
        app.entries.append(r)
    app.rebuild_table()
    app.update_suggestion()
    app.info(lambda: tr("status.added", label=app.entries[-1].label()))
    app.zone.focus_force()
    app.zone.var.set("ka")
    app.update()
    app.update_idletasks()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    img = PIL.grab(bbox=(x, y, x + app.winfo_width(), y + app.winfo_height()), xdisplay=os.environ["DISPLAY"])
    out_dir = Path(os.environ.get("ZONEENTRY_SHOTS", tmp_path))
    out_dir.mkdir(parents=True, exist_ok=True)
    img.save(out_dir / f"shot-{code}.png")
    assert (out_dir / f"shot-{code}.png").exists()


def test_screenshot_help_popup(app, tmp_path):
    PIL = pytest.importorskip("PIL.ImageGrab")
    rows, _ = zl.import_xlsx(SAMPLE)
    app.set_language(os.environ.get("ZONEENTRY_HELP_LANG", "en"))
    for r in rows[:9]:
        app.entries.append(r)
    app.rebuild_table()
    app.update_suggestion()
    app.help.show()
    app.update()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    img = PIL.grab(bbox=(x, y, x + app.winfo_width(), y + app.winfo_height()), xdisplay=os.environ["DISPLAY"])
    out_dir = Path(os.environ.get("ZONEENTRY_SHOTS", tmp_path))
    out_dir.mkdir(parents=True, exist_ok=True)
    img.save(out_dir / "shot-help.png")


# ================================================================ new store (day 2)
def test_new_store_clears_rows_and_name_and_warns_until_exported(app, tmp_path, monkeypatch):
    messages = []
    app.ask = lambda kind, title, msg, default_yes=True: messages.append(msg) or True
    app.store.set("Hornbach Köln")
    add_row(app, "Kassen", "10", start="1")
    assert len(app.entries) == 1

    app.new_list()  # not exported yet -> the dialog carries the warning
    assert tr("dlg.new.unexported").strip() in messages[-1]
    assert app.entries == [] and app.store.get() == ""

    app.undo()  # rows come back
    assert len(app.entries) == 1
    monkeypatch.setattr(appmod.filedialog, "asksaveasfilename", lambda **k: str(tmp_path / "x.xlsx"))
    app.export()
    app.new_list()  # exported -> no warning
    assert tr("dlg.new.unexported").strip() not in messages[-1]
    assert app.entries == []


# ================================================================ floors (EG / OG) and outdoor zones
def test_floor_prefix_is_added_to_indoor_zones_only(app):
    app.set_floor("OG")
    add_row(app, "san", "10", start="1")
    add_row(app, "garten", "20")  # "Garten" is an outdoor zone
    assert [e.zone for e in app.entries] == ["OG Sanitär", "Garten"]
    app.set_floor("")
    add_row(app, "kassen", "30")
    assert app.entries[-1].zone == "Kassen"


def test_floor_is_sticky_and_hotkeys_switch_it(app):
    add_row(app, "san", "10", start="1")
    assert app.entries[0].zone == "Sanitär" and app.floor.get() == ""
    press(app.zone, "Control-Key-1")
    assert app.floor.get() == "EG"
    add_row(app, "kassen", "20")
    add_row(app, "holz", "30")  # still EG: nothing was touched
    press(app.zone, "Control-Key-2")
    assert app.floor.get() == "OG"
    add_row(app, "deko", "40")
    press(app.zone, "Control-Key-0")
    assert app.floor.get() == ""
    assert [e.zone for e in app.entries] == ["Sanitär", "EG Kassen", "EG Holz", "OG Deko"]


def test_clicking_a_floor_button_sets_the_floor_and_returns_focus_to_the_zone_box(app):
    app.floor_buttons["EG"].invoke()
    app.update()
    assert app.floor.get() == "EG" and app.focus_get() is app.zone
    assert "EG" in app.status.get()
    app.floor_buttons[""].invoke()
    assert app.floor.get() == "" and app.status.get() == tr("status.floor_none")


def test_floor_buttons_are_skipped_by_tab(app):
    assert all(not int(str(b.cget("takefocus")) or 0) for b in app.floor_buttons.values())


def test_status_shows_the_final_text_when_a_zone_is_picked(app):
    app.set_floor("OG")
    app.zone.focus_force()
    app.zone.var.set("san")
    press(app.zone, "Return")
    assert app.status.get() == tr("status.zone_selected", zone="OG Sanitär")
    app.zone.clear()
    app.zone.var.set("garten")
    press(app.zone, "Return")
    assert app.status.get() == tr("status.zone_selected", zone="Garten")


def test_editing_a_row_shows_its_own_floor_and_restores_the_sticky_one(app):
    app.set_floor("EG")
    add_row(app, "san", "10", start="1")
    app.set_floor("OG")
    add_row(app, "san", "20")
    app.set_floor("EG")  # what the person is counting now
    app.begin_edit(1)
    assert app.floor.get() == "OG" and app.zone.var.get() == "Sanitär"
    app.end.var.set("25")
    press(app.end, "Return")
    assert app.entries[1].zone == "OG Sanitär" and app.entries[1].end == "0025"
    assert app.floor.get() == "EG"  # back to the sticky floor
    app.begin_edit(0)
    app.cancel_edit()
    assert app.floor.get() == "EG"


def test_a_zone_that_really_is_called_eg_something_is_not_split(app):
    app.zones.append("EG Lager")
    app.entries.append(zl.Entry("0001", "0005", "EG Lager"))
    app.rebuild_table()
    app.set_floor("OG")
    app.begin_edit(0)
    assert app.zone.var.get() == "EG Lager" and app.floor.get() == ""
    app.cancel_edit()
    assert app.floor.get() == "OG"


def test_floor_survives_a_restart_and_new_store_clears_it(app):
    app.set_floor("OG")
    add_row(app, "san", "10", start="1")
    app.flush_session()
    second = appmod.App()
    try:
        assert second.floor.get() == "OG"
    finally:
        second.destroy()
    app.ask = lambda *a, **k: True
    app.new_list()
    assert app.floor.get() == ""
    app.flush_session()
    assert zl.load_session(app.data_dir)["floor"] == ""


def test_floor_while_editing_does_not_overwrite_the_saved_sticky_floor(app):
    app.set_floor("EG")
    add_row(app, "san", "10", start="1")
    app.set_floor("")
    app.begin_edit(0)
    app.flush_session()
    assert zl.load_session(app.data_dir)["floor"] == ""
    app.cancel_edit()


# ---------------------------------------------------------------- unknown zones: add on the fly
def test_unknown_zone_can_be_added_as_an_indoor_zone(app):
    app.ask_choice = lambda *a, **k: "add"
    app.set_floor("OG")
    add_row(app, "gartenhaus", "10", start="1")  # typed in lower case -> tidied up
    assert "Gartenhaus" in app.zones and not app.is_outdoor("Gartenhaus")
    assert app.entries[0].zone == "OG Gartenhaus"
    assert "Gartenhaus" in (app.data_dir / "zones.txt").read_text(encoding="utf-8").splitlines()


def test_unknown_zone_can_be_added_as_an_outdoor_zone(app):
    app.ask_choice = lambda *a, **k: "outdoor"
    app.set_floor("OG")
    add_row(app, "Terrasse", "10", start="1")
    assert app.is_outdoor("Terrasse")
    assert app.entries[0].zone == "Terrasse"  # no OG
    assert "*Terrasse" in (app.data_dir / "zones.txt").read_text(encoding="utf-8").splitlines()
    assert zl.load_zone_defs(app.data_dir)[-1] == ("Terrasse", True)


def test_added_zone_is_found_by_autocomplete_next_time(app):
    app.ask_choice = lambda *a, **k: "add"
    add_row(app, "Regenerationsbereich", "10", start="1")
    assert zl.filter_zones("regen", app.zones)[0] == "Regenerationsbereich"


def test_zone_list_editor_keeps_the_outdoor_marks(app):
    seen = []
    app.edit_zone_list_dialog = None
    dlg = widgets.ZoneListDialog(app, app._zone_defs(), zl.default_zone_defs(), lambda defs: seen.append(defs))
    dlg.text.delete("1.0", "end")
    dlg.text.insert("1.0", "Sanitär\n*Garten {Links|Rechts}\n")
    dlg._save()
    assert seen == [[("Sanitär", False), ("Garten Links", True), ("Garten Rechts", True)]]


def test_import_adds_bare_zone_names_not_prefixed_ones(app, tmp_path, monkeypatch):
    path = tmp_path / "in.xlsx"
    zl.export_xlsx(
        path,
        [
            zl.Entry("0001", "0010", "EG Neuer Bereich"),
            zl.Entry("0011", "0020", "OG Neuer Bereich"),
            zl.Entry("0021", "0030", "OG Sanitär"),
            zl.Entry("0031", "0040", "Garten Links"),
        ],
    )
    monkeypatch.setattr(appmod.filedialog, "askopenfilename", lambda **k: str(path))
    app.import_file()
    assert [e.zone for e in app.entries][:3] == ["EG Neuer Bereich", "OG Neuer Bereich", "OG Sanitär"]
    assert app.zones.count("Neuer Bereich") == 1
    assert "EG Neuer Bereich" not in app.zones and "OG Sanitär" not in app.zones
    assert "Garten Links" in app.zones and app.is_outdoor("Garten Links")


def test_export_contains_the_prefixed_text(app, tmp_path, monkeypatch):
    from openpyxl import load_workbook

    app.set_floor("EG")
    add_row(app, "san", "10", start="1")
    out = tmp_path / "x.xlsx"
    monkeypatch.setattr(appmod.filedialog, "asksaveasfilename", lambda **k: str(out))
    app.export()
    ws = load_workbook(out).active
    assert [c.value for c in ws[2]] == ["0001", "0010", "EG Sanitär"]


def test_floor_selector_labels_and_buttons_in_every_language(app):
    for code in i18n.LANGUAGES:
        app.set_language(code)
        app.update()
        assert [b.cget("text") for b in app.floor_buttons.values()] == ["–", "EG", "OG"]
        assert app.winfo_reqwidth() <= app.winfo_screenwidth()
