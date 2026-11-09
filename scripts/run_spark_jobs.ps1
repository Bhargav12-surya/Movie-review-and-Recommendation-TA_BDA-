<#
.SYNOPSIS
Preflight or launch an already installed Spark distribution and existing project JAR.
.DESCRIPTION
Never invokes SBT, an installer, package resolution, downloads or model training.
Default preflight and -DryRun are read-only unless -ReportPath explicitly requests
a new report. Actual jobs require pinned local runtime/JAR and resource headroom.
#>
[CmdletBinding()]
param(
    [string]$Workspace,
    [string]$PythonPath,
    [string]$ConfigPath,
    [ValidateSet('preflight','batch','rdd','smoke','stream')]
    [string]$Job = 'preflight',
    [string]$SparkHome,
    [string]$JavaHome,
    [string]$InputPath = 'data/raw/movielens/ml-32m',
    [string]$OutputPath,
    [string]$JarPath = 'scala/target/scala-2.13/movieintel-spark_2.13-0.1.0.jar',
    [string]$Master = 'local[2]',
    [ValidateSet('1g','2g','3g','4g')]
    [string]$DriverMemory = '3g',
    [int]$ShufflePartitions = 8,
    [int]$InputPartitions = 4,
    [string]$EventInput,
    [string]$CheckpointPath,
    [string]$Watermark = '24 hours',
    [int]$MaxFilesPerTrigger = 5,
    [switch]$Continuous,
    [switch]$Resume,
    [switch]$AllowSyntheticEvents,
    [int]$HoldUiSeconds = 0,
    [switch]$DryRun,
    [switch]$Json,
    [string]$ReportPath
)
$ErrorActionPreference = 'Stop'
$launcherRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $Workspace) { $Workspace = Split-Path -Parent $launcherRoot }
if (-not $PythonPath) { $PythonPath = Join-Path $Workspace '.venv\Scripts\python.exe' }
elseif (-not [IO.Path]::IsPathRooted($PythonPath)) { $PythonPath = Join-Path $Workspace $PythonPath }
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    $failure = @{schema_version=1; command='run_spark_jobs'; ready=$false; executed=$false;
                 exit_code=2; blocking_checks=@('python.executable');
                 detail='Selected root Python does not exist. No interpreter or installer fallback was attempted.'}
    $failure | ConvertTo-Json -Depth 5
    exit 2
}
$launcherArgs = @('-I','-B',(Join-Path $launcherRoot 'spark_job_launcher.py'),
    '--workspace',$Workspace,'--job',$Job,'--input',$InputPath,'--jar',$JarPath,
    '--master',$Master,'--driver-memory',$DriverMemory,
    '--shuffle-partitions',[string]$ShufflePartitions,'--input-partitions',[string]$InputPartitions,
    '--hold-ui-seconds',[string]$HoldUiSeconds,
    '--watermark',$Watermark,'--max-files-per-trigger',[string]$MaxFilesPerTrigger)
foreach ($entry in @(
    @('--config-path',$ConfigPath), @('--spark-home',$SparkHome), @('--java-home',$JavaHome),
    @('--output',$OutputPath), @('--event-input',$EventInput), @('--checkpoint',$CheckpointPath),
    @('--report-path',$ReportPath))) {
    if ($entry[1]) { $launcherArgs += $entry }
}
if ($Resume) { $launcherArgs += '--resume' }
if ($AllowSyntheticEvents) { $launcherArgs += '--allow-synthetic-events' }
if ($Continuous) { $launcherArgs += '--continuous' }
if ($DryRun) { $launcherArgs += '--dry-run' }
if ($Json) { $launcherArgs += '--json' }
& $PythonPath @launcherArgs
exit $LASTEXITCODE
