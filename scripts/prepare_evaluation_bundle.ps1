<# Curated reviewed allowlist only; default prints the plan and copies nothing. #>
[CmdletBinding()]
param([string]$ConfigPath='configs/validation/bundle.example.json',[string]$PythonPath,[switch]$Execute)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '_local_services.ps1')
$bundlePython=Get-MoviePython $PythonPath
$bundleArgs=@('-B','-m','validation.cli','bundle','--config',$ConfigPath)
if ($Execute) {$bundleArgs+='--execute'}
Push-Location -LiteralPath (Get-MovieWorkspace)
try {& $bundlePython @bundleArgs;$bundleCode=$LASTEXITCODE} finally {Pop-Location}
exit $bundleCode
