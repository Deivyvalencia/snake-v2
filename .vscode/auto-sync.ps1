$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$git = 'C:\Program Files\Git\cmd\git.exe'

if (-not (Test-Path $git)) {
    $git = (Get-Command git -ErrorAction Stop).Source
}

Set-Location $projectRoot
$lastStatus = ''

Write-Host 'Sincronizacion automatica con GitHub activa.'
while ($true) {
    try {
        $status = (& $git status --porcelain) -join "`n"
        if ($status -and $status -ne $lastStatus) {
            & $git add --all
            $message = "Actualizacion automatica $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
            & $git commit -m $message
            & $git push origin main
            $lastStatus = (& $git status --porcelain) -join "`n"
            Write-Host "Cambios enviados a GitHub: $message"
        } elseif (-not $status) {
            $lastStatus = ''
        }
    } catch {
        Write-Warning "No se pudo sincronizar: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds 5
}
