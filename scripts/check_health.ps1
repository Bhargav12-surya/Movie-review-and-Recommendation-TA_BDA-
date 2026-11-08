<#
.SYNOPSIS
Inspect existing localhost services without starting them.
.DESCRIPTION
HTTP/TCP reachability is reported separately from explicit backend readiness
and read-only database/pgvector verification. No password prompt or migration.
Exit codes: 0 checked services ready; 2 unavailable/unverified; 1 diagnostic error.
#>
[CmdletBinding()]
param(
    [string]$Workspace,
    [string]$PythonPath,
    [string]$BackendUrl = 'http://127.0.0.1:8000/api/v1/health',
    [string]$FrontendUrl = 'http://127.0.0.1:3000',
    [string]$PostgresHost = '127.0.0.1',
    [int]$PostgresPort = 5432,
    [double]$TimeoutSeconds = 2,
    [switch]$CheckDatabase,
    [string]$DatabaseName,
    [string]$DatabaseUser,
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
        schema_version=1; command='check_health'; ready=$false
        blocking_checks=@('python.executable'); exit_code=2
        checks=@(@{id='python.executable'; status='missing'; required=$true; phase=0
                    detail='Selected project Python executable does not exist; health checks did not run.'})
    }
    if ($Json) { $failure | ConvertTo-Json -Depth 6 } else { Write-Output $failure.checks[0].detail }
    exit 2
}
$probeArguments = @('-I','-B',(Join-Path $diagnosticScriptRoot 'check_health.py'),
                    '--workspace',$Workspace,'--backend-url',$BackendUrl,
                    '--frontend-url',$FrontendUrl,'--postgres-host',$PostgresHost,
                    '--postgres-port',[string]$PostgresPort,'--timeout',[string]$TimeoutSeconds)
if ($CheckDatabase) { $probeArguments += '--check-database' }
if ($DatabaseName) { $probeArguments += @('--database-name',$DatabaseName) }
if ($DatabaseUser) { $probeArguments += @('--database-user',$DatabaseUser) }
if ($Json) { $probeArguments += '--json' }
if ($OutputPath) { $probeArguments += @('--output-path',$OutputPath) }
& $PythonPath @probeArguments
exit $LASTEXITCODE
