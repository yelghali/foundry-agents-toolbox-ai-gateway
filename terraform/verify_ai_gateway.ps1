[CmdletBinding()]
param(
    [string]$GatewayName,
    [switch]$TestRuntime,
    [string]$ModelName,
    [string]$ToolServerName
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$foundryUserRoleId = "53ca6127-db72-4b80-b1b0-d745d6d5456d"

function Invoke-CheckedJson {
    param(
        [Parameter(Mandatory)][scriptblock]$Command,
        [Parameter(Mandatory)][string]$FailureMessage
    )

    $json = & $Command
    if ($LASTEXITCODE -ne 0) { throw $FailureMessage }
    return $json | ConvertFrom-Json
}

Push-Location $PSScriptRoot
try {
    $outputs = Invoke-CheckedJson -FailureMessage "Could not read Terraform outputs. Apply the top-level composition first." -Command {
        terraform output -json
    }
    if ($null -eq $outputs -or $null -eq $outputs.PSObject.Properties["gateways"] -or
        $null -eq $outputs.PSObject.Properties["foundry"]) {
        throw "No top-level gateway outputs were found. Apply the top-level composition before running this verifier."
    }
    $gatewayProperties = @($outputs.gateways.value.PSObject.Properties)
    if ($gatewayProperties.Count -eq 0) {
        throw "This Terraform state contains no dedicated AI gateway."
    }

    if ([string]::IsNullOrWhiteSpace($GatewayName)) {
        if ($gatewayProperties.Count -ne 1) {
            throw "Specify -GatewayName. Available gateways: $($gatewayProperties.Name -join ', ')."
        }
        $GatewayName = $gatewayProperties[0].Name
    }

    $selected = @($gatewayProperties | Where-Object Name -eq $GatewayName)
    if ($selected.Count -ne 1) {
        throw "Gateway '$GatewayName' is not in this Terraform state. Available gateways: $($gatewayProperties.Name -join ', ')."
    }
    $gateway = $selected[0].Value
    $foundry = $outputs.foundry.value

    $resource = Invoke-CheckedJson -FailureMessage "Could not read the AI gateway ARM resource." -Command {
        az rest --method get --uri "https://management.azure.com$($gateway.id)?api-version=2026-09-01-preview" --output json
    }
    if ($resource.type -ne "Microsoft.ApiManagement/aigateways" -or $resource.sku.name -ne "AIGateway") {
        throw "Resource '$GatewayName' is not the dedicated Microsoft.ApiManagement/aigateways AIGateway tier."
    }
    if ($resource.properties.provisioningState -ne "Succeeded") {
        throw "Gateway provisioning state is '$($resource.properties.provisioningState)', not 'Succeeded'."
    }

    $assignments = Invoke-CheckedJson -FailureMessage "Could not read role assignments on the shared Foundry resource." -Command {
        az role assignment list --assignee-object-id $gateway.principal_id --scope $foundry.id --output json
    }
    $foundryRole = @($assignments | Where-Object {
            $_.roleDefinitionId -and $_.roleDefinitionId.EndsWith("/$foundryUserRoleId", [StringComparison]::OrdinalIgnoreCase)
        })
    if ($foundryRole.Count -eq 0) {
        throw "Gateway identity '$($gateway.principal_id)' lacks Foundry User ($foundryUserRoleId) on '$($foundry.id)'."
    }

    Write-Host "Infrastructure verified: $GatewayName is ready and its system identity has Foundry User on the shared Foundry resource."
    Write-Host "Portal steps still required by the preview service:"
    Write-Host "  1. Models -> Add models -> Import from Foundry -> Managed identity."
    Write-Host "  2. Optionally publish MCP servers under MCP servers."
    Write-Host "  3. Keys -> create a runtime access key and store it in an approved secret store."
    Write-Warning "Every preview runtime key can call every published model and tool in this gateway; use separate gateways for authorization isolation."

    if (-not $TestRuntime) { return }
    if ([string]::IsNullOrWhiteSpace($env:AI_GATEWAY_RUNTIME_ACCESS_KEY)) {
        throw "Set AI_GATEWAY_RUNTIME_ACCESS_KEY in the current process before using -TestRuntime. The script never prints it."
    }
    if ([string]::IsNullOrWhiteSpace($ModelName) -and [string]::IsNullOrWhiteSpace($ToolServerName)) {
        throw "Use -ModelName, -ToolServerName, or both with -TestRuntime."
    }

    $headers = @{ "api-key" = $env:AI_GATEWAY_RUNTIME_ACCESS_KEY }
    if (-not [string]::IsNullOrWhiteSpace($ModelName)) {
        $modelBody = @{
            model      = $ModelName
            messages   = @(@{ role = "user"; content = "Reply with READY." })
            max_tokens = 8
        } | ConvertTo-Json -Depth 8
        $modelResponse = Invoke-RestMethod -Method Post `
            -Uri "$($gateway.endpoint)/default/models/openai/v1/chat/completions" `
            -Headers $headers -ContentType "application/json" -Body $modelBody
        if (@($modelResponse.choices).Count -eq 0) {
            throw "The model endpoint returned no choices."
        }
        Write-Host "Runtime model smoke test passed for '$ModelName'; response content was not printed."
    }

    if (-not [string]::IsNullOrWhiteSpace($ToolServerName)) {
        $toolBody = @{ jsonrpc = "2.0"; id = 1; method = "tools/list" } | ConvertTo-Json
        $toolResponse = Invoke-RestMethod -Method Post `
            -Uri "$($gateway.endpoint)/default/toolservers/$ToolServerName/mcp" `
            -Headers $headers -ContentType "application/json" -Body $toolBody
        if ($null -eq $toolResponse.result -or $null -eq $toolResponse.result.tools) {
            throw "The MCP endpoint did not return a tools list."
        }
        Write-Host "Runtime MCP smoke test passed for '$ToolServerName' with $(@($toolResponse.result.tools).Count) tools."
    }
}
finally {
    Pop-Location
}
