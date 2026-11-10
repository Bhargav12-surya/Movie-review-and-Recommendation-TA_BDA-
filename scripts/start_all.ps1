[CmdletBinding()]
param([string]$PythonPath, [string]$NodePath, [switch]$Production, [switch]$Run)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_local_services.ps1')
$python = Get-MoviePython $PythonPath
$node = Get-MovieNode $NodePath
$next = Get-MovieNext
Assert-MovieBackendPackages $python
if (-not $Run) { Write-Output 'Preflight only. Use -Run to start API, one worker and frontend after PostgreSQL setup and artifact approval. No services started.'; exit 0 }
Assert-MoviePortFree 8000
Assert-MoviePortFree 3000
Assert-MovieTcp
$workspace = Get-MovieWorkspace
if ($Production -and -not (Test-Path -LiteralPath (Join-Path $workspace 'frontend\.next\BUILD_ID') -PathType Leaf)) { throw 'Build the production frontend manually first.' }
Set-MovieOfflineProcess
$sessionRoot = Join-Path $workspace ('artifacts\services\' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8))
[IO.Directory]::CreateDirectory($sessionRoot) | Out-Null
$records = [Collections.Generic.List[object]]::new()
$recordFile = Join-Path $sessionRoot 'processes.json'
try {
    $records.Add((Start-MovieOwnedProcess -Executable $python -ArgumentValues @('-B','-m','uvicorn','backend.app.main:create_app','--factory','--host','127.0.0.1','--port','8000','--workers','1','--no-access-log','--no-proxy-headers') -WorkingDirectory $workspace -LogDirectory $sessionRoot -Name 'backend'))
    $records | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $recordFile -Encoding UTF8
    $ready = $false
    for ($attempt=0; $attempt -lt 12; $attempt++) {
        try { $response=Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/ready' -TimeoutSec 2; if ($response.ready) { $ready=$true; break } } catch { }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) { throw 'Backend schema readiness failed. Inspect owned logs and database setup; no seed or migration was run.' }
    $records.Add((Start-MovieOwnedProcess -Executable $python -ArgumentValues @('-B','-m','backend.app.workers.main') -WorkingDirectory $workspace -LogDirectory $sessionRoot -Name 'worker'))
    $records | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $recordFile -Encoding UTF8
    $mode=if ($Production) { 'start' } else { 'dev' }
    $records.Add((Start-MovieOwnedProcess -Executable $node -ArgumentValues @($next,$mode,'--hostname','127.0.0.1','--port','3000') -WorkingDirectory (Join-Path $workspace 'frontend') -LogDirectory $sessionRoot -Name 'frontend'))
    $records | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $recordFile -Encoding UTF8
    Write-Output 'Processes launched; run the health checks. Launch success does not prove model or browser readiness.'
    Write-Output "Owned process record: $recordFile"
    Write-Output 'Frontend http://localhost:3000 | API http://localhost:8000/docs'
} catch {
    foreach ($owned in @($records.ToArray()) | Sort-Object name -Descending) { Stop-MovieOwnedProcess $owned }
    throw
}
