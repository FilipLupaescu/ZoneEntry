# ZoneEntry

Fast keyboard-driven entry of **Store Zones → Inventory Zone ranges** for store inventory counts,
with one-click export to Excel in `ZoneUpdate.xlsx` layout (`from | to | Division`).

Develop on macOS, ship a native Windows `.exe`. Python + Tkinter (ships with Python) + openpyxl, nothing else.

---

## How the entry works

One row = a Store Zone + the first and last Inventory Zone inside it.

| Step | You do | The app does |
|---|---|---|
| 1 | Type the first letters of a Store Zone (`san`) | Filters the list live: `Sanitär` on top. Also matches `sanitaer`, `aussen` → `Außenbereich`, word starts (`wand` → `Garten Wand`), upper/lower case doesn't matter |
| 2 | **Enter** (or Tab / click) | Takes the top suggestion, jumps to **End Zone** |
| 3 | Type the End Zone (`56`) **Enter** | Pads to `0056`, adds the row, then fills **Start Zone** with previous End + 1 (`0057`), clears the fields and puts the cursor back in Store Zone |

So a normal row is: `kas` ⏎ `42` ⏎ — nothing else.

* **Start Zone is editable.** If the numbering skips (e.g. 7747 → 7750) just type over it. The status bar tells you what was skipped.
* **First row:** nothing to suggest yet, so you type the Start Zone yourself.
* **Short numbers are padded:** `7` → `0007`. Only digits are accepted, 0001–9999.
* **Exact name beats longer ones:** typing `Garten` + Enter gives `Garten`, not `Garten Grill`.
* Up/Down arrows move through suggestions. Esc closes the list.

### Safety nets
* **Overlap check:** a range that overlaps an existing row asks before it's added.
* **Gap hint** in the bottom-right, e.g. `32 rows · 6001–7764 · 1159 zones · not covered: 7748–7749`.
  Jumps into a new thousand block (6397 → 7001) are treated as intentional and not reported.
* **Edit** a row: double-click it, or select + `F2` / `Enter`. Enter saves, Esc cancels.
* **Delete** with the Delete key, **Undo** with Ctrl+Z (Cmd+Z on Mac), up to 200 steps.
* **Autosave:** every change is saved. Close the window or crash, reopen, and your list is back.
* The same Store Zone can appear in several rows.

### Other buttons
* **Import…** loads an existing `from | to | Division` sheet (e.g. last time's file) so you can continue it. Unknown zone names are added to your list.
* **Zone list…** edit the predefined Store Zones (one per line). Saved in `zones.txt`.
* **New list** clears the rows for the next store.
* **Export to Excel…** (Ctrl+S / Cmd+S). Suggested file name: `ZoneUpdate_<store>_<date>.xlsx`.

---

## Excel layout (copied from your `ZoneUpdate.xlsx`)

* Sheet `Tabelle1`, headers `from`, `to`, `Division` in A1:C1, one row per entry from row 2
* Every cell is **text**, column-wide, so `0042` keeps its leading zeros and blank cells below stay text
* Font Aptos Narrow 11, column widths 11 / 11.86 / 23.14

A test (`tests/test_zonelogic.py::test_export_matches_original_layout`) re-exports your original sheet and compares it to the original cell by cell.

---

## Run it on Mac

```bash
cd ZoneEntry
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Use Python from **python.org** (or `brew install python-tk`). The Python that comes with Xcode/macOS ships an old Tk that renders badly.

Run the tests: `pip install pytest && python -m pytest -q`

---

## Get the Windows `.exe` (from your Mac)

PyInstaller can't cross-compile, so the `.exe` has to be built *on Windows*. You don't need a Windows PC:
GitHub builds it for you (free). One-time setup:

1. Create a GitHub account if you don't have one, and install git (`xcode-select --install`).
2. In this folder:
   ```bash
   git init -b main
   git add .
   git commit -m "ZoneEntry"
   # create an empty PRIVATE repo called ZoneEntry on github.com, then:
   git remote add origin https://github.com/<your-username>/ZoneEntry.git
   git push -u origin main
   ```
3. On GitHub open the repo → **Actions** → *Build Windows app*. After ~3 minutes click the finished run and
   download the artifact **ZoneEntry-windows** (a zip containing `ZoneEntry.exe`).

Every later `git push` builds a fresh `.exe` the same way. The workflow also runs the tests first, so a broken
build never produces an exe.

**Alternatives:** a Windows PC or a Windows VM (Parallels/UTM) → install Python from python.org and double-click `build_windows.bat`.

### Using the exe
* Single file, no installer, no Python needed on the target PC. Copy it anywhere (USB stick is fine).
* First launch: Windows SmartScreen may say *"Windows protected your PC"* because the exe isn't code-signed.
  Click **More info → Run anyway**. Some company antivirus tools flag every PyInstaller one-file exe; if that happens,
  change `--onefile` to `--onedir` in the workflow and ship the whole `ZoneEntry` folder instead (far fewer false alarms).

---

## Where your data lives

| What | Windows | macOS |
|---|---|---|
| Folder | `%APPDATA%\ZoneEntry` | `~/Library/Application Support/ZoneEntry` |
| `zones.txt` | predefined Store Zones (edit in the app or in any text editor, UTF-8) | same |
| `session.json` | autosaved rows + store name + last export folder | same |

Delete `zones.txt` to get the default list back. Set the environment variable `ZONEENTRY_HOME` to use a different folder.

---

## Project layout

```
app.py              the window (Tkinter): autocomplete, table, buttons
zonelogic.py        all rules, no GUI: padding, +1, search, overlap/gaps, Excel read/write
tests/              unit tests + a GUI test that types your whole sample sheet
.github/workflows/  builds ZoneEntry.exe on GitHub's Windows machines
build_windows.bat   same build, on a Windows PC
```

GUI test (needs a display): `ZONEENTRY_GUI_TESTS=1 python -m pytest tests/test_gui_smoke.py`
