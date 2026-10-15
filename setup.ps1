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
Push-Location $PSScriptRoot
try {
    & (Join-Path $PSScriptRoot "deploy.ps1") @PSBoundParameters
    function Invoke-LabPython {
        param([Parameter(ValueFromRemainingArguments)][string[]]$Arguments)
        & python @Arguments
        if ($LASTEXITCODE -ne 0) { throw "Lab step failed: python $($Arguments -join ' ')" }
    }
    foreach ($cohort in @("a", "b", "c")) {
        Invoke-LabPython provision.py --cohort $cohort
    }
    Invoke-LabPython publish_agents.py --cohort a --routes direct toolbox apim --showcase
    Invoke-LabPython publish_agents.py --cohort b --routes direct toolbox --showcase
    Invoke-LabPython publish_agents.py --cohort c --routes direct toolbox
    Invoke-LabPython configure_agent_gateway.py
    Invoke-LabPython publish_agents.py --cohort b --routes data-gateway
    Invoke-LabPython configure_user_ingress.py
    Write-Host "Primary A/B/C setup published. Run verify.ps1 for live evidence; no success is inferred from deployment alone."
}
finally {
    Pop-Location
}
