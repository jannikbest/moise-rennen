# Dev launcher (Windows): mock ESP + stats + Kino static server
# Usage:  powershell -ExecutionPolicy Bypass -File .\dev.ps1
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
. (Join-Path $Root 'moise-common.ps1')

Ensure-MoiseStatsVenv $Root

if (-not $env:ESP_WS_URL) { $env:ESP_WS_URL = 'ws://127.0.0.1:81/' }
if (-not $env:MOCK_CONTROL_URL) { $env:MOCK_CONTROL_URL = 'http://127.0.0.1:82/go' }

$procs = @()
try {
    $procs += Start-MoiseProcess -FilePath $MoisePy -ArgumentList @(
        (Join-Path $Root 'moise-kino\mock-esp.py')
    )
    $procs += Start-MoiseProcess -FilePath $MoisePy -ArgumentList @(
        (Join-Path $Root 'moise-stats\main.py')
    )
    $procs += Start-MoiseProcess -FilePath $MoisePy -ArgumentList @(
        '-m', 'http.server', '8080'
    ) -WorkingDirectory (Join-Path $Root 'moise-kino')

    Write-Host 'Mock ESP: ws://127.0.0.1:81/   (control http://127.0.0.1:82/go)'
    Write-Host 'Stats:    ws://127.0.0.1:8770/'
    Write-Host 'Kino:     http://127.0.0.1:8080'
    Write-Host 'Ctrl+C stops all.'

    Wait-Process -Id ($procs | ForEach-Object { $_.Id })
} finally {
    Stop-MoiseProcesses $procs
}
