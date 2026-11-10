[CmdletBinding()]
param([string]$NodePath, [switch]$Production, [switch]$Run)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_local_services.ps1')
$node = Get-MovieNode $NodePath
$next = Get-MovieNext
& $node --version
if ($LASTEXITCODE -ne 0) { throw 'Node version verification failed.' }
if (-not $Run) { Write-Output 'Preflight only. Use -Run to start the manually installed frontend. No package resolution or build was run.'; exit 0 }
Assert-MoviePortFree 3000
if ($Production -and -not (Test-Path -LiteralPath (Join-Path (Get-MovieWorkspace) 'frontend\.next\BUILD_ID') -PathType Leaf)) { throw 'A manually produced production build is required. This script never builds or installs.' }
Set-MovieOfflineProcess
$mode = if ($Production) { 'start' } else { 'dev' }
Push-Location -LiteralPath (Join-Path (Get-MovieWorkspace) 'frontend')
try { & $node $next $mode --hostname 127.0.0.1 --port 3000; exit $LASTEXITCODE }
finally { Pop-Location }
