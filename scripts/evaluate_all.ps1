<# Plan by default. Explicit -Execute runs selected already-installed checks only. #>
[CmdletBinding()]
param(
    [string]$ConfigPath='configs/validation/suite.json',
    [ValidateSet('unit','postgres','browser','benchmark','parity','grounding','evidence')][string[]]$Groups=@('unit'),
    [string]$PythonPath,[switch]$Execute,[switch]$AllowBrowser
)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '_local_services.ps1')
$evaluationPython=Get-MoviePython $PythonPath
$evaluationArgs=@('-B','-m','validation.runner','--config',$ConfigPath,'--groups')+$Groups
if ($Execute) { $evaluationArgs+='--execute';Set-MovieOfflineProcess }
if ($AllowBrowser) {$evaluationArgs+='--allow-browser'}
Push-Location -LiteralPath (Get-MovieWorkspace)
try {& $evaluationPython @evaluationArgs;$evaluationCode=$LASTEXITCODE} finally {Pop-Location}
exit $evaluationCode
