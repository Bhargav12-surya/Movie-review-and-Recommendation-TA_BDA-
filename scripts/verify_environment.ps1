<#
.SYNOPSIS
Read-only prerequisite verification; never installs, downloads, or trains.
.DESCRIPTION
Foundation/Data profiles validate the standard-library tools available now.
Missing scientific/JVM/NLP/backend/frontend prerequisites remain explicit.
Use -CheckCuda only after the approved PyTorch wheel is manually installed.
An optional report must be a new file in an existing workspace directory.
Exit codes: 0 selected scope ready; 2 prerequisites block it; 1 diagnostic error.
#>
[CmdletBinding()]
param(
    [string]$Workspace,
    [string]$PythonPath,
    [string]$ConfigPath,
    [string]$JavaHome,
    [ValidateSet('Foundation','Data','Spark','Nlp','Backend','Frontend','All')]
    [string]$Profile = 'Foundation',
    [switch]$CheckCuda,
    [switch]$CheckImports,
    [switch]$Json,
    [string]$OutputPath
)
$ErrorActionPreference = 'Stop'
$diagnosticScriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $Workspace) { $Workspace = Split-Path -Parent $diagnosticScriptRoot }
if (-not $PythonPath) {
    $PythonPath = Join-Path $Workspace '.venv\Scripts\python.exe'
} elseif (-not [IO.Path]::IsPathRooted($PythonPath)) {
    $PythonPath = Join-Path $Workspace $PythonPath
}
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    $failure = [ordered]@{
        schema_version=1; command='verify_environment'; profile=$Profile
        ready=$false; blocking_checks=@('python.executable'); exit_code=2
        checks=@(@{id='python.executable'; status='missing'; required=$true; phase=0
                    detail='Selected project Python executable does not exist. No interpreter fallback was attempted.'})
    }
    if ($Json) { $failure | ConvertTo-Json -Depth 6 } else { Write-Output $failure.checks[0].detail }
    exit 2
}
$probeArguments = @('-I','-B',(Join-Path $diagnosticScriptRoot 'verify_environment.py'),
                    '--workspace',$Workspace,'--profile',$Profile)
if ($ConfigPath) { $probeArguments += @('--config-path',$ConfigPath) }
if ($JavaHome) { $probeArguments += @('--java-home',$JavaHome) }
if ($CheckCuda) { $probeArguments += '--check-cuda' }
if ($CheckImports) { $probeArguments += '--check-imports' }
if ($Json) { $probeArguments += '--json' }
if ($OutputPath) { $probeArguments += @('--output-path',$OutputPath) }
& $PythonPath @probeArguments
exit $LASTEXITCODE
