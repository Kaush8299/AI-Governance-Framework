@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 app.py
) else (
  python app.py
)
if errorlevel 1 (
  echo.
  echo Python 3.10 or later and local loopback access are required.
  echo See README.md for approved setup and troubleshooting.
)
pause
