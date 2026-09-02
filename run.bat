@echo off
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
    echo 找不到 Python。請安裝 Python 3.11+：https://www.python.org/downloads/
    exit /b 1
)

py -m pip show twoshiftly >nul 2>&1
if errorlevel 1 (
    echo 正在安裝 twoshiftly...
    py -m pip install -e . -q
    if errorlevel 1 (
        echo 安裝失敗。請手動執行：py -m pip install -e .
        exit /b 1
    )
)

py -m twoshiftly.cli %*
exit /b %ERRORLEVEL%
