"""UI translations for ZoneEntry: English, Romanian, Hungarian, Polish, German.

Every string lives in ONE place with all languages side by side, so a missing
translation is easy to spot (tests/test_i18n.py fails if one is missing or if a
{placeholder} differs between languages).

Store-zone names (Sanitär, Kassen, ...) are data, not UI, and are never translated.
The Excel file headers (from / to / Division) are part of the file format and also
stay as they are.

To add a language: add its code to LANGUAGES, then add one more entry to every
string below (the test tells you which ones you missed).
"""
from __future__ import annotations

import os
import sys

LANGUAGES: dict[str, str] = {  # code -> name shown in the language menu (always in its own language)
    "en": "English",
    "ro": "Română",
    "hu": "Magyar",
    "pl": "Polski",
    "de": "Deutsch",
}
DEFAULT_LANGUAGE = "en"
_current = DEFAULT_LANGUAGE


def _t(en: str, ro: str, hu: str, pl: str, de: str) -> dict[str, str]:
    return {"en": en, "ro": ro, "hu": hu, "pl": pl, "de": de}


STRINGS: dict[str, dict[str, str]] = {
    # ------------------------------------------------------------ main window
    "app.title": _t(
        "ZoneEntry {version} – Inventory Zones",
        "ZoneEntry {version} – Zone de inventar",
        "ZoneEntry {version} – Leltározási zónák",
        "ZoneEntry {version} – Strefy inwentaryzacji",
        "ZoneEntry {version} – Inventurzonen",
    ),
    "store.label": _t("Store / location:", "Magazin / locație:", "Üzlet / helyszín:", "Sklep / lokalizacja:", "Markt / Standort:"),
    "btn.import": _t("Import…", "Importă…", "Importálás…", "Importuj…", "Importieren…"),
    "btn.zonelist": _t("Zone list…", "Lista zonelor…", "Zónalista…", "Lista stref…", "Zonenliste…"),
    "btn.new": _t("New store", "Magazin nou", "Új üzlet", "Nowy sklep", "Neuer Markt"),
    "box.title": _t("New entry", "Intrare nouă", "Új tétel", "Nowy wpis", "Neuer Eintrag"),
    "lbl.store_zone": _t("Store Zone", "Zonă magazin", "Üzletzóna", "Strefa sklepu", "Marktzone"),
    "lbl.start": _t("Start Zone", "Zonă de start", "Kezdőzóna", "Strefa początkowa", "Startzone"),
    "lbl.end": _t("End Zone", "Zonă de final", "Zárózóna", "Strefa końcowa", "Endzone"),
    "btn.add": _t("Add", "Adaugă", "Hozzáadás", "Dodaj", "Hinzufügen"),
    "btn.save": _t("Save", "Salvează", "Mentés", "Zapisz", "Speichern"),
    "col.n": _t("#", "#", "#", "#", "#"),
    "col.from": _t("From", "De la", "Kezdő", "Od", "Von"),
    "col.to": _t("To", "Până la", "Záró", "Do", "Bis"),
    "col.zone": _t("Store Zone", "Zonă magazin", "Üzletzóna", "Strefa sklepu", "Marktzone"),
    "col.count": _t("Zones", "Zone", "Zónák", "Strefy", "Zonen"),
    "btn.edit": _t("Edit", "Editează", "Szerkesztés", "Edytuj", "Bearbeiten"),
    "btn.delete": _t("Delete", "Șterge", "Törlés", "Usuń", "Löschen"),
    "btn.undo": _t("Undo", "Anulare", "Visszavonás", "Cofnij", "Rückgängig"),
    "btn.export": _t(
        "Export to Excel…", "Exportă în Excel…", "Exportálás Excelbe…", "Eksportuj do Excela…", "Nach Excel exportieren…"
    ),
    # Names of keys as printed on the keyboard
    "key.ctrl": _t("Ctrl", "Ctrl", "Ctrl", "Ctrl", "Strg"),
    "key.del": _t("Del", "Del", "Del", "Del", "Entf"),
    # ------------------------------------------------------------------ hints
    "hint.first": _t(
        "First row: type the Start Zone yourself (e.g. 0001), then the End Zone.",
        "Primul rând: introdu singur Zona de start (ex. 0001), apoi Zona de final.",
        "Első sor: a kezdőzónát add meg te (pl. 0001), utána a zárózónát.",
        "Pierwszy wiersz: wpisz strefę początkową samodzielnie (np. 0001), potem strefę końcową.",
        "Erste Zeile: Startzone selbst eingeben (z. B. 0001), dann die Endzone.",
    ),
    "hint.suggest": _t(
        "Start Zone suggested: {start}  (previous End {prev} + 1) – overwrite it if the numbering skips.",
        "Zonă de start sugerată: {start}  (finalul anterior {prev} + 1) – suprascrie dacă numerotarea sare.",
        "Javasolt kezdőzóna: {start}  (előző vég {prev} + 1) – írd felül, ha a számozás kihagy.",
        "Sugerowana strefa początkowa: {start}  (poprzedni koniec {prev} + 1) – nadpisz, jeśli numeracja ma przerwę.",
        "Vorgeschlagene Startzone: {start}  (vorheriges Ende {prev} + 1) – überschreiben, falls die Nummerierung springt.",
    ),
    "hint.max": _t(
        "Zone 9999 reached – there is no next zone.",
        "S-a atins zona 9999 – nu există o zonă următoare.",
        "Elérted a 9999-es zónát – nincs további zóna.",
        "Osiągnięto strefę 9999 – nie ma następnej strefy.",
        "Zone 9999 erreicht – es gibt keine weitere Zone.",
    ),
    "hint.editing": _t(
        "Editing row {n} – Enter saves, Esc cancels.",
        "Editezi rândul {n} – Enter salvează, Esc anulează.",
        "A(z) {n}. sor szerkesztése – Enter ment, Esc elvet.",
        "Edycja wiersza {n} – Enter zapisuje, Esc anuluje.",
        "Zeile {n} wird bearbeitet – Enter speichert, Esc bricht ab.",
    ),
    # ----------------------------------------------------------------- status
    "status.ready": _t(
        "Ready. Type a Store Zone to begin.",
        "Gata. Scrie o zonă de magazin pentru a începe.",
        "Kész. Kezdéshez írj be egy üzletzónát.",
        "Gotowe. Wpisz strefę sklepu, aby zacząć.",
        "Bereit. Marktzone eingeben, um zu beginnen.",
    ),
    "status.restored": _t(
        "Restored {n} rows from your last session.",
        "Am restaurat {n} rânduri din sesiunea anterioară.",
        "{n} sor visszaállítva az előző munkamenetből.",
        "Przywrócono wiersze z ostatniej sesji: {n}.",
        "{n} Zeilen aus der letzten Sitzung wiederhergestellt.",
    ),
    "status.zone_selected": _t("Selected: {zone}", "Selectat: {zone}", "Kiválasztva: {zone}", "Wybrano: {zone}", "Ausgewählt: {zone}"),
    "status.added": _t("Added  {label}", "Adăugat  {label}", "Hozzáadva  {label}", "Dodano  {label}", "Hinzugefügt  {label}"),
    "status.skips": _t(
        "⚠ skips {range}", "⚠ sare peste {range}", "⚠ kihagyja: {range}", "⚠ pomija {range}", "⚠ überspringt {range}"
    ),
    "status.not_after": _t(
        "⚠ not after the previous row",
        "⚠ nu urmează după rândul anterior",
        "⚠ nem az előző sor után következik",
        "⚠ nie następuje po poprzednim wierszu",
        "⚠ nicht nach der vorherigen Zeile",
    ),
    "status.updated": _t(
        "Row {n} updated:  {label}",
        "Rândul {n} actualizat:  {label}",
        "{n}. sor frissítve:  {label}",
        "Zaktualizowano wiersz {n}:  {label}",
        "Zeile {n} aktualisiert:  {label}",
    ),
    "status.edit_cancelled": _t(
        "Edit cancelled.", "Editare anulată.", "Szerkesztés elvetve.", "Anulowano edycję.", "Bearbeitung abgebrochen."
    ),
    "status.deleted": _t(
        "Deleted {n} row(s). Undo with {key}.",
        "Am șters {n} rând(uri). Anulare cu {key}.",
        "{n} sor törölve. Visszavonás: {key}.",
        "Usunięto wierszy: {n}. Cofnij: {key}.",
        "{n} Zeile(n) gelöscht. Rückgängig mit {key}.",
    ),
    "status.undone": _t("Undone.", "Anulat.", "Visszavonva.", "Cofnięto.", "Rückgängig gemacht."),
    "status.nothing_undo": _t(
        "Nothing to undo.", "Nimic de anulat.", "Nincs mit visszavonni.", "Nie ma czego cofać.", "Nichts rückgängig zu machen."
    ),
    "status.newlist": _t(
        "New store. Enter the store name, then the first Store Zone.",
        "Magazin nou. Introdu numele magazinului, apoi prima zonă de magazin.",
        "Új üzlet. Add meg az üzlet nevét, majd az első üzletzónát.",
        "Nowy sklep. Wpisz nazwę sklepu, a potem pierwszą strefę sklepu.",
        "Neuer Markt. Marktnamen eingeben, dann die erste Marktzone.",
    ),
    "status.zones_saved": _t(
        "Zone list saved ({n} zones).",
        "Lista zonelor a fost salvată ({n} zone).",
        "Zónalista mentve ({n} zóna).",
        "Zapisano listę stref ({n}).",
        "Zonenliste gespeichert ({n} Zonen).",
    ),
    "status.zones_save_failed": _t(
        "Could not save the zone list: {err}",
        "Nu am putut salva lista zonelor: {err}",
        "A zónalista mentése nem sikerült: {err}",
        "Nie można zapisać listy stref: {err}",
        "Zonenliste konnte nicht gespeichert werden: {err}",
    ),
    "status.exported": _t(
        "Exported {n} rows → {path}",
        "Am exportat {n} rânduri → {path}",
        "{n} sor exportálva → {path}",
        "Wyeksportowano wiersze: {n} → {path}",
        "{n} Zeilen exportiert → {path}",
    ),
    "status.imported": _t(
        "Imported {n} rows.", "Am importat {n} rânduri.", "{n} sor importálva.", "Zaimportowano wiersze: {n}.", "{n} Zeilen importiert."
    ),
    "status.imported_new": _t(
        "Added {n} new zone name(s) to your list.",
        "Am adăugat {n} nume noi de zone în listă.",
        "{n} új zónanév került a listába.",
        "Dodano nowe nazwy stref do listy: {n}.",
        "{n} neue Zonennamen zur Liste hinzugefügt.",
    ),
    "status.imported_skipped": _t(
        "Skipped {n} bad row(s).",
        "Am ignorat {n} rând(uri) greșite.",
        "{n} hibás sor kihagyva.",
        "Pominięto błędne wiersze: {n}.",
        "{n} fehlerhafte Zeile(n) übersprungen.",
    ),
    "summary.none": _t("No rows yet", "Niciun rând încă", "Még nincs sor", "Brak wierszy", "Noch keine Zeilen"),
    "summary.main": _t(
        "{rows} rows · {lo}–{hi} · {zones} zones",
        "{rows} rânduri · {lo}–{hi} · {zones} zone",
        "{rows} sor · {lo}–{hi} · {zones} zóna",
        "wiersze: {rows} · {lo}–{hi} · strefy: {zones}",
        "{rows} Zeilen · {lo}–{hi} · {zones} Zonen",
    ),
    "summary.gaps": _t(
        "not covered: {list}", "neacoperite: {list}", "nem lefedett: {list}", "nieobjęte: {list}", "nicht abgedeckt: {list}"
    ),
    # ----------------------------------------------------------------- errors
    "err.zone_unknown": _t(
        "'{t}' is not in the Store Zone list (add it via “Zone list…”).",
        "„{t}” nu este în lista zonelor de magazin (adaug-o din „Lista zonelor…”).",
        "A(z) „{t}” nincs az üzletzónák listájában (add hozzá a „Zónalista…” gombbal).",
        "„{t}” nie ma na liście stref sklepu (dodaj ją przez „Lista stref…”).",
        "„{t}“ steht nicht in der Zonenliste (über „Zonenliste…“ hinzufügen).",
    ),
    "err.zone_type": _t(
        "Type a few letters of the Store Zone first.",
        "Scrie mai întâi câteva litere din zona de magazin.",
        "Előbb írj be néhány betűt az üzletzónából.",
        "Najpierw wpisz kilka liter strefy sklepu.",
        "Zuerst einige Buchstaben der Marktzone eingeben.",
    ),
    "err.zone_pick": _t(
        "Pick a Store Zone first.",
        "Alege mai întâi o zonă de magazin.",
        "Előbb válassz üzletzónát.",
        "Najpierw wybierz strefę sklepu.",
        "Zuerst eine Marktzone auswählen.",
    ),
    "err.zone_not_in_list": _t(
        "'{t}' is not in the Store Zone list.",
        "„{t}” nu este în lista zonelor de magazin.",
        "A(z) „{t}” nincs az üzletzónák listájában.",
        "„{t}” nie ma na liście stref sklepu.",
        "„{t}“ steht nicht in der Zonenliste.",
    ),
    "err.end_lt_start": _t(
        "End Zone {end} is smaller than Start Zone {start}.",
        "Zona de final {end} este mai mică decât zona de start {start}.",
        "A(z) {end} zárózóna kisebb, mint a(z) {start} kezdőzóna.",
        "Strefa końcowa {end} jest mniejsza niż strefa początkowa {start}.",
        "Endzone {end} ist kleiner als Startzone {start}.",
    ),
    "zone.err.empty": _t(
        "{what} is empty.", "{what}: câmpul este gol.", "{what}: üres.", "{what}: puste pole.", "{what}: leer."
    ),
    "zone.err.digits": _t(
        "{what} must contain digits only (got '{text}').",
        "{what}: sunt permise doar cifre (primit „{text}”).",
        "{what}: csak számjegyek engedélyezettek („{text}”).",
        "{what}: dozwolone są tylko cyfry („{text}”).",
        "{what}: nur Ziffern erlaubt („{text}“).",
    ),
    "zone.err.len": _t(
        "{what} can have at most 4 digits (got '{text}').",
        "{what}: maximum 4 cifre (primit „{text}”).",
        "{what}: legfeljebb 4 számjegy lehet („{text}”).",
        "{what}: maksymalnie 4 cyfry („{text}”).",
        "{what}: höchstens 4 Ziffern („{text}“).",
    ),
    "zone.err.range": _t(
        "{what} must be between {lo} and {hi}.",
        "{what}: trebuie să fie între {lo} și {hi}.",
        "{what}: {lo} és {hi} között kell lennie.",
        "{what}: musi być między {lo} a {hi}.",
        "{what}: muss zwischen {lo} und {hi} liegen.",
    ),
    "imp.err.header": _t(
        "This file doesn't look like a zone sheet: expected the headers 'from', 'to', 'Division' in A1:C1.",
        "Fișierul nu pare o foaie de zone: se așteaptă antetele „from”, „to”, „Division” în A1:C1.",
        "Ez a fájl nem tűnik zónatáblának: az A1:C1 cellákban a „from”, „to”, „Division” fejlécek kellenek.",
        "Ten plik nie wygląda na arkusz stref: oczekiwano nagłówków „from”, „to”, „Division” w A1:C1.",
        "Diese Datei sieht nicht wie eine Zonentabelle aus: In A1:C1 werden die Überschriften „from“, „to“, „Division“ erwartet.",
    ),
    "imp.err.from_gt_to": _t(
        "'from' is bigger than 'to'.",
        "„from” este mai mare decât „to”.",
        "A „from” nagyobb, mint a „to”.",
        "„from” jest większe niż „to”.",
        "„from“ ist größer als „to“.",
    ),
    "imp.err.row": _t("Row {r}: {msg}", "Rândul {r}: {msg}", "{r}. sor: {msg}", "Wiersz {r}: {msg}", "Zeile {r}: {msg}"),
    # ---------------------------------------------------------------- dialogs
    "dlg.yes": _t("Yes", "Da", "Igen", "Tak", "Ja"),
    "dlg.no": _t("No", "Nu", "Nem", "Nie", "Nein"),
    "dlg.ok": _t("OK", "OK", "OK", "OK", "OK"),
    "dlg.cancel": _t("Cancel", "Anulează", "Mégse", "Anuluj", "Abbrechen"),
    "dlg.overlap.title": _t("Overlapping zones", "Zone suprapuse", "Átfedő zónák", "Nakładające się strefy", "Überlappende Zonen"),
    "dlg.overlap.msg": _t(
        "{start}–{end} overlaps with row {n}:\n\n    {label}\n\nAdd it anyway?",
        "{start}–{end} se suprapune cu rândul {n}:\n\n    {label}\n\nO adaugi oricum?",
        "A(z) {start}–{end} átfedésben van a(z) {n}. sorral:\n\n    {label}\n\nMégis hozzáadod?",
        "{start}–{end} nakłada się na wiersz {n}:\n\n    {label}\n\nDodać mimo to?",
        "{start}–{end} überschneidet sich mit Zeile {n}:\n\n    {label}\n\nTrotzdem hinzufügen?",
    ),
    "dlg.new.title": _t("New store", "Magazin nou", "Új üzlet", "Nowy sklep", "Neuer Markt"),
    "dlg.new.unexported": _t(
        "\n\nWARNING: these rows have not been exported to Excel yet!",
        "\n\nATENȚIE: aceste rânduri nu au fost încă exportate în Excel!",
        "\n\nFIGYELEM: ezeket a sorokat még nem exportáltad Excelbe!",
        "\n\nUWAGA: te wiersze nie zostały jeszcze wyeksportowane do Excela!",
        "\n\nACHTUNG: Diese Zeilen wurden noch nicht nach Excel exportiert!",
    ),
    "dlg.new.msg": _t(
        "Clear all {n} rows and start a new store?\n(You can still undo with {key}.)",
        "Ștergi toate cele {n} rânduri și începi un magazin nou?\n(Poți anula cu {key}.)",
        "Törlöd mind a(z) {n} sort, és új üzlettel kezdesz?\n(Visszavonhatod ezzel: {key}.)",
        "Usunąć wszystkie wiersze ({n}) i zacząć nowy sklep?\n(Możesz to cofnąć: {key}.)",
        "Alle {n} Zeilen löschen und einen neuen Markt beginnen?\n(Rückgängig mit {key} möglich.)",
    ),
    "dlg.export.title": _t("Export", "Export", "Exportálás", "Eksport", "Export"),
    "dlg.export.empty": _t(
        "There are no rows to export yet.",
        "Nu există încă rânduri de exportat.",
        "Még nincs exportálható sor.",
        "Brak wierszy do wyeksportowania.",
        "Es gibt noch keine Zeilen zum Exportieren.",
    ),
    "dlg.export.save_title": _t(
        "Export to Excel", "Exportă în Excel", "Exportálás Excelbe", "Eksportuj do Excela", "Nach Excel exportieren"
    ),
    "dlg.filetype.xlsx": _t("Excel workbook", "Registru Excel", "Excel-munkafüzet", "Skoroszyt programu Excel", "Excel-Arbeitsmappe"),
    "dlg.cantsave.title": _t("Can't save", "Nu se poate salva", "Nem menthető", "Nie można zapisać", "Speichern nicht möglich"),
    "dlg.cantsave.msg": _t(
        "{file} can't be written.\nIs it open in Excel? Close it and try again.",
        "Nu se poate scrie în {file}.\nEste deschis în Excel? Închide-l și încearcă din nou.",
        "A(z) {file} nem írható.\nMeg van nyitva Excelben? Zárd be, és próbáld újra.",
        "Nie można zapisać pliku {file}.\nCzy jest otwarty w Excelu? Zamknij go i spróbuj ponownie.",
        "{file} kann nicht geschrieben werden.\nIst die Datei in Excel geöffnet? Schließen und erneut versuchen.",
    ),
    "dlg.import.title": _t("Import", "Import", "Importálás", "Import", "Import"),
    "dlg.import.open_title": _t(
        "Import a zone sheet", "Importă o foaie cu zone", "Zónatábla importálása", "Importuj arkusz stref", "Zonentabelle importieren"
    ),
    "dlg.import.read_err": _t(
        "Could not read the file:\n{err}",
        "Fișierul nu a putut fi citit:\n{err}",
        "A fájl nem olvasható:\n{err}",
        "Nie można odczytać pliku:\n{err}",
        "Die Datei konnte nicht gelesen werden:\n{err}",
    ),
    "dlg.import.none": _t(
        "No usable rows found in that file.",
        "Nu s-au găsit rânduri utilizabile în fișier.",
        "A fájlban nincs használható sor.",
        "W pliku nie znaleziono użytecznych wierszy.",
        "In der Datei wurden keine verwertbaren Zeilen gefunden.",
    ),
    "dlg.import.replace": _t(
        "This replaces the {old} rows currently in the list with {new} rows from the file.\n(Undo brings them back.)",
        "Aceasta înlocuiește cele {old} rânduri din listă cu {new} rânduri din fișier.\n(Cu Anulare le poți recupera.)",
        "Ez lecseréli a listában lévő {old} sort a fájl {new} sorára.\n(A visszavonás visszahozza őket.)",
        "Zastąpi to wiersze z listy ({old}) wierszami z pliku ({new}).\n(Cofnięcie je przywróci.)",
        "Dadurch werden die {old} Zeilen der Liste durch {new} Zeilen aus der Datei ersetzt.\n(Mit „Rückgängig“ kommen sie zurück.)",
    ),
    "dlg.import.skipped": _t(
        "Skipped rows:\n\n{rows}", "Rânduri ignorate:\n\n{rows}", "Kihagyott sorok:\n\n{rows}", "Pominięte wiersze:\n\n{rows}", "Übersprungene Zeilen:\n\n{rows}"
    ),
    "zl.title": _t(
        "Store Zone list", "Lista zonelor de magazin", "Üzletzóna-lista", "Lista stref sklepu", "Liste der Marktzonen"
    ),
    "zl.help": _t(
        "One Store Zone per line. Existing rows are not changed.",
        "O zonă de magazin pe linie. Rândurile existente nu se modifică.",
        "Soronként egy üzletzóna. A meglévő sorok nem változnak.",
        "Jedna strefa sklepu w wierszu. Istniejące wiersze nie zmieniają się.",
        "Eine Marktzone pro Zeile. Vorhandene Zeilen bleiben unverändert.",
    ),
    "zl.reset": _t(
        "Reset to defaults", "Resetează la valorile implicite", "Alapértelmezések", "Przywróć domyślne", "Standard wiederherstellen"
    ),
    "zl.empty": _t(
        "The list can't be empty.", "Lista nu poate fi goală.", "A lista nem lehet üres.", "Lista nie może być pusta.", "Die Liste darf nicht leer sein."
    ),
    # ------------------------------------------------------------ help popup
    "help.title": _t("Quick guide", "Ghid rapid", "Gyorsútmutató", "Krótki przewodnik", "Kurzanleitung"),
    "help.step1": _t(
        "Type the first letters of the Store Zone, press Enter.",
        "Scrie primele litere ale zonei de magazin, apoi apasă Enter.",
        "Írd be az üzletzóna első betűit, majd nyomj Entert.",
        "Wpisz pierwsze litery strefy sklepu i naciśnij Enter.",
        "Erste Buchstaben der Marktzone eingeben, Enter drücken.",
    ),
    "help.step2": _t(
        "Type the End Zone, press Enter – the row is added.",
        "Scrie zona de final și apasă Enter – rândul este adăugat.",
        "Írd be a zárózónát, nyomj Entert – a sor hozzáadódik.",
        "Wpisz strefę końcową i naciśnij Enter – wiersz zostanie dodany.",
        "Endzone eingeben, Enter drücken – die Zeile wird hinzugefügt.",
    ),
    "help.step3": _t(
        "The next Start Zone is filled in for you (previous End + 1). Type over it if the numbering skips.",
        "Următoarea zonă de start este completată automat (finalul anterior + 1). Suprascrie-o dacă numerotarea sare.",
        "A következő kezdőzóna automatikusan kitöltődik (előző vég + 1). Ha a számozás kihagy, írd felül.",
        "Następna strefa początkowa wypełnia się automatycznie (poprzedni koniec + 1). Nadpisz ją, jeśli numeracja ma przerwę.",
        "Die nächste Startzone wird automatisch ausgefüllt (vorheriges Ende + 1). Bei Sprüngen in der Nummerierung einfach überschreiben.",
    ),
    "help.hotkeys": _t("Hotkeys", "Scurtături de tastatură", "Gyorsbillentyűk", "Skróty klawiszowe", "Tastenkürzel"),
    "hk.enter": _t(
        "Accept suggestion · next field · add row",
        "Acceptă sugestia · câmpul următor · adaugă rândul",
        "Javaslat elfogadása · következő mező · sor hozzáadása",
        "Zatwierdź podpowiedź · następne pole · dodaj wiersz",
        "Vorschlag übernehmen · nächstes Feld · Zeile hinzufügen",
    ),
    "hk.updown": _t(
        "Move through suggestions",
        "Navighează prin sugestii",
        "Lépkedés a javaslatok között",
        "Przechodzenie po podpowiedziach",
        "In den Vorschlägen navigieren",
    ),
    "hk.tab": _t(
        "Next / previous field", "Câmpul următor / anterior", "Következő / előző mező", "Następne / poprzednie pole", "Nächstes / vorheriges Feld"
    ),
    "hk.esc": _t(
        "Close suggestions · cancel editing",
        "Închide sugestiile · anulează editarea",
        "Javaslatok bezárása · szerkesztés elvetése",
        "Zamknij podpowiedzi · anuluj edycję",
        "Vorschläge schließen · Bearbeitung abbrechen",
    ),
    "hk.f2": _t(
        "Edit selected row (or double-click)",
        "Editează rândul selectat (sau dublu clic)",
        "A kijelölt sor szerkesztése (vagy dupla kattintás)",
        "Edytuj zaznaczony wiersz (lub dwukrotne kliknięcie)",
        "Markierte Zeile bearbeiten (oder Doppelklick)",
    ),
    "hk.del": _t(
        "Delete selected rows",
        "Șterge rândurile selectate",
        "A kijelölt sorok törlése",
        "Usuń zaznaczone wiersze",
        "Markierte Zeilen löschen",
    ),
    "hk.undo": _t("Undo", "Anulare", "Visszavonás", "Cofnij", "Rückgängig"),
    "hk.export": _t(
        "Export to Excel", "Exportă în Excel", "Exportálás Excelbe", "Eksportuj do Excela", "Nach Excel exportieren"
    ),
    "hk.f1": _t(
        "Show / hide this guide",
        "Arată / ascunde acest ghid",
        "Az útmutató megjelenítése / elrejtése",
        "Pokaż / ukryj ten przewodnik",
        "Diese Anleitung ein-/ausblenden",
    ),
    "help.note": _t(
        "The store name is only used for the file name. Your work is saved automatically.",
        "Numele magazinului este folosit doar pentru numele fișierului. Lucrul tău se salvează automat.",
        "Az üzlet neve csak a fájlnévhez kell. A munkád automatikusan mentődik.",
        "Nazwa sklepu jest używana tylko w nazwie pliku. Twoja praca zapisuje się automatycznie.",
        "Der Marktname wird nur für den Dateinamen verwendet. Die Arbeit wird automatisch gespeichert.",
    ),
}


# =============================================================================
def set_language(code: str) -> str:
    """Select the UI language (unknown codes fall back to English). Returns the code used."""
    global _current
    _current = code if code in LANGUAGES else DEFAULT_LANGUAGE
    return _current


def get_language() -> str:
    return _current


def tr(key: str, /, **params) -> str:
    """Translate `key` into the current language and fill in {placeholders}.

    A key that isn't in the table is returned as-is, so plain text can pass through.
    (`key` is positional-only so a placeholder may itself be called {key}.)
    """
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(_current) or entry[DEFAULT_LANGUAGE]
    return text.format(**params) if params else text


_WINDOWS_PRIMARY_LANGUAGE = {0x07: "de", 0x18: "ro", 0x0E: "hu", 0x15: "pl"}


def _language_from_windows_ui(langid: int) -> str:
    """Windows language id (e.g. 0x0418 = Romanian) -> our language code."""
    return _WINDOWS_PRIMARY_LANGUAGE.get(langid & 0x3FF, DEFAULT_LANGUAGE)


def _language_from_environment() -> str:
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        code = os.environ.get(var, "").split(".")[0].split("_")[0].lower()
        if code in LANGUAGES:
            return code
    return DEFAULT_LANGUAGE


def detect_language() -> str:
    """Language for a first start: the Windows display language if we support it, else English."""
    if sys.platform == "win32":
        try:
            import ctypes

            return _language_from_windows_ui(ctypes.windll.kernel32.GetUserDefaultUILanguage())
        except Exception:
            return DEFAULT_LANGUAGE
    return _language_from_environment()
