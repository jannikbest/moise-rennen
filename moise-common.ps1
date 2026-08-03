# Shared helpers for Moise PowerShell launchers (Windows).

function Get-MoiseSystemPython {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) { return $python.Source }

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return $py.Source }

    throw 'Python 3 is required (install from python.org or the Microsoft Store).'
}

function Resolve-MoiseVenvBins {
    param([Parameter(Mandatory)][string]$Venv)

    $py = Join-Path $Venv 'Scripts\python.exe'
    if (-not (Test-Path $py)) {
        $py = Join-Path $Venv 'Scripts\python'
    }
    if (-not (Test-Path $py)) {
        throw "Broken venv at $Venv — remove it and retry"
    }

    $script:MoisePy = (Resolve-Path $py).Path
    $pip = Join-Path (Split-Path $script:MoisePy -Parent) 'pip.exe'
    if (-not (Test-Path $pip)) {
        $pip = Join-Path (Split-Path $script:MoisePy -Parent) 'pip'
    }
    $script:MoisePip = $pip
}

function Ensure-MoiseStatsVenv {
    param([Parameter(Mandatory)][string]$Root)

    $venv = Join-Path $Root 'moise-stats\.venv'
    $req = Join-Path $Root 'moise-stats\requirements.txt'
    $envFile = Join-Path $Root 'moise-stats\.env'
    $envExample = Join-Path $Root 'moise-stats\.env.example'
    $sysPy = Get-MoiseSystemPython

    if (-not (Test-Path $venv)) {
        Write-Host 'Creating moise-stats venv…'
        if ((Split-Path $sysPy -Leaf) -eq 'py.exe') {
            & $sysPy -3 -m venv $venv
        } else {
            & $sysPy -m venv $venv
        }
        if ($LASTEXITCODE -ne 0) { throw 'Failed to create venv' }
        Resolve-MoiseVenvBins $venv
        & $script:MoisePy -m pip install -r $req
        if ($LASTEXITCODE -ne 0) { throw 'Failed to install requirements' }
    } else {
        Resolve-MoiseVenvBins $venv
    }

    if (-not (Test-Path $envFile)) {
        Copy-Item $envExample $envFile
        Write-Host 'Created moise-stats/.env from example'
    }
}

function Format-MoiseArg {
    param([string]$Value)
    if ($Value -match '[\s"]') {
        return '"' + ($Value -replace '"', '\"') + '"'
    }
    return $Value
}

function Start-MoiseProcess {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$ArgumentList,
        [string]$WorkingDirectory = $null
    )
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    $psi.Arguments = ($ArgumentList | ForEach-Object { Format-MoiseArg $_ }) -join ' '
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $false
    if ($WorkingDirectory) { $psi.WorkingDirectory = $WorkingDirectory }
    return [System.Diagnostics.Process]::Start($psi)
}

function Stop-MoiseProcesses {
    param([System.Diagnostics.Process[]]$Processes)
    foreach ($p in $Processes) {
        if ($null -eq $p) { continue }
        try {
            if (-not $p.HasExited) {
                Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
            }
        } catch {}
    }
}
