$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Cần cài Python 3.12 và Python Launcher trước." }
}
& .venv\Scripts\python.exe -m pip install -e ".[build]"
if ($LASTEXITCODE -ne 0) { throw "Không cài được thư viện đóng gói." }
& .venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onedir --name VehicleLogStudio --collect-all pyqtgraph --collect-all asammdf launch.py
if ($LASTEXITCODE -ne 0) { throw "Đóng gói thất bại." }
Write-Host "Kết quả: dist\VehicleLogStudio\VehicleLogStudio.exe. Cần sao chép cả thư mục."
