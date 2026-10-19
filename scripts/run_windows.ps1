$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Cần cài Python 3.12 và Python Launcher trước." }
}
& .venv\Scripts\python.exe -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw "Không cài được thư viện." }
& .venv\Scripts\python.exe -m vehiclelog
