@echo off
REM One-click Windows build for The Isle Companion.
REM Requires Python 3.11+ (python.org, "Add Python to PATH"). Run from this folder.
setlocal
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py) || (set PY=python)
if not exist .venv\Scripts\python.exe (
  %PY% -m venv .venv || goto :fail
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip || goto :fail
python -m pip install -r requirements-dev.txt || goto :fail
set QT_QPA_PLATFORM=offscreen
python -m pytest -q -p no:cacheprovider || goto :fail
set QT_QPA_PLATFORM=
python tools\build_exe.py || goto :fail
echo.
echo Done. Your app is in dist\TheIsleCompanion\TheIsleCompanion.exe
echo Share dist\TheIsleCompanion-*-windows.zip
pause
exit /b 0
:fail
echo.
echo BUILD FAILED - see messages above.
pause
exit /b 1
