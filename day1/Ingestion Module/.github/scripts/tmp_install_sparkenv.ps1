$ErrorActionPreference = "Stop"

Set-Location "C:/Users/abderrahmane.filali/Documents/git/ADIF-Core"
. ./.github/scripts/authentication.ps1
$fabricToken = Get-FabricAccessToken
$headers = @{ Authorization = "Bearer $fabricToken"; "Content-Type" = "application/json" }

function Get-AllPages {
    param([string]$Url)
    $items = @()
    $next = $Url
    while ($next) {
        $resp = Invoke-RestMethod -Uri $next -Headers $headers -Method GET
        if ($resp.value) { $items += $resp.value }
        if ($resp.continuationUri) {
            $next = $resp.continuationUri
        } elseif ($resp.continuationToken) {
            if ($Url -match "\?") { $next = "$Url&continuationToken=$($resp.continuationToken)" }
            else { $next = "$Url?continuationToken=$($resp.continuationToken)" }
        } else {
            $next = $null
        }
    }
    return ,$items
}

$deName = "Pro-DE-dev"
$dataName = "Pro-Data-dev"

$workspaces = Get-AllPages -Url "https://api.fabric.microsoft.com/v1/workspaces"
$deWs = $workspaces | Where-Object { $_.displayName -ieq $deName } | Select-Object -First 1
$dataWs = $workspaces | Where-Object { $_.displayName -ieq $dataName } | Select-Object -First 1
if (-not $deWs) { throw "DE workspace not found: $deName" }
if (-not $dataWs) { throw "Data workspace not found: $dataName" }
$deWorkspaceId = $deWs.id
$dataWorkspaceId = $dataWs.id

$wheelPath = "src/sparkenv.Environment/Libraries/CustomLibraries/DIFForFabric-1.0-py3-none-any.whl"
if (-not (Test-Path $wheelPath)) { throw "Wheel not found at $wheelPath" }

$envs = Get-AllPages -Url "https://api.fabric.microsoft.com/v1/workspaces/$deWorkspaceId/environments"
$sparkEnv = $envs | Where-Object { $_.displayName -ieq "sparkenv" } | Select-Object -First 1
$createdSparkEnv = $false

if (-not $sparkEnv) {
    $createEnvJson = python .github/scripts/fabric-operation/create_spark_environment.py --token $fabricToken --workspace-id $deWorkspaceId --name sparkenv --wheel-path $wheelPath
    if ($LASTEXITCODE -ne 0) { throw "create_spark_environment.py failed: $createEnvJson" }

    $found = $null
    for ($i=0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 1500
        $envs = Get-AllPages -Url "https://api.fabric.microsoft.com/v1/workspaces/$deWorkspaceId/environments"
        $found = $envs | Where-Object { $_.displayName -ieq "sparkenv" } | Select-Object -First 1
        if ($found) { break }
    }
    if (-not $found) { throw "sparkenv creation requested but environment was not discoverable in time." }
    $sparkEnv = $found
    $createdSparkEnv = $true
}

$sparkenvId = $sparkEnv.id

$envDefResp = Invoke-RestMethod -Uri "https://api.fabric.microsoft.com/v1/workspaces/$deWorkspaceId/environments/$sparkenvId/getDefinition" -Headers $headers -Method POST
$parts = @()
if ($envDefResp.definition.parts) { $parts = $envDefResp.definition.parts }
$hasWheel = $false
foreach ($p in $parts) {
    if ($p.path -ieq "Libraries/CustomLibraries/DIFForFabric-1.0-py3-none-any.whl") { $hasWheel = $true; break }
}
if (-not $hasWheel) {
    throw "Existing sparkenv does not include required DIFForFabric wheel."
}

if ($createdSparkEnv) {
    $publishResp = Invoke-WebRequest -Uri "https://api.fabric.microsoft.com/v1/workspaces/$deWorkspaceId/environments/$sparkenvId/staging/publish?beta=False" -Headers $headers -Method POST
    if ($publishResp.StatusCode -eq 202) {
        $location = $publishResp.Headers["Location"]
        if ($location) {
            for ($i=0; $i -lt 60; $i++) {
                Start-Sleep -Milliseconds 2000
                $op = Invoke-RestMethod -Uri $location -Headers @{ Authorization = "Bearer $fabricToken" } -Method GET
                if ($op.status -in @("Succeeded","Failed","Canceled")) {
                    if ($op.status -ne "Succeeded") { throw "sparkenv publish failed: $($op | ConvertTo-Json -Depth 6 -Compress)" }
                    break
                }
                if ($i -eq 59) { throw "Timed out waiting for sparkenv publish." }
            }
        }
    } elseif ($publishResp.StatusCode -notin @(200,201,204)) {
        throw "Unexpected publish response status: $($publishResp.StatusCode)"
    }
}

$lakehouses = Get-AllPages -Url "https://api.fabric.microsoft.com/v1/workspaces/$dataWorkspaceId/lakehouses"
$bronze = $lakehouses | Where-Object { $_.displayName -ieq "bronze_LH" } | Select-Object -First 1
$silver = $lakehouses | Where-Object { $_.displayName -ieq "silver_LH" } | Select-Object -First 1
$gold   = $lakehouses | Where-Object { $_.displayName -ieq "gold_LH" } | Select-Object -First 1
if (-not $bronze) { throw "bronze_LH not found." }
if (-not $silver) { throw "silver_LH not found." }
if (-not $gold)   { throw "gold_LH not found." }

$jobs = Get-AllPages -Url "https://api.fabric.microsoft.com/v1/workspaces/$deWorkspaceId/sparkJobDefinitions"
$ing = $jobs | Where-Object { $_.displayName -ieq "IngestionJob" } | Select-Object -First 1
$std = $jobs | Where-Object { $_.displayName -ieq "StandardizationJob" } | Select-Object -First 1
$trf = $jobs | Where-Object { $_.displayName -ieq "TransformationJob" } | Select-Object -First 1

function Invoke-CreateOrUpdateSparkJob {
    param(
        [string]$Name,
        [string]$DefinitionPath,
        [string]$DefaultLakehouseId,
        [string]$DefaultLakehouseWorkspaceId,
        [string[]]$AdditionalLakehouseIds,
        [string[]]$AdditionalLakehouseWorkspaceIds,
        [string]$ExistingJobId
    )

    $args = @(
        ".github/scripts/fabric-operation/create_spark_job.py",
        "--token", $fabricToken,
        "--workspace-id", $deWorkspaceId,
        "--name", $Name,
        "--definition-path", $DefinitionPath,
        "--default-lakehouse-id", $DefaultLakehouseId,
        "--default-lakehouse-workspace-id", $DefaultLakehouseWorkspaceId,
        "--environment-id", $sparkenvId,
        "--executable-workspace-id", $deWorkspaceId
    )

    if ($ExistingJobId) {
        $args += @("--spark-job-id", $ExistingJobId)
    }

    for ($i=0; $i -lt $AdditionalLakehouseIds.Count; $i++) {
        $args += @("--additional-lakehouse-id", $AdditionalLakehouseIds[$i])
        $args += @("--additional-lakehouse-workspace-id", $AdditionalLakehouseWorkspaceIds[$i])
    }

    $result = python @args
    if ($LASTEXITCODE -ne 0) { throw "create_spark_job.py failed for ${Name}: $result" }
}

Invoke-CreateOrUpdateSparkJob -Name "IngestionJob" -DefinitionPath "src/sparkjobs/IngestionJob.SparkJobDefinition/SparkJobDefinitionV1.json" -DefaultLakehouseId $bronze.id -DefaultLakehouseWorkspaceId $dataWorkspaceId -AdditionalLakehouseIds @() -AdditionalLakehouseWorkspaceIds @() -ExistingJobId $ing.id
Invoke-CreateOrUpdateSparkJob -Name "StandardizationJob" -DefinitionPath "src/sparkjobs/StandardizationJob.SparkJobDefinition/SparkJobDefinitionV1.json" -DefaultLakehouseId $silver.id -DefaultLakehouseWorkspaceId $dataWorkspaceId -AdditionalLakehouseIds @($bronze.id) -AdditionalLakehouseWorkspaceIds @($dataWorkspaceId) -ExistingJobId $std.id
Invoke-CreateOrUpdateSparkJob -Name "TransformationJob" -DefinitionPath "src/sparkjobs/TransformationJob.SparkJobDefinition/SparkJobDefinitionV1.json" -DefaultLakehouseId $gold.id -DefaultLakehouseWorkspaceId $dataWorkspaceId -AdditionalLakehouseIds @($silver.id) -AdditionalLakehouseWorkspaceIds @($dataWorkspaceId) -ExistingJobId $trf.id

$jobsAfter = Get-AllPages -Url "https://api.fabric.microsoft.com/v1/workspaces/$deWorkspaceId/sparkJobDefinitions"
$ingAfter = $jobsAfter | Where-Object { $_.displayName -ieq "IngestionJob" } | Select-Object -First 1
$stdAfter = $jobsAfter | Where-Object { $_.displayName -ieq "StandardizationJob" } | Select-Object -First 1
$trfAfter = $jobsAfter | Where-Object { $_.displayName -ieq "TransformationJob" } | Select-Object -First 1
if (-not $ingAfter -or -not $stdAfter -or -not $trfAfter) { throw "One or more Spark jobs missing after deployment." }

[ordered]@{
    deWorkspaceName = $deName
    deWorkspaceId = $deWorkspaceId
    dataWorkspaceName = $dataName
    dataWorkspaceId = $dataWorkspaceId
    sparkenvId = $sparkenvId
    ingestionJobId = $ingAfter.id
    standardizationJobId = $stdAfter.id
    transformationJobId = $trfAfter.id
    bronzeLakehouseId = $bronze.id
    silverLakehouseId = $silver.id
    goldLakehouseId = $gold.id
    sparkenvCreatedThisRun = $createdSparkEnv
} | ConvertTo-Json -Depth 6

