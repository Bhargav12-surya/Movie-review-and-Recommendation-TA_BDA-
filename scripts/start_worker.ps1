[CmdletBinding()]
param([string]$PythonPath, [switch]$Run)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_local_services.ps1')
$python = Get-MoviePython $PythonPath
Assert-MovieBackendPackages $python
if (-not $Run) { Write-Output 'Preflight only. Use -Run after approving inference execution. No worker or model was started.'; exit 0 }
Assert-MovieTcp
Set-MovieOfflineProcess
Push-Location -LiteralPath (Get-MovieWorkspace)
try { & $python -B -m backend.app.workers.main; exit $LASTEXITCODE }
finally { Pop-Location }
