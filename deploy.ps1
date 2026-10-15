[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$SubscriptionId,
    [Parameter(Mandatory)][string]$FoundryResourceGroup,
    [Parameter(Mandatory)][string]$FoundryAccountName,
    [Parameter(Mandatory)][string]$ApimResourceGroup,
    [Parameter(Mandatory)][string]$ApimName,
    [string]$ResourceGroup = "rg-foundry-agents-toolbox",
    [string]$SearchLocation = "swedencentral",
    [string]$ModelDeployment = "gpt-4o-mini"
)

$ErrorActionPreference = "Stop"
$foundry = az cognitiveservices account show --subscription $SubscriptionId `
    --resource-group $FoundryResourceGroup --name $FoundryAccountName --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Could not resolve the existing Foundry account." }
$apim = az apim show --subscription $SubscriptionId --resource-group $ApimResourceGroup `
    --name $ApimName --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Could not resolve the existing APIM service." }
if ($apim.sku.name -ne "StandardV2") {
    throw "This lab was verified with StandardV2 APIM, not $($apim.sku.name). Other tiers, including the dedicated AI Gateway preview tier, require separate validation."
}
$path = Join-Path $PSScriptRoot ".config.json"
$previous = $null
if (Test-Path -LiteralPath $path) {
    $previous = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    if ($previous.subscriptionId -ne $SubscriptionId -or
        $previous.foundryAccountName -ne $FoundryAccountName -or
        $previous.apimResourceId -ne $apim.id) {
        throw "Existing runtime configuration targets a different environment. Preserve it separately before switching targets."
    }
}
az group create --subscription $SubscriptionId --name $ResourceGroup --location $foundry.location --output none
if ($LASTEXITCODE -ne 0) { throw "Could not create the additive lab resource group." }
$token = az account get-access-token --subscription $SubscriptionId `
    --resource https://management.azure.com --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Could not obtain the deployer's management token." }
$payload = $token.accessToken.Split(".")[1].Replace("-", "+").Replace("_", "/")
$payload += "=" * ((4 - $payload.Length % 4) % 4)
$claims = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($payload)) | ConvertFrom-Json
$deployment = az deployment group create --subscription $SubscriptionId `
    --resource-group $ResourceGroup --name "foundry-agents-foundation" `
    --template-file (Join-Path $PSScriptRoot "infra.bicep") `
    --parameters foundryAccountName=$FoundryAccountName foundryResourceGroup=$FoundryResourceGroup `
        foundryLocation=$($foundry.location) deployerPrincipalId=$($claims.oid) searchLocation=$SearchLocation `
        modelDeployment=$ModelDeployment apimName=$ApimName apimResourceGroup=$ApimResourceGroup `
    --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Lab infrastructure deployment failed." }
$config = [ordered]@{}
foreach ($property in $deployment.properties.outputs.PSObject.Properties) {
    $config[$property.Name] = $property.Value.value
}
if ($null -ne $previous) {
    $config.cohorts = @($config.cohorts | ForEach-Object {
        $fresh = $_
        $existing = @($previous.cohorts | Where-Object { $_.project.id -eq $fresh.project.id })
        if ($existing.Count -eq 1) { $existing[0] } else { $fresh }
    })
}
$nextPath = Join-Path $PSScriptRoot ".config.next.json"
$config | ConvertTo-Json -Depth 32 | Set-Content -Encoding utf8 $nextPath
Move-Item -LiteralPath $nextPath -Destination $path -Force
Write-Host "Foundation deployed; existing agent/tool state retained. APIM tier: $($config.apimSku)."
