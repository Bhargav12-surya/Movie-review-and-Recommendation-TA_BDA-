[CmdletBinding()]
param([string]$PythonPath, [switch]$Run)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_local_services.ps1')
$python = Get-MoviePython $PythonPath
Assert-MovieBackendPackages $python
if (-not $Run) { Write-Output 'Preflight only. Use -Run after approving local service execution. No service was started.'; exit 0 }
Assert-MoviePortFree 8000
Set-MovieOfflineProcess
Push-Location -LiteralPath (Get-MovieWorkspace)
try { & $python -B -m uvicorn backend.app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1 --no-access-log --no-proxy-headers; exit $LASTEXITCODE }
finally { Pop-Location }
