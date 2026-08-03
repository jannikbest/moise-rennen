# Production launcher (Windows): stats + Kino — real ESP, no mock
# Usage:  powershell -ExecutionPolicy Bypass -File .\run.ps1
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
. (Join-Path $Root 'moise-common.ps1')

Ensure-MoiseStatsVenv $Root

# Never expose the mock control button in production
$env:MOCK_CONTROL_URL = ''

$procs = @()
try {
    $procs += Start-MoiseProcess -FilePath $MoisePy -ArgumentList @(
        (Join-Path $Root 'moise-stats\main.py')
    )
    $procs += Start-MoiseProcess -FilePath $MoisePy -ArgumentList @(
        '-m', 'http.server', '8080'
    ) -WorkingDirectory (Join-Path $Root 'moise-kino')

    Write-Host 'Stats: ws://0.0.0.0:8770/'
    Write-Host 'ESP:   ESP_WS_URL from moise-stats/.env (IP or host, e.g. 192.168.4.1)'
    Write-Host 'Kino:  http://127.0.0.1:8080'
    Write-Host 'Ctrl+C stops all.'

    Wait-Process -Id ($procs | ForEach-Object { $_.Id })
} finally {
    Stop-MoiseProcesses $procs
}
