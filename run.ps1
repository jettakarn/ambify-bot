# twoshiftly (2shiftly) launcher — no PATH required
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Error "找不到 Python。請安裝 Python 3.11+：https://www.python.org/downloads/"
    exit 1
}

$installed = & py -m pip show twoshiftly 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "正在安裝 twoshiftly..."
    & py -m pip install -e . -q
    if ($LASTEXITCODE -ne 0) {
        Write-Error "安裝失敗。請手動執行：py -m pip install -e ."
        exit 1
    }
}

& py -m twoshiftly.cli @args
exit $LASTEXITCODE
