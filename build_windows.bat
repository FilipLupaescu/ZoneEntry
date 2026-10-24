@echo off
REM Builds dist\ZoneEntry.exe on a Windows PC (or a Windows VM on your Mac).
REM Needs Python 3.10+ from python.org (tick "Add python.exe to PATH").

py -3 -m venv .venv || goto :error
call .venv\Scripts\activate.bat || goto :error
python -m pip install -r requirements.txt pyinstaller pytest || goto :error
python -m pytest -q || goto :error
pyinstaller --onefile --windowed --name ZoneEntry app.py || goto :error

echo.
echo Done: dist\ZoneEntry.exe
exit /b 0

:error
echo.
echo Build failed - see the messages above.
exit /b 1
