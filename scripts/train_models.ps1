<#
.SYNOPSIS
Explicit model entry points for manual use. Default action is preflight only.
.DESCRIPTION
Never installs dependencies or downloads data/models. Train/Resume require the
ExecuteApprovedRun switch and valid permission/approval records in configuration.
This script was generated for later user execution; it is not a training result.
#>
[CmdletBinding()]
param(
    [ValidateSet('sentiment_tfidf','sentiment_transformer','multilingual_sentiment','sarcasm')]
    [string]$Component = 'sentiment_transformer',
    [ValidateSet('Preflight','Train','Resume','Evaluate','Predict')]
    [string]$Action = 'Preflight',
    [string]$ConfigPath,
    [string]$RunDirectory,
    [string]$ResumeCheckpoint,
    [ValidateSet('tuning','calibration','test')]
    [string]$Split = 'tuning',
    [ValidateSet('cpu','cuda','auto')]
    [string]$Device = 'cpu',
    [string]$ReviewText,
    [string]$Language = 'en',
    [switch]$FinalTest,
    [switch]$ExecuteApprovedRun
)
$ErrorActionPreference = 'Stop'
$modelWorkspace = Split-Path -Parent $PSScriptRoot
$modelPython = Join-Path $modelWorkspace '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $modelPython -PathType Leaf)) { throw 'The configured Python3.11 environment is missing.' }
if ($Action -in @('Train','Resume') -and -not $ExecuteApprovedRun) {
    throw 'Train/Resume need ExecuteApprovedRun and separately approved source/model/run records.'
}
$modelEntry = if ($Action -in @('Preflight','Train','Resume')) { 'train' } elseif ($Action -eq 'Evaluate') { 'evaluate' } else { 'predict' }
$modelArguments = @('-B','-m',"ml.$Component.$modelEntry")
if ($ConfigPath) { $modelArguments += @('--config',$ConfigPath) }
if ($Action -in @('Train','Resume')) { $modelArguments += '--execute' }
if ($Action -eq 'Resume') {
    if ($Component -eq 'sentiment_tfidf') { throw 'Classical baseline resume is unsupported; choose a fresh approved run.' }
    if (-not $ResumeCheckpoint) { throw 'ResumeCheckpoint is required.' }
    $modelArguments += @('--resume-checkpoint',$ResumeCheckpoint)
}
if ($Action -in @('Evaluate','Predict')) {
    if (-not $RunDirectory) { throw 'RunDirectory is required.' }
    $modelArguments += @('--run-dir',$RunDirectory)
}
if ($Action -eq 'Evaluate') {
    $modelArguments += @('--split',$Split)
    if ($FinalTest) { $modelArguments += '--final-test' }
    if ($Component -ne 'sentiment_tfidf') { $modelArguments += @('--device',$Device) }
}
if ($Action -eq 'Predict') {
    if (-not $ReviewText) { throw 'ReviewText is required; it is not echoed by this launcher.' }
    $modelArguments += @('--text',$ReviewText,'--language',$Language)
    if ($Component -ne 'sentiment_tfidf') { $modelArguments += @('--device',$Device) }
}
Push-Location -LiteralPath $modelWorkspace
try { & $modelPython @modelArguments; $modelExitCode = $LASTEXITCODE }
finally { Pop-Location }
exit $modelExitCode
