$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot '.venv-1\Scripts\python.exe'

if (-not (Test-Path $python)) {
    $python = 'python'
}

Set-Location $projectRoot
& $python -m pip install -r requirements.txt pyinstaller
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name Snakerson snake.py

Write-Host "Aplicacion creada en: $projectRoot\dist\Snakerson.exe"
