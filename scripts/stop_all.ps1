[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ProcessRecord, [switch]$Run)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_local_services.ps1')
$recordPath = [IO.Path]::GetFullPath($ProcessRecord)
$allowed = [IO.Path]::GetFullPath((Join-Path (Get-MovieWorkspace) 'artifacts\services')) + [IO.Path]::DirectorySeparatorChar
if (-not $recordPath.StartsWith($allowed, [StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($recordPath) -ne 'processes.json') { throw 'Only an owned artifacts/services/.../processes.json record is accepted.' }
$records = @(Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json)
foreach ($record in $records) {
    if ($record.name -notin @('backend','worker','frontend')) { throw 'Unknown process record component.' }
    if ($Run) { Stop-MovieOwnedProcess $record } else { Write-Output "Would verify and stop owned $($record.name), PID $($record.process_id). Use -Run to execute." }
}
Write-Output 'PostgreSQL, Spark, Jupyter and unrelated processes are never stopped by this script. Logs and process records are retained.'
