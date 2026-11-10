<# Read-only checks and reviewed operator evidence; never starts/stops a service. #>
[CmdletBinding()]
param([string]$ConfigPath='configs/validation/rehearsal.example.json',[string]$PythonPath,[switch]$Execute)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '_local_services.ps1')
$rehearsalPython=Get-MoviePython $PythonPath
$rehearsalArgs=@('-B','-m','validation.cli','rehearsal','--config',$ConfigPath)
if ($Execute) {$rehearsalArgs+='--execute';Set-MovieOfflineProcess}
Push-Location -LiteralPath (Get-MovieWorkspace)
try {& $rehearsalPython @rehearsalArgs;$rehearsalCode=$LASTEXITCODE} finally {Pop-Location}
exit $rehearsalCode
