@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title CloudKrafts QR Manager - Local Test

echo ==================================================
echo       CLOUDKRAFTS QR MANAGER - LOCAL TEST
echo ==================================================
echo.

REM Detect Python launcher or python.exe
where py >nul 2>&1
if not errorlevel 1 (
    set "PY=py -3"
) else (
    where python >nul 2>&1
    if not errorlevel 1 (
        set "PY=python"
    ) else (
        echo ERROR: Python 3 was not found.
        echo Install Python from https://www.python.org/downloads/
        echo IMPORTANT: During installation, tick "Add Python to PATH".
        echo Then close this window and double-click this file again.
        echo.
        pause
        exit /b 1
    )
)

echo Checking Python installation...
%PY% --version
if errorlevel 1 goto python_error

echo.
echo Checking QR-code library...
%PY% -c "import qrcode, PIL" >nul 2>&1
if errorlevel 1 (
    echo QR library is missing. Installing it now...
    %PY% -m pip install --user "qrcode[pil]"
    if errorlevel 1 goto library_error
)

echo.
echo Starting local server...
echo Keep this black window OPEN while using the software.
echo To stop the server, press CTRL+C.
echo.
start "" /min cmd /c "timeout /t 3 /nobreak ^>nul ^& start http://127.0.0.1:8765"
%PY% server.py

echo.
echo The local server has stopped.
echo If an error appeared above, take a screenshot and send it to ChatGPT.
pause
exit /b 0

:python_error
echo ERROR: Python was detected but could not run.
echo Reinstall Python 3 and enable Add Python to PATH.
echo.
pause
exit /b 1

:library_error
echo ERROR: Could not install the QR library.
echo Check your internet connection, then try again.
echo You can also run: %PY% -m pip install --user "qrcode[pil]"
echo.
pause
exit /b 1
