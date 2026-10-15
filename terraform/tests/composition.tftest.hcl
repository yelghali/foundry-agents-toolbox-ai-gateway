mock_provider "azapi" {}
mock_provider "azurerm" {
  mock_data "azurerm_virtual_network" {
    defaults = { location = "eastus2" }
  }
}

variables {
  subscription_id     = "00000000-0000-0000-0000-000000000000"
  resource_group_name = "lab"
  foundry_name        = "foundry-compose-test"
}

run "multiple_gateways_one_shared_foundry" {
  command = plan
  variables {
    gateways = {
      "gateway-team-a" = {}
      "gateway-team-b" = {}
    }
  }
  assert {
    condition     = length(module.gateways) == 2 && length(azurerm_role_assignment.gateway_foundry_user) == 2
    error_message = "Each new gateway requires its own identity and documented Foundry backend grant."
  }
  assert {
    condition     = alltrue([for gateway in values(module.gateways) : gateway.sku == "AIGateway"])
    error_message = "Every created gateway must be the dedicated AI Gateway tier."
  }
  assert {
    condition = alltrue([
      for assignment in values(azurerm_role_assignment.gateway_foundry_user) :
      endswith(assignment.role_definition_id, "/53ca6127-db72-4b80-b1b0-d745d6d5456d")
    ])
    error_message = "Gateway managed identities require the Foundry User role ID documented for managed-identity backend authentication."
  }
  assert {
    condition = alltrue([
      for handoff in values(output.gateway_onboarding) :
      handoff.backend_identity.required_role == "Foundry User" &&
      startswith(handoff.runtime_key_scope, "All published models and tools")
    ])
    error_message = "The onboarding handoff must preserve the documented backend role and preview-wide runtime-key boundary."
  }
  assert {
    condition     = length(module.abc) == 0
    error_message = "Deploying shared Foundry/gateways must not silently add three Search services."
  }
}

run "foundry_only_no_gateways" {
  command = plan
  assert {
    condition     = length(module.gateways) == 0 && length(azurerm_role_assignment.gateway_foundry_user) == 0 && length(output.gateway_onboarding) == 0
    error_message = "Foundry-only mode must not create a gateway or its roles."
  }
}

run "public_abc_without_classic_apim" {
  command = plan
  variables {
    enable_abc_lab     = true
    deployer_object_id = "22222222-2222-2222-2222-222222222222"
    model_deployments = {
      "gpt-4o-mini" = { model_name = "gpt-4o-mini", model_version = "2024-07-18" }
    }
  }
  assert {
    condition     = length(module.abc) == 1 && length(output.abc_config.cohorts) == 3 && output.abc_config.apimResourceId == null
    error_message = "The similar ABC foundation must compose without inventing a classic APIM dependency."
  }
}

run "private_foundry_only_no_addons" {
  command = plan
  variables {
    private_network = {
      virtual_network_id         = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/network/providers/Microsoft.Network/virtualNetworks/existing"
      private_endpoint_subnet_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/network/providers/Microsoft.Network/virtualNetworks/existing/subnets/pe"
    }
  }
  assert {
    condition     = length(module.gateways) == 0 && length(module.abc) == 0 && module.foundry.public_network_access == "Disabled"
    error_message = "Private Foundry-only must create neither gateway nor public ABC addons."
  }
}

run "reject_private_foundry_with_public_gateway" {
  command = plan
  variables {
    gateways = { "gateway-team-a" = {} }
    private_network = {
      virtual_network_id         = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/network/providers/Microsoft.Network/virtualNetworks/existing"
      private_endpoint_subnet_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/network/providers/Microsoft.Network/virtualNetworks/existing/subnets/pe"
    }
  }
  expect_failures = [var.gateways]
}

run "reject_private_foundry_public_abc_addon" {
  command = plan
  variables {
    enable_abc_lab     = true
    deployer_object_id = "22222222-2222-2222-2222-222222222222"
    model_deployments = {
      "gpt-4o-mini" = { model_name = "gpt-4o-mini", model_version = "2024-07-18" }
    }
    private_network = {
      virtual_network_id         = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/network/providers/Microsoft.Network/virtualNetworks/existing"
      private_endpoint_subnet_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/network/providers/Microsoft.Network/virtualNetworks/existing/subnets/pe"
    }
  }
  expect_failures = [var.enable_abc_lab]
}

run "reject_abc_without_required_model" {
  command = plan
  variables {
    enable_abc_lab     = true
    deployer_object_id = "22222222-2222-2222-2222-222222222222"
  }
  expect_failures = [var.abc_model_deployment_name]
}
