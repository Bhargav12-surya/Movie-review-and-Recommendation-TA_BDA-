<# Compatibility entry point; stop only a verified start_all process record. #>
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ProcessRecord,[switch]$Execute)
$stopArguments=@('-ProcessRecord',$ProcessRecord)
if ($Execute) {$stopArguments+='-Run'}
& (Join-Path $PSScriptRoot 'stop_all.ps1') @stopArguments
exit $LASTEXITCODE
