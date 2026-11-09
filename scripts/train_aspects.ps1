<# Explicit later model entry points; no install/download and no fit by default. #>
[CmdletBinding()]
param(
    [ValidateSet('aspect_extraction','aspect_sentiment','themes')][string]$Component='aspect_extraction',
    [ValidateSet('Preflight','Train','Resume','Evaluate','Predict')][string]$Action='Preflight',
    [string]$ConfigPath,[string]$RunDirectory,[string]$ResumeCheckpoint,
    [ValidateSet('tuning','calibration','test')][string]$Split='tuning',
    [ValidateSet('cpu','cuda','auto')][string]$Device='cpu',
    [string]$ReviewText,[string]$Language='en',[string]$AspectCategory,
    [Nullable[int]]$AspectStart,[Nullable[int]]$AspectEnd,
    [switch]$FinalTest,[switch]$ExecuteApprovedRun
)
$ErrorActionPreference='Stop'
$aspectWorkspace=Split-Path -Parent $PSScriptRoot
$aspectPython=Join-Path $aspectWorkspace '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $aspectPython -PathType Leaf)) { throw 'Selected Python3.11 is missing.' }
if ($Action -in @('Train','Resume') -and -not $ExecuteApprovedRun) { throw 'Explicit ExecuteApprovedRun plus actual run records required.' }
$aspectEntry=if ($Action -in @('Preflight','Train','Resume')) {'train'} elseif ($Action -eq 'Evaluate') {'evaluate'} else {'predict'}
$aspectArguments=@('-B','-m',"ml.$Component.$aspectEntry")
if ($ConfigPath) {$aspectArguments+=@('--config',$ConfigPath)}
if ($Action -in @('Train','Resume')) {$aspectArguments+='--execute'}
if ($Action -eq 'Resume') {
    if (-not $ResumeCheckpoint) {throw 'ResumeCheckpoint is required.'}
    $aspectArguments+=@('--resume-checkpoint',$ResumeCheckpoint)
}
if ($Action -in @('Evaluate','Predict')) {
    if (-not $RunDirectory) {throw 'RunDirectory is required.'}
    $aspectArguments+=@('--run-dir',$RunDirectory,'--device',$Device)
}
if ($Action -eq 'Evaluate') {
    $aspectArguments+=@('--split',$Split)
    if ($FinalTest) {$aspectArguments+='--final-test'}
}
if ($Action -eq 'Predict') {
    if (-not $ReviewText) {throw 'ReviewText is required and is not echoed by this launcher.'}
    $aspectArguments+=@('--text',$ReviewText,'--language',$Language)
    if ($Component -eq 'aspect_sentiment') {
        if (-not $AspectCategory -or $null -eq $AspectStart -or $null -eq $AspectEnd) {throw 'Exact original target category/start/end are required.'}
        $aspectArguments+=@('--aspect-category',$AspectCategory,'--aspect-start',[string]$AspectStart,'--aspect-end',[string]$AspectEnd)
    }
}
Push-Location -LiteralPath $aspectWorkspace
try { & $aspectPython @aspectArguments; $aspectExitCode=$LASTEXITCODE } finally {Pop-Location}
exit $aspectExitCode
