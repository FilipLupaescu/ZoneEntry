"""End-to-end GUI test: types the sample sheet through the real widgets.

Needs a display, so it only runs when ZONEENTRY_GUI_TESTS=1
(on Linux:  xvfb-run -a env ZONEENTRY_GUI_TESTS=1 python -m pytest tests/test_gui_smoke.py).
"""
import os
from pathlib import Path
from tkinter import messagebox

import pytest

if os.environ.get("ZONEENTRY_GUI_TESTS") != "1":
    pytest.skip("set ZONEENTRY_GUI_TESTS=1 to run GUI tests", allow_module_level=True)

import app as appmod
import zonelogic as zl

SAMPLE = Path(__file__).parent / "data" / "ZoneUpdate_sample.xlsx"


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("ZONEENTRY_HOME", str(tmp_path / "data"))

    def no_dialog(*a, **k):  # a modal dialog would block a headless run forever
        raise AssertionError(f"unexpected dialog: {a[:2]}")

    for name in ("askyesno", "askokcancel", "showinfo", "showwarning", "showerror"):
        monkeypatch.setattr(messagebox, name, no_dialog)
    a = appmod.App()
    a.update()
    yield a
    a.destroy()


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


def test_whole_sample_typed_through_the_gui(app):
    rows, _ = zl.import_xlsx(SAMPLE)
    for i, row in enumerate(rows):
        suggested = app.start.var.get()
        needs_start = suggested != row.start  # first row, or numbering skips (7747 -> 7750)
        add_row(app, row.zone, row.end, start=row.start if needs_start else None)
        assert len(app.entries) == i + 1, f"row {i + 1} ({row}) was not added: {app.status.get()}"
    assert app.entries == rows
    assert app.start.var.get() == "7765"  # last End 7764 + 1


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


def test_unknown_zone_is_rejected_and_nothing_is_added(app):
    add_row(app, "zzz", "10", start="1")
    assert app.entries == []
    assert "not in the Store Zone list" in app.status.get()


def test_end_before_start_is_rejected(app):
    add_row(app, "holz", "5", start="10")
    assert app.entries == []
    assert "smaller" in app.status.get()


def test_overlap_asks_and_respects_no(app, monkeypatch):
    add_row(app, "kassen", "10", start="1")
    asked = []
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: asked.append(a) or False)
    add_row(app, "holz", "20", start="5")
    assert asked and len(app.entries) == 1
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    press(app.end, "Return")
    assert len(app.entries) == 2


def test_edit_delete_undo(app):
    add_row(app, "kassen", "10", start="1")
    add_row(app, "holz", "20")
    add_row(app, "deko", "30")

    app.begin_edit(1)
    assert app.edit_index == 1 and app.end.var.get() == "0020"
    app.end.var.set("0018")
    press(app.end, "Return")
    assert app.entries[1].end == "0018" and app.edit_index is None
    assert app.start.var.get() == "0031"  # suggestion still follows the last row

    app.tree.selection_set("2")
    app.delete_selected()
    assert len(app.entries) == 2 and app.start.var.get() == "0019"  # 0018 + 1
    app.undo()
    assert len(app.entries) == 3 and app.entries[2].zone == "Deko"
    app.undo()  # undoes the edit
    assert app.entries[1].end == "0020"


def test_edit_that_overlaps_asks_first(app, monkeypatch):
    add_row(app, "kassen", "10", start="1")
    add_row(app, "holz", "20")
    asked = []
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: asked.append(a) or False)
    app.begin_edit(0)
    app.end.var.set("0015")  # would run into row 2
    press(app.end, "Return")
    assert asked and app.entries[0].end == "0010"


def test_autosave_and_restore(app, tmp_path):
    add_row(app, "kassen", "10", start="1")
    app.store.set("Markt Test")
    app._save_session()
    second = appmod.App()
    try:
        assert second.entries == app.entries and second.store.get() == "Markt Test"
        assert second.start.var.get() == "0011"
    finally:
        second.destroy()


def test_screenshot(app, tmp_path):
    """Not an assertion: leaves a PNG next to the test for a visual check."""
    PIL = pytest.importorskip("PIL.ImageGrab")
    rows, _ = zl.import_xlsx(SAMPLE)
    app.store.set("Beispiel-Markt Köln")
    for r in rows[:12]:
        app.entries.append(r)
    app.refresh()
    app.update_suggestion()
    app.zone.focus_force()
    app.zone.var.set("ka")
    app.update()
    app.update_idletasks()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    img = PIL.grab(bbox=(x, y, x + app.winfo_width(), y + app.winfo_height()), xdisplay=os.environ["DISPLAY"])
    out = Path(os.environ.get("ZONEENTRY_SHOT", tmp_path / "shot.png"))
    img.save(out)
    assert out.exists()
