@echo off
REM Builds dist\ZoneEntry\ZoneEntry.exe on a Windows PC (and the installer if Inno Setup 6 is installed).
REM Needs Python 3.10+ from python.org (tick "Add python.exe to PATH").
setlocal

py -3 -m venv .venv || goto :error
call .venv\Scripts\activate.bat || goto :error
python -m pip install -r requirements.txt pyinstaller pytest || goto :error
python -m pytest -q || goto :error

pyinstaller --noconfirm --windowed --name ZoneEntry --icon assets\zoneentry.ico --add-data "assets\zoneentry.ico;assets" --exclude-module numpy --exclude-module PIL --exclude-module pandas --exclude-module matplotlib --exclude-module scipy --exclude-module lxml app.py || goto :error

echo Checking the built app...
start /wait "" dist\ZoneEntry\ZoneEntry.exe --selftest
if errorlevel 1 (
  echo Self-test failed. Details: %TEMP%\zoneentry-selftest.log
  goto :error
)

set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" goto :done
for /f %%v in ('python -c "from version import __version__; print(__version__)"') do set VER=%%v
"%ISCC%" /DAppVersion=%VER% installer\ZoneEntry.iss || goto :error

:done
echo.
echo Done:  dist\ZoneEntry\ZoneEntry.exe   (installer: dist\ZoneEntry-Setup.exe if Inno Setup was found)
exit /b 0

:error
echo.
echo Build failed - see the messages above.
exit /b 1
