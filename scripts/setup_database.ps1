[CmdletBinding()]
param([string]$PythonPath, [switch]$ExecuteMigration)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_local_services.ps1')
$python = Get-MoviePython $PythonPath
Assert-MovieBackendPackages $python
if (-not $ExecuteMigration) {
    Write-Output 'Metadata preflight only. No database connection, creation or migration was attempted.'
    Write-Output 'Manually create the PostgreSQL role/database, enable pgvector using an appropriate administrator, and configure backend/.env. Review backend/alembic/schema_v1.sql before using -ExecuteMigration.'
    exit 0
}
Assert-MovieTcp
Set-MovieOfflineProcess
Push-Location -LiteralPath (Get-MovieWorkspace)
try { & $python -B -m alembic -c backend/alembic.ini upgrade head; exit $LASTEXITCODE }
finally { Pop-Location }
