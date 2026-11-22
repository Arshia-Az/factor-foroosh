@echo off
setlocal
cd /d "%~dp0"
echo ==== Building FactorForoosh.exe ====
where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
%PY% --version
if errorlevel 1 goto nopython
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto fail
%PY% -m PyInstaller --noconfirm --clean --windowed --name FactorForoosh --icon assets\icon.ico --add-data "fonts;fonts" app.py
if errorlevel 1 goto fail
echo.
echo ==== DONE ====
echo Your program is here: dist\FactorForoosh\FactorForoosh.exe
echo Right-click that file and choose Send to - Desktop (create shortcut).
pause
exit /b 0
:nopython
echo.
echo Python was not found. Install Python 3.10 or newer from python.org
echo and tick "Add python.exe to PATH" during setup. Then run this file again.
pause
exit /b 1
:fail
echo.
echo Build failed. Please read the messages above.
pause
exit /b 1
