# Shared helpers. Dot-sourcing defines functions only; no service or installer starts.
Set-StrictMode -Version Latest

function Get-MovieWorkspace {
    return [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
}

function Get-MoviePython {
    param([string]$PythonPath)
    if (-not $PythonPath) { $PythonPath = Join-Path (Get-MovieWorkspace) '.venv\Scripts\python.exe' }
    $resolved = [IO.Path]::GetFullPath($PythonPath)
    if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) { throw 'Selected Python does not exist. Install prerequisites manually; no installer was run.' }
    return $resolved
}

function Get-MovieNode {
    param([string]$NodePath)
    if (-not $NodePath) {
        $command = Get-Command node.exe -ErrorAction SilentlyContinue
        if ($command) { $NodePath = $command.Source }
    }
    if (-not $NodePath) { throw 'Node.js was not found. Supply -NodePath to the manually installed Node 24 executable.' }
    $resolved = [IO.Path]::GetFullPath($NodePath)
    if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) { throw 'Selected Node executable does not exist.' }
    return $resolved
}

function Assert-MoviePortFree {
    param([int]$Port)
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
    if ($listeners.Count -gt 0) { throw "Port $Port is occupied. Inspect its owner manually; this script does not terminate other processes." }
}

function Assert-MovieTcp {
    param([int]$Port = 5432)
    $client = New-Object Net.Sockets.TcpClient
    try {
        $attempt = $client.ConnectAsync('127.0.0.1', $Port)
        if (-not $attempt.Wait(2000) -or -not $client.Connected) { throw 'Local PostgreSQL is unreachable. Start the manually installed service and validate its schema first.' }
    } finally { $client.Dispose() }
}

function Set-MovieOfflineProcess {
    # Process-only variables, inherited by owned children; no global PATH/Java/CUDA edits.
    $env:HF_HUB_OFFLINE = '1'
    $env:TRANSFORMERS_OFFLINE = '1'
    $env:HF_DATASETS_OFFLINE = '1'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:NEXT_TELEMETRY_DISABLED = '1'
}

function Assert-MovieBackendPackages {
    param([string]$PythonPath)
    # Distribution metadata only; no project imports, database calls or model loads.
    $probe = @'
import importlib.metadata as metadata
import sys
packages = ['fastapi', 'uvicorn', 'SQLAlchemy', 'psycopg', 'pgvector', 'alembic', 'pydantic', 'pydantic-settings', 'pwdlib', 'python-multipart']
missing = []
for package in packages:
    try:
        print(package + ' ' + metadata.version(package))
    except metadata.PackageNotFoundError:
        missing.append(package)
print('Missing: ' + (', '.join(missing) if missing else 'none'))
sys.exit(2 if missing else 0)
'@
    & $PythonPath -I -B -c $probe
    if ($LASTEXITCODE -ne 0) { throw 'Backend prerequisites are missing. Follow PREREQUISITES.md; nothing was installed.' }
}

function Get-MovieNext {
    $entry = Join-Path (Get-MovieWorkspace) 'frontend\node_modules\next\dist\bin\next'
    if (-not (Test-Path -LiteralPath $entry -PathType Leaf)) { throw 'Local Next.js dependencies are missing. Install the approved lockfile manually; npx/npm downloads are never invoked by launch scripts.' }
    return $entry
}

function Quote-MovieArgument {
    param([string]$Value)
    if ($Value.Contains('"') -or $Value.Contains("`r") -or $Value.Contains("`n")) { throw 'Unsupported quote or newline in process argument.' }
    return '"' + $Value + '"'
}

function Start-MovieOwnedProcess {
    param([string]$Executable, [string[]]$ArgumentValues, [string]$WorkingDirectory, [string]$LogDirectory, [string]$Name)
    $arguments = ($ArgumentValues | ForEach-Object { Quote-MovieArgument $_ }) -join ' '
    $child = Start-Process -FilePath $Executable -ArgumentList $arguments -WorkingDirectory $WorkingDirectory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $LogDirectory "$Name.stdout.log") -RedirectStandardError (Join-Path $LogDirectory "$Name.stderr.log")
    return [pscustomobject]@{ name=$Name; process_id=$child.Id; started_utc=$child.StartTime.ToUniversalTime().ToString('o'); executable=[IO.Path]::GetFullPath($Executable) }
}

function Stop-MovieOwnedProcess {
    param($Record)
    $process = Get-Process -Id ([int]$Record.process_id) -ErrorAction SilentlyContinue
    if (-not $process) { return }
    $time = [DateTime]::Parse($Record.started_utc).ToUniversalTime()
    if ([Math]::Abs(($process.StartTime.ToUniversalTime() - $time).TotalSeconds) -gt 1 -or -not [string]::Equals($process.Path, $Record.executable, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Process identity changed for $($Record.name). Refusing to stop an unverified process."
    }
    # Next dev may fork a Node server. Follow the verified parent's current tree,
    # accepting only the same executable created after its parent; no broad taskkill.
    $children = @(Get-CimInstance -ClassName Win32_Process -Filter ("ParentProcessId=" + [int]$process.Id) -Property ProcessId,ExecutablePath,CreationDate -ErrorAction Stop)
    foreach ($child in $children) {
        if (-not $child.ExecutablePath -or -not [string]::Equals($child.ExecutablePath, $Record.executable, [StringComparison]::OrdinalIgnoreCase) -or $child.CreationDate.ToUniversalTime() -lt $time) {
            throw 'An unexpected descendant was found. Inspect it manually; shutdown did not terminate an unverified process.'
        }
        $childRecord = [pscustomobject]@{ name=($Record.name + '-child'); process_id=$child.ProcessId; started_utc=$child.CreationDate.ToUniversalTime().ToString('o'); executable=$child.ExecutablePath }
        Stop-MovieOwnedProcess $childRecord
    }
    # Recheck the original process after walking children to reduce PID-reuse risk.
    $again = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
    if (-not $again) { return }
    if ([Math]::Abs(($again.StartTime.ToUniversalTime() - $time).TotalSeconds) -gt 1 -or -not [string]::Equals($again.Path, $Record.executable, [StringComparison]::OrdinalIgnoreCase)) { throw 'Process identity changed during shutdown.' }
    Stop-Process -Id $process.Id -ErrorAction Stop
}
