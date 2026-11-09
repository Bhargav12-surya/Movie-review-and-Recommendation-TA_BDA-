<# Real Scala MLlib execution only after separately reviewed local readiness. #>
[CmdletBinding()]
param(
    [ValidateSet('Preflight','Train')][string]$Action='Preflight',
    [string]$ConfigPath='configs/recommendation/als.json',
    [string]$ApprovalPath,[string]$JarPath,
    [switch]$ExecuteApprovedRun
)
$ErrorActionPreference='Stop'
$recommendationWorkspace=Split-Path -Parent $PSScriptRoot
$recommendationEnvironment=Get-Content -LiteralPath (Join-Path $recommendationWorkspace 'configs/environment.json') -Raw | ConvertFrom-Json
$recommendationSpark=Join-Path $recommendationEnvironment.spark.home 'bin\spark-submit.cmd'
$recommendationConfig=[IO.Path]::GetFullPath((Join-Path $recommendationWorkspace $ConfigPath))
if ($Action -eq 'Preflight') {
    @{scope='metadata_only';spark_submit_present=(Test-Path -LiteralPath $recommendationSpark -PathType Leaf);config_present=(Test-Path -LiteralPath $recommendationConfig -PathType Leaf);trained=$false;runtime_ready=$false;next='Review source/split approval, exact input fingerprints, final compiled JAR and current RAM before explicit training.'} | ConvertTo-Json
    exit 2
}
if (-not $ExecuteApprovedRun -or -not $ApprovalPath -or -not $JarPath) {throw 'ExecuteApprovedRun, exact ApprovalPath and final JarPath are required.'}
$recommendationApproval=[IO.Path]::GetFullPath((Join-Path $recommendationWorkspace $ApprovalPath))
$recommendationJar=[IO.Path]::GetFullPath((Join-Path $recommendationWorkspace $JarPath))
foreach ($recommendationPath in @($recommendationConfig,$recommendationApproval,$recommendationJar)) {
    if (-not $recommendationPath.StartsWith($recommendationWorkspace+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {throw 'Inputs must stay inside the workspace.'}
    if (-not (Test-Path -LiteralPath $recommendationPath -PathType Leaf)) {throw 'A supplied local input is missing.'}
}
$recommendationPython=Join-Path $recommendationWorkspace '.venv\Scripts\python.exe'
& $recommendationPython -I -B (Join-Path $PSScriptRoot 'recommendation_readiness.py')
if ($LASTEXITCODE -ne 0) {throw 'Insufficient verified local toolchain/resources; no Spark job started.'}
$recommendationOldJava=$env:JAVA_HOME
$recommendationOldLocal=$env:SPARK_LOCAL_IP
$recommendationOldHost=$env:SPARK_LOCAL_HOSTNAME
Push-Location -LiteralPath $recommendationWorkspace
try {
    $env:JAVA_HOME=$recommendationEnvironment.java.home
    $env:SPARK_LOCAL_IP='127.0.0.1'
    $env:SPARK_LOCAL_HOSTNAME='localhost'
    & $recommendationSpark '--master' 'local[2]' '--driver-memory' '3g' '--class' 'com.movieintel.recommendation.RecommendationJob' $recommendationJar $recommendationWorkspace $recommendationConfig $recommendationApproval
    $recommendationExitCode=$LASTEXITCODE
} finally {
    $env:JAVA_HOME=$recommendationOldJava
    $env:SPARK_LOCAL_IP=$recommendationOldLocal
    $env:SPARK_LOCAL_HOSTNAME=$recommendationOldHost
    Pop-Location
}
exit $recommendationExitCode
