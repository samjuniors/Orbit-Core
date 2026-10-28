@echo off
setlocal
cd /d "%~dp0"
rem Prefer an installed tested Python with Tkinter; do not silently select Python 3.14/3.15.
for %%V in (3.12 3.13 3.11 3.10) do (
    py -%%V -c "import tkinter" >nul 2>&1
    if not errorlevel 1 (
        py -%%V "%~dp0orbit_setup.py" --gui
        if errorlevel 1 pause
        exit /b
    )
)
echo Orbit Setup requires Python 3.10-3.13 with Tkinter.
echo Recommended: install Python 3.12 and double-click Orbit Setup.cmd again.
echo Available Python installations:
py -0p
pause
exit /b 1
