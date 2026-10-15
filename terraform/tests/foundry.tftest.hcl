mock_provider "azapi" {}
mock_provider "azurerm" {
  mock_data "azurerm_virtual_network" {
    defaults = { location = "swedencentral" }
  }
}

variables {
  name                = "foundry-module-test"
  resource_group_id   = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/lab"
  resource_group_name = "lab"
  location            = "eastus2"
}

run "public_foundry_only" {
  command = plan
  module { source = "./modules/shared-foundry" }
  assert {
    condition     = azapi_resource.account.body.properties.allowProjectManagement && azapi_resource.account.body.properties.disableLocalAuth
    error_message = "The shared account must support projects and disable local keys."
  }
  assert {
    condition     = output.public_network_access == "Enabled" && length(azurerm_private_endpoint.foundry) == 0 && length(azurerm_private_dns_zone.foundry) == 0
    error_message = "Public Foundry-only mode must not create Private Link resources."
  }
  assert {
    condition     = length(azapi_resource.project) == 0 && length(azapi_resource.model) == 0
    error_message = "Projects and model deployments are optional."
  }
}

run "private_foundry_existing_vnet" {
  command = plan
  module { source = "./modules/shared-foundry" }
  variables {
    private_network = {
      virtual_network_id         = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/network/providers/Microsoft.Network/virtualNetworks/existing"
      private_endpoint_subnet_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/network/providers/Microsoft.Network/virtualNetworks/existing/subnets/pe"
    }
  }
  assert {
    condition     = output.public_network_access == "Disabled" && azapi_resource.account.body.properties.networkAcls.defaultAction == "Deny"
    error_message = "Private mode must fail closed on public Foundry access."
  }
  assert {
    condition     = length(azurerm_private_endpoint.foundry) == 1 && azurerm_private_endpoint.foundry[0].subnet_id == var.private_network.private_endpoint_subnet_id
    error_message = "The PE must be in the caller's existing subnet."
  }
  assert {
    condition     = azurerm_private_endpoint.foundry[0].location == "swedencentral"
    error_message = "The PE NIC must use the existing VNet's region, not the account's region."
  }
  assert {
    condition     = length(azurerm_private_dns_zone.foundry) == 3 && length(azurerm_private_dns_zone_virtual_network_link.foundry) == 3
    error_message = "Create and link all three Foundry endpoint DNS zones."
  }
}

run "reuse_all_dns_zones_and_links" {
  command = plan
  module { source = "./modules/shared-foundry" }
  variables {
    private_network = {
      virtual_network_id         = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/network/providers/Microsoft.Network/virtualNetworks/existing"
      private_endpoint_subnet_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/network/providers/Microsoft.Network/virtualNetworks/existing/subnets/pe"
      create_dns_vnet_links      = false
      private_dns_zone_ids = {
        "privatelink.cognitiveservices.azure.com" = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/dns/providers/Microsoft.Network/privateDnsZones/privatelink.cognitiveservices.azure.com"
        "privatelink.openai.azure.com"            = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/dns/providers/Microsoft.Network/privateDnsZones/privatelink.openai.azure.com"
        "privatelink.services.ai.azure.com"       = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/dns/providers/Microsoft.Network/privateDnsZones/privatelink.services.ai.azure.com"
      }
    }
  }
  assert {
    condition     = length(azurerm_private_dns_zone.foundry) == 0 && length(azurerm_private_dns_zone_virtual_network_link.foundry) == 0
    error_message = "Reusing existing zones/links must not recreate them."
  }
  assert {
    condition     = length(azurerm_private_endpoint.foundry[0].private_dns_zone_group[0].private_dns_zone_ids) == 3
    error_message = "The PE zone group still needs all three existing zones."
  }
}

run "reject_subnet_outside_vnet" {
  command = plan
  module { source = "./modules/shared-foundry" }
  variables {
    private_network = {
      virtual_network_id         = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/network/providers/Microsoft.Network/virtualNetworks/existing"
      private_endpoint_subnet_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/network/providers/Microsoft.Network/virtualNetworks/other/subnets/pe"
    }
  }
  expect_failures = [var.private_network]
}

run "reject_partial_dns_reuse" {
  command = plan
  module { source = "./modules/shared-foundry" }
  variables {
    private_network = {
      virtual_network_id         = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/network/providers/Microsoft.Network/virtualNetworks/existing"
      private_endpoint_subnet_id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/network/providers/Microsoft.Network/virtualNetworks/existing/subnets/pe"
      private_dns_zone_ids       = { "privatelink.openai.azure.com" = "/incomplete-zone-id" }
    }
  }
  expect_failures = [var.private_network]
}
