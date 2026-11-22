@echo off
cd /d "%~dp0"
python gui.py
if %ERRORLEVEL% NEQ 0 (
    echo Error running application.
    pause
)
