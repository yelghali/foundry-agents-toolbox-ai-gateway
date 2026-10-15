mock_provider "azapi" {
  mock_resource "azapi_resource" {
    defaults = {
      output = {
        identity = { principalId = "11111111-1111-1111-1111-111111111111" }
        properties = {
          frontend = { defaultHostname = "gateway-module-test.azure-api.net" }
        }
      }
    }
  }
  mock_data "azapi_resource" {
    defaults = {
      output = {
        properties = { delegations = [{ properties = { serviceName = "Microsoft.App/environments" } }] }
      }
    }
  }
}
mock_provider "azurerm" {
  mock_data "azurerm_virtual_network" {
    defaults = { location = "eastus2" }
  }
}

variables {
  name              = "gateway-module-test"
  resource_group_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/lab"
  location          = "eastus2"
}

run "dedicated_ai_gateway_not_classic_apim" {
  command = apply
  module { source = "./modules/ai-gateway" }
  assert {
    condition     = azapi_resource.gateway.type == "Microsoft.ApiManagement/aigateways@2026-09-01-preview" && output.sku == "AIGateway"
    error_message = "Terraform must deploy the dedicated AIGateway resource/SKU, not StandardV2."
  }
  assert {
    condition     = length(data.azapi_resource.backend_subnet) == 0 && length(keys(azapi_resource.gateway.body.properties)) == 0
    error_message = "Public gateway mode must not assume a VNet or subnet."
  }
  assert {
    condition = (
      endswith(output.models_endpoint, "/default/models") &&
      endswith(output.models_openai_base_url, "/default/models/openai/v1") &&
      endswith(output.toolservers_endpoint, "/default/toolservers")
    )
    error_message = "The module must expose the documented model and tool-server endpoint prefixes."
  }
}

run "private_backend_existing_delegated_subnet" {
  command = plan
  module { source = "./modules/ai-gateway" }
  variables {
    backend_subnet_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/network/providers/Microsoft.Network/virtualNetworks/existing/subnets/gateway"
  }
  assert {
    condition     = azapi_resource.gateway.body.properties.backend.subnet.id == var.backend_subnet_id && terraform_data.backend.triggers_replace == var.backend_subnet_id
    error_message = "The pinned create-only backend setting must use the existing subnet and force replacement when changed."
  }
}

run "reject_incorrect_delegation" {
  command = plan
  module { source = "./modules/ai-gateway" }
  variables {
    backend_subnet_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/network/providers/Microsoft.Network/virtualNetworks/existing/subnets/gateway"
  }
  override_data {
    target = data.azapi_resource.backend_subnet[0]
    values = { output = { properties = { delegations = [{ properties = { serviceName = "Microsoft.Web/serverFarms" } }] } } }
  }
  expect_failures = [azapi_resource.gateway]
}

run "reject_wrong_backend_region" {
  command = plan
  module { source = "./modules/ai-gateway" }
  variables {
    backend_subnet_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/network/providers/Microsoft.Network/virtualNetworks/existing/subnets/gateway"
  }
  override_data {
    target = data.azurerm_virtual_network.backend[0]
    values = { location = "swedencentral" }
  }
  expect_failures = [azapi_resource.gateway]
}

run "reject_unsupported_preview_region" {
  command = plan
  module { source = "./modules/ai-gateway" }
  variables { location = "westus2" }
  expect_failures = [var.location]
}
