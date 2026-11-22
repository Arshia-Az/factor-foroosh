@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set PY=py -3) else (set PY=python)
%PY% --version
if errorlevel 1 goto nopython
%PY% -m pip install -r requirements.txt
if errorlevel 1 goto fail
%PY% app.py
if errorlevel 1 pause
exit /b 0
:nopython
echo Python was not found. Install Python 3.10 or newer from python.org and tick "Add python.exe to PATH".
pause
exit /b 1
:fail
echo Installing the requirements failed. Check your internet connection and try again.
pause
exit /b 1
