@echo off
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
    echo Python not found. Install Python 3.11+: https://www.python.org/downloads/
    pause
    exit /b 1
)

py -c "import twoshiftly.web" >nul 2>&1
if errorlevel 1 goto install

for /f "tokens=2 delims=: " %%A in ('py -m pip show twoshiftly 2^>nul ^| findstr /C:"Editable project location:"') do set EDITABLE=%%A
if defined EDITABLE (
    if /I not "%EDITABLE%"=="%~dp0." if /I not "%EDITABLE%"=="%~dp0" goto install
)

goto run

:install
echo Installing twoshiftly...
py -m pip install -e . -q
if errorlevel 1 (
    echo Install failed. Run manually: py -m pip install -e .
    pause
    exit /b 1
)

:run
echo Starting 2shiftly web UI...
py -m twoshiftly.web
exit /b %ERRORLEVEL%
