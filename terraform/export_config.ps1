[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repository = Split-Path $PSScriptRoot -Parent
$path = Join-Path $repository ".config.json"
Push-Location $PSScriptRoot
try {
    $config = terraform output -json abc_config | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw "Terraform output failed. Apply the ABC-enabled foundation first." }
    if ($null -eq $config) { throw "This deployment does not enable the optional ABC foundation." }
    if (Test-Path -LiteralPath $path) {
        throw "Runtime configuration already exists. Preserve it or deliberately reconcile it; this export will not erase agent/tool state."
    }
    $config | ConvertTo-Json -Depth 32 | Set-Content -LiteralPath $path -Encoding utf8
    Write-Host "Exported nonsecret ABC foundation configuration. Python provisioning creates the data-plane resources."
    if ($null -eq $config.apimResourceId) {
        Write-Host "No StandardV2 APIM bridge: use direct/toolbox routes. Dedicated AI Gateway assets and policies are separate."
    }
}
finally {
    Pop-Location
}
